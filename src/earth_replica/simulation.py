"""Local preview simulation primitives.

These classes provide a lightweight development loop before a selected cell is
handed to Genesis or another specialized solver.
"""

from __future__ import annotations

from dataclasses import dataclass

from earth_replica.cells import LocalGenesisCell
from earth_replica.earth import EARTH_SCALE

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for a deterministic local preview simulation."""

    time_step_s: float = 1.0 / 60.0
    gravity_m_s2: float = -9.80665

    def __post_init__(self) -> None:
        if self.time_step_s <= 0:
            raise ValueError("time_step_s must be positive")


@dataclass(frozen=True)
class PreviewBody:
    """A simple body used by the dependency-light preview backend."""

    name: str
    position_m: Vector3
    velocity_m_s: Vector3 = (0.0, 0.0, 0.0)

    def step(self, config: SimulationConfig) -> PreviewBody:
        vx, vy, vz = self.velocity_m_s
        px, py, pz = self.position_m
        next_vz = vz + config.gravity_m_s2 * config.time_step_s
        next_z = pz + next_vz * config.time_step_s

        if next_z <= 0.0:
            next_z = 0.0
            next_vz = 0.0

        return PreviewBody(
            name=self.name,
            position_m=(px + vx * config.time_step_s, py + vy * config.time_step_s, next_z),
            velocity_m_s=(vx, vy, next_vz),
        )

    def to_record(self) -> dict[str, object]:
        return {
            "position_m": list(self.position_m),
            "velocity_m_s": list(self.velocity_m_s),
        }


@dataclass(frozen=True)
class SimulationFrame:
    """One time step of local preview output."""

    h3_index: str
    cell: LocalGenesisCell
    step: int
    time_s: float
    bodies: dict[str, PreviewBody]

    def to_record(self) -> dict[str, object]:
        return {
            "h3_index": self.h3_index,
            "planet": EARTH_SCALE.to_record(),
            "cell": {
                "center_latitude": self.cell.origin_latitude,
                "center_longitude": self.cell.origin_longitude,
                "center_elevation_m": self.cell.origin_elevation_m,
                "extent_m": self.cell.extent_m,
            },
            "step": self.step,
            "time_s": self.time_s,
            "bodies": {
                name: body.to_record()
                for name, body in sorted(self.bodies.items())
            },
        }


@dataclass(frozen=True)
class LocalPreviewSimulation:
    """A fast local-cell simulation for development and CI."""

    local_cell: LocalGenesisCell
    config: SimulationConfig
    bodies: tuple[PreviewBody, ...]

    def run(self, steps: int) -> list[SimulationFrame]:
        if steps < 0:
            raise ValueError("steps must be non-negative")

        bodies = {body.name: body for body in self.bodies}
        frames: list[SimulationFrame] = []

        for step_number in range(1, steps + 1):
            bodies = {
                name: body.step(self.config)
                for name, body in bodies.items()
            }
            frames.append(
                SimulationFrame(
                    h3_index=self.local_cell.h3_index,
                    cell=self.local_cell,
                    step=step_number,
                    time_s=step_number * self.config.time_step_s,
                    bodies=bodies,
                )
            )

        return frames
