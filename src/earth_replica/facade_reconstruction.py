"""Facade reconstruction contracts for building-level visual provenance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from earth_replica.open_tile_pipeline import OpenFeature


@dataclass(frozen=True)
class FacadeCandidate:
    """One measured or cataloged facade image candidate for a building."""

    building_id: str
    source_name: str
    source_uri: str
    license: str
    confidence: float
    texture_uri: str | None = None
    captured_at: str | None = None

    def __post_init__(self) -> None:
        if not self.building_id:
            raise ValueError("building_id is required")
        if not self.source_name:
            raise ValueError("source_name is required")
        if not self.source_uri:
            raise ValueError("source_uri is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "building_id": self.building_id,
            "source_name": self.source_name,
            "source_uri": self.source_uri,
            "license": self.license,
            "confidence": self.confidence,
        }
        if self.texture_uri is not None:
            record["texture_uri"] = self.texture_uri
        if self.captured_at is not None:
            record["captured_at"] = self.captured_at
        return record


class FacadeAdapter(Protocol):
    """Source adapter that returns facade candidates for a set of buildings."""

    source_name: str

    def candidates_for(self, buildings: tuple[OpenFeature, ...]) -> tuple[FacadeCandidate, ...]:
        """Return candidate facade observations keyed by building feature id."""


@dataclass(frozen=True)
class FacadeAssignment:
    """Selected facade source for a building, or an honest inferred fallback."""

    building_id: str
    state: str
    style: str
    confidence: float
    source_name: str
    license: str
    source_uri: str | None = None
    texture_uri: str | None = None
    captured_at: str | None = None

    def __post_init__(self) -> None:
        if self.state not in {"observed", "inferred"}:
            raise ValueError("state must be observed or inferred")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "building_id": self.building_id,
            "state": self.state,
            "style": self.style,
            "confidence": self.confidence,
            "source_name": self.source_name,
            "license": self.license,
        }
        if self.source_uri is not None:
            record["source_uri"] = self.source_uri
        if self.texture_uri is not None:
            record["texture_uri"] = self.texture_uri
        if self.captured_at is not None:
            record["captured_at"] = self.captured_at
        return record


@dataclass(frozen=True)
class FacadeReconstructionResult:
    """Per-building facade assignments and aggregate coverage."""

    assignments: tuple[FacadeAssignment, ...]

    @property
    def observed_feature_count(self) -> int:
        return sum(1 for assignment in self.assignments if assignment.state == "observed")

    @property
    def inferred_feature_count(self) -> int:
        return sum(1 for assignment in self.assignments if assignment.state == "inferred")

    @property
    def state(self) -> str:
        if self.assignments and self.observed_feature_count == len(self.assignments):
            return "observed"
        if self.observed_feature_count:
            return "mixed"
        return "inferred"

    @property
    def source_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for assignment in self.assignments:
            if assignment.state != "observed":
                continue
            counts[assignment.source_name] = counts.get(assignment.source_name, 0) + 1
        return counts

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/facade-reconstruction/v1",
            "state": self.state,
            "building_count": len(self.assignments),
            "observed_feature_count": self.observed_feature_count,
            "inferred_feature_count": self.inferred_feature_count,
            "source_counts": self.source_counts,
            "assignments": [assignment.to_record() for assignment in self.assignments],
            "quality_policy": {
                "observed_facades_remain_separate_from_inferred_facades": True,
                "missing_facade_imagery_uses_inferred_style_fallback": True,
            },
        }


class LocalFacadeCatalogAdapter:
    """Read facade candidates from a local JSON catalog."""

    source_name = "Local facade catalog"

    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = catalog_path

    def candidates_for(self, buildings: tuple[OpenFeature, ...]) -> tuple[FacadeCandidate, ...]:
        building_ids = {building.feature_id for building in buildings}
        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        candidates = []
        for item in payload.get("candidates", []):
            building_id = str(item.get("building_id", ""))
            if building_id not in building_ids:
                continue
            candidates.append(
                FacadeCandidate(
                    building_id=building_id,
                    source_name=str(item.get("source_name") or self.source_name),
                    source_uri=str(item.get("source_uri", "")),
                    texture_uri=item.get("texture_uri"),
                    license=str(item.get("license", "source license required")),
                    confidence=float(item.get("confidence", 0.0)),
                    captured_at=item.get("captured_at"),
                )
            )
        return tuple(candidates)


def reconstruct_facades(
    buildings: tuple[OpenFeature, ...],
    *,
    adapters: tuple[FacadeAdapter, ...] = (),
) -> FacadeReconstructionResult:
    """Select the best facade observation for each building, falling back to inferred style."""

    candidates_by_building: dict[str, list[FacadeCandidate]] = {}
    for adapter in adapters:
        for candidate in adapter.candidates_for(buildings):
            candidates_by_building.setdefault(candidate.building_id, []).append(candidate)

    assignments = []
    for building in buildings:
        candidates = candidates_by_building.get(building.feature_id, [])
        best_candidate = max(candidates, key=lambda candidate: candidate.confidence, default=None)
        style = _facade_style(building.height_m)
        if best_candidate is None:
            assignments.append(
                FacadeAssignment(
                    building_id=building.feature_id,
                    state="inferred",
                    style=style,
                    confidence=_inferred_confidence(style),
                    source_name="Earth Replica procedural facade atlas",
                    license="MIT",
                )
            )
            continue
        assignments.append(
            FacadeAssignment(
                building_id=building.feature_id,
                state="observed",
                style=style,
                confidence=best_candidate.confidence,
                source_name=best_candidate.source_name,
                source_uri=best_candidate.source_uri,
                texture_uri=best_candidate.texture_uri,
                license=best_candidate.license,
                captured_at=best_candidate.captured_at,
            )
        )

    return FacadeReconstructionResult(tuple(assignments))


def _facade_style(height_m: float) -> str:
    if height_m <= 18.0:
        return "low_rise"
    if height_m <= 60.0:
        return "mid_rise"
    return "high_rise"


def _inferred_confidence(style: str) -> float:
    return {
        "low_rise": 0.42,
        "mid_rise": 0.36,
        "high_rise": 0.32,
    }[style]
