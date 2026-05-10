"""Source acquisition catalog for whole-planet replica data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REQUIRED_SOURCE_FAMILIES = {
    "base_map",
    "buildings",
    "transportation",
    "terrain",
    "bathymetry",
    "land_cover",
    "imagery",
}


@dataclass(frozen=True)
class SourceAcquisition:
    """One global data source required for Earth Replica ingestion."""

    name: str
    family: str
    source_uri: str
    access_method: str
    license: str
    scope: str
    provenance_state: str
    ingestion_mode: str
    local_default: str = "metadata_only"
    expected_scale: str = "planetary"

    def __post_init__(self) -> None:
        if self.family not in REQUIRED_SOURCE_FAMILIES:
            raise ValueError(f"unsupported source family: {self.family}")
        if self.scope not in {"whole_planet", "global_index", "baseline_global"}:
            raise ValueError("scope must describe a global source")
        if self.provenance_state not in {"observed", "inferred", "simulated", "rendered"}:
            raise ValueError("invalid provenance_state")

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "family": self.family,
            "source_uri": self.source_uri,
            "access_method": self.access_method,
            "license": self.license,
            "scope": self.scope,
            "provenance_state": self.provenance_state,
            "ingestion_mode": self.ingestion_mode,
            "local_default": self.local_default,
            "expected_scale": self.expected_scale,
        }


@dataclass(frozen=True)
class SourceAcquisitionCatalog:
    """The global source catalog needed before planet-scale ingestion."""

    sources: tuple[SourceAcquisition, ...]

    def __post_init__(self) -> None:
        families = {source.family for source in self.sources}
        missing = REQUIRED_SOURCE_FAMILIES - families
        if missing:
            raise ValueError(f"missing required source family: {sorted(missing)[0]}")

    def to_record(self, *, allow_full_planet_downloads: bool = False) -> dict[str, object]:
        return {
            "schema": "earth-replica/source-acquisition-catalog/v1",
            "sources": [source.to_record() for source in self.sources],
            "execution": {
                "allow_full_planet_downloads": allow_full_planet_downloads,
                "local_execution": (
                    "bounded samples and metadata manifests only unless "
                    "allow_full_planet_downloads is true"
                ),
                "requires": [
                    "object storage",
                    "distributed worker pool",
                    "checkpoint database",
                    "dataset license review",
                ],
            },
            "safety": {
                "full_planet_download_requires_explicit_flag": True,
                "local_default": "metadata_and_bounded_samples_only",
                "reason": "whole-planet source datasets are too large and license-sensitive for accidental local download",
            },
            "provenance_policy": {
                "observed_sources_stay_separate_from_inferred_layers": True,
                "generated_visuals_are_authoritative": False,
            },
        }

    def write_fetch_plan(self, path: Path, *, allow_full_planet_downloads: bool = False) -> Path:
        if not allow_full_planet_downloads:
            raise PermissionError(
                "full planet downloads require allow_full_planet_downloads=True"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                self.to_record(allow_full_planet_downloads=allow_full_planet_downloads),
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def write_metadata_plan(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_record(allow_full_planet_downloads=False), indent=2),
            encoding="utf-8",
        )
        return path


def build_replica_source_catalog() -> SourceAcquisitionCatalog:
    return SourceAcquisitionCatalog(
        sources=(
            SourceAcquisition(
                name="OSM planet PBF",
                family="base_map",
                source_uri="https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf",
                access_method="bulk planet PBF or regional extract mirror",
                license="ODbL",
                scope="whole_planet",
                provenance_state="observed",
                ingestion_mode="pbf_to_h3_features",
                local_default="regional_extract_or_bounded_overpass_sample",
            ),
            SourceAcquisition(
                name="Overture Maps Buildings",
                family="buildings",
                source_uri="s3://overturemaps-us-west-2/release/latest/theme=buildings/",
                access_method="partitioned GeoParquet scan",
                license="CDLA Permissive 2.0",
                scope="whole_planet",
                provenance_state="observed",
                ingestion_mode="geoparquet_to_h3_building_meshes",
                local_default="local GeoParquet subset",
            ),
            SourceAcquisition(
                name="Overture Maps Transportation",
                family="transportation",
                source_uri="s3://overturemaps-us-west-2/release/latest/theme=transportation/",
                access_method="partitioned GeoParquet scan",
                license="CDLA Permissive 2.0",
                scope="whole_planet",
                provenance_state="observed",
                ingestion_mode="geoparquet_to_h3_roads",
                local_default="local GeoParquet subset",
            ),
            SourceAcquisition(
                name="NOAA ETOPO 2022",
                family="terrain",
                source_uri="https://www.ncei.noaa.gov/products/etopo-global-relief-model",
                access_method="global grid download or ERDDAP windows",
                license="public domain",
                scope="whole_planet",
                provenance_state="observed",
                ingestion_mode="dem_grid_to_h3_terrain",
                local_default="bounded ERDDAP window",
            ),
            SourceAcquisition(
                name="GEBCO global bathymetry",
                family="bathymetry",
                source_uri="https://www.gebco.net/data-products-gridded-bathymetry-data/",
                access_method="global bathymetry grid download",
                license="GEBCO terms",
                scope="whole_planet",
                provenance_state="observed",
                ingestion_mode="bathymetry_grid_to_h3_water_depth",
                local_default="metadata_only",
            ),
            SourceAcquisition(
                name="Copernicus global land cover",
                family="land_cover",
                source_uri="https://land.copernicus.eu/en/products/global-dynamic-land-cover",
                access_method="global land-cover raster products",
                license="Copernicus terms",
                scope="whole_planet",
                provenance_state="observed",
                ingestion_mode="raster_classes_to_material_map",
                local_default="metadata_only",
            ),
            SourceAcquisition(
                name="Sentinel-2 global imagery index",
                family="imagery",
                source_uri="https://registry.opendata.aws/sentinel-2/",
                access_method="cloud object storage scene index",
                license="Copernicus Sentinel data terms",
                scope="global_index",
                provenance_state="observed",
                ingestion_mode="scene_index_to_texture_jobs",
                local_default="metadata_only",
            ),
            SourceAcquisition(
                name="NASA Blue Marble baseline imagery",
                family="imagery",
                source_uri="https://visibleearth.nasa.gov/collection/1484/blue-marble",
                access_method="baseline imagery download",
                license="NASA imagery terms",
                scope="baseline_global",
                provenance_state="observed",
                ingestion_mode="baseline_texture_fallback",
                local_default="metadata_only",
            ),
        )
    )
