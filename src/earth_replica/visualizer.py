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
  <style>
    :root {
      color-scheme: dark;
      --bg: #070a0f;
      --panel: #101722;
      --panel-2: #151f2c;
      --text: #e9f0f7;
      --muted: #95a3b5;
      --line: #273445;
      --accent: #55d6be;
      --accent-2: #8fb7ff;
      --ground: #314356;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0;
    }

    .topbar {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.1;
      font-weight: 720;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }

    .stats {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .stat {
      min-width: 112px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
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
      font-weight: 650;
    }

    .viewer {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      overflow: hidden;
    }

    canvas {
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      background: #09101a;
    }

    .controls {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 14px;
      align-items: center;
      padding: 12px;
      border-top: 1px solid var(--line);
      background: var(--panel-2);
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
      min-width: 96px;
      text-align: right;
    }

    .legend {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }

    .body-row {
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }

    .body-row strong {
      display: block;
      margin-bottom: 2px;
      color: var(--text);
      font-size: 14px;
    }
  </style>
</head>
<body>
  <main>
    <section class="topbar">
      <div>
        <h1>Earth Replica Preview</h1>
        <p class="subtitle">Local H3 cell playback from the lightweight preview backend.</p>
      </div>
      <div class="stats">
        <div class="stat"><span>H3 Cell</span><strong id="h3Cell">-</strong></div>
        <div class="stat"><span>Time</span><strong id="timeValue">0.000s</strong></div>
        <div class="stat"><span>Bodies</span><strong id="bodyCount">0</strong></div>
      </div>
    </section>

    <section class="viewer">
      <canvas id="scene" width="1280" height="720" aria-label="Earth Replica local-cell preview"></canvas>
      <div class="controls">
        <button id="playButton" type="button">Pause</button>
        <input id="frameSlider" type="range" min="0" value="0" step="1">
        <span id="frameLabel" class="frame-label">Frame 1</span>
      </div>
    </section>

    <section id="legend" class="legend" aria-live="polite"></section>
  </main>

  <script id="frames-data" type="application/json">__FRAMES_JSON__</script>
  <script>
    const frames = JSON.parse(document.getElementById("frames-data").textContent);
    const canvas = document.getElementById("scene");
    const ctx = canvas.getContext("2d");
    const slider = document.getElementById("frameSlider");
    const playButton = document.getElementById("playButton");
    const frameLabel = document.getElementById("frameLabel");
    const h3Cell = document.getElementById("h3Cell");
    const timeValue = document.getElementById("timeValue");
    const bodyCount = document.getElementById("bodyCount");
    const legend = document.getElementById("legend");
    const colors = ["#55d6be", "#8fb7ff", "#ffcf66", "#ff8f8f", "#c6a6ff"];
    let frameIndex = 0;
    let playing = true;

    slider.max = Math.max(0, frames.length - 1);

    function bounds() {
      const values = [];
      for (const frame of frames) {
        for (const body of Object.values(frame.bodies)) {
          values.push(body.position_m);
        }
      }
      const xs = values.map((p) => p[0]);
      const zs = values.map((p) => p[2]);
      return {
        minX: Math.min(...xs, -4),
        maxX: Math.max(...xs, 4),
        minZ: 0,
        maxZ: Math.max(...zs, 4),
      };
    }

    const world = bounds();

    function scaleX(x) {
      const pad = 96;
      return pad + ((x - world.minX) / (world.maxX - world.minX || 1)) * (canvas.width - pad * 2);
    }

    function scaleZ(z) {
      const groundY = canvas.height - 122;
      const topY = 82;
      return groundY - ((z - world.minZ) / (world.maxZ - world.minZ || 1)) * (groundY - topY);
    }

    function drawGrid() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#09101a";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = "#162333";
      ctx.lineWidth = 1;
      for (let x = 96; x < canvas.width - 64; x += 80) {
        ctx.beginPath();
        ctx.moveTo(x, 68);
        ctx.lineTo(x, canvas.height - 100);
        ctx.stroke();
      }
      for (let y = 100; y < canvas.height - 100; y += 72) {
        ctx.beginPath();
        ctx.moveTo(64, y);
        ctx.lineTo(canvas.width - 64, y);
        ctx.stroke();
      }

      ctx.fillStyle = "#13202c";
      ctx.fillRect(0, canvas.height - 122, canvas.width, 122);
      ctx.fillStyle = "#314356";
      ctx.fillRect(0, canvas.height - 122, canvas.width, 4);
      ctx.fillStyle = "#95a3b5";
      ctx.font = "14px Inter, system-ui, sans-serif";
      ctx.fillText("local Genesis cell side view: x / elevation", 64, 54);
    }

    function drawFrame(index) {
      const frame = frames[index];
      const names = Object.keys(frame.bodies).sort();
      drawGrid();

      names.forEach((name, i) => {
        const body = frame.bodies[name];
        const x = scaleX(body.position_m[0]);
        const y = scaleZ(body.position_m[2]);
        const color = colors[i % colors.length];

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 13, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#e9f0f7";
        ctx.font = "13px Inter, system-ui, sans-serif";
        ctx.fillText(name, x + 18, y + 4);
      });

      h3Cell.textContent = frame.h3_index;
      timeValue.textContent = `${Number(frame.time_s).toFixed(3)}s`;
      bodyCount.textContent = String(names.length);
      frameLabel.textContent = `Frame ${index + 1} / ${frames.length}`;
      slider.value = String(index);
      legend.innerHTML = names.map((name, i) => {
        const body = frame.bodies[name];
        return `<div class="body-row"><strong style="color:${colors[i % colors.length]}">${name}</strong>x ${body.position_m[0].toFixed(2)}m · z ${body.position_m[2].toFixed(2)}m · vz ${body.velocity_m_s[2].toFixed(2)}m/s</div>`;
      }).join("");
    }

    slider.addEventListener("input", () => {
      frameIndex = Number(slider.value);
      drawFrame(frameIndex);
    });

    playButton.addEventListener("click", () => {
      playing = !playing;
      playButton.textContent = playing ? "Pause" : "Play";
    });

    function tick() {
      if (playing) {
        frameIndex = (frameIndex + 1) % frames.length;
        drawFrame(frameIndex);
      }
      window.setTimeout(() => window.requestAnimationFrame(tick), 66);
    }

    drawFrame(frameIndex);
    tick();
  </script>
</body>
</html>
"""
