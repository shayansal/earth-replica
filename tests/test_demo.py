from earth_replica.demo import build_demo_preview_simulation


def test_demo_preview_simulation_uses_bounded_h3_cell():
    simulation = build_demo_preview_simulation(steps_extent_m=125.0)

    frames = simulation.run(steps=1)

    assert simulation.local_cell.h3_index == "872830828ffffff"
    assert simulation.local_cell.extent_m == 125.0
    assert "probe" in frames[0].bodies
