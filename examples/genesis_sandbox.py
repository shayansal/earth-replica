"""Minimal Genesis sandbox for Earth Replica.

Install Genesis before running:

    python -m pip install genesis-world
    python examples/genesis_sandbox.py
"""

from __future__ import annotations

from earth_replica import PROJECT


def main() -> None:
    try:
        import genesis as gs
    except ImportError as exc:
        raise SystemExit(
            "Genesis is not installed. Run `python -m pip install genesis-world` "
            "after installing the platform-specific PyTorch build you need."
        ) from exc

    gs.init(backend=gs.cpu)

    scene = gs.Scene(show_viewer=True)
    scene.add_entity(gs.morphs.Plane())
    scene.add_entity(gs.morphs.Box(pos=(0.0, 0.0, 1.0), size=(0.25, 0.25, 0.25)))
    scene.build()

    print(f"Running {PROJECT.name} Genesis sandbox. Close the viewer to stop.")

    for _ in range(240):
        scene.step()


if __name__ == "__main__":
    main()
