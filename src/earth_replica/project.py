"""Project metadata and initial simulation scope for Earth Replica."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationDomain:
    """A bounded physical domain that Earth Replica can model over time."""

    name: str
    purpose: str
    fidelity: str
    primary_source: str


@dataclass(frozen=True)
class EarthReplicaProject:
    """Public mission and initial technical boundary for the project."""

    name: str
    slug: str
    description: str
    goal: str
    is_open_source: bool
    initial_domains: tuple[SimulationDomain, ...]


PROJECT = EarthReplicaProject(
    name="Earth Replica",
    slug="earth-replica",
    description=(
        "An open source initiative to create a global 4D live illustration of "
        "Earth where physical laws apply and live planetary state is simulated "
        "through sensor inputs, IoT devices, and edge devices."
    ),
    goal=(
        "Enable people to experience being anywhere on Earth from anywhere, "
        "at any time, and simulate physical scenarios with progressively "
        "validated fidelity."
    ),
    is_open_source=True,
    initial_domains=(
        SimulationDomain(
            name="rigid bodies",
            purpose="Represent terrain, structures, vehicles, agents, and tools.",
            fidelity="interactive",
            primary_source="Genesis rigid-body solvers",
        ),
        SimulationDomain(
            name="fluids",
            purpose="Prototype water, gases, and local flow interactions.",
            fidelity="progressive",
            primary_source="Genesis SPH and Stable Fluid solvers",
        ),
        SimulationDomain(
            name="deformables",
            purpose="Model cloth, vegetation, soft bodies, and selected materials.",
            fidelity="progressive",
            primary_source="Genesis FEM, MPM, and PBD solvers",
        ),
        SimulationDomain(
            name="sensor-driven state",
            purpose="Assimilate observations from public datasets, IoT, and edge devices.",
            fidelity="data-dependent",
            primary_source="Validated live and historical sensor feeds",
        ),
        SimulationDomain(
            name="rendered observation",
            purpose="Create visual, spatial, and sensor-like views into simulated places.",
            fidelity="perceptual",
            primary_source="Genesis rendering plus geospatial assets",
        ),
    ),
)
