# Animated Water Terrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore readable terrain relief and add hybrid animated water to the Earth preview.

**Architecture:** Add a small Python manifest for water rendering/provenance, embed it into the MapLibre preview, and drive lightweight browser animation from that manifest. Terrain relief is restored through explicit DEM terrain activation plus a hillshade layer so altitude remains visible at globe scale.

**Tech Stack:** Python dataclasses, pytest, MapLibre GL JS raster-dem terrain, MapLibre hillshade, vector water layers, requestAnimationFrame paint updates.

---

### Task 1: Water Rendering Manifest

**Files:**
- Create: `src/earth_replica/water_rendering.py`
- Create: `tests/test_water_rendering.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_water_rendering.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'earth_replica.water_rendering'`.

- [ ] **Step 3: Write minimal implementation**

```python
def water_render_manifest() -> dict[str, object]:
    return {
        "schema": "earth-replica/water-rendering/v1",
        "global_motion": {
            "mode": "rendered_shader",
            "wave_speed_mps": 0.35,
            "shimmer_period_s": 5.5,
            "highlight_opacity": 0.18,
            "provenance": {"state": "rendered", "source": "semantic water polygons plus procedural wave render"},
        },
        "local_physics": {
            "activation_zoom": 10.0,
            "fallback_mode": "shader_only",
            "provenance_without_frames": {"state": "rendered"},
            "provenance_with_frames": {"state": "simulated"},
        },
        "recommended_repositories": [
            {"name": "jbouny/fft-ocean", "url": "https://github.com/jbouny/fft-ocean"}
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_water_rendering.py -q`

Expected: PASS.

### Task 2: Preview Embedding And Terrain Relief Tests

**Files:**
- Modify: `tests/test_visualizer.py`

- [ ] **Step 1: Write the failing tests**

```python
assert '<script id="water-render-data" type="application/json">' in html
assert "semantic-water-motion" in html
assert "animateWaterLayers" in html
assert "local-water-wave-shader" in html
assert "terrain-relief-hillshade" in html
assert "map.setTerrain({ source: \"terrainSource\", exaggeration: terrainExaggeration })" in html
assert "Terrain relief" in html
assert "Animated water" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_visualizer.py::test_render_preview_html_embeds_frames_and_maplibre_globe -q`

Expected: FAIL because the preview does not yet embed water render data or explicit relief/water animation markers.

### Task 3: MapLibre Preview Implementation

**Files:**
- Modify: `src/earth_replica/visualizer.py`

- [ ] **Step 1: Embed water manifest JSON**

Import `water_render_manifest`, serialize it in `render_preview_html`, add a `water-render-data` script tag, and parse `waterRenderManifest` in the MapLibre template.

- [ ] **Step 2: Restore visible terrain altitude**

Add `const terrainExaggeration = 1.75`, a `terrain-relief-hillshade` layer using `terrainSource`, and call `map.setTerrain({ source: "terrainSource", exaggeration: terrainExaggeration })` during style load.

- [ ] **Step 3: Add global water animation**

Add a `semantic-water-motion` layer over the vector `water` source-layer and an `animateWaterLayers(timestamp)` loop that updates fill opacity and color through `map.setPaintProperty`.

- [ ] **Step 4: Add local shader hook**

Add a hidden animated canvas source named `localWaterCanvas` with a raster layer `local-water-wave-shader`. Render procedural wave lines into the canvas and keep the layer near-transparent until close zoom so it becomes the later Three.js/Genesis bridge.

- [ ] **Step 5: Update preview copy**

Add legend rows for `Terrain relief` and `Animated water`, with provenance wording that says global water is rendered and local water becomes simulated only when Genesis frames are present.

- [ ] **Step 6: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_water_rendering.py tests\test_visualizer.py::test_render_preview_html_embeds_frames_and_maplibre_globe tests\test_visualizer.py::test_render_preview_html_supports_global_terrain_mode -q`

Expected: PASS.

### Task 4: Verification And Preview

**Files:**
- Generated only: `artifacts/preview.jsonl`, `artifacts/cesium-preview.html`

- [ ] **Step 1: Run full tests**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Regenerate preview**

Run: `.\.venv\Scripts\python.exe examples\preview_simulation.py --steps 120 --lat 48.593568 --lon 7.72106 --output artifacts\preview.jsonl --html artifacts\cesium-preview.html --renderer maplibre`

Expected: writes `artifacts\preview.jsonl` and `artifacts\cesium-preview.html`.

- [ ] **Step 3: Browser check**

Open `http://127.0.0.1:8765/artifacts/cesium-preview.html?fresh=animated-water-terrain`.

Expected: page loads, legend includes terrain relief and animated water, and no app-blocking JavaScript errors appear.

- [ ] **Step 4: Protected publishing scan**

Run the repository protected publishing scan before committing.

Expected: exit code 1 with no matches.

- [ ] **Step 5: Commit and push**

Run:

```powershell
git add docs/superpowers/plans/2026-05-11-animated-water-terrain.md src/earth_replica/water_rendering.py src/earth_replica/visualizer.py tests/test_water_rendering.py tests/test_visualizer.py
git commit -m "feat: animate water and restore terrain relief"
git push origin main
```
