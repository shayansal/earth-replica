"""Golden tile orchestration for one measured, high-quality Earth patch."""

from __future__ import annotations

import json
from dataclasses import dataclass
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
    overture_buildings_path: Path | None = None

    def __post_init__(self) -> None:
        if self.extent_degrees <= 0:
            raise ValueError("extent_degrees must be positive")
        if self.terrain_stride <= 0:
            raise ValueError("terrain_stride must be positive")

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
) -> GoldenTileResult:
    """Fetch bounded open data and emit the canonical local 3D Tiles benchmark."""

    fetch_terrain = terrain_fetcher or _fetch_terrain
    fetch_osm = osm_fetcher or _fetch_osm
    bounds = config.bounds
    terrain = fetch_terrain(bounds, config.terrain_stride, config.terrain_timeout_s)
    osm_context = fetch_osm(bounds, config.osm_timeout_s)
    buildings = osm_context.buildings
    if config.overture_buildings_path is not None:
        buildings = load_overture_buildings_from_geoparquet(str(config.overture_buildings_path), bounds)

    tile_result = OpenTileWorker(output_root=output_root).run(
        request=OpenTileRequest(
            h3_index=config.h3_index,
            resolution=config.resolution,
            center_latitude=config.center_latitude,
            center_longitude=config.center_longitude,
            bounds=bounds,
        ),
        terrain=terrain,
        buildings=buildings,
        roads=osm_context.roads,
        water=osm_context.water,
        land_cover=osm_context.land_cover,
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


def _quality_manifest(
    *,
    config: GoldenTileConfig,
    tile_result: OpenTileResult,
    terrain: TerrainTile,
    buildings: tuple[OpenFeature, ...],
    roads: tuple[OpenFeature, ...],
    water: tuple[OpenFeature, ...],
    land_cover: dict[str, float],
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
