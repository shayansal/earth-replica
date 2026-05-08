from earth_replica.earth import EARTH_SCALE


def test_earth_scale_uses_real_planet_dimensions():
    assert EARTH_SCALE.mean_radius_m == 6_371_008.8
    assert EARTH_SCALE.equatorial_radius_m == 6_378_137.0
    assert EARTH_SCALE.polar_radius_m == 6_356_752.314245
    assert round(EARTH_SCALE.mean_circumference_m, 1) == 40_030_228.9


def test_earth_scale_exports_json_serializable_metadata():
    record = EARTH_SCALE.to_record()

    assert record["name"] == "Earth"
    assert record["mean_radius_m"] == 6_371_008.8
    assert record["coordinate_system"] == "WGS84 latitude/longitude plus local ENU meters"
