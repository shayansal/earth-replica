"""HTML rendering for local preview simulation frames."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_preview_frames(frames_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in frames_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    if not records:
        raise ValueError(f"No preview frames found in {frames_path}")
    return records


def render_preview_html(frames_path: Path, output_path: Path) -> Path:
    frames = load_preview_frames(frames_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame_json = json.dumps(frames, separators=(",", ":")).replace("</", "<\\/")
    output_path.write_text(
        _HTML_TEMPLATE.replace("__FRAMES_JSON__", frame_json),
        encoding="utf-8",
    )
    return output_path


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Earth Replica Preview</title>
  <script type="importmap">
  {
    "imports": {
      "three": "https://cdn.jsdelivr.net/npm/three@0.183.2/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/"
    }
  }
  </script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #05070b;
      --glass: rgba(9, 14, 22, 0.74);
      --glass-strong: rgba(13, 21, 32, 0.9);
      --text: #edf5ff;
      --muted: #9babbd;
      --line: rgba(145, 164, 185, 0.24);
      --accent: #55d6be;
      --accent-2: #8fb7ff;
      --warning: #ffcf66;
    }

    * { box-sizing: border-box; }

    html,
    body {
      margin: 0;
      width: 100%;
      min-height: 100%;
      overflow: hidden;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    #scene {
      display: block;
      width: 100vw;
      height: 100vh;
      background: radial-gradient(circle at 50% 50%, #0d1521 0, #05070b 68%);
    }

    .hud {
      position: fixed;
      top: 20px;
      left: 20px;
      right: 20px;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      pointer-events: none;
    }

    .title-block {
      max-width: min(520px, calc(100vw - 40px));
    }

    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.08;
      font-weight: 740;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }

    .stats {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
      max-width: min(660px, 52vw);
    }

    .stat,
    .legend,
    .controls {
      border: 1px solid var(--line);
      background: var(--glass);
      backdrop-filter: blur(14px);
      box-shadow: 0 18px 46px rgba(0, 0, 0, 0.28);
    }

    .stat {
      min-width: 118px;
      padding: 10px 12px;
      border-radius: 8px;
    }

    .stat span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .stat strong {
      display: block;
      margin-top: 4px;
      font-size: 15px;
      font-weight: 680;
      white-space: nowrap;
    }

    .legend {
      position: fixed;
      right: 20px;
      bottom: 92px;
      width: min(360px, calc(100vw - 40px));
      max-height: min(280px, calc(100vh - 220px));
      overflow: auto;
      border-radius: 8px;
      padding: 10px;
    }

    .body-row {
      padding: 10px;
      border-bottom: 1px solid rgba(145, 164, 185, 0.18);
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }

    .body-row:last-child { border-bottom: 0; }

    .body-row strong {
      display: block;
      margin-bottom: 2px;
      color: var(--text);
      font-size: 14px;
    }

    .controls {
      position: fixed;
      left: 20px;
      right: 20px;
      bottom: 20px;
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 14px;
      align-items: center;
      padding: 12px;
      border-radius: 8px;
      background: var(--glass-strong);
    }

    button {
      min-width: 86px;
      height: 38px;
      border: 1px solid #3b5266;
      border-radius: 8px;
      background: #0d2531;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      cursor: pointer;
    }

    button:hover { border-color: var(--accent); }

    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }

    .frame-label {
      color: var(--muted);
      font-size: 13px;
      min-width: 112px;
      text-align: right;
    }

    @media (max-width: 760px) {
      .hud {
        top: 12px;
        left: 12px;
        right: 12px;
        display: block;
      }

      h1 { font-size: 22px; }

      .subtitle { font-size: 13px; }

      .stats {
        max-width: none;
        justify-content: flex-start;
        margin-top: 12px;
      }

      .stat {
        min-width: calc(50% - 5px);
        flex: 1 1 calc(50% - 5px);
      }

      .legend {
        left: 12px;
        right: 12px;
        bottom: 86px;
        width: auto;
        max-height: 150px;
      }

      .controls {
        left: 12px;
        right: 12px;
        bottom: 12px;
        grid-template-columns: auto 1fr;
      }

      .frame-label {
        grid-column: 1 / -1;
        text-align: left;
        min-width: 0;
      }
    }
  </style>
</head>
<body>
  <canvas id="scene" width="1280" height="720" aria-label="Earth Replica 4D Three.js preview"></canvas>

  <section class="hud">
    <div class="title-block">
      <h1>Earth Replica Preview</h1>
      <p class="subtitle">Three.js 4D playback: WGS84 Earth scale with time-indexed local simulation state.</p>
    </div>
    <div class="stats">
      <div class="stat"><span>Earth Radius</span><strong id="earthRadius">6,371,008.8 m</strong></div>
      <div class="stat"><span>H3 Cell</span><strong id="h3Cell">-</strong></div>
      <div class="stat"><span>Time</span><strong id="timeValue">0.000s</strong></div>
      <div class="stat"><span>Bodies</span><strong id="bodyCount">0</strong></div>
      <div class="stat"><span>Render Scale</span><strong id="renderScale">1 unit = Earth radius / 3.2</strong></div>
    </div>
  </section>

  <section id="legend" class="legend" aria-live="polite"></section>

  <section class="controls">
    <button id="playButton" type="button">Pause</button>
    <input id="frameSlider" type="range" min="0" value="0" step="1">
    <span id="frameLabel" class="frame-label">Frame 1</span>
  </section>

  <script id="frames-data" type="application/json">__FRAMES_JSON__</script>
  <script type="module">
    import * as THREE from "three";
    import { OrbitControls } from "three/addons/controls/OrbitControls.js";

    const frames = JSON.parse(document.getElementById("frames-data").textContent);
    const canvas = document.getElementById("scene");
    const slider = document.getElementById("frameSlider");
    const playButton = document.getElementById("playButton");
    const frameLabel = document.getElementById("frameLabel");
    const h3Cell = document.getElementById("h3Cell");
    const timeValue = document.getElementById("timeValue");
    const bodyCount = document.getElementById("bodyCount");
    const earthRadius = document.getElementById("earthRadius");
    const legend = document.getElementById("legend");
    const colors = [0x55d6be, 0x8fb7ff, 0xffcf66, 0xff8f8f, 0xc6a6ff];
    const renderEarthRadius = 3.2;
    const altitudeExaggeration = 120000;
    let frameIndex = 0;
    let playing = true;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05070b);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 1000);
    camera.position.set(0, 0.6, 10.8);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 4.6;
    controls.maxDistance = 14;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.18;

    const ambient = new THREE.AmbientLight(0x6d87a9, 1.4);
    scene.add(ambient);

    const sun = new THREE.DirectionalLight(0xffffff, 2.8);
    sun.position.set(5, 4, 7);
    scene.add(sun);

    const rim = new THREE.DirectionalLight(0x55d6be, 1.1);
    rim.position.set(-4, -1, -3);
    scene.add(rim);

    const earthGeometry = new THREE.SphereGeometry(renderEarthRadius, 96, 48);
    const earthMaterial = new THREE.MeshStandardMaterial({
      color: 0x1a5e84,
      roughness: 0.82,
      metalness: 0.02,
      emissive: 0x061622,
      emissiveIntensity: 0.38,
    });
    const earth = new THREE.Mesh(earthGeometry, earthMaterial);
    scene.add(earth);

    const grid = new THREE.Group();
    addLatitudeLines(grid);
    addLongitudeLines(grid);
    scene.add(grid);

    const atmosphere = new THREE.Mesh(
      new THREE.SphereGeometry(renderEarthRadius * 1.018, 96, 48),
      new THREE.MeshBasicMaterial({
        color: 0x6fb8ff,
        transparent: true,
        opacity: 0.12,
        side: THREE.BackSide,
      })
    );
    scene.add(atmosphere);

    const cellMarker = new THREE.Mesh(
      new THREE.SphereGeometry(0.055, 24, 16),
      new THREE.MeshStandardMaterial({
        color: 0xffcf66,
        emissive: 0xffb03a,
        emissiveIntensity: 1.2,
      })
    );
    scene.add(cellMarker);

    const bodyGroup = new THREE.Group();
    scene.add(bodyGroup);
    const bodyMeshes = new Map();
    const trailMeshes = new Map();

    slider.max = Math.max(0, frames.length - 1);

    function addLatitudeLines(group) {
      for (let lat = -60; lat <= 60; lat += 30) {
        const points = [];
        for (let lon = -180; lon <= 180; lon += 4) {
          points.push(latLonToVector(lat, lon, renderEarthRadius * 1.002));
        }
        group.add(makeLine(points, 0x24465c, 0.52));
      }
    }

    function addLongitudeLines(group) {
      for (let lon = -180; lon < 180; lon += 30) {
        const points = [];
        for (let lat = -88; lat <= 88; lat += 4) {
          points.push(latLonToVector(lat, lon, renderEarthRadius * 1.003));
        }
        group.add(makeLine(points, 0x24465c, 0.5));
      }
    }

    function makeLine(points, color, opacity) {
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity,
      });
      return new THREE.Line(geometry, material);
    }

    function latLonToVector(latitude, longitude, radius) {
      const lat = THREE.MathUtils.degToRad(latitude);
      const lon = THREE.MathUtils.degToRad(longitude);
      const cosLat = Math.cos(lat);
      return new THREE.Vector3(
        radius * cosLat * Math.sin(lon),
        radius * Math.sin(lat),
        radius * cosLat * Math.cos(lon)
      );
    }

    function localMetersToLatLon(cell, position) {
      const earth = frames[0].planet;
      const radius = earth.mean_radius_m;
      const centerLat = cell.center_latitude;
      const centerLon = cell.center_longitude;
      const eastM = position[0];
      const northM = position[1];
      const latDelta = THREE.MathUtils.radToDeg(northM / radius);
      const lonDelta = THREE.MathUtils.radToDeg(
        eastM / (radius * Math.cos(THREE.MathUtils.degToRad(centerLat)))
      );
      return {
        latitude: centerLat + latDelta,
        longitude: centerLon + lonDelta,
      };
    }

    function radiusForAltitude(altitudeM) {
      const earth = frames[0].planet;
      return renderEarthRadius + (altitudeM / earth.mean_radius_m) * renderEarthRadius * altitudeExaggeration;
    }

    function ensureBodyMesh(name, color) {
      if (bodyMeshes.has(name)) {
        return bodyMeshes.get(name);
      }
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.045, 24, 16),
        new THREE.MeshStandardMaterial({
          color,
          emissive: color,
          emissiveIntensity: 0.48,
        })
      );
      bodyGroup.add(mesh);
      bodyMeshes.set(name, mesh);
      return mesh;
    }

    function updateTrails(frameNumber, names) {
      const windowStart = Math.max(0, frameNumber - 24);
      names.forEach((name, i) => {
        const color = colors[i % colors.length];
        if (trailMeshes.has(name)) {
          bodyGroup.remove(trailMeshes.get(name));
          trailMeshes.get(name).geometry.dispose();
          trailMeshes.get(name).material.dispose();
        }
        const points = [];
        for (let index = windowStart; index <= frameNumber; index += 1) {
          const frame = frames[index];
          const body = frame.bodies[name];
          if (!body) continue;
          const cell = frame.cell;
          const latLon = localMetersToLatLon(cell, body.position_m);
          points.push(latLonToVector(
            latLon.latitude,
            latLon.longitude,
            radiusForAltitude(body.position_m[2])
          ));
        }
        const trail = makeLine(points, color, 0.72);
        trailMeshes.set(name, trail);
        bodyGroup.add(trail);
      });
    }

    function drawFrame(index) {
      const frame = frames[index];
      const names = Object.keys(frame.bodies).sort();
      const cell = frame.cell;

      cellMarker.position.copy(latLonToVector(
        cell.center_latitude,
        cell.center_longitude,
        renderEarthRadius * 1.01
      ));

      names.forEach((name, i) => {
        const body = frame.bodies[name];
        const latLon = localMetersToLatLon(cell, body.position_m);
        const mesh = ensureBodyMesh(name, colors[i % colors.length]);
        mesh.position.copy(latLonToVector(
          latLon.latitude,
          latLon.longitude,
          radiusForAltitude(body.position_m[2])
        ));
      });

      updateTrails(index, names);

      h3Cell.textContent = frame.h3_index;
      earthRadius.textContent = `${Number(frame.planet.mean_radius_m).toLocaleString(undefined, { maximumFractionDigits: 1 })} m`;
      timeValue.textContent = `${Number(frame.time_s).toFixed(3)}s`;
      bodyCount.textContent = String(names.length);
      frameLabel.textContent = `Frame ${index + 1} / ${frames.length}`;
      slider.value = String(index);
      legend.innerHTML = names.map((name, i) => {
        const body = frame.bodies[name];
        const color = `#${colors[i % colors.length].toString(16).padStart(6, "0")}`;
        return `<div class="body-row"><strong style="color:${color}">${name}</strong>east ${body.position_m[0].toFixed(2)}m · north ${body.position_m[1].toFixed(2)}m · altitude ${body.position_m[2].toFixed(2)}m · vz ${body.velocity_m_s[2].toFixed(2)}m/s</div>`;
      }).join("");
    }

    function resize() {
      const width = window.innerWidth;
      const height = window.innerHeight;
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    }

    slider.addEventListener("input", () => {
      frameIndex = Number(slider.value);
      drawFrame(frameIndex);
    });

    playButton.addEventListener("click", () => {
      playing = !playing;
      playButton.textContent = playing ? "Pause" : "Play";
      controls.autoRotate = playing;
    });

    window.addEventListener("resize", resize);

    function tick() {
      if (playing) {
        frameIndex = (frameIndex + 1) % frames.length;
        drawFrame(frameIndex);
      }
      controls.update();
      renderer.render(scene, camera);
      window.setTimeout(() => window.requestAnimationFrame(tick), 66);
    }

    resize();
    drawFrame(frameIndex);
    tick();
  </script>
</body>
</html>
"""
