"""Earth Replica public package surface."""

from earth_replica.cells import CellState, LocalGenesisCell
from earth_replica.demo import build_demo_cell, build_demo_preview_simulation
from earth_replica.earth import EARTH_SCALE, EarthScale
from earth_replica.project import PROJECT, EarthReplicaProject, SimulationDomain
from earth_replica.simulation import (
    LocalPreviewSimulation,
    PreviewBody,
    SimulationConfig,
    SimulationFrame,
)
from earth_replica.surface import SurfaceSample, SurfaceSource, SurfaceType

__all__ = [
    "PROJECT",
    "CellState",
    "EarthReplicaProject",
    "EarthScale",
    "EARTH_SCALE",
    "LocalGenesisCell",
    "LocalPreviewSimulation",
    "PreviewBody",
    "SimulationDomain",
    "SimulationConfig",
    "SimulationFrame",
    "SurfaceSample",
    "SurfaceSource",
    "SurfaceType",
    "build_demo_cell",
    "build_demo_preview_simulation",
]
