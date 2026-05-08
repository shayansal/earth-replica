from earth_replica import PROJECT, SimulationDomain


def test_project_metadata_names_the_public_initiative():
    assert PROJECT.name == "Earth Replica"
    assert PROJECT.slug == "earth-replica"
    assert "global 4D live illustration of Earth" in PROJECT.description
    assert PROJECT.is_open_source is True


def test_project_goal_keeps_global_presence_and_simulation_in_scope():
    assert "experience being anywhere on Earth" in PROJECT.goal
    assert "simulate physical scenarios" in PROJECT.goal


def test_initial_domains_include_genesis_backed_physics_targets():
    domain_names = {domain.name for domain in PROJECT.initial_domains}

    assert {
        "rigid bodies",
        "fluids",
        "deformables",
        "sensor-driven state",
        "rendered observation",
    }.issubset(domain_names)


def test_simulation_domain_records_source_and_fidelity():
    domain = SimulationDomain(
        name="atmospheric flow",
        purpose="Model wind, heat transfer, and weather-adjacent dynamics.",
        fidelity="research",
        primary_source="OpenFOAM or dedicated climate/weather solvers",
    )

    assert domain.name == "atmospheric flow"
    assert domain.fidelity == "research"
    assert "climate" in domain.primary_source
