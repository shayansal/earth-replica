from earth_replica.semantic_layers import semantic_surface_layers, semantic_surface_manifest


def test_semantic_surface_manifest_defines_materials_and_provenance():
    manifest = semantic_surface_manifest()
    layers = {layer["id"]: layer for layer in manifest["layers"]}

    assert manifest["schema"] == "earth-replica/semantic-surface-layers/v1"
    assert set(layers) >= {
        "water",
        "roads",
        "forest",
        "snow_ice",
        "desert_sand",
        "farmland",
        "urban",
        "park_grass",
        "wetland",
    }
    assert layers["water"]["material"]["class"] == "water"
    assert layers["roads"]["material"]["physical_surface"] == "impervious"
    assert layers["forest"]["provenance"]["state"] == "observed"
    assert layers["snow_ice"]["source_layers"] == ["landcover"]
    assert manifest["quality_policy"]["semantic_layers_are_not_pixel_colors"] is True


def test_semantic_surface_layers_are_ordered_for_map_rendering():
    ids = [layer.id for layer in semantic_surface_layers()]

    assert ids.index("water") < ids.index("roads")
    assert ids.index("urban") < ids.index("roads")
    assert len(ids) == len(set(ids))
