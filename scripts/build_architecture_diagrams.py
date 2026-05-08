import re
import subprocess
import tempfile
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MARKDOWN = ROOT / "docs" / "thesis" / "system_architecture_diagrams_zh.md"
OUTPUT_DIR = ROOT / "outputs" / "figures" / "architecture"
CANVAS_W = 1600
CANVAS_H = 900


STYLE = """
    <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <path d="M 0 0 L 12 6 L 0 12 z" fill="#334155"/>
    </marker>
    <marker id="arrowDash" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <path d="M 0 0 L 12 6 L 0 12 z" fill="#64748b"/>
    </marker>
    <style>
      .panel { fill: #f8fafc; stroke: #94a3b8; stroke-width: 2.2; rx: 22; }
      .blue { fill: #e0f2fe; stroke: #0284c7; stroke-width: 2.2; rx: 16; }
      .green { fill: #ecfdf5; stroke: #059669; stroke-width: 2.2; rx: 16; }
      .orange { fill: #fff7ed; stroke: #ea580c; stroke-width: 2.2; rx: 16; }
      .yellow { fill: #fef9c3; stroke: #ca8a04; stroke-width: 2.2; }
      .white { fill: #ffffff; stroke: #94a3b8; stroke-width: 2.2; rx: 14; }
      .soft { fill: #f1f5f9; stroke: #94a3b8; stroke-width: 2.0; rx: 14; }
      .title { font: 700 34px Arial, sans-serif; fill: #0f172a; }
      .subtitle { font: 17px Arial, sans-serif; fill: #475569; }
      .panelTitle { font: 700 25px Arial, sans-serif; fill: #0f172a; }
      .label { font: 700 20px Arial, sans-serif; fill: #0f172a; }
      .small { font: 16px Arial, sans-serif; fill: #334155; }
      .tiny { font: 14px Arial, sans-serif; fill: #475569; }
      .arrow { stroke: #334155; stroke-width: 2.3; fill: none; marker-end: url(#arrow); }
      .dash { stroke: #64748b; stroke-width: 2.2; stroke-dasharray: 8 7; fill: none; marker-end: url(#arrowDash); }
    </style>
"""


def slugify(text: str) -> str:
    normalized = re.sub(r"^\d+\.\s*", "", text.strip())
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "diagram"


def extract_mermaid_diagrams(markdown: str):
    pattern = re.compile(r"^##\s+(.+?)\n+```mermaid\n(.*?)\n```", re.MULTILINE | re.DOTALL)
    return [(title.strip(), body.strip() + "\n") for title, body in pattern.findall(markdown)]


def text_lines(x: float, y: float, lines, css: str = "small", anchor: str = "middle", step: int = 24) -> str:
    if isinstance(lines, str):
        lines = [lines]
    return "\n".join(
        f'<text x="{x}" y="{y + idx * step}" text-anchor="{anchor}" class="{css}">{escape(line)}</text>'
        for idx, line in enumerate(lines)
    )


def box(x: float, y: float, w: float, h: float, css: str, title: str, lines=()) -> str:
    content = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{css}"/>']
    content.append(text_lines(x + w / 2, y + 30, title, "label"))
    if lines:
        content.append(text_lines(x + w / 2, y + 54, lines, "small", step=19))
    return "\n".join(content)


def panel(x: float, y: float, w: float, h: float, title: str = "") -> str:
    content = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="panel"/>']
    if title:
        content.append(text_lines(x + w / 2, y + 38, title, "panelTitle"))
    return "\n".join(content)


def diamond(cx: float, cy: float, w: float, h: float, title_lines) -> str:
    points = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
    return "\n".join(
        [
            f'<polygon points="{points}" class="yellow"/>',
            text_lines(cx, cy - 8, title_lines, "label", step=26),
        ]
    )


def arrow(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<path d="M{x1} {y1} L{x2} {y2}" class="arrow"/>'


def dash(path_d: str) -> str:
    return f'<path d="{path_d}" class="dash"/>'


def page(title: str, subtitle: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">
  <defs>
{STYLE}
  </defs>
  <rect width="{CANVAS_W}" height="{CANVAS_H}" fill="#ffffff"/>
  {text_lines(800, 48, title, "title")}
  {text_lines(800, 78, subtitle, "subtitle")}
  {body}
</svg>
"""


def svg_overall_architecture() -> str:
    body = "\n".join(
        [
            panel(86, 115, 1428, 715, "從互動介面到估測與推薦輸出"),
            box(145, 185, 350, 82, "green", "Human interaction", ["web demo / dashboard"]),
            box(555, 185, 350, 82, "green", "AI tool access", ["MCP clients / Gemma bridge"]),
            box(965, 185, 350, 82, "green", "Scripted experiments", ["reproduction and validation"]),
            box(395, 330, 810, 84, "blue", "Service orchestration layer", ["scenario assembly, overrides, parameter management"]),
            box(395, 470, 810, 84, "blue", "Environmental digital twin core", ["bulk + local field estimation, appliance influence modeling"]),
            box(170, 625, 500, 84, "orange", "Calibration and impact learning", ["power calibration, trilinear correction, least-squares learning"]),
            box(760, 625, 500, 84, "yellow", "Optional residual neural layer", ["hybrid residual correction"]),
            box(455, 755, 690, 64, "green", "System outputs", ["spatial field, point sample, zone estimate, action ranking"]),
            arrow(320, 267, 575, 330),
            arrow(730, 267, 760, 330),
            arrow(1140, 267, 1025, 330),
            arrow(800, 414, 800, 470),
            arrow(695, 554, 505, 625),
            arrow(905, 554, 1010, 625),
            arrow(520, 709, 665, 755),
            arrow(1010, 709, 935, 755),
        ]
    )
    return page(
        "系統整體分層架構",
        "MCP 與 Web 只是入口；核心估測、校正與學習共用同一個 service path",
        body,
    )


def svg_execution_flow() -> str:
    body = "\n".join(
        [
            panel(55, 125, 1490, 700, "一次 runtime request 的資料路徑"),
            box(95, 215, 260, 90, "green", "Input", ["scenario, devices", "baseline, target"]),
            box(425, 180, 300, 90, "blue", "Entry layer", ["web demo", "MCP tool call"]),
            box(425, 315, 300, 90, "blue", "Scenario build", ["base scenario", "overrides"]),
            box(805, 215, 300, 90, "blue", "DigitalTwinModel", ["simulate T/H/L field"]),
            box(805, 350, 300, 90, "orange", "Sparse correction", ["power calibration", "trilinear residual"]),
            box(1175, 215, 300, 90, "yellow", "Optional hybrid", ["residual checkpoint"]),
            box(1175, 350, 300, 90, "green", "Outputs", ["point / zone values", "dashboard / MCP"]),
            box(1175, 500, 300, 90, "green", "Action ranking", ["sample scope + T/H/L target", "counterfactual penalty reduction"]),
            arrow(355, 255, 425, 220),
            arrow(575, 270, 575, 315),
            arrow(725, 360, 805, 260),
            arrow(955, 305, 955, 350),
            arrow(1105, 260, 1175, 260),
            arrow(1105, 395, 1175, 395),
            arrow(1325, 440, 1325, 500),
            dash("M575 395 C690 520 1000 560 1175 540"),
            text_lines(800, 620, "同一條 service path 同時支援腳本驗證、Web demo 與 MCP tools", "subtitle"),
        ]
    )
    return page(
        "主要執行資料流",
        "輸入先被組成 scenario state，再進入估測、校正、輸出與推薦",
        body,
    )


def svg_sensor_calibration_learning() -> str:
    body = "\n".join(
        [
            panel(55, 120, 1490, 710, "校正與 impact learning 的共同證據來源"),
            box(120, 195, 310, 78, "blue", "Truth-adjusted devices", ["controlled simulation"]),
            box(120, 330, 310, 78, "blue", "Truth simulation", ["dense reference field"]),
            box(120, 465, 310, 78, "blue", "Synthetic sensors", ["8 corner observations"]),
            box(610, 195, 310, 78, "soft", "Nominal device settings", ["original scenario"]),
            box(610, 330, 310, 78, "soft", "Nominal simulation", ["base estimate"]),
            box(610, 465, 310, 78, "soft", "Predicted sensors", ["sensor locations"]),
            box(1040, 330, 360, 78, "orange", "Sensor residuals", ["observed - predicted"]),
            box(1040, 465, 360, 78, "orange", "Power calibration", ["active-device scale"]),
            box(1040, 600, 360, 78, "orange", "Trilinear correction", ["8-corner residual field"]),
            box(585, 690, 350, 78, "green", "Corrected field", ["point / zone reconstruction"]),
            box(120, 690, 330, 78, "yellow", "Before / after deltas", ["non-networked device"]),
            box(1040, 735, 360, 62, "green", "Learned impact coefficients", ["least-squares output"]),
            arrow(275, 273, 275, 330),
            arrow(275, 408, 275, 465),
            arrow(765, 273, 765, 330),
            arrow(765, 408, 765, 465),
            arrow(430, 504, 1040, 360),
            arrow(920, 504, 1040, 370),
            arrow(1220, 408, 1220, 465),
            arrow(1220, 543, 1220, 600),
            arrow(1040, 639, 935, 715),
            arrow(275, 543, 285, 690),
            dash("M450 728 C650 820 900 820 1040 765"),
        ]
    )
    return page(
        "感測器校正與影響學習流程",
        "8 顆角落觀測同時支援 residual correction 與非連網裝置影響係數學習",
        body,
    )


def svg_training_inference_flow() -> str:
    body = "\n".join(
        [
            panel(38, 105, 724, 742, "A. Learning / Training Path"),
            panel(838, 105, 724, 742, "B. Runtime Inference / Recommendation Path"),
            box(140, 172, 520, 72, "blue", "Raw records", ["corner sensors / device events / outdoor / scenario"]),
            box(140, 276, 520, 72, "blue", "Time alignment and normalization", ["timestamp, units, coordinates, valid ranges"]),
            box(140, 380, 520, 76, "blue", "Scenario state assembly", ["baseline + outdoor + devices + furniture + time"]),
            box(140, 488, 520, 76, "blue", "Nominal field + sparse calibration", ["T/H/L models, power scale, trilinear residual"]),
            diamond(400, 658, 240, 128, ["Training", "branch"]),
            box(76, 745, 280, 72, "orange", "Impact coefficients", ["before / after delta"]),
            box(444, 745, 280, 72, "orange", "Residual checkpoint", ["features + residual labels"]),
            box(940, 160, 520, 70, "green", "Runtime input", ["MCP / web demo / script / API"]),
            box(940, 260, 520, 70, "green", "Scenario override and validation", ["baseline + devices + furniture + time"]),
            box(940, 360, 520, 70, "green", "Nominal T/H/L estimate", ["variable-specific physical models"]),
            box(940, 460, 520, 70, "green", "Sparse correction / optional hybrid", ["registered sensors, calibration state, checkpoint"]),
            box(940, 560, 520, 70, "green", "Point or zone prediction", ["temperature + humidity + illuminance"]),
            box(940, 660, 520, 70, "yellow", "Recommendation precondition", ["point or cluster sample + T/H/L target"]),
            diamond(1200, 790, 260, 100, ["Complete", "scope + target?"]),
            box(850, 766, 180, 64, "green", "Return", ["prediction", "or missing-target error"]),
            box(1370, 748, 160, 74, "green", "Counterfactual", ["rerun each", "candidate"]),
            box(1370, 824, 160, 42, "orange", "Rank", ["penalty reduction"]),
            arrow(400, 244, 400, 276),
            arrow(400, 348, 400, 380),
            arrow(400, 456, 400, 488),
            arrow(400, 564, 400, 594),
            arrow(330, 708, 250, 745),
            arrow(470, 708, 550, 745),
            arrow(1200, 230, 1200, 260),
            arrow(1200, 330, 1200, 360),
            arrow(1200, 430, 1200, 460),
            arrow(1200, 530, 1200, 560),
            arrow(1200, 630, 1200, 660),
            arrow(1200, 730, 1200, 740),
            arrow(1070, 790, 1030, 798),
            arrow(1330, 790, 1370, 786),
            arrow(1450, 822, 1450, 824),
            dash("M724 780 C800 780 850 520 940 520"),
            dash("M356 780 C710 860 835 530 940 530"),
            text_lines(798, 498, "saved training outputs", "tiny"),
        ]
    )
    return page(
        "模型學習、推論與推薦資料流",
        "訓練端產生的係數與 checkpoint 會被推論端重用；推薦需先有 sample scope 與完整三因子目標",
        body,
    )


def svg_modular_devices_furniture() -> str:
    body = "\n".join(
        [
            panel(70, 125, 1460, 695, "裝置與家具先進入 scenario state，再由模型統一處理"),
            box(120, 220, 330, 92, "green", "Device sources", ["built-in devices", "device specs / extra devices"]),
            box(120, 430, 330, 92, "green", "Furniture sources", ["built-in furniture", "extra blockers"]),
            box(580, 310, 380, 100, "blue", "Scenario state", ["room geometry, baseline", "devices, furniture, outdoor"]),
            box(1075, 310, 360, 100, "blue", "DigitalTwinModel", ["shared estimator"]),
            box(1010, 520, 260, 76, "orange", "Local effects", ["device influence"]),
            box(1300, 520, 260, 76, "orange", "Obstacle attenuation", ["furniture blockers"]),
            box(1155, 650, 260, 76, "green", "Spatial output", ["field / point / zone"]),
            arrow(450, 266, 580, 345),
            arrow(450, 476, 580, 375),
            arrow(960, 360, 1075, 360),
            arrow(1160, 410, 1110, 520),
            arrow(1280, 410, 1430, 520),
            arrow(1140, 596, 1250, 650),
            arrow(1430, 596, 1340, 650),
        ]
    )
    return page(
        "可模組化裝置與家具架構",
        "新設備與家具不直接改模型主流程，而是以 scenario state 的模組化輸入進入估測",
        body,
    )


def svg_room_topology() -> str:
    body = "\n".join(
        [
            panel(70, 120, 1460, 715, "標準房間拓樸：6 m × 4 m × 3 m"),
            '<rect x="255" y="230" width="860" height="430" fill="#ffffff" stroke="#334155" stroke-width="3" rx="10"/>',
            text_lines(685, 210, "Top view with floor/ceiling corner sensors", "panelTitle"),
            box(305, 300, 180, 78, "green", "Window", ["window_main"]),
            box(585, 290, 200, 78, "orange", "Light", ["ceiling center"]),
            box(890, 300, 180, 78, "blue", "AC", ["right wall"]),
            box(325, 470, 205, 84, "soft", "window_zone", ["near daylight source"]),
            box(585, 470, 205, 84, "soft", "center_zone", ["target workspace"]),
            box(845, 470, 205, 84, "soft", "door_side_zone", ["far-side area"]),
            box(1175, 250, 240, 92, "blue", "Ceiling sensors", ["ceiling_sw/se", "ceiling_nw/ne"]),
            box(1175, 450, 240, 92, "green", "Floor sensors", ["floor_sw/se", "floor_nw/ne"]),
            '<circle cx="255" cy="230" r="11" fill="#059669"/><circle cx="1115" cy="230" r="11" fill="#059669"/>',
            '<circle cx="255" cy="660" r="11" fill="#059669"/><circle cx="1115" cy="660" r="11" fill="#059669"/>',
            '<circle cx="275" cy="250" r="9" fill="#0284c7"/><circle cx="1095" cy="250" r="9" fill="#0284c7"/>',
            '<circle cx="275" cy="640" r="9" fill="#0284c7"/><circle cx="1095" cy="640" r="9" fill="#0284c7"/>',
            text_lines(685, 700, "8 corner nodes provide sparse observations; zones define evaluation and recommendation targets.", "subtitle"),
            dash("M1175 296 C1140 280 1132 260 1115 250"),
            dash("M1175 496 C1140 565 1132 625 1115 640"),
        ]
    )
    return page(
        "房間感測器與目標區域配置",
        "感測器、裝置與目標區域共用同一個三維座標系",
        body,
    )


def svg_validation_flow() -> str:
    body = "\n".join(
        [
            panel(45, 120, 1510, 705, "E1-E6 controlled validation 的產生與比對流程"),
            box(90, 230, 300, 90, "green", "Validation scenario", ["room, environment", "devices, furniture"]),
            box(485, 180, 300, 76, "blue", "Truth adjustment", ["active device powers"]),
            box(485, 305, 300, 76, "blue", "Truth simulation", ["dense reference field"]),
            box(485, 430, 300, 76, "blue", "8-corner observations", ["synthetic sparse sensors"]),
            box(875, 305, 300, 76, "soft", "Nominal simulation", ["original device settings"]),
            box(875, 430, 300, 90, "orange", "Sensor-informed correction", ["power calibration", "trilinear residual"]),
            box(875, 555, 300, 76, "yellow", "Optional hybrid residual", ["checkpoint if available"]),
            box(1260, 305, 250, 76, "soft", "Baselines", ["IDW / ablations"]),
            box(1260, 450, 250, 92, "green", "Comparison", ["truth vs corrected", "truth vs baseline"]),
            box(1260, 600, 250, 92, "green", "Evidence outputs", ["MAE metrics", "summary JSON / figures"]),
            arrow(390, 275, 485, 218),
            arrow(635, 256, 635, 305),
            arrow(635, 381, 635, 430),
            arrow(785, 468, 875, 468),
            arrow(785, 343, 875, 343),
            arrow(1025, 506, 1025, 555),
            arrow(1175, 343, 1260, 343),
            arrow(1175, 475, 1260, 475),
            arrow(1385, 542, 1385, 600),
            dash("M635 506 C760 700 1110 720 1260 646"),
        ]
    )
    return page(
        "驗證與實驗流程",
        "先產生可控 truth，再以相同 sparse sensor evidence 比較 corrected model、baseline 與 hybrid",
        body,
    )


def svg_code_structure() -> str:
    body = "\n".join(
        [
            panel(90, 135, 1420, 650, "程式碼模組與研究功能對應"),
            box(650, 190, 300, 70, "green", "Repository root", ["digital_twin, scripts, tests"]),
            box(140, 355, 250, 76, "blue", "core", ["entities, scenarios", "service"]),
            box(430, 355, 250, 76, "blue", "physics", ["model, baselines", "learning"]),
            box(720, 355, 250, 76, "yellow", "neural", ["hybrid residual"]),
            box(1010, 355, 250, 76, "green", "mcp / web", ["runtime interface", "demo render"]),
            box(575, 555, 450, 76, "orange", "scripts + tests", ["reproduction, verification, regression checks"]),
            arrow(800, 260, 265, 355),
            arrow(800, 260, 555, 355),
            arrow(800, 260, 845, 355),
            arrow(800, 260, 1135, 355),
            arrow(555, 431, 680, 555),
            arrow(845, 431, 830, 555),
        ]
    )
    return page("程式碼結構圖", "研究功能、服務介面與驗證腳本分層管理", body)


def svg_docs_outputs() -> str:
    body = "\n".join(
        [
            panel(90, 135, 1420, 650, "文件、圖表與輸出同步"),
            box(650, 190, 300, 70, "green", "Repository root", ["source + generated outputs"]),
            box(260, 335, 280, 78, "blue", "docs", ["thesis, papers", "mcp, experiments"]),
            box(690, 335, 280, 78, "orange", "outputs", ["data, figures", "papers"]),
            box(1120, 335, 280, 78, "yellow", "scripts", ["builders", "verification"]),
            box(220, 555, 360, 78, "green", "Published artifacts", ["DOCX, PDF, PPTX, IEEE PDF"]),
            box(640, 555, 360, 78, "green", "Evidence artifacts", ["summary JSON", "verification report"]),
            arrow(800, 260, 400, 335),
            arrow(800, 260, 830, 335),
            arrow(800, 260, 1260, 335),
            arrow(400, 413, 400, 555),
            arrow(830, 413, 820, 555),
            arrow(1260, 413, 1000, 585),
        ]
    )
    return page("文件與輸出結構圖", "來源文件、實驗輸出與可驗證報告需要保持同步", body)


def fallback_svg_for_title(title: str) -> str:
    renderers = {
        "整體分層架構": svg_overall_architecture,
        "主要執行資料流": svg_execution_flow,
        "感測器校正與學習流程": svg_sensor_calibration_learning,
        "模型學習推論與推薦資料流": svg_training_inference_flow,
        "可模組化裝置與家具架構": svg_modular_devices_furniture,
        "房間感測器與目標區域配置": svg_room_topology,
        "驗證與實驗流程圖": svg_validation_flow,
        "程式碼結構圖": svg_code_structure,
        "文件與輸出結構圖": svg_docs_outputs,
    }
    renderer = renderers.get(slugify(title))
    return renderer() if renderer else ""


def render_diagram(title: str, mermaid_source: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{slugify(title)}.svg"

    fallback_svg = fallback_svg_for_title(title)
    if fallback_svg:
        output_path.write_text(fallback_svg, encoding="utf-8")
        return output_path

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        source_path = temp_dir_path / "diagram.mmd"
        source_path.write_text(mermaid_source, encoding="utf-8")
        subprocess.run(
            [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli",
                "-i",
                str(source_path),
                "-o",
                str(output_path),
                "-b",
                "transparent",
            ],
            check=True,
            cwd=str(ROOT),
        )
    return output_path


def main() -> None:
    markdown = SOURCE_MARKDOWN.read_text(encoding="utf-8")
    diagrams = extract_mermaid_diagrams(markdown)
    if not diagrams:
        raise SystemExit("No Mermaid diagrams found in source markdown.")

    rendered = [render_diagram(title, body) for title, body in diagrams]
    expected_names = {path.name for path in rendered}
    for stale in OUTPUT_DIR.glob("*.svg"):
        if stale.name not in expected_names:
            stale.unlink()
    print("Rendered architecture diagrams:")
    for path in rendered:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
