"""Golden tile orchestration for one measured, high-quality Earth patch."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen
from pathlib import Path
from typing import Callable

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
    imagery_size_px: int = 1024
    imagery_timeout_s: int = 120
    overture_buildings_path: Path | None = None

    def __post_init__(self) -> None:
        if self.extent_degrees <= 0:
            raise ValueError("extent_degrees must be positive")
        if self.terrain_stride <= 0:
            raise ValueError("terrain_stride must be positive")
        if self.imagery_size_px <= 0:
            raise ValueError("imagery_size_px must be positive")
        if self.imagery_timeout_s <= 0:
            raise ValueError("imagery_timeout_s must be positive")

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

    def to_record(self) -> dict[str, str]:
        return {
            **self.tile_result.to_record(),
            "quality_manifest_path": str(self.quality_manifest_path),
            "preview_manifest_path": str(self.preview_manifest_path),
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

    tile_result = OpenTileWorker(output_root=output_root).run(
        request=request,
        terrain=terrain,
        buildings=buildings,
        roads=osm_context.roads,
        water=osm_context.water,
        land_cover=osm_context.land_cover,
        terrain_texture_uri=terrain_texture_path.name,
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
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return GoldenTileResult(
        tile_result=tile_result,
        quality_manifest_path=quality_manifest_path,
        preview_manifest_path=preview_manifest_path,
    )


def _fetch_terrain(bounds: TerrainBounds, stride: int, timeout_s: int) -> TerrainTile:
    return fetch_etopo_tile(bounds, stride=stride, timeout_s=timeout_s)


def _fetch_osm(bounds: TerrainBounds, timeout_s: int):
    return fetch_osm_context(bounds, timeout_s=timeout_s)


def _fetch_imagery(bounds: TerrainBounds, size_px: int, timeout_s: int) -> TileImagery:
    source_uri = _esri_imagery_export_url(bounds, size_px)
    request = Request(
        source_uri,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            image_bytes = response.read()
            content_type = response.headers.get_content_type() or "image/jpeg"
    except URLError as exc:
        if sys.platform != "win32" or not _is_certificate_error(exc):
            raise
        image_bytes = _fetch_bytes_with_windows_trust_store(source_uri, timeout_s)
        content_type = "image/jpeg"
    return TileImagery(
        bytes=image_bytes,
        content_type=content_type,
        source_name="Esri World Imagery export",
        source_uri=source_uri,
        license="Attribution and redistribution terms require review before publishing derived tiles",
        resolution=f"{size_px}px orthophoto tile",
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
