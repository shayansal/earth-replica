"""Command-line helpers for local Earth Replica development."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from earth_replica.demo import build_demo_preview_simulation


def run_preview(steps: int, output_path: Path) -> Path:
    if steps <= 0:
        raise ValueError("steps must be positive")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    simulation = build_demo_preview_simulation()
    frames = simulation.run(steps=steps)

    with output_path.open("w", encoding="utf-8") as handle:
        for frame in frames:
            handle.write(json.dumps(frame.to_record(), sort_keys=True))
            handle.write("\n")

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
    args = parser.parse_args()

    output_path = run_preview(steps=args.steps, output_path=args.output)
    print(f"Wrote preview frames to {output_path}")


if __name__ == "__main__":
    main()
