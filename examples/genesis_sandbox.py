"""Minimal local-cell Genesis sandbox for Earth Replica.

Install Genesis before running:

    python -m pip install genesis-world
    python examples/genesis_sandbox.py
"""

from __future__ import annotations

from datetime import UTC, datetime

from earth_replica import PROJECT, CellState, LocalGenesisCell


def build_demo_cell() -> LocalGenesisCell:
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
    return LocalGenesisCell.from_cell_state(cell, extent_m=250.0)


def main() -> None:
    try:
        import genesis as gs
    except ImportError as exc:
        raise SystemExit(
            "Genesis is not installed. Run `python -m pip install genesis-world` "
            "after installing the platform-specific PyTorch build you need."
        ) from exc

    gs.init(backend=gs.cpu)

    local_cell = build_demo_cell()
    scene = gs.Scene(show_viewer=True)
    scene.add_entity(gs.morphs.Plane())
    scene.add_entity(
        gs.morphs.Box(
            pos=(
                local_cell.genesis_origin[0],
                local_cell.genesis_origin[1],
                local_cell.genesis_origin[2] + 1.0,
            ),
            size=(0.25, 0.25, 0.25),
        )
    )
    scene.build()

    print(
        f"Running {PROJECT.name} Genesis sandbox for H3 cell "
        f"{local_cell.h3_index} over {local_cell.extent_m} meters."
    )

    for _ in range(240):
        scene.step()


if __name__ == "__main__":
    main()
