import json

from earth_replica.cli import run_preview


def test_run_preview_writes_jsonl_frames(tmp_path):
    output_path = tmp_path / "preview.jsonl"

    returned_path = run_preview(steps=3, output_path=output_path)

    records = [
        json.loads(line)
        for line in returned_path.read_text(encoding="utf-8").splitlines()
    ]
    assert returned_path == output_path
    assert [record["step"] for record in records] == [1, 2, 3]
    assert all(record["h3_index"] == "872830828ffffff" for record in records)


def test_run_preview_can_write_html_viewer(tmp_path):
    output_path = tmp_path / "preview.jsonl"
    html_path = tmp_path / "preview.html"

    run_preview(steps=3, output_path=output_path, html_path=html_path)

    assert output_path.exists()
    assert html_path.exists()
    assert "Earth Replica Preview" in html_path.read_text(encoding="utf-8")


def test_run_preview_can_embed_physics_artifact(tmp_path):
    output_path = tmp_path / "preview.jsonl"
    html_path = tmp_path / "preview.html"
    physics_path = tmp_path / "physics.json"
    physics_path.write_text(
        json.dumps(
            {
                "schema": "earth-replica/genesis-water-soil-frames/v1",
                "engine": {"name": "Genesis"},
                "frames": [
                    {
                        "step": 1,
                        "time_s": 0.01,
                        "water_particles": [[0.0, 0.0, 0.1]],
                        "soil_particles": [[0.0, 0.0, 0.0]],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    run_preview(
        steps=3,
        output_path=output_path,
        html_path=html_path,
        physics_path=physics_path,
    )

    assert "Genesis water/soil shard" in html_path.read_text(encoding="utf-8")
