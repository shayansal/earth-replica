# Architecture

Earth Replica is designed as a layered system. The early repository focuses on the smallest useful foundation: define the mission, define the physics boundaries, and provide a Genesis-backed sandbox that later modules can build around.

## Layers

### Observation Layer

The observation layer receives live and historical signals from public datasets, sensor networks, IoT devices, edge devices, satellites, cameras, weather stations, and human-curated data sources.

Initial work should prefer open, reproducible datasets. Live sensor integrations should include source metadata, timestamps, geospatial coordinates, confidence, and privacy constraints.

### State Layer

The state layer represents Earth as time-indexed geospatial state:

- Places and tiles
- Entities and materials
- Environmental measurements
- Simulated state
- Observation provenance

This layer should separate observed facts from simulated estimates.

### Physics Layer

The physics layer starts with Genesis for local physical simulation. Genesis is useful for early rigid-body, deformable, fluid, granular, material, and rendered-world experiments.

Specialized solvers can be added later for domains where Genesis is not the right tool, including atmospheric modeling, climate, hydrology, electromagnetism, acoustics, chemistry, and high-resolution CFD.

### Assimilation Layer

The assimilation layer reconciles observations with simulated state. It should answer:

- What was directly observed?
- What was inferred?
- What was simulated forward from prior state?
- How confident is the result?

### Experience Layer

The experience layer lets people inspect, replay, and interact with Earth Replica. Early versions can be command-line experiments and rendered simulation clips. Later versions can become web, VR, AR, and agent-facing interfaces.

### Validation Layer

The validation layer compares simulation output with real observations. This layer is essential because the project should earn fidelity through measurement instead of claiming it.

## First Milestone

The first milestone is a local Genesis sandbox plus a clear project contract:

- Project metadata
- Initial physics domains
- Public mission and boundaries
- CI and tests
- Documentation for architecture and physics scope

The next milestone should add a small geospatial state model and one real public data adapter.
