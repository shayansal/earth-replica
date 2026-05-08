"""Reusable demo factories for local development."""

from __future__ import annotations

from datetime import UTC, datetime

from earth_replica.cells import CellState, LocalGenesisCell
from earth_replica.simulation import (
    LocalPreviewSimulation,
    PreviewBody,
    SimulationConfig,
)


def build_demo_cell(extent_m: float = 250.0) -> LocalGenesisCell:
    cell = CellState(
        h3_index="872830828ffffff",
        resolution=7,
        latitude=37.7749,
        longitude=-122.4194,
        elevation_m=12.5,
        observed_at=datetime.now(UTC),
        fidelity="interactive",
        properties={
            "label": "San Francisco demo cell",
            "terrain": "flat placeholder",
            "source": "example",
        },
    )
    return LocalGenesisCell.from_cell_state(cell, extent_m=extent_m)


def build_demo_preview_simulation(
    steps_extent_m: float = 250.0,
) -> LocalPreviewSimulation:
    return LocalPreviewSimulation(
        local_cell=build_demo_cell(extent_m=steps_extent_m),
        config=SimulationConfig(time_step_s=1.0 / 30.0),
        bodies=(
            PreviewBody(name="probe", position_m=(0.0, 0.0, 3.0)),
            PreviewBody(
                name="eastbound",
                position_m=(-2.0, 0.0, 0.4),
                velocity_m_s=(1.0, 0.0, 0.0),
            ),
        ),
    )
