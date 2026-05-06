# -*- coding: utf-8 -*-
"""
Build the full Chinese thesis with the latest MCP workflow description.

This generator reuses the stable full thesis renderer and inserts an updated
section describing the current five-tool MCP workflow:

- initialize_environment
- sample_point
- learn_impacts
- run_window_direct
- rank_actions

Outputs:
- outputs/papers/thesis_full_zh_mcp_updated.tex
- outputs/papers/thesis_full_zh_mcp_updated.pdf, if xelatex is available
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from typing import List


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = ROOT / "outputs" / "papers"

sys.path.insert(0, str(SCRIPT_DIR))

import build_thesis_full_zh_stable as stable  # noqa: E402
from build_thesis_docx import Block, build_blocks  # noqa: E402


TEX_PATH = OUTPUT_DIR / "thesis_full_zh_mcp_updated.tex"
PDF_PATH = OUTPUT_DIR / "thesis_full_zh_mcp_updated.pdf"


def mcp_workflow_blocks() -> List[Block]:
    return [
        {"type": "heading", "text": "MCP 互動式數位孿生工具流程", "level": 2},
        {
            "type": "paragraph",
            "text": (
                "本研究的 MCP 介面已由早期 demo-oriented tools 收斂為 workflow-oriented tools。"
                "新版 MCP server 不再只是列出或執行預設情境，而是讓 AI client 以互動流程操作空間數位孿生："
                "先初始化室內環境，再查詢指定點、學習非連網設備影響，最後依舒適目標排序候選控制動作。"
            ),
        },
        {
            "type": "table",
            "headers": ["MCP tool", "功能定位"],
            "rows": [
                [
                    "initialize_environment",
                    "初始化房間情境，註冊設備與家具，設定室內 baseline、外部溫度、外部濕度、日照與其他邊界條件。",
                ],
                [
                    "sample_point",
                    "查詢任意座標 $(x,y,z)$ 的溫度、濕度與照度估計；支援 elapsed minutes 與 steady-state 類型查詢。",
                ],
                [
                    "learn_impacts",
                    "接收 before/after 感測器觀測資料，學習非連網設備的 temperature、humidity 與 illuminance impact coefficients。",
                ],
                [
                    "run_window_direct",
                    "直接輸入 outdoor temperature、outdoor humidity、sunlight illuminance 與 opening ratio，模擬窗戶邊界條件對室內場的影響。",
                ],
                [
                    "rank_actions",
                    "針對指定空間點與目標溫度、濕度、照度，計算目前 penalty，並排序候選控制動作與預期改善量。",
                ],
            ],
        },
        {
            "type": "paragraph",
            "text": (
                "此設計使本研究的 digital twin 不只是 Web demo 或固定 scenario runner，"
                "而是可被 LLM agent 操作的 AI-agent-accessible spatial digital twin workflow。"
                "其中 learn_impacts 對應本研究的非連網設備影響學習，rank_actions 則對應控制建議排序；"
                "兩者共同使模型能由感測資料形成環境理解，再轉化為可執行的控制建議。"
            ),
        },
    ]


def insert_mcp_workflow(blocks: List[Block]) -> List[Block]:
    """Insert MCP workflow section without removing original content."""
    output: List[Block] = []
    inserted = False
    anchors = (
        "系統實作",
        "第四章 系統實作",
        "4. 系統實作",
        "4.1 系統架構",
    )
    for block in blocks:
        output.append(block)
        text = str(block.get("text", ""))
        if not inserted and block.get("type") == "heading" and any(anchor in text for anchor in anchors):
            output.extend(mcp_workflow_blocks())
            inserted = True
    if not inserted:
        output.extend(mcp_workflow_blocks())
    return output


def compile_pdf(tex_path: Path) -> None:
    xelatex = shutil.which("xelatex")
    if xelatex is None:
        print("xelatex not found; generated LaTeX only.")
        return
    for _ in range(2):
        completed = subprocess.run(
            [xelatex, "-interaction=nonstopmode", tex_path.name],
            cwd=OUTPUT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            print(completed.stdout)
            print(completed.stderr, file=sys.stderr)
            raise SystemExit(completed.returncode)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    blocks = stable.insert_extras(build_blocks())
    blocks = insert_mcp_workflow(blocks)
    TEX_PATH.write_text(stable.render_document(blocks), encoding="utf-8")
    compile_pdf(TEX_PATH)
    print(f"Wrote {TEX_PATH}")
    if PDF_PATH.exists():
        print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
