import json

from earth_replica.open_tile_pipeline import (
    OpenFeature,
    OpenTileRequest,
    OpenTileWorker,
    ProvenanceRecord,
)
from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile


def test_open_tile_worker_emits_3d_tiles_manifest_and_genesis_patch(tmp_path):
    request = OpenTileRequest(
        h3_index="872830828ffffff",
        resolution=7,
        center_latitude=37.7749,
        center_longitude=-122.4194,
        bounds=TerrainBounds(37.77, 37.78, -122.43, -122.41),
    )
    terrain = TerrainTile(
        bounds=request.bounds,
        stride=1,
        samples=(
            TerrainSample(37.77, -122.43, 3.0),
            TerrainSample(37.77, -122.41, 6.0),
            TerrainSample(37.78, -122.43, 7.0),
            TerrainSample(37.78, -122.41, 12.0),
        ),
    )
    building = OpenFeature(
        feature_id="building-1",
        layer="buildings",
        geometry=(
            (-122.421, 37.774),
            (-122.420, 37.774),
            (-122.420, 37.775),
            (-122.421, 37.775),
        ),
        height_m=18.0,
        provenance=ProvenanceRecord(
            source_id="overture:building-1",
            source_name="Overture Maps Buildings",
            domain="buildings",
            state="observed",
            license="CDLA Permissive 2.0",
            resolution="feature footprint",
        ),
    )
    road = OpenFeature(
        feature_id="road-1",
        layer="roads",
        geometry=((-122.425, 37.773), (-122.416, 37.777)),
        width_m=14.0,
        provenance=ProvenanceRecord(
            source_id="osm:way:1",
            source_name="OpenStreetMap",
            domain="roads",
            state="observed",
            license="ODbL",
            resolution="mapped way",
        ),
    )

    result = OpenTileWorker(output_root=tmp_path).run(
        request=request,
        terrain=terrain,
        buildings=(building,),
        roads=(road,),
        land_cover={"urban": 0.72, "vegetation": 0.2, "water": 0.08},
    )

    assert result.tileset_path.exists()
    assert result.glb_path.exists()
    assert result.provenance_path.exists()
    assert result.genesis_patch_path.exists()

    tileset = json.loads(result.tileset_path.read_text(encoding="utf-8"))
    assert tileset["asset"]["version"] == "1.1"
    assert tileset["root"]["content"]["uri"] == "tile.glb"
    assert tileset["root"]["boundingVolume"]["region"][0] < tileset["root"]["boundingVolume"]["region"][2]

    provenance = json.loads(result.provenance_path.read_text(encoding="utf-8"))
    assert provenance["schema"] == "earth-replica/open-tile-provenance/v1"
    assert {entry["state"] for entry in provenance["records"]} >= {"observed", "inferred", "simulated", "rendered"}
    assert provenance["quality_policy"]["generated_visuals_are_authoritative"] is False

    patch = json.loads(result.genesis_patch_path.read_text(encoding="utf-8"))
    assert patch["schema"] == "earth-replica/genesis-terrain-patch/v1"
    assert patch["anchor"]["latitude"] == 37.7749
    assert patch["anchor"]["longitude"] == -122.4194
    assert patch["terrain"]["min_elevation_m"] == 3.0
    assert patch["materials"]["land_cover"]["urban"] == 0.72


def test_open_tile_request_rejects_out_of_bounds_center():
    try:
        OpenTileRequest(
            h3_index="872830828ffffff",
            resolution=7,
            center_latitude=95.0,
            center_longitude=0.0,
            bounds=TerrainBounds(-1.0, 1.0, -1.0, 1.0),
        )
    except ValueError as error:
        assert "center_latitude" in str(error)
    else:
        raise AssertionError("OpenTileRequest accepted invalid latitude")
