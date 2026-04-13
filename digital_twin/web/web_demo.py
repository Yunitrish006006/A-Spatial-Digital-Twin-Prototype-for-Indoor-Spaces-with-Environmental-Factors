import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import parse_qs, urlparse

from digital_twin.core.service import (
    compare_scenario_baseline,
    evaluate_scenario,
    evaluate_window_direct,
    evaluate_window_direct_dashboard,
    evaluate_window_matrix,
    get_scenario_volume,
    get_scenario_timeline,
    get_window_direct_timeline,
    learn_scenario_impacts,
    list_scenario_metadata,
    rank_scenario_actions,
    sample_window_direct_point,
    sample_scenario_point,
)
from digital_twin.core.scenarios import (
    SEASON_PROFILES,
    TIME_OF_DAY_PROFILES,
    WEATHER_PROFILES,
    WINDOW_SEASON_ORDER,
    WINDOW_TIME_ORDER,
    WINDOW_WEATHER_ORDER,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
DEVICE_OVERRIDE_NAMES = ("ac_main", "window_main", "light_main")
FURNITURE_OVERRIDE_NAMES = ("cabinet_window", "sofa_main", "table_center")
AC_MODE_OPTIONS = ("cool", "dry", "heat", "fan")
AC_SWING_OPTIONS = ("fixed", "swing")
WINDOW_PRESET_DATA = json.dumps(
    {
        "seasonOrder": list(WINDOW_SEASON_ORDER),
        "weatherOrder": list(WINDOW_WEATHER_ORDER),
        "timeOrder": list(WINDOW_TIME_ORDER),
        "seasons": SEASON_PROFILES,
        "weathers": WEATHER_PROFILES,
        "times": TIME_OF_DAY_PROFILES,
    },
    ensure_ascii=False,
)


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
      max-height: calc(100vh - 36px);
      overflow: auto;
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
    .device-controls {
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }
    .device-toggle {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 10px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 11px 12px;
      background: #fffdf7;
    }
    .device-toggle input {
      width: 18px;
      height: 18px;
      accent-color: var(--forest);
    }
    .device-toggle span {
      display: block;
      font: 800 0.88rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .device-toggle small {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font: 0.78rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .metric-controls {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .metric-toggle {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 8px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 10px 12px;
      background: #fffdf7;
      font: 800 0.78rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
      cursor: pointer;
    }
    .metric-toggle input {
      width: 16px;
      height: 16px;
      accent-color: var(--blue);
    }
    .metric-toggle.disabled {
      opacity: 0.46;
      cursor: default;
    }
    .control-group {
      margin-top: 16px;
    }
    .sidebar-section + .sidebar-section {
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px solid rgba(223, 209, 184, 0.8);
    }
    .sidebar-form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .sidebar-actions {
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }
    .sidebar-actions button {
      margin-top: 0;
    }
    .item-list {
      display: grid;
      gap: 10px;
      margin-top: 12px;
    }
    .item-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: #fffdf7;
    }
    .item-field-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .item-field-grid label {
      margin-bottom: 4px;
      font-size: 0.68rem;
    }
    .item-field-grid input {
      padding: 9px 10px;
      font-size: 0.84rem;
    }
    .item-actions {
      display: flex;
      gap: 8px;
      margin-top: 10px;
      flex-wrap: wrap;
    }
    .item-actions button {
      width: auto;
      min-width: 0;
      margin-top: 0;
      padding: 9px 12px;
      border-radius: 12px;
      font-size: 0.78rem;
    }
    .item-actions button.remove {
      background: var(--clay);
    }
    .slider-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
    }
    input[type="range"] {
      padding: 0;
      accent-color: var(--clay);
    }
    .slider-readout {
      min-width: 72px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 10px 12px;
      background: #fffdf7;
      color: var(--ink);
      text-align: center;
      font: 800 0.82rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
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
    .timeline-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(220px, 1fr));
      gap: 14px;
    }
    .timeline-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 14px;
      background: #fffdf7;
    }
    .timeline-svg {
      width: 100%;
      height: 180px;
      display: block;
    }
    .preview-timeline {
      margin-bottom: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: #fffdf7;
    }
    .preview-timeline-meta {
      display: grid;
      gap: 10px;
      margin-top: 12px;
    }
    .preview-timeline-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .preview-timeline-actions button {
      width: auto;
      min-width: 150px;
      margin-top: 0;
    }
    .volume-toolbar {
      display: flex;
      gap: 12px;
      align-items: end;
      margin-bottom: 14px;
    }
    .volume-toolbar label { margin-bottom: 6px; }
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
      aside {
        position: static;
        max-height: none;
        overflow: visible;
      }
      .sidebar-form-grid { grid-template-columns: 1fr; }
      .cards, .heatmaps, .timeline-grid { grid-template-columns: 1fr; }
      .volume-toolbar { display: block; }
      .volume-toolbar button { width: 100%; margin-top: 14px; }
      .volume-canvas { height: 420px; }
      .item-field-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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
      <div class="sidebar-section">
        <label>Device Toggles</label>
        <div class="device-controls" id="deviceControls"></div>
      </div>
      <div class="sidebar-section">
        <label>AC Controls</label>
        <div class="control-group">
          <label>AC Mode</label>
          <div class="metric-controls" id="acModeControls"></div>
        </div>
        <div class="control-group">
          <label>AC Temperature</label>
          <div class="slider-row">
            <input id="acTargetTemperature" type="range" min="20" max="33" step="1" value="24">
            <div class="slider-readout" id="acTargetTemperatureValue">24°C</div>
          </div>
        </div>
        <div class="control-group">
          <label>Left / Right Swing</label>
          <div class="metric-controls" id="acHorizontalModeControls"></div>
          <div class="metric-controls" id="acHorizontalAngleControls"></div>
        </div>
        <div class="control-group">
          <label>Up / Down Swing</label>
          <div class="metric-controls" id="acVerticalModeControls"></div>
          <div class="metric-controls" id="acVerticalAngleControls"></div>
        </div>
      </div>
      <div class="sidebar-section">
        <label>Indoor Baseline</label>
        <p class="status">These baseline values feed the full room model, including zone cards, ranking, timeline, 3D preview, and direct-window mode.</p>
        <div class="sidebar-form-grid">
          <div><label for="baselineIndoorTemperature">Indoor °C</label><input id="baselineIndoorTemperature" type="number" step="0.1" value="29"></div>
          <div><label for="baselineIndoorHumidity">Indoor RH</label><input id="baselineIndoorHumidity" type="number" step="0.1" value="67"></div>
          <div><label for="baselineIlluminance">Base lx</label><input id="baselineIlluminance" type="number" step="1" value="90"></div>
        </div>
      </div>
      <div class="sidebar-section">
        <label>Estimator</label>
        <label class="device-toggle">
          <input id="useHybridResidual" type="checkbox" checked>
          <span>Hybrid Residual Correction<small>Apply the saved residual neural checkpoint on top of the physics model when available.</small></span>
        </label>
        <p class="status" id="hybridEstimatorStatus">Hybrid residual status will appear here.</p>
      </div>
      <div class="sidebar-section">
        <label>Window Controls</label>
        <p class="status">Season, weather, and time presets derive outdoor humidity and sunlight. Manual input here only overrides outdoor temperature and window opening.</p>
        <div class="control-group">
          <label>Outdoor Season</label>
          <div class="metric-controls" id="windowSeasonControls"></div>
        </div>
        <div class="control-group">
          <label>Outdoor Weather</label>
          <div class="metric-controls" id="windowWeatherControls"></div>
        </div>
        <div class="control-group">
          <label>Time Of Day</label>
          <div class="metric-controls" id="windowTimeControls"></div>
        </div>
        <p class="status" id="windowPresetSummary">Preset values will appear here.</p>
        <div class="sidebar-form-grid">
          <div><label for="directOutdoorTemperature">Outdoor °C</label><input id="directOutdoorTemperature" type="number" step="0.1" value="33"></div>
          <div><label for="directOpening">Opening</label><input id="directOpening" type="number" min="0" max="1" step="0.05" value="0.7"></div>
        </div>
        <div class="sidebar-actions">
          <button class="secondary" onclick="applyWindowPreset()">Apply Outdoor Preset</button>
          <button class="secondary" onclick="loadDirectWindow()">Run Direct Window Simulation</button>
        </div>
      </div>
      <div class="sidebar-section">
        <label>Furniture Blocking</label>
        <p class="status">Toggle simplified furniture blockers to attenuate airflow, daylight, and window exchange along their paths. Custom furniture snaps to a 0.1 m grid and avoids overlapping active blockers.</p>
        <div class="device-controls" id="furnitureControls"></div>
        <div class="control-group">
          <label>Custom Furniture</label>
          <div class="sidebar-form-grid">
            <div><label for="customFurnitureLabel">Label</label><input id="customFurnitureLabel" type="text" value="Desk Divider"></div>
            <div><label for="customFurnitureKind">Kind</label><input id="customFurnitureKind" type="text" value="custom"></div>
            <div><label for="customFurnitureCenterX">Center X</label><input id="customFurnitureCenterX" type="number" step="0.1" value="2.8"></div>
            <div><label for="customFurnitureCenterY">Center Y</label><input id="customFurnitureCenterY" type="number" step="0.1" value="2.0"></div>
            <div><label for="customFurnitureBaseZ">Base Z</label><input id="customFurnitureBaseZ" type="number" step="0.1" value="0.0"></div>
            <div><label for="customFurnitureWidth">Width X</label><input id="customFurnitureWidth" type="number" min="0.1" step="0.1" value="1.2"></div>
            <div><label for="customFurnitureLength">Length Y</label><input id="customFurnitureLength" type="number" min="0.1" step="0.1" value="0.6"></div>
            <div><label for="customFurnitureHeight">Height Z</label><input id="customFurnitureHeight" type="number" min="0.1" step="0.1" value="1.2"></div>
            <div><label for="customFurnitureBlock">Block</label><input id="customFurnitureBlock" type="number" min="0.05" max="0.95" step="0.05" value="0.35"></div>
          </div>
          <label class="device-toggle" style="margin-top: 12px;">
            <input id="customFurnitureActive" type="checkbox" checked>
            <span>Enable On Add<small>New custom furniture starts active and immediately affects the simulation.</small></span>
          </label>
          <div class="sidebar-actions">
            <button class="secondary" id="addCustomFurnitureButton" onclick="addCustomFurniture()">Add Custom Furniture</button>
            <button class="secondary" id="clearCustomFurnitureButton" onclick="clearCustomFurniture()">Clear Custom Furniture</button>
          </div>
          <div class="item-list" id="customFurnitureList"></div>
        </div>
      </div>
      <div class="sidebar-section">
        <label>Scenario Controls</label>
        <button onclick="loadScenario()">Run Simulation</button>
        <button class="secondary" onclick="resetDeviceControls()">Clear Devices</button>
      </div>
      <div class="sidebar-section">
        <label>Point Sample</label>
        <div class="sidebar-form-grid">
          <div><label for="x">X</label><input id="x" type="number" step="0.1" value="3"></div>
          <div><label for="y">Y</label><input id="y" type="number" step="0.1" value="2"></div>
          <div><label for="z">Z</label><input id="z" type="number" step="0.1" value="1.5"></div>
        </div>
        <button onclick="samplePoint()">Sample Point</button>
      </div>
      <p class="status" id="status">Loading scenarios...</p>
    </aside>
    <div class="content">
      <section class="panel">
        <h2>Target Zone Estimate</h2>
        <p class="status" id="estimatorStatus">Estimator status will appear here.</p>
        <div class="cards" id="zoneCards"></div>
      </section>
      <section class="panel">
        <h2>Time Evolution</h2>
        <p class="status">Shows how the target zone changes from startup toward steady state under the current device and window settings.</p>
        <div class="timeline-grid" id="timelineCharts"></div>
      </section>
      <section class="panel">
        <h2>Direct Window Input</h2>
        <p class="status">Use the fixed left sidebar to edit outdoor window conditions, then read the resulting zone estimates here.</p>
        <div id="windowDirectResult"></div>
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
        <p class="status">Drag to rotate, wheel or pinch-pad scroll to zoom. Colored markers show appliances and translucent boxes show active furniture blockers. Drag a custom furniture box to reposition it on the floor plane, then release to recompute the field.</p>
        <div class="preview-timeline">
          <label>Preview Timeline</label>
          <div class="slider-row">
            <input id="elapsedMinutes" type="range" min="0" max="120" step="1" value="18">
            <div class="slider-readout" id="elapsedMinutesValue">18 min</div>
          </div>
          <div class="preview-timeline-meta">
            <div class="metric-controls" id="playbackSpeedControls"></div>
            <div class="preview-timeline-actions">
              <button class="secondary" id="elapsedPlayButton" onclick="toggleElapsedPlayback()">Play Timeline</button>
              <button class="secondary" onclick="resetElapsedPlayback()">Reset To 0</button>
            </div>
          </div>
          <p class="status" id="elapsedTimelineStatus">Current minute and remaining change will appear here.</p>
          <p class="status">Scrub from startup toward quasi-steady state. The preview, zone cards, point sample, and time charts stay synchronized.</p>
        </div>
        <div class="volume-toolbar">
          <div>
            <label>Metric</label>
            <div class="metric-controls" id="metricControls"></div>
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
    const furnitureColors = { cabinet: "#7a4a2c", sofa: "#87546a", table: "#8d7a2f" };
    const deviceDefaultActivation = { ac_main: 0.8, window_main: 0.7, light_main: 0.8 };
    const acModeLabels = { cool: "Cool", dry: "Dry", heat: "Heat", fan: "Fan" };
    const acSwingLabels = { fixed: "Fixed", swing: "Swing" };
    const acHorizontalAngles = [-45, -20, 0, 20, 45];
    const acVerticalAngles = [5, 15, 25, 35];
    const windowPresetData = __WINDOW_PRESET_DATA__;
    const timelineColors = { temperature: "#b4552b", humidity: "#2b5c7c", illuminance: "#c58b2d" };
    const playbackSpeedOptions = [
      { value: "1x", label: "1x", delayMs: 320 },
      { value: "2x", label: "2x", delayMs: 180 },
      { value: "4x", label: "4x", delayMs: 90 }
    ];
    let activeScenario = "idle";
    let activeContext = { kind: "scenario", name: "idle" };
    let scenarioMetadata = {};
    let currentTimeline = null;
    let volumeData = null;
    let volumeMetric = "temperature";
    let volumeRotation = { pitch: -0.62, yaw: 0.72 };
    let volumeZoom = 1.0;
    let volumeInteraction = null;
    let volumeFurnitureHandles = [];
    let elapsedPlayback = { running: false, stepMinutes: 5, delayMs: 180 };
    let customFurnitureItems = [];
    let customFurnitureCounter = 1;

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
      scenarioMetadata = Object.fromEntries(data.scenarios.map(item => [item.name, item]));
      activeScenario = scenarioMetadata.idle ? "idle" : data.scenarios[0].name;
      activeContext = { kind: "scenario", name: activeScenario };
      setupElapsedTimeControl();
      setupIndoorBaselineControls();
      setupHybridEstimatorControls();
      setupCustomFurnitureControls();
      syncDeviceControlsFromScenario(activeScenario);
      syncFurnitureControlsFromScenario(activeScenario);
      syncAcControlsFromScenario(activeScenario);
      setupWindowPresetControls();
      await loadScenario();
      loadDirectWindow(false).catch(error => {
        document.getElementById("windowDirectResult").innerHTML = `<p class="status">${error.message}</p>`;
      });
    }

    function setupElapsedTimeControl() {
      const slider = document.getElementById("elapsedMinutes");
      renderRadioGroup(
        "playbackSpeedControls",
        "playbackSpeed",
        playbackSpeedOptions.map(item => item.value),
        "2x",
        null,
        value => value
      );
      syncElapsedTimeReadout();
      updateElapsedPlaybackButton();
      if (slider.dataset.bound === "1") {
        return;
      }
      slider.dataset.bound = "1";
      slider.addEventListener("input", () => {
        stopElapsedPlayback();
        syncElapsedTimeReadout();
      });
      slider.addEventListener("change", async () => {
        stopElapsedPlayback();
        await refreshActiveContext();
      });
      document.querySelectorAll("#playbackSpeedControls input").forEach(input => {
        input.addEventListener("change", () => syncPlaybackSpeed());
      });
      syncPlaybackSpeed();
    }

    function setupIndoorBaselineControls() {
      document.querySelectorAll("#baselineIndoorTemperature, #baselineIndoorHumidity, #baselineIlluminance").forEach(input => {
        if (input.dataset.bound === "1") {
          return;
        }
        input.dataset.bound = "1";
        input.addEventListener("change", async () => {
          stopElapsedPlayback();
          await refreshActiveContext();
        });
      });
    }

    function setupHybridEstimatorControls() {
      const input = document.getElementById("useHybridResidual");
      if (input.dataset.bound === "1") {
        return;
      }
      input.dataset.bound = "1";
      input.addEventListener("change", async () => {
        stopElapsedPlayback();
        await refreshActiveContext();
      });
      setEstimatorStatus(null);
    }

    function setupCustomFurnitureControls() {
      syncCustomFurnitureList();
    }

    async function loadScenario() {
      activeContext = { kind: "scenario", name: activeScenario };
      document.getElementById("status").textContent = "Running checkbox-defined simulation...";
      const query = scenarioQuery();
      const [scenario, ranking, baseline, impacts, volume, timeline] = await Promise.all([
        getJSON(`/api/scenario?${query}`),
        getJSON(`/api/rank_actions?${query}`),
        getJSON(`/api/compare_baseline?${query}`),
        getJSON(`/api/learn_impacts?${query}`),
        getJSON(`/api/volume?${query}`),
        getJSON(`/api/timeline?${query}`)
      ]);
      renderZoneCards(scenario);
      renderRecommendations(ranking);
      renderBaseline(baseline);
      renderImpacts(impacts);
      setVolumeData(volume);
      renderTimeline(timeline);
      renderHeatmapsForScenario(activeScenario);
      await samplePoint();
      document.getElementById("status").textContent = "Loaded checkbox-defined simulation.";
    }

    async function refreshActiveContext() {
      if (activeContext.kind === "window_direct") {
        await loadDirectWindow(true);
        return;
      }
      await loadScenario();
    }

    function syncDeviceControlsFromScenario(name) {
      const scenario = scenarioMetadata[name];
      const container = document.getElementById("deviceControls");
      if (!scenario) {
        container.innerHTML = "";
        return;
      }
      container.innerHTML = scenario.devices.map(device => {
        const activeLevel = device.activation > 0 ? device.activation : (deviceDefaultActivation[device.name] || 1.0);
        const checked = device.activation > 0 ? "checked" : "";
        const shape = device.geometry?.shape === "wall_bar" ? "bar" : (device.geometry?.shape === "wall_rectangle" ? "surface" : "point");
        return `
          <label class="device-toggle">
            <input type="checkbox" data-device="${device.name}" data-activation="${activeLevel}" ${checked}>
            <span>${device.name}<small>${device.kind}, ${shape}, ${Math.round(activeLevel * 100)}% when checked</small></span>
          </label>
        `;
      }).join("");
      container.querySelectorAll("input[type='checkbox']").forEach(input => {
        input.addEventListener("change", () => loadScenario());
      });
    }

    function syncFurnitureControlsFromScenario(name) {
      const scenario = scenarioMetadata[name];
      const container = document.getElementById("furnitureControls");
      if (!scenario) {
        container.innerHTML = "";
        return;
      }
      container.innerHTML = (scenario.furniture || []).map(item => {
        const checked = item.activation > 0 ? "checked" : "";
        const label = item.metadata?.label || item.name;
        const block = Math.round(Number(item.metadata?.block_strength || 0.3) * 100);
        return `
          <label class="device-toggle">
            <input type="checkbox" data-furniture="${item.name}" data-activation="1" ${checked}>
            <span>${label}<small>${item.kind}, approx. ${block}% path attenuation when enabled</small></span>
          </label>
        `;
      }).join("");
      container.querySelectorAll("input[type='checkbox']").forEach(input => {
        input.addEventListener("change", async () => {
          stopElapsedPlayback();
          await refreshActiveContext();
        });
      });
    }

    async function addCustomFurniture() {
      const room = currentRoomDimensions();
      const label = document.getElementById("customFurnitureLabel").value.trim() || `Custom Furniture ${customFurnitureCounter}`;
      const kind = sanitizeFurnitureKind(document.getElementById("customFurnitureKind").value);
      const centerX = Number(document.getElementById("customFurnitureCenterX").value || room.width / 2);
      const centerY = Number(document.getElementById("customFurnitureCenterY").value || room.length / 2);
      const baseZ = Number(document.getElementById("customFurnitureBaseZ").value || 0);
      const width = Math.max(0.1, Number(document.getElementById("customFurnitureWidth").value || 1.0));
      const length = Math.max(0.1, Number(document.getElementById("customFurnitureLength").value || 0.8));
      const height = Math.max(0.1, Number(document.getElementById("customFurnitureHeight").value || 1.0));
      const blockStrength = clamp(Number(document.getElementById("customFurnitureBlock").value || 0.35), 0.05, 0.95);
      const activation = document.getElementById("customFurnitureActive").checked ? 1.0 : 0.0;

      const minCorner = {
        x: clamp(centerX - width / 2, 0, room.width),
        y: clamp(centerY - length / 2, 0, room.length),
        z: clamp(baseZ, 0, room.height)
      };
      const maxCorner = {
        x: clamp(centerX + width / 2, 0, room.width),
        y: clamp(centerY + length / 2, 0, room.length),
        z: clamp(baseZ + height, 0, room.height)
      };
      if ((maxCorner.x - minCorner.x) < 0.05 || (maxCorner.y - minCorner.y) < 0.05 || (maxCorner.z - minCorner.z) < 0.05) {
        document.getElementById("status").textContent = "Custom furniture dimensions collapsed outside the room bounds. Adjust the geometry and try again.";
        return;
      }

      customFurnitureItems.push({
        name: `custom_furniture_${customFurnitureCounter++}`,
        kind,
        activation,
        min_corner: minCorner,
        max_corner: maxCorner,
        metadata: {
          label,
          custom: true,
          block_strength: blockStrength,
          window_block: blockStrength,
          light_block: clamp(blockStrength * 1.05, 0.05, 0.98),
          ac_block: clamp(blockStrength * 0.9, 0.05, 0.95),
          mixing_penalty: clamp(blockStrength * 0.12, 0.01, 0.16)
        }
      });
      syncCustomFurnitureList();
      stopElapsedPlayback();
      await refreshActiveContext();
    }

    async function clearCustomFurniture() {
      customFurnitureItems = [];
      syncCustomFurnitureList();
      stopElapsedPlayback();
      await refreshActiveContext();
    }

    function syncCustomFurnitureList() {
      const container = document.getElementById("customFurnitureList");
      if (!customFurnitureItems.length) {
        container.innerHTML = `<p class="status">No custom furniture yet. Add blockers here to place multiple extra objects in the room.</p>`;
        return;
      }
      container.innerHTML = customFurnitureItems.map((item, index) => {
        const view = customFurnitureView(item);
        return `
          <div class="item-card">
            <label class="device-toggle">
              <input type="checkbox" data-custom-index="${index}" ${Number(item.activation) > 0 ? "checked" : ""}>
              <span>${item.metadata?.label || item.name}<small>${item.kind}, center (${fmt(view.centerX)}, ${fmt(view.centerY)}, ${fmt(view.baseZ)})</small></span>
            </label>
            <p class="status">Min (${fmt(item.min_corner.x)}, ${fmt(item.min_corner.y)}, ${fmt(item.min_corner.z)}), max (${fmt(item.max_corner.x)}, ${fmt(item.max_corner.y)}, ${fmt(item.max_corner.z)}), block ${Math.round(Number(item.metadata?.block_strength || 0.3) * 100)}%.</p>
            <div class="item-field-grid">
              <div><label>Center X</label><input type="number" step="0.1" value="${view.centerX.toFixed(1)}" data-edit-custom="${index}" data-field="center_x"></div>
              <div><label>Center Y</label><input type="number" step="0.1" value="${view.centerY.toFixed(1)}" data-edit-custom="${index}" data-field="center_y"></div>
              <div><label>Base Z</label><input type="number" step="0.1" value="${view.baseZ.toFixed(1)}" data-edit-custom="${index}" data-field="base_z"></div>
              <div><label>Width X</label><input type="number" min="0.1" step="0.1" value="${view.width.toFixed(1)}" data-edit-custom="${index}" data-field="width"></div>
              <div><label>Length Y</label><input type="number" min="0.1" step="0.1" value="${view.length.toFixed(1)}" data-edit-custom="${index}" data-field="length"></div>
              <div><label>Height Z</label><input type="number" min="0.1" step="0.1" value="${view.height.toFixed(1)}" data-edit-custom="${index}" data-field="height"></div>
              <div><label>Block</label><input type="number" min="0.05" max="0.95" step="0.05" value="${Number(item.metadata?.block_strength || 0.3).toFixed(2)}" data-edit-custom="${index}" data-field="block_strength"></div>
            </div>
            <div class="item-actions">
              <button class="secondary remove" data-remove-custom="${index}">Remove</button>
            </div>
          </div>
        `;
      }).join("");
      container.querySelectorAll("input[data-custom-index]").forEach(input => {
        input.addEventListener("change", async event => {
          const index = Number(event.currentTarget.dataset.customIndex);
          customFurnitureItems[index].activation = event.currentTarget.checked ? 1.0 : 0.0;
          stopElapsedPlayback();
          await refreshActiveContext();
        });
      });
      container.querySelectorAll("input[data-edit-custom]").forEach(input => {
        input.addEventListener("change", async event => {
          const target = event.currentTarget;
          updateCustomFurnitureField(
            Number(target.dataset.editCustom),
            String(target.dataset.field || ""),
            Number(target.value || "0")
          );
          syncCustomFurnitureList();
          stopElapsedPlayback();
          await refreshActiveContext();
        });
      });
      container.querySelectorAll("button[data-remove-custom]").forEach(button => {
        button.addEventListener("click", async event => {
          const index = Number(event.currentTarget.dataset.removeCustom);
          customFurnitureItems.splice(index, 1);
          syncCustomFurnitureList();
          stopElapsedPlayback();
          await refreshActiveContext();
        });
      });
    }

    function customFurnitureView(item) {
      return {
        centerX: (Number(item.min_corner.x) + Number(item.max_corner.x)) / 2,
        centerY: (Number(item.min_corner.y) + Number(item.max_corner.y)) / 2,
        baseZ: Number(item.min_corner.z),
        width: Number(item.max_corner.x) - Number(item.min_corner.x),
        length: Number(item.max_corner.y) - Number(item.min_corner.y),
        height: Number(item.max_corner.z) - Number(item.min_corner.z),
      };
    }

    function updateCustomFurnitureField(index, field, rawValue) {
      const item = customFurnitureItems[index];
      if (!item) return;
      const room = currentRoomDimensions();
      const view = customFurnitureView(item);
      const next = { ...view };

      if (field === "center_x") next.centerX = rawValue;
      if (field === "center_y") next.centerY = rawValue;
      if (field === "base_z") next.baseZ = rawValue;
      if (field === "width") next.width = Math.max(0.1, rawValue);
      if (field === "length") next.length = Math.max(0.1, rawValue);
      if (field === "height") next.height = Math.max(0.1, rawValue);
      if (field === "block_strength") {
        const block = clamp(rawValue, 0.05, 0.95);
        item.metadata.block_strength = block;
        item.metadata.window_block = block;
        item.metadata.light_block = clamp(block * 1.05, 0.05, 0.98);
        item.metadata.ac_block = clamp(block * 0.9, 0.05, 0.95);
        item.metadata.mixing_penalty = clamp(block * 0.12, 0.01, 0.16);
        syncLiveFurnitureData(item);
        return;
      }

      const geometry = normalizedFurnitureGeometry(next, room);
      if (customFurnitureCollides(item.name, geometry.minCorner, geometry.maxCorner)) {
        document.getElementById("status").textContent = `${item.metadata?.label || item.name} would overlap another active blocker. The change was rejected.`;
        return;
      }
      item.min_corner = geometry.minCorner;
      item.max_corner = geometry.maxCorner;
      syncLiveFurnitureData(item);
    }

    function normalizedFurnitureGeometry(view, room) {
      const width = Math.max(0.1, Number(view.width));
      const length = Math.max(0.1, Number(view.length));
      const height = Math.max(0.1, Number(view.height));
      const centerX = snapToGrid(clamp(Number(view.centerX), width / 2, room.width - width / 2));
      const centerY = snapToGrid(clamp(Number(view.centerY), length / 2, room.length - length / 2));
      const baseZ = snapToGrid(clamp(Number(view.baseZ), 0, room.height - height));
      return {
        minCorner: {
          x: snapToGrid(clamp(centerX - width / 2, 0, room.width - width)),
          y: snapToGrid(clamp(centerY - length / 2, 0, room.length - length)),
          z: baseZ,
        },
        maxCorner: {
          x: snapToGrid(clamp(centerX - width / 2, 0, room.width - width) + width),
          y: snapToGrid(clamp(centerY - length / 2, 0, room.length - length) + length),
          z: snapToGrid(baseZ + height),
        }
      };
    }

    function syncAcControlsFromScenario(name) {
      const scenario = scenarioMetadata[name];
      const acDevice = scenario?.devices?.find(device => device.name === "ac_main");
      const metadata = acDevice?.metadata || {};

      renderRadioGroup("acModeControls", "acMode", Object.keys(acModeLabels), metadata.ac_mode || "cool", acModeLabels);
      renderRadioGroup("acHorizontalModeControls", "acHorizontalMode", ["fixed", "swing"], metadata.horizontal_mode || "fixed", acSwingLabels);
      renderRadioGroup(
        "acHorizontalAngleControls",
        "acHorizontalAngle",
        acHorizontalAngles.map(String),
        String(Math.round(Number(metadata.horizontal_angle_deg ?? 0))),
        null,
        value => `${value}°`
      );
      renderRadioGroup("acVerticalModeControls", "acVerticalMode", ["fixed", "swing"], metadata.vertical_mode || "fixed", acSwingLabels);
      renderRadioGroup(
        "acVerticalAngleControls",
        "acVerticalAngle",
        acVerticalAngles.map(String),
        String(Math.round(Number(metadata.vertical_angle_deg ?? 15))),
        null,
        value => `${value}°`
      );

      const slider = document.getElementById("acTargetTemperature");
      slider.value = String(Math.round(Number(metadata.target_temperature ?? 24)));
      syncAcTemperatureReadout();

      document.querySelectorAll("#acModeControls input, #acHorizontalModeControls input, #acHorizontalAngleControls input, #acVerticalModeControls input, #acVerticalAngleControls input")
        .forEach(input => input.addEventListener("change", () => {
          syncAcAngleControlState();
          loadScenario();
        }));
      slider.addEventListener("input", syncAcTemperatureReadout);
      slider.addEventListener("change", () => loadScenario());
      syncAcAngleControlState();
    }

    function setupWindowPresetControls() {
      const seasonLabels = Object.fromEntries(windowPresetData.seasonOrder.map(name => [name, windowPresetData.seasons[name].zh]));
      const weatherLabels = Object.fromEntries(windowPresetData.weatherOrder.map(name => [name, windowPresetData.weathers[name].zh]));
      const timeLabels = Object.fromEntries(windowPresetData.timeOrder.map(name => [name, windowPresetData.times[name].zh]));

      renderRadioGroup("windowSeasonControls", "windowSeason", windowPresetData.seasonOrder, "summer", seasonLabels);
      renderRadioGroup("windowWeatherControls", "windowWeather", windowPresetData.weatherOrder, "sunny", weatherLabels);
      renderRadioGroup("windowTimeControls", "windowTime", windowPresetData.timeOrder, "morning", timeLabels);

      document.querySelectorAll("#windowSeasonControls input, #windowWeatherControls input, #windowTimeControls input")
        .forEach(input => input.addEventListener("change", () => syncWindowPresetSummary()));
      document.getElementById("directOutdoorTemperature").addEventListener("input", () => syncWindowPresetSummary());
      syncWindowPresetSummary();
    }

    function renderRadioGroup(containerId, name, options, selected, labelsMap = null, formatter = null) {
      const container = document.getElementById(containerId);
      container.innerHTML = options.map(option => {
        const label = formatter ? formatter(option) : (labelsMap ? labelsMap[option] : option);
        return `
          <label class="metric-toggle">
            <input type="radio" name="${name}" value="${option}" ${String(option) === String(selected) ? "checked" : ""}>
            <span>${label}</span>
          </label>
        `;
      }).join("");
    }

    function syncAcTemperatureReadout() {
      const value = document.getElementById("acTargetTemperature").value;
      document.getElementById("acTargetTemperatureValue").textContent = `${value}°C`;
    }

    function syncElapsedTimeReadout() {
      const value = Number(document.getElementById("elapsedMinutes").value || "18");
      document.getElementById("elapsedMinutesValue").textContent = `${value} min`;
      syncElapsedTimelineStatus();
    }

    function syncPlaybackSpeed() {
      const selected = selectedChoice("playbackSpeed", "2x");
      const option = playbackSpeedOptions.find(item => item.value === selected) || playbackSpeedOptions[1];
      elapsedPlayback.delayMs = option.delayMs;
    }

    function formatDelta(value, unit) {
      const numeric = Number(value);
      const sign = numeric > 0 ? "+" : "";
      return `${sign}${fmt(numeric)} ${unit}`;
    }

    function selectedElapsedMinutes() {
      return Number(document.getElementById("elapsedMinutes").value || "18");
    }

    function setElapsedMinutes(value) {
      document.getElementById("elapsedMinutes").value = String(clamp(Number(value), 0, 120));
      syncElapsedTimeReadout();
    }

    function updateElapsedPlaybackButton() {
      const button = document.getElementById("elapsedPlayButton");
      if (!button) return;
      button.textContent = elapsedPlayback.running ? "Pause Playback" : "Play Timeline";
    }

    function stopElapsedPlayback() {
      if (!elapsedPlayback.running) return;
      elapsedPlayback.running = false;
      updateElapsedPlaybackButton();
    }

    async function toggleElapsedPlayback() {
      if (elapsedPlayback.running) {
        stopElapsedPlayback();
        return;
      }
      elapsedPlayback.running = true;
      updateElapsedPlaybackButton();
      if (selectedElapsedMinutes() >= 120) {
        setElapsedMinutes(0);
      }
      try {
        while (elapsedPlayback.running && selectedElapsedMinutes() < 120) {
          setElapsedMinutes(selectedElapsedMinutes() + elapsedPlayback.stepMinutes);
          await refreshActiveContext();
          if (!elapsedPlayback.running || selectedElapsedMinutes() >= 120) {
            break;
          }
          await sleep(elapsedPlayback.delayMs);
        }
      } finally {
        elapsedPlayback.running = false;
        updateElapsedPlaybackButton();
      }
    }

    async function resetElapsedPlayback() {
      stopElapsedPlayback();
      setElapsedMinutes(0);
      await refreshActiveContext();
    }

    function sleep(ms) {
      return new Promise(resolve => window.setTimeout(resolve, ms));
    }

    function resetDeviceControls() {
      document.querySelectorAll("#deviceControls input[type='checkbox']").forEach(input => {
        input.checked = false;
      });
      loadScenario();
    }

    function scenarioQuery() {
      const params = new URLSearchParams({ name: activeScenario });
      Object.entries(deviceOverrides()).forEach(([name, value]) => {
        params.set(name, String(value));
      });
      Object.entries(furnitureOverrides()).forEach(([name, value]) => {
        params.set(name, String(value));
      });
      Object.entries(acSettings()).forEach(([name, value]) => {
        params.set(name, String(value));
      });
      Object.entries(indoorBaselineParams()).forEach(([name, value]) => {
        params.set(name, String(value));
      });
      if (customFurnitureItems.length) {
        params.set("custom_furniture", JSON.stringify(customFurniturePayload()));
      }
      params.set("elapsed_minutes", String(selectedElapsedMinutes()));
      params.set("use_hybrid_residual", hybridResidualEnabled() ? "1" : "0");
      return params.toString();
    }

    function deviceOverrides() {
      const overrides = {};
      document.querySelectorAll("#deviceControls input[type='checkbox']").forEach(input => {
        const activation = Number(input.dataset.activation || "1");
        overrides[input.dataset.device] = input.checked ? activation : 0.0;
      });
      return overrides;
    }

    function furnitureOverrides() {
      const overrides = {};
      document.querySelectorAll("#furnitureControls input[type='checkbox']").forEach(input => {
        const activation = Number(input.dataset.activation || "1");
        overrides[input.dataset.furniture] = input.checked ? activation : 0.0;
      });
      return overrides;
    }

    function customFurniturePayload() {
      return customFurnitureItems.map(item => ({
        name: item.name,
        kind: item.kind,
        activation: item.activation,
        min_corner: item.min_corner,
        max_corner: item.max_corner,
        metadata: item.metadata
      }));
    }

    function acSettings() {
      return {
        ac_mode: selectedChoice("acMode", "cool"),
        ac_target_temperature: Number(document.getElementById("acTargetTemperature").value || "24"),
        ac_horizontal_mode: selectedChoice("acHorizontalMode", "fixed"),
        ac_horizontal_angle_deg: Number(selectedChoice("acHorizontalAngle", "0")),
        ac_vertical_mode: selectedChoice("acVerticalMode", "fixed"),
        ac_vertical_angle_deg: Number(selectedChoice("acVerticalAngle", "15"))
      };
    }

    function indoorBaselineParams() {
      return {
        indoor_temperature: Number(document.getElementById("baselineIndoorTemperature").value || "29"),
        indoor_humidity: Number(document.getElementById("baselineIndoorHumidity").value || "67"),
        base_illuminance: Number(document.getElementById("baselineIlluminance").value || "90")
      };
    }

    function hybridResidualEnabled() {
      return document.getElementById("useHybridResidual")?.checked ?? false;
    }

    function selectedChoice(name, fallback) {
      return document.querySelector(`input[name='${name}']:checked`)?.value || fallback;
    }

    function syncAcAngleControlState() {
      const horizontalFixed = selectedChoice("acHorizontalMode", "fixed") === "fixed";
      const verticalFixed = selectedChoice("acVerticalMode", "fixed") === "fixed";
      setRadioGroupDisabled("acHorizontalAngleControls", !horizontalFixed);
      setRadioGroupDisabled("acVerticalAngleControls", !verticalFixed);
    }

    function setRadioGroupDisabled(containerId, disabled) {
      const container = document.getElementById(containerId);
      container.querySelectorAll("label.metric-toggle").forEach(label => {
        label.classList.toggle("disabled", disabled);
      });
      container.querySelectorAll("input").forEach(input => {
        input.disabled = disabled;
      });
    }

    function selectedWindowPreset() {
      return {
        season: selectedChoice("windowSeason", "summer"),
        weather: selectedChoice("windowWeather", "sunny"),
        time: selectedChoice("windowTime", "morning"),
      };
    }

    function computeWindowPresetValues() {
      const preset = selectedWindowPreset();
      const season = windowPresetData.seasons[preset.season];
      const weather = windowPresetData.weathers[preset.weather];
      const time = windowPresetData.times[preset.time];
      return {
        season,
        weather,
        time,
        indoorTemperature: Number(season.indoor_temperature),
        indoorHumidity: Number(season.indoor_humidity),
        outdoorTemperature: Number(season.outdoor_temperature) + Number(weather.temperature_delta) + Number(time.temperature_delta),
        outdoorHumidity: clamp(Number(season.outdoor_humidity) + Number(weather.humidity_delta), 0, 100),
        sunlightIlluminance: Number(season.sunlight_illuminance) * Number(weather.sunlight_factor) * Number(time.sunlight_factor),
      };
    }

    function syncWindowPresetSummary() {
      const values = computeWindowPresetValues();
      document.getElementById("windowPresetSummary").innerHTML = [
        `Selected preset: ${values.season.zh} / ${values.weather.zh} / ${values.time.zh}`,
        `Preset-derived RH ${fmt(values.outdoorHumidity)}%, Sun ${fmt(values.sunlightIlluminance)} lx, suggested outdoor T ${fmt(values.outdoorTemperature)}°C`,
        `Indoor baseline comes from the panel above. Current manual outdoor T input: ${fmt(Number(document.getElementById("directOutdoorTemperature").value || values.outdoorTemperature))}°C`
      ].join("<br>");
    }

    function applyWindowPreset() {
      const values = computeWindowPresetValues();
      document.getElementById("directOutdoorTemperature").value = String(Number(values.outdoorTemperature.toFixed(2)));
      syncWindowPresetSummary();
      loadDirectWindow();
    }

    function renderZoneCards(data) {
      const values = data.target_zone_estimated;
      setEstimatorStatus(data.estimator || null);
      document.getElementById("zoneCards").innerHTML = metrics.map(metric => `
        <div class="card">
          <div class="metric">${labels[metric]}</div>
          <div class="value">${fmt(values[metric])}</div>
          <div class="status">MAE ${fmt(data.field_mae[metric])}</div>
        </div>
      `).join("");
    }

    function renderTimeline(data) {
      const container = document.getElementById("timelineCharts");
      currentTimeline = data?.points?.length ? data : null;
      if (!data?.points?.length) {
        container.innerHTML = `<p class="status">No timeline data available.</p>`;
        syncElapsedTimelineStatus();
        return;
      }
      container.innerHTML = metrics.map(metric => timelineCard(metric, data)).join("");
      syncElapsedTimelineStatus();
    }

    function timelineCard(metric, data) {
      const width = 320;
      const height = 180;
      const padding = { left: 40, right: 12, top: 12, bottom: 28 };
      const values = data.points.map(point => Number(point.target_zone_values[metric]));
      const minValue = Math.min(...values);
      const maxValue = Math.max(...values);
      const rangeMin = minValue === maxValue ? minValue - 1 : minValue;
      const rangeMax = minValue === maxValue ? maxValue + 1 : maxValue;
      const duration = Math.max(Number(data.duration_minutes || 0), 1);
      const current = nearestTimelinePoint(data.points, Number(data.current_elapsed_minutes || 0));

      const polyline = data.points.map(point => {
        const x = padding.left + (Number(point.elapsed_minutes) / duration) * (width - padding.left - padding.right);
        const y = padding.top + (1 - metricFraction(Number(point.target_zone_values[metric]), { min: rangeMin, max: rangeMax })) * (height - padding.top - padding.bottom);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
      const currentX = padding.left + (Number(current.elapsed_minutes) / duration) * (width - padding.left - padding.right);
      const currentY = padding.top + (1 - metricFraction(Number(current.target_zone_values[metric]), { min: rangeMin, max: rangeMax })) * (height - padding.top - padding.bottom);

      return `
        <div class="timeline-card">
          <div class="metric">${labels[metric]}</div>
          <svg class="timeline-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${labels[metric]} time evolution">
            <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#cdbca0" stroke-width="1.5" />
            <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}" stroke="#cdbca0" stroke-width="1.5" />
            <polyline fill="none" stroke="${timelineColors[metric]}" stroke-width="3" points="${polyline}" />
            <line x1="${currentX.toFixed(1)}" y1="${padding.top}" x2="${currentX.toFixed(1)}" y2="${height - padding.bottom}" stroke="#17211b" stroke-dasharray="4 4" stroke-width="1.5" />
            <circle cx="${currentX.toFixed(1)}" cy="${currentY.toFixed(1)}" r="4.5" fill="${timelineColors[metric]}" stroke="#17211b" stroke-width="1.5" />
            <text x="${padding.left}" y="${padding.top - 2}" fill="#69776e" font-size="11">${rangeMax.toFixed(1)} ${units[metric]}</text>
            <text x="${padding.left}" y="${height - 8}" fill="#69776e" font-size="11">${rangeMin.toFixed(1)} ${units[metric]}</text>
            <text x="${padding.left}" y="${height - padding.bottom + 18}" fill="#69776e" font-size="11">0 min</text>
            <text x="${width - padding.right - 40}" y="${height - 8}" fill="#69776e" font-size="11">${duration.toFixed(0)} min</text>
          </svg>
          <div class="status">Current ${Number(current.elapsed_minutes).toFixed(1)} min: ${fmt(current.target_zone_values[metric])} ${units[metric]}</div>
        </div>
      `;
    }

    function nearestTimelinePoint(points, minute) {
      return points.reduce((best, point) => {
        if (!best) return point;
        return Math.abs(Number(point.elapsed_minutes) - minute) < Math.abs(Number(best.elapsed_minutes) - minute) ? point : best;
      }, null);
    }

    function syncElapsedTimelineStatus() {
      const container = document.getElementById("elapsedTimelineStatus");
      if (!container) return;
      if (!currentTimeline?.points?.length) {
        container.textContent = "Current minute and remaining change will appear here.";
        return;
      }
      const current = nearestTimelinePoint(currentTimeline.points, selectedElapsedMinutes());
      const steadyState = currentTimeline.points[currentTimeline.points.length - 1];
      const remaining = metrics.map(metric => {
        const delta = Number(steadyState.target_zone_values[metric]) - Number(current.target_zone_values[metric]);
        return `${labels[metric]} ${formatDelta(delta, units[metric])}`;
      }).join(", ");
      container.textContent = `Current ${Number(current.elapsed_minutes).toFixed(1)} min. Remaining to quasi-steady state: ${remaining}.`;
    }

    function renderRecommendations(data) {
      const estimatorNote = data.estimator?.label ? `<p class="status">Ranking estimator: ${data.estimator.label}.</p>` : "";
      document.getElementById("recommendations").innerHTML = estimatorNote + table(
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
      const estimatorNote = data.estimator?.label ? `<p class="status">Estimator under comparison: ${data.estimator.label}.</p>` : "";
      document.getElementById("baseline").innerHTML = estimatorNote + table(
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
      const note = [
        data.estimator?.label ? `Estimator context: ${data.estimator.label}.` : null,
        data.estimator_note || null
      ].filter(Boolean).join(" ");
      document.getElementById("impacts").innerHTML = `${note ? `<p class="status">${note}</p>` : ""}` + table(
        ["Device", "Temperature", "Humidity", "Illuminance"],
        data.learned_device_impacts.map(item => [
          item.device_name,
          fmt(item.metric_coefficients.temperature),
          fmt(item.metric_coefficients.humidity),
          fmt(item.metric_coefficients.illuminance)
        ])
      );
    }

    function renderHeatmapsForScenario(name) {
      document.getElementById("heatmaps").innerHTML = metrics.map(metric => `
        <img src="/outputs/${name}_${metric}_3d.svg" alt="${name} ${metric} 3D heatmap">
      `).join("");
    }

    function renderDirectHeatmapNotice() {
      document.getElementById("heatmaps").innerHTML = `
        <p class="status">Static SVG snapshots are generated only for named validation scenarios. Direct window mode is shown in the rotatable 3D preview above.</p>
      `;
    }

    function setupVolumeControls() {
      const container = document.getElementById("metricControls");
      container.innerHTML = metrics.map(metric => `
        <label class="metric-toggle">
          <input type="checkbox" data-metric="${metric}" ${metric === volumeMetric ? "checked" : ""}>
          <span>${labels[metric]}</span>
        </label>
      `).join("");
      container.querySelectorAll("input[type='checkbox']").forEach(input => {
        input.addEventListener("change", () => {
          if (!input.checked) {
            input.checked = true;
            return;
          }
          volumeMetric = input.dataset.metric;
          container.querySelectorAll("input[type='checkbox']").forEach(other => {
            if (other !== input) other.checked = false;
          });
          drawVolume();
        });
      });

      const canvas = document.getElementById("volumeCanvas");
      canvas.addEventListener("pointerdown", event => {
        const handle = findCustomFurnitureHandle(event);
        if (handle) {
          stopElapsedPlayback();
          volumeInteraction = {
            mode: "move_furniture",
            pointerId: event.pointerId,
            itemName: handle.name,
            x: event.clientX,
            y: event.clientY,
            startState: snapshotCustomFurniture(handle.name),
          };
          canvas.setPointerCapture(event.pointerId);
          document.getElementById("volumeStatus").textContent = `Dragging ${handle.label}. Release to recompute the field.`;
          return;
        }
        volumeInteraction = { mode: "rotate", pointerId: event.pointerId, x: event.clientX, y: event.clientY };
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointermove", async event => {
        if (!volumeInteraction) return;
        if (volumeInteraction.mode === "move_furniture") {
          const item = customFurnitureItems.find(candidate => candidate.name === volumeInteraction.itemName);
          const startState = volumeInteraction.startState;
          if (!item || !startState) return;
          moveCustomFurnitureFromDrag(
            item.name,
            startState,
            event.clientX - volumeInteraction.x,
            event.clientY - volumeInteraction.y
          );
          drawVolume();
          return;
        }
        const dx = event.clientX - volumeInteraction.x;
        const dy = event.clientY - volumeInteraction.y;
        volumeRotation.yaw += dx * 0.012;
        volumeRotation.pitch = clamp(volumeRotation.pitch + dy * 0.012, -1.35, 1.1);
        volumeInteraction = { ...volumeInteraction, x: event.clientX, y: event.clientY };
        drawVolume();
      });
      canvas.addEventListener("pointerup", async event => {
        if (volumeInteraction?.mode === "move_furniture") {
          volumeInteraction = null;
          canvas.releasePointerCapture(event.pointerId);
          syncCustomFurnitureList();
          await refreshActiveContext();
          return;
        }
        volumeInteraction = null;
        canvas.releasePointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointercancel", () => {
        volumeInteraction = null;
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
      volumeFurnitureHandles = [];
      const estimatorLabel = data.estimator?.label ? `, estimator: ${data.estimator.label}` : "";
      const activeFurniture = (data.furniture || []).filter(item => Number(item.activation) > 0).length;
      document.getElementById("volumeStatus").textContent = `${data.scenario}: ${data.points.length} samples, ${data.devices.length} appliance markers, ${activeFurniture} active furniture blockers${estimatorLabel}.`;
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
      drawFurnitureMarkers(ctx, projector);
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
        if (["wall_rectangle", "wall_bar"].includes(device.geometry?.shape)) {
          drawWallSurface(ctx, project, device);
          return;
        }
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

        const label = deviceLabel(device);
        ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
        const labelWidth = ctx.measureText(label).width;
        ctx.fillStyle = "rgba(255, 253, 247, 0.86)";
        roundedRect(ctx, projected.x + 12, projected.y - 24, labelWidth + 12, 20, 8);
        ctx.fill();
        ctx.fillStyle = "#17211b";
        ctx.fillText(label, projected.x + 18, projected.y - 10);
      });
    }

    function drawFurnitureMarkers(ctx, project) {
      volumeFurnitureHandles = [];
      (volumeData.furniture || [])
        .filter(item => Number(item.activation) > 0)
        .forEach(item => drawFurnitureBox(ctx, project, item));
    }

    function drawFurnitureBox(ctx, project, item) {
      const minCorner = item.min_corner;
      const maxCorner = item.max_corner;
      const corners3d = [
        { x: minCorner.x, y: minCorner.y, z: minCorner.z },
        { x: maxCorner.x, y: minCorner.y, z: minCorner.z },
        { x: maxCorner.x, y: maxCorner.y, z: minCorner.z },
        { x: minCorner.x, y: maxCorner.y, z: minCorner.z },
        { x: minCorner.x, y: minCorner.y, z: maxCorner.z },
        { x: maxCorner.x, y: minCorner.y, z: maxCorner.z },
        { x: maxCorner.x, y: maxCorner.y, z: maxCorner.z },
        { x: minCorner.x, y: maxCorner.y, z: maxCorner.z }
      ];
      const corners = corners3d.map(project);
      const color = furnitureColors[item.kind] || "#7a4a2c";
      const faces = [
        { indices: [0, 1, 2, 3], alpha: 0.08 },
        { indices: [4, 5, 6, 7], alpha: 0.14 },
        { indices: [0, 1, 5, 4], alpha: 0.16 },
        { indices: [1, 2, 6, 5], alpha: 0.24 },
        { indices: [2, 3, 7, 6], alpha: 0.2 },
        { indices: [3, 0, 4, 7], alpha: 0.12 }
      ]
        .map(face => ({
          ...face,
          depth: face.indices.reduce((sum, index) => sum + corners[index].depth, 0) / face.indices.length
        }))
        .sort((a, b) => a.depth - b.depth);

      faces.forEach(face => {
        const points = face.indices.map(index => corners[index]);
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        points.slice(1).forEach(point => ctx.lineTo(point.x, point.y));
        ctx.closePath();
        ctx.fillStyle = colorWithAlpha(color, face.alpha);
        ctx.strokeStyle = colorWithAlpha(color, 0.72);
        ctx.lineWidth = 1.4;
        ctx.fill();
        ctx.stroke();
      });

      const center = project(item.center);
      const label = furnitureLabel(item);
      if (item.metadata?.custom) {
        volumeFurnitureHandles.push({
          name: item.name,
          label,
          x: center.x,
          y: center.y,
          radius: 20
        });
      }
      ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
      const labelWidth = ctx.measureText(label).width;
      ctx.fillStyle = "rgba(255, 253, 247, 0.88)";
      roundedRect(ctx, center.x + 12, center.y - 24, labelWidth + 12, 20, 8);
      ctx.fill();
      ctx.fillStyle = "#17211b";
      ctx.fillText(label, center.x + 18, center.y - 10);
    }

    function findCustomFurnitureHandle(event) {
      const canvas = document.getElementById("volumeCanvas");
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      let best = null;
      volumeFurnitureHandles.forEach(handle => {
        const dx = x - handle.x;
        const dy = y - handle.y;
        const distance = Math.hypot(dx, dy);
        if (distance > handle.radius) return;
        if (!best || distance < best.distance) {
          best = { ...handle, distance };
        }
      });
      return best;
    }

    function snapshotCustomFurniture(name) {
      const item = customFurnitureItems.find(candidate => candidate.name === name);
      if (!item) return null;
      return JSON.parse(JSON.stringify(item));
    }

    function moveCustomFurnitureFromDrag(name, startState, dxScreen, dyScreen) {
      const item = customFurnitureItems.find(candidate => candidate.name === name);
      if (!item || !startState) return;
      const room = currentRoomDimensions();
      const scale = currentVolumeScale();
      if (scale <= 1e-9) return;
      const roomDelta = projectScreenDeltaToRoomDelta(dxScreen, dyScreen, scale);
      const sizeX = Number(startState.max_corner.x) - Number(startState.min_corner.x);
      const sizeY = Number(startState.max_corner.y) - Number(startState.min_corner.y);
      const minX = snapToGrid(clamp(Number(startState.min_corner.x) + roomDelta.x, 0, room.width - sizeX));
      const minY = snapToGrid(clamp(Number(startState.min_corner.y) + roomDelta.y, 0, room.length - sizeY));
      const minZ = Number(startState.min_corner.z);
      const maxZ = Number(startState.max_corner.z);
      const maxX = snapToGrid(minX + sizeX);
      const maxY = snapToGrid(minY + sizeY);
      const proposedMin = { x: minX, y: minY, z: minZ };
      const proposedMax = { x: maxX, y: maxY, z: maxZ };
      if (customFurnitureCollides(name, proposedMin, proposedMax)) {
        document.getElementById("status").textContent = `${item.metadata?.label || item.name} cannot overlap another active blocker.`;
        return;
      }
      item.min_corner = proposedMin;
      item.max_corner = proposedMax;
      syncLiveFurnitureData(item);
    }

    function currentVolumeScale() {
      const canvas = document.getElementById("volumeCanvas");
      if (!canvas) return 1;
      const rect = canvas.getBoundingClientRect();
      return Math.min(rect.width / 9.2, rect.height / 6.3) * volumeZoom;
    }

    function projectScreenDeltaToRoomDelta(dxScreen, dyScreen, scale) {
      const yaw = volumeRotation.yaw;
      const pitch = volumeRotation.pitch;
      const cy = Math.cos(yaw);
      const sy = Math.sin(yaw);
      const cp = Math.max(Math.cos(pitch), 1e-6);
      const sx = dxScreen / scale;
      const syProjected = dyScreen / scale;
      return {
        x: cy * sx + sy * (syProjected / cp),
        y: -sy * sx + cy * (syProjected / cp),
      };
    }

    function syncLiveFurnitureData(item) {
      if (!volumeData?.furniture) return;
      const target = volumeData.furniture.find(candidate => candidate.name === item.name);
      if (!target) return;
      target.activation = item.activation;
      target.min_corner = { ...item.min_corner };
      target.max_corner = { ...item.max_corner };
      target.center = {
        x: (Number(item.min_corner.x) + Number(item.max_corner.x)) / 2,
        y: (Number(item.min_corner.y) + Number(item.max_corner.y)) / 2,
        z: (Number(item.min_corner.z) + Number(item.max_corner.z)) / 2,
      };
      target.size = {
        x: Number(item.max_corner.x) - Number(item.min_corner.x),
        y: Number(item.max_corner.y) - Number(item.min_corner.y),
        z: Number(item.max_corner.z) - Number(item.min_corner.z),
      };
      target.metadata = { ...item.metadata };
    }

    function snapToGrid(value, step = 0.1) {
      return Math.round(Number(value) / step) * step;
    }

    function customFurnitureCollides(name, minCorner, maxCorner) {
      const activeFurniture = (volumeData?.furniture || []).filter(item => Number(item.activation) > 0 && item.name !== name);
      return activeFurniture.some(item => boxesOverlap(minCorner, maxCorner, item.min_corner, item.max_corner));
    }

    function boxesOverlap(aMin, aMax, bMin, bMax) {
      return (
        Number(aMin.x) < Number(bMax.x) && Number(aMax.x) > Number(bMin.x) &&
        Number(aMin.y) < Number(bMax.y) && Number(aMax.y) > Number(bMin.y) &&
        Number(aMin.z) < Number(bMax.z) && Number(aMax.z) > Number(bMin.z)
      );
    }

    function drawWallSurface(ctx, project, device) {
      const width = device.geometry.width || 1.4;
      const height = device.geometry.height || 1.1;
      const center = device.position;
      const color = deviceColors[device.kind] || "#b4552b";
      const yMin = clamp(center.y - width / 2, 0, volumeData.room.length);
      const yMax = clamp(center.y + width / 2, 0, volumeData.room.length);
      const zMin = clamp(center.z - height / 2, 0, volumeData.room.height);
      const zMax = clamp(center.z + height / 2, 0, volumeData.room.height);
      const corners = [
        project({ x: center.x, y: yMin, z: zMin }),
        project({ x: center.x, y: yMax, z: zMin }),
        project({ x: center.x, y: yMax, z: zMax }),
        project({ x: center.x, y: yMin, z: zMax })
      ];
      ctx.beginPath();
      ctx.moveTo(corners[0].x, corners[0].y);
      corners.slice(1).forEach(point => ctx.lineTo(point.x, point.y));
      ctx.closePath();
      ctx.fillStyle = colorWithAlpha(color, 0.24);
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.fill();
      ctx.stroke();

      const projected = project(center);
      const label = deviceLabel(device);
      ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
      const labelWidth = ctx.measureText(label).width;
      ctx.fillStyle = "rgba(255, 253, 247, 0.88)";
      roundedRect(ctx, projected.x + 12, projected.y - 24, labelWidth + 12, 20, 8);
      ctx.fill();
      ctx.fillStyle = "#17211b";
      ctx.fillText(label, projected.x + 18, projected.y - 10);
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

    function colorWithAlpha(hex, alpha) {
      const value = hex.replace("#", "");
      const red = parseInt(value.slice(0, 2), 16);
      const green = parseInt(value.slice(2, 4), 16);
      const blue = parseInt(value.slice(4, 6), 16);
      return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
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

    function deviceLabel(device) {
      if (device.kind !== "ac") {
        return `${device.name} (${device.kind}, ${Math.round(device.activation * 100)}%)`;
      }
      const meta = device.metadata || {};
      const mode = String(meta.ac_mode || "cool").toUpperCase();
      const target = Math.round(Number(meta.target_temperature || 24));
      const lr = meta.horizontal_mode === "swing" ? "LR swing" : `LR ${Math.round(Number(meta.horizontal_angle_deg || 0))}°`;
      const ud = meta.vertical_mode === "swing" ? "UD swing" : `UD ${Math.round(Number(meta.vertical_angle_deg || 15))}°`;
      return `${device.name} (${mode} ${target}°C, ${lr}, ${ud})`;
    }

    function furnitureLabel(item) {
      const label = item.metadata?.label || item.name;
      return `${label} (${Math.round(Number(item.activation || 0) * 100)}%)`;
    }

    function currentRoomDimensions() {
      if (volumeData?.room) {
        return volumeData.room;
      }
      const scenario = scenarioMetadata[activeScenario];
      if (scenario?.room) {
        return scenario.room;
      }
      return { width: 6.0, length: 4.0, height: 3.0 };
    }

    function sanitizeFurnitureKind(value) {
      const normalized = String(value || "custom").trim().toLowerCase().replace(/[^a-z0-9_\\-]/g, "_");
      return normalized || "custom";
    }

    function directWindowParams() {
      const preset = computeWindowPresetValues();
      const params = new URLSearchParams({
        outdoor_temperature: document.getElementById("directOutdoorTemperature").value,
        outdoor_humidity: String(Number(preset.outdoorHumidity.toFixed(2))),
        sunlight_illuminance: String(Number(preset.sunlightIlluminance.toFixed(2))),
        opening_ratio: document.getElementById("directOpening").value,
        indoor_temperature: document.getElementById("baselineIndoorTemperature").value,
        indoor_humidity: document.getElementById("baselineIndoorHumidity").value,
        base_illuminance: document.getElementById("baselineIlluminance").value,
        elapsed_minutes: String(selectedElapsedMinutes()),
        use_hybrid_residual: hybridResidualEnabled() ? "1" : "0"
      });
      Object.entries(furnitureOverrides()).forEach(([name, value]) => {
        params.set(name, String(value));
      });
      if (customFurnitureItems.length) {
        params.set("custom_furniture", JSON.stringify(customFurniturePayload()));
      }
      return params;
    }

    function renderDirectWindowResult(data) {
      const container = document.getElementById("windowDirectResult");
      const activeFurniture = (data.furniture || [])
        .filter(item => Number(item.activation) > 0)
        .map(item => item.metadata?.label || item.name);
      container.innerHTML = `
        <p class="status">Direct input mode at ${fmt(data.input.elapsed_minutes)} min, window opening ${Math.round(data.input.opening_ratio * 100)}%, target zone: ${data.target_zone}, estimator: ${data.estimator?.label || "n/a"}, active blockers: ${activeFurniture.length ? activeFurniture.join(", ") : "none"}.</p>
        ${table(
          ["Input", "Window Zone", "Center Zone", "Door-Side Zone"],
          [[
            [
              `Outdoor T: ${fmt(data.environment.outdoor_temperature)}`,
              `Outdoor H: ${fmt(data.environment.outdoor_humidity)}`,
              `Sun: ${fmt(data.environment.sunlight_illuminance)}`,
              `Indoor T: ${fmt(data.input.indoor_temperature)}`,
              `Indoor H: ${fmt(data.input.indoor_humidity)}`,
              `Base lx: ${fmt(data.input.base_illuminance)}`
            ].join("<br>"),
            metrics.map(metric => `${labels[metric]}: ${fmt(data.zone_estimated.window_zone[metric])}`).join("<br>"),
            metrics.map(metric => `${labels[metric]}: ${fmt(data.zone_estimated.center_zone[metric])}`).join("<br>"),
            metrics.map(metric => `${labels[metric]}: ${fmt(data.zone_estimated.door_side_zone[metric])}`).join("<br>")
          ]]
        )}
      `;
    }

    async function loadDirectWindow(updateDashboard = true) {
      const container = document.getElementById("windowDirectResult");
      container.innerHTML = `<p class="status">Running direct window simulation...</p>`;
      const params = directWindowParams();
      if (!updateDashboard) {
        const data = await getJSON(`/api/window_direct?${params.toString()}`);
        renderDirectWindowResult(data);
        return;
      }

      activeContext = { kind: "window_direct" };
      document.getElementById("status").textContent = "Running direct window dashboard...";
      const bundle = await getJSON(`/api/window_direct_dashboard?${params.toString()}`);
      renderDirectWindowResult(bundle.scenario);
      renderZoneCards(bundle.scenario);
      renderRecommendations(bundle.ranking);
      renderBaseline(bundle.baseline);
      renderImpacts(bundle.impacts);
      setVolumeData(bundle.volume);
      renderTimeline(bundle.timeline);
      renderDirectHeatmapNotice();
      await samplePoint();
      document.getElementById("status").textContent = "Loaded direct window dashboard.";
    }

    async function samplePoint() {
      const x = document.getElementById("x").value;
      const y = document.getElementById("y").value;
      const z = document.getElementById("z").value;
      let data;
      if (activeContext.kind === "window_direct") {
        const params = directWindowParams();
        params.set("x", x);
        params.set("y", y);
        params.set("z", z);
        data = await getJSON(`/api/window_direct_sample?${params.toString()}`);
      } else {
        const params = new URLSearchParams(scenarioQuery());
        params.set("x", x);
        params.set("y", y);
        params.set("z", z);
        data = await getJSON(`/api/sample?${params.toString()}`);
      }
      document.getElementById("sample").textContent = JSON.stringify(data, null, 2);
    }

    function setEstimatorStatus(estimator) {
      const sidebar = document.getElementById("hybridEstimatorStatus");
      const banner = document.getElementById("estimatorStatus");
      if (!sidebar || !banner) return;
      if (!estimator) {
        const text = hybridResidualEnabled()
          ? "Hybrid residual correction requested. The demo will use the saved checkpoint when it is available."
          : "Using the trilinear-corrected appliance influence field only.";
        sidebar.textContent = text;
        banner.textContent = text;
        return;
      }
      if (estimator.requested && estimator.applied) {
        const text = `Estimator: ${estimator.label}. Saved checkpoint loaded from outputs and applied on top of the physics model.`;
        sidebar.textContent = text;
        banner.textContent = text;
        return;
      }
      if (estimator.requested && !estimator.applied) {
        const text = "Hybrid residual correction was requested, but no checkpoint is available. Falling back to the trilinear-corrected appliance influence field.";
        sidebar.textContent = text;
        banner.textContent = text;
        return;
      }
      const text = `Estimator: ${estimator.label}.`;
      sidebar.textContent = text;
      banner.textContent = text;
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

INDEX_HTML = INDEX_HTML.replace("__WINDOW_PRESET_DATA__", WINDOW_PRESET_DATA)


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
                query = parse_qs(parsed.query)
                self._send_json(
                    evaluate_scenario(
                        _query_name(parsed.query),
                        _query_device_overrides(parsed.query),
                        _query_device_metadata_overrides(parsed.query),
                        _query_furniture_overrides(parsed.query),
                        _query_float(query, "indoor_temperature", 29.0),
                        _query_float(query, "indoor_humidity", 67.0),
                        _query_float(query, "base_illuminance", 90.0),
                        _query_float(query, "elapsed_minutes", 18.0),
                        _query_bool(query, "use_hybrid_residual", False),
                        _query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/window_matrix":
                self._send_json(evaluate_window_matrix())
                return
            if parsed.path == "/api/window_direct":
                query = parse_qs(parsed.query)
                self._send_json(
                    evaluate_window_direct(
                        outdoor_temperature=_query_float(query, "outdoor_temperature", 33.0),
                        outdoor_humidity=_query_float(query, "outdoor_humidity", 74.0),
                        sunlight_illuminance=_query_float(query, "sunlight_illuminance", 32000.0),
                        opening_ratio=_query_float(query, "opening_ratio", 0.7),
                        furniture_overrides=_query_furniture_overrides(parsed.query),
                        indoor_temperature=_query_float(query, "indoor_temperature", 29.0),
                        indoor_humidity=_query_float(query, "indoor_humidity", 67.0),
                        base_illuminance=_query_float(query, "base_illuminance", 90.0),
                        elapsed_minutes=_query_float(query, "elapsed_minutes", 18.0),
                        use_hybrid_residual=_query_bool(query, "use_hybrid_residual", False),
                        extra_furniture=_query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/window_direct_dashboard":
                query = parse_qs(parsed.query)
                self._send_json(
                    evaluate_window_direct_dashboard(
                        outdoor_temperature=_query_float(query, "outdoor_temperature", 33.0),
                        outdoor_humidity=_query_float(query, "outdoor_humidity", 74.0),
                        sunlight_illuminance=_query_float(query, "sunlight_illuminance", 32000.0),
                        opening_ratio=_query_float(query, "opening_ratio", 0.7),
                        furniture_overrides=_query_furniture_overrides(parsed.query),
                        indoor_temperature=_query_float(query, "indoor_temperature", 29.0),
                        indoor_humidity=_query_float(query, "indoor_humidity", 67.0),
                        base_illuminance=_query_float(query, "base_illuminance", 90.0),
                        elapsed_minutes=_query_float(query, "elapsed_minutes", 18.0),
                        use_hybrid_residual=_query_bool(query, "use_hybrid_residual", False),
                        extra_furniture=_query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/volume":
                query = parse_qs(parsed.query)
                self._send_json(
                    get_scenario_volume(
                        _query_name(parsed.query),
                        _query_device_overrides(parsed.query),
                        _query_device_metadata_overrides(parsed.query),
                        _query_furniture_overrides(parsed.query),
                        _query_float(query, "indoor_temperature", 29.0),
                        _query_float(query, "indoor_humidity", 67.0),
                        _query_float(query, "base_illuminance", 90.0),
                        _query_float(query, "elapsed_minutes", 18.0),
                        _query_bool(query, "use_hybrid_residual", False),
                        _query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/rank_actions":
                query = parse_qs(parsed.query)
                self._send_json(
                    rank_scenario_actions(
                        _query_name(parsed.query),
                        _query_device_overrides(parsed.query),
                        _query_device_metadata_overrides(parsed.query),
                        _query_furniture_overrides(parsed.query),
                        _query_float(query, "indoor_temperature", 29.0),
                        _query_float(query, "indoor_humidity", 67.0),
                        _query_float(query, "base_illuminance", 90.0),
                        _query_float(query, "elapsed_minutes", 18.0),
                        _query_bool(query, "use_hybrid_residual", False),
                        _query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/compare_baseline":
                query = parse_qs(parsed.query)
                self._send_json(
                    compare_scenario_baseline(
                        _query_name(parsed.query),
                        _query_device_overrides(parsed.query),
                        _query_device_metadata_overrides(parsed.query),
                        _query_furniture_overrides(parsed.query),
                        _query_float(query, "indoor_temperature", 29.0),
                        _query_float(query, "indoor_humidity", 67.0),
                        _query_float(query, "base_illuminance", 90.0),
                        _query_float(query, "elapsed_minutes", 18.0),
                        _query_bool(query, "use_hybrid_residual", False),
                        _query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/learn_impacts":
                query = parse_qs(parsed.query)
                self._send_json(
                    learn_scenario_impacts(
                        _query_name(parsed.query),
                        _query_device_overrides(parsed.query),
                        _query_device_metadata_overrides(parsed.query),
                        _query_furniture_overrides(parsed.query),
                        _query_float(query, "indoor_temperature", 29.0),
                        _query_float(query, "indoor_humidity", 67.0),
                        _query_float(query, "base_illuminance", 90.0),
                        _query_float(query, "elapsed_minutes", 18.0),
                        _query_bool(query, "use_hybrid_residual", False),
                        _query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/timeline":
                query = parse_qs(parsed.query)
                self._send_json(
                    get_scenario_timeline(
                        _query_name(parsed.query),
                        _query_device_overrides(parsed.query),
                        _query_device_metadata_overrides(parsed.query),
                        _query_furniture_overrides(parsed.query),
                        _query_float(query, "indoor_temperature", 29.0),
                        _query_float(query, "indoor_humidity", 67.0),
                        _query_float(query, "base_illuminance", 90.0),
                        _query_float(query, "elapsed_minutes", 18.0),
                        use_hybrid_residual=_query_bool(query, "use_hybrid_residual", False),
                        extra_furniture=_query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/window_direct_timeline":
                query = parse_qs(parsed.query)
                self._send_json(
                    get_window_direct_timeline(
                        outdoor_temperature=_query_float(query, "outdoor_temperature", 33.0),
                        outdoor_humidity=_query_float(query, "outdoor_humidity", 74.0),
                        sunlight_illuminance=_query_float(query, "sunlight_illuminance", 32000.0),
                        opening_ratio=_query_float(query, "opening_ratio", 0.7),
                        furniture_overrides=_query_furniture_overrides(parsed.query),
                        indoor_temperature=_query_float(query, "indoor_temperature", 29.0),
                        indoor_humidity=_query_float(query, "indoor_humidity", 67.0),
                        base_illuminance=_query_float(query, "base_illuminance", 90.0),
                        elapsed_minutes=_query_float(query, "elapsed_minutes", 18.0),
                        use_hybrid_residual=_query_bool(query, "use_hybrid_residual", False),
                        extra_furniture=_query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/sample":
                query = parse_qs(parsed.query)
                self._send_json(
                    sample_scenario_point(
                        scenario_name=_query_name(parsed.query),
                        x=_query_float(query, "x", 3.0),
                        y=_query_float(query, "y", 2.0),
                        z=_query_float(query, "z", 1.5),
                        device_overrides=_query_device_overrides(parsed.query),
                        device_metadata_overrides=_query_device_metadata_overrides(parsed.query),
                        furniture_overrides=_query_furniture_overrides(parsed.query),
                        indoor_temperature=_query_float(query, "indoor_temperature", 29.0),
                        indoor_humidity=_query_float(query, "indoor_humidity", 67.0),
                        base_illuminance=_query_float(query, "base_illuminance", 90.0),
                        elapsed_minutes=_query_float(query, "elapsed_minutes", 18.0),
                        use_hybrid_residual=_query_bool(query, "use_hybrid_residual", False),
                        extra_furniture=_query_custom_furniture(parsed.query),
                    )
                )
                return
            if parsed.path == "/api/window_direct_sample":
                query = parse_qs(parsed.query)
                self._send_json(
                    sample_window_direct_point(
                        x=_query_float(query, "x", 3.0),
                        y=_query_float(query, "y", 2.0),
                        z=_query_float(query, "z", 1.5),
                        outdoor_temperature=_query_float(query, "outdoor_temperature", 33.0),
                        outdoor_humidity=_query_float(query, "outdoor_humidity", 74.0),
                        sunlight_illuminance=_query_float(query, "sunlight_illuminance", 32000.0),
                        opening_ratio=_query_float(query, "opening_ratio", 0.7),
                        furniture_overrides=_query_furniture_overrides(parsed.query),
                        indoor_temperature=_query_float(query, "indoor_temperature", 29.0),
                        indoor_humidity=_query_float(query, "indoor_humidity", 67.0),
                        base_illuminance=_query_float(query, "base_illuminance", 90.0),
                        elapsed_minutes=_query_float(query, "elapsed_minutes", 18.0),
                        use_hybrid_residual=_query_bool(query, "use_hybrid_residual", False),
                        extra_furniture=_query_custom_furniture(parsed.query),
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


def _query_bool(query: Dict[str, list], key: str, default: bool = False) -> bool:
    value = query.get(key, [default])[0]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _query_device_overrides(query_string: str) -> Dict[str, float]:
    query = parse_qs(query_string)
    overrides: Dict[str, float] = {}
    for name in DEVICE_OVERRIDE_NAMES:
        if name in query:
            overrides[name] = _query_float(query, name, 0.0)
    return overrides


def _query_furniture_overrides(query_string: str) -> Dict[str, float]:
    query = parse_qs(query_string)
    overrides: Dict[str, float] = {}
    for name in FURNITURE_OVERRIDE_NAMES:
        if name in query:
            overrides[name] = _query_float(query, name, 0.0)
    return overrides


def _query_custom_furniture(query_string: str):
    query = parse_qs(query_string)
    payload = query.get("custom_furniture", [None])[0]
    if not payload:
        return []
    try:
        decoded = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return decoded if isinstance(decoded, list) else []


def _query_device_metadata_overrides(query_string: str) -> Dict[str, Dict[str, object]]:
    query = parse_qs(query_string)
    ac_metadata: Dict[str, object] = {}

    ac_mode = query.get("ac_mode", [None])[0]
    if ac_mode in AC_MODE_OPTIONS:
        ac_metadata["ac_mode"] = ac_mode

    horizontal_mode = query.get("ac_horizontal_mode", [None])[0]
    if horizontal_mode in AC_SWING_OPTIONS:
        ac_metadata["horizontal_mode"] = horizontal_mode

    vertical_mode = query.get("ac_vertical_mode", [None])[0]
    if vertical_mode in AC_SWING_OPTIONS:
        ac_metadata["vertical_mode"] = vertical_mode

    if "ac_target_temperature" in query:
        ac_metadata["target_temperature"] = max(20.0, min(33.0, _query_float(query, "ac_target_temperature", 24.0)))
    if "ac_horizontal_angle_deg" in query:
        ac_metadata["horizontal_angle_deg"] = max(-60.0, min(60.0, _query_float(query, "ac_horizontal_angle_deg", 0.0)))
    if "ac_vertical_angle_deg" in query:
        ac_metadata["vertical_angle_deg"] = max(0.0, min(40.0, _query_float(query, "ac_vertical_angle_deg", 15.0)))

    if not ac_metadata:
        return {}
    return {"ac_main": ac_metadata}


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
