from earth_replica.terrain import (
    TerrainBounds,
    TerrainSample,
    TerrainTile,
    build_etopo_erddap_url,
    parse_etopo_csvp,
)


def test_build_etopo_url_requests_subset_with_stride():
    bounds = TerrainBounds(
        min_latitude=37.7,
        max_latitude=37.8,
        min_longitude=-122.5,
        max_longitude=-122.4,
    )

    url = build_etopo_erddap_url(bounds=bounds, stride=10)

    assert url.startswith(
        "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ETOPO_2022_v1_15s.csvp?"
    )
    assert "z%5B%2837.7%29%3A10%3A%2837.8%29%5D" in url
    assert "%5B%28-122.5%29%3A10%3A%28-122.4%29%5D" in url


def test_parse_etopo_csvp_builds_meter_based_tile():
    csvp = "\n".join(
        [
            "latitude (degrees_north),longitude (degrees_east),z",
            "37.702083333333334,-122.49791666666667,55.77853",
            "37.702083333333334,-122.45625,179.21123",
            "37.74375,-122.49791666666667,-12.5",
        ]
    )

    tile = parse_etopo_csvp(csvp)

    assert tile.source.name == "NOAA ETOPO 2022 Global Relief Model"
    assert tile.bounds.min_latitude == 37.702083333333334
    assert tile.bounds.max_longitude == -122.45625
    assert len(tile.samples) == 3
    assert tile.min_elevation_m == -12.5
    assert tile.max_elevation_m == 179.21123
    assert tile.samples[0].elevation_m == 55.77853


def test_terrain_tile_exports_json_record():
    tile = TerrainTile(
        bounds=TerrainBounds(0.0, 1.0, 10.0, 11.0),
        stride=10,
        samples=(
            TerrainSample(latitude=0.0, longitude=10.0, elevation_m=-5.0),
            TerrainSample(latitude=0.0, longitude=11.0, elevation_m=3.0),
            TerrainSample(latitude=1.0, longitude=10.0, elevation_m=7.0),
            TerrainSample(latitude=1.0, longitude=11.0, elevation_m=20.0),
        ),
    )

    record = tile.to_record()

    assert record["bounds"]["min_latitude"] == 0.0
    assert record["min_elevation_m"] == -5.0
    assert record["max_elevation_m"] == 20.0
    assert record["grid"]["latitude_count"] == 2
    assert record["grid"]["longitude_count"] == 2
    assert record["grid"]["elevation_rows_m"] == [[-5.0, 3.0], [7.0, 20.0]]
    assert record["samples"][3]["elevation_m"] == 20.0
    assert record["source"]["confidence"] == "integrated source grid"


def test_terrain_tile_rejects_samples_that_do_not_form_grid():
    tile = TerrainTile(
        bounds=TerrainBounds(0.0, 1.0, 10.0, 11.0),
        stride=10,
        samples=(
            TerrainSample(latitude=0.0, longitude=10.0, elevation_m=-5.0),
            TerrainSample(latitude=1.0, longitude=11.0, elevation_m=20.0),
        ),
    )

    try:
        tile.grid_record()
    except ValueError as exc:
        assert "complete latitude/longitude grid" in str(exc)
    else:
        raise AssertionError("Expected incomplete terrain grid to raise")
