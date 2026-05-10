# Realistic Earth Rendering Stack

Earth Replica should converge on one continuous, lifelike planet experience: orbit from space, zoom to the ground like Google Earth, and attach local Genesis physics only around the camera.

## Primary Runtime Choice

Use CesiumJS and 3D Tiles as the primary Earth renderer for high-fidelity globe streaming. It is the best fit for a browser-based Google Earth-like experience because it is built around WGS84 precision, terrain/imagery streaming, 3D Tiles, camera navigation, and city/building-scale geospatial content.

Keep Three.js for local experimental visualization and Genesis coupling only where we need custom physics rendering that Cesium does not own.

## Photorealistic Data

Preferred target:

- Google Photorealistic 3D Tiles through CesiumJS/Cesium ion or the Google Map Tiles API.
- Cesium World Terrain and Cesium OSM Buildings where licensing/API access permits.
- Open fallback layers: NASA Blue Marble, NOAA ETOPO, OGC/WMTS/WMS layers, OpenStreetMap-derived vectors/buildings.

The production renderer must stream real terrain and imagery tiles rather than drawing a separate local plate. Local effects should be clamped to the globe surface or to a true georeferenced 3D tile location.

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
