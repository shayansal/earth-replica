"""Planetary surface elevation, bathymetry, and provenance models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SurfaceType(StrEnum):
    """Primary surface category for a sampled point or cell."""

    LAND = "land"
    WATER = "water"
    ICE = "ice"
    COAST = "coast"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SurfaceSource:
    """Where a surface sample came from and how trustworthy it is."""

    name: str
    url: str
    vertical_datum: str
    resolution: str
    confidence: str

    def to_record(self) -> dict[str, str]:
        return {
            "name": self.name,
            "url": self.url,
            "vertical_datum": self.vertical_datum,
            "resolution": self.resolution,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SurfaceSample:
    """A known point on Earth's physical surface in meters relative to sea level."""

    name: str
    latitude: float
    longitude: float
    elevation_m: float
    surface_type: SurfaceType
    source: SurfaceSource

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")

    @property
    def is_above_sea_level(self) -> bool:
        return self.elevation_m > 0

    @property
    def is_below_sea_level(self) -> bool:
        return self.elevation_m < 0

    @property
    def depth_m(self) -> float:
        return abs(self.elevation_m) if self.elevation_m < 0 else 0.0

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "depth_m": self.depth_m,
            "surface_type": self.surface_type.value,
            "source": self.source.to_record(),
        }


ETOPO_2022 = SurfaceSource(
    name="NOAA ETOPO 2022 Global Relief Model",
    url="https://www.ncei.noaa.gov/products/etopo-global-relief-model",
    vertical_datum="mean sea level",
    resolution="15 arc-second global topography and bathymetry grid",
    confidence="integrated source grid",
)

GEBCO_2025 = SurfaceSource(
    name="GEBCO_2025 Grid",
    url="https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2025-grid",
    vertical_datum="mean sea level, with regional datum caveats in shallow water",
    resolution="15 arc-second global terrain and bathymetry grid",
    confidence="measured and interpolated source grid",
)

SURVEYED_EXTREMES = SurfaceSource(
    name="Surveyed global elevation/depth reference points",
    url="https://www.ncei.noaa.gov/products/etopo-global-relief-model",
    vertical_datum="mean sea level",
    resolution="known reference point",
    confidence="measured or best available published value",
)

KNOWN_SURFACE_SAMPLES: tuple[SurfaceSample, ...] = (
    SurfaceSample(
        name="Mount Everest",
        latitude=27.9881,
        longitude=86.9250,
        elevation_m=8848.86,
        surface_type=SurfaceType.LAND,
        source=SURVEYED_EXTREMES,
    ),
    SurfaceSample(
        name="Challenger Deep",
        latitude=11.3693,
        longitude=142.5873,
        elevation_m=-10984.0,
        surface_type=SurfaceType.WATER,
        source=GEBCO_2025,
    ),
    SurfaceSample(
        name="Dead Sea shore",
        latitude=31.5590,
        longitude=35.4732,
        elevation_m=-430.5,
        surface_type=SurfaceType.LAND,
        source=ETOPO_2022,
    ),
    SurfaceSample(
        name="Mauna Kea summit",
        latitude=19.8206,
        longitude=-155.4681,
        elevation_m=4207.3,
        surface_type=SurfaceType.LAND,
        source=ETOPO_2022,
    ),
)


def known_surface_records() -> list[dict[str, object]]:
    return [sample.to_record() for sample in KNOWN_SURFACE_SAMPLES]
