"""Terrain tile fetching and parsing for real ETOPO elevation data."""

from __future__ import annotations

import csv
import json
import ssl
import subprocess
import sys
import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import urlopen

from earth_replica.surface import ETOPO_2022, SurfaceSource

ETOPO_ERDDAP_BASE_URL = (
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ETOPO_2022_v1_15s.csvp"
)


@dataclass(frozen=True)
class TerrainBounds:
    """Latitude/longitude bounds for a terrain tile."""

    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.min_latitude <= 90.0:
            raise ValueError("min_latitude must be between -90 and 90")
        if not -90.0 <= self.max_latitude <= 90.0:
            raise ValueError("max_latitude must be between -90 and 90")
        if not -180.0 <= self.min_longitude <= 180.0:
            raise ValueError("min_longitude must be between -180 and 180")
        if not -180.0 <= self.max_longitude <= 180.0:
            raise ValueError("max_longitude must be between -180 and 180")
        if self.min_latitude > self.max_latitude:
            raise ValueError("min_latitude must be <= max_latitude")
        if self.min_longitude > self.max_longitude:
            raise ValueError("min_longitude must be <= max_longitude")

    def to_record(self) -> dict[str, float]:
        return {
            "min_latitude": self.min_latitude,
            "max_latitude": self.max_latitude,
            "min_longitude": self.min_longitude,
            "max_longitude": self.max_longitude,
        }


@dataclass(frozen=True)
class TerrainSample:
    """One terrain elevation sample in real meters."""

    latitude: float
    longitude: float
    elevation_m: float

    def to_record(self) -> dict[str, float]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
        }


@dataclass(frozen=True)
class TerrainTile:
    """A gridded terrain subset from a physical elevation source."""

    bounds: TerrainBounds
    stride: int
    samples: tuple[TerrainSample, ...]
    source: SurfaceSource = ETOPO_2022

    @property
    def min_elevation_m(self) -> float:
        return min(sample.elevation_m for sample in self.samples)

    @property
    def max_elevation_m(self) -> float:
        return max(sample.elevation_m for sample in self.samples)

    @property
    def latitudes(self) -> tuple[float, ...]:
        return tuple(sorted({sample.latitude for sample in self.samples}))

    @property
    def longitudes(self) -> tuple[float, ...]:
        return tuple(sorted({sample.longitude for sample in self.samples}))

    def grid_record(self) -> dict[str, object]:
        latitudes = self.latitudes
        longitudes = self.longitudes
        by_coordinate = {
            (sample.latitude, sample.longitude): sample.elevation_m
            for sample in self.samples
        }
        expected_count = len(latitudes) * len(longitudes)
        if expected_count != len(self.samples):
            raise ValueError("Terrain samples must form a complete latitude/longitude grid")

        elevation_rows = []
        for latitude in latitudes:
            row = []
            for longitude in longitudes:
                coordinate = (latitude, longitude)
                if coordinate not in by_coordinate:
                    raise ValueError("Terrain samples must form a complete latitude/longitude grid")
                row.append(by_coordinate[coordinate])
            elevation_rows.append(row)

        return {
            "latitudes": list(latitudes),
            "longitudes": list(longitudes),
            "latitude_count": len(latitudes),
            "longitude_count": len(longitudes),
            "elevation_rows_m": elevation_rows,
        }

    def to_record(self) -> dict[str, object]:
        return {
            "bounds": self.bounds.to_record(),
            "stride": self.stride,
            "source": self.source.to_record(),
            "min_elevation_m": self.min_elevation_m,
            "max_elevation_m": self.max_elevation_m,
            "grid": self.grid_record(),
            "samples": [sample.to_record() for sample in self.samples],
        }

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_record(), indent=2), encoding="utf-8")
        return path


def build_etopo_erddap_url(bounds: TerrainBounds, stride: int) -> str:
    if stride <= 0:
        raise ValueError("stride must be positive")
    query = (
        f"z[({bounds.min_latitude}):{stride}:({bounds.max_latitude})]"
        f"[({bounds.min_longitude}):{stride}:({bounds.max_longitude})]"
    )
    return f"{ETOPO_ERDDAP_BASE_URL}?{quote(query, safe='')}"


def parse_etopo_csvp(csvp: str, stride: int = 1) -> TerrainTile:
    reader = csv.DictReader(StringIO(csvp))
    samples: list[TerrainSample] = []
    for row in reader:
        if not row:
            continue
        latitude_value = row.get("latitude (degrees_north)") or row.get("latitude")
        longitude_value = row.get("longitude (degrees_east)") or row.get("longitude")
        z_value = row.get("z")
        if latitude_value is None or longitude_value is None or z_value is None:
            raise ValueError(f"Unexpected ETOPO CSV columns: {reader.fieldnames}")
        samples.append(
            TerrainSample(
                latitude=float(latitude_value),
                longitude=float(longitude_value),
                elevation_m=float(z_value),
            )
        )
    if not samples:
        raise ValueError("ETOPO response contained no terrain samples")

    return TerrainTile(
        bounds=TerrainBounds(
            min_latitude=min(sample.latitude for sample in samples),
            max_latitude=max(sample.latitude for sample in samples),
            min_longitude=min(sample.longitude for sample in samples),
            max_longitude=max(sample.longitude for sample in samples),
        ),
        stride=stride,
        samples=tuple(samples),
    )


def fetch_etopo_tile(bounds: TerrainBounds, stride: int = 10, timeout_s: int = 120) -> TerrainTile:
    url = build_etopo_erddap_url(bounds=bounds, stride=stride)
    csvp = _fetch_text(url=url, timeout_s=timeout_s)
    return parse_etopo_csvp(csvp, stride=stride)


def _fetch_text(url: str, timeout_s: int) -> str:
    try:
        with urlopen(url, timeout=timeout_s) as response:
            return response.read().decode("utf-8")
    except URLError as exc:
        if sys.platform != "win32" or not _is_certificate_error(exc):
            raise
        return _fetch_text_with_windows_trust_store(url=url, timeout_s=timeout_s)


def _is_certificate_error(exc: URLError) -> bool:
    return isinstance(exc.reason, ssl.SSLError)


def _fetch_text_with_windows_trust_store(url: str, timeout_s: int) -> str:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$ProgressPreference='SilentlyContinue'; "
            "$u=[Environment]::GetEnvironmentVariable('EARTH_REPLICA_FETCH_URL'); "
            "(Invoke-WebRequest -UseBasicParsing -Uri $u).Content"
        ),
    ]
    env = os.environ.copy()
    env["EARTH_REPLICA_FETCH_URL"] = url
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=env,
    )
    return result.stdout
