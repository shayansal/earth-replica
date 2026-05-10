"""Build one local open-data 3D Tiles shard for the preview pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from earth_replica.open_data_adapters import (
    fetch_osm_features,
    load_overture_buildings_from_geoparquet,
)
from earth_replica.open_tile_pipeline import (
    OpenFeature,
    OpenTileRequest,
    OpenTileWorker,
    ProvenanceRecord,
)
from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile, fetch_etopo_tile


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local open 3D Tiles shard.")
    parser.add_argument("--lat", type=float, default=37.7749, help="Tile center latitude.")
    parser.add_argument("--lon", type=float, default=-122.4194, help="Tile center longitude.")
    parser.add_argument("--h3", default="872830828ffffff", help="H3 index for the tile.")
    parser.add_argument("--resolution", type=int, default=7, help="H3 resolution.")
    parser.add_argument("--extent-degrees", type=float, default=0.01, help="Half tile extent in degrees.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/open-tiles"), help="Output root.")
    parser.add_argument("--fetch-dem", action="store_true", help="Fetch ETOPO DEM samples for this tile.")
    parser.add_argument("--fetch-osm", action="store_true", help="Fetch bounded OSM features through Overpass.")
    parser.add_argument("--overture-buildings", type=Path, default=None, help="Optional local Overture buildings GeoParquet file.")
    parser.add_argument("--terrain-stride", type=int, default=1, help="ETOPO stride for --fetch-dem.")
    args = parser.parse_args()

    bounds = TerrainBounds(
        min_latitude=args.lat - args.extent_degrees,
        max_latitude=args.lat + args.extent_degrees,
        min_longitude=args.lon - args.extent_degrees,
        max_longitude=args.lon + args.extent_degrees,
    )
    if args.fetch_dem:
        terrain = fetch_etopo_tile(bounds, stride=args.terrain_stride, timeout_s=180)
    else:
        terrain = TerrainTile(
            bounds=bounds,
            stride=1,
            samples=(
                TerrainSample(bounds.min_latitude, bounds.min_longitude, 2.0),
                TerrainSample(bounds.min_latitude, bounds.max_longitude, 4.0),
                TerrainSample(bounds.max_latitude, bounds.min_longitude, 7.0),
                TerrainSample(bounds.max_latitude, bounds.max_longitude, 11.0),
            ),
        )
    fixture_building = OpenFeature(
        feature_id="demo-building",
        layer="buildings",
        geometry=(
            (args.lon - 0.0012, args.lat - 0.0008),
            (args.lon + 0.0012, args.lat - 0.0008),
            (args.lon + 0.0012, args.lat + 0.0008),
            (args.lon - 0.0012, args.lat + 0.0008),
        ),
        height_m=24.0,
        provenance=ProvenanceRecord(
            source_id="demo:overture-building",
            source_name="Overture Maps Buildings adapter placeholder",
            domain="buildings",
            state="observed",
            license="CDLA Permissive 2.0",
            resolution="feature footprint",
        ),
    )
    fixture_road = OpenFeature(
        feature_id="demo-road",
        layer="roads",
        geometry=((args.lon - 0.004, args.lat - 0.003), (args.lon + 0.004, args.lat + 0.003)),
        width_m=12.0,
        provenance=ProvenanceRecord(
            source_id="demo:osm-way",
            source_name="OpenStreetMap adapter placeholder",
            domain="roads",
            state="observed",
            license="ODbL",
            resolution="mapped way",
        ),
    )

    roads = (fixture_road,)
    water = ()
    land_cover = {"urban": 0.7, "vegetation": 0.22, "water": 0.08}
    if args.fetch_osm:
        roads, water, land_cover = fetch_osm_features(bounds)

    buildings = (fixture_building,)
    if args.overture_buildings is not None:
        buildings = load_overture_buildings_from_geoparquet(str(args.overture_buildings), bounds)

    result = OpenTileWorker(output_root=args.output).run(
        request=OpenTileRequest(
            h3_index=args.h3,
            resolution=args.resolution,
            center_latitude=args.lat,
            center_longitude=args.lon,
            bounds=bounds,
        ),
        terrain=terrain,
        buildings=buildings,
        roads=roads,
        water=water,
        land_cover=land_cover,
    )
    print(f"Wrote tileset to {result.tileset_path}")
    print(f"Wrote Genesis patch to {result.genesis_patch_path}")
    print(f"Mesh metrics: {result.metrics}")


if __name__ == "__main__":
    main()
