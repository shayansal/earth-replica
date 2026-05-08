"""Exascale-shaped simulation shard runtime.

The local runtime intentionally uses the same job/result contracts that a
future cluster scheduler will use. A laptop becomes one worker node, not a
special case.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class ShardSpec:
    """A bounded piece of Earth that can be scheduled independently."""

    h3_index: str
    resolution: int
    extent_m: float
    execution_scope: str = "tile"
    fidelity: str = "local-physics-preview"

    def __post_init__(self) -> None:
        if not self.h3_index:
            raise ValueError("h3_index is required")
        if not 0 <= self.resolution <= 15:
            raise ValueError("resolution must be between 0 and 15")
        if self.extent_m <= 0:
            raise ValueError("extent_m must be positive")

    @property
    def shard_id(self) -> str:
        return f"h3:{self.resolution}:{self.h3_index}"

    def to_record(self) -> dict[str, object]:
        return {
            "shard_id": self.shard_id,
            "h3_index": self.h3_index,
            "resolution": self.resolution,
            "extent_m": self.extent_m,
            "execution_scope": self.execution_scope,
            "fidelity": self.fidelity,
        }


@dataclass(frozen=True)
class ShardJob:
    """A simulation request for one shard."""

    spec: ShardSpec
    steps: int
    time_step_s: float = 1.0 / 60.0
    materials: tuple[str, ...] = ("water", "soil")
    backend: str = "genesis-local"
    job_id: str = field(default_factory=lambda: f"job-{uuid4().hex[:12]}")

    def __post_init__(self) -> None:
        if self.steps < 0:
            raise ValueError("steps must be non-negative")
        if self.time_step_s <= 0:
            raise ValueError("time_step_s must be positive")
        if not self.materials:
            raise ValueError("materials must not be empty")

    def to_record(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "backend": self.backend,
            "steps": self.steps,
            "time_step_s": self.time_step_s,
            "materials": list(self.materials),
            "spec": self.spec.to_record(),
        }


@dataclass(frozen=True)
class WorkerCapabilities:
    """Advertised worker features for local, cloud, or HPC schedulers."""

    backend: str
    materials: tuple[str, ...]
    distributed_ready: bool
    genesis_powered: bool

    def to_record(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "materials": list(self.materials),
            "distributed_ready": self.distributed_ready,
            "genesis_powered": self.genesis_powered,
        }


@dataclass(frozen=True)
class ShardArtifact:
    """A file emitted by a shard worker."""

    kind: str
    path: Path
    media_type: str = "application/json"

    def to_record(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "path": str(self.path),
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class ShardResult:
    """A completed shard simulation result."""

    job_id: str
    shard_id: str
    backend: str
    steps_completed: int
    artifacts: tuple[ShardArtifact, ...]
    metrics: dict[str, object] = field(default_factory=dict)
    scheduler: dict[str, object] = field(default_factory=dict)

    def with_scheduler(self, node_id: str) -> ShardResult:
        return ShardResult(
            job_id=self.job_id,
            shard_id=self.shard_id,
            backend=self.backend,
            steps_completed=self.steps_completed,
            artifacts=self.artifacts,
            metrics=self.metrics,
            scheduler={"node_id": node_id, "mode": "local"},
        )

    def to_record(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "shard_id": self.shard_id,
            "backend": self.backend,
            "steps_completed": self.steps_completed,
            "artifacts": [artifact.to_record() for artifact in self.artifacts],
            "metrics": self.metrics,
            "scheduler": self.scheduler,
        }


class ShardWorker(Protocol):
    """Worker contract shared by local and future distributed backends."""

    capabilities: WorkerCapabilities

    def run(self, job: ShardJob, store: ArtifactStore) -> ShardResult:
        """Run a shard job and write artifacts through the store."""


class ArtifactStore:
    """Filesystem artifact store with stable per-job directories."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job: ShardJob) -> Path:
        path = self.root / job.spec.shard_id.replace(":", "_") / job.job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(
        self,
        job: ShardJob,
        filename: str,
        payload: dict[str, object],
        *,
        kind: str = "frames",
    ) -> ShardArtifact:
        path = self.job_dir(job) / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ShardArtifact(kind=kind, path=path)


class LocalShardScheduler:
    """Single-process scheduler that preserves distributed job semantics."""

    def __init__(self, worker: ShardWorker, store: ArtifactStore, node_id: str = "local") -> None:
        self.worker = worker
        self.store = store
        self.node_id = node_id
        self._pending: deque[ShardJob] = deque()

    def submit(self, job: ShardJob) -> None:
        self._pending.append(job)

    def run(self, job: ShardJob) -> ShardResult:
        result = self.worker.run(job, self.store).with_scheduler(self.node_id)
        manifest = self.store.write_json(
            job,
            "manifest.json",
            result.to_record(),
            kind="manifest",
        )
        return ShardResult(
            job_id=result.job_id,
            shard_id=result.shard_id,
            backend=result.backend,
            steps_completed=result.steps_completed,
            artifacts=(*result.artifacts, manifest),
            metrics=result.metrics,
            scheduler=result.scheduler,
        )

    def run_pending(self) -> list[ShardResult]:
        results: list[ShardResult] = []
        while self._pending:
            results.append(self.run(self._pending.popleft()))
        return results
