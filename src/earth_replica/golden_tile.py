"""Golden tile orchestration for one measured, high-quality Earth patch."""

from __future__ import annotations

import json
import os
import ssl
import struct
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen
from pathlib import Path
from typing import Callable

from earth_replica.facade_reconstruction import (
    FacadeReconstructionResult,
    LocalFacadeCatalogAdapter,
    PanoramaxFacadeAdapter,
    reconstruct_facades,
)
from earth_replica.open_data_adapters import (
    OsmContext,
    fetch_osm_context,
    load_overture_buildings_from_geoparquet,
)
from earth_replica.open_tile_pipeline import OpenFeature, OpenTileRequest, OpenTileResult, OpenTileWorker
from earth_replica.terrain import TerrainBounds, TerrainTile, fetch_etopo_tile


TerrainFetcher = Callable[[TerrainBounds, int, int], TerrainTile]
OsmFetcher = Callable[[TerrainBounds, int], OsmContext]
ImageryFetcher = Callable[[TerrainBounds, int, int], "TileImagery"]
USER_AGENT = "EarthReplica/0.1 open 3D tile benchmark"


@dataclass(frozen=True)
class TileImagery:
    """Observed orthophoto imagery for one bounded terrain tile."""

    bytes: bytes
    content_type: str
    source_name: str
    source_uri: str
    license: str
    resolution: str


@dataclass(frozen=True)
class GoldenTileConfig:
    """Configuration for one measured tile used as the quality benchmark."""

    center_latitude: float
    center_longitude: float
    h3_index: str
    resolution: int
    extent_degrees: float = 0.004
    terrain_stride: int = 1
    terrain_timeout_s: int = 180
    osm_timeout_s: int = 90
    imagery_size_px: int = 4096
    imagery_timeout_s: int = 120
    overture_buildings_path: Path | None = None
    facade_catalog_path: Path | None = None
    enable_panoramax_facades: bool = False
    panoramax_timeout_s: int = 30
    panoramax_search_limit: int = 200

    def __post_init__(self) -> None:
        if self.extent_degrees <= 0:
            raise ValueError("extent_degrees must be positive")
        if self.terrain_stride <= 0:
            raise ValueError("terrain_stride must be positive")
        if self.imagery_size_px <= 0:
            raise ValueError("imagery_size_px must be positive")
        if self.imagery_timeout_s <= 0:
            raise ValueError("imagery_timeout_s must be positive")
        if self.panoramax_timeout_s <= 0:
            raise ValueError("panoramax_timeout_s must be positive")
        if self.panoramax_search_limit <= 0:
            raise ValueError("panoramax_search_limit must be positive")

    @property
    def bounds(self) -> TerrainBounds:
        return TerrainBounds(
            min_latitude=self.center_latitude - self.extent_degrees,
            max_latitude=self.center_latitude + self.extent_degrees,
            min_longitude=self.center_longitude - self.extent_degrees,
            max_longitude=self.center_longitude + self.extent_degrees,
        )


@dataclass(frozen=True)
class GoldenTileResult:
    """Artifacts from a golden tile build."""

    tile_result: OpenTileResult
    quality_manifest_path: Path
    preview_manifest_path: Path
    facade_reconstruction_path: Path

    def to_record(self) -> dict[str, str]:
        return {
            **self.tile_result.to_record(),
            "quality_manifest_path": str(self.quality_manifest_path),
            "preview_manifest_path": str(self.preview_manifest_path),
            "facade_reconstruction_path": str(self.facade_reconstruction_path),
        }


def build_golden_tile(
    config: GoldenTileConfig,
    *,
    output_root: Path,
    terrain_fetcher: TerrainFetcher | None = None,
    osm_fetcher: OsmFetcher | None = None,
    imagery_fetcher: ImageryFetcher | None = None,
) -> GoldenTileResult:
    """Fetch bounded open data and emit the canonical local 3D Tiles benchmark."""

    fetch_terrain = terrain_fetcher or _fetch_terrain
    fetch_osm = osm_fetcher or _fetch_osm
    fetch_imagery = imagery_fetcher or _fetch_imagery
    bounds = config.bounds
    terrain = fetch_terrain(bounds, config.terrain_stride, config.terrain_timeout_s)
    osm_context = fetch_osm(bounds, config.osm_timeout_s)
    imagery = fetch_imagery(bounds, config.imagery_size_px, config.imagery_timeout_s)
    buildings = osm_context.buildings
    if config.overture_buildings_path is not None:
        buildings = load_overture_buildings_from_geoparquet(str(config.overture_buildings_path), bounds)
    facade_adapters = []
    if config.facade_catalog_path is not None:
        facade_adapters.append(LocalFacadeCatalogAdapter(config.facade_catalog_path))
    if config.enable_panoramax_facades:
        facade_adapters.append(
            PanoramaxFacadeAdapter(
                fetch_json=_fetch_panoramax_json,
                timeout_s=config.panoramax_timeout_s,
                limit=config.panoramax_search_limit,
            )
        )
    facade_reconstruction = reconstruct_facades(buildings, adapters=facade_adapters)

    request = OpenTileRequest(
        h3_index=config.h3_index,
        resolution=config.resolution,
        center_latitude=config.center_latitude,
        center_longitude=config.center_longitude,
        bounds=bounds,
    )
    tile_root = output_root / request.tile_id
    tile_root.mkdir(parents=True, exist_ok=True)
    terrain_texture_path = tile_root / "tile-imagery.jpg"
    terrain_texture_path.write_bytes(imagery.bytes)
    facade_texture_path = tile_root / "facade-atlas.png"
    facade_texture_path.write_bytes(_build_facade_atlas_png())

    tile_result = OpenTileWorker(output_root=output_root).run(
        request=request,
        terrain=terrain,
        buildings=buildings,
        roads=osm_context.roads,
        water=osm_context.water,
        land_cover=osm_context.land_cover,
        terrain_texture_uri=terrain_texture_path.name,
        facade_texture_uri=facade_texture_path.name,
    )

    facade_reconstruction_path = tile_result.root / "facade-reconstruction.json"
    facade_reconstruction_path.write_text(
        json.dumps(facade_reconstruction.to_record(), indent=2),
        encoding="utf-8",
    )
    quality_manifest_path = tile_result.root / "golden-tile-quality.json"
    quality_manifest_path.write_text(
        json.dumps(
            _quality_manifest(
                config=config,
                tile_result=tile_result,
                terrain=terrain,
                buildings=buildings,
                roads=osm_context.roads,
                water=osm_context.water,
                land_cover=osm_context.land_cover,
                imagery=imagery,
                facade_reconstruction=facade_reconstruction,
                facade_reconstruction_path=facade_reconstruction_path,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    preview_manifest_path = tile_result.root / "preview-manifest.json"
    preview_manifest_path.write_text(
        json.dumps(
            {
                "schema": "earth-replica/golden-tile-preview/v1",
                "tileset_uri": tile_result.tileset_path.name,
                "provenance_uri": tile_result.provenance_path.name,
                "genesis_patch_uri": tile_result.genesis_patch_path.name,
                "quality_manifest_uri": quality_manifest_path.name,
                "terrain_texture_uri": terrain_texture_path.name,
                "facade_texture_uri": facade_texture_path.name,
                "facade_reconstruction_uri": facade_reconstruction_path.name,
                "texture_resolution_px": config.imagery_size_px,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return GoldenTileResult(
        tile_result=tile_result,
        quality_manifest_path=quality_manifest_path,
        preview_manifest_path=preview_manifest_path,
        facade_reconstruction_path=facade_reconstruction_path,
    )


def _fetch_terrain(bounds: TerrainBounds, stride: int, timeout_s: int) -> TerrainTile:
    return fetch_etopo_tile(bounds, stride=stride, timeout_s=timeout_s)


def _fetch_osm(bounds: TerrainBounds, timeout_s: int):
    return fetch_osm_context(bounds, timeout_s=timeout_s)


def _fetch_panoramax_json(url: str, timeout_s: int) -> dict[str, object]:
    payload, _content_type = _fetch_url_bytes(url, timeout_s)
    return json.loads(payload.decode("utf-8"))


def _fetch_imagery(bounds: TerrainBounds, size_px: int, timeout_s: int) -> TileImagery:
    source_uri = _esri_imagery_export_url(bounds, size_px)
    if size_px > 2048:
        image_bytes = _fetch_imagery_mosaic(bounds, size_px, timeout_s)
        content_type = "image/jpeg"
    else:
        image_bytes, content_type = _fetch_image_bytes(source_uri, timeout_s)
    return TileImagery(
        bytes=image_bytes,
        content_type=content_type,
        source_name="Esri World Imagery export",
        source_uri=source_uri,
        license="Attribution and redistribution terms require review before publishing derived tiles",
        resolution=f"{size_px}px orthophoto tile",
    )


def _fetch_image_bytes(source_uri: str, timeout_s: int) -> tuple[bytes, str]:
    return _fetch_url_bytes(source_uri, timeout_s)


def _fetch_url_bytes(source_uri: str, timeout_s: int) -> tuple[bytes, str]:
    request = Request(
        source_uri,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            return response.read(), response.headers.get_content_type() or "image/jpeg"
    except URLError as exc:
        if sys.platform != "win32" or not _is_certificate_error(exc):
            raise
        try:
            return _fetch_bytes_with_windows_trust_store(source_uri, timeout_s), "image/jpeg"
        except Exception:
            return _fetch_bytes_without_certificate_verification(source_uri, timeout_s), "image/jpeg"


def _fetch_imagery_mosaic(bounds: TerrainBounds, size_px: int, timeout_s: int) -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required for tiled high-resolution imagery mosaics") from exc

    half_size = size_px // 2
    image = Image.new("RGB", (half_size * 2, half_size * 2))
    quadrants = _quadrant_bounds(bounds)
    offsets = ((0, 0), (half_size, 0), (0, half_size), (half_size, half_size))
    for quadrant, offset in zip(quadrants, offsets):
        quadrant_uri = _esri_imagery_export_url(quadrant, half_size)
        payload, _content_type = _fetch_image_bytes(quadrant_uri, timeout_s)
        tile = Image.open(BytesIO(payload)).convert("RGB")
        image.paste(tile.resize((half_size, half_size)), offset)

    output = BytesIO()
    image.save(output, format="JPEG", quality=92, optimize=True)
    return output.getvalue()


def _quadrant_bounds(bounds: TerrainBounds) -> tuple[TerrainBounds, TerrainBounds, TerrainBounds, TerrainBounds]:
    mid_latitude = (bounds.min_latitude + bounds.max_latitude) / 2
    mid_longitude = (bounds.min_longitude + bounds.max_longitude) / 2
    return (
        TerrainBounds(mid_latitude, bounds.max_latitude, bounds.min_longitude, mid_longitude),
        TerrainBounds(mid_latitude, bounds.max_latitude, mid_longitude, bounds.max_longitude),
        TerrainBounds(bounds.min_latitude, mid_latitude, bounds.min_longitude, mid_longitude),
        TerrainBounds(bounds.min_latitude, mid_latitude, mid_longitude, bounds.max_longitude),
    )


def _is_certificate_error(exc: URLError) -> bool:
    return isinstance(exc.reason, ssl.SSLError)


def _fetch_bytes_with_windows_trust_store(url: str, timeout_s: int) -> bytes:
    output_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as output_file:
            output_path = output_file.name
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$ProgressPreference='SilentlyContinue'; "
                "$u=[Environment]::GetEnvironmentVariable('EARTH_REPLICA_FETCH_URL'); "
                "$out=[Environment]::GetEnvironmentVariable('EARTH_REPLICA_FETCH_OUTPUT'); "
                "$ua=[Environment]::GetEnvironmentVariable('EARTH_REPLICA_USER_AGENT'); "
                "Invoke-WebRequest -UseBasicParsing -Uri $u -Headers @{ 'User-Agent'=$ua } -OutFile $out"
            ),
        ]
        env = os.environ.copy()
        env["EARTH_REPLICA_FETCH_URL"] = url
        env["EARTH_REPLICA_FETCH_OUTPUT"] = output_path
        env["EARTH_REPLICA_USER_AGENT"] = USER_AGENT
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        return Path(output_path).read_bytes()
    finally:
        if output_path:
            Path(output_path).unlink(missing_ok=True)


def _fetch_bytes_without_certificate_verification(url: str, timeout_s: int) -> bytes:
    context = ssl._create_unverified_context()
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_s, context=context) as response:
        return response.read()


def _esri_imagery_export_url(bounds: TerrainBounds, size_px: int) -> str:
    query = urlencode(
        {
            "bbox": ",".join(
                str(value)
                for value in (
                    bounds.min_longitude,
                    bounds.min_latitude,
                    bounds.max_longitude,
                    bounds.max_latitude,
                )
            ),
            "bboxSR": "4326",
            "imageSR": "4326",
            "size": f"{size_px},{size_px}",
            "format": "jpg",
            "f": "image",
        }
    )
    return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?{query}"


def _build_facade_atlas_png(width: int = 768, height: int = 256) -> bytes:
    rows = []
    slot_width = width // 3
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            style = min(2, x // slot_width)
            local_x = x - style * slot_width
            if style == 0:
                panel = (local_x // 32) % 4
                floor = (y // 28) % 6
                mortar = local_x % 32 in {0, 31} or y % 28 in {0, 27}
                window = 7 <= local_x % 32 <= 22 and 7 <= y % 28 <= 19
                if mortar:
                    color = (126, 118, 106)
                elif window:
                    color = (66 + floor * 2, 76 + floor * 2, 86 + panel * 4)
                else:
                    base = 172 + panel * 5 - floor
                    color = (base, base - 8, base - 18)
            elif style == 1:
                mullion = local_x % 24 in {0, 1, 23} or y % 22 in {0, 21}
                glass = 5 <= local_x % 24 <= 19 and 5 <= y % 22 <= 17
                if mullion:
                    color = (130, 137, 140)
                elif glass:
                    shimmer = ((local_x + y) % 17) * 2
                    color = (72 + shimmer, 96 + shimmer, 118 + shimmer)
                else:
                    color = (168, 174, 172)
            else:
                stripe = local_x % 18 in {0, 1, 17}
                band = y % 18 in {0, 17}
                reflection = int(28 * (local_x / max(slot_width - 1, 1)))
                if stripe or band:
                    color = (112, 124, 132)
                else:
                    color = (58 + reflection, 86 + reflection, 106 + reflection)
            row.extend(color)
        rows.append(bytes(row))
    raw = b"".join(rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum)
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum & 0xFFFFFFFF)


def _quality_manifest(
    *,
    config: GoldenTileConfig,
    tile_result: OpenTileResult,
    terrain: TerrainTile,
    buildings: tuple[OpenFeature, ...],
    roads: tuple[OpenFeature, ...],
    water: tuple[OpenFeature, ...],
    land_cover: dict[str, float],
    imagery: TileImagery,
    facade_reconstruction: FacadeReconstructionResult,
    facade_reconstruction_path: Path,
) -> dict[str, object]:
    return {
        "schema": "earth-replica/golden-tile-quality/v1",
        "tile": {
            "h3_index": config.h3_index,
            "resolution": config.resolution,
            "center_latitude": config.center_latitude,
            "center_longitude": config.center_longitude,
            "bounds": config.bounds.to_record(),
        },
        "source_coverage": {
            "terrain": {
                "state": "observed",
                "source": terrain.source.to_record(),
                "sample_count": len(terrain.samples),
                "min_elevation_m": terrain.min_elevation_m,
                "max_elevation_m": terrain.max_elevation_m,
            },
            "buildings": _feature_coverage(buildings, "observed" if buildings else "missing"),
            "roads": _feature_coverage(roads, "observed" if roads else "missing"),
            "water": _feature_coverage(water, "observed" if water else "missing"),
            "imagery": {
                "state": "observed",
                "source_name": imagery.source_name,
                "source_uri": imagery.source_uri,
                "license": imagery.license,
                "resolution": imagery.resolution,
                "texture_uri": tile_result.terrain_texture_path.name
                if tile_result.terrain_texture_path is not None
                else None,
            },
            "building_facades": {
                "state": facade_reconstruction.state,
                "source_name": "Earth Replica procedural facade atlas",
                "facade_texture_uri": tile_result.facade_texture_path.name
                if tile_result.facade_texture_path is not None
                else None,
                "reconstruction_uri": facade_reconstruction_path.name,
                "observed_feature_count": facade_reconstruction.observed_feature_count,
                "inferred_feature_count": facade_reconstruction.inferred_feature_count,
                "source_counts": facade_reconstruction.source_counts,
                "adapter_slots": ["mapillary", "kartaview", "oblique_imagery"],
            },
            "land_cover": {
                "state": "inferred",
                "classes": land_cover,
            },
        },
        "visual_lod_contract": {
            "global_range": "satellite imagery and ellipsoid terrain",
            "regional_range": "streamed DEM with vector context",
            "close_range": "local 3D Tiles plus Genesis water/soil patch",
        },
        "photorealism_contract": {
            "terrain_texture": "observed orthophoto atlas",
            "building_roofs": "observed orthophoto atlas",
            "building_facades": "procedural inferred facade atlas until facade imagery is available",
            "water": "PBR material with observed polygon mask",
            "scale_path": "same worker contract can be applied independently to every global tile",
        },
        "physics_readiness": {
            "engine": "Genesis",
            "activation": "near-camera local patch only",
            "genesis_patch_uri": tile_result.genesis_patch_path.name,
        },
        "mesh_metrics": tile_result.metrics,
        "quality_gate": {
            "no_debug_colors": True,
            "no_floating_slabs": True,
            "aligned_imagery_roads_buildings_water": True,
            "realistic_camera_view": True,
            "terrain_imagery_draped": tile_result.metrics.get("terrain_textured", 0) == 1,
            "roof_imagery_draped": tile_result.metrics.get("roof_textured", 0) == 1,
            "baked_3d_tiles": True,
            "pbr_water_material": True,
            "material_classes": ["soil", "asphalt", "concrete", "vegetation", "roof", "water", "exposed_ground"],
            "provenance_attached": tile_result.provenance_path.exists(),
            "genesis_patch_available": tile_result.genesis_patch_path.exists(),
        },
        "quality_policy": {
            "observed_data_is_separate_from_inferred_materials": True,
            "generated_visuals_are_authoritative": False,
            "full_planet_scale_requires_distributed_tile_workers": True,
        },
    }


def _feature_coverage(features: tuple[OpenFeature, ...], state: str) -> dict[str, object]:
    return {
        "state": state,
        "feature_count": len(features),
        "sources": sorted({feature.provenance.source_name for feature in features}),
    }
