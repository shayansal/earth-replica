"""Earth-scale constants and coordinate-system metadata."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EarthScale:
    """Real Earth dimensions used by Earth Replica state records."""

    name: str = "Earth"
    mean_radius_m: float = 6_371_008.8
    equatorial_radius_m: float = 6_378_137.0
    polar_radius_m: float = 6_356_752.314245
    coordinate_system: str = "WGS84 latitude/longitude plus local ENU meters"

    @property
    def mean_circumference_m(self) -> float:
        return 2.0 * math.pi * self.mean_radius_m

    def to_record(self) -> dict[str, float | str]:
        return {
            "name": self.name,
            "mean_radius_m": self.mean_radius_m,
            "equatorial_radius_m": self.equatorial_radius_m,
            "polar_radius_m": self.polar_radius_m,
            "mean_circumference_m": self.mean_circumference_m,
            "coordinate_system": self.coordinate_system,
        }


EARTH_SCALE = EarthScale()
