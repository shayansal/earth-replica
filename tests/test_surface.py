from earth_replica.surface import (
    KNOWN_SURFACE_SAMPLES,
    SurfaceSample,
    SurfaceSource,
    SurfaceType,
)


def test_surface_sample_represents_elevation_and_bathymetry_in_meters():
    everest = SurfaceSample(
        name="Mount Everest",
        latitude=27.9881,
        longitude=86.9250,
        elevation_m=8848.86,
        surface_type=SurfaceType.LAND,
        source=SurfaceSource(
            name="National Geographic Information Centre of Nepal and Chinese authorities",
            url="https://en.wikipedia.org/wiki/Mount_Everest",
            vertical_datum="mean sea level",
            resolution="surveyed summit height",
            confidence="measured",
        ),
    )
    challenger = SurfaceSample(
        name="Challenger Deep",
        latitude=11.3693,
        longitude=142.5873,
        elevation_m=-10984.0,
        surface_type=SurfaceType.WATER,
        source=SurfaceSource(
            name="GEBCO",
            url="https://www.gebco.net/",
            vertical_datum="mean sea level",
            resolution="bathymetric sounding synthesis",
            confidence="measured",
        ),
    )

    assert everest.is_above_sea_level is True
    assert challenger.is_below_sea_level is True
    assert challenger.depth_m == 10984.0


def test_known_surface_samples_include_extreme_land_and_ocean_points():
    samples = {sample.name: sample for sample in KNOWN_SURFACE_SAMPLES}

    assert samples["Mount Everest"].elevation_m > 8800
    assert samples["Challenger Deep"].elevation_m < -10900
    assert samples["Dead Sea shore"].surface_type == SurfaceType.LAND


def test_surface_sample_exports_json_serializable_record():
    record = KNOWN_SURFACE_SAMPLES[0].to_record()

    assert set(record) == {
        "name",
        "latitude",
        "longitude",
        "elevation_m",
        "depth_m",
        "surface_type",
        "source",
    }
    assert "confidence" in record["source"]
