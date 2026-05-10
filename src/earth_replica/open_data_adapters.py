"""Adapters for open OSM and Overture-shaped geospatial feature ingestion."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Callable, Iterable, Any
from urllib.request import Request, urlopen

from earth_replica.open_tile_pipeline import OpenFeature, ProvenanceRecord
from earth_replica.terrain import TerrainBounds

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


FetchText = Callable[[str, bytes, int], str]


def build_overpass_query(bounds: TerrainBounds) -> str:
    """Build a bounded Overpass query for roads, water, parks, coastlines, and landuse."""

    bbox = (
        f"{bounds.min_latitude},{bounds.min_longitude},"
        f"{bounds.max_latitude},{bounds.max_longitude}"
    )
    return f"""
[out:json][timeout:60];
(
  way["highway"]({bbox});
  way["natural"="water"]({bbox});
  way["waterway"]({bbox});
  way["natural"="coastline"]({bbox});
  way["leisure"="park"]({bbox});
  way["landuse"]({bbox});
);
out geom;
""".strip()


def fetch_osm_features(
    bounds: TerrainBounds,
    *,
    timeout_s: int = 60,
    fetcher: FetchText | None = None,
) -> tuple[tuple[OpenFeature, ...], tuple[OpenFeature, ...], dict[str, float]]:
    """Fetch bounded OSM features from Overpass.

    Whole-planet ingestion should use planet PBF/regional extracts instead of
    this bounded Overpass adapter. This function is for preview tiles and smoke
    tests only.
    """

    fetch = fetcher or _default_fetch_text
    data = build_overpass_query(bounds).encode("utf-8")
    payload = json.loads(fetch(OVERPASS_URL, data, timeout_s))
    return features_from_osm_overpass(payload)


def features_from_osm_overpass(payload: dict[str, Any]) -> tuple[tuple[OpenFeature, ...], tuple[OpenFeature, ...], dict[str, float]]:
    roads: list[OpenFeature] = []
    water: list[OpenFeature] = []
    land_cover_counts = {"urban": 0.0, "vegetation": 0.0, "water": 0.0}
    for element in payload.get("elements", []):
        if element.get("type") != "way":
            continue
        geometry = _geometry_from_overpass(element)
        if len(geometry) < 2:
            continue
        tags = element.get("tags", {})
        way_id = element.get("id", "unknown")
        if "highway" in tags:
            roads.append(
                OpenFeature(
                    feature_id=f"osm:way:{way_id}",
                    layer="roads",
                    geometry=geometry,
                    width_m=_road_width(tags.get("highway", "")),
                    provenance=_osm_provenance(f"osm:way:{way_id}", "roads", "mapped way"),
                )
            )
            land_cover_counts["urban"] += 1.0
        elif tags.get("natural") == "water" or "waterway" in tags or tags.get("natural") == "coastline":
            water.append(
                OpenFeature(
                    feature_id=f"osm:way:{way_id}",
                    layer="water",
                    geometry=geometry,
                    provenance=_osm_provenance(f"osm:way:{way_id}", "water", "mapped polygon/way"),
                )
            )
            land_cover_counts["water"] += 1.0
        elif tags.get("leisure") == "park" or "landuse" in tags:
            if tags.get("landuse") in {"residential", "commercial", "industrial", "retail"}:
                land_cover_counts["urban"] += 1.0
            else:
                land_cover_counts["vegetation"] += 1.0

    total = sum(land_cover_counts.values())
    if total <= 0:
        land_cover = {"urban": 0.0, "vegetation": 0.0, "water": 0.0}
    else:
        land_cover = {
            key: round(value / total, 4)
            for key, value in land_cover_counts.items()
        }
    return (tuple(roads), tuple(water), land_cover)


def features_from_overture_records(
    records: Iterable[dict[str, Any]],
    bounds: TerrainBounds,
) -> tuple[OpenFeature, ...]:
    """Convert Overture-shaped records into worker features.

    The reader accepts records from a future GeoParquet scan. Geometry can be
    WKB bytes or an iterable of (longitude, latitude) tuples.
    """

    buildings: list[OpenFeature] = []
    for record in records:
        geometry = _geometry_from_overture_record(record)
        clipped = tuple(
            point
            for point in geometry
            if bounds.min_longitude <= point[0] <= bounds.max_longitude
            and bounds.min_latitude <= point[1] <= bounds.max_latitude
        )
        if len(clipped) < 3:
            continue
        feature_id = str(record.get("id") or record.get("id_overture") or "unknown")
        height = _height_from_record(record)
        buildings.append(
            OpenFeature(
                feature_id=f"overture:{feature_id}",
                layer="buildings",
                geometry=clipped,
                height_m=height,
                provenance=ProvenanceRecord(
                    source_id=f"overture:{feature_id}",
                    source_name="Overture Maps Buildings",
                    domain="buildings",
                    state="observed",
                    license="CDLA Permissive 2.0",
                    resolution="feature footprint",
                    confidence=0.9,
                ),
            )
        )
    return tuple(buildings)


def load_overture_buildings_from_geoparquet(path: str, bounds: TerrainBounds) -> tuple[OpenFeature, ...]:
    """Load Overture building features from a local GeoParquet file.

    Requires optional `pyarrow`. This intentionally reads a local/regional file;
    whole-planet runs should scan partitioned Overture GeoParquet through a
    distributed worker pool.
    """

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow is required to read Overture GeoParquet") from exc
    table = pq.read_table(path)
    return features_from_overture_records(table.to_pylist(), bounds)


def _default_fetch_text(url: str, data: bytes, timeout_s: int) -> str:
    request = Request(url, data=data, headers={"Content-Type": "text/plain; charset=utf-8"})
    with urlopen(request, timeout=timeout_s) as response:
        return response.read().decode("utf-8")


def _geometry_from_overpass(element: dict[str, Any]) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(point["lon"]), float(point["lat"]))
        for point in element.get("geometry", [])
        if "lon" in point and "lat" in point
    )


def _geometry_from_overture_record(record: dict[str, Any]) -> tuple[tuple[float, float], ...]:
    geometry = record.get("geometry")
    if isinstance(geometry, bytes):
        return _polygon_points_from_wkb(geometry)
    if isinstance(geometry, str):
        try:
            return _polygon_points_from_wkb(bytes.fromhex(geometry))
        except ValueError:
            return ()
    if geometry is None:
        return ()
    return tuple((float(point[0]), float(point[1])) for point in geometry)


def _polygon_points_from_wkb(wkb: bytes) -> tuple[tuple[float, float], ...]:
    if len(wkb) < 13:
        return ()
    endian_flag = wkb[0]
    endian = "<" if endian_flag == 1 else ">"
    geometry_type = struct.unpack_from(f"{endian}I", wkb, 1)[0]
    if geometry_type != 3:
        return ()
    ring_count = struct.unpack_from(f"{endian}I", wkb, 5)[0]
    if ring_count < 1:
        return ()
    offset = 9
    point_count = struct.unpack_from(f"{endian}I", wkb, offset)[0]
    offset += 4
    points = []
    for _ in range(point_count):
        longitude, latitude = struct.unpack_from(f"{endian}dd", wkb, offset)
        offset += 16
        points.append((longitude, latitude))
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return tuple(points)


def _height_from_record(record: dict[str, Any]) -> float:
    for key in ("height", "height_m", "building_height"):
        value = record.get(key)
        if value is not None:
            return max(float(value), 3.0)
    levels = record.get("levels") or record.get("num_floors")
    if levels is not None:
        return max(float(levels) * 3.2, 3.0)
    return 9.0


def _road_width(highway: str) -> float:
    if highway in {"motorway", "trunk"}:
        return 28.0
    if highway in {"primary", "secondary"}:
        return 16.0
    if highway in {"tertiary", "residential"}:
        return 10.0
    return 6.0


def _osm_provenance(source_id: str, domain: str, resolution: str) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_id=source_id,
        source_name="OpenStreetMap",
        domain=domain,
        state="observed",
        license="ODbL",
        resolution=resolution,
        confidence=0.82,
    )
