from earth_replica.water_rendering import water_render_manifest


def test_water_render_manifest_defines_global_and_local_modes():
    manifest = water_render_manifest()

    assert manifest["schema"] == "earth-replica/water-rendering/v1"
    assert manifest["global_motion"]["mode"] == "rendered_shader"
    assert manifest["global_motion"]["provenance"]["state"] == "rendered"
    assert manifest["local_physics"]["fallback_mode"] == "shader_only"
    assert manifest["local_physics"]["provenance_without_frames"]["state"] == "rendered"
    assert manifest["local_physics"]["provenance_with_frames"]["state"] == "simulated"
    assert "jbouny/fft-ocean" in {repo["name"] for repo in manifest["recommended_repositories"]}
