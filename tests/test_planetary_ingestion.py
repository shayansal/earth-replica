from earth_replica.planetary_ingestion import (
    IngestionDataset,
    PlanetaryIngestionPlan,
    build_whole_planet_ingestion_plan,
)


def test_whole_planet_ingestion_plan_covers_required_open_sources():
    plan = build_whole_planet_ingestion_plan(h3_resolution=7)
    record = plan.to_record()

    dataset_names = {dataset["name"] for dataset in record["datasets"]}
    assert "OSM planet PBF" in dataset_names
    assert "Overture Maps Buildings" in dataset_names
    assert "Overture Maps Transportation" in dataset_names
    assert "NOAA ETOPO 2022" in dataset_names
    assert "GEBCO global bathymetry" in dataset_names
    assert record["planetary_scope"]["coverage"] == "whole_planet"
    assert record["tiling"]["index"] == "H3"
    assert record["tiling"]["resolution"] == 7
    assert record["execution"]["mode"] == "manifest_only_until_worker_pool_configured"
    assert record["provenance_policy"]["separate_observed_inferred_simulated_rendered"] is True


def test_plan_rejects_dataset_without_global_or_regional_scope():
    try:
        PlanetaryIngestionPlan(
            h3_resolution=7,
            datasets=(
                IngestionDataset(
                    name="tiny demo",
                    domain="buildings",
                    source_uri="file://demo",
                    scope="single_tile",
                    license="demo",
                    ingestion_mode="fixture",
                ),
            ),
        )
    except ValueError as error:
        assert "whole_planet or regional" in str(error)
    else:
        raise AssertionError("PlanetaryIngestionPlan accepted single-tile dataset scope")
