import json

from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile
from earth_replica.visualizer import render_preview_html


def test_render_preview_html_embeds_frames_and_maplibre_globe(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    frames = [
        {
            "h3_index": "872830828ffffff",
            "planet": {
                "mean_radius_m": 6371008.8,
                "mean_circumference_m": 40030228.88412017,
            },
            "cell": {
                "center_latitude": 37.7749,
                "center_longitude": -122.4194,
            },
            "step": 1,
            "time_s": 0.033,
            "bodies": {
                "probe": {
                    "position_m": [0.0, 0.0, 2.9],
                    "velocity_m_s": [0.0, 0.0, -0.3],
                }
            },
        },
        {
            "h3_index": "872830828ffffff",
            "planet": {
                "mean_radius_m": 6371008.8,
                "mean_circumference_m": 40030228.88412017,
            },
            "cell": {
                "center_latitude": 37.7749,
                "center_longitude": -122.4194,
            },
            "step": 2,
            "time_s": 0.066,
            "bodies": {
                "probe": {
                    "position_m": [0.0, 0.0, 2.7],
                    "velocity_m_s": [0.0, 0.0, -0.6],
                }
            },
        },
    ]
    frames_path.write_text(
        "\n".join(json.dumps(frame) for frame in frames),
        encoding="utf-8",
    )
    terrain_path = tmp_path / "terrain.json"
    terrain_path.write_text(
        json.dumps(
            TerrainTile(
                bounds=TerrainBounds(37.7, 37.8, -122.5, -122.4),
                stride=10,
                samples=(
                    TerrainSample(37.7, -122.5, 10.0),
                    TerrainSample(37.7, -122.4, 20.0),
                    TerrainSample(37.8, -122.5, 15.0),
                    TerrainSample(37.8, -122.4, 25.0),
                ),
            ).to_record()
        ),
        encoding="utf-8",
    )

    returned_path = render_preview_html(frames_path, output_path, terrain_path=terrain_path)
    html = returned_path.read_text(encoding="utf-8")

    assert returned_path == output_path
    assert "Earth Replica Preview" in html
    assert '<div id="map" aria-label="Earth Replica MapLibre globe preview">' in html
    assert "maplibre-gl" in html
    assert "MapLibre GL JS" in html
    assert 'map.setProjection({ type: "globe" })' in html
    assert 'map.setProjection({ type: "mercator" })' in html
    assert "Local tangent" in html
    assert "satelliteSource" in html
    assert "terrainSource" in html
    assert "Focus Physics Area" in html
    assert "1:1 physical data model" in html
    assert "mean_radius_m" in html
    assert "formatMeters(planetRadiusM)" in html
    assert "Challenger Deep" in html
    assert "Mount Everest" in html
    assert '<script id="terrain-tile-data" type="application/json">' in html
    assert "NOAA ETOPO 2022 Global Relief Model" in html
    assert '<script id="frames-data" type="application/json">' in html
    assert '<script id="surface-samples-data" type="application/json">' in html
    assert "__MAPTILER_API_KEY__" not in html
    assert 'const maptilerApiKey = "";' in html
    assert "872830828ffffff" in html
    assert "probe" in html


def test_render_preview_html_supports_global_terrain_mode(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    frames_path.write_text(
        json.dumps(
            {
                "h3_index": "872830828ffffff",
                "planet": {
                    "mean_radius_m": 6371008.8,
                    "mean_circumference_m": 40030228.88412017,
                },
                "cell": {
                    "center_latitude": 0.0,
                    "center_longitude": 0.0,
                },
                "step": 1,
                "time_s": 0.033,
                "bodies": {},
            }
        ),
        encoding="utf-8",
    )
    terrain_path = tmp_path / "global_terrain.json"
    terrain_path.write_text(
        json.dumps(
            TerrainTile(
                bounds=TerrainBounds(-90.0, 90.0, -180.0, 180.0),
                stride=720,
                samples=(
                    TerrainSample(-90.0, -180.0, -4000.0),
                    TerrainSample(-90.0, 180.0, -3500.0),
                    TerrainSample(90.0, -180.0, 2000.0),
                    TerrainSample(90.0, 180.0, 3000.0),
                ),
            ).to_record()
        ),
        encoding="utf-8",
    )

    returned_path = render_preview_html(frames_path, output_path, terrain_path=terrain_path)
    html = returned_path.read_text(encoding="utf-8")

    assert '"raster-dem"' in html
    assert "terrain-rgb-v2" in html
    assert "World_Imagery" in html
    assert "physics-context-fill" in html
    assert "MapLibre renders a globe projection" in html
    assert "streamed satellite raster tiles and raster DEM terrain" in html
    assert "NOAA ETOPO 2022 Global Relief Model" in html


def test_render_preview_html_embeds_genesis_physics_frames(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    physics_path = tmp_path / "physics.json"
    frames_path.write_text(
        json.dumps(
            {
                "h3_index": "872830828ffffff",
                "planet": {"mean_radius_m": 6371008.8},
                "cell": {
                    "center_latitude": 37.7749,
                    "center_longitude": -122.4194,
                },
                "step": 1,
                "time_s": 0.033,
                "bodies": {},
            }
        ),
        encoding="utf-8",
    )
    physics_path.write_text(
        json.dumps(
            {
                "schema": "earth-replica/genesis-water-soil-frames/v1",
                "engine": {
                    "name": "Genesis",
                    "materials": {
                        "water": "Genesis SPH.Liquid",
                        "soil": "Genesis MPM.Sand",
                    },
                },
                "frames": [
                    {
                        "step": 1,
                        "time_s": 0.033,
                        "water_particles": [[0.0, 0.0, 0.1]],
                        "soil_particles": [[0.1, 0.0, 0.0]],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    returned_path = render_preview_html(
        frames_path,
        output_path,
        physics_path=physics_path,
    )
    html = returned_path.read_text(encoding="utf-8")

    assert '<script id="physics-frames-data" type="application/json">' in html
    assert "Genesis SPH.Liquid" in html
    assert "Genesis MPM.Sand" in html
    assert "Genesis local physics shard" in html
    assert "water samples" in html
    assert "soil samples" in html
    assert "not floating particles" in html
    assert "SphereGeometry" not in html


def test_render_preview_html_has_natural_zoom_to_georeferenced_physics_context(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    physics_path = tmp_path / "physics.json"
    frames_path.write_text(
        json.dumps(
            {
                "h3_index": "872830828ffffff",
                "planet": {"mean_radius_m": 6371008.8},
                "cell": {
                    "center_latitude": 37.7749,
                    "center_longitude": -122.4194,
                },
                "step": 1,
                "time_s": 0.033,
                "bodies": {},
            }
        ),
        encoding="utf-8",
    )
    physics_path.write_text(
        json.dumps(
            {
                "schema": "earth-replica/genesis-water-soil-frames/v1",
                "engine": {"name": "Genesis"},
                "frames": [
                    {
                        "step": 1,
                        "time_s": 0.033,
                        "water_particles": [[0.0, 0.0, 0.1]],
                        "soil_particles": [[0.1, 0.0, 0.0]],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    render_preview_html(frames_path, output_path, physics_path=physics_path)
    html = output_path.read_text(encoding="utf-8")

    assert "Focus Physics Area" in html
    assert "map.easeTo" in html
    assert "zoom: 13" in html
    assert "pitch: 56" in html
    assert "makePhysicsContextFeature" in html
    assert "physicsContext" in html
    assert 'zoom >= 10 ? "Local terrain" : "Global terrain"' in html
    assert "renderWorldCopies: false" in html
    assert "not floating particles" in html
    assert "localPhysicsBubble" not in html
    assert "buildLocalPhysicsBubble" not in html
    assert "scene.add(physicsGroup)" not in html
    assert "SphereGeometry" not in html
    assert "CircleGeometry" not in html
    assert "PlaneGeometry" not in html
    assert "ConeGeometry" not in html


def test_render_preview_html_can_emit_cesium_3d_tiles_preview(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "cesium-preview.html"
    frames_path.write_text(
        json.dumps(
            {
                "h3_index": "872830828ffffff",
                "planet": {"mean_radius_m": 6371008.8},
                "cell": {
                    "center_latitude": 37.7749,
                    "center_longitude": -122.4194,
                },
                "step": 1,
                "time_s": 0.033,
                "bodies": {},
            }
        ),
        encoding="utf-8",
    )

    returned_path = render_preview_html(frames_path, output_path, renderer="cesium")
    html = returned_path.read_text(encoding="utf-8")

    assert returned_path == output_path
    assert "Earth Replica Cesium Preview" in html
    assert "CesiumJS" in html
    assert "Cesium.Cesium3DTileset.fromUrl" in html
    assert "Google Photorealistic 3D Tiles" in html
    assert "createOsmBuildingsAsync" in html
    assert "Genesis physics shard anchor" in html
    assert "WGS84" in html
    assert "872830828ffffff" in html
    assert "__CESIUM_ION_TOKEN_JSON__" not in html
    assert "__GOOGLE_MAPS_API_KEY_JSON__" not in html
    assert 'const cesiumIonToken = "";' in html
    assert 'const googleMapsApiKey = "";' in html


def test_render_preview_html_can_link_local_open_tileset(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    tileset_path = tmp_path / "open" / "h3_7_872830828ffffff" / "tileset.json"
    tileset_path.parent.mkdir(parents=True)
    tileset_path.write_text('{"asset":{"version":"1.1"}}', encoding="utf-8")
    frames_path.write_text(
        json.dumps(
            {
                "h3_index": "872830828ffffff",
                "planet": {"mean_radius_m": 6371008.8},
                "cell": {
                    "center_latitude": 37.7749,
                    "center_longitude": -122.4194,
                },
                "step": 1,
                "time_s": 0.033,
                "bodies": {},
            }
        ),
        encoding="utf-8",
    )

    render_preview_html(
        frames_path,
        output_path,
        renderer="cesium",
        open_tileset_path=tileset_path,
    )
    html = output_path.read_text(encoding="utf-8")

    assert 'const openTilesetUri = "open/h3_7_872830828ffffff/tileset.json";' in html
    assert 'const openGenesisPatchUri = "open/h3_7_872830828ffffff/genesis-terrain-patch.json";' in html
    assert "Local open 3D Tiles" in html
    assert "openTilesetUri" in html
    assert "addMeasuredTileOverlay" in html
    assert "Measured tile overlay" in html
    assert "imageryRectangleUrl" in html
    assert "ImageMaterialProperty" in html
    assert "productionMapStyle" in html
    assert "localTiles.show = false" in html
    assert "viewer.scene.globe.show = false" in html
    assert "if (!openGenesisPatchUri) {"
    assert "flyFocus(viewer)" in html
    assert "HeadingPitchRange" in html
    assert "lookAtTransform" in html
    assert "water_features" in html
    assert "Color.LIME" not in html
    assert "Color.CYAN.withAlpha(0.48)" not in html
    assert "Color.GOLD" not in html
    assert "#0d4f73" not in html
    assert "Roads, water, buildings, and the tile bounds" not in html


def test_render_preview_html_rejects_unknown_renderer(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    frames_path.write_text(
        json.dumps(
            {
                "h3_index": "872830828ffffff",
                "planet": {"mean_radius_m": 6371008.8},
                "cell": {
                    "center_latitude": 0.0,
                    "center_longitude": 0.0,
                },
                "step": 1,
                "time_s": 0.033,
                "bodies": {},
            }
        ),
        encoding="utf-8",
    )

    try:
        render_preview_html(frames_path, output_path, renderer="unknown")
    except ValueError as error:
        assert "renderer must be one of" in str(error)
    else:
        raise AssertionError("render_preview_html accepted an unknown renderer")
