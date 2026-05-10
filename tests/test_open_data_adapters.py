import json

from earth_replica.open_data_adapters import (
    build_overpass_query,
    features_from_osm_overpass,
    features_from_overture_records,
    fetch_osm_features,
)
from earth_replica.terrain import TerrainBounds


def test_build_overpass_query_requests_roads_water_parks_and_landuse():
    query = build_overpass_query(TerrainBounds(37.7, 37.8, -122.5, -122.4))

    assert "[out:json]" in query
    assert 'way["highway"]' in query
    assert 'way["natural"="water"]' in query
    assert 'way["natural"="coastline"]' in query
    assert 'way["leisure"="park"]' in query
    assert 'way["landuse"]' in query
    assert "out geom" in query


def test_features_from_osm_overpass_converts_open_features():
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 10,
                "tags": {"highway": "primary", "name": "Market Street"},
                "geometry": [
                    {"lon": -122.42, "lat": 37.77},
                    {"lon": -122.41, "lat": 37.78},
                ],
            },
            {
                "type": "way",
                "id": 20,
                "tags": {"natural": "water"},
                "geometry": [
                    {"lon": -122.43, "lat": 37.77},
                    {"lon": -122.42, "lat": 37.77},
                    {"lon": -122.42, "lat": 37.78},
                ],
            },
            {
                "type": "way",
                "id": 30,
                "tags": {"leisure": "park"},
                "geometry": [
                    {"lon": -122.44, "lat": 37.77},
                    {"lon": -122.43, "lat": 37.77},
                    {"lon": -122.43, "lat": 37.78},
                ],
            },
        ],
    }

    roads, water, land_cover = features_from_osm_overpass(payload)

    assert len(roads) == 1
    assert roads[0].feature_id == "osm:way:10"
    assert roads[0].layer == "roads"
    assert roads[0].width_m > 0
    assert roads[0].provenance.source_name == "OpenStreetMap"
    assert len(water) == 1
    assert water[0].layer == "water"
    assert land_cover["urban"] > 0
    assert land_cover["water"] > 0
    assert land_cover["vegetation"] > 0


def test_fetch_osm_features_uses_injected_fetcher():
    def fake_fetch(url: str, data: bytes, timeout_s: int) -> str:
        assert "overpass" in url
        assert b'way["highway"]' in data
        assert timeout_s == 15
        return json.dumps({"elements": []})

    roads, water, land_cover = fetch_osm_features(
        TerrainBounds(37.7, 37.8, -122.5, -122.4),
        timeout_s=15,
        fetcher=fake_fetch,
    )

    assert roads == ()
    assert water == ()
    assert land_cover["urban"] == 0.0


def test_features_from_overture_records_extracts_building_height_and_wkb():
    # Little-endian WKB polygon: square around (-122.42, 37.77)
    geometry_wkb_hex = (
        "01030000000100000005000000"
        "b81e85eb519a5ec0295c8fc2f5e34240"
        "48e17a14ae995ec0295c8fc2f5e34240"
        "48e17a14ae995ec0c3f5285c8fe34240"
        "b81e85eb519a5ec0c3f5285c8fe34240"
        "b81e85eb519a5ec0295c8fc2f5e34240"
    )
    records = [
        {
            "id": "building-123",
            "height": 21.5,
            "geometry": bytes.fromhex(geometry_wkb_hex),
        }
    ]

    buildings = features_from_overture_records(
        records,
        TerrainBounds(37.7, 37.8, -122.5, -122.4),
    )

    assert len(buildings) == 1
    assert buildings[0].feature_id == "overture:building-123"
    assert buildings[0].height_m == 21.5
    assert buildings[0].layer == "buildings"
    assert buildings[0].provenance.source_name == "Overture Maps Buildings"
