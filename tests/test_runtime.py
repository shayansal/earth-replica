import json

from earth_replica.runtime import (
    ArtifactStore,
    LocalShardScheduler,
    ShardJob,
    ShardResult,
    ShardSpec,
    WorkerCapabilities,
)


class RecordingWorker:
    capabilities = WorkerCapabilities(
        backend="recording",
        materials=("water", "soil"),
        distributed_ready=True,
        genesis_powered=False,
    )

    def run(self, job: ShardJob, store: ArtifactStore) -> ShardResult:
        artifact = store.write_json(
            job,
            "frames.json",
            {
                "schema": "earth-replica/shard-frame-stream/v1",
                "shard_id": job.spec.shard_id,
                "frames": [
                    {
                        "step": 1,
                        "time_s": job.time_step_s,
                        "water_particles": [[0.0, 0.0, 0.12]],
                        "soil_particles": [[0.0, 0.0, 0.0]],
                    }
                ],
            },
        )
        return ShardResult(
            job_id=job.job_id,
            shard_id=job.spec.shard_id,
            backend=self.capabilities.backend,
            steps_completed=job.steps,
            artifacts=(artifact,),
            metrics={"frames": 1},
        )


def test_shard_spec_uses_stable_global_cell_identity():
    spec = ShardSpec(h3_index="872830828ffffff", resolution=7, extent_m=250.0)

    assert spec.shard_id == "h3:7:872830828ffffff"
    assert spec.to_record()["execution_scope"] == "tile"


def test_local_scheduler_runs_jobs_and_writes_browser_artifact(tmp_path):
    store = ArtifactStore(tmp_path)
    scheduler = LocalShardScheduler(worker=RecordingWorker(), store=store, node_id="local-dev")
    job = ShardJob(
        spec=ShardSpec(h3_index="872830828ffffff", resolution=7, extent_m=250.0),
        steps=4,
        time_step_s=1.0 / 60.0,
    )

    scheduler.submit(job)
    results = scheduler.run_pending()

    assert len(results) == 1
    assert results[0].backend == "recording"
    assert results[0].artifacts[0].kind == "frames"
    payload = json.loads(results[0].artifacts[0].path.read_text(encoding="utf-8"))
    assert payload["schema"] == "earth-replica/shard-frame-stream/v1"
    assert payload["frames"][0]["water_particles"] == [[0.0, 0.0, 0.12]]


def test_scheduler_manifest_is_exascale_ready(tmp_path):
    store = ArtifactStore(tmp_path)
    scheduler = LocalShardScheduler(worker=RecordingWorker(), store=store, node_id="local-dev")
    job = ShardJob(
        spec=ShardSpec(h3_index="872830828ffffff", resolution=7, extent_m=250.0),
        steps=2,
    )

    result = scheduler.run(job)
    manifest = result.to_record()

    assert manifest["job_id"] == job.job_id
    assert manifest["shard_id"] == "h3:7:872830828ffffff"
    assert manifest["scheduler"]["node_id"] == "local-dev"
    assert manifest["artifacts"][0]["media_type"] == "application/json"
