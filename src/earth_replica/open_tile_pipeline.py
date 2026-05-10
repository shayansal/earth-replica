"""Open geospatial tile ingestion and local 3D Tiles emission."""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

from earth_replica.terrain import TerrainBounds, TerrainTile


@dataclass(frozen=True)
class ProvenanceRecord:
    """Provenance for one observed, inferred, simulated, or rendered layer."""

    source_id: str
    source_name: str
    domain: str
    state: str
    license: str
    resolution: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.state not in {"observed", "inferred", "simulated", "rendered"}:
            raise ValueError("state must be observed, inferred, simulated, or rendered")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_record(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "domain": self.domain,
            "state": self.state,
            "license": self.license,
            "resolution": self.resolution,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class OpenFeature:
    """A small open geospatial feature clipped to a worker tile."""

    feature_id: str
    layer: str
    geometry: tuple[tuple[float, float], ...]
    provenance: ProvenanceRecord
    height_m: float = 0.0
    width_m: float = 0.0

    def __post_init__(self) -> None:
        if not self.feature_id:
            raise ValueError("feature_id is required")
        if not self.geometry:
            raise ValueError("geometry is required")
        if self.height_m < 0:
            raise ValueError("height_m must not be negative")
        if self.width_m < 0:
            raise ValueError("width_m must not be negative")

    def to_record(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "layer": self.layer,
            "geometry": [list(point) for point in self.geometry],
            "height_m": self.height_m,
            "width_m": self.width_m,
            "provenance": self.provenance.to_record(),
        }


@dataclass(frozen=True)
class OpenTileRequest:
    """Request for one local open-data 3D tile worker."""

    h3_index: str
    resolution: int
    center_latitude: float
    center_longitude: float
    bounds: TerrainBounds

    def __post_init__(self) -> None:
        if not self.h3_index:
            raise ValueError("h3_index is required")
        if not 0 <= self.resolution <= 15:
            raise ValueError("resolution must be between 0 and 15")
        if not -90.0 <= self.center_latitude <= 90.0:
            raise ValueError("center_latitude must be between -90 and 90")
        if not -180.0 <= self.center_longitude <= 180.0:
            raise ValueError("center_longitude must be between -180 and 180")

    @property
    def tile_id(self) -> str:
        return f"h3_{self.resolution}_{self.h3_index}"

    def to_record(self) -> dict[str, object]:
        return {
            "h3_index": self.h3_index,
            "resolution": self.resolution,
            "center_latitude": self.center_latitude,
            "center_longitude": self.center_longitude,
            "bounds": self.bounds.to_record(),
        }


@dataclass(frozen=True)
class OpenTileResult:
    """Artifacts emitted by one open tile worker run."""

    root: Path
    tileset_path: Path
    glb_path: Path
    provenance_path: Path
    genesis_patch_path: Path

    def to_record(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "tileset_path": str(self.tileset_path),
            "glb_path": str(self.glb_path),
            "provenance_path": str(self.provenance_path),
            "genesis_patch_path": str(self.genesis_patch_path),
        }


class OpenTileWorker:
    """Build one local 3D Tiles shard from open geospatial inputs."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    def run(
        self,
        *,
        request: OpenTileRequest,
        terrain: TerrainTile,
        buildings: tuple[OpenFeature, ...] = (),
        roads: tuple[OpenFeature, ...] = (),
        water: tuple[OpenFeature, ...] = (),
        land_cover: dict[str, float] | None = None,
    ) -> OpenTileResult:
        tile_root = self.output_root / request.tile_id
        tile_root.mkdir(parents=True, exist_ok=True)

        glb_path = tile_root / "tile.glb"
        tileset_path = tile_root / "tileset.json"
        provenance_path = tile_root / "provenance.json"
        genesis_patch_path = tile_root / "genesis-terrain-patch.json"

        glb_path.write_bytes(_build_glb(request, terrain, buildings, roads, water))
        tileset_path.write_text(
            json.dumps(_build_tileset_record(request, terrain), indent=2),
            encoding="utf-8",
        )
        provenance_path.write_text(
            json.dumps(
                _build_provenance_record(request, terrain, buildings, roads, water, land_cover or {}),
                indent=2,
            ),
            encoding="utf-8",
        )
        genesis_patch_path.write_text(
            json.dumps(
                _build_genesis_patch_record(request, terrain, buildings, roads, water, land_cover or {}),
                indent=2,
            ),
            encoding="utf-8",
        )

        return OpenTileResult(
            root=tile_root,
            tileset_path=tileset_path,
            glb_path=glb_path,
            provenance_path=provenance_path,
            genesis_patch_path=genesis_patch_path,
        )


def _build_tileset_record(request: OpenTileRequest, terrain: TerrainTile) -> dict[str, object]:
    bounds = request.bounds
    return {
        "asset": {
            "version": "1.1",
            "tilesetVersion": "0.1.0",
            "extras": {
                "schema": "earth-replica/open-3d-tiles/v1",
                "h3_index": request.h3_index,
                "provenance": "provenance.json",
                "genesis_patch": "genesis-terrain-patch.json",
            },
        },
        "geometricError": 256,
        "root": {
            "boundingVolume": {
                "region": [
                    math.radians(bounds.min_longitude),
                    math.radians(bounds.min_latitude),
                    math.radians(bounds.max_longitude),
                    math.radians(bounds.max_latitude),
                    terrain.min_elevation_m,
                    max(terrain.max_elevation_m, terrain.min_elevation_m + 1.0) + 80.0,
                ],
            },
            "geometricError": 64,
            "refine": "ADD",
            "content": {"uri": "tile.glb"},
            "transform": _east_north_up_transform(
                request.center_latitude,
                request.center_longitude,
                max(terrain.min_elevation_m, 0.0),
            ),
        },
    }


def _build_provenance_record(
    request: OpenTileRequest,
    terrain: TerrainTile,
    buildings: tuple[OpenFeature, ...],
    roads: tuple[OpenFeature, ...],
    water: tuple[OpenFeature, ...],
    land_cover: dict[str, float],
) -> dict[str, object]:
    records = [
        ProvenanceRecord(
            source_id="terrain:source",
            source_name=terrain.source.name,
            domain="terrain_bathymetry",
            state="observed",
            license="public source metadata required",
            resolution=terrain.source.resolution,
            confidence=0.92,
        ),
        ProvenanceRecord(
            source_id="land-cover:local-classifier",
            source_name="Earth Replica material classifier",
            domain="land_cover",
            state="inferred",
            license="derived from source imagery and terrain",
            resolution="tile aggregate",
            confidence=0.55,
        ),
        ProvenanceRecord(
            source_id="genesis:terrain-patch",
            source_name="Genesis local shard patch",
            domain="water_soil_physics",
            state="simulated",
            license="MIT",
            resolution="local tile",
            confidence=0.5,
        ),
        ProvenanceRecord(
            source_id="3d-tiles:local-glb",
            source_name="Earth Replica local 3D Tiles emitter",
            domain="rendering",
            state="rendered",
            license="MIT",
            resolution="local tile",
            confidence=1.0,
        ),
    ]
    records.extend(feature.provenance for feature in (*buildings, *roads, *water))
    return {
        "schema": "earth-replica/open-tile-provenance/v1",
        "request": request.to_record(),
        "records": [record.to_record() for record in records],
        "feature_counts": {
            "buildings": len(buildings),
            "roads": len(roads),
            "water": len(water),
            "land_cover_classes": len(land_cover),
        },
        "quality_policy": {
            "generated_visuals_are_authoritative": False,
            "separate_observed_inferred_simulated_rendered": True,
            "requires_license_review_before_public_distribution": True,
        },
    }


def _build_genesis_patch_record(
    request: OpenTileRequest,
    terrain: TerrainTile,
    buildings: tuple[OpenFeature, ...],
    roads: tuple[OpenFeature, ...],
    water: tuple[OpenFeature, ...],
    land_cover: dict[str, float],
) -> dict[str, object]:
    return {
        "schema": "earth-replica/genesis-terrain-patch/v1",
        "anchor": {
            "frame": "WGS84",
            "latitude": request.center_latitude,
            "longitude": request.center_longitude,
            "height_m": max(terrain.min_elevation_m, 0.0),
        },
        "extent": {
            "bounds": request.bounds.to_record(),
            "h3_index": request.h3_index,
            "resolution": request.resolution,
        },
        "terrain": {
            "source": terrain.source.to_record(),
            "min_elevation_m": terrain.min_elevation_m,
            "max_elevation_m": terrain.max_elevation_m,
            "grid": terrain.grid_record(),
        },
        "materials": {
            "land_cover": land_cover,
            "water_features": [feature.to_record() for feature in water],
            "soil_classes": _soil_classes(land_cover),
        },
        "obstacles": {
            "buildings": [feature.to_record() for feature in buildings],
            "roads": [feature.to_record() for feature in roads],
        },
        "physics_contract": {
            "engine": "Genesis",
            "expected_materials": ["water", "soil", "terrain"],
            "outputs": ["surface_deformation_m", "water_depth_m", "soil_moisture"],
        },
    }


def _soil_classes(land_cover: dict[str, float]) -> dict[str, float]:
    urban = land_cover.get("urban", 0.0)
    vegetation = land_cover.get("vegetation", 0.0)
    water = land_cover.get("water", 0.0)
    exposed_soil = max(0.0, 1.0 - urban - vegetation - water)
    return {
        "sand": round(exposed_soil * 0.35, 4),
        "loam": round(exposed_soil * 0.45 + vegetation * 0.25, 4),
        "impervious": round(urban, 4),
        "saturated": round(water + vegetation * 0.12, 4),
    }


def _build_glb(
    request: OpenTileRequest,
    terrain: TerrainTile,
    buildings: tuple[OpenFeature, ...],
    roads: tuple[OpenFeature, ...],
    water: tuple[OpenFeature, ...],
) -> bytes:
    builder = _MeshBuilder(request)
    builder.add_terrain(terrain)
    for feature in buildings:
        builder.add_building(feature)
    for feature in roads:
        builder.add_polyline_strip(feature, height_m=0.08)
    for feature in water:
        builder.add_polygon(feature, z_m=0.04)
    return builder.to_glb()


class _MeshBuilder:
    def __init__(self, request: OpenTileRequest) -> None:
        self.request = request
        self.positions: list[tuple[float, float, float]] = []
        self.normals: list[tuple[float, float, float]] = []
        self.indices: list[int] = []

    def add_terrain(self, terrain: TerrainTile) -> None:
        bounds = terrain.bounds
        corners = [
            (bounds.min_longitude, bounds.min_latitude, terrain.min_elevation_m),
            (bounds.max_longitude, bounds.min_latitude, terrain.min_elevation_m),
            (bounds.max_longitude, bounds.max_latitude, terrain.max_elevation_m),
            (bounds.min_longitude, bounds.max_latitude, terrain.max_elevation_m),
        ]
        self._add_quad([self._local(lon, lat, z) for lon, lat, z in corners])

    def add_building(self, feature: OpenFeature) -> None:
        if len(feature.geometry) < 3:
            return
        base = [self._local(lon, lat, 0.1) for lon, lat in feature.geometry[:4]]
        if len(base) == 3:
            base.append(base[-1])
        top = [(x, y, z + max(feature.height_m, 3.0)) for x, y, z in base]
        self._add_quad(base)
        self._add_quad(list(reversed(top)))
        for index in range(4):
            self._add_quad([
                base[index],
                base[(index + 1) % 4],
                top[(index + 1) % 4],
                top[index],
            ])

    def add_polyline_strip(self, feature: OpenFeature, height_m: float) -> None:
        if len(feature.geometry) < 2:
            return
        half_width = max(feature.width_m, 4.0) / 2.0
        for start, end in zip(feature.geometry, feature.geometry[1:]):
            ax, ay, _ = self._local(start[0], start[1], height_m)
            bx, by, _ = self._local(end[0], end[1], height_m)
            dx = bx - ax
            dy = by - ay
            length = math.hypot(dx, dy) or 1.0
            nx = -dy / length * half_width
            ny = dx / length * half_width
            self._add_quad([
                (ax + nx, ay + ny, height_m),
                (bx + nx, by + ny, height_m),
                (bx - nx, by - ny, height_m),
                (ax - nx, ay - ny, height_m),
            ])

    def add_polygon(self, feature: OpenFeature, z_m: float) -> None:
        if len(feature.geometry) < 3:
            return
        points = [self._local(lon, lat, z_m) for lon, lat in feature.geometry[:4]]
        if len(points) == 3:
            points.append(points[-1])
        self._add_quad(points)

    def _add_quad(self, points: list[tuple[float, float, float]]) -> None:
        start = len(self.positions)
        normal = _normal(points[0], points[1], points[2])
        self.positions.extend(points)
        self.normals.extend([normal] * 4)
        self.indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])

    def _local(self, longitude: float, latitude: float, z_m: float) -> tuple[float, float, float]:
        meters_per_degree_lat = 111_320.0
        meters_per_degree_lon = meters_per_degree_lat * math.cos(math.radians(self.request.center_latitude))
        east = (longitude - self.request.center_longitude) * meters_per_degree_lon
        north = (latitude - self.request.center_latitude) * meters_per_degree_lat
        return (east, north, z_m)

    def to_glb(self) -> bytes:
        position_bytes = b"".join(struct.pack("<3f", *value) for value in self.positions)
        normal_bytes = b"".join(struct.pack("<3f", *value) for value in self.normals)
        index_bytes = b"".join(struct.pack("<H", value) for value in self.indices)
        binary = _pad4(position_bytes) + _pad4(normal_bytes) + _pad4(index_bytes)
        position_offset = 0
        normal_offset = len(_pad4(position_bytes))
        index_offset = normal_offset + len(_pad4(normal_bytes))
        mins = [min(position[axis] for position in self.positions) for axis in range(3)]
        maxs = [max(position[axis] for position in self.positions) for axis in range(3)]
        gltf = {
            "asset": {"version": "2.0", "generator": "earth-replica-open-tile-worker"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{
                "primitives": [{
                    "attributes": {"POSITION": 0, "NORMAL": 1},
                    "indices": 2,
                    "mode": 4,
                    "material": 0,
                }],
            }],
            "materials": [{
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.56, 0.68, 0.52, 1.0],
                    "roughnessFactor": 0.82,
                },
            }],
            "buffers": [{"byteLength": len(binary)}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": position_offset, "byteLength": len(position_bytes), "target": 34962},
                {"buffer": 0, "byteOffset": normal_offset, "byteLength": len(normal_bytes), "target": 34962},
                {"buffer": 0, "byteOffset": index_offset, "byteLength": len(index_bytes), "target": 34963},
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,
                    "count": len(self.positions),
                    "type": "VEC3",
                    "min": mins,
                    "max": maxs,
                },
                {
                    "bufferView": 1,
                    "componentType": 5126,
                    "count": len(self.normals),
                    "type": "VEC3",
                },
                {
                    "bufferView": 2,
                    "componentType": 5123,
                    "count": len(self.indices),
                    "type": "SCALAR",
                },
            ],
        }
        json_chunk = _pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), pad_byte=b" ")
        bin_chunk = _pad4(binary)
        total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
        return (
            struct.pack("<4sII", b"glTF", 2, total_length)
            + struct.pack("<I4s", len(json_chunk), b"JSON")
            + json_chunk
            + struct.pack("<I4s", len(bin_chunk), b"BIN\x00")
            + bin_chunk
        )


def _normal(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
) -> tuple[float, float, float]:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)


def _pad4(data: bytes, pad_byte: bytes = b"\x00") -> bytes:
    padding = (-len(data)) % 4
    return data + pad_byte * padding


def _east_north_up_transform(latitude: float, longitude: float, height_m: float) -> list[float]:
    lat = math.radians(latitude)
    lon = math.radians(longitude)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)
    x, y, z = _wgs84_to_ecef(latitude, longitude, height_m)
    east = (-sin_lon, cos_lon, 0.0)
    north = (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat)
    up = (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat)
    return [
        east[0], east[1], east[2], 0.0,
        north[0], north[1], north[2], 0.0,
        up[0], up[1], up[2], 0.0,
        x, y, z, 1.0,
    ]


def _wgs84_to_ecef(latitude: float, longitude: float, height_m: float) -> tuple[float, float, float]:
    semi_major = 6378137.0
    eccentricity_sq = 6.69437999014e-3
    lat = math.radians(latitude)
    lon = math.radians(longitude)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    prime_vertical = semi_major / math.sqrt(1.0 - eccentricity_sq * sin_lat * sin_lat)
    x = (prime_vertical + height_m) * cos_lat * math.cos(lon)
    y = (prime_vertical + height_m) * cos_lat * math.sin(lon)
    z = (prime_vertical * (1.0 - eccentricity_sq) + height_m) * sin_lat
    return (x, y, z)
