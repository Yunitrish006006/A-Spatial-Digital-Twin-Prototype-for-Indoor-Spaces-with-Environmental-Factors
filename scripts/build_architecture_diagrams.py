import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MARKDOWN = ROOT / "docs" / "thesis" / "system_architecture_diagrams_zh.md"
OUTPUT_DIR = ROOT / "outputs" / "figures" / "architecture"
MERMAID_DISABLED = False


def slugify(text: str) -> str:
    normalized = re.sub(r"^\d+\.\s*", "", text.strip())
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "diagram"


def extract_mermaid_diagrams(markdown: str):
    pattern = re.compile(r"^##\s+(.+?)\n+```mermaid\n(.*?)\n```", re.MULTILINE | re.DOTALL)
    return [(title.strip(), body.strip() + "\n") for title, body in pattern.findall(markdown)]


def fallback_svg_for_title(title: str) -> str:
    if slugify(title) != "模型學習推論與推薦資料流":
        return ""

    return """<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <path d="M 0 0 L 12 6 L 0 12 z" fill="#334155"/>
    </marker>
    <marker id="arrowDashed" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <path d="M 0 0 L 12 6 L 0 12 z" fill="#64748b"/>
    </marker>
    <style>
      .panel { fill: #f8fafc; stroke: #94a3b8; stroke-width: 2; rx: 22; }
      .train { fill: #e0f2fe; stroke: #0284c7; stroke-width: 2; rx: 16; }
      .run { fill: #ecfdf5; stroke: #059669; stroke-width: 2; rx: 16; }
      .artifact { fill: #fff7ed; stroke: #ea580c; stroke-width: 2; rx: 16; }
      .decision { fill: #fef9c3; stroke: #ca8a04; stroke-width: 2; }
      .title { font: 700 34px Arial, sans-serif; fill: #0f172a; }
      .panelTitle { font: 700 25px Arial, sans-serif; fill: #0f172a; }
      .label { font: 700 20px Arial, sans-serif; fill: #0f172a; }
      .small { font: 16px Arial, sans-serif; fill: #334155; }
      .arrow { stroke: #334155; stroke-width: 2.2; fill: none; marker-end: url(#arrow); }
      .dash { stroke: #64748b; stroke-width: 2.2; stroke-dasharray: 8 7; fill: none; marker-end: url(#arrowDashed); }
      .note { font: 15px Arial, sans-serif; fill: #475569; }
    </style>
  </defs>

  <rect width="1600" height="900" fill="#ffffff"/>
  <text x="800" y="48" text-anchor="middle" class="title">模型學習、推論與推薦資料流</text>
  <text x="800" y="78" text-anchor="middle" class="note">訓練端產生的係數與 checkpoint 會被推論端重用；推薦動作是反事實重跑同一條推論流程</text>

  <rect x="38" y="105" width="724" height="742" class="panel"/>
  <rect x="838" y="105" width="724" height="742" class="panel"/>
  <text x="400" y="142" text-anchor="middle" class="panelTitle">A. Learning / Training Path</text>
  <text x="1200" y="142" text-anchor="middle" class="panelTitle">B. Runtime Inference / Recommendation Path</text>

  <rect x="140" y="172" width="520" height="72" class="train"/>
  <text x="400" y="199" text-anchor="middle" class="label">Raw records</text>
  <text x="400" y="225" text-anchor="middle" class="small">corner sensors / device events / outdoor / scenario</text>

  <rect x="140" y="276" width="520" height="72" class="train"/>
  <text x="400" y="303" text-anchor="middle" class="label">Time alignment and normalization</text>
  <text x="400" y="329" text-anchor="middle" class="small">timestamp, units, coordinates, valid ranges</text>

  <rect x="140" y="380" width="520" height="76" class="train"/>
  <text x="400" y="407" text-anchor="middle" class="label">Scenario state assembly</text>
  <text x="400" y="433" text-anchor="middle" class="small">baseline + outdoor + devices + furniture + time</text>

  <rect x="140" y="488" width="520" height="76" class="train"/>
  <text x="400" y="515" text-anchor="middle" class="label">Nominal field + sparse calibration</text>
  <text x="400" y="541" text-anchor="middle" class="small">T/H/L models, power scale, trilinear residual</text>

  <polygon points="400,594 520,658 400,722 280,658" class="decision"/>
  <text x="400" y="652" text-anchor="middle" class="label">Training</text>
  <text x="400" y="678" text-anchor="middle" class="label">branch</text>

  <rect x="76" y="745" width="280" height="72" class="artifact"/>
  <text x="216" y="772" text-anchor="middle" class="label">Impact coefficients</text>
  <text x="216" y="798" text-anchor="middle" class="small">before / after delta</text>

  <rect x="444" y="745" width="280" height="72" class="artifact"/>
  <text x="584" y="772" text-anchor="middle" class="label">Residual checkpoint</text>
  <text x="584" y="798" text-anchor="middle" class="small">features + residual labels</text>

  <rect x="940" y="172" width="520" height="72" class="run"/>
  <text x="1200" y="199" text-anchor="middle" class="label">Runtime input</text>
  <text x="1200" y="225" text-anchor="middle" class="small">MCP / web demo / script / API</text>

  <rect x="940" y="276" width="520" height="72" class="run"/>
  <text x="1200" y="303" text-anchor="middle" class="label">Scenario override and validation</text>
  <text x="1200" y="329" text-anchor="middle" class="small">query point or target zone</text>

  <rect x="940" y="380" width="520" height="76" class="run"/>
  <text x="1200" y="407" text-anchor="middle" class="label">Nominal T/H/L estimate</text>
  <text x="1200" y="433" text-anchor="middle" class="small">variable-specific physical models</text>

  <rect x="940" y="488" width="520" height="76" class="run"/>
  <text x="1200" y="515" text-anchor="middle" class="label">Sparse correction / optional hybrid</text>
  <text x="1200" y="541" text-anchor="middle" class="small">registered sensors, calibration state, checkpoint</text>

  <rect x="940" y="596" width="520" height="72" class="run"/>
  <text x="1200" y="623" text-anchor="middle" class="label">Point or zone prediction</text>
  <text x="1200" y="649" text-anchor="middle" class="small">temperature + humidity + illuminance</text>

  <polygon points="1200,694 1330,754 1200,814 1070,754" class="decision"/>
  <text x="1200" y="748" text-anchor="middle" class="label">Need action</text>
  <text x="1200" y="774" text-anchor="middle" class="label">ranking?</text>

  <rect x="850" y="738" width="180" height="64" class="run"/>
  <text x="940" y="764" text-anchor="middle" class="label">Return</text>
  <text x="940" y="788" text-anchor="middle" class="small">prediction</text>

  <rect x="1370" y="710" width="160" height="92" class="run"/>
  <text x="1450" y="736" text-anchor="middle" class="label">Counterfactual</text>
  <text x="1450" y="760" text-anchor="middle" class="small">rerun each</text>
  <text x="1450" y="784" text-anchor="middle" class="small">candidate</text>

  <rect x="1370" y="803" width="160" height="42" class="artifact"/>
  <text x="1450" y="829" text-anchor="middle" class="small">Rank by penalty reduction</text>

  <path d="M400 244 L400 276" class="arrow"/>
  <path d="M400 348 L400 380" class="arrow"/>
  <path d="M400 456 L400 488" class="arrow"/>
  <path d="M400 564 L400 594" class="arrow"/>
  <path d="M330 708 L250 745" class="arrow"/>
  <path d="M470 708 L550 745" class="arrow"/>

  <path d="M1200 244 L1200 276" class="arrow"/>
  <path d="M1200 348 L1200 380" class="arrow"/>
  <path d="M1200 456 L1200 488" class="arrow"/>
  <path d="M1200 564 L1200 596" class="arrow"/>
  <path d="M1200 668 L1200 694" class="arrow"/>
  <path d="M1070 754 L1030 770" class="arrow"/>
  <path d="M1330 754 L1370 754" class="arrow"/>
  <path d="M1450 802 L1450 803" class="arrow"/>

  <path d="M724 780 C800 780 850 520 940 520" class="dash"/>
  <path d="M356 780 C710 860 835 530 940 530" class="dash"/>
  <text x="798" y="498" text-anchor="middle" class="note">saved training outputs</text>
</svg>
"""


def render_diagram(title: str, mermaid_source: str) -> Path:
    global MERMAID_DISABLED
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{slugify(title)}.svg"
    if not MERMAID_DISABLED:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            source_path = temp_dir_path / "diagram.mmd"
            source_path.write_text(mermaid_source, encoding="utf-8")
            try:
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
            except (FileNotFoundError, subprocess.CalledProcessError):
                MERMAID_DISABLED = True
                print("Mermaid CLI unavailable; preserving existing SVGs and using built-in fallbacks when available.")

    fallback_svg = fallback_svg_for_title(title)
    if fallback_svg:
        output_path.write_text(fallback_svg, encoding="utf-8")
    elif not output_path.exists():
        raise RuntimeError(f"Cannot render {title!r}: Mermaid CLI unavailable and no existing SVG found.")
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
