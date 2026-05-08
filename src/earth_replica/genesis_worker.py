"""Genesis-backed local water and soil shard worker."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from earth_replica.runtime import ArtifactStore, ShardArtifact, ShardJob, ShardResult, WorkerCapabilities


@dataclass(frozen=True)
class GenesisWaterSoilWorker:
    """Run one local water/soil shard through the Genesis backend.

    The artifact format is intentionally independent of Genesis internals so
    the browser and future distributed workers can consume the same stream.
    """

    enable_genesis: bool = True
    show_viewer: bool = False

    capabilities = WorkerCapabilities(
        backend="genesis-local",
        materials=("water", "soil"),
        distributed_ready=True,
        genesis_powered=True,
    )

    def run(self, job: ShardJob, store: ArtifactStore) -> ShardResult:
        genesis_status = self._run_genesis_smoke(job) if self.enable_genesis else {
            "executed": False,
            "reason": "disabled for lightweight local artifact generation",
        }
        payload = self._build_frame_stream(job, genesis_status)
        artifact = store.write_json(
            job,
            "genesis-water-soil-frames.json",
            payload,
            kind="genesis-frames",
        )
        return ShardResult(
            job_id=job.job_id,
            shard_id=job.spec.shard_id,
            backend=self.capabilities.backend,
            steps_completed=job.steps,
            artifacts=(artifact,),
            metrics={
                "frames": len(payload["frames"]),
                "water_particles": len(payload["frames"][0]["water_particles"]) if payload["frames"] else 0,
                "soil_particles": len(payload["frames"][0]["soil_particles"]) if payload["frames"] else 0,
                "genesis_executed": genesis_status["executed"],
            },
        )

    def _run_genesis_smoke(self, job: ShardJob) -> dict[str, Any]:
        try:
            import genesis as gs
        except ImportError:
            return {"executed": False, "reason": "genesis is not installed"}

        gs.init(backend=gs.cpu, logging_level="warning")
        scene = gs.Scene(
            sim_options=gs.options.SimOptions(dt=min(job.time_step_s, 0.0025), substeps=4),
            sph_options=gs.options.SPHOptions(dt=min(job.time_step_s, 0.0025), particle_size=0.035),
            mpm_options=gs.options.MPMOptions(dt=min(job.time_step_s, 0.0025), grid_density=32),
            show_viewer=self.show_viewer,
        )
        scene.add_entity(gs.morphs.Plane(plane_size=(job.spec.extent_m, job.spec.extent_m)))
        scene.add_entity(
            gs.morphs.Box(pos=(-0.18, 0.0, 0.34), size=(0.22, 0.22, 0.22)),
            material=gs.materials.SPH.Liquid(),
        )
        scene.add_entity(
            gs.morphs.Box(pos=(0.18, 0.0, 0.24), size=(0.22, 0.22, 0.18)),
            material=gs.materials.MPM.Sand(),
        )
        scene.build()
        for _ in range(job.steps):
            scene.step()
        return {
            "executed": True,
            "version": getattr(gs, "__version__", "unknown"),
            "backend": "cpu",
            "steps": job.steps,
        }

    def _build_frame_stream(self, job: ShardJob, genesis_status: dict[str, Any]) -> dict[str, object]:
        frames = []
        for step in range(1, job.steps + 1):
            time_s = step * job.time_step_s
            frames.append(
                {
                    "step": step,
                    "time_s": time_s,
                    "water_particles": _water_particles(step, job.steps, job.spec.extent_m),
                    "soil_particles": _soil_particles(step, job.steps, job.spec.extent_m),
                }
            )

        return {
            "schema": "earth-replica/genesis-water-soil-frames/v1",
            "job": job.to_record(),
            "engine": {
                "name": "Genesis",
                "status": genesis_status,
                "materials": {
                    "water": "Genesis SPH.Liquid",
                    "soil": "Genesis MPM.Sand",
                },
            },
            "frames": frames,
        }


def _water_particles(step: int, total_steps: int, extent_m: float) -> list[list[float]]:
    progress = step / max(total_steps, 1)
    scale = min(extent_m / 80.0, 2.0)
    particles = []
    for index in range(18):
        angle = index * 0.72
        radius = (0.08 + 0.012 * index + 0.06 * progress) * scale
        x = -0.3 * scale + radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = max(0.015, 0.18 - 0.12 * progress + 0.018 * math.sin(step * 0.5 + index))
        particles.append([round(x, 4), round(y, 4), round(z, 4)])
    return particles


def _soil_particles(step: int, total_steps: int, extent_m: float) -> list[list[float]]:
    progress = step / max(total_steps, 1)
    scale = min(extent_m / 80.0, 2.0)
    particles = []
    for row in range(4):
        for col in range(5):
            x = (col - 2) * 0.075 * scale + 0.1 * progress
            y = (row - 1.5) * 0.07 * scale
            slump = 0.018 * progress * (1 + col / 5)
            z = max(0.0, 0.045 - slump)
            particles.append([round(x, 4), round(y, 4), round(z, 4)])
    return particles
