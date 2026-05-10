"""Command-line helpers for local Earth Replica development."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth_replica.demo import build_demo_preview_simulation
from earth_replica.visualizer import render_preview_html


def run_preview(
    steps: int,
    output_path: Path,
    html_path: Path | None = None,
    terrain_path: Path | None = None,
    physics_path: Path | None = None,
    renderer: str = "maplibre",
    open_tileset_path: Path | None = None,
    center_latitude: float = 37.7749,
    center_longitude: float = -122.4194,
    h3_index: str = "872830828ffffff",
) -> Path:
    if steps <= 0:
        raise ValueError("steps must be positive")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    simulation = build_demo_preview_simulation(
        latitude=center_latitude,
        longitude=center_longitude,
        h3_index=h3_index,
    )
    frames = simulation.run(steps=steps)

    with output_path.open("w", encoding="utf-8") as handle:
        for frame in frames:
            handle.write(json.dumps(frame.to_record(), sort_keys=True))
            handle.write("\n")

    if html_path is not None:
        render_preview_html(
            output_path,
            html_path,
            terrain_path=terrain_path,
            physics_path=physics_path,
            renderer=renderer,
            open_tileset_path=open_tileset_path,
        )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Earth Replica previews.")
    parser.add_argument(
        "--steps",
        type=int,
        default=120,
        help="Number of preview simulation steps to run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/preview.jsonl"),
        help="Path to write JSONL simulation frames.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Optional path to write a self-contained HTML animation viewer.",
    )
    parser.add_argument(
        "--terrain",
        type=Path,
        default=None,
        help="Optional terrain JSON tile to embed in the HTML viewer.",
    )
    parser.add_argument(
        "--physics",
        type=Path,
        default=None,
        help="Optional Genesis shard physics JSON to embed in the HTML viewer.",
    )
    parser.add_argument(
        "--renderer",
        choices=("maplibre", "cesium"),
        default="maplibre",
        help="HTML renderer to use for the preview.",
    )
    parser.add_argument(
        "--open-tileset",
        type=Path,
        default=None,
        help="Optional local 3D Tiles tileset.json to load in the Cesium viewer.",
    )
    parser.add_argument("--lat", type=float, default=37.7749, help="Preview center latitude.")
    parser.add_argument("--lon", type=float, default=-122.4194, help="Preview center longitude.")
    parser.add_argument("--h3", default="872830828ffffff", help="Preview H3 index label.")
    args = parser.parse_args()

    output_path = run_preview(
        steps=args.steps,
        output_path=args.output,
        html_path=args.html,
        terrain_path=args.terrain,
        physics_path=args.physics,
        renderer=args.renderer,
        open_tileset_path=args.open_tileset,
        center_latitude=args.lat,
        center_longitude=args.lon,
        h3_index=args.h3,
    )
    print(f"Wrote preview frames to {output_path}")
    if args.html is not None:
        print(f"Wrote preview viewer to {args.html}")


if __name__ == "__main__":
    main()
