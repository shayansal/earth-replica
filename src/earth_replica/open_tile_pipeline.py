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
    metrics: dict[str, int]
    terrain_texture_path: Path | None = None
    facade_texture_path: Path | None = None

    def to_record(self) -> dict[str, str]:
        record = {
            "root": str(self.root),
            "tileset_path": str(self.tileset_path),
            "glb_path": str(self.glb_path),
            "provenance_path": str(self.provenance_path),
            "genesis_patch_path": str(self.genesis_patch_path),
        }
        if self.terrain_texture_path is not None:
            record["terrain_texture_path"] = str(self.terrain_texture_path)
        if self.facade_texture_path is not None:
            record["facade_texture_path"] = str(self.facade_texture_path)
        return record


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
        terrain_texture_uri: str | None = None,
        facade_texture_uri: str | None = None,
    ) -> OpenTileResult:
        tile_root = self.output_root / request.tile_id
        tile_root.mkdir(parents=True, exist_ok=True)

        glb_path = tile_root / "tile.glb"
        tileset_path = tile_root / "tileset.json"
        provenance_path = tile_root / "provenance.json"
        genesis_patch_path = tile_root / "genesis-terrain-patch.json"
        terrain_texture_path = tile_root / terrain_texture_uri if terrain_texture_uri else None
        facade_texture_path = tile_root / facade_texture_uri if facade_texture_uri else None

        mesh_metrics: dict[str, int] = {}
        glb_path.write_bytes(
            _build_glb(
                request,
                terrain,
                buildings,
                roads,
                water,
                mesh_metrics,
                terrain_texture_uri,
                facade_texture_uri,
            )
        )
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
            metrics={
                **mesh_metrics,
                "building_features": len(buildings),
                "road_features": len(roads),
                "water_features": len(water),
            },
            terrain_texture_path=terrain_texture_path,
            facade_texture_path=facade_texture_path,
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
    metrics: dict[str, int],
    terrain_texture_uri: str | None = None,
    facade_texture_uri: str | None = None,
) -> bytes:
    builder = _MeshBuilder(request)
    builder.add_terrain(terrain)
    for feature in buildings:
        builder.add_building(feature)
    for feature in roads:
        builder.add_polyline_strip(feature, height_m=0.08)
    for feature in water:
        builder.add_polygon(feature, z_m=0.04)
    metrics["terrain_vertices"] = builder.terrain_vertices
    metrics["vertices"] = len(builder.positions)
    metrics["triangles"] = sum(len(indices) for indices in builder.primitive_indices.values()) // 3
    metrics["material_primitives"] = sum(1 for indices in builder.primitive_indices.values() if indices)
    metrics["terrain_textured"] = 1 if terrain_texture_uri else 0
    metrics["roof_textured"] = 1 if terrain_texture_uri and builder.primitive_indices.get(4) else 0
    metrics["facade_textured"] = 1 if facade_texture_uri and builder.primitive_indices.get(1) else 0
    return builder.to_glb(terrain_texture_uri=terrain_texture_uri, facade_texture_uri=facade_texture_uri)


class _MeshBuilder:
    def __init__(self, request: OpenTileRequest) -> None:
        self.request = request
        self.positions: list[tuple[float, float, float]] = []
        self.normals: list[tuple[float, float, float]] = []
        self.texcoords: list[tuple[float, float]] = []
        self.primitive_indices: dict[int, list[int]] = {
            0: [],
            1: [],
            2: [],
            3: [],
            4: [],
        }
        self.terrain_vertices = 0

    def add_terrain(self, terrain: TerrainTile) -> None:
        latitudes = terrain.latitudes
        longitudes = terrain.longitudes
        by_coordinate = {
            (sample.latitude, sample.longitude): sample.elevation_m
            for sample in terrain.samples
        }
        vertex_indices: list[list[int]] = []
        for latitude in latitudes:
            row = []
            for longitude in longitudes:
                row.append(
                    self._add_vertex(
                        self._local(longitude, latitude, by_coordinate[(latitude, longitude)]),
                        (0.0, 0.0, 1.0),
                        _terrain_uv(terrain.bounds, longitude, latitude),
                    )
                )
            vertex_indices.append(row)
        for lat_index in range(len(latitudes) - 1):
            for lon_index in range(len(longitudes) - 1):
                a = vertex_indices[lat_index][lon_index]
                b = vertex_indices[lat_index][lon_index + 1]
                c = vertex_indices[lat_index + 1][lon_index + 1]
                d = vertex_indices[lat_index + 1][lon_index]
                self.primitive_indices[0].extend([a, b, c, a, c, d])
        self.terrain_vertices = len(latitudes) * len(longitudes)

    def add_building(self, feature: OpenFeature) -> None:
        if len(feature.geometry) < 3:
            return
        footprint = feature.geometry[:4]
        base = [self._local(lon, lat, 0.1) for lon, lat in footprint]
        if len(base) == 3:
            base.append(base[-1])
            footprint = (*footprint, footprint[-1])
        top = [(x, y, z + max(feature.height_m, 3.0)) for x, y, z in base]
        self._add_quad(base, material_index=1)
        roof_texcoords = [_terrain_uv(self.request.bounds, lon, lat) for lon, lat in footprint]
        self._add_quad(list(reversed(top)), material_index=4, texcoords=list(reversed(roof_texcoords)))
        for index in range(4):
            self._add_quad([
                base[index],
                base[(index + 1) % 4],
                top[(index + 1) % 4],
                top[index],
            ], material_index=1)

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
            ], material_index=2)

    def add_polygon(self, feature: OpenFeature, z_m: float) -> None:
        if len(feature.geometry) < 3:
            return
        points = [self._local(lon, lat, z_m) for lon, lat in feature.geometry[:4]]
        if len(points) == 3:
            points.append(points[-1])
        self._add_quad(points, material_index=3)

    def _add_quad(
        self,
        points: list[tuple[float, float, float]],
        material_index: int,
        texcoords: list[tuple[float, float]] | None = None,
    ) -> None:
        normal = _normal(points[0], points[1], points[2])
        start = len(self.positions)
        quad_texcoords = texcoords or [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        for point, texcoord in zip(points, quad_texcoords):
            self._add_vertex(point, normal, texcoord)
        self.primitive_indices[material_index].extend([start, start + 1, start + 2, start, start + 2, start + 3])

    def _add_vertex(
        self,
        point: tuple[float, float, float],
        normal: tuple[float, float, float],
        texcoord: tuple[float, float] = (0.0, 0.0),
    ) -> int:
        self.positions.append(point)
        self.normals.append(normal)
        self.texcoords.append(texcoord)
        return len(self.positions) - 1

    def _local(self, longitude: float, latitude: float, z_m: float) -> tuple[float, float, float]:
        meters_per_degree_lat = 111_320.0
        meters_per_degree_lon = meters_per_degree_lat * math.cos(math.radians(self.request.center_latitude))
        east = (longitude - self.request.center_longitude) * meters_per_degree_lon
        north = (latitude - self.request.center_latitude) * meters_per_degree_lat
        return (east, north, z_m)

    def to_glb(self, terrain_texture_uri: str | None = None, facade_texture_uri: str | None = None) -> bytes:
        position_bytes = b"".join(struct.pack("<3f", *value) for value in self.positions)
        normal_bytes = b"".join(struct.pack("<3f", *value) for value in self.normals)
        texcoord_bytes = b"".join(struct.pack("<2f", *value) for value in self.texcoords)
        index_component_type = 5125 if len(self.positions) > 65_535 else 5123
        index_pack = "<I" if index_component_type == 5125 else "<H"
        index_byte_chunks = {
            material_index: b"".join(struct.pack(index_pack, value) for value in indices)
            for material_index, indices in self.primitive_indices.items()
            if indices
        }
        binary = _pad4(position_bytes) + _pad4(normal_bytes) + _pad4(texcoord_bytes)
        position_offset = 0
        normal_offset = len(_pad4(position_bytes))
        texcoord_offset = normal_offset + len(_pad4(normal_bytes))
        index_offsets: dict[int, int] = {}
        running_offset = texcoord_offset + len(_pad4(texcoord_bytes))
        for material_index, index_bytes in index_byte_chunks.items():
            index_offsets[material_index] = running_offset
            binary += _pad4(index_bytes)
            running_offset += len(_pad4(index_bytes))
        mins = [min(position[axis] for position in self.positions) for axis in range(3)]
        maxs = [max(position[axis] for position in self.positions) for axis in range(3)]
        buffer_views = [
            {"buffer": 0, "byteOffset": position_offset, "byteLength": len(position_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": normal_offset, "byteLength": len(normal_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": texcoord_offset, "byteLength": len(texcoord_bytes), "target": 34962},
        ]
        accessors = [
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
                "componentType": 5126,
                "count": len(self.texcoords),
                "type": "VEC2",
            },
        ]
        primitives = []
        for material_index, index_bytes in index_byte_chunks.items():
            buffer_view_index = len(buffer_views)
            accessor_index = len(accessors)
            buffer_views.append(
                {
                    "buffer": 0,
                    "byteOffset": index_offsets[material_index],
                    "byteLength": len(index_bytes),
                    "target": 34963,
                }
            )
            accessors.append(
                {
                    "bufferView": buffer_view_index,
                    "componentType": index_component_type,
                    "count": len(self.primitive_indices[material_index]),
                    "type": "SCALAR",
                }
            )
            primitives.append(
                {
                    "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                    "indices": accessor_index,
                    "mode": 4,
                    "material": material_index,
                }
            )
        terrain_texture_index = 0 if terrain_texture_uri else None
        facade_texture_index = (1 if terrain_texture_uri else 0) if facade_texture_uri else None
        gltf = {
            "asset": {"version": "2.0", "generator": "earth-replica-open-tile-worker"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": primitives}],
            "materials": _gltf_materials(terrain_texture_index, facade_texture_index),
            "buffers": [{"byteLength": len(binary)}],
            "bufferViews": buffer_views,
            "accessors": accessors,
        }
        if terrain_texture_uri or facade_texture_uri:
            gltf["extensionsUsed"] = ["KHR_materials_unlit"]
            gltf["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}]
            images = []
            textures = []
            if terrain_texture_uri:
                images.append({"uri": terrain_texture_uri})
                textures.append({"source": 0, "sampler": 0})
            if facade_texture_uri:
                images.append({"uri": facade_texture_uri})
                textures.append({"source": len(images) - 1, "sampler": 0})
            gltf["images"] = images
            gltf["textures"] = textures
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


def _terrain_uv(bounds: TerrainBounds, longitude: float, latitude: float) -> tuple[float, float]:
    longitude_span = bounds.max_longitude - bounds.min_longitude
    latitude_span = bounds.max_latitude - bounds.min_latitude
    u = 0.0 if longitude_span == 0 else (longitude - bounds.min_longitude) / longitude_span
    v = 0.0 if latitude_span == 0 else (bounds.max_latitude - latitude) / latitude_span
    return (max(0.0, min(1.0, u)), max(0.0, min(1.0, v)))


def _gltf_materials(
    terrain_texture_index: int | None = None,
    facade_texture_index: int | None = None,
) -> list[dict[str, object]]:
    terrain_pbr: dict[str, object] = {
        "baseColorFactor": [0.46, 0.56, 0.36, 1.0],
        "roughnessFactor": 0.92,
    }
    if terrain_texture_index is not None:
        terrain_pbr = {
            "baseColorTexture": {"index": terrain_texture_index},
            "roughnessFactor": 0.95,
            "metallicFactor": 0.0,
        }
    facade_pbr: dict[str, object] = {
        "baseColorFactor": [0.64, 0.66, 0.62, 1.0],
        "roughnessFactor": 0.84,
    }
    if facade_texture_index is not None:
        facade_pbr = {
            "baseColorTexture": {"index": facade_texture_index},
            "roughnessFactor": 0.88,
            "metallicFactor": 0.0,
        }
    return [
        {
            "name": "measured terrain",
            "pbrMetallicRoughness": terrain_pbr,
            **({"extensions": {"KHR_materials_unlit": {}}} if terrain_texture_index is not None else {}),
        },
        {
            "name": "inferred building facades",
            "pbrMetallicRoughness": facade_pbr,
        },
        {
            "name": "observed roads",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.12, 0.13, 0.14, 1.0],
                "roughnessFactor": 0.86,
            },
        },
        {
            "name": "observed water",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.02, 0.08, 0.1, 0.64],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.12,
            },
            "alphaMode": "BLEND",
            "doubleSided": True,
        },
        {
            "name": "observed building roofs",
            "pbrMetallicRoughness": terrain_pbr,
            **({"extensions": {"KHR_materials_unlit": {}}} if terrain_texture_index is not None else {}),
        },
    ]


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
