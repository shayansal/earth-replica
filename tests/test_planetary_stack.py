from datetime import UTC, datetime

from earth_replica.planetary_stack import (
    AccessPolicy,
    CoupledSolverPlan,
    DatasetSource,
    DistributedExecutionPlan,
    PlanetaryDataFabric,
    PlanetaryTile,
    TileStore,
    TileStreamManifest,
    ValidationObservation,
    ValidationReport,
)
from earth_replica.runtime import ShardSpec


def test_data_fabric_registers_sources_with_provenance():
    fabric = PlanetaryDataFabric()
    source = DatasetSource(
        name="NOAA ETOPO 2022",
        domain="terrain",
        uri="https://example.test/etopo",
        resolution="15 arc-second",
        license="public domain",
        update_cadence="static",
    )

    fabric.register(source)

    assert fabric.require("NOAA ETOPO 2022").domain == "terrain"
    assert fabric.catalog_record()["sources"][0]["provenance_required"] is True


def test_tile_store_persists_state_with_neighbors_and_material_layers(tmp_path):
    tile = PlanetaryTile(
        spec=ShardSpec(h3_index="872830828ffffff", resolution=7, extent_m=250.0),
        material_layers=("water", "soil", "terrain"),
        neighbor_shards=("h3:7:87283082affffff",),
        state={
            "elevation_m": 12.0,
            "water_depth_m": 0.3,
            "soil_moisture": 0.41,
        },
    )
    store = TileStore(tmp_path)

    path = store.write(tile)
    loaded = store.read(tile.spec.shard_id)

    assert path.exists()
    assert loaded.spec.shard_id == tile.spec.shard_id
    assert loaded.state["water_depth_m"] == 0.3
    assert loaded.neighbor_shards == ("h3:7:87283082affffff",)


def test_coupled_solver_plan_routes_domains_to_engines():
    plan = CoupledSolverPlan.local_default()

    assert plan.engine_for("water") == "Genesis SPH"
    assert plan.engine_for("soil") == "Genesis MPM"
    assert plan.engine_for("atmosphere") == "external CFD"
    assert plan.to_record()["coupling"] == "tile-boundary exchange"


def test_distributed_execution_plan_scales_down_to_local_node():
    plan = DistributedExecutionPlan.local_exascale_shape(max_active_shards=2)

    assert plan.mode == "local"
    assert plan.backends == ("local-process",)
    assert plan.scheduler_features["checkpoint_restart"] is True
    assert plan.to_record()["max_active_shards"] == 2


def test_stream_manifest_describes_lod_and_visible_physics_layers():
    manifest = TileStreamManifest(
        root_uri="artifacts/streams",
        lod_levels=(0, 1, 2),
        visible_layers=("terrain", "water", "soil"),
        time_window_s=30.0,
    )

    assert manifest.to_record()["streaming"] == "progressive"
    assert manifest.to_record()["visible_layers"] == ["terrain", "water", "soil"]


def test_validation_report_scores_prediction_against_observation():
    report = ValidationReport(
        shard_id="h3:7:872830828ffffff",
        observed_at=datetime(2026, 5, 8, tzinfo=UTC),
        observations=(
            ValidationObservation(
                quantity="water_depth_m",
                predicted=0.42,
                observed=0.5,
                tolerance=0.1,
                source="sensor:test",
            ),
        ),
    )

    assert report.passed is True
    assert report.to_record()["metrics"][0]["absolute_error"] == 0.08


def test_access_policy_blocks_sensitive_live_sensor_export_by_default():
    policy = AccessPolicy.public_open_source_default()

    assert policy.can_export("terrain") is True
    assert policy.can_export("live_private_sensor") is False
    assert "privacy_review" in policy.to_record()["required_reviews"]
