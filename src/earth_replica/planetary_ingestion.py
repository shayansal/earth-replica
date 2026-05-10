"""Whole-planet ingestion manifests for open Earth data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IngestionDataset:
    """One dataset that participates in global ingestion."""

    name: str
    domain: str
    source_uri: str
    scope: str
    license: str
    ingestion_mode: str
    partitioning: str = "spatial"
    provenance_state: str = "observed"

    def __post_init__(self) -> None:
        if self.scope not in {"whole_planet", "regional"}:
            raise ValueError("dataset scope must be whole_planet or regional")
        if self.provenance_state not in {"observed", "inferred", "simulated", "rendered"}:
            raise ValueError("provenance_state must be observed, inferred, simulated, or rendered")

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "domain": self.domain,
            "source_uri": self.source_uri,
            "scope": self.scope,
            "license": self.license,
            "ingestion_mode": self.ingestion_mode,
            "partitioning": self.partitioning,
            "provenance_state": self.provenance_state,
        }


@dataclass(frozen=True)
class PlanetaryIngestionPlan:
    """A resumable global ingestion plan, not a claim that ingestion is complete."""

    h3_resolution: int
    datasets: tuple[IngestionDataset, ...]
    worker_backend: str = "local-dry-run"

    def __post_init__(self) -> None:
        if not 0 <= self.h3_resolution <= 15:
            raise ValueError("h3_resolution must be between 0 and 15")
        if not self.datasets:
            raise ValueError("datasets must not be empty")

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "earth-replica/whole-planet-ingestion-plan/v1",
            "planetary_scope": {
                "coverage": "whole_planet",
                "execution_note": (
                    "This manifest defines global ingestion jobs. Local execution "
                    "must run bounded shards or attach a worker pool/object store."
                ),
            },
            "tiling": {
                "index": "H3",
                "resolution": self.h3_resolution,
                "activation": "progressive shard queue",
            },
            "datasets": [dataset.to_record() for dataset in self.datasets],
            "execution": {
                "backend": self.worker_backend,
                "mode": "manifest_only_until_worker_pool_configured",
                "checkpointing": True,
                "resume_by_dataset_and_tile": True,
                "requires_object_storage_for_full_planet": True,
            },
            "outputs": {
                "per_tile": [
                    "tileset.json",
                    "tile.glb",
                    "provenance.json",
                    "genesis-terrain-patch.json",
                ],
                "planetary": [
                    "dataset-catalog.json",
                    "tile-index.json",
                    "ingestion-checkpoints.json",
                ],
            },
            "provenance_policy": {
                "separate_observed_inferred_simulated_rendered": True,
                "generated_visuals_are_authoritative": False,
                "license_review_required": True,
            },
        }

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_record(), indent=2), encoding="utf-8")
        return path


def build_whole_planet_ingestion_plan(h3_resolution: int = 7) -> PlanetaryIngestionPlan:
    return PlanetaryIngestionPlan(
        h3_resolution=h3_resolution,
        datasets=(
            IngestionDataset(
                name="OSM planet PBF",
                domain="roads_water_landuse",
                source_uri="https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf",
                scope="whole_planet",
                license="ODbL",
                ingestion_mode="planet_pbf_or_regional_extract",
                partitioning="clip to H3 cells from planet PBF",
            ),
            IngestionDataset(
                name="Overture Maps Buildings",
                domain="buildings",
                source_uri="s3://overturemaps-us-west-2/release/latest/theme=buildings/",
                scope="whole_planet",
                license="CDLA Permissive 2.0",
                ingestion_mode="partitioned_geoparquet_scan",
                partitioning="spatial parquet partitions clipped to H3 cells",
            ),
            IngestionDataset(
                name="Overture Maps Transportation",
                domain="roads",
                source_uri="s3://overturemaps-us-west-2/release/latest/theme=transportation/",
                scope="whole_planet",
                license="CDLA Permissive 2.0",
                ingestion_mode="partitioned_geoparquet_scan",
                partitioning="spatial parquet partitions clipped to H3 cells",
            ),
            IngestionDataset(
                name="NOAA ETOPO 2022",
                domain="terrain",
                source_uri="https://www.ncei.noaa.gov/products/etopo-global-relief-model",
                scope="whole_planet",
                license="public domain",
                ingestion_mode="global_grid_windowing",
                partitioning="DEM windows by H3 cell bounds",
            ),
            IngestionDataset(
                name="GEBCO global bathymetry",
                domain="bathymetry",
                source_uri="https://www.gebco.net/data-products-gridded-bathymetry-data/",
                scope="whole_planet",
                license="GEBCO terms",
                ingestion_mode="global_grid_windowing",
                partitioning="bathymetry windows by H3 cell bounds",
            ),
        ),
    )
