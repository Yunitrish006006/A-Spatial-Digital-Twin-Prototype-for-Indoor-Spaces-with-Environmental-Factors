# -*- coding: utf-8 -*-
"""
Build the full Chinese thesis PDF with stable LaTeX rendering.

This script keeps the existing full thesis content from build_thesis_docx.py
instead of using the short detailed draft. It fixes the common PDF problems:

1. Chinese garbling on macOS by using built-in Traditional Chinese fonts.
2. Table math such as $T_0$ being escaped as plain text.
3. Narrow table columns causing symbol tables to wrap badly.
4. Markdown/code style math blocks appearing as raw text in PDF.

Outputs:
- outputs/papers/thesis_full_zh_stable.tex
- outputs/papers/thesis_full_zh_stable.pdf, if xelatex is available
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = ROOT / "outputs" / "papers"

sys.path.insert(0, str(SCRIPT_DIR))
from build_thesis_docx import Block, build_blocks, ensure_image_asset  # noqa: E402


TEX_PATH = OUTPUT_DIR / "thesis_full_zh_stable.tex"
PDF_PATH = OUTPUT_DIR / "thesis_full_zh_stable.pdf"


def latex_escape(text: object) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_\allowbreak{}",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(text))


def latex_escape_with_math(text: object) -> str:
    """Escape normal text but preserve inline math segments: $...$."""
    parts = re.split(r"(\$[^$]+\$)", str(text))
    return "".join(part if i % 2 == 1 else latex_escape(part) for i, part in enumerate(parts))


def render_title(text: str, level: int) -> str:
    size = r"\LARGE" if level == 0 else r"\Large"
    lines = [latex_escape(line) for line in text.splitlines()]
    body = r"\\[0.6em]".join(lines)
    return (
        r"\begin{center}" + "\n"
        rf"{{{size}\bfseries {body}}}" + "\n"
        r"\end{center}" + "\n"
    )


def render_heading(text: str, level: int) -> str:
    escaped = latex_escape(text)
    if level <= 1:
        return rf"\section*{{{escaped}}}" + "\n" + rf"\addcontentsline{{toc}}{{section}}{{{escaped}}}" + "\n"
    if level == 2:
        return rf"\subsection*{{{escaped}}}" + "\n"
    return rf"\subsubsection*{{{escaped}}}" + "\n"


def render_paragraph(text: str, align: str) -> str:
    escaped = latex_escape_with_math(text).replace("\n", r"\\")
    if align == "center":
        return r"\begin{center}" + escaped + r"\end{center}" + "\n"
    return escaped + "\n\n"


def render_bullets(items: Iterable[object]) -> str:
    lines = [r"\begin{itemize}"]
    lines.extend(rf"\item {latex_escape_with_math(item)}" for item in items)
    lines.append(r"\end{itemize}")
    return "\n".join(lines) + "\n"


def render_code(text: str) -> str:
    # Keep code blocks readable and avoid fonts that are unavailable on macOS.
    safe_text = (
        str(text)
        .replace("→", "->")
        .replace("Σ", "sum")
        .replace("φ", "phi")
        .replace("θ", "theta")
        .replace("≤", "<=")
        .replace("≥", ">=")
    )
    return "\n".join(
        [
            r"\begin{lstlisting}[basicstyle=\footnotesize\ttfamily,breaklines=true,columns=flexible]",
            safe_text,
            r"\end{lstlisting}",
        ]
    ) + "\n"


def column_spec(column_count: int) -> str:
    if column_count <= 1:
        return r"|>{\raggedright\arraybackslash}p{0.88\textwidth}|"
    if column_count == 2:
        return r"|>{\raggedright\arraybackslash}p{0.33\textwidth}|>{\raggedright\arraybackslash}p{0.53\textwidth}|"
    width = 0.78 / column_count
    return "|" + "|".join(rf">{{\raggedright\arraybackslash}}p{{{width:.3f}\textwidth}}" for _ in range(column_count)) + "|"


def render_table(headers: List[object], rows: List[List[object]]) -> str:
    spec = column_spec(len(headers))
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\footnotesize",
        r"\renewcommand{\arraystretch}{1.25}",
        rf"\begin{{tabular}}{{{spec}}}",
        r"\hline",
    ]
    lines.append(" & ".join(rf"\textbf{{{latex_escape_with_math(header)}}}" for header in headers) + r" \\")
    lines.append(r"\hline")
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        lines.append(" & ".join(latex_escape_with_math(cell) for cell in padded[: len(headers)]) + r" \\")
        lines.append(r"\hline")
    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines) + "\n"


def render_math(latex: str, display: bool = True) -> str:
    if display:
        return "\\[\n" + latex + "\n\\]\n"
    return "$" + latex + "$"


def render_image(block: Block) -> str:
    try:
        asset_path = ensure_image_asset(block)
    except Exception as exc:
        return render_paragraph(f"[圖檔暫缺：{block.get('caption', '')}；原因：{exc}]", "left")

    try:
        asset_rel = asset_path.relative_to(OUTPUT_DIR).as_posix()
    except ValueError:
        asset_rel = asset_path.as_posix()

    width_inches = float(block.get("width_inches", 5.8))
    text_width_ratio = min(0.9, max(0.45, width_inches / 7.0))
    caption = latex_escape(str(block["caption"]))
    return (
        r"\begin{figure}[htbp]" + "\n"
        r"\centering" + "\n"
        rf"\includegraphics[width={text_width_ratio:.2f}\textwidth]{{{asset_rel}}}" + "\n"
        r"\par\smallskip" + "\n"
        rf"{{\small {caption}}}" + "\n"
        r"\end{figure}" + "\n"
    )


def render_block(block: Block) -> str:
    kind = str(block["type"])
    if kind == "title":
        return render_title(str(block["text"]), int(block["level"]))
    if kind == "heading":
        return render_heading(str(block["text"]), int(block["level"]))
    if kind == "paragraph":
        return render_paragraph(str(block["text"]), str(block.get("align", "left")))
    if kind == "bullets":
        return render_bullets(block["items"])
    if kind == "code":
        return render_code(str(block["text"]))
    if kind == "table":
        return render_table(list(block["headers"]), list(block["rows"]))
    if kind == "image":
        return render_image(block)
    if kind == "math":
        return render_math(str(block["latex"]), bool(block.get("display", True)))
    if kind == "raw_latex":
        return str(block["content"]) + "\n"
    if kind == "page_break":
        return r"\clearpage" + "\n"
    raise ValueError(f"Unsupported block type: {kind}")


def stable_extra_blocks() -> List[Block]:
    """Method-oriented additions requested by the user."""
    return [
        {"type": "heading", "text": "1.3.1 本研究解決之核心問題", "level": 3},
        {
            "type": "paragraph",
            "text": (
                "本研究解決的核心問題不是單純建立室內模擬畫面，而是在缺乏設備連網能力與高密度感測器部署的情況下，"
                "仍能重建室內空間環境分布，並推估設備對環境的影響。此問題可拆成三個子問題：稀疏感測空間重建、"
                "非連網設備影響推估，以及稀疏監督下的模型誤差補償。"
            ),
        },
        {
            "type": "bullets",
            "items": [
                "稀疏感測空間重建：在僅有 8 顆角落感測器的條件下，估計完整三維溫度、濕度與照度場。",
                "非連網設備影響推估：在冷氣、窗戶與燈具無法直接回報狀態時，由 before/after 感測殘差反推設備影響。",
                "模型誤差補償：以 physics model 作為主體，再用 trilinear correction 與 hybrid residual learning 修正剩餘誤差。",
            ],
        },
        {"type": "heading", "text": "1.5.1 研究貢獻與原創性補充", "level": 3},
        {
            "type": "paragraph",
            "text": (
                "本研究的原創性不在於單獨提出複雜神經網路，而在於將稀疏感測、非連網設備推估、可解釋物理模型、"
                "感測器校正與殘差學習整合為可執行且可重現的室內空間數位孿生方法。"
            ),
        },
        {
            "type": "bullets",
            "items": [
                "提出可在非連網設備環境下運作的空間數位孿生架構。",
                "提出基於 8 顆角落感測器的 trilinear 三維空間校正方法。",
                "提出由環境變化反推非連網設備影響係數的資料驅動學習流程。",
                r"提出 $F_{\mathrm{final}} = F_{\mathrm{physics}} + f_\theta$ 的 physics-informed hybrid residual learning 架構。",
                "建立完整研究 pipeline，包含情境生成、模擬、校正、baseline 比較、裝置影響學習、Web demo、MCP 工具介面與論文輸出。",
            ],
        },
    ]


def insert_extras(blocks: List[Block]) -> List[Block]:
    """Insert stable_extra_blocks without dropping any original thesis blocks.

    Previous implementation stopped when it reached 第二章, which truncated the
    rest of the thesis. This version iterates through all blocks and inserts the
    additions exactly once before the 第二章 heading, after the first-chapter
    contribution section has appeared. If that anchor is not found, it falls
    back to inserting after 第一章 緒論.
    """
    extras = stable_extra_blocks()
    output: List[Block] = []
    seen_contribution_heading = False
    inserted = False

    for block in blocks:
        if (
            not inserted
            and seen_contribution_heading
            and block.get("type") == "heading"
            and str(block.get("text", "")).startswith("第二章")
        ):
            output.extend(extras)
            inserted = True

        output.append(block)

        if block.get("type") == "heading" and str(block.get("text")) == "1.5 預期貢獻":
            seen_contribution_heading = True

    if inserted:
        return output

    # Fallback: insert after 第一章 緒論 heading without truncating anything.
    output = []
    for block in blocks:
        output.append(block)
        if (
            not inserted
            and block.get("type") == "heading"
            and str(block.get("text")) == "第一章 緒論"
        ):
            output.extend(extras)
            inserted = True

    if not inserted:
        output = extras + list(blocks)
    return output


def render_document(blocks: List[Block]) -> str:
    body = "\n".join(render_block(b) for b in blocks)
    return rf"""\documentclass[12pt,a4paper]{{article}}
\usepackage[top=2.54cm,bottom=2.54cm,left=2.54cm,right=2.54cm]{{geometry}}
\usepackage{{fontspec}}
\usepackage{{xeCJK}}
\usepackage{{array}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage{{amsmath}}
\usepackage{{listings}}
\usepackage{{setspace}}
\usepackage{{indentfirst}}

\setmainfont{{Times New Roman}}
\setsansfont{{Arial}}
\setmonofont{{Menlo}}
% macOS built-in Traditional Chinese fonts. This avoids garbled CJK text on
% local MacTeX installations that do not have Noto CJK registered.
\setCJKmainfont[AutoFakeBold=2.5, AutoFakeSlant=0.15]{{Songti TC}}
\setCJKsansfont[AutoFakeBold=2.5]{{Heiti TC}}
\setCJKmonofont{{Heiti TC}}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
\hypersetup{{hidelinks}}
\sloppy
\setlength{{\parindent}}{{2em}}
\setlength{{\parskip}}{{0pt}}
\onehalfspacing
\renewcommand{{\contentsname}}{{目錄}}

\begin{{document}}
\pagenumbering{{roman}}
{body}
\end{{document}}
"""


def write_latex(path: Path, blocks: List[Block]) -> None:
    path.write_text(render_document(blocks), encoding="utf-8")


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
    blocks = insert_extras(build_blocks())
    write_latex(TEX_PATH, blocks)
    compile_pdf(TEX_PATH)
    print(f"Wrote {TEX_PATH}")
    if PDF_PATH.exists():
        print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
