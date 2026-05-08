import json

from earth_replica.genesis_worker import GenesisWaterSoilWorker
from earth_replica.runtime import ArtifactStore, ShardJob, ShardSpec


def test_genesis_worker_advertises_water_soil_capabilities():
    worker = GenesisWaterSoilWorker(enable_genesis=False)

    assert worker.capabilities.backend == "genesis-local"
    assert worker.capabilities.genesis_powered is True
    assert "water" in worker.capabilities.materials
    assert "soil" in worker.capabilities.materials


def test_genesis_worker_writes_browser_particle_frames_without_cluster(tmp_path):
    worker = GenesisWaterSoilWorker(enable_genesis=False)
    job = ShardJob(
        spec=ShardSpec(h3_index="872830828ffffff", resolution=7, extent_m=80.0),
        steps=5,
        time_step_s=0.05,
    )

    result = worker.run(job, ArtifactStore(tmp_path))

    assert result.backend == "genesis-local"
    assert result.steps_completed == 5
    payload = json.loads(result.artifacts[0].path.read_text(encoding="utf-8"))
    assert payload["schema"] == "earth-replica/genesis-water-soil-frames/v1"
    assert payload["engine"]["materials"]["water"] == "Genesis SPH.Liquid"
    assert payload["engine"]["materials"]["soil"] == "Genesis MPM.Sand"
    assert payload["frames"][0]["water_particles"]
    assert payload["frames"][0]["soil_particles"]
