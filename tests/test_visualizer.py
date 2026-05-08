import json

from earth_replica.visualizer import render_preview_html


def test_render_preview_html_embeds_frames_and_canvas(tmp_path):
    frames_path = tmp_path / "preview.jsonl"
    output_path = tmp_path / "preview.html"
    frames = [
        {
            "h3_index": "872830828ffffff",
            "planet": {
                "mean_radius_m": 6371008.8,
                "mean_circumference_m": 40030228.88412017,
            },
            "cell": {
                "center_latitude": 37.7749,
                "center_longitude": -122.4194,
            },
            "step": 1,
            "time_s": 0.033,
            "bodies": {
                "probe": {
                    "position_m": [0.0, 0.0, 2.9],
                    "velocity_m_s": [0.0, 0.0, -0.3],
                }
            },
        },
        {
            "h3_index": "872830828ffffff",
            "planet": {
                "mean_radius_m": 6371008.8,
                "mean_circumference_m": 40030228.88412017,
            },
            "cell": {
                "center_latitude": 37.7749,
                "center_longitude": -122.4194,
            },
            "step": 2,
            "time_s": 0.066,
            "bodies": {
                "probe": {
                    "position_m": [0.0, 0.0, 2.7],
                    "velocity_m_s": [0.0, 0.0, -0.6],
                }
            },
        },
    ]
    frames_path.write_text(
        "\n".join(json.dumps(frame) for frame in frames),
        encoding="utf-8",
    )

    returned_path = render_preview_html(frames_path, output_path)
    html = returned_path.read_text(encoding="utf-8")

    assert returned_path == output_path
    assert "Earth Replica Preview" in html
    assert '<canvas id="scene"' in html
    assert 'from "three"' in html
    assert 'from "topojson-client"' in html
    assert "land-110m.json" in html
    assert "6,371,008.8 m" in html
    assert "Challenger Deep" in html
    assert "Mount Everest" in html
    assert '<script id="frames-data" type="application/json">' in html
    assert '<script id="surface-samples-data" type="application/json">' in html
    assert "872830828ffffff" in html
    assert "probe" in html
