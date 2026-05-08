"""Run one exascale-shaped water/soil shard on the local machine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth_replica.genesis_worker import GenesisWaterSoilWorker
from earth_replica.runtime import ArtifactStore, LocalShardScheduler, ShardJob, ShardSpec


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Earth Replica simulation shard.")
    parser.add_argument("--h3", default="872830828ffffff", help="H3 cell index for the shard.")
    parser.add_argument("--resolution", type=int, default=7, help="H3 resolution.")
    parser.add_argument("--extent-m", type=float, default=80.0, help="Local shard extent in meters.")
    parser.add_argument("--steps", type=int, default=12, help="Simulation steps to run.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/shards"),
        help="Directory where shard artifacts are written.",
    )
    parser.add_argument(
        "--skip-genesis",
        action="store_true",
        help="Write deterministic browser frames without stepping Genesis.",
    )
    args = parser.parse_args()

    job = ShardJob(
        spec=ShardSpec(
            h3_index=args.h3,
            resolution=args.resolution,
            extent_m=args.extent_m,
        ),
        steps=args.steps,
    )
    scheduler = LocalShardScheduler(
        worker=GenesisWaterSoilWorker(enable_genesis=not args.skip_genesis),
        store=ArtifactStore(args.output_dir),
        node_id="local-dev-node",
    )
    result = scheduler.run(job)

    print(json.dumps(result.to_record(), indent=2))
    physics_artifacts = [artifact for artifact in result.artifacts if artifact.kind == "genesis-frames"]
    if physics_artifacts:
        print(f"Physics frames: {physics_artifacts[0].path}")


if __name__ == "__main__":
    main()
