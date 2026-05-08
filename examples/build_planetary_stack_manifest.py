"""Write a local manifest for the exascale-ready Earth Replica stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth_replica.planetary_stack import (
    AccessPolicy,
    CoupledSolverPlan,
    DatasetSource,
    DistributedExecutionPlan,
    PlanetaryDataFabric,
    TileStreamManifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Earth Replica stack manifest.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/planetary-stack-manifest.json"),
    )
    args = parser.parse_args()

    fabric = PlanetaryDataFabric()
    fabric.register(
        DatasetSource(
            name="NOAA ETOPO 2022",
            domain="terrain",
            uri="https://www.ncei.noaa.gov/products/etopo-global-relief-model",
            resolution="15 arc-second",
            license="public domain / NOAA terms",
            update_cadence="static release",
        )
    )
    fabric.register(
        DatasetSource(
            name="GEBCO global bathymetry",
            domain="bathymetry",
            uri="https://www.gebco.net/",
            resolution="15 arc-second",
            license="GEBCO terms",
            update_cadence="annual release",
        )
    )

    manifest = {
        "schema": "earth-replica/planetary-stack-manifest/v1",
        "data_fabric": fabric.catalog_record(),
        "solver_plan": CoupledSolverPlan.local_default().to_record(),
        "execution_plan": DistributedExecutionPlan.local_exascale_shape(
            max_active_shards=1
        ).to_record(),
        "streaming": TileStreamManifest(
            root_uri="artifacts/streams",
            lod_levels=(0, 1, 2, 3),
            visible_layers=("terrain", "water", "soil", "atmosphere"),
            time_window_s=30.0,
        ).to_record(),
        "governance": AccessPolicy.public_open_source_default().to_record(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote planetary stack manifest to {args.output}")


if __name__ == "__main__":
    main()
