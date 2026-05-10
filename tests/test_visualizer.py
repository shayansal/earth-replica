import json

from earth_replica.terrain import TerrainBounds, TerrainSample, TerrainTile
from earth_replica.visualizer import render_preview_html


def test_render_preview_html_embeds_frames_and_canvas(tmp_path):
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
    assert '<canvas id="scene"' in html
    assert 'from "three"' in html
    assert 'from "topojson-client"' in html
    assert "land-110m.json" in html
    assert "6,371,008.8 m" in html
    assert "Challenger Deep" in html
    assert "Mount Everest" in html
    assert '<script id="terrain-tile-data" type="application/json">' in html
    assert "NOAA ETOPO 2022 Global Relief Model" in html
    assert "buildTerrainMesh" in html
    assert "buildLocalTerrainMesh" in html
    assert "Vertical display" in html
    assert "Terrain exaggeration" in html
    assert 'bodyCount.textContent = terrainTile ? "hidden" : String(names.length)' in html
    assert "if (!terrainTile) {\n      focusTerrainTile();" in html
    assert '<script id="frames-data" type="application/json">' in html
    assert '<script id="surface-samples-data" type="application/json">' in html
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

    assert "isGlobalTerrainTile" in html
    assert "buildGlobalTerrainMesh" in html
    assert "createGlobalTerrainTextures" in html
    assert "displacementMap" in html
    assert "satelliteTextureUrl" in html
    assert "world.200407.3x5400x2700.jpg" in html
    assert "NASA Blue Marble satellite" in html
    assert "nearestElevation" in html
    assert "enableGlobalTerrainMode" in html
    assert "Global ETOPO relief mesh" in html
    assert (
        'function enableGlobalTerrainMode() {\n      activeRenderMode = "global";\n'
        "      earth.visible = false;\n      atmosphere.visible = true;\n"
        "      grid.visible = false;"
    ) in html
    assert "coastlineGroup.visible = false;\n      terrainGroup.visible = true;" in html
    assert 'terrainScale.textContent = "ETOPO visual relief"' in html
    assert 'verticalScale.textContent = "global bump map"' in html
    assert "if (terrainTile && !isGlobalTerrainTile())" in html
    assert "terrainTile.bounds.max_latitude >= 88" in html
    assert "terrainTile.bounds.max_longitude >= 178" in html


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
    assert "buildPhysicsParticles" in html
    assert "updatePhysicsFrame" in html
    assert "Genesis SPH.Liquid" in html
    assert "Genesis MPM.Sand" in html


def test_render_preview_html_has_camera_driven_local_physics_bubble(tmp_path):
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

    assert "localPhysicsBubble" in html
    assert "buildLocalPhysicsBubble" in html
    assert "applyLocalSoilRelief" in html
    assert "animateLocalPhysicsBubble" in html
    assert "physicalContextBlend" in html
    assert "updatePhysicalContextBlend" in html
    assert "setPhysicalContextBlend" in html
    assert "deriveLocalContextFromSatellite" in html
    assert "classifySatelliteContext" in html
    assert "localVegetationGroup" in html
    assert "positionPhysicalContextOnGlobe" in html
    assert "makeSurfaceBasis" in html
    assert "localContextPatchRadius" in html
    assert "ConeGeometry" not in html
    assert "updateRenderModeFromCamera" in html
    assert "particleToLocalVector" in html
    assert "modeValue.textContent = renderModeLabels[activeRenderMode]" in html
