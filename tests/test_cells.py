from datetime import UTC, datetime

import pytest

from earth_replica.cells import CellState, LocalGenesisCell


def test_cell_state_exports_postgis_row_with_wkt_point():
    cell = CellState(
        h3_index="872830828ffffff",
        resolution=7,
        latitude=37.7749,
        longitude=-122.4194,
        observed_at=datetime(2026, 5, 8, 18, 30, tzinfo=UTC),
        fidelity="observed",
        properties={"temperature_c": 16.2, "source": "example-sensor"},
    )

    row = cell.to_postgis_row()

    assert row == {
        "h3_index": "872830828ffffff",
        "resolution": 7,
        "center_wkt": "POINT(-122.4194 37.7749)",
        "observed_at": "2026-05-08T18:30:00+00:00",
        "fidelity": "observed",
        "properties": {"temperature_c": 16.2, "source": "example-sensor"},
    }


def test_cell_state_rejects_out_of_range_coordinates():
    with pytest.raises(ValueError, match="latitude"):
        CellState(
            h3_index="872830828ffffff",
            resolution=7,
            latitude=91.0,
            longitude=0.0,
            observed_at=datetime(2026, 5, 8, tzinfo=UTC),
            fidelity="observed",
        )


def test_cell_state_requires_timezone_aware_observation_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        CellState(
            h3_index="872830828ffffff",
            resolution=7,
            latitude=37.7749,
            longitude=-122.4194,
            observed_at=datetime(2026, 5, 8),
            fidelity="observed",
        )


def test_local_genesis_cell_uses_h3_cell_as_bounded_simulation_origin():
    cell = CellState(
        h3_index="872830828ffffff",
        resolution=7,
        latitude=37.7749,
        longitude=-122.4194,
        observed_at=datetime(2026, 5, 8, 18, 30, tzinfo=UTC),
        fidelity="interactive",
        elevation_m=12.5,
    )
    local = LocalGenesisCell.from_cell_state(cell, extent_m=250.0)

    assert local.h3_index == "872830828ffffff"
    assert local.origin_latitude == 37.7749
    assert local.origin_longitude == -122.4194
    assert local.origin_elevation_m == 12.5
    assert local.extent_m == 250.0
    assert local.genesis_origin == (0.0, 0.0, 12.5)
