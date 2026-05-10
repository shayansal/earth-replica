"""HTML rendering for local preview simulation frames."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from earth_replica.surface import known_surface_records


def load_preview_frames(frames_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in frames_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    if not records:
        raise ValueError(f"No preview frames found in {frames_path}")
    return records


def render_preview_html(
    frames_path: Path,
    output_path: Path,
    terrain_path: Path | None = None,
    physics_path: Path | None = None,
) -> Path:
    frames = load_preview_frames(frames_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame_json = json.dumps(frames, separators=(",", ":")).replace("</", "<\\/")
    surface_json = json.dumps(known_surface_records(), separators=(",", ":")).replace(
        "</",
        "<\\/",
    )
    terrain_json = "null"
    if terrain_path is not None:
        terrain_json = terrain_path.read_text(encoding="utf-8").replace("</", "<\\/")
    physics_json = "null"
    if physics_path is not None:
        physics_json = physics_path.read_text(encoding="utf-8").replace("</", "<\\/")
    output_path.write_text(
        _HTML_TEMPLATE.replace("__FRAMES_JSON__", frame_json).replace(
            "__SURFACE_SAMPLES_JSON__",
            surface_json,
        ).replace("__TERRAIN_TILE_JSON__", terrain_json).replace(
            "__PHYSICS_FRAMES_JSON__",
            physics_json,
        ),
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
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.183.2/examples/jsm/",
      "topojson-client": "https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/+esm"
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
      <p class="subtitle">Satellite global shell with WGS84/real-meter data and camera-activated Genesis physics tiles.</p>
    </div>
    <div class="stats">
      <div class="stat"><span>Earth Radius</span><strong id="earthRadius">6,371,008.8 m</strong></div>
      <div class="stat"><span>H3 Cell</span><strong id="h3Cell">-</strong></div>
      <div class="stat"><span>Time</span><strong id="timeValue">0.000s</strong></div>
      <div class="stat"><span>Bodies</span><strong id="bodyCount">0</strong></div>
      <div class="stat"><span>Surface</span><strong id="surfaceStatus">Loading land/water</strong></div>
      <div class="stat"><span>Mode</span><strong id="modeValue">Global shell</strong></div>
      <div class="stat"><span>Terrain exaggeration</span><strong id="terrainScale">25,000x globe</strong></div>
      <div class="stat"><span>Vertical display</span><strong id="verticalScale">1x local mesh</strong></div>
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
  <script id="surface-samples-data" type="application/json">__SURFACE_SAMPLES_JSON__</script>
  <script id="terrain-tile-data" type="application/json">__TERRAIN_TILE_JSON__</script>
  <script id="physics-frames-data" type="application/json">__PHYSICS_FRAMES_JSON__</script>
  <script type="module">
    import * as THREE from "three";
    import { OrbitControls } from "three/addons/controls/OrbitControls.js";
    import { feature } from "topojson-client";

    const frames = JSON.parse(document.getElementById("frames-data").textContent);
    const surfaceSamples = JSON.parse(document.getElementById("surface-samples-data").textContent);
    const terrainTile = JSON.parse(document.getElementById("terrain-tile-data").textContent);
    const physicsFrames = JSON.parse(document.getElementById("physics-frames-data").textContent);
    const canvas = document.getElementById("scene");
    const slider = document.getElementById("frameSlider");
    const playButton = document.getElementById("playButton");
    const frameLabel = document.getElementById("frameLabel");
    const h3Cell = document.getElementById("h3Cell");
    const timeValue = document.getElementById("timeValue");
    const bodyCount = document.getElementById("bodyCount");
    const earthRadius = document.getElementById("earthRadius");
    const surfaceStatus = document.getElementById("surfaceStatus");
    const modeValue = document.getElementById("modeValue");
    const terrainScale = document.getElementById("terrainScale");
    const verticalScale = document.getElementById("verticalScale");
    const legend = document.getElementById("legend");
    const colors = [0x55d6be, 0x8fb7ff, 0xffcf66, 0xff8f8f, 0xc6a6ff];
    const renderEarthRadius = 3.2;
    const altitudeExaggeration = 120000;
    const terrainExaggeration = 25000;
    const localVerticalExaggeration = 1;
    const localPhysicsEnterDistance = 8.8;
    const localPhysicsExitDistance = 14;
    const physicalContextStartDistance = 22;
    const physicalContextFullDistance = 7.2;
    const localContextPatchRadius = renderEarthRadius * 1.022;
    const satelliteTextureUrl = "world.200407.3x5400x2700.jpg";
    const satelliteTextureCredit = "NASA Blue Marble satellite";
    const renderModeLabels = {
      global: "Global shell",
      regional: "Regional stream",
      "physical-transition": "Physical transition",
      "local-physics": "Local physics",
    };
    let frameIndex = 0;
    let playing = true;
    let activeRenderMode = "global";
    let satelliteTextureLoaded = false;
    let physicalContextBlend = 0;
    let satelliteTextureCanvas = null;
    let satelliteTextureContext = null;
    let localContextGrid = [];

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
    const earthTexture = createBaseEarthTexture();
    const earthMaterial = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      map: earthTexture,
      roughness: 0.82,
      metalness: 0.02,
      emissive: 0x061622,
      emissiveIntensity: 0.16,
    });
    const earth = new THREE.Mesh(earthGeometry, earthMaterial);
    scene.add(earth);

    const grid = new THREE.Group();
    addLatitudeLines(grid);
    addLongitudeLines(grid);
    scene.add(grid);
    const coastlineGroup = new THREE.Group();
    scene.add(coastlineGroup);

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
    const surfaceGroup = new THREE.Group();
    scene.add(surfaceGroup);
    const surfaceMeshes = [];
    const terrainGroup = new THREE.Group();
    scene.add(terrainGroup);
    let terrainMesh = null;
    const localTerrainGroup = new THREE.Group();
    scene.add(localTerrainGroup);
    const localPhysicsBubble = new THREE.Group();
    scene.add(localPhysicsBubble);
    const physicsGroup = new THREE.Group();
    scene.add(physicsGroup);
    const waterParticleMeshes = [];
    const soilParticleMeshes = [];
    let localWaterMesh = null;
    let localSoilMesh = null;
    let localVegetationGroup = null;

    slider.max = Math.max(0, frames.length - 1);
    loadLandWaterTexture();
    addKnownSurfaceSamples();
    buildTerrainMesh();
    buildLocalTerrainMesh();
    buildLocalPhysicsBubble();
    buildPhysicsParticles();
    if (terrainTile && !isGlobalTerrainTile()) {
      enableLocalTerrainMode();
    }
    if (terrainTile && isGlobalTerrainTile()) {
      enableGlobalTerrainMode();
    }

    function createBaseEarthTexture() {
      const textureCanvas = document.createElement("canvas");
      textureCanvas.width = 2048;
      textureCanvas.height = 1024;
      const ctx = textureCanvas.getContext("2d");
      const oceanGradient = ctx.createLinearGradient(0, 0, 0, textureCanvas.height);
      oceanGradient.addColorStop(0, "#123b68");
      oceanGradient.addColorStop(0.48, "#0e5d8a");
      oceanGradient.addColorStop(1, "#08223c");
      ctx.fillStyle = oceanGradient;
      ctx.fillRect(0, 0, textureCanvas.width, textureCanvas.height);
      drawBathymetryBands(ctx, textureCanvas.width, textureCanvas.height);
      const texture = new THREE.CanvasTexture(textureCanvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = 8;
      texture.userData.canvas = textureCanvas;
      texture.userData.context = ctx;
      return texture;
    }

    function drawBathymetryBands(ctx, width, height) {
      ctx.save();
      ctx.globalAlpha = 0.22;
      ctx.strokeStyle = "#57a7d8";
      ctx.lineWidth = 1;
      for (let lat = -75; lat <= 75; lat += 15) {
        const y = latitudeToTextureY(lat, height);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.restore();
    }

    async function loadLandWaterTexture() {
      try {
        const response = await fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json");
        if (!response.ok) {
          throw new Error(`land fetch failed: ${response.status}`);
        }
        const topology = await response.json();
        const land = feature(topology, topology.objects.land);
        drawLandTexture(land);
        surfaceStatus.textContent = "Natural Earth 110m";
      } catch (error) {
        console.warn("Land/water layer failed to load", error);
        surfaceStatus.textContent = "Ocean fallback";
      }
    }

    function drawLandTexture(land) {
      const textureCanvas = earthTexture.userData.canvas;
      const ctx = earthTexture.userData.context;
      ctx.save();
      ctx.fillStyle = "#4b7f55";
      ctx.strokeStyle = "#7fcf86";
      ctx.lineWidth = 1.5;
      const geometries = land.type === "FeatureCollection"
        ? land.features.map((item) => item.geometry)
        : [land.geometry];
      geometries.forEach((geometry) => drawGeoJsonGeometry(ctx, geometry, textureCanvas.width, textureCanvas.height));
      ctx.restore();
      earthTexture.needsUpdate = true;
      addCoastlineLines(land);
    }

    function drawGeoJsonGeometry(ctx, geometry, width, height) {
      if (!geometry) return;
      if (geometry.type === "Polygon") {
        drawPolygon(ctx, geometry.coordinates, width, height);
      }
      if (geometry.type === "MultiPolygon") {
        geometry.coordinates.forEach((polygon) => drawPolygon(ctx, polygon, width, height));
      }
    }

    function drawPolygon(ctx, rings, width, height) {
      ctx.beginPath();
      rings.forEach((ring) => {
        ring.forEach(([lon, lat], index) => {
          const x = longitudeToTextureX(lon, width);
          const y = latitudeToTextureY(lat, height);
          if (index === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.closePath();
      });
      ctx.fill("evenodd");
      ctx.stroke();
    }

    function longitudeToTextureX(longitude, width) {
      return ((longitude + 180) / 360) * width;
    }

    function latitudeToTextureY(latitude, height) {
      return ((90 - latitude) / 180) * height;
    }

    function addCoastlineLines(land) {
      const material = new THREE.LineBasicMaterial({
        color: 0x9ce78f,
        transparent: true,
        opacity: 0.48,
      });
      const geometries = land.type === "FeatureCollection"
        ? land.features.map((item) => item.geometry)
        : [land.geometry];
      geometries.forEach((geometry) => {
        if (geometry?.type === "Polygon") addPolygonLines(geometry.coordinates, material);
        if (geometry?.type === "MultiPolygon") {
          geometry.coordinates.forEach((polygon) => addPolygonLines(polygon, material));
        }
      });
    }

    function addPolygonLines(rings, material) {
      rings.forEach((ring) => {
        const points = ring
          .filter((_, index) => index % 2 === 0)
          .map(([lon, lat]) => latLonToVector(lat, lon, renderEarthRadius * 1.006));
        if (points.length < 2) return;
        const line = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(points),
          material.clone()
        );
        coastlineGroup.add(line);
      });
    }

    function addKnownSurfaceSamples() {
      surfaceSamples.forEach((sample) => {
        const isWater = sample.surface_type === "water";
        const color = isWater ? 0x66b7ff : sample.elevation_m < 0 ? 0xffcf66 : 0xd8f27a;
        const radius = isWater ? 0.052 : 0.06;
        const marker = new THREE.Mesh(
          new THREE.SphereGeometry(radius, 20, 14),
          new THREE.MeshStandardMaterial({
            color,
            emissive: color,
            emissiveIntensity: 0.62,
          })
        );
        marker.position.copy(latLonToVector(
          sample.latitude,
          sample.longitude,
          radiusForSurfaceElevation(sample.elevation_m)
        ));
        surfaceGroup.add(marker);
        surfaceMeshes.push({ marker, sample });
      });
    }

    function buildTerrainMesh() {
      if (!terrainTile?.grid) {
        return;
      }
      if (isGlobalTerrainTile()) {
        buildGlobalTerrainMesh();
        return;
      }
      const { latitudes, longitudes, elevation_rows_m: elevations } = terrainTile.grid;
      const positions = [];
      const colors = [];
      const indices = [];
      const color = new THREE.Color();

      latitudes.forEach((latitude, latIndex) => {
        longitudes.forEach((longitude, lonIndex) => {
          const elevation = elevations[latIndex][lonIndex];
          const point = latLonToVector(
            latitude,
            longitude,
            radiusForTerrainElevation(elevation)
          );
          positions.push(point.x, point.y, point.z);
          color.set(terrainColor(elevation));
          colors.push(color.r, color.g, color.b);
        });
      });

      const width = longitudes.length;
      for (let latIndex = 0; latIndex < latitudes.length - 1; latIndex += 1) {
        for (let lonIndex = 0; lonIndex < longitudes.length - 1; lonIndex += 1) {
          const a = latIndex * width + lonIndex;
          const b = a + 1;
          const c = (latIndex + 1) * width + lonIndex;
          const d = c + 1;
          indices.push(a, c, b, b, c, d);
        }
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(positions, 3)
      );
      geometry.setAttribute(
        "color",
        new THREE.Float32BufferAttribute(colors, 3)
      );
      geometry.setIndex(indices);
      geometry.computeVertexNormals();

      terrainMesh = new THREE.Mesh(
        geometry,
        new THREE.MeshStandardMaterial({
          vertexColors: true,
          roughness: 0.92,
          metalness: 0.0,
          transparent: !isGlobalTerrainTile(),
          opacity: isGlobalTerrainTile() ? 1 : 0.86,
          side: THREE.DoubleSide,
        })
      );
      terrainGroup.add(terrainMesh);

      const outline = makeLine(
        [
          latLonToVector(latitudes[0], longitudes[0], renderEarthRadius * 1.012),
          latLonToVector(latitudes[0], longitudes[longitudes.length - 1], renderEarthRadius * 1.012),
          latLonToVector(latitudes[latitudes.length - 1], longitudes[longitudes.length - 1], renderEarthRadius * 1.012),
          latLonToVector(latitudes[latitudes.length - 1], longitudes[0], renderEarthRadius * 1.012),
          latLonToVector(latitudes[0], longitudes[0], renderEarthRadius * 1.012),
        ],
        0xffcf66,
        0.85
      );
      terrainGroup.add(outline);
    }

    function buildGlobalTerrainMesh() {
      const { longitude_count: longitudeCount, latitude_count: latitudeCount } = terrainTile.grid;
      const widthSegments = Math.max(48, Math.min(longitudeCount - 1, 240));
      const heightSegments = Math.max(24, Math.min(latitudeCount - 1, 120));
      const { colorTexture, displacementTexture } = createGlobalTerrainTextures();
      const geometry = new THREE.SphereGeometry(renderEarthRadius, widthSegments, heightSegments);
      terrainMesh = new THREE.Mesh(
        geometry,
        new THREE.MeshStandardMaterial({
          map: colorTexture,
          displacementMap: displacementTexture,
          displacementScale: 0.18,
          displacementBias: -0.07,
          bumpMap: displacementTexture,
          bumpScale: 0.045,
          roughness: 0.9,
          metalness: 0,
        })
      );
      loadSatelliteTexture(terrainMesh.material);
      terrainGroup.add(terrainMesh);
    }

    function createGlobalTerrainTextures() {
      const { latitudes, longitudes, elevation_rows_m: elevations } = terrainTile.grid;
      const colorCanvas = document.createElement("canvas");
      colorCanvas.width = longitudes.length;
      colorCanvas.height = latitudes.length;
      const displacementCanvas = document.createElement("canvas");
      displacementCanvas.width = colorCanvas.width;
      displacementCanvas.height = colorCanvas.height;
      const colorCtx = colorCanvas.getContext("2d");
      const displacementCtx = displacementCanvas.getContext("2d");
      const elevationSpan = Math.max(
        terrainTile.max_elevation_m - terrainTile.min_elevation_m,
        1
      );

      latitudes.forEach((_, latIndex) => {
        const y = latitudes.length - latIndex - 1;
        longitudes.forEach((_, lonIndex) => {
          const elevation = elevations[latIndex][lonIndex];
          const colorValue = terrainColor(elevation);
          colorCtx.fillStyle = `#${colorValue.toString(16).padStart(6, "0")}`;
          colorCtx.fillRect(lonIndex, y, 1, 1);

          const normalized = Math.round(
            ((elevation - terrainTile.min_elevation_m) / elevationSpan) * 255
          );
          displacementCtx.fillStyle = `rgb(${normalized}, ${normalized}, ${normalized})`;
          displacementCtx.fillRect(lonIndex, y, 1, 1);
        });
      });

      const colorTexture = new THREE.CanvasTexture(colorCanvas);
      colorTexture.colorSpace = THREE.SRGBColorSpace;
      colorTexture.anisotropy = 8;
      colorTexture.wrapS = THREE.RepeatWrapping;
      colorTexture.needsUpdate = true;

      const displacementTexture = new THREE.CanvasTexture(displacementCanvas);
      displacementTexture.wrapS = THREE.RepeatWrapping;
      displacementTexture.needsUpdate = true;
      return { colorTexture, displacementTexture };
    }

    function loadSatelliteTexture(material) {
      const loader = new THREE.TextureLoader();
      loader.load(
        satelliteTextureUrl,
        (texture) => {
          texture.colorSpace = THREE.SRGBColorSpace;
          texture.anisotropy = 8;
          texture.wrapS = THREE.RepeatWrapping;
          texture.needsUpdate = true;
          material.map = texture;
          material.needsUpdate = true;
          satelliteTextureLoaded = true;
          captureSatelliteTexture(texture.image);
          deriveLocalContextFromSatellite();
          applyDerivedLocalContext();
          surfaceStatus.textContent = `${satelliteTextureCredit} + ETOPO relief`;
        },
        undefined,
        () => {
          satelliteTextureLoaded = false;
        }
      );
    }

    function captureSatelliteTexture(image) {
      const width = image.naturalWidth || image.width;
      const height = image.naturalHeight || image.height;
      if (!width || !height) {
        return;
      }
      satelliteTextureCanvas = document.createElement("canvas");
      satelliteTextureCanvas.width = width;
      satelliteTextureCanvas.height = height;
      satelliteTextureContext = satelliteTextureCanvas.getContext("2d", { willReadFrequently: true });
      satelliteTextureContext.drawImage(image, 0, 0, width, height);
    }

    function nearestElevation(latitude, longitude) {
      const { latitudes, longitudes, elevation_rows_m: elevations } = terrainTile.grid;
      const latIndex = nearestIndex(latitudes, latitude);
      const lonIndex = nearestIndex(longitudes, longitude);
      return elevations[latIndex][lonIndex];
    }

    function nearestIndex(values, value) {
      if (values.length < 2) {
        return 0;
      }
      const first = values[0];
      const last = values[values.length - 1];
      const fraction = (value - first) / (last - first);
      const index = Math.round(fraction * (values.length - 1));
      return Math.max(0, Math.min(values.length - 1, index));
    }

    function buildLocalTerrainMesh() {
      if (!terrainTile?.grid || isGlobalTerrainTile()) {
        return;
      }
      const { latitudes, longitudes, elevation_rows_m: elevations } = terrainTile.grid;
      const centerLat = (terrainTile.bounds.min_latitude + terrainTile.bounds.max_latitude) / 2;
      const centerLon = (terrainTile.bounds.min_longitude + terrainTile.bounds.max_longitude) / 2;
      const earthRadiusM = frames[0].planet.mean_radius_m;
      const eastings = longitudes.map((longitude) => (
        THREE.MathUtils.degToRad(longitude - centerLon) *
        earthRadiusM *
        Math.cos(THREE.MathUtils.degToRad(centerLat))
      ));
      const northings = latitudes.map((latitude) => (
        THREE.MathUtils.degToRad(latitude - centerLat) * earthRadiusM
      ));
      const spanM = Math.max(
        Math.max(...eastings) - Math.min(...eastings),
        Math.max(...northings) - Math.min(...northings),
        1
      );
      const metersToScene = 7 / spanM;
      const positions = [];
      const colors = [];
      const indices = [];
      const color = new THREE.Color();

      latitudes.forEach((_, latIndex) => {
        longitudes.forEach((_, lonIndex) => {
          const elevation = elevations[latIndex][lonIndex];
          positions.push(
            eastings[lonIndex] * metersToScene,
            elevation * metersToScene * localVerticalExaggeration,
            -northings[latIndex] * metersToScene
          );
          color.set(terrainColor(elevation));
          colors.push(color.r, color.g, color.b);
        });
      });

      const width = longitudes.length;
      for (let latIndex = 0; latIndex < latitudes.length - 1; latIndex += 1) {
        for (let lonIndex = 0; lonIndex < longitudes.length - 1; lonIndex += 1) {
          const a = latIndex * width + lonIndex;
          const b = a + 1;
          const c = (latIndex + 1) * width + lonIndex;
          const d = c + 1;
          indices.push(a, c, b, b, c, d);
        }
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();

      const mesh = new THREE.Mesh(
        geometry,
        new THREE.MeshStandardMaterial({
          vertexColors: true,
          roughness: 0.88,
          metalness: 0,
          side: THREE.DoubleSide,
        })
      );
      localTerrainGroup.add(mesh);

      const waterGeometry = new THREE.PlaneGeometry(
        (Math.max(...eastings) - Math.min(...eastings)) * metersToScene,
        (Math.max(...northings) - Math.min(...northings)) * metersToScene,
        1,
        1
      );
      const water = new THREE.Mesh(
        waterGeometry,
        new THREE.MeshStandardMaterial({
          color: 0x267db8,
          transparent: true,
          opacity: 0.42,
          roughness: 0.6,
          metalness: 0.05,
          side: THREE.DoubleSide,
        })
      );
      water.rotation.x = -Math.PI / 2;
      water.position.y = 0;
      localTerrainGroup.add(water);

      const gridHelper = new THREE.GridHelper(7.4, 12, 0x456070, 0x233644);
      gridHelper.position.y = -0.015;
      localTerrainGroup.add(gridHelper);
      localTerrainGroup.userData = { metersToScene, spanM };
    }

    function buildLocalPhysicsBubble() {
      localSoilMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(9, 9, 64, 64),
        new THREE.MeshStandardMaterial({
          color: 0x7d6244,
          vertexColors: true,
          transparent: true,
          opacity: 0,
          roughness: 0.96,
          metalness: 0,
        })
      );
      applyLocalSoilRelief(localSoilMesh.geometry);
      localSoilMesh.rotation.x = -Math.PI / 2;
      localSoilMesh.position.y = -0.025;
      localPhysicsBubble.add(localSoilMesh);

      localWaterMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(4.8, 3.2, 48, 32),
        new THREE.MeshPhysicalMaterial({
          color: 0x2f9fd2,
          transparent: true,
          opacity: 0,
          roughness: 0.18,
          metalness: 0.02,
          transmission: 0.18,
          clearcoat: 0.65,
          clearcoatRoughness: 0.08,
          side: THREE.DoubleSide,
        })
      );
      localWaterMesh.rotation.x = -Math.PI / 2;
      localWaterMesh.position.set(-0.75, 0.035, 0.15);
      localPhysicsBubble.add(localWaterMesh);

      const ridge = new THREE.Mesh(
        new THREE.BoxGeometry(2.8, 0.16, 0.32),
        new THREE.MeshStandardMaterial({
          color: 0x9d8059,
          roughness: 0.92,
        })
      );
      ridge.position.set(1.25, 0.08, -0.85);
      ridge.rotation.y = -0.28;
      ridge.material.transparent = true;
      ridge.material.opacity = 0;
      localPhysicsBubble.add(ridge);

      const fill = new THREE.HemisphereLight(0xaed8ff, 0x5a4028, 1.2);
      localPhysicsBubble.add(fill);

      localVegetationGroup = new THREE.Group();
      localPhysicsBubble.add(localVegetationGroup);
      deriveLocalContextFromSatellite();
      applyDerivedLocalContext();
      localPhysicsBubble.visible = false;
    }

    function deriveLocalContextFromSatellite() {
      const frame = frames[frameIndex] || frames[0];
      const centerLat = frame?.cell?.center_latitude ?? 0;
      const centerLon = frame?.cell?.center_longitude ?? 0;
      const spanDegrees = 1.4;
      const gridSize = 11;
      const cells = [];
      for (let row = 0; row < gridSize; row += 1) {
        for (let col = 0; col < gridSize; col += 1) {
          const u = (col / (gridSize - 1)) * 2 - 1;
          const v = (row / (gridSize - 1)) * 2 - 1;
          const latitude = clamp(centerLat + v * spanDegrees * 0.5, -89.8, 89.8);
          const longitude = wrapLongitude(centerLon + u * spanDegrees * 0.5);
          const elevation = terrainTile?.grid ? nearestElevation(latitude, longitude) : 0;
          const pixel = sampleSatellitePixel(latitude, longitude);
          cells.push({
            x: u * 4.2,
            z: -v * 4.2,
            latitude,
            longitude,
            elevation,
            type: classifySatelliteContext(pixel, elevation),
          });
        }
      }
      localContextGrid = cells;
      return cells;
    }

    function sampleSatellitePixel(latitude, longitude) {
      if (!satelliteTextureContext || !satelliteTextureCanvas) {
        const fallbackColor = new THREE.Color(terrainColor(terrainTile?.grid ? nearestElevation(latitude, longitude) : 0));
        return {
          r: Math.round(fallbackColor.r * 255),
          g: Math.round(fallbackColor.g * 255),
          b: Math.round(fallbackColor.b * 255),
        };
      }
      const x = Math.floor(clamp((longitude + 180) / 360, 0, 0.9999) * satelliteTextureCanvas.width);
      const y = Math.floor(clamp((90 - latitude) / 180, 0, 0.9999) * satelliteTextureCanvas.height);
      const data = satelliteTextureContext.getImageData(x, y, 1, 1).data;
      return { r: data[0], g: data[1], b: data[2] };
    }

    function classifySatelliteContext(pixel, elevation) {
      if (elevation < -1) {
        return "water";
      }
      const brightness = (pixel.r + pixel.g + pixel.b) / 3;
      if (brightness > 205 && pixel.r > 180 && pixel.g > 180) {
        return "snow";
      }
      if (pixel.g > pixel.r * 1.08 && pixel.g > pixel.b * 1.05) {
        return "vegetation";
      }
      if (pixel.r > pixel.g * 1.08 && pixel.r > pixel.b * 1.05) {
        return "soil";
      }
      return elevation > 1800 ? "rock" : "soil";
    }

    function applyDerivedLocalContext() {
      if (!localSoilMesh || !localContextGrid.length) {
        return;
      }
      const color = new THREE.Color();
      const colors = [];
      const positions = localSoilMesh.geometry.attributes.position;
      for (let index = 0; index < positions.count; index += 1) {
        const x = positions.getX(index);
        const y = positions.getY(index);
        const cell = nearestLocalContextCell(x, y);
        color.set(localContextColor(cell.type, cell.elevation));
        colors.push(color.r, color.g, color.b);
      }
      localSoilMesh.geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      localSoilMesh.material.vertexColors = true;
      localSoilMesh.material.needsUpdate = true;
      buildVegetationFromContext();
      updateLocalWaterFromContext();
    }

    function nearestLocalContextCell(x, z) {
      let nearest = localContextGrid[0];
      let nearestDistance = Number.POSITIVE_INFINITY;
      localContextGrid.forEach((cell) => {
        const distance = ((cell.x - x) ** 2) + ((cell.z - z) ** 2);
        if (distance < nearestDistance) {
          nearest = cell;
          nearestDistance = distance;
        }
      });
      return nearest;
    }

    function localContextColor(type, elevation) {
      if (type === "water") return 0x315f64;
      if (type === "vegetation") return elevation > 700 ? 0x3f6f35 : 0x2f7d42;
      if (type === "snow") return 0xdde6dc;
      if (type === "rock") return 0x7f7b70;
      return 0x78684f;
    }

    function buildVegetationFromContext() {
      if (!localVegetationGroup) {
        return;
      }
      localVegetationGroup.clear();
      const vegetationCells = localContextGrid
        .filter((cell, index) => cell.type === "vegetation" && index % 2 === 0)
        .slice(0, 80);
      const vegetationMaterial = new THREE.MeshStandardMaterial({
        color: 0x2f7d42,
        roughness: 0.9,
        transparent: true,
        opacity: physicalContextBlend * 0.72,
      });
      vegetationCells.forEach((cell, index) => {
        const patch = new THREE.Mesh(
          new THREE.SphereGeometry(0.055 + (index % 3) * 0.01, 8, 6),
          vegetationMaterial.clone()
        );
        patch.scale.set(1, 0.22, 1);
        patch.position.set(cell.x + ((index % 3) - 1) * 0.035, 0.035, cell.z);
        localVegetationGroup.add(patch);
      });
    }

    function updateLocalWaterFromContext() {
      if (!localWaterMesh || !localContextGrid.length) {
        return;
      }
      const waterFraction = localContextGrid.filter((cell) => cell.type === "water").length / localContextGrid.length;
      const scale = clamp(0.55 + waterFraction * 1.35, 0.55, 1.45);
      localWaterMesh.scale.set(scale, scale, 1);
      localWaterMesh.visible = waterFraction > 0.04;
    }

    function applyLocalSoilRelief(geometry) {
      const positions = geometry.attributes.position;
      for (let index = 0; index < positions.count; index += 1) {
        const x = positions.getX(index);
        const y = positions.getY(index);
        const ridge = 0.14 * Math.exp(-(((x - 1.0) ** 2) + ((y + 0.8) ** 2)) / 2.6);
        const bank = -0.05 * Math.exp(-(((x + 0.8) ** 2) + ((y - 0.2) ** 2)) / 1.9);
        const ripple = 0.025 * Math.sin(x * 2.1) * Math.cos(y * 1.7);
        positions.setZ(index, ridge + bank + ripple);
      }
      positions.needsUpdate = true;
      geometry.computeVertexNormals();
    }

    function animateLocalPhysicsBubble(elapsedS) {
      if (!localWaterMesh) {
        return;
      }
      const positions = localWaterMesh.geometry.attributes.position;
      for (let index = 0; index < positions.count; index += 1) {
        const x = positions.getX(index);
        const y = positions.getY(index);
        const waveA = 0.024 * Math.sin((x * 2.3) + (elapsedS * 1.4));
        const waveB = 0.014 * Math.cos((y * 3.1) - (elapsedS * 1.9));
        positions.setZ(index, waveA + waveB);
      }
      positions.needsUpdate = true;
      localWaterMesh.geometry.computeVertexNormals();
      localWaterMesh.position.y = 0.035 + 0.012 * Math.sin(elapsedS * 1.1);
      localWaterMesh.rotation.z = 0.01 * Math.sin(elapsedS * 0.7);
    }

    function buildPhysicsParticles() {
      if (!physicsFrames?.frames?.length) {
        physicsGroup.visible = false;
        return;
      }
      const maxWater = Math.max(...physicsFrames.frames.map((frame) => frame.water_particles?.length || 0));
      const maxSoil = Math.max(...physicsFrames.frames.map((frame) => frame.soil_particles?.length || 0));
      for (let index = 0; index < maxWater; index += 1) {
        const mesh = new THREE.Mesh(
          new THREE.SphereGeometry(0.018, 14, 10),
          new THREE.MeshStandardMaterial({
            color: 0x4cc9ff,
            emissive: 0x126c94,
            emissiveIntensity: 0.5,
            transparent: true,
            opacity: 0.82,
          })
        );
        waterParticleMeshes.push(mesh);
        physicsGroup.add(mesh);
      }
      for (let index = 0; index < maxSoil; index += 1) {
        const mesh = new THREE.Mesh(
          new THREE.SphereGeometry(0.016, 12, 8),
          new THREE.MeshStandardMaterial({
            color: 0xa9855a,
            roughness: 0.95,
            metalness: 0,
          })
        );
        soilParticleMeshes.push(mesh);
        physicsGroup.add(mesh);
      }
    }

    function updatePhysicsFrame(index, cell) {
      if (!physicsFrames?.frames?.length) {
        return;
      }
      const physicsFrame = physicsFrames.frames[index % physicsFrames.frames.length];
      updateParticleMeshes(waterParticleMeshes, physicsFrame.water_particles || [], cell);
      updateParticleMeshes(soilParticleMeshes, physicsFrame.soil_particles || [], cell);
    }

    function updateParticleMeshes(meshes, particles, cell) {
      meshes.forEach((mesh, index) => {
        const particle = particles[index];
        mesh.visible = Boolean(particle);
        if (!particle) {
          return;
        }
        if (activeRenderMode === "local-physics") {
          mesh.position.copy(particleToLocalVector(particle));
          return;
        }
        const latLon = localMetersToLatLon(cell, particle);
        mesh.position.copy(latLonToVector(
          latLon.latitude,
          latLon.longitude,
          radiusForAltitude(particle[2] + 30)
        ));
      });
    }

    function particleToLocalVector(particle) {
      const localScale = 8;
      return new THREE.Vector3(
        particle[0] * localScale,
        particle[2] * localScale + 0.05,
        -particle[1] * localScale
      );
    }

    function physicsLegendRows() {
      if (!physicsFrames?.frames?.length) {
        return "";
      }
      const firstFrame = physicsFrames.frames[0];
      return `<div class="body-row"><strong style="color:#4cc9ff">Genesis water/soil shard</strong>${physicsFrames.frames.length} frames · ${firstFrame.water_particles.length} SPH water particles · ${firstFrame.soil_particles.length} MPM soil particles · exascale shard contract</div>`;
    }

    function isGlobalTerrainTile() {
      if (!terrainTile?.bounds) {
        return false;
      }
      return (
        terrainTile.bounds.min_latitude <= -89.5 &&
        terrainTile.bounds.max_latitude >= 88 &&
        terrainTile.bounds.min_longitude <= -179.5 &&
        terrainTile.bounds.max_longitude >= 178
      );
    }

    function enableGlobalTerrainMode() {
      activeRenderMode = "global";
      earth.visible = false;
      atmosphere.visible = true;
      grid.visible = false;
      coastlineGroup.visible = false;
      terrainGroup.visible = true;
      surfaceGroup.visible = false;
      bodyGroup.visible = false;
      cellMarker.visible = false;
      localTerrainGroup.visible = false;
      localPhysicsBubble.visible = false;
      physicsGroup.visible = true;
      playing = true;
      playButton.textContent = "Pause";
      modeValue.textContent = renderModeLabels.global;
      terrainScale.textContent = "ETOPO visual relief";
      verticalScale.textContent = "global bump map";
      controls.autoRotate = true;
      controls.minDistance = 7.2;
      controls.maxDistance = 80;
      controls.target.set(0, 0, 0);
      camera.position.set(0, 2.8, 48);
      camera.lookAt(controls.target);
      controls.update();
    }

    function enableLocalTerrainMode() {
      activeRenderMode = "local-physics";
      earth.visible = false;
      atmosphere.visible = false;
      grid.visible = false;
      coastlineGroup.visible = false;
      terrainGroup.visible = false;
      surfaceGroup.visible = false;
      bodyGroup.visible = false;
      cellMarker.visible = false;
      localTerrainGroup.visible = true;
      localPhysicsBubble.visible = false;
      physicsGroup.visible = false;
      playing = false;
      playButton.textContent = "Inspect";
      modeValue.textContent = renderModeLabels["local-physics"];
      terrainScale.textContent = "25,000x globe";
      verticalScale.textContent = "1x local mesh";
      controls.autoRotate = false;
      controls.minDistance = 1.6;
      controls.maxDistance = 14;
      controls.target.set(0, 0, 0);
      camera.position.set(0, 3.4, 6.6);
      camera.lookAt(controls.target);
    }

    function setRenderMode(mode) {
      if (!renderModeLabels[mode]) {
        return;
      }
      activeRenderMode = mode;
      modeValue.textContent = renderModeLabels[activeRenderMode];
      if (mode === "local-physics") {
        setPhysicalContextBlend(1);
        controls.autoRotate = false;
        controls.minDistance = 2.5;
        controls.maxDistance = 18;
        return;
      }
      if (mode === "regional") {
        setPhysicalContextBlend(0.45);
        controls.autoRotate = false;
        return;
      }
      setPhysicalContextBlend(0);
    }

    function updateRenderModeFromCamera() {
      if (!physicsFrames?.frames?.length || !isGlobalTerrainTile()) {
        return;
      }
      updatePhysicalContextBlend();
    }

    function updatePhysicalContextBlend() {
      const distance = camera.position.distanceTo(controls.target);
      const normalized = clamp(
        (physicalContextStartDistance - distance) /
          (physicalContextStartDistance - physicalContextFullDistance),
        0,
        1
      );
      setPhysicalContextBlend(smoothstep(normalized));
    }

    function setPhysicalContextBlend(blend) {
      physicalContextBlend = clamp(blend, 0, 1);
      const hasLocalContext = physicalContextBlend > 0.025;
      terrainGroup.visible = Boolean(terrainTile?.grid);
      localTerrainGroup.visible = false;
      localPhysicsBubble.visible = hasLocalContext;
      physicsGroup.visible = Boolean(physicsFrames?.frames?.length);
      bodyGroup.visible = false;
      cellMarker.visible = false;
      surfaceGroup.visible = false;
      grid.visible = false;
      coastlineGroup.visible = false;
      earth.visible = !terrainTile?.grid;
      atmosphere.visible = true;

      if (terrainMesh?.material) {
        terrainMesh.material.transparent = physicalContextBlend > 0;
        terrainMesh.material.opacity = 1 - physicalContextBlend * 0.88;
        terrainMesh.material.needsUpdate = true;
      }
      if (atmosphere.material) {
        atmosphere.material.opacity = 0.12 * (1 - physicalContextBlend * 0.85);
      }
      setGroupOpacity(localPhysicsBubble, physicalContextBlend);
      if (localWaterMesh?.material) {
        localWaterMesh.material.opacity = 0.55 * physicalContextBlend;
      }
      positionPhysicalContextOnGlobe();

      if (physicalContextBlend >= 0.92) {
        activeRenderMode = "local-physics";
        modeValue.textContent = renderModeLabels["local-physics"];
        terrainScale.textContent = "data-derived physics";
        verticalScale.textContent = "Genesis local";
      } else if (physicalContextBlend > 0.06) {
        activeRenderMode = "physical-transition";
        modeValue.textContent = renderModeLabels["physical-transition"];
        terrainScale.textContent = "satellite + ETOPO context";
        verticalScale.textContent = `${Math.round(physicalContextBlend * 100)}% physical`;
      } else {
        activeRenderMode = "global";
        modeValue.textContent = renderModeLabels.global;
        terrainScale.textContent = "ETOPO visual relief";
        verticalScale.textContent = "global bump map";
      }
    }

    function positionPhysicalContextOnGlobe() {
      const frame = frames[frameIndex] || frames[0];
      const cell = frame?.cell;
      if (!cell) {
        return;
      }
      const center = latLonToVector(
        cell.center_latitude,
        cell.center_longitude,
        localContextPatchRadius + physicalContextBlend * 0.018
      );
      const basis = makeSurfaceBasis(cell.center_latitude, cell.center_longitude);
      localPhysicsBubble.position.copy(center);
      localPhysicsBubble.quaternion.setFromRotationMatrix(basis);
      const patchScale = 0.018 + physicalContextBlend * 0.105;
      localPhysicsBubble.scale.setScalar(patchScale);
      controls.target.lerp(center, physicalContextBlend * 0.08);
    }

    function makeSurfaceBasis(latitude, longitude) {
      const lat = THREE.MathUtils.degToRad(latitude);
      const lon = THREE.MathUtils.degToRad(longitude);
      const up = new THREE.Vector3(
        Math.cos(lat) * Math.cos(lon),
        Math.sin(lat),
        Math.cos(lat) * Math.sin(lon)
      ).normalize();
      const east = new THREE.Vector3(-Math.sin(lon), 0, Math.cos(lon)).normalize();
      const north = new THREE.Vector3().crossVectors(up, east).normalize();
      return new THREE.Matrix4().makeBasis(east, up, north);
    }

    function setGroupOpacity(group, opacity) {
      group.traverse((child) => {
        if (!child.material) {
          return;
        }
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        materials.forEach((material) => {
          material.transparent = true;
          material.opacity = opacity;
          material.needsUpdate = true;
        });
      });
    }

    function clamp(value, min, max) {
      return Math.min(max, Math.max(min, value));
    }

    function smoothstep(value) {
      const x = clamp(value, 0, 1);
      return x * x * (3 - 2 * x);
    }

    function wrapLongitude(longitude) {
      return ((((longitude + 180) % 360) + 360) % 360) - 180;
    }

    function terrainColor(elevation) {
      if (elevation < -4000) return 0x072e63;
      if (elevation < -1000) return 0x135c9c;
      if (elevation < 0) return 0x4ca8d8;
      if (elevation < 50) return 0x71a85c;
      if (elevation < 500) return 0x9da85f;
      if (elevation < 2000) return 0xc8b06d;
      return 0xf2e4bb;
    }

    function focusTerrainTile() {
      if (!terrainTile?.bounds) {
        return;
      }
      const centerLat = (terrainTile.bounds.min_latitude + terrainTile.bounds.max_latitude) / 2;
      const centerLon = (terrainTile.bounds.min_longitude + terrainTile.bounds.max_longitude) / 2;
      const target = latLonToVector(centerLat, centerLon, renderEarthRadius);
      controls.target.copy(target.clone().multiplyScalar(0.7));
      camera.position.copy(
        target.clone().normalize().multiplyScalar(renderEarthRadius + 2.4)
      );
      camera.position.y += 0.6;
      camera.lookAt(controls.target);
    }

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

    function radiusForSurfaceElevation(elevationM) {
      const earth = frames[0].planet;
      const sign = elevationM < 0 ? 0.28 : 1;
      return renderEarthRadius + (elevationM / earth.mean_radius_m) * renderEarthRadius * altitudeExaggeration * sign;
    }

    function radiusForTerrainElevation(elevationM) {
      const earth = frames[0].planet;
      return renderEarthRadius + (elevationM / earth.mean_radius_m) * renderEarthRadius * terrainExaggeration;
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
      updatePhysicsFrame(index, cell);

      h3Cell.textContent = frame.h3_index;
      earthRadius.textContent = `${Number(frame.planet.mean_radius_m).toLocaleString(undefined, { maximumFractionDigits: 1 })} m`;
      timeValue.textContent = `${Number(frame.time_s).toFixed(3)}s`;
      bodyCount.textContent = terrainTile ? "hidden" : String(names.length);
      if (terrainTile) {
        surfaceStatus.textContent = satelliteTextureLoaded
          ? `${satelliteTextureCredit} + ETOPO relief`
          : `${terrainTile.source.name}`;
      }
      frameLabel.textContent = `Frame ${index + 1} / ${frames.length}`;
      slider.value = String(index);
      if (activeRenderMode === "local-physics") {
        legend.innerHTML = `<div class="body-row"><strong style="color:#4cc9ff">Active local physical context</strong>Genesis water and soil particles are rendered over a satellite/ETOPO-derived tile with water, soil, rock, snow, and vegetation classes inferred from the focused Earth location</div>${physicsLegendRows()}`;
        return;
      }
      if (activeRenderMode === "physical-transition") {
        legend.innerHTML = `<div class="body-row"><strong style="color:#4cc9ff">Continuous physical context</strong>the satellite globe remains visible while the local Genesis layer fades in from ${Math.round(physicalContextBlend * 100)}% context strength; material classes are inferred from satellite color and ETOPO elevation</div>${physicsLegendRows()}`;
        return;
      }
      if (terrainTile && isGlobalTerrainTile()) {
        legend.innerHTML = `<div class="body-row"><strong style="color:#b9c36b">Global ETOPO relief mesh</strong>${terrainTile.samples.length.toLocaleString()} ETOPO samples · ${terrainTile.grid.latitude_count} x ${terrainTile.grid.longitude_count} planet grid · ${Number(terrainTile.min_elevation_m).toFixed(1)}m to ${Number(terrainTile.max_elevation_m).toFixed(1)}m · stored 1:1 meters</div><div class="body-row"><strong style="color:#66b7ff">Full Earth view</strong>the globe mesh is built from global elevation and bathymetry samples; vertical relief is exaggerated only for visibility in the browser preview</div>${physicsLegendRows()}<div class="body-row"><strong style="color:#edf5ff">Source</strong>${terrainTile.source.name} · ${terrainTile.source.vertical_datum} · ${terrainTile.source.confidence}</div>`;
        return;
      }
      if (terrainTile) {
        legend.innerHTML = `<div class="body-row"><strong style="color:#b9c36b">Fetched terrain mesh</strong>${terrainTile.samples.length} ETOPO samples · ${terrainTile.grid.latitude_count} x ${terrainTile.grid.longitude_count} grid · ${Number(terrainTile.min_elevation_m).toFixed(1)}m to ${Number(terrainTile.max_elevation_m).toFixed(1)}m · stored 1:1 meters · local mesh vertical display ${localVerticalExaggeration}x</div><div class="body-row"><strong style="color:#66b7ff">Sea level water plane</strong>water surface is rendered at 0m; negative terrain values are bathymetry below that plane</div>${physicsLegendRows()}<div class="body-row"><strong style="color:#edf5ff">Source</strong>${terrainTile.source.name} · ${terrainTile.source.vertical_datum} · ${terrainTile.source.confidence}</div>`;
        return;
      }

      legend.innerHTML = names.map((name, i) => {
        const body = frame.bodies[name];
        const color = `#${colors[i % colors.length].toString(16).padStart(6, "0")}`;
        return `<div class="body-row"><strong style="color:${color}">${name}</strong>east ${body.position_m[0].toFixed(2)}m · north ${body.position_m[1].toFixed(2)}m · altitude ${body.position_m[2].toFixed(2)}m · vz ${body.velocity_m_s[2].toFixed(2)}m/s</div>`;
      }).join("") + physicsLegendRows() + surfaceSamples.map((sample) => {
        const color = sample.surface_type === "water" ? "#66b7ff" : sample.elevation_m < 0 ? "#ffcf66" : "#d8f27a";
        const depth = sample.depth_m > 0 ? `depth ${Number(sample.depth_m).toLocaleString()}m` : `elevation ${Number(sample.elevation_m).toLocaleString()}m`;
        return `<div class="body-row"><strong style="color:${color}">${sample.name}</strong>${depth} · ${sample.source.confidence} · ${sample.source.name}</div>`;
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
      updateRenderModeFromCamera();
      animateLocalPhysicsBubble(performance.now() / 1000);
      renderer.render(scene, camera);
      window.setTimeout(() => window.requestAnimationFrame(tick), 66);
    }

    resize();
    drawFrame(frameIndex);
    if (!terrainTile) {
      focusTerrainTile();
    }
    tick();
  </script>
</body>
</html>
"""
