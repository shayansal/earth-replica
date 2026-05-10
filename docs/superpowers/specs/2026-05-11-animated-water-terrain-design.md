# Animated Water And Terrain Relief Design

Date: 2026-05-11

## Goal

Make the Earth preview feel physically alive without losing planet-scale performance. The next milestone restores visible terrain relief and adds hybrid water animation:

- global water motion that is lightweight enough for the whole globe
- close-range water that transitions into shader-driven and eventually Genesis-driven physical behavior
- provenance metadata that distinguishes observed water geometry, rendered animation, inferred flow, and simulated local physics

## Recommended Sources

- MapLibre GL JS remains the globe renderer for the current whole-planet preview.
- Three.js ocean and water shader techniques provide the close-range water model.
- `jbouny/fft-ocean` is the best open MIT reference for FFT-style ocean rendering with displacement and normal maps.
- Cesium Fabric water materials remain a future option for Cesium/3D Tiles water surfaces.

## Architecture

### Terrain Relief

The preview must enable DEM terrain again by default when a MapTiler key is present. The UI should show terrain status so it is obvious whether altitude is active, degraded, or unavailable.

Terrain is still a rendering layer, not the source of truth. The source-of-truth elevation model remains the project terrain/DEM ingestion pipeline, while MapLibre terrain provides browser-scale relief in the live preview.

### Global Water Motion

Global water remains a semantic layer with provenance. Instead of a flat fill, the preview applies a subtle animated material effect:

- slow opacity shimmer
- moving wave highlights
- directional flow metadata stored in a render manifest
- low GPU cost at orbital zooms

This is a rendered visual layer. It must not be labeled as fully physically simulated.

### Local Physical Water

At close zooms, the renderer should transition into a local water patch:

- shader water with animated normals, depth tint, reflectivity, and roughness
- shoreline blending against terrain and semantic water polygons
- hooks for Genesis/SPH frame data when a local physics shard exists
- fallback to shader-only water when no physics shard is loaded

The close-range patch is the path toward natural-looking water that can later use true local physics.

## Data Flow

1. Semantic water polygons identify where water exists.
2. DEM/bathymetry data describes terrain height and water depth where available.
3. A water render manifest records global visual parameters and local physics availability.
4. MapLibre renders the whole globe with DEM terrain and animated water semantics.
5. Close zoom activates a local shader/physics water surface over the selected water area.
6. Provenance panel reports each water layer as observed, rendered, inferred, or simulated.

## Components

- `water_rendering.py`: serializable water render manifest and provenance contract.
- `visualizer.py`: MapLibre terrain restoration, animated semantic water layer, and preview UI status.
- Local shader hook in the preview template: lightweight first pass, compatible with later Three.js or Cesium path.
- Tests for manifest shape, DEM activation markers, animated water markers, and provenance language.

## Error Handling

- If MapTiler terrain is unavailable, show a visible "terrain unavailable" status and keep satellite/semantic layers working.
- If animated water cannot run, fall back to the static semantic water layer.
- If Genesis water frames are absent, mark local water as rendered shader water, not simulated physics.

## Testing

- Unit tests must assert the preview embeds terrain activation and animated water metadata.
- Unit tests must assert the water provenance states are present.
- Browser verification should confirm the preview loads, the legend shows terrain and water statuses, and no JavaScript errors block rendering.

## Out Of Scope For This Milestone

- Full global ocean physics.
- Global tide, current, wind, and weather assimilation.
- Downloading all global bathymetry/ocean products.
- Replacing the current globe renderer.

Those are future ingestion and physics milestones. This milestone makes the preview visibly alive while preserving the honest data model.
