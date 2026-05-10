"""Facade reconstruction contracts for building-level visual provenance."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode

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


class PanoramaxFacadeAdapter:
    """Discover open Panoramax street-level imagery candidates for building facades."""

    source_name = "Panoramax"

    def __init__(
        self,
        *,
        fetch_json,
        base_url: str = "https://api.panoramax.xyz/api",
        timeout_s: int = 30,
        limit: int = 200,
        max_distance_m: float = 85.0,
    ) -> None:
        self.fetch_json = fetch_json
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.limit = limit
        self.max_distance_m = max_distance_m

    def candidates_for(self, buildings: tuple[OpenFeature, ...]) -> tuple[FacadeCandidate, ...]:
        if not buildings:
            return ()
        payload = self.fetch_json(self._search_url(buildings), self.timeout_s)
        pictures = tuple(_panoramax_pictures(payload))
        candidates = []
        for building in buildings:
            centroid = _feature_centroid_lon_lat(building)
            best = max(
                (
                    _candidate_from_panoramax_picture(
                        building=building,
                        building_centroid=centroid,
                        picture=picture,
                        base_url=self.base_url,
                        max_distance_m=self.max_distance_m,
                    )
                    for picture in pictures
                ),
                key=lambda candidate: candidate.confidence if candidate else -1.0,
                default=None,
            )
            if best is not None:
                candidates.append(best)
        return tuple(candidates)

    def _search_url(self, buildings: tuple[OpenFeature, ...]) -> str:
        min_lon, min_lat, max_lon, max_lat = _features_bbox(buildings, padding_degrees=0.0008)
        query = urlencode(
            {
                "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "limit": str(self.limit),
            }
        )
        return f"{self.base_url}/search?{query}"


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


def _features_bbox(
    features: tuple[OpenFeature, ...],
    *,
    padding_degrees: float = 0.0,
) -> tuple[float, float, float, float]:
    longitudes = [point[0] for feature in features for point in feature.geometry]
    latitudes = [point[1] for feature in features for point in feature.geometry]
    return (
        min(longitudes) - padding_degrees,
        min(latitudes) - padding_degrees,
        max(longitudes) + padding_degrees,
        max(latitudes) + padding_degrees,
    )


def _feature_centroid_lon_lat(feature: OpenFeature) -> tuple[float, float]:
    count = len(feature.geometry) or 1
    return (
        sum(point[0] for point in feature.geometry) / count,
        sum(point[1] for point in feature.geometry) / count,
    )


def _panoramax_pictures(payload: dict[str, object]) -> list[dict[str, object]]:
    features = payload.get("features", [])
    if not isinstance(features, list):
        return []
    return [feature for feature in features if isinstance(feature, dict)]


def _candidate_from_panoramax_picture(
    *,
    building: OpenFeature,
    building_centroid: tuple[float, float],
    picture: dict[str, object],
    base_url: str,
    max_distance_m: float,
) -> FacadeCandidate | None:
    picture_point = _panoramax_picture_point(picture)
    if picture_point is None:
        return None
    distance_m = _distance_meters(picture_point, building_centroid)
    if distance_m > max_distance_m:
        return None
    properties = picture.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    azimuth = _float_or_none(properties.get("view:azimuth"))
    facing_score = _facing_score(picture_point, building_centroid, azimuth)
    if facing_score < 0.25:
        return None
    picture_id = str(picture.get("id", "")).strip()
    if not picture_id:
        return None
    asset_href = _best_panoramax_asset_href(picture)
    confidence = round(max(0.0, min(0.96, 0.5 + facing_score * 0.32 + (1.0 - distance_m / max_distance_m) * 0.18)), 3)
    return FacadeCandidate(
        building_id=building.feature_id,
        source_name="Panoramax",
        source_uri=f"{base_url}/search?ids={picture_id}",
        texture_uri=asset_href,
        license="open street-level imagery; verify item license before redistribution",
        confidence=confidence,
        captured_at=str(properties.get("datetime") or properties.get("datetimetz") or "") or None,
    )


def _panoramax_picture_point(picture: dict[str, object]) -> tuple[float, float] | None:
    geometry = picture.get("geometry", {})
    if not isinstance(geometry, dict):
        return None
    coordinates = geometry.get("coordinates", [])
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        return None
    lon = _float_or_none(coordinates[0])
    lat = _float_or_none(coordinates[1])
    if lon is None or lat is None:
        return None
    return (lon, lat)


def _best_panoramax_asset_href(picture: dict[str, object]) -> str | None:
    assets = picture.get("assets", {})
    if not isinstance(assets, dict):
        return None
    for key in ("hd", "sd", "visual", "thumbnail", "thumb"):
        asset = assets.get(key)
        if isinstance(asset, dict) and asset.get("href"):
            return str(asset["href"])
    for asset in assets.values():
        if isinstance(asset, dict) and asset.get("href"):
            return str(asset["href"])
    return None


def _facing_score(
    camera_lon_lat: tuple[float, float],
    target_lon_lat: tuple[float, float],
    azimuth: float | None,
) -> float:
    if azimuth is None:
        return 0.5
    target_bearing = _bearing_degrees(camera_lon_lat, target_lon_lat)
    delta = abs((azimuth - target_bearing + 180.0) % 360.0 - 180.0)
    return max(0.0, 1.0 - delta / 90.0)


def _bearing_degrees(start_lon_lat: tuple[float, float], end_lon_lat: tuple[float, float]) -> float:
    start_lon, start_lat = map(math.radians, start_lon_lat)
    end_lon, end_lat = map(math.radians, end_lon_lat)
    delta_lon = end_lon - start_lon
    y = math.sin(delta_lon) * math.cos(end_lat)
    x = math.cos(start_lat) * math.sin(end_lat) - math.sin(start_lat) * math.cos(end_lat) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _distance_meters(a_lon_lat: tuple[float, float], b_lon_lat: tuple[float, float]) -> float:
    lon_a, lat_a = a_lon_lat
    lon_b, lat_b = b_lon_lat
    mean_lat = math.radians((lat_a + lat_b) / 2.0)
    meters_per_degree_lat = 111_320.0
    meters_per_degree_lon = meters_per_degree_lat * math.cos(mean_lat)
    return math.hypot((lon_b - lon_a) * meters_per_degree_lon, (lat_b - lat_a) * meters_per_degree_lat)


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
