import json
import ssl
import struct
from urllib.error import URLError

import earth_replica.golden_tile as golden_tile
from earth_replica.golden_tile import GoldenTileConfig, TileImagery, build_golden_tile
from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile


def test_golden_tile_pipeline_fetches_measured_sources_and_writes_quality_manifest(tmp_path):
    calls = {"terrain": 0, "osm": 0, "imagery": 0}

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

    def fake_fetch_imagery(bounds: TerrainBounds, size_px: int, timeout_s: int) -> TileImagery:
        calls["imagery"] += 1
        assert size_px == 1024
        assert timeout_s == 120
        assert bounds.min_latitude < bounds.max_latitude
        return TileImagery(
            bytes=b"fake-jpeg-bytes",
            content_type="image/jpeg",
            source_name="Test orthophoto",
            source_uri="https://example.test/imagery",
            license="test imagery license",
            resolution="1024px test tile",
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
        imagery_fetcher=fake_fetch_imagery,
    )

    assert calls == {"terrain": 1, "osm": 1, "imagery": 1}
    assert result.tile_result.tileset_path.exists()
    assert result.tile_result.terrain_texture_path is not None
    assert result.tile_result.terrain_texture_path.exists()
    assert result.tile_result.terrain_texture_path.read_bytes() == b"fake-jpeg-bytes"
    assert result.quality_manifest_path.exists()
    assert result.preview_manifest_path.exists()

    quality = json.loads(result.quality_manifest_path.read_text(encoding="utf-8"))
    assert quality["schema"] == "earth-replica/golden-tile-quality/v1"
    assert quality["tile"]["center_latitude"] == 37.7749
    assert quality["source_coverage"]["terrain"]["state"] == "observed"
    assert quality["source_coverage"]["buildings"]["feature_count"] == 1
    assert quality["source_coverage"]["roads"]["feature_count"] == 1
    assert quality["source_coverage"]["water"]["feature_count"] == 1
    assert quality["source_coverage"]["imagery"]["state"] == "observed"
    assert quality["source_coverage"]["imagery"]["source_name"] == "Test orthophoto"
    assert quality["quality_gate"]["no_debug_colors"] is True
    assert quality["quality_gate"]["terrain_imagery_draped"] is True
    assert quality["quality_gate"]["baked_3d_tiles"] is True
    assert quality["physics_readiness"]["genesis_patch_uri"].endswith("genesis-terrain-patch.json")
    assert quality["visual_lod_contract"]["close_range"] == "local 3D Tiles plus Genesis water/soil patch"

    preview = json.loads(result.preview_manifest_path.read_text(encoding="utf-8"))
    assert preview["tileset_uri"].endswith("tileset.json")
    assert preview["provenance_uri"].endswith("provenance.json")
    assert preview["quality_manifest_uri"].endswith("golden-tile-quality.json")
    assert preview["terrain_texture_uri"].endswith("tile-imagery.jpg")


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
        terrain_texture_uri="tile-imagery.jpg",
    )

    gltf = _read_glb_json(result.glb_path.read_bytes())
    primitive_materials = {primitive["material"] for primitive in gltf["meshes"][0]["primitives"]}
    material_names = {material["name"] for material in gltf["materials"]}
    terrain_primitive = gltf["meshes"][0]["primitives"][0]
    terrain_material = gltf["materials"][terrain_primitive["material"]]

    assert primitive_materials == {0, 1, 2, 3}
    assert material_names >= {"measured terrain", "observed buildings", "observed roads", "observed water"}
    assert terrain_primitive["attributes"]["TEXCOORD_0"] == 2
    assert terrain_material["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 0
    assert terrain_material["extensions"]["KHR_materials_unlit"] == {}
    assert "KHR_materials_unlit" in gltf["extensionsUsed"]
    assert gltf["images"][0]["uri"] == "tile-imagery.jpg"
    assert gltf["textures"][0]["source"] == 0
    assert result.metrics["material_primitives"] == 4
    assert result.metrics["terrain_textured"] == 1


def test_fetch_imagery_falls_back_to_windows_trust_store_for_certificate_errors(monkeypatch):
    bounds = TerrainBounds(37.77, 37.78, -122.43, -122.41)

    def raise_certificate_error(*_args, **_kwargs):
        raise URLError(ssl.SSLError("certificate verify failed"))

    monkeypatch.setattr(golden_tile.sys, "platform", "win32")
    monkeypatch.setattr(golden_tile, "urlopen", raise_certificate_error)
    monkeypatch.setattr(
        golden_tile,
        "_fetch_bytes_with_windows_trust_store",
        lambda url, timeout_s: b"fallback-jpeg",
    )

    imagery = golden_tile._fetch_imagery(bounds, 512, 30)

    assert imagery.bytes == b"fallback-jpeg"
    assert imagery.content_type == "image/jpeg"
    assert "World_Imagery" in imagery.source_uri


def _read_glb_json(glb: bytes) -> dict:
    magic, version, _length = struct.unpack_from("<4sII", glb, 0)
    assert magic == b"glTF"
    assert version == 2
    json_length, chunk_type = struct.unpack_from("<I4s", glb, 12)
    assert chunk_type == b"JSON"
    return json.loads(glb[20 : 20 + json_length].decode("utf-8"))
