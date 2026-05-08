# Planetary Surface Model

Earth Replica treats land elevation and ocean depth as physical state, not decoration. Values are stored in meters relative to sea level with source, vertical datum, resolution, and confidence metadata.

## Current Surface Layers

### Land and Water Mask

The browser preview loads Natural Earth 110m land polygons through the `world-atlas` TopoJSON redistribution. This gives the globe a real land/water layout suitable for global visualization and early surface classification.

This layer is a global mask, not terrain height. It answers "land or water here?" at coarse scale.

### Elevation and Bathymetry Samples

The Python package includes a starter set of known surface samples:

- Mount Everest, positive elevation.
- Challenger Deep, negative bathymetry.
- Dead Sea shore, land below sea level.
- Mauna Kea summit, volcanic land elevation.

These samples prove the record shape for known elevation and depth values. They are rendered with visual exaggeration so they are visible on a globe, but the stored values remain real meters.

## Target Data Sources

### NOAA ETOPO 2022

ETOPO 2022 is the preferred first global relief substrate because it integrates topography, bathymetry, shoreline, and ice data into one global model at 15 arc-second resolution.

Use it for the first full-planet elevation/depth tile pipeline.

### GEBCO 2025

GEBCO 2025 is the preferred bathymetry-focused upgrade path. It provides a 15 arc-second global terrain and bathymetry grid, plus source/type identifiers. Some ocean floor values are measured directly and others are inferred or interpolated, so source metadata must remain attached.

### Copernicus DEM

Copernicus DEM GLO-30 and GLO-90 are preferred higher-resolution land elevation sources for local terrain once we implement tiled loading.

## Physical Correctness Rules

- Store elevation and depth in meters.
- Store vertical datum and source metadata with each sample, tile, or derived cell.
- Never present interpolated or low-confidence data as measured.
- Use visual exaggeration only in the renderer, never in stored physical values.
- Feed Genesis local terrain from real local tiles, not from the exaggerated globe mesh.

## Next Implementation Steps

1. Add a downloader/converter for small ETOPO 2022 subsets.
2. Convert DEM subsets into local ENU terrain meshes.
3. Attach source/confidence metadata to each terrain tile.
4. Feed selected H3 cells into Genesis as terrain colliders.
5. Add GEBCO source identifiers for ocean regions.
