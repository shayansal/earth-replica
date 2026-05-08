"""Minimal local-cell Genesis sandbox for Earth Replica.

Install Genesis before running:

    python -m pip install genesis-world
    python examples/genesis_sandbox.py
"""

from __future__ import annotations

import argparse

from earth_replica import PROJECT, build_demo_cell


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Genesis local-cell sandbox.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening the Genesis viewer.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=240,
        help="Number of Genesis simulation steps to run.",
    )
    args = parser.parse_args()

    try:
        import genesis as gs
    except ImportError as exc:
        raise SystemExit(
            "Genesis is not installed. Run `python -m pip install genesis-world` "
            "after installing the platform-specific PyTorch build you need."
        ) from exc

    gs.init(backend=gs.cpu)

    local_cell = build_demo_cell()
    scene = gs.Scene(show_viewer=not args.headless)
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

    for _ in range(args.steps):
        scene.step()

    print(f"Completed {args.steps} Genesis steps.")


if __name__ == "__main__":
    main()
