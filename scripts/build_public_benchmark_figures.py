# -*- coding: utf-8 -*-
"""Build explanatory public-benchmark task-family figures.

The figures are generated from the existing public benchmark JSON outputs.
They intentionally summarize task families instead of copying a large row-wise
table into the thesis or slides.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BENCHMARKS = ROOT / "outputs" / "data" / "public_benchmarks"
OUT_DIR = ROOT / "outputs" / "figures" / "public_benchmarks"
MODEL_NAME = "hybrid_digital_twin_readout"


TASK_META: Dict[str, Dict[str, Dict[str, Any]]] = {
    "SML2010": {
        "S1": {
            "title": "S1 純日照/照度邊界響應",
            "stance": "主要劣勢",
            "why": [
                "短視窗照度高度受上一時步控制，persistence 已很強。",
                "公開資料缺實際窗戶幾何/遮蔽/燈具配置，daylight mapping 易有誤差。",
                "60 分鐘可勝過 linear regression，但仍未勝過 persistence。",
            ],
            "case": "15min dining lx: 本研究 5.346，P 3.418。",
        },
        "S2": {
            "title": "S2 溫濕度邊界響應",
            "stance": "溫度有優勢、濕度劣勢",
            "why": [
                "60 分鐘溫度受外氣與熱邊界影響，structured prior 能補上 LR 不足。",
                "濕度有量測尺度與基準對齊問題，簡化濕度模型容易偏移。",
                "因此 S2 不能被概括成全面優勢，只能主張長視窗溫度較有利。",
            ],
            "case": "60min T: 本研究 0.156 < LR 0.192；15min H: 0.832 > P 0.198。",
        },
        "S3": {
            "title": "S3 facade event delta response",
            "stance": "主要優勢",
            "why": [
                "事件型 delta response 需要變化方向，persistence 無法提供事件方向。",
                "邊界條件、日照與裝置/環境響應特徵能提供有效先驗。",
                "60 分鐘的 6 個 target 全部同時勝過 linear regression 與 persistence。",
            ],
            "case": "15min dining T: 本研究 0.071，LR 0.093，P 0.233。",
        },
    },
    "CU-BEMS": {
        "C1": {
            "title": "C1 AC 溫濕度 zone response",
            "stance": "只勝 linear regression",
            "why": [
                "AC power 與 plug load 提供裝置狀態線索，可改善部分 LR 結果。",
                "商辦 zone-level 溫濕度短時間自相關很強，上一時步通常已是極強 baseline。",
                "因此可主張 structured prior 對 linear regression 有幫助，不能主張取代 persistence。",
            ],
            "case": "15min T: 本研究 0.282，LR 0.288，P 0.262。",
        },
        "C2": {
            "title": "C2 lighting/illuminance response",
            "stance": "明顯劣勢",
            "why": [
                "商辦照度受排程/遮陽/自然光/多燈具影響，與單房間假設不一致。",
                "照度在短視窗也有強慣性，persistence 直接沿用上一時步反而較穩。",
                "提醒：照度不能只靠簡化幾何映射外推到大型商辦區域。",
            ],
            "case": "15min lx: 本研究 7.700，LR 1.794，P 1.363。",
        },
        "C3": {
            "title": "C3 compound event delta response",
            "stance": "相對 linear regression 有優勢",
            "why": [
                "事件 delta 任務讓裝置 power 與環境響應特徵變得有用，因此 6/6 勝過 linear regression。",
                "但 CU-BEMS zone-level 資料仍有強時間慣性，persistence 在 MAE 上全部最佳。",
                "可解讀為外部資料上的壓力測試，而不是 full 3D 場驗證。",
            ],
            "case": "60min lx: 本研究 5.728，LR 7.093，P 4.509。",
        },
    },
}


def read_summary(dataset: str) -> Dict[str, Any]:
    filename = {
        "SML2010": "sml2010_hybrid_twin_comparison.json",
        "CU-BEMS": "cu_bems_hybrid_twin_comparison.json",
    }[dataset]
    path = PUBLIC_BENCHMARKS / filename
    return json.loads(path.read_text(encoding="utf-8"))


def task_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for task in summary.get("tasks", []):
        if not isinstance(task, dict) or task.get("status") not in (None, "ok"):
            continue
        targets = task.get("targets", {})
        if not isinstance(targets, dict):
            continue
        for target_name, metrics_by_method in targets.items():
            if not isinstance(metrics_by_method, dict):
                continue
            model = metrics_by_method.get(MODEL_NAME, {})
            linear = metrics_by_method.get("linear_regression", {})
            persistence = metrics_by_method.get("persistence", {})
            try:
                model_mae = float(model["mae"])
                linear_mae = float(linear["mae"])
                persistence_mae = float(persistence["mae"])
            except (KeyError, TypeError, ValueError):
                continue
            best_mae = min(model_mae, linear_mae, persistence_mae)
            rows.append(
                {
                    "task_id": task.get("task_id", ""),
                    "target": target_name,
                    "horizon_minutes": task.get("horizon_minutes", ""),
                    "model_mae": model_mae,
                    "linear_mae": linear_mae,
                    "persistence_mae": persistence_mae,
                    "model_best": model_mae == best_mae,
                    "beats_linear": model_mae < linear_mae,
                    "beats_persistence": model_mae < persistence_mae,
                }
            )
    return rows


def family_stats(rows: Iterable[Dict[str, Any]], task_id: str) -> Dict[str, int]:
    task_rows_only = [row for row in rows if row["task_id"] == task_id]
    return {
        "total": len(task_rows_only),
        "best": sum(1 for row in task_rows_only if row["model_best"]),
        "linear": sum(1 for row in task_rows_only if row["beats_linear"]),
        "persistence": sum(1 for row in task_rows_only if row["beats_persistence"]),
    }


def text(x: int, y: int, value: str, css_class: str = "", size: int | None = None) -> str:
    class_attr = f' class="{css_class}"' if css_class else ""
    size_attr = f' font-size="{size}"' if size is not None else ""
    return f'<text x="{x}" y="{y}"{class_attr}{size_attr}>{escape(value)}</text>'


def text_lines(
    x: int,
    y: int,
    lines: Iterable[str],
    css_class: str = "",
    line_height: int = 24,
    size: int | None = None,
) -> List[str]:
    return [text(x, y + index * line_height, line, css_class, size) for index, line in enumerate(lines)]


def bar(x: int, y: int, width: int, height: int, value: int, total: int, css_class: str) -> str:
    ratio = (value / total) if total else 0.0
    fill_width = max(0, min(width, round(width * ratio)))
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" class="bar-bg"/>'
        f'<rect x="{x}" y="{y}" width="{fill_width}" height="{height}" rx="8" class="{css_class}"/>'
    )


def render_family_card(dataset: str, task_id: str, stats: Dict[str, int], y: int) -> List[str]:
    meta = TASK_META[dataset][task_id]
    total = stats["total"]
    parts: List[str] = [
        f'<rect x="70" y="{y}" width="1460" height="205" rx="22" class="card"/>',
        text(105, y + 45, f"{task_id} | {meta['title']}", "task-title"),
        text(105, y + 82, f"判讀：{meta['stance']}", "stance"),
        text(105, y + 118, f"代表案例：{meta['case']}", "case"),
    ]

    metrics = [
        ("最低 MAE", stats["best"], "bar-best"),
        ("勝過 LinReg", stats["linear"], "bar-linear"),
        ("勝過 Persist", stats["persistence"], "bar-persist"),
    ]
    for index, (label, count, css_class) in enumerate(metrics):
        row_y = y + 42 + index * 48
        parts.append(text(1000, row_y + 16, label, "metric-label"))
        parts.append(bar(1140, row_y, 250, 22, count, total, css_class))
        parts.append(text(1410, row_y + 17, f"{count}/{total}", "metric-count"))

    why_lines = ["為什麼：" + meta["why"][0], *meta["why"][1:]]
    parts.extend(text_lines(105, y + 155, why_lines, "why", line_height=23))
    return parts


def render_dataset_figure(dataset: str, output_name: str) -> None:
    summary = read_summary(dataset)
    rows = task_rows(summary)
    task_order = list(TASK_META[dataset].keys())
    total = len(rows)
    best = sum(1 for row in rows if row["model_best"])
    linear = sum(1 for row in rows if row["beats_linear"])
    persistence = sum(1 for row in rows if row["beats_persistence"])
    title = f"{dataset} task-aligned benchmark 任務族群拆解"
    subtitle = (
        f"總計 {total} 個 target-horizon 任務；本研究最低 MAE {best} 項，"
        f"勝過 linear regression {linear} 項，勝過 persistence {persistence} 項。"
    )

    svg_parts: List[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
        "<style>",
        "text { font-family: Arial, 'Noto Sans CJK TC', sans-serif; fill: #17211b; }",
        ".title { font-size: 40px; font-weight: 800; }",
        ".subtitle { font-size: 22px; fill: #536174; }",
        ".card { fill: #fffdf7; stroke: #d8c9b4; stroke-width: 2; }",
        ".task-title { font-size: 26px; font-weight: 800; }",
        ".stance { font-size: 22px; font-weight: 800; fill: #005382; }",
        ".case { font-size: 20px; fill: #3f4a54; }",
        ".why { font-size: 18px; fill: #536174; }",
        ".metric-label { font-size: 18px; font-weight: 800; fill: #3f4a54; }",
        ".metric-count { font-size: 18px; font-weight: 800; fill: #17211b; }",
        ".bar-bg { fill: #e5edf2; }",
        ".bar-best { fill: #2f855a; }",
        ".bar-linear { fill: #2b5c7c; }",
        ".bar-persist { fill: #b4552b; }",
        "</style>",
        '<rect x="0" y="0" width="1600" height="900" fill="#f8f2e7"/>',
        text(70, 82, title, "title"),
        text(70, 118, subtitle, "subtitle"),
    ]

    for index, task_id in enumerate(task_order):
        y = 155 + index * 230
        svg_parts.extend(render_family_card(dataset, task_id, family_stats(rows, task_id), y))

    svg_parts.append("</svg>")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / output_name).write_text("\n".join(svg_parts), encoding="utf-8")


def main() -> None:
    render_dataset_figure("SML2010", "sml2010_task_breakdown.svg")
    render_dataset_figure("CU-BEMS", "cu_bems_task_breakdown.svg")
    print(f"Wrote {OUT_DIR / 'sml2010_task_breakdown.svg'}")
    print(f"Wrote {OUT_DIR / 'cu_bems_task_breakdown.svg'}")


if __name__ == "__main__":
    main()
