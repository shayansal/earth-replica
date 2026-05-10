"""Water rendering and provenance contract for the globe preview."""

from __future__ import annotations


def water_render_manifest() -> dict[str, object]:
    """Return render parameters for global and local water animation."""

    return {
        "schema": "earth-replica/water-rendering/v1",
        "global_motion": {
            "mode": "rendered_shader",
            "wave_speed_mps": 0.35,
            "shimmer_period_s": 5.5,
            "highlight_opacity": 0.18,
            "provenance": {
                "state": "rendered",
                "source": "semantic water polygons plus procedural wave render",
                "confidence": 0.68,
            },
        },
        "local_physics": {
            "activation_zoom": 10.0,
            "fallback_mode": "shader_only",
            "provenance_without_frames": {
                "state": "rendered",
                "source": "procedural close-range water shader",
                "confidence": 0.52,
            },
            "provenance_with_frames": {
                "state": "simulated",
                "source": "Genesis local water frames",
                "confidence": 0.72,
            },
        },
        "recommended_repositories": [
            {
                "name": "jbouny/fft-ocean",
                "purpose": "Open MIT reference for FFT-style ocean displacement and normal-map water.",
                "url": "https://github.com/jbouny/fft-ocean",
            },
            {
                "name": "mrdoob/three.js",
                "purpose": "Reference WebGL water and ocean shader examples for close-range rendering.",
                "url": "https://github.com/mrdoob/three.js",
            },
            {
                "name": "CesiumGS/cesium",
                "purpose": "Future Cesium material path for time-dynamic water in 3D Tiles previews.",
                "url": "https://github.com/CesiumGS/cesium",
            },
        ],
    }
