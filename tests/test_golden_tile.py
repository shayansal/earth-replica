import json
import struct

from earth_replica.golden_tile import GoldenTileConfig, build_golden_tile
from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile


def test_golden_tile_pipeline_fetches_measured_sources_and_writes_quality_manifest(tmp_path):
    calls = {"terrain": 0, "osm": 0}

    def fake_fetch_terrain(bounds: TerrainBounds, stride: int, timeout_s: int) -> TerrainTile:
        calls["terrain"] += 1
        assert stride == 3
        assert timeout_s == 180
        return TerrainTile(
            bounds=bounds,
            stride=stride,
            samples=(
                TerrainSample(bounds.min_latitude, bounds.min_longitude, -3.0),
                TerrainSample(bounds.min_latitude, bounds.max_longitude, 2.0),
                TerrainSample(bounds.max_latitude, bounds.min_longitude, 5.0),
                TerrainSample(bounds.max_latitude, bounds.max_longitude, 14.0),
            ),
        )

    def fake_fetch_osm(bounds: TerrainBounds, timeout_s: int):
        calls["osm"] += 1
        assert timeout_s == 90
        from earth_replica.open_data_adapters import OsmContext
        from earth_replica.open_tile_pipeline import OpenFeature, ProvenanceRecord

        building = OpenFeature(
            feature_id="osm:building:1",
            layer="buildings",
            geometry=(
                (bounds.min_longitude, bounds.min_latitude),
                (bounds.max_longitude, bounds.min_latitude),
                (bounds.max_longitude, bounds.max_latitude),
                (bounds.min_longitude, bounds.max_latitude),
            ),
            height_m=12.0,
            provenance=ProvenanceRecord(
                source_id="osm:building:1",
                source_name="OpenStreetMap",
                domain="buildings",
                state="observed",
                license="ODbL",
                resolution="mapped footprint",
            ),
        )
        road = OpenFeature(
            feature_id="osm:way:road-1",
            layer="roads",
            geometry=((bounds.min_longitude, bounds.min_latitude), (bounds.max_longitude, bounds.max_latitude)),
            width_m=11.0,
            provenance=ProvenanceRecord(
                source_id="osm:way:road-1",
                source_name="OpenStreetMap",
                domain="roads",
                state="observed",
                license="ODbL",
                resolution="mapped way",
            ),
        )
        water = OpenFeature(
            feature_id="osm:way:water-1",
            layer="water",
            geometry=(
                (bounds.min_longitude, bounds.min_latitude),
                (bounds.max_longitude, bounds.min_latitude),
                (bounds.max_longitude, bounds.max_latitude),
                (bounds.min_longitude, bounds.max_latitude),
            ),
            provenance=ProvenanceRecord(
                source_id="osm:way:water-1",
                source_name="OpenStreetMap",
                domain="water",
                state="observed",
                license="ODbL",
                resolution="mapped polygon",
            ),
        )
        return OsmContext(
            buildings=(building,),
            roads=(road,),
            water=(water,),
            land_cover={"urban": 0.4, "vegetation": 0.2, "water": 0.4},
        )

    result = build_golden_tile(
        GoldenTileConfig(
            center_latitude=37.7749,
            center_longitude=-122.4194,
            h3_index="872830828ffffff",
            resolution=7,
            extent_degrees=0.002,
            terrain_stride=3,
        ),
        output_root=tmp_path,
        terrain_fetcher=fake_fetch_terrain,
        osm_fetcher=fake_fetch_osm,
    )

    assert calls == {"terrain": 1, "osm": 1}
    assert result.tile_result.tileset_path.exists()
    assert result.quality_manifest_path.exists()
    assert result.preview_manifest_path.exists()

    quality = json.loads(result.quality_manifest_path.read_text(encoding="utf-8"))
    assert quality["schema"] == "earth-replica/golden-tile-quality/v1"
    assert quality["tile"]["center_latitude"] == 37.7749
    assert quality["source_coverage"]["terrain"]["state"] == "observed"
    assert quality["source_coverage"]["buildings"]["feature_count"] == 1
    assert quality["source_coverage"]["roads"]["feature_count"] == 1
    assert quality["source_coverage"]["water"]["feature_count"] == 1
    assert quality["physics_readiness"]["genesis_patch_uri"].endswith("genesis-terrain-patch.json")
    assert quality["visual_lod_contract"]["close_range"] == "local 3D Tiles plus Genesis water/soil patch"

    preview = json.loads(result.preview_manifest_path.read_text(encoding="utf-8"))
    assert preview["tileset_uri"].endswith("tileset.json")
    assert preview["provenance_uri"].endswith("provenance.json")
    assert preview["quality_manifest_uri"].endswith("golden-tile-quality.json")


def test_open_tile_glb_uses_distinct_material_primitives_for_physical_layers(tmp_path):
    from earth_replica.open_tile_pipeline import OpenFeature, OpenTileRequest, OpenTileWorker, ProvenanceRecord

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
            TerrainSample(37.77, -122.43, 1.0),
            TerrainSample(37.77, -122.41, 3.0),
            TerrainSample(37.78, -122.43, 4.0),
            TerrainSample(37.78, -122.41, 8.0),
        ),
    )
    provenance = ProvenanceRecord(
        source_id="source:1",
        source_name="test",
        domain="test",
        state="observed",
        license="test",
        resolution="fixture",
    )
    building = OpenFeature(
        feature_id="building-1",
        layer="buildings",
        geometry=((-122.422, 37.772), (-122.421, 37.772), (-122.421, 37.773), (-122.422, 37.773)),
        height_m=16.0,
        provenance=provenance,
    )
    road = OpenFeature(
        feature_id="road-1",
        layer="roads",
        geometry=((-122.425, 37.771), (-122.416, 37.777)),
        width_m=10.0,
        provenance=provenance,
    )
    water = OpenFeature(
        feature_id="water-1",
        layer="water",
        geometry=((-122.43, 37.77), (-122.41, 37.77), (-122.41, 37.771), (-122.43, 37.771)),
        provenance=provenance,
    )

    result = OpenTileWorker(output_root=tmp_path).run(
        request=request,
        terrain=terrain,
        buildings=(building,),
        roads=(road,),
        water=(water,),
        land_cover={"urban": 0.6, "vegetation": 0.2, "water": 0.2},
    )

    gltf = _read_glb_json(result.glb_path.read_bytes())
    primitive_materials = {primitive["material"] for primitive in gltf["meshes"][0]["primitives"]}
    material_names = {material["name"] for material in gltf["materials"]}

    assert primitive_materials == {0, 1, 2, 3}
    assert material_names >= {"measured terrain", "observed buildings", "observed roads", "observed water"}
    assert result.metrics["material_primitives"] == 4


def _read_glb_json(glb: bytes) -> dict:
    magic, version, _length = struct.unpack_from("<4sII", glb, 0)
    assert magic == b"glTF"
    assert version == 2
    json_length, chunk_type = struct.unpack_from("<I4s", glb, 12)
    assert chunk_type == b"JSON"
    return json.loads(glb[20 : 20 + json_length].decode("utf-8"))
