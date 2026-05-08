# Earth Replica

**Earth Replica** is an open source initiative to create a global 4D live illustration of Earth where physical laws apply and the live state of the planet is simulated through sensor inputs, IoT devices, edge devices, public datasets, and physics engines.

The long-term goal is simple to say and hard to build: make it possible to experience being anywhere on Earth, at any time, from anywhere, and to simulate physical scenarios with transparent, progressively validated fidelity.

This repository is the foundation layer. It starts with a Genesis-backed simulation sandbox, a clear physics scope, and the project structure needed for contributors to add sensor ingestion, geospatial state, rendering, and domain-specific solvers over time.

## What This Is

- A public foundation for a 4D Earth simulation and illustration platform.
- A place to connect live and historical observations with physical simulation.
- A progressive-fidelity system: every simulated behavior should state what physical domain it models, what assumptions it makes, and how it can be validated.
- A Genesis-first Python project for early embodied, material, rigid-body, deformable, fluid, and rendered-world experiments.

## What This Is Not Yet

- It is not a complete replica of Earth.
- It is not a claim that every physical law can be simulated perfectly at planetary scale.
- It is not a replacement for weather, climate, CFD, geophysics, or quantum-scale scientific tools.

Earth Replica treats "all physical laws apply" as a north star: a modular architecture where physical domains can be added, tested, coupled, and improved.

## Foundation Architecture

```text
Earth Replica
├── observation layer       sensor feeds, IoT, edge devices, public datasets
├── state layer             geospatial tiles, entities, materials, time-series state
├── physics layer           Genesis first, specialized solvers over time
├── assimilation layer      reconcile observations with simulated state
├── experience layer        render, replay, inspect, and interact with places
└── validation layer        compare predictions and simulations with real observations
```

See [docs/architecture.md](docs/architecture.md) and [docs/physics-scope.md](docs/physics-scope.md).
The first integration map is in [docs/integration-roadmap.md](docs/integration-roadmap.md).

## Quick Start

Create a Python environment with Python 3.10 through 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the tests:

```bash
python -m pytest
```

Run the dependency-light local preview loop:

```bash
python examples/preview_simulation.py --steps 120 --output artifacts/preview.jsonl --html artifacts/preview.html
```

The generated HTML viewer uses Three.js to render Earth at real WGS84 scale in the data model, with a scaled globe for browser visualization and time playback as the fourth dimension.
It also loads a Natural Earth land/water mask and renders known elevation/bathymetry samples with meter-based provenance. See [docs/surface-model.md](docs/surface-model.md).

Fetch a coarse global NOAA ETOPO 2022 relief grid and embed it in the preview:

```bash
python -c "from pathlib import Path; from earth_replica.terrain import TerrainBounds, fetch_etopo_tile; tile=fetch_etopo_tile(TerrainBounds(-90,90,-180,180), stride=360, timeout_s=360); tile.write_json(Path('artifacts/etopo_global.json'))"
python examples/preview_simulation.py --steps 120 --output artifacts/preview.jsonl --html artifacts/preview.html --terrain artifacts/etopo_global.json
```

Fetch a local higher-resolution ETOPO 2022 terrain subset and embed it in the preview:

```bash
python examples/fetch_etopo_tile.py --min-lat 37.7 --max-lat 37.8 --min-lon -122.5 --max-lon -122.4 --stride 10 --output artifacts/etopo_tile.json
python examples/preview_simulation.py --steps 120 --output artifacts/preview.jsonl --html artifacts/preview.html --terrain artifacts/etopo_tile.json
```

Genesis is an optional heavy dependency because it may require platform-specific PyTorch setup. Install it when you are ready to run the simulation sandbox:

```bash
python -m pip install genesis-world
$env:PYTHONUTF8 = "1"
python examples/genesis_sandbox.py --headless --steps 60
python examples/genesis_sandbox.py --steps 240
```

Run the exascale-shaped local shard runtime. This uses the same shard/job/artifact
contract we can later point at cloud, Slurm, Kubernetes, or Ray workers, but runs
one water/soil tile on this machine:

```bash
python examples/run_local_shard.py --steps 12
python examples/preview_simulation.py --steps 120 --output artifacts/preview.jsonl --html artifacts/preview.html --terrain artifacts/etopo_global.json --physics artifacts/shards/h3_7_872830828ffffff/<job-id>/genesis-water-soil-frames.json
```

Use `--skip-genesis` for a fast contract-only artifact when iterating on browser rendering.

Build the local exascale stack manifest:

```bash
python examples/build_planetary_stack_manifest.py --output artifacts/planetary-stack-manifest.json
```

The manifest describes the data fabric, tile solver plan, local execution backend,
progressive streaming layers, and governance policy. Each piece is local today but
uses contracts designed to map to object storage, distributed workers, and live
sensor ingestion later.

## Repository Layout

```text
src/earth_replica/        core package metadata and interfaces
examples/                 runnable experiments and sandboxes
docs/                     architecture, physics scope, and project plans
db/                       database schemas for planetary state
tests/                    executable project contracts
.github/workflows/        CI checks
```

## Contributing Direction

Useful first contributions include:

- Add a small geospatial state tile abstraction.
- Add a public weather or sensor dataset adapter.
- Add a Genesis example for a local terrain, rigid body, fluid, or deformable scene.
- Add validation examples that compare simulated output with observed data.
- Improve documentation around physics assumptions and limitations.

Every contribution should make its physical assumptions explicit.

## License

MIT License. See [LICENSE](LICENSE).
