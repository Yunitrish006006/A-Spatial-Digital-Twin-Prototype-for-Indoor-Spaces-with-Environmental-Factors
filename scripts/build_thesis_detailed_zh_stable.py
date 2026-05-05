# -*- coding: utf-8 -*-
"""
Stable detailed Chinese thesis generator.

This version avoids Markdown-table-to-PDF conversion problems by rendering
symbol tables and math-heavy content directly as LaTeX.

Outputs:
- outputs/papers/thesis_detailed_zh_stable.md
- outputs/papers/thesis_detailed_zh_stable.tex
- outputs/papers/thesis_detailed_zh_stable.pdf, if xelatex is available
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "papers"


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    body: str


def clean_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def latex_escape(text: object) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(text))


def latex_escape_with_math(text: object) -> str:
    """Escape normal text but preserve inline math segments: $...$."""
    parts = re.split(r"(\$[^$]+\$)", str(text))
    return "".join(part if i % 2 == 1 else latex_escape(part) for i, part in enumerate(parts))


def symbol_table_latex() -> str:
    return r"""
\begin{table}[htbp]
\centering
\footnotesize
\renewcommand{\arraystretch}{1.25}
\begin{tabular}{|>{\raggedright\arraybackslash}p{0.32\textwidth}|>{\raggedright\arraybackslash}p{0.55\textwidth}|}
\hline
\textbf{符號} & \textbf{意義} \\
\hline
$T_0, H_0, L_0$ & Indoor baseline，即設備作用與 residual correction 前的起始室內溫度、相對濕度與照度。 \\
\hline
$T_{\mathrm{out}}, H_{\mathrm{out}}, S_{\mathrm{out}}$ & 室外溫度、室外相對濕度與外部日照照度。 \\
\hline
$p_j$ & 第 $j$ 個裝置的 power scale，可由感測資料校正。 \\
\hline
$g_k, r_k$ & 全室平均響應與空間局部響應的簡化增益係數。 \\
\hline
$M(t)$ & 房間混合係數，用於控制垂直分層強度。 \\
\hline
$C_v(\mathbf{p}, t)$ & 由 8 顆角落感測器 residual 形成的三線性校正場。 \\
\hline
\end{tabular}
\end{table}
"""


def latex_paragraphs(text: str) -> str:
    parts: List[str] = []
    for block in clean_text(text).split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block == "[[SYMBOL_TABLE]]":
            parts.append(symbol_table_latex())
        elif block.startswith("-"):
            items = [line[1:].strip() for line in block.splitlines() if line.strip().startswith("-")]
            parts.append(
                "\\begin{itemize}\n"
                + "\n".join(f"\\item {latex_escape_with_math(item)}" for item in items)
                + "\n\\end{itemize}"
            )
        elif block.startswith("```") and block.endswith("```"):
            code = block.removeprefix("```").removesuffix("```").strip()
            parts.append("\\begin{verbatim}\n" + code + "\n\\end{verbatim}")
        else:
            parts.append(latex_escape_with_math(" ".join(block.splitlines())))
    return "\n\n".join(parts)


def sections() -> List[Section]:
    return [
        Section(1, "緒論", """
        智慧建築與智慧居家系統需要掌握室內環境狀態，才能支援舒適度評估、能源管理與設備控制。然而，實際房間中常見的冷氣、窗戶與照明往往沒有連網能力，也無法直接回報狀態；同時，房間內通常只能布建少量感測器，難以直接量測完整空間分布。這使得一般數位孿生若同時缺乏設備遙測與高密度量測，便難以對真實房間提供可用的環境估計與控制建議。

        本研究以單一矩形房間為研究場域，提出一個基於有限角落感測器與連續影響場估計之三因子空間數位孿生原型。研究目標不是建立一個僅供展示的室內模擬畫面，而是處理稀疏感測、非連網設備與空間場重建之間的實際落差。
        """),
        Section(2, "本研究解決之核心問題", """
        本研究針對智慧室內環境建模中一個實際存在但容易被簡化的問題：在缺乏設備連網能力與高密度感測器部署的情況下，是否仍能重建室內空間環境分布，並推估設備對環境的影響。

        第一，稀疏感測空間重建問題。在僅有 8 顆角落感測器的條件下，空間中可觀測資訊遠低於需要預測的空間維度。例如本研究的標準網格為 16 × 12 × 6，共 1152 個空間點，但每個時間點只有 8 個感測位置。此問題本質上是高度欠定問題，若僅使用距離插值或純黑盒模型，容易在房間中央、設備附近或家具遮蔽區域產生不可靠估計。本研究透過物理模型結合空間校正，使低維觀測能夠約束高維空間場。

        第二，非連網設備影響推估問題。在多數室內場景中，冷氣、窗戶與燈具不一定具有 API 或 IoT 回傳能力，因此系統無法直接取得其運作狀態與輸出功率。本研究將設備視為不可直接觀測但可由環境變化間接推估的影響源，透過設備啟用前後的感測器殘差，學習其對溫度、濕度與照度的影響係數。

        第三，稀疏監督下的模型誤差補償問題。純物理模型會因為簡化假設而產生系統性誤差，但若直接使用神經網路學習完整三維場，又會因監督資料過度稀疏而缺乏可靠性。因此，本研究採用 hybrid residual learning，讓物理模型負責主要結構，神經網路只學習殘差。
        """),
        Section(2, "研究貢獻與原創性", """
        本研究的原創性不在於單獨提出某一個複雜神經網路，而在於將稀疏感測、非連網設備推估、可解釋物理模型、感測器校正與殘差學習組合成一個可執行且可驗證的室內空間數位孿生方法。

        - 提出一個可在非連網設備環境下運作的空間數位孿生架構。
        - 提出基於 8 顆角落感測器的三維空間校正方法。
        - 提出非連網設備影響的資料驅動學習方法。
        - 提出 $F_{\mathrm{final}} = F_{\mathrm{physics}} + f_\theta$ 的 physics-informed hybrid residual learning 架構。
        - 建立完整可重現的研究 pipeline，包含情境生成、模擬、校正、baseline 比較、裝置影響學習、hybrid residual 實驗、Web demo、MCP 工具介面與論文輸出腳本。
        """),
        Section(1, "問題形式化", """
        本研究將室內環境表示為三個隨時間變化的連續空間場：溫度 $T(x,y,z,t)$、濕度 $H(x,y,z,t)$ 與照度 $L(x,y,z,t)$。其中 $(x,y,z)$ 表示房間內的三維座標，$t$ 表示時間。

        對於每一個感測器 $s_i$，其觀測值可表示為 $y_i(t) = [T_i(t), H_i(t), L_i(t)]$。由於感測器數量遠少於空間網格點數，系統的目標不是單純對感測器資料做平滑插值，而是利用房間結構、設備位置、設備作用模式與校正模型，推估完整空間場 $F(x,y,z,t)$。
        """),
        Section(1, "系統架構與方法", """
        系統架構分為五個層次：core orchestration layer、physics digital twin layer、calibration and impact learning layer、optional hybrid residual neural layer，以及 web/MCP service layer。
        """),
        Section(2, "共用符號說明", """
        本研究使用之主要符號如下。此處在 LaTeX 輸出中使用原生 tabular 排版，避免 PDF 中 Markdown 表格轉換造成數學符號顯示錯誤。

        [[SYMBOL_TABLE]]
        """),
        Section(2, "Physics Digital Twin 主模型", """
        本研究的主模型可概念化為 bulk state 加上局部設備影響場。bulk state 描述整個房間的背景環境，例如平均溫度、平均濕度與基礎照度；local field 則描述設備對不同空間位置造成的非均勻影響。

        對冷氣而言，模型需要描述其出風方向、降溫強度、作用距離與時間響應，並可包含弱除濕效果。對窗戶而言，模型需要描述外部溫度、外部濕度與日照進入室內後的影響。對照明而言，模型需要描述光源位置、距離衰減、遮蔽與弱熱效應。
        """),
        Section(2, "8 顆角落感測器與 Trilinear Calibration", """
        本研究固定使用房間八個角落的感測器，包括地面四角與天花板四角。這種配置的優點是感測器數量固定、佈署邏輯清楚，且可自然對應三維空間中的 trilinear correction。

        校正模型形式為：

        ```
        C(x, y, z) = c0 + c1X + c2Y + c3Z + c4XY + c5XZ + c6YZ + c7XYZ
        ```

        其中 $X$、$Y$、$Z$ 為正規化後的空間座標。此模型共有 8 個參數，能由 8 顆角落感測器的殘差支撐。
        """),
        Section(2, "非連網設備影響學習", """
        對於無法直接回報狀態的設備，本研究採用 before/after observation 的方式估計設備影響。當某設備在時間 $t_0$ 前後狀態發生變化時，感測器觀測差異可表示為 $\Delta y = y_{\mathrm{after}} - y_{\mathrm{before}}$。

        系統可將多個感測器位置的變化組成回歸問題，估計設備對溫度、濕度與照度的影響係數。在單一設備情境下可使用 least squares，在多設備同時作用時則可使用 ridge regression 降低共線性造成的不穩定。
        """),
        Section(2, "Hybrid Residual Neural Network", """
        本研究的神經網路層不是主模型，而是殘差修正器。完整形式為：

        ```
        F_final(p, t) = F_physics(p, t) + f_theta(features(p, t))
        ```

        其中 $p$ 表示空間點，$F_{\mathrm{physics}}$ 為可解釋主模型輸出，$f_\theta$ 為小型 MLP，用來學習 truth 與 physics estimate 之間的剩餘誤差。
        """),
        Section(1, "實驗設計與評估方法", """
        本研究之實驗目的不是單純展示系統畫面，而是驗證三個問題：第一，在稀疏感測條件下是否能有效重建三維空間環境場；第二，power calibration 與 trilinear correction 是否能降低模型誤差；第三，hybrid residual learning 是否能在物理模型基礎上進一步提升估計準確度。

        實驗場景為 6 m × 4 m × 3 m 的單一房間，空間離散為 16 × 12 × 6 規則網格，共 1152 個點。每個點包含溫度、濕度與照度三個變數。感測器配置固定為 8 顆角落感測器，代表極端稀疏觀測條件。
        """),
        Section(2, "Baseline 與消融實驗", """
        - IDW baseline：僅根據感測器與目標點距離進行反距離加權插值，不使用設備語意與物理結構。
        - Physics only：僅使用物理主模型，不進行感測器校正。
        - Physics + Calibration：使用主模型並加入 power calibration 與 trilinear correction。
        - Full model：在校正後模型上加入 hybrid residual neural correction。
        """),
        Section(2, "結果解讀原則", """
        本研究的結果應避免過度宣稱。若 ground truth 來自受控模擬，則可用於驗證模型在已知情境與完整真值下的重建能力，但不能直接等同於所有真實房間的高精度保證。若使用公開資料集，則應將其視為 task-aligned benchmark，而不是完整三維場真值。
        """),
        Section(1, "結論與未來工作", """
        本研究提出一個以稀疏感測為基礎的單房間空間數位孿生方法，針對非連網設備、有限感測器與三維環境場重建問題，建立 physics model、感測器校正、設備影響學習與 hybrid residual learning 的分層架構。
        """),
    ]


def build_markdown(parts: Iterable[Section]) -> str:
    lines: List[str] = [
        "# 單房間非連網家電環境影響學習之稀疏感測空間數位孿生系統\n",
        "**版本：方法說明詳細穩定版**\n",
        "**用途：中文碩士論文草稿生成，不以 IEEE 投稿格式為主要目標。**\n",
    ]
    for section in parts:
        lines.append(f"{'#' * section.level} {section.title}\n")
        body = clean_text(section.body).replace("[[SYMBOL_TABLE]]", "見 PDF/LaTeX 輸出之正式符號表。")
        lines.append(body + "\n")
    return "\n".join(lines).strip() + "\n"


def build_latex(parts: Iterable[Section]) -> str:
    body: List[str] = []
    for section in parts:
        if section.level == 1:
            body.append(f"\\chapter{{{latex_escape(section.title)}}}")
        elif section.level == 2:
            body.append(f"\\section{{{latex_escape(section.title)}}}")
        else:
            body.append(f"\\subsection{{{latex_escape(section.title)}}}")
        body.append(latex_paragraphs(section.body))

    return r'''
\documentclass[12pt,a4paper]{report}
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{geometry}
\usepackage{array}
\usepackage{setspace}
\usepackage{hyperref}
\geometry{left=3cm,right=2.5cm,top=2.5cm,bottom=2.5cm}
\setstretch{1.35}
\setmainfont{Times New Roman}
\setCJKmainfont{Noto Serif CJK TC}
\hypersetup{colorlinks=true, linkcolor=black, urlcolor=blue}
\begin{document}
\begin{titlepage}
\centering
{\Large 國立彰化師範大學\\資訊工程學系碩士班\\碩士論文草稿\\[2cm]}
{\LARGE 單房間非連網家電環境影響學習之稀疏感測空間數位孿生系統\\[1cm]}
{\large 方法說明詳細穩定版\\[2cm]}
{\large 研究生：林昀佑\\}
\vfill
{\large \today}
\end{titlepage}
\tableofcontents
\clearpage
''' + "\n\n".join(body) + r'''
\end{document}
'''


def write_outputs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    thesis_sections = sections()
    md_path = OUTPUT_DIR / "thesis_detailed_zh_stable.md"
    tex_path = OUTPUT_DIR / "thesis_detailed_zh_stable.tex"
    pdf_path = OUTPUT_DIR / "thesis_detailed_zh_stable.pdf"

    md_path.write_text(build_markdown(thesis_sections), encoding="utf-8")
    tex_path.write_text(build_latex(thesis_sections), encoding="utf-8")

    xelatex = shutil.which("xelatex")
    if xelatex:
        for _ in range(2):
            subprocess.run(
                [xelatex, "-interaction=nonstopmode", tex_path.name],
                cwd=OUTPUT_DIR,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    else:
        print("xelatex not found; generated Markdown and LaTeX only.")

    print(f"Wrote {md_path}")
    print(f"Wrote {tex_path}")
    if pdf_path.exists():
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    write_outputs()
