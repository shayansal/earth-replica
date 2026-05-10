# Realistic Earth Rendering Stack

Earth Replica should converge on one continuous, lifelike planet experience: orbit from space, zoom to the ground like Google Earth, and attach local Genesis physics only around the camera.

## Primary Runtime Choice

Use CesiumJS and 3D Tiles as the primary Earth renderer for high-fidelity globe streaming. It is the best fit for a browser-based Google Earth-like experience because it is built around WGS84 precision, terrain/imagery streaming, 3D Tiles, camera navigation, and city/building-scale geospatial content.

Keep Three.js for local experimental visualization and Genesis coupling only where we need custom physics rendering that Cesium does not own.

The local preview now supports two renderer modes:

- `maplibre`: lightweight satellite globe and DEM preview for fast iteration.
- `cesium`: 3D Tiles-ready globe path for photorealistic reconstruction, WGS84 anchoring, and future city-scale geometry streaming.

## Photorealistic Data

Preferred target:

- Google Photorealistic 3D Tiles through CesiumJS/Cesium ion or the Google Map Tiles API.
- Cesium World Terrain and Cesium OSM Buildings where licensing/API access permits.
- Open fallback layers: NASA Blue Marble, NOAA ETOPO, OGC/WMTS/WMS layers, OpenStreetMap-derived vectors/buildings.

The production renderer must stream real terrain and imagery tiles rather than drawing a separate local plate. Local effects should be clamped to the globe surface or to a true georeferenced 3D tile location.

## High-Fidelity Reconstruction Pipeline

Earth Replica should pursue lifelike global quality through an open, modular pipeline:

```text
multi-view imagery + DEM/DSM
-> radiometric correction, cloud/shadow masking, change detection
-> dense point cloud or depth inference
-> semantic segmentation for roads, water, soil, vegetation, structures
-> footprint extraction and height estimation
-> mesh/building/terrain generation
-> texture synthesis from real imagery
-> 3D Tiles packaging with LOD and provenance
-> Cesium streaming
-> Genesis local physics shard anchored to WGS84
```

Important rule: AI-enhanced geometry or textures must be marked as inferred. Observed imagery, measured DEM/DSM values, and simulated Genesis state must keep separate provenance so the project never confuses generated detail with source truth.

## Build Phases

1. **Renderer foundation:** CesiumJS preview, satellite fallback imagery, optional Cesium ion terrain/buildings, optional Google Photorealistic 3D Tiles, and Genesis shard anchoring.
2. **Open 3D context:** Overture/OSM buildings, roads, places, land-cover classes, and terrain/bathymetry converted into local 3D Tiles.
3. **AI reconstruction:** tile workers for cloud/shadow removal, DSM/DEM fusion, footprint refinement, height estimation, material classification, and texture generation.
4. **Validation and provenance:** per-tile source metadata, confidence scores, temporal stamps, and observed/inferred/simulated/rendered separation.
5. **Physics coupling:** Genesis local shards receive WGS84 anchor, terrain patch, material map, weather/ocean state, and return deformation/water/soil state as local overlays.

## Open Tile Worker Contract

The first open tile worker accepts a bounded WGS84 tile request and emits:

- `tileset.json`: 3D Tiles 1.1 manifest with a WGS84 region, local ENU transform, and `tile.glb` content.
- `tile.glb`: generated local glTF/GLB geometry for the terrain patch and clipped features.
- `provenance.json`: explicit observed, inferred, simulated, and rendered records for every layer.
- `genesis-terrain-patch.json`: terrain grid, material map, water/building/road obstacles, and the Genesis physics output contract.

The golden tile builder in `examples/build_golden_tile.py` is the first quality benchmark. It fetches a bounded measured patch, emits multi-material terrain/building/road/water GLB primitives, and writes `golden-tile-quality.json` so the preview can be judged against source coverage instead of hand-made demo geometry.

Production adapters should replace the fixture features in `examples/build_open_tile.py` with:

- Overture Maps buildings and places.
- OpenStreetMap roads and water features.
- ETOPO/GEBCO/other DEM and bathymetry sources.
- land-cover and material classifiers.
- optional DSM/point-cloud derived building heights.

## Whole-Planet Ingestion Mode

Whole-planet ingestion must use bulk datasets and distributed workers, not public per-tile APIs. The manifest in `examples/build_whole_planet_ingestion_manifest.py` defines:

- OSM planet PBF or regional extracts for roads, water, parks, coastlines, and land use.
- Overture Maps GeoParquet for global building and transportation features.
- ETOPO and GEBCO global grids for terrain and bathymetry.
- Copernicus/Sentinel global land-cover and imagery indexes for material classes and texture work.
- H3 shard activation, checkpointing, resumability, and object-storage-ready outputs.

The local machine can run bounded preview tiles. A full global run requires object storage, a worker pool, dataset license review, and checkpointed shard scheduling.

The source acquisition catalog in `examples/build_source_acquisition_catalog.py` is the first global gate. By default it writes metadata and bulk-source URIs only. Full-planet download plans require an explicit `--allow-full-planet-downloads` flag so the repo does not accidentally trigger multi-terabyte local downloads.

## AI Earth Context

Use TerraMind as the semantic Earth-observation model layer. TerraMind should run as a Python service that accepts a geospatial tile request and returns land-cover/material context, such as water, vegetation, soil, snow, rock, urban, flood, burn scars, or crop state.

The renderer and Genesis shard runtime should consume this as a local physical context map instead of relying on RGB heuristics.

## Physics Layer

Genesis stays as the local physics engine. The system should simulate only the camera neighborhood on normal machines, then expose a global simulation mode for cluster/exascale deployments.

The local physics region must be georeferenced:

- positioned by latitude/longitude/height
- oriented to the WGS84 surface normal
- scaled by real meters
- attached to streamed terrain rather than intersecting the globe

## WorldWind Role

NASA Web WorldWind is valuable as an OGC/geospatial layer reference and possible adapter, but it should not be the primary photorealistic renderer. CesiumJS plus 3D Tiles is the better core for the target visual experience.
