from datetime import UTC, datetime

from earth_replica import CellState, LocalGenesisCell
from earth_replica.simulation import (
    LocalPreviewSimulation,
    PreviewBody,
    SimulationConfig,
)


def make_local_cell() -> LocalGenesisCell:
    cell = CellState(
        h3_index="872830828ffffff",
        resolution=7,
        latitude=37.7749,
        longitude=-122.4194,
        elevation_m=12.5,
        observed_at=datetime(2026, 5, 8, 18, 30, tzinfo=UTC),
        fidelity="interactive",
    )
    return LocalGenesisCell.from_cell_state(cell, extent_m=250.0)


def test_preview_simulation_advances_body_with_gravity():
    simulation = LocalPreviewSimulation(
        local_cell=make_local_cell(),
        config=SimulationConfig(time_step_s=0.5, gravity_m_s2=-10.0),
        bodies=(PreviewBody(name="probe", position_m=(0.0, 0.0, 10.0)),),
    )

    frames = simulation.run(steps=2)

    assert len(frames) == 2
    assert frames[0].step == 1
    assert frames[0].bodies["probe"].position_m == (0.0, 0.0, 7.5)
    assert frames[1].bodies["probe"].position_m == (0.0, 0.0, 2.5)


def test_preview_simulation_collides_with_cell_ground():
    simulation = LocalPreviewSimulation(
        local_cell=make_local_cell(),
        config=SimulationConfig(time_step_s=1.0, gravity_m_s2=-10.0),
        bodies=(PreviewBody(name="probe", position_m=(0.0, 0.0, 1.0)),),
    )

    frame = simulation.run(steps=1)[0]

    assert frame.bodies["probe"].position_m == (0.0, 0.0, 0.0)
    assert frame.bodies["probe"].velocity_m_s == (0.0, 0.0, 0.0)


def test_preview_frame_exports_json_serializable_record():
    simulation = LocalPreviewSimulation(
        local_cell=make_local_cell(),
        config=SimulationConfig(time_step_s=0.25),
        bodies=(PreviewBody(name="probe", position_m=(1.0, 2.0, 3.0)),),
    )

    record = simulation.run(steps=1)[0].to_record()

    assert record["h3_index"] == "872830828ffffff"
    assert record["step"] == 1
    assert record["time_s"] == 0.25
    assert record["bodies"]["probe"]["position_m"][0] == 1.0
