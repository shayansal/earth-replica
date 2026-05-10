"""Build the measured benchmark tile used to raise visual and physics fidelity."""

from __future__ import annotations

import argparse
from pathlib import Path

from earth_replica.golden_tile import GoldenTileConfig, build_golden_tile


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one measured golden 3D Tiles patch.")
    parser.add_argument("--lat", type=float, default=37.7955, help="Tile center latitude.")
    parser.add_argument("--lon", type=float, default=-122.3937, help="Tile center longitude.")
    parser.add_argument("--h3", default="872830828ffffff", help="H3 index for the tile.")
    parser.add_argument("--resolution", type=int, default=7, help="H3 resolution.")
    parser.add_argument("--extent-degrees", type=float, default=0.004, help="Half tile extent in degrees.")
    parser.add_argument("--terrain-stride", type=int, default=1, help="ETOPO grid stride.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/golden-tiles"), help="Output root.")
    parser.add_argument(
        "--overture-buildings",
        type=Path,
        default=None,
        help="Optional local Overture Buildings GeoParquet file for preferred building footprints.",
    )
    parser.add_argument(
        "--facade-catalog",
        type=Path,
        default=None,
        help="Optional local JSON facade candidate catalog keyed by building feature id.",
    )
    args = parser.parse_args()

    result = build_golden_tile(
        GoldenTileConfig(
            center_latitude=args.lat,
            center_longitude=args.lon,
            h3_index=args.h3,
            resolution=args.resolution,
            extent_degrees=args.extent_degrees,
            terrain_stride=args.terrain_stride,
            overture_buildings_path=args.overture_buildings,
            facade_catalog_path=args.facade_catalog,
        ),
        output_root=args.output,
    )
    print(f"Wrote tileset to {result.tile_result.tileset_path}")
    if result.tile_result.terrain_texture_path is not None:
        print(f"Wrote terrain imagery to {result.tile_result.terrain_texture_path}")
    if result.tile_result.facade_texture_path is not None:
        print(f"Wrote facade atlas to {result.tile_result.facade_texture_path}")
    print(f"Wrote facade reconstruction manifest to {result.facade_reconstruction_path}")
    print(f"Wrote quality manifest to {result.quality_manifest_path}")
    print(f"Wrote preview manifest to {result.preview_manifest_path}")
    print(f"Mesh metrics: {result.tile_result.metrics}")


if __name__ == "__main__":
    main()
