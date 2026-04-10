import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import parse_qs, urlparse

from .service import (
    compare_scenario_baseline,
    evaluate_scenario,
    evaluate_window_matrix,
    get_scenario_volume,
    learn_scenario_impacts,
    list_scenario_metadata,
    rank_scenario_actions,
    sample_scenario_point,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


INDEX_HTML = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MCP-Enabled Single-Room Spatial Digital Twin</title>
  <style>
    :root {
      --ink: #17211b;
      --muted: #69776e;
      --paper: #f8f2e7;
      --panel: #fffaf0;
      --line: #dfd1b8;
      --forest: #215941;
      --clay: #b4552b;
      --gold: #c58b2d;
      --blue: #2b5c7c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(197, 139, 45, 0.20), transparent 34rem),
        radial-gradient(circle at top right, rgba(43, 92, 124, 0.18), transparent 32rem),
        linear-gradient(135deg, #fbf4e8 0%, #f2eadb 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }
    header {
      padding: 44px min(7vw, 92px) 28px;
      border-bottom: 1px solid var(--line);
    }
    .eyebrow {
      color: var(--clay);
      font: 700 0.78rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
      letter-spacing: 0.15em;
      text-transform: uppercase;
    }
    h1 {
      max-width: 980px;
      margin: 12px 0 14px;
      font-size: clamp(2.2rem, 5vw, 5.8rem);
      line-height: 0.94;
      letter-spacing: -0.055em;
    }
    .lead {
      max-width: 860px;
      color: var(--muted);
      font-size: clamp(1.05rem, 2vw, 1.35rem);
      line-height: 1.7;
    }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 360px) 1fr;
      gap: 20px;
      padding: 24px min(7vw, 92px) 56px;
    }
    .panel {
      background: rgba(255, 250, 240, 0.88);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 50px rgba(68, 48, 19, 0.08);
    }
    aside {
      align-self: start;
      position: sticky;
      top: 18px;
      padding: 20px;
    }
    label {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font: 700 0.78rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    select, input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fffdf7;
      color: var(--ink);
      padding: 12px 14px;
      font: 1rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    button {
      width: 100%;
      border: 0;
      border-radius: 16px;
      padding: 13px 16px;
      margin-top: 14px;
      background: var(--forest);
      color: white;
      font: 800 0.9rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
      cursor: pointer;
    }
    button.secondary { background: var(--blue); }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 14px;
    }
    .content {
      display: grid;
      gap: 20px;
    }
    section { padding: 20px; }
    h2 {
      margin: 0 0 14px;
      font-size: clamp(1.35rem, 2.5vw, 2.15rem);
      letter-spacing: -0.035em;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(160px, 1fr));
      gap: 14px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 16px;
      background: #fffdf7;
    }
    .metric {
      color: var(--muted);
      font: 700 0.75rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
      text-transform: uppercase;
    }
    .value {
      margin-top: 8px;
      font-size: 2rem;
      letter-spacing: -0.04em;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 16px;
      background: #fffdf7;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 12px 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font: 800 0.75rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
      text-transform: uppercase;
    }
    .heatmaps {
      display: grid;
      grid-template-columns: repeat(3, minmax(210px, 1fr));
      gap: 14px;
    }
    .heatmaps img {
      width: 100%;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: white;
    }
    .volume-toolbar {
      display: flex;
      gap: 12px;
      align-items: end;
      margin-bottom: 14px;
    }
    .volume-toolbar label { margin-bottom: 6px; }
    .volume-toolbar select { max-width: 260px; }
    .volume-toolbar button {
      width: auto;
      min-width: 150px;
      margin-top: 0;
    }
    .volume-canvas {
      width: 100%;
      height: 540px;
      display: block;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: #fffdf7;
      cursor: grab;
      touch-action: none;
    }
    .volume-canvas:active { cursor: grabbing; }
    pre {
      max-height: 320px;
      overflow: auto;
      border-radius: 18px;
      padding: 16px;
      background: #1f261f;
      color: #f4f1df;
      font-size: 0.82rem;
    }
    .status { color: var(--muted); margin-top: 12px; line-height: 1.5; }
    @media (max-width: 920px) {
      main { grid-template-columns: 1fr; }
      aside { position: static; }
      .cards, .heatmaps { grid-template-columns: 1fr; }
      .volume-toolbar { display: block; }
      .volume-toolbar button { width: 100%; margin-top: 14px; }
      .volume-canvas { height: 420px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">MCP-Enabled Digital Twin Demo</div>
    <h1>Learning non-networked appliance impact from room sensors.</h1>
    <p class="lead">This demo estimates temperature, humidity, and illuminance fields in a single room using corner sensor calibration, compares the model against IDW, learns appliance impacts, and exposes the same capabilities through MCP tools.</p>
  </header>
  <main>
    <aside class="panel">
      <label for="scenario">Scenario</label>
      <select id="scenario"></select>
      <button onclick="loadScenario()">Run Scenario</button>
      <button class="secondary" onclick="loadScenario()">Refresh Outputs</button>
      <div class="form-grid">
        <div><label for="x">X</label><input id="x" type="number" step="0.1" value="3"></div>
        <div><label for="y">Y</label><input id="y" type="number" step="0.1" value="2"></div>
        <div><label for="z">Z</label><input id="z" type="number" step="0.1" value="1.5"></div>
      </div>
      <button onclick="samplePoint()">Sample Point</button>
      <p class="status" id="status">Loading scenarios...</p>
    </aside>
    <div class="content">
      <section class="panel">
        <h2>Target Zone Estimate</h2>
        <div class="cards" id="zoneCards"></div>
      </section>
      <section class="panel">
        <h2>Window Season/Weather/Time Matrix</h2>
        <p class="status">Runs 48 window-only simulations: 4 time periods × 3 weather states × 4 seasons.</p>
        <button class="secondary" onclick="loadWindowMatrix()">Run Window Matrix</button>
        <div id="windowMatrix"></div>
      </section>
      <section class="panel">
        <h2>Recommendation Ranking</h2>
        <div id="recommendations"></div>
      </section>
      <section class="panel">
        <h2>IDW Baseline Comparison</h2>
        <div id="baseline"></div>
      </section>
      <section class="panel">
        <h2>Learned Non-Networked Appliance Impact</h2>
        <div id="impacts"></div>
      </section>
      <section class="panel">
        <h2>Rotatable 3D Field Preview</h2>
        <p class="status">Drag to rotate, wheel or pinch-pad scroll to zoom. Colored squares mark appliance positions.</p>
        <div class="volume-toolbar">
          <div>
            <label for="volumeMetric">Metric</label>
            <select id="volumeMetric"></select>
          </div>
          <button class="secondary" onclick="resetVolumeView()">Reset View</button>
        </div>
        <canvas class="volume-canvas" id="volumeCanvas" width="960" height="540"></canvas>
        <p class="status" id="volumeStatus">Loading 3D volume...</p>
      </section>
      <section class="panel">
        <h2>3D SVG Snapshots</h2>
        <p class="status">Static 3D sampled-field exports with appliance position markers. Run <code>python3 scripts/run_demo.py</code> after model changes to refresh SVG outputs.</p>
        <div class="heatmaps" id="heatmaps"></div>
      </section>
      <section class="panel">
        <h2>Point Sample</h2>
        <pre id="sample">{}</pre>
      </section>
    </div>
  </main>
  <script>
    const metrics = ["temperature", "humidity", "illuminance"];
    const labels = { temperature: "Temperature", humidity: "Humidity", illuminance: "Illuminance" };
    const units = { temperature: "°C", humidity: "%", illuminance: "lx" };
    const deviceColors = { ac: "#2b5c7c", window: "#2f855a", light: "#c58b2d" };
    let activeScenario = "idle";
    let volumeData = null;
    let volumeMetric = "temperature";
    let volumeRotation = { pitch: -0.62, yaw: 0.72 };
    let volumeZoom = 1.0;
    let volumeDrag = null;

    async function getJSON(url) {
      const response = await fetch(url);
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }

    function fmt(value) {
      return Number(value).toFixed(4).replace(/\\.0000$/, ".0000");
    }

    async function loadScenarios() {
      const data = await getJSON("/api/scenarios");
      const select = document.getElementById("scenario");
      select.innerHTML = data.scenarios.map(item => `<option value="${item.name}">${item.name} — ${item.description}</option>`).join("");
      activeScenario = data.scenarios[0].name;
      select.value = activeScenario;
      await loadScenario();
      loadWindowMatrix().catch(error => {
        document.getElementById("windowMatrix").innerHTML = `<p class="status">${error.message}</p>`;
      });
    }

    async function loadScenario() {
      activeScenario = document.getElementById("scenario").value;
      document.getElementById("status").textContent = `Running ${activeScenario}...`;
      const [scenario, ranking, baseline, impacts, volume] = await Promise.all([
        getJSON(`/api/scenario?name=${encodeURIComponent(activeScenario)}`),
        getJSON(`/api/rank_actions?name=${encodeURIComponent(activeScenario)}`),
        getJSON(`/api/compare_baseline?name=${encodeURIComponent(activeScenario)}`),
        getJSON(`/api/learn_impacts?name=${encodeURIComponent(activeScenario)}`),
        getJSON(`/api/volume?name=${encodeURIComponent(activeScenario)}`)
      ]);
      renderZoneCards(scenario);
      renderRecommendations(ranking);
      renderBaseline(baseline);
      renderImpacts(impacts);
      setVolumeData(volume);
      renderHeatmaps(activeScenario);
      await samplePoint();
      document.getElementById("status").textContent = `Loaded ${activeScenario}.`;
    }

    function renderZoneCards(data) {
      const values = data.target_zone_estimated;
      document.getElementById("zoneCards").innerHTML = metrics.map(metric => `
        <div class="card">
          <div class="metric">${labels[metric]}</div>
          <div class="value">${fmt(values[metric])}</div>
          <div class="status">MAE ${fmt(data.field_mae[metric])}</div>
        </div>
      `).join("");
    }

    function renderRecommendations(data) {
      document.getElementById("recommendations").innerHTML = table(
        ["Rank", "Action", "Improvement", "Resulting Zone Values"],
        data.recommendations.map((item, index) => [
          index + 1,
          `${item.name}<br><span class="status">${item.description}</span>`,
          fmt(item.improvement),
          metrics.map(metric => `${labels[metric]}: ${fmt(item.resulting_zone_values[metric])}`).join("<br>")
        ])
      );
    }

    function renderBaseline(data) {
      document.getElementById("baseline").innerHTML = table(
        ["Metric", "Model MAE", "IDW MAE", "Reduction"],
        metrics.map(metric => {
          const item = data.comparison[metric];
          return [labels[metric], fmt(item.model_mae), fmt(item.idw_mae), `${fmt(item.mae_reduction)} (${item.mae_reduction_percent}%)`];
        })
      );
    }

    function renderImpacts(data) {
      if (!data.learned_device_impacts.length) {
        document.getElementById("impacts").innerHTML = `<p class="status">No active appliance in this scenario.</p>`;
        return;
      }
      document.getElementById("impacts").innerHTML = table(
        ["Device", "Temperature", "Humidity", "Illuminance"],
        data.learned_device_impacts.map(item => [
          item.device_name,
          fmt(item.metric_coefficients.temperature),
          fmt(item.metric_coefficients.humidity),
          fmt(item.metric_coefficients.illuminance)
        ])
      );
    }

    function renderHeatmaps(name) {
      document.getElementById("heatmaps").innerHTML = metrics.map(metric => `
        <img src="/outputs/${name}_${metric}_3d.svg" alt="${name} ${metric} 3D heatmap">
      `).join("");
    }

    function setupVolumeControls() {
      const select = document.getElementById("volumeMetric");
      select.innerHTML = metrics.map(metric => `<option value="${metric}">${labels[metric]}</option>`).join("");
      select.value = volumeMetric;
      select.addEventListener("change", () => {
        volumeMetric = select.value;
        drawVolume();
      });

      const canvas = document.getElementById("volumeCanvas");
      canvas.addEventListener("pointerdown", event => {
        volumeDrag = { x: event.clientX, y: event.clientY };
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointermove", event => {
        if (!volumeDrag) return;
        const dx = event.clientX - volumeDrag.x;
        const dy = event.clientY - volumeDrag.y;
        volumeRotation.yaw += dx * 0.012;
        volumeRotation.pitch = clamp(volumeRotation.pitch + dy * 0.012, -1.35, 1.1);
        volumeDrag = { x: event.clientX, y: event.clientY };
        drawVolume();
      });
      canvas.addEventListener("pointerup", event => {
        volumeDrag = null;
        canvas.releasePointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointercancel", () => {
        volumeDrag = null;
      });
      canvas.addEventListener("wheel", event => {
        event.preventDefault();
        volumeZoom = clamp(volumeZoom * (event.deltaY > 0 ? 0.92 : 1.08), 0.55, 2.2);
        drawVolume();
      }, { passive: false });
      window.addEventListener("resize", drawVolume);
    }

    function setVolumeData(data) {
      volumeData = data;
      document.getElementById("volumeStatus").textContent = `${data.scenario}: ${data.points.length} samples, ${data.devices.length} appliance markers.`;
      drawVolume();
    }

    function resetVolumeView() {
      volumeRotation = { pitch: -0.62, yaw: 0.72 };
      volumeZoom = 1.0;
      drawVolume();
    }

    function drawVolume() {
      const canvas = document.getElementById("volumeCanvas");
      if (!canvas || !volumeData) return;

      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));

      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, rect.width, rect.height);
      ctx.fillStyle = "#fffdf7";
      ctx.fillRect(0, 0, rect.width, rect.height);

      const projector = makeProjector(rect.width, rect.height, volumeData.room);
      drawRoomBox(ctx, projector);
      drawVolumePoints(ctx, projector);
      drawDeviceMarkers(ctx, projector);
      drawVolumeLegend(ctx, rect.width, volumeMetricRange(), volumeMetric);
    }

    function makeProjector(width, height, room) {
      const scale = Math.min(width / 9.2, height / 6.3) * volumeZoom;
      const center = { x: width * 0.48, y: height * 0.56 };
      const yaw = volumeRotation.yaw;
      const pitch = volumeRotation.pitch;
      const cy = Math.cos(yaw);
      const sy = Math.sin(yaw);
      const cp = Math.cos(pitch);
      const sp = Math.sin(pitch);
      return function project(point) {
        const x = point.x - room.width / 2;
        const y = point.y - room.length / 2;
        const z = point.z - room.height / 2;
        const xr = x * cy - y * sy;
        const yr = x * sy + y * cy;
        const yp = yr * cp - z * sp;
        const depth = yr * sp + z * cp;
        return {
          x: center.x + xr * scale,
          y: center.y + yp * scale,
          depth,
        };
      };
    }

    function drawRoomBox(ctx, project) {
      const room = volumeData.room;
      const corners = [
        { x: 0, y: 0, z: 0 }, { x: room.width, y: 0, z: 0 },
        { x: 0, y: room.length, z: 0 }, { x: room.width, y: room.length, z: 0 },
        { x: 0, y: 0, z: room.height }, { x: room.width, y: 0, z: room.height },
        { x: 0, y: room.length, z: room.height }, { x: room.width, y: room.length, z: room.height }
      ].map(project);
      const edges = [[0,1],[0,2],[1,3],[2,3],[4,5],[4,6],[5,7],[6,7],[0,4],[1,5],[2,6],[3,7]];
      ctx.strokeStyle = "rgba(82, 99, 86, 0.58)";
      ctx.lineWidth = 1.2;
      edges.forEach(([a, b]) => {
        ctx.beginPath();
        ctx.moveTo(corners[a].x, corners[a].y);
        ctx.lineTo(corners[b].x, corners[b].y);
        ctx.stroke();
      });
    }

    function drawVolumePoints(ctx, project) {
      const range = volumeMetricRange();
      const points = volumeData.points.map(point => ({
        ...point,
        projected: project(point),
      })).sort((a, b) => a.projected.depth - b.projected.depth);

      points.forEach(point => {
        const value = point[volumeMetric];
        const fraction = metricFraction(value, range);
        ctx.beginPath();
        ctx.fillStyle = valueColor(fraction);
        ctx.globalAlpha = 0.42 + 0.48 * fraction;
        ctx.arc(point.projected.x, point.projected.y, 4.2 + 2.8 * fraction, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;
    }

    function drawDeviceMarkers(ctx, project) {
      volumeData.devices.forEach(device => {
        const projected = project(device.position);
        const color = deviceColors[device.kind] || "#b4552b";
        ctx.save();
        ctx.translate(projected.x, projected.y);
        ctx.fillStyle = "#fffdf7";
        ctx.strokeStyle = "#17211b";
        ctx.lineWidth = 2.4;
        roundedRect(ctx, -9, -9, 18, 18, 4);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = color;
        roundedRect(ctx, -5.5, -5.5, 11, 11, 3);
        ctx.fill();
        ctx.restore();

        const label = `${device.name} (${device.kind}, ${Math.round(device.activation * 100)}%)`;
        ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
        const labelWidth = ctx.measureText(label).width;
        ctx.fillStyle = "rgba(255, 253, 247, 0.86)";
        roundedRect(ctx, projected.x + 12, projected.y - 24, labelWidth + 12, 20, 8);
        ctx.fill();
        ctx.fillStyle = "#17211b";
        ctx.fillText(label, projected.x + 18, projected.y - 10);
      });
    }

    function drawVolumeLegend(ctx, width, range, metric) {
      const x = width - 112;
      const y = 42;
      const h = 190;
      ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillStyle = "#69776e";
      ctx.fillText(`${labels[metric]} (${units[metric]})`, x - 38, y - 14);
      for (let i = 0; i < h; i += 1) {
        const fraction = 1 - i / h;
        ctx.fillStyle = valueColor(fraction);
        ctx.fillRect(x, y + i, 20, 1);
      }
      ctx.fillStyle = "#17211b";
      ctx.fillText(range.max.toFixed(1), x + 28, y + 9);
      ctx.fillText(range.min.toFixed(1), x + 28, y + h);
    }

    function volumeMetricRange() {
      const values = volumeData.points.map(point => point[volumeMetric]);
      return { min: Math.min(...values), max: Math.max(...values) };
    }

    function metricFraction(value, range) {
      if (Math.abs(range.max - range.min) < 1e-9) return 0.5;
      return clamp((value - range.min) / (range.max - range.min), 0, 1);
    }

    function valueColor(fraction) {
      const stops = fraction < 0.5
        ? [[49, 130, 189], [255, 244, 173], fraction / 0.5]
        : [[255, 244, 173], [203, 24, 29], (fraction - 0.5) / 0.5];
      const [start, end, local] = stops;
      const rgb = start.map((value, index) => Math.round(value + (end[index] - value) * local));
      return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    }

    function roundedRect(ctx, x, y, width, height, radius) {
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + width - radius, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
      ctx.lineTo(x + width, y + height - radius);
      ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
      ctx.lineTo(x + radius, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    async function loadWindowMatrix() {
      const container = document.getElementById("windowMatrix");
      container.innerHTML = `<p class="status">Running 48 window scenarios...</p>`;
      const data = await getJSON("/api/window_matrix");
      container.innerHTML = table(
        ["Season", "Weather", "Time", "Outdoor", "Window Zone", "Center Zone"],
        data.scenarios.map(item => [
          item.metadata.season_zh,
          item.metadata.weather_zh,
          item.metadata.time_of_day_zh,
          [
            `T: ${fmt(item.environment.outdoor_temperature)}`,
            `H: ${fmt(item.environment.outdoor_humidity)}`,
            `Sun: ${fmt(item.environment.sunlight_illuminance)}`
          ].join("<br>"),
          metrics.map(metric => `${labels[metric]}: ${fmt(item.window_zone_estimated[metric])}`).join("<br>"),
          metrics.map(metric => `${labels[metric]}: ${fmt(item.center_zone_estimated[metric])}`).join("<br>")
        ])
      );
    }

    async function samplePoint() {
      const x = document.getElementById("x").value;
      const y = document.getElementById("y").value;
      const z = document.getElementById("z").value;
      const data = await getJSON(`/api/sample?name=${encodeURIComponent(activeScenario)}&x=${x}&y=${y}&z=${z}`);
      document.getElementById("sample").textContent = JSON.stringify(data, null, 2);
    }

    function table(headers, rows) {
      return `<table><thead><tr>${headers.map(item => `<th>${item}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }

    setupVolumeControls();
    loadScenarios().catch(error => {
      document.getElementById("status").textContent = error.message;
    });
  </script>
</body>
</html>
"""


class DemoRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_text(INDEX_HTML, "text/html; charset=utf-8")
                return
            if parsed.path == "/api/scenarios":
                self._send_json({"scenarios": list_scenario_metadata()})
                return
            if parsed.path == "/api/scenario":
                self._send_json(evaluate_scenario(_query_name(parsed.query)))
                return
            if parsed.path == "/api/window_matrix":
                self._send_json(evaluate_window_matrix())
                return
            if parsed.path == "/api/volume":
                self._send_json(get_scenario_volume(_query_name(parsed.query)))
                return
            if parsed.path == "/api/rank_actions":
                self._send_json(rank_scenario_actions(_query_name(parsed.query)))
                return
            if parsed.path == "/api/compare_baseline":
                self._send_json(compare_scenario_baseline(_query_name(parsed.query)))
                return
            if parsed.path == "/api/learn_impacts":
                self._send_json(learn_scenario_impacts(_query_name(parsed.query)))
                return
            if parsed.path == "/api/sample":
                query = parse_qs(parsed.query)
                self._send_json(
                    sample_scenario_point(
                        scenario_name=_query_name(parsed.query),
                        x=_query_float(query, "x", 3.0),
                        y=_query_float(query, "y", 2.0),
                        z=_query_float(query, "z", 1.5),
                    )
                )
                return
            if parsed.path.startswith("/outputs/"):
                self._send_file(OUTPUTS / parsed.path.removeprefix("/outputs/"))
                return
            self.send_error(404, "Not found")
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: Dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, payload: str, content_type: str, status: int = 200) -> None:
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        resolved = path.resolve()
        if not str(resolved).startswith(str(OUTPUTS.resolve())) or not resolved.exists() or not resolved.is_file():
            self.send_error(404, "File not found")
            return
        data = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _query_name(query_string: str) -> str:
    query = parse_qs(query_string)
    return query.get("name", ["idle"])[0]


def _query_float(query: Dict[str, list], key: str, default: float) -> float:
    try:
        return float(query.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


def run_server(host: str = "127.0.0.1", port: int = 8765) -> Tuple[str, int]:
    server = ThreadingHTTPServer((host, port), DemoRequestHandler)
    print(f"Serving web demo at http://{host}:{port}")
    server.serve_forever()
    return host, port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local web demo server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
