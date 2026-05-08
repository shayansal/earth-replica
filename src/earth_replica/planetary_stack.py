"""Foundational subsystems for a planetary-scale Earth digital twin.

These types do not pretend to simulate Earth by themselves. They define the
contracts required to plug real data, tile storage, solvers, schedulers,
streaming, validation, and governance into the shard runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from earth_replica.runtime import ShardSpec


@dataclass(frozen=True)
class DatasetSource:
    """A source of planetary observations or reference data."""

    name: str
    domain: str
    uri: str
    resolution: str
    license: str
    update_cadence: str
    provenance_required: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")
        if not self.domain:
            raise ValueError("domain is required")
        if not self.uri:
            raise ValueError("uri is required")

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "domain": self.domain,
            "uri": self.uri,
            "resolution": self.resolution,
            "license": self.license,
            "update_cadence": self.update_cadence,
            "provenance_required": self.provenance_required,
        }


class PlanetaryDataFabric:
    """Registry for datasets feeding the digital twin."""

    def __init__(self) -> None:
        self._sources: dict[str, DatasetSource] = {}

    def register(self, source: DatasetSource) -> None:
        self._sources[source.name] = source

    def require(self, name: str) -> DatasetSource:
        try:
            return self._sources[name]
        except KeyError as exc:
            raise KeyError(f"Unknown dataset source: {name}") from exc

    def catalog_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/data-fabric-catalog/v1",
            "sources": [source.to_record() for source in self._sources.values()],
        }


@dataclass(frozen=True)
class PlanetaryTile:
    """Persistent state bundle for one simulation shard."""

    spec: ShardSpec
    material_layers: tuple[str, ...]
    neighbor_shards: tuple[str, ...] = ()
    state: dict[str, Any] = field(default_factory=dict)
    source_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.material_layers:
            raise ValueError("material_layers must not be empty")

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/planetary-tile/v1",
            "spec": self.spec.to_record(),
            "material_layers": list(self.material_layers),
            "neighbor_shards": list(self.neighbor_shards),
            "state": self.state,
            "source_names": list(self.source_names),
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> PlanetaryTile:
        spec_record = record["spec"]
        return cls(
            spec=ShardSpec(
                h3_index=spec_record["h3_index"],
                resolution=int(spec_record["resolution"]),
                extent_m=float(spec_record["extent_m"]),
                execution_scope=spec_record.get("execution_scope", "tile"),
                fidelity=spec_record.get("fidelity", "local-physics-preview"),
            ),
            material_layers=tuple(record["material_layers"]),
            neighbor_shards=tuple(record.get("neighbor_shards", ())),
            state=dict(record.get("state", {})),
            source_names=tuple(record.get("source_names", ())),
        )


class TileStore:
    """Filesystem tile store that can be replaced by object storage later."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, shard_id: str) -> Path:
        return self.root / f"{shard_id.replace(':', '_')}.json"

    def write(self, tile: PlanetaryTile) -> Path:
        path = self.path_for(tile.spec.shard_id)
        path.write_text(json.dumps(tile.to_record(), indent=2), encoding="utf-8")
        return path

    def read(self, shard_id: str) -> PlanetaryTile:
        return PlanetaryTile.from_record(
            json.loads(self.path_for(shard_id).read_text(encoding="utf-8"))
        )


@dataclass(frozen=True)
class CoupledSolverPlan:
    """Map physical domains to engines and define boundary coupling."""

    domain_engines: dict[str, str]
    coupling: str
    exchange_quantities: tuple[str, ...]

    @classmethod
    def local_default(cls) -> CoupledSolverPlan:
        return cls(
            domain_engines={
                "rigid": "Genesis Rigid",
                "water": "Genesis SPH",
                "soil": "Genesis MPM",
                "terrain": "Genesis Terrain",
                "atmosphere": "external CFD",
                "ocean": "external CFD",
                "hydrology": "external hydrology",
                "traffic": "external agent simulation",
            },
            coupling="tile-boundary exchange",
            exchange_quantities=(
                "height",
                "velocity",
                "pressure",
                "temperature",
                "moisture",
                "uncertainty",
            ),
        )

    def engine_for(self, domain: str) -> str:
        try:
            return self.domain_engines[domain]
        except KeyError as exc:
            raise KeyError(f"No solver engine registered for domain: {domain}") from exc

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/coupled-solver-plan/v1",
            "domain_engines": self.domain_engines,
            "coupling": self.coupling,
            "exchange_quantities": list(self.exchange_quantities),
        }


@dataclass(frozen=True)
class DistributedExecutionPlan:
    """Scheduler plan that can run locally or target a cluster backend."""

    mode: str
    backends: tuple[str, ...]
    max_active_shards: int
    scheduler_features: dict[str, bool]

    @classmethod
    def local_exascale_shape(cls, max_active_shards: int = 1) -> DistributedExecutionPlan:
        return cls(
            mode="local",
            backends=("local-process",),
            max_active_shards=max_active_shards,
            scheduler_features={
                "checkpoint_restart": True,
                "tile_activation": True,
                "neighbor_boundary_exchange": True,
                "job_migration": False,
                "federated_workers": False,
            },
        )

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/distributed-execution-plan/v1",
            "mode": self.mode,
            "backends": list(self.backends),
            "max_active_shards": self.max_active_shards,
            "scheduler_features": self.scheduler_features,
        }


@dataclass(frozen=True)
class TileStreamManifest:
    """Browser streaming contract for terrain, physics, and time layers."""

    root_uri: str
    lod_levels: tuple[int, ...]
    visible_layers: tuple[str, ...]
    time_window_s: float
    streaming: str = "progressive"

    def __post_init__(self) -> None:
        if self.time_window_s <= 0:
            raise ValueError("time_window_s must be positive")
        if not self.lod_levels:
            raise ValueError("lod_levels must not be empty")

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/tile-stream-manifest/v1",
            "root_uri": self.root_uri,
            "lod_levels": list(self.lod_levels),
            "visible_layers": list(self.visible_layers),
            "time_window_s": self.time_window_s,
            "streaming": self.streaming,
        }


@dataclass(frozen=True)
class ValidationObservation:
    """One observed-vs-predicted validation point."""

    quantity: str
    predicted: float
    observed: float
    tolerance: float
    source: str

    @property
    def absolute_error(self) -> float:
        return round(abs(self.predicted - self.observed), 10)

    @property
    def passed(self) -> bool:
        return self.absolute_error <= self.tolerance

    def to_record(self) -> dict[str, object]:
        return {
            "quantity": self.quantity,
            "predicted": self.predicted,
            "observed": self.observed,
            "tolerance": self.tolerance,
            "absolute_error": self.absolute_error,
            "passed": self.passed,
            "source": self.source,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Validation result for a tile at a point in time."""

    shard_id: str
    observed_at: datetime
    observations: tuple[ValidationObservation, ...]

    @property
    def passed(self) -> bool:
        return all(observation.passed for observation in self.observations)

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/validation-report/v1",
            "shard_id": self.shard_id,
            "observed_at": self.observed_at.isoformat(),
            "passed": self.passed,
            "metrics": [observation.to_record() for observation in self.observations],
        }


@dataclass(frozen=True)
class AccessPolicy:
    """Dataset and live-sensor export policy."""

    allowed_export_domains: tuple[str, ...]
    blocked_export_domains: tuple[str, ...]
    required_reviews: tuple[str, ...]

    @classmethod
    def public_open_source_default(cls) -> AccessPolicy:
        return cls(
            allowed_export_domains=(
                "terrain",
                "bathymetry",
                "weather_public",
                "derived_simulation",
            ),
            blocked_export_domains=(
                "live_private_sensor",
                "personal_location",
                "restricted_infrastructure",
            ),
            required_reviews=("license_review", "privacy_review", "security_review"),
        )

    def can_export(self, domain: str) -> bool:
        if domain in self.blocked_export_domains:
            return False
        return domain in self.allowed_export_domains

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/access-policy/v1",
            "allowed_export_domains": list(self.allowed_export_domains),
            "blocked_export_domains": list(self.blocked_export_domains),
            "required_reviews": list(self.required_reviews),
        }
