"""Write the whole-planet open data ingestion manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from earth_replica.planetary_ingestion import build_whole_planet_ingestion_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the whole-planet ingestion manifest.")
    parser.add_argument("--h3-resolution", type=int, default=7, help="H3 resolution for global tile jobs.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/whole-planet-ingestion-manifest.json"),
        help="Output manifest path.",
    )
    args = parser.parse_args()

    path = build_whole_planet_ingestion_plan(args.h3_resolution).write_json(args.output)
    print(f"Wrote whole-planet ingestion manifest to {path}")


if __name__ == "__main__":
    main()
