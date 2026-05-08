"""Fetch a real ETOPO 2022 terrain subset from NOAA ERDDAP."""

from __future__ import annotations

import argparse
from pathlib import Path

from earth_replica.terrain import TerrainBounds, fetch_etopo_tile


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a NOAA ETOPO 2022 terrain tile.")
    parser.add_argument("--min-lat", type=float, default=37.7)
    parser.add_argument("--max-lat", type=float, default=37.8)
    parser.add_argument("--min-lon", type=float, default=-122.5)
    parser.add_argument("--max-lon", type=float, default=-122.4)
    parser.add_argument("--stride", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("artifacts/etopo_tile.json"))
    args = parser.parse_args()

    tile = fetch_etopo_tile(
        bounds=TerrainBounds(
            min_latitude=args.min_lat,
            max_latitude=args.max_lat,
            min_longitude=args.min_lon,
            max_longitude=args.max_lon,
        ),
        stride=args.stride,
    )
    tile.write_json(args.output)
    print(
        f"Wrote {len(tile.samples)} ETOPO samples to {args.output} "
        f"({tile.min_elevation_m:.1f}m to {tile.max_elevation_m:.1f}m)."
    )


if __name__ == "__main__":
    main()
