"""Planetary cell state primitives for Earth Replica."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


FIDELITY_LEVELS = {
    "illustrative",
    "interactive",
    "engineering",
    "research",
    "observed",
    "data-dependent",
    "progressive",
    "perceptual",
}


@dataclass(frozen=True)
class CellState:
    """Observed or simulated state for a single H3-indexed Earth cell."""

    h3_index: str
    resolution: int
    latitude: float
    longitude: float
    observed_at: datetime
    fidelity: str
    elevation_m: float = 0.0
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.h3_index:
            raise ValueError("h3_index is required")
        if not 0 <= self.resolution <= 15:
            raise ValueError("resolution must be between 0 and 15")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.fidelity not in FIDELITY_LEVELS:
            raise ValueError(f"fidelity must be one of {sorted(FIDELITY_LEVELS)}")

    @property
    def center_wkt(self) -> str:
        return f"POINT({self.longitude} {self.latitude})"

    def to_postgis_row(self) -> dict[str, Any]:
        """Return a DB-ready row shape for the PostGIS cell observation tables."""

        return {
            "h3_index": self.h3_index,
            "resolution": self.resolution,
            "center_wkt": self.center_wkt,
            "observed_at": self.observed_at.isoformat(),
            "fidelity": self.fidelity,
            "properties": self.properties,
        }


@dataclass(frozen=True)
class LocalGenesisCell:
    """A bounded local Genesis scene rooted at a planetary H3 cell center."""

    h3_index: str
    origin_latitude: float
    origin_longitude: float
    origin_elevation_m: float
    extent_m: float

    @classmethod
    def from_cell_state(cls, cell: CellState, extent_m: float) -> LocalGenesisCell:
        if extent_m <= 0:
            raise ValueError("extent_m must be positive")
        return cls(
            h3_index=cell.h3_index,
            origin_latitude=cell.latitude,
            origin_longitude=cell.longitude,
            origin_elevation_m=cell.elevation_m,
            extent_m=extent_m,
        )

    @property
    def genesis_origin(self) -> tuple[float, float, float]:
        return (0.0, 0.0, self.origin_elevation_m)
