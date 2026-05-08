# Integration Roadmap

Earth Replica should use Genesis as the local interactive physics kernel, not as the only engine in the system. Planet-scale simulation needs a federation of geospatial data systems, live observation pipelines, and specialized solvers that exchange bounded state.

## Core Direction

```text
H3 cell -> observed state -> local Genesis scene -> simulated deltas -> validation -> planetary state
```

Each simulated location should begin as an H3-indexed cell or cell set. Genesis can simulate a bounded local scene inside that cell while the rest of the platform stores global state, history, provenance, and cross-domain solver output.

## Priority Integrations

### 1. Planetary Index and Storage

- [H3](https://github.com/uber/h3): global hierarchical cell addressing.
- [PostGIS](https://github.com/postgis/postgis): spatial storage for cells, geometry, terrain, roads, buildings, and regions.
- [TimescaleDB](https://github.com/timescale/timescaledb): time-series storage for observed and simulated cell state.
- [GDAL](https://www.osgeo.org/projects/gdal/): raster and vector import/export.
- [osm2pgsql](https://github.com/osm2pgsql-dev/osm2pgsql): OpenStreetMap import into PostGIS.

First target: store H3 cell centers and time-indexed observations in PostGIS/TimescaleDB.

### 2. Experience and Visualization

- [CesiumJS](https://github.com/CesiumGS/cesium): full-globe 3D visualization, terrain, 3D Tiles, glTF, and time-dynamic layers.
- [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js): web-native maps, vector tiles, 3D terrain, and lighter client views.
- [osgEarth](https://github.com/gwaldron/osgearth): native C++ geospatial terrain and visualization if a desktop/native engine becomes useful.

First target: export cell state and simulation deltas into formats a Cesium viewer can render.

### 3. Weather, Ocean, Ice, and Climate

- [ECMWF earthkit](https://github.com/ecmwf/earthkit): weather and climate data workflows.
- [Open-Meteo](https://github.com/open-meteo/open-meteo): approachable weather API stack for early live weather ingestion.
- [CESM](https://github.com/ESCOMP/CESM): coupled Earth system modeling.
- [MITgcm](https://mitgcm.readthedocs.io/): ocean and atmosphere circulation modeling.
- [MOM6 examples](https://github.com/NOAA-GFDL/MOM6-examples): NOAA/GFDL ocean modeling configurations.
- [CICE](https://github.com/CICE-Consortium/CICE): sea ice modeling.

First target: ingest weather observations and forecasts as cell properties before attempting solver coupling.

### 4. Specialized Physics Solvers

- [Project Chrono](https://github.com/projectchrono/chrono): multiphysics, vehicles, deformable terrain, granular dynamics, and fluid-solid interaction.
- [OpenFOAM](https://openfoam.org/): high-fidelity computational fluid dynamics.
- [ASPECT](https://github.com/geodynamics/aspect): geodynamics, mantle convection, and tectonic processes.
- [Fluidity](https://fluidityproject.github.io/): multiphase CFD on unstructured meshes.

First target: define adapter boundaries and data exchange formats. Do not couple these directly into Genesis until a specific scenario needs them.

### 5. Sensor, IoT, and Edge Digital Twins

- [Eclipse Ditto](https://github.com/eclipse-ditto/ditto): digital twins for real-world devices and state.
- [Eclipse Hono](https://github.com/eclipse-hono/hono): IoT messaging interfaces.
- [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib): telemetry ingestion for metrics, logs, traces, and edge signals.
- [ns-3](https://www.nsnam.org/): network simulation for IoT and edge connectivity scenarios.

First target: normalize sensor observations into the same `CellState` shape used by the local simulation layer.

## Near-Term Build Order

1. Define an H3 cell state model in Python.
2. Add a PostGIS/TimescaleDB schema for cells and observations.
3. Add a Genesis local-cell sandbox that accepts a cell center and extent.
4. Add a public weather adapter that writes properties onto a cell.
5. Add Cesium export for cell state and local simulation outputs.

## Integration Rule

Every adapter must state:

- What physical domain it represents.
- Whether data is observed, inferred, simulated, or rendered.
- Its spatial resolution.
- Its temporal resolution.
- Its assumptions and validation path.
