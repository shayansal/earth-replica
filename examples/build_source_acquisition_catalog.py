"""Write the source catalog needed for whole-planet Earth Replica ingestion."""

from __future__ import annotations

import argparse
from pathlib import Path

from earth_replica.source_acquisition import build_replica_source_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the global source acquisition catalog.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/source-acquisition-catalog.json"),
        help="Output catalog path.",
    )
    parser.add_argument(
        "--allow-full-planet-downloads",
        action="store_true",
        help="Write a fetch plan that explicitly allows full-planet bulk downloads.",
    )
    args = parser.parse_args()

    catalog = build_replica_source_catalog()
    if args.allow_full_planet_downloads:
        path = catalog.write_fetch_plan(args.output, allow_full_planet_downloads=True)
    else:
        path = catalog.write_metadata_plan(args.output)
    print(f"Wrote source acquisition catalog to {path}")


if __name__ == "__main__":
    main()
