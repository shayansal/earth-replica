import json
import ssl
import struct
from io import BytesIO
from urllib.error import URLError

import earth_replica.golden_tile as golden_tile
from earth_replica.golden_tile import GoldenTileConfig, TileImagery, build_golden_tile
from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile


def test_local_facade_catalog_assigns_observed_candidates_and_inferred_fallback(tmp_path):
    from earth_replica.facade_reconstruction import LocalFacadeCatalogAdapter, reconstruct_facades
    from earth_replica.open_tile_pipeline import OpenFeature, ProvenanceRecord

    provenance = ProvenanceRecord(
        source_id="source:buildings",
        source_name="OpenStreetMap",
        domain="buildings",
        state="observed",
        license="ODbL",
        resolution="mapped footprint",
    )
    observed_building = OpenFeature(
        feature_id="building-observed",
        layer="buildings",
        geometry=((-122.422, 37.772), (-122.421, 37.772), (-122.421, 37.773), (-122.422, 37.773)),
        height_m=26.0,
        provenance=provenance,
    )
    inferred_building = OpenFeature(
        feature_id="building-inferred",
        layer="buildings",
        geometry=((-122.424, 37.772), (-122.423, 37.772), (-122.423, 37.773), (-122.424, 37.773)),
        height_m=8.0,
        provenance=provenance,
    )
    catalog_path = tmp_path / "facades.json"
    catalog_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "building_id": "building-observed",
                        "source_name": "Street-level imagery catalog",
                        "source_uri": "https://example.test/facade-weak.jpg",
                        "texture_uri": "facades/building-observed-weak.jpg",
                        "license": "catalog test license",
                        "confidence": 0.61,
                        "captured_at": "2026-01-02",
                    },
                    {
                        "building_id": "building-observed",
                        "source_name": "Street-level imagery catalog",
                        "source_uri": "https://example.test/facade-strong.jpg",
                        "texture_uri": "facades/building-observed-strong.jpg",
                        "license": "catalog test license",
                        "confidence": 0.91,
                        "captured_at": "2026-01-03",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = reconstruct_facades(
        (observed_building, inferred_building),
        adapters=(LocalFacadeCatalogAdapter(catalog_path),),
    )
    record = result.to_record()

    assert record["observed_feature_count"] == 1
    assert record["inferred_feature_count"] == 1
    assert record["assignments"][0]["building_id"] == "building-observed"
    assert record["assignments"][0]["state"] == "observed"
    assert record["assignments"][0]["source_uri"].endswith("facade-strong.jpg")
    assert record["assignments"][0]["confidence"] == 0.91
    assert record["assignments"][1]["building_id"] == "building-inferred"
    assert record["assignments"][1]["state"] == "inferred"
    assert record["assignments"][1]["style"] == "low_rise"
    assert record["source_counts"] == {"Street-level imagery catalog": 1}


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
                ((bounds.min_longitude + bounds.max_longitude) / 2, bounds.min_latitude),
                ((bounds.min_longitude + bounds.max_longitude) / 2, (bounds.min_latitude + bounds.max_latitude) / 2),
                (bounds.min_longitude, (bounds.min_latitude + bounds.max_latitude) / 2),
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
        assert size_px == 4096
        assert timeout_s == 120
        assert bounds.min_latitude < bounds.max_latitude
        return TileImagery(
            bytes=b"fake-jpeg-bytes",
            content_type="image/jpeg",
            source_name="Test orthophoto",
            source_uri="https://example.test/imagery",
            license="test imagery license",
            resolution="4096px test tile",
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
    assert result.tile_result.facade_texture_path is not None
    assert result.tile_result.facade_texture_path.exists()
    assert result.tile_result.facade_texture_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
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
    assert quality["source_coverage"]["imagery"]["resolution"] == "4096px test tile"
    assert quality["source_coverage"]["building_facades"]["state"] == "inferred"
    assert quality["source_coverage"]["building_facades"]["observed_feature_count"] == 0
    assert quality["source_coverage"]["building_facades"]["facade_texture_uri"] == "facade-atlas.png"
    assert quality["source_coverage"]["building_facades"]["reconstruction_uri"] == "facade-reconstruction.json"
    assert quality["source_coverage"]["building_facades"]["adapter_slots"] == ["mapillary", "kartaview", "oblique_imagery"]
    assert quality["photorealism_contract"]["terrain_texture"] == "observed orthophoto atlas"
    assert quality["photorealism_contract"]["building_roofs"] == "observed orthophoto atlas"
    assert quality["photorealism_contract"]["building_facades"] == "procedural inferred facade atlas until facade imagery is available"
    assert quality["quality_gate"]["no_debug_colors"] is True
    assert quality["quality_gate"]["terrain_imagery_draped"] is True
    assert quality["quality_gate"]["roof_imagery_draped"] is True
    assert quality["quality_gate"]["baked_3d_tiles"] is True
    assert quality["physics_readiness"]["genesis_patch_uri"].endswith("genesis-terrain-patch.json")
    assert quality["visual_lod_contract"]["close_range"] == "local 3D Tiles plus Genesis water/soil patch"

    preview = json.loads(result.preview_manifest_path.read_text(encoding="utf-8"))
    assert preview["tileset_uri"].endswith("tileset.json")
    assert preview["provenance_uri"].endswith("provenance.json")
    assert preview["quality_manifest_uri"].endswith("golden-tile-quality.json")
    assert preview["terrain_texture_uri"].endswith("tile-imagery.jpg")
    assert preview["facade_texture_uri"].endswith("facade-atlas.png")
    assert preview["facade_reconstruction_uri"].endswith("facade-reconstruction.json")
    assert preview["texture_resolution_px"] == 4096


def test_golden_tile_uses_local_facade_catalog_for_observed_facade_provenance(tmp_path):
    def fake_fetch_terrain(bounds: TerrainBounds, stride: int, timeout_s: int) -> TerrainTile:
        return TerrainTile(
            bounds=bounds,
            stride=stride,
            samples=(
                TerrainSample(bounds.min_latitude, bounds.min_longitude, 1.0),
                TerrainSample(bounds.min_latitude, bounds.max_longitude, 1.0),
                TerrainSample(bounds.max_latitude, bounds.min_longitude, 1.0),
                TerrainSample(bounds.max_latitude, bounds.max_longitude, 1.0),
            ),
        )

    def fake_fetch_osm(bounds: TerrainBounds, timeout_s: int):
        from earth_replica.open_data_adapters import OsmContext
        from earth_replica.open_tile_pipeline import OpenFeature, ProvenanceRecord

        provenance = ProvenanceRecord(
            source_id="osm:building:facade-test",
            source_name="OpenStreetMap",
            domain="buildings",
            state="observed",
            license="ODbL",
            resolution="mapped footprint",
        )
        building = OpenFeature(
            feature_id="osm:building:facade-test",
            layer="buildings",
            geometry=(
                (bounds.min_longitude, bounds.min_latitude),
                (bounds.max_longitude, bounds.min_latitude),
                (bounds.max_longitude, bounds.max_latitude),
                (bounds.min_longitude, bounds.max_latitude),
            ),
            height_m=40.0,
            provenance=provenance,
        )
        return OsmContext(buildings=(building,), roads=(), water=(), land_cover={"urban": 1.0})

    def fake_fetch_imagery(bounds: TerrainBounds, size_px: int, timeout_s: int) -> TileImagery:
        return TileImagery(
            bytes=b"fake-jpeg-bytes",
            content_type="image/jpeg",
            source_name="Test orthophoto",
            source_uri="https://example.test/imagery",
            license="test imagery license",
            resolution="4096px test tile",
        )

    catalog_path = tmp_path / "facades.json"
    catalog_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "building_id": "osm:building:facade-test",
                        "source_name": "Street-level imagery catalog",
                        "source_uri": "https://example.test/facade.jpg",
                        "texture_uri": "facades/osm-building-facade-test.jpg",
                        "license": "catalog test license",
                        "confidence": 0.82,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = build_golden_tile(
        GoldenTileConfig(
            center_latitude=37.7749,
            center_longitude=-122.4194,
            h3_index="872830828ffffff",
            resolution=7,
            extent_degrees=0.002,
            facade_catalog_path=catalog_path,
        ),
        output_root=tmp_path / "tiles",
        terrain_fetcher=fake_fetch_terrain,
        osm_fetcher=fake_fetch_osm,
        imagery_fetcher=fake_fetch_imagery,
    )

    quality = json.loads(result.quality_manifest_path.read_text(encoding="utf-8"))
    preview = json.loads(result.preview_manifest_path.read_text(encoding="utf-8"))
    facade_manifest = json.loads((result.tile_result.root / preview["facade_reconstruction_uri"]).read_text(encoding="utf-8"))

    assert quality["source_coverage"]["building_facades"]["state"] == "observed"
    assert quality["source_coverage"]["building_facades"]["observed_feature_count"] == 1
    assert quality["source_coverage"]["building_facades"]["inferred_feature_count"] == 0
    assert facade_manifest["assignments"][0]["state"] == "observed"
    assert facade_manifest["assignments"][0]["texture_uri"] == "facades/osm-building-facade-test.jpg"


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
        facade_texture_uri="facade-atlas.png",
    )

    gltf = _read_glb_json(result.glb_path.read_bytes())
    primitive_materials = {primitive["material"] for primitive in gltf["meshes"][0]["primitives"]}
    material_names = {material["name"] for material in gltf["materials"]}
    terrain_primitive = gltf["meshes"][0]["primitives"][0]
    terrain_material = gltf["materials"][terrain_primitive["material"]]
    roof_primitive = next(primitive for primitive in gltf["meshes"][0]["primitives"] if primitive["material"] == 4)
    roof_material = gltf["materials"][roof_primitive["material"]]
    facade_material = gltf["materials"][1]

    assert primitive_materials == {0, 1, 2, 3, 4}
    assert material_names >= {
        "measured terrain",
        "inferred low-rise facades",
        "observed roads",
        "observed water",
        "observed building roofs",
    }
    assert terrain_primitive["attributes"]["TEXCOORD_0"] == 2
    assert terrain_material["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 0
    assert terrain_material["extensions"]["KHR_materials_unlit"] == {}
    assert facade_material["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 1
    assert roof_primitive["attributes"]["TEXCOORD_0"] == 2
    assert roof_material["pbrMetallicRoughness"]["baseColorTexture"]["index"] == 0
    assert roof_material["extensions"]["KHR_materials_unlit"] == {}
    assert "KHR_materials_unlit" in gltf["extensionsUsed"]
    assert gltf["images"][0]["uri"] == "tile-imagery.jpg"
    assert gltf["images"][1]["uri"] == "facade-atlas.png"
    assert gltf["textures"][0]["source"] == 0
    assert gltf["textures"][1]["source"] == 1
    assert result.metrics["material_primitives"] == 5
    assert result.metrics["terrain_textured"] == 1
    assert result.metrics["roof_textured"] == 1
    assert result.metrics["facade_textured"] == 1
    assert result.metrics["facade_style_low_rise"] == 1


def test_open_tile_glb_preserves_full_building_footprint_for_roofs_and_facades(tmp_path):
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
        source_id="source:building",
        source_name="test",
        domain="buildings",
        state="observed",
        license="test",
        resolution="fixture",
    )
    pentagon = OpenFeature(
        feature_id="building-pentagon",
        layer="buildings",
        geometry=(
            (-122.4230, 37.7720),
            (-122.4216, 37.7721),
            (-122.4212, 37.7730),
            (-122.4220, 37.7738),
            (-122.4232, 37.7730),
        ),
        height_m=22.0,
        provenance=provenance,
    )

    result = OpenTileWorker(output_root=tmp_path).run(
        request=request,
        terrain=terrain,
        buildings=(pentagon,),
        terrain_texture_uri="tile-imagery.jpg",
        facade_texture_uri="facade-atlas.png",
    )

    gltf = _read_glb_json(result.glb_path.read_bytes())
    primitives = gltf["meshes"][0]["primitives"]
    roof = next(primitive for primitive in primitives if primitive["material"] == 4)
    facade = next(primitive for primitive in primitives if primitive["material"] in {1, 5, 6})

    assert gltf["accessors"][roof["indices"]]["count"] == 15
    assert gltf["accessors"][facade["indices"]]["count"] == 30
    assert result.metrics["building_roof_triangles"] == 5
    assert result.metrics["building_wall_quads"] == 5


def test_open_tile_worker_skips_building_extrusions_centered_in_water(tmp_path):
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
        source_id="source:water-test",
        source_name="test",
        domain="test",
        state="observed",
        license="test",
        resolution="fixture",
    )
    building = OpenFeature(
        feature_id="building-in-water",
        layer="buildings",
        geometry=((-122.424, 37.772), (-122.422, 37.772), (-122.422, 37.774), (-122.424, 37.774)),
        height_m=18.0,
        provenance=provenance,
    )
    water = OpenFeature(
        feature_id="water-covering-building",
        layer="water",
        geometry=((-122.425, 37.771), (-122.421, 37.771), (-122.421, 37.775), (-122.425, 37.775)),
        provenance=provenance,
    )

    result = OpenTileWorker(output_root=tmp_path).run(
        request=request,
        terrain=terrain,
        buildings=(building,),
        water=(water,),
        terrain_texture_uri="tile-imagery.jpg",
        facade_texture_uri="facade-atlas.png",
    )

    gltf = _read_glb_json(result.glb_path.read_bytes())
    materials = {primitive["material"] for primitive in gltf["meshes"][0]["primitives"]}

    assert 1 not in materials
    assert 4 not in materials
    assert result.metrics["building_features"] == 0
    assert result.metrics["buildings_skipped_in_water"] == 1


def test_open_tile_glb_assigns_facade_style_primitives_by_building_height(tmp_path):
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
        source_id="source:facade-styles",
        source_name="test",
        domain="buildings",
        state="observed",
        license="test",
        resolution="fixture",
    )

    def building(feature_id: str, lon: float, height: float) -> OpenFeature:
        return OpenFeature(
            feature_id=feature_id,
            layer="buildings",
            geometry=((lon, 37.772), (lon + 0.0004, 37.772), (lon + 0.0004, 37.7724), (lon, 37.7724)),
            height_m=height,
            provenance=provenance,
        )

    result = OpenTileWorker(output_root=tmp_path).run(
        request=request,
        terrain=terrain,
        buildings=(
            building("low-rise", -122.426, 10.0),
            building("mid-rise", -122.424, 30.0),
            building("high-rise", -122.422, 85.0),
        ),
        terrain_texture_uri="tile-imagery.jpg",
        facade_texture_uri="facade-atlas.png",
    )

    gltf = _read_glb_json(result.glb_path.read_bytes())
    primitive_materials = {primitive["material"] for primitive in gltf["meshes"][0]["primitives"]}
    material_names = {material["name"] for material in gltf["materials"]}

    assert primitive_materials >= {1, 5, 6}
    assert material_names >= {
        "inferred low-rise facades",
        "inferred mid-rise facades",
        "inferred high-rise facades",
    }
    assert result.metrics["facade_style_low_rise"] == 1
    assert result.metrics["facade_style_mid_rise"] == 1
    assert result.metrics["facade_style_high_rise"] == 1
    assert result.metrics["facade_styles_used"] == 3


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


def test_fetch_imagery_builds_large_requests_from_observed_quadrants(monkeypatch):
    from PIL import Image

    colors = [
        (220, 20, 20),
        (20, 180, 60),
        (35, 80, 220),
        (230, 200, 40),
    ]
    payloads = []
    for color in colors:
        image = Image.new("RGB", (2, 2), color)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        payloads.append(buffer.getvalue())

    calls = []

    def fake_fetch_image_bytes(url: str, timeout_s: int):
        calls.append(url)
        return payloads[len(calls) - 1], "image/jpeg"

    monkeypatch.setattr(golden_tile, "_fetch_image_bytes", fake_fetch_image_bytes)

    image_bytes = golden_tile._fetch_imagery_mosaic(TerrainBounds(10.0, 12.0, 20.0, 22.0), 4, 30)
    result = Image.open(BytesIO(image_bytes)).convert("RGB")

    assert len(calls) == 4
    assert result.size == (4, 4)
    assert result.getpixel((0, 0))[0] > 180
    assert result.getpixel((3, 0))[1] > 140
    assert result.getpixel((0, 3))[2] > 170
    assert result.getpixel((3, 3))[0] > 180


def test_facade_atlas_contains_distinct_style_bands():
    from PIL import Image

    image = Image.open(BytesIO(golden_tile._build_facade_atlas_png())).convert("RGB")

    assert image.size == (768, 256)
    assert image.getpixel((40, 40)) != image.getpixel((300, 40))
    assert image.getpixel((300, 40)) != image.getpixel((560, 40))


def _read_glb_json(glb: bytes) -> dict:
    magic, version, _length = struct.unpack_from("<4sII", glb, 0)
    assert magic == b"glTF"
    assert version == 2
    json_length, chunk_type = struct.unpack_from("<I4s", glb, 12)
    assert chunk_type == b"JSON"
    return json.loads(glb[20 : 20 + json_length].decode("utf-8"))
