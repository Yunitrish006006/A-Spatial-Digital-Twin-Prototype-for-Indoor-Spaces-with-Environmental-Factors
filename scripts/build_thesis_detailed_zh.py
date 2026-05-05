# -*- coding: utf-8 -*-
"""
Build a detailed Chinese thesis draft focused on method explanation.

This generator is intentionally method-oriented rather than submission-oriented.
It emphasizes:

1. What problem the research solves.
2. Where the originality is.
3. Why the model is designed as physics + calibration + residual learning.
4. How the experiments should be interpreted.

Outputs:
- outputs/papers/thesis_detailed_zh.md
- outputs/papers/thesis_detailed_zh.tex

If xelatex is available, it also builds:
- outputs/papers/thesis_detailed_zh.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def h(level: int, title: str) -> str:
    return f"{'#' * level} {title}\n"


def md_escape_block(text: str) -> str:
    return clean_text(text) + "\n"


def latex_escape(text: str) -> str:
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
    return "".join(replacements.get(ch, ch) for ch in text)


def latex_paragraphs(text: str) -> str:
    parts: List[str] = []
    for block in clean_text(text).split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("-"):
            items = [line[1:].strip() for line in block.splitlines() if line.strip().startswith("-")]
            parts.append("\\begin{itemize}\n" + "\n".join(f"\\item {latex_escape(item)}" for item in items) + "\n\\end{itemize}")
        elif block.startswith("```") and block.endswith("```"):
            code = block.strip("`").strip()
            parts.append("\\begin{verbatim}\n" + code + "\n\\end{verbatim}")
        else:
            parts.append(latex_escape(" ".join(block.splitlines())))
    return "\n\n".join(parts)


def build_sections() -> List[Section]:
    return [
        Section(
            1,
            "緒論",
            """
            智慧建築與智慧居家系統需要掌握室內環境狀態，才能支援舒適度評估、能源管理與設備控制。然而，實際房間中常見的冷氣、窗戶與照明往往沒有連網能力，也無法直接回報狀態；同時，房間內通常只能布建少量感測器，難以直接量測完整空間分布。這使得一般數位孿生若同時缺乏設備遙測與高密度量測，便難以對真實房間提供可用的環境估計與控制建議。

            本研究以單一矩形房間為研究場域，提出一個基於有限角落感測器與連續影響場估計之三因子空間數位孿生原型。研究目標不是建立一個僅供展示的室內模擬畫面，而是處理稀疏感測、非連網設備與空間場重建之間的實際落差。
            """,
        ),
        Section(
            2,
            "研究背景",
            """
            在實際室內環境中，感測器部署通常受限於成本、供電、通訊、維護與美觀等因素，因此不可能在每一個空間點都安裝感測器。使用者真正關心的區域也不一定位於感測器附近，例如床邊、書桌前、靠窗處或門邊。因此，若系統只回報單一溫濕度讀值，並不能代表整個房間的舒適狀態。

            另一方面，既有家電不一定具備智慧化介面。冷氣可能無法提供即時輸出功率，窗戶可能只是手動開關，傳統燈具也可能沒有可讀取的 API。這些設備雖然無法直接被系統讀取，卻會實際改變室內溫度、濕度與照度。因此，本研究關注的不是單純的智慧裝置整合，而是如何由環境觀測反推不可觀測設備的影響。
            """,
        ),
        Section(
            2,
            "本研究解決之核心問題",
            """
            本研究針對智慧室內環境建模中一個實際存在但容易被簡化的問題：在缺乏設備連網能力與高密度感測器部署的情況下，是否仍能重建室內空間環境分布，並推估設備對環境的影響。

            具體而言，本研究解決以下三個核心問題。

            第一，稀疏感測空間重建問題。在僅有 8 顆角落感測器的條件下，空間中可觀測資訊遠低於需要預測的空間維度。例如本研究的標準網格為 16 × 12 × 6，共 1152 個空間點，但每個時間點只有 8 個感測位置。此問題本質上是高度欠定問題，若僅使用距離插值或純黑盒模型，容易在房間中央、設備附近或家具遮蔽區域產生不可靠估計。本研究透過物理模型結合空間校正，使低維觀測能夠約束高維空間場。

            第二，非連網設備影響推估問題。在多數室內場景中，冷氣、窗戶與燈具不一定具有 API 或 IoT 回傳能力，因此系統無法直接取得其運作狀態與輸出功率。本研究將設備視為不可直接觀測但可由環境變化間接推估的影響源，透過設備啟用前後的感測器殘差，學習其對溫度、濕度與照度的影響係數。

            第三，稀疏監督下的模型誤差補償問題。純物理模型會因為簡化假設而產生系統性誤差，例如忽略複雜氣流、材料熱容量、反射路徑或家具遮蔽細節；但若直接使用神經網路學習完整三維場，又會因監督資料過度稀疏而缺乏可靠性。因此，本研究採用 hybrid residual learning，讓物理模型負責主要結構，神經網路只學習殘差。
            """,
        ),
        Section(
            2,
            "研究貢獻與原創性",
            """
            本研究的原創性不在於單獨提出某一個複雜神經網路，而在於將稀疏感測、非連網設備推估、可解釋物理模型、感測器校正與殘差學習組合成一個可執行且可驗證的室內空間數位孿生方法。

            本研究主要貢獻如下。

            第一，提出一個可在非連網設備環境下運作的空間數位孿生架構。與多數依賴 IoT 設備或完整裝置 API 的智慧建築方法不同，本研究假設設備可能無法回報自身狀態，並以環境感測資料反推設備影響，使方法更接近一般房間中的實際部署情境。

            第二，提出基於 8 顆角落感測器的三維空間校正方法。本研究使用 trilinear correction，以房間八個角落的感測器對三維空間中的校正場進行約束。此設計使 8 顆角落感測器能對應 8 個校正參數，在極低感測器數量下仍保留明確的空間結構。

            第三，提出非連網設備影響的資料驅動學習方法。本研究不要求直接觀測設備輸出，而是利用設備啟用前後的環境變化，以 least squares 或 ridge regression 學習設備影響係數。此方法將傳統設備轉化為可被數位孿生估計的環境影響源。

            第四，提出 physics-informed hybrid residual learning 架構。本研究不使用神經網路直接取代整個空間場模型，而是建立 F_final = F_physics + f_theta 的殘差修正形式。這使模型同時具備可解釋性與資料修正能力，並降低在稀疏監督下訓練黑盒模型的風險。

            第五，建立完整可重現的研究 pipeline。專案包含情境生成、模擬、校正、baseline 比較、裝置影響學習、hybrid residual 實驗、Web demo、MCP 工具介面與論文輸出腳本，使方法不是停留在概念描述，而是可被實際執行與重複驗證。
            """,
        ),
        Section(
            1,
            "問題形式化",
            """
            本研究將室內環境表示為三個隨時間變化的連續空間場：溫度 T(x, y, z, t)、濕度 H(x, y, z, t) 與照度 L(x, y, z, t)。其中 (x, y, z) 表示房間內的三維座標，t 表示時間。

            對於每一個感測器 s_i，其觀測值可表示為 y_i(t) = [T_i(t), H_i(t), L_i(t)]。由於感測器數量遠少於空間網格點數，系統的目標不是單純對感測器資料做平滑插值，而是利用房間結構、設備位置、設備作用模式與校正模型，推估完整空間場 F(x, y, z, t)。

            因此，本研究的核心任務可以寫成：在已知房間幾何、少量感測器觀測與可能的設備配置下，估計完整三維環境場，並學習不可直接觀測設備對該環境場的影響。
            """,
        ),
        Section(
            1,
            "系統架構與方法",
            """
            系統架構分為五個層次：core orchestration layer、physics digital twin layer、calibration and impact learning layer、optional hybrid residual neural layer，以及 web/MCP service layer。

            core 層負責建立房間、感測器、設備、家具與情境，並統一處理 CLI、Web demo 與 MCP tool call 的輸入。physics 層是主模型，負責估計 bulk room state 與 device local field。calibration 層使用感測器殘差進行 active device power calibration 與 trilinear residual correction。neural 層只在需要時學習物理模型剩餘誤差。service 層則將同一套模型能力提供給 Web UI、MCP client 與本地 LLM bridge 使用。
            """,
        ),
        Section(
            2,
            "Physics Digital Twin 主模型",
            """
            本研究的主模型可概念化為 bulk state 加上局部設備影響場。bulk state 描述整個房間的背景環境，例如平均溫度、平均濕度與基礎照度；local field 則描述設備對不同空間位置造成的非均勻影響。

            對冷氣而言，模型需要描述其出風方向、降溫強度、作用距離與時間響應，並可包含弱除濕效果。對窗戶而言，模型需要描述外部溫度、外部濕度與日照進入室內後的影響。對照明而言，模型需要描述光源位置、距離衰減、遮蔽與弱熱效應。

            這種設計的重點是讓模型具備設備語意，而不是只將感測器值進行幾何插值。因此，當冷氣、窗戶或照明狀態改變時，模型能產生具有方向性與局部性的空間變化。
            """,
        ),
        Section(
            2,
            "8 顆角落感測器與 Trilinear Calibration",
            """
            本研究固定使用房間八個角落的感測器，包括地面四角與天花板四角。這種配置的優點是感測器數量固定、佈署邏輯清楚，且可自然對應三維空間中的 trilinear correction。

            校正模型形式為：

            ```
            C(x, y, z) = c0 + c1X + c2Y + c3Z + c4XY + c5XZ + c6YZ + c7XYZ
            ```

            其中 X、Y、Z 為正規化後的空間座標。此模型共有 8 個參數，能由 8 顆角落感測器的殘差支撐。換言之，角落感測器不是任意選擇，而是與三線性校正模型具有結構對應關係。

            這個校正方法的定位是修正主模型在空間上的系統性偏差，而不是宣稱只靠 8 個點就能直接觀測到完整三維真值。其合理性來自於先有 physics prior，再由感測器殘差對模型進行低維校正。
            """,
        ),
        Section(
            2,
            "非連網設備影響學習",
            """
            對於無法直接回報狀態的設備，本研究採用 before/after observation 的方式估計設備影響。當某設備在時間 t0 前後狀態發生變化時，感測器觀測差異可表示為 Delta y = y_after - y_before。此變化包含設備造成的影響、背景漂移與噪聲。

            系統可將多個感測器位置的變化組成回歸問題，估計設備對溫度、濕度與照度的影響係數。在單一設備情境下可使用 least squares，在多設備同時作用時則可使用 ridge regression 降低共線性造成的不穩定。

            此方法的重點是由環境反推設備，而不是由設備 API 直接讀取設備。這使本研究可以處理傳統冷氣、手動窗戶與普通燈具等非智慧設備。
            """,
        ),
        Section(
            2,
            "Hybrid Residual Neural Network",
            """
            本研究的神經網路層不是主模型，而是殘差修正器。完整形式為：

            ```
            F_final(p, t) = F_physics(p, t) + f_theta(features(p, t))
            ```

            其中 p 表示空間點，F_physics 為可解釋主模型輸出，f_theta 為小型 MLP，用來學習 truth 與 physics estimate 之間的剩餘誤差。

            這樣設計的原因是：在只有 8 顆角落感測器時，直接訓練完整三維 neural field 會使監督資訊過度稀疏，容易在未觀測區域產生不可驗證的預測。相反地，先使用 physics model 提供合理空間結構，再讓 neural network 學習系統性殘差，可以兼顧可解釋性、穩定性與資料驅動能力。
            """,
        ),
        Section(
            1,
            "實驗設計與評估方法",
            """
            本研究之實驗目的不是單純展示系統畫面，而是驗證三個問題：第一，在稀疏感測條件下是否能有效重建三維空間環境場；第二，power calibration 與 trilinear correction 是否能降低模型誤差；第三，hybrid residual learning 是否能在物理模型基礎上進一步提升估計準確度。

            實驗場景為 6 m × 4 m × 3 m 的單一房間，空間離散為 16 × 12 × 6 規則網格，共 1152 個點。每個點包含溫度、濕度與照度三個變數。感測器配置固定為 8 顆角落感測器，代表極端稀疏觀測條件。

            主要情境包含冷氣、窗戶與照明單獨或共同作用的標準案例，並包含窗戶矩陣實驗。窗戶矩陣由 4 個時段、3 種天氣與 4 個季節組成，共 48 組情境，用以測試外部溫度、外部濕度與日照條件變化下模型是否穩定。
            """,
        ),
        Section(
            2,
            "Baseline 與消融實驗",
            """
            本研究至少應比較四種模型設定。

            - IDW baseline：僅根據感測器與目標點距離進行反距離加權插值，不使用設備語意與物理結構。
            - Physics only：僅使用物理主模型，不進行感測器校正。
            - Physics + Calibration：使用主模型並加入 power calibration 與 trilinear correction。
            - Full model：在校正後模型上加入 hybrid residual neural correction。

            消融實驗的目的，是將模型改進拆解為可解釋的步驟。若完整模型優於 IDW，代表物理結構相較純插值有效；若 Physics + Calibration 優於 Physics only，代表角落感測器校正有效；若 Full model 進一步改善，代表 residual learning 能補足物理模型無法描述的誤差。
            """,
        ),
        Section(
            2,
            "評估指標",
            """
            主要評估指標為平均絕對誤差 MAE，分別對溫度、濕度與照度計算。對於完整空間場，MAE 可衡量所有網格點上預測值與 truth 之間的平均差異。對於實際使用情境，亦可計算特定區域的 zone error，例如床邊、窗邊或書桌區域的平均誤差。

            除 MAE 外，也可使用 improvement ratio 量化模型相對 baseline 的改善幅度：

            ```
            Improvement = (Error_baseline - Error_model) / Error_baseline
            ```

            此指標能清楚呈現 calibration 與 residual learning 對誤差降低的貢獻。
            """,
        ),
        Section(
            2,
            "結果解讀原則",
            """
            本研究的結果應避免過度宣稱。若 ground truth 來自受控模擬，則可用於驗證模型在已知情境與完整真值下的重建能力，但不能直接等同於所有真實房間的高精度保證。若使用公開資料集，則應將其視為 task-aligned benchmark，而不是完整三維場真值。若使用真實房間快照，則應清楚標示其感測點位、時間範圍與是否包含介入實驗。

            因此，本研究的合理 claim boundary 是：在已知房間幾何、有限感測器、可描述設備位置與受控或半受控環境資料下，physics-informed sparse-sensing digital twin 能提供比純插值更具結構性的空間估計，並能透過校正與殘差學習降低誤差。至於推薦動作是否具有真實因果改善效果，仍需進一步 before/after 介入實驗驗證。
            """,
        ),
        Section(
            1,
            "系統實作",
            """
            本研究以 Python 實作完整原型。核心程式碼分為 digital_twin/core、digital_twin/physics、digital_twin/neural、digital_twin/mcp 與 digital_twin/web。core 負責資料結構與 scenario orchestration；physics 負責主模型、baseline、learning 與 recommendation；neural 負責 hybrid residual model；mcp 負責 MCP server 與本地 LLM bridge；web 負責展示介面與視覺化輸出。

            scripts 目錄提供主要執行入口，包括 run_demo.py、run_window_matrix.py、run_hybrid_residual_experiment.py、run_mcp_server.py、run_web_demo.py，以及論文與簡報生成腳本。outputs 目錄則保存資料、圖表與論文輸出。
            """,
        ),
        Section(
            1,
            "結論與未來工作",
            """
            本研究提出一個以稀疏感測為基礎的單房間空間數位孿生方法，針對非連網設備、有限感測器與三維環境場重建問題，建立 physics model、感測器校正、設備影響學習與 hybrid residual learning 的分層架構。

            本研究最重要的結論是：在感測器數量有限時，不應直接依賴純黑盒模型重建完整空間場；較穩定的做法是先建立可解釋物理結構，再使用有限感測器進行低維校正，最後以殘差學習補足模型不足。此設計不僅能保留可解釋性，也能讓方法較容易對接真實資料。

            未來工作包含三個方向。第一，導入更多真實房間長期資料，驗證模型在不同季節、作息與設備使用模式下的穩定性。第二，增加移動式量測或中間區域感測器，以取得更密集的空間 ground truth。第三，執行推薦動作的 before/after 介入實驗，驗證模型排序是否能在真實環境中帶來可量測改善。
            """,
        ),
    ]


def build_markdown(sections: Iterable[Section]) -> str:
    lines: List[str] = []
    lines.append("# 單房間非連網家電環境影響學習之稀疏感測空間數位孿生系統\n")
    lines.append("**版本：方法說明詳細版**\n")
    lines.append("**用途：中文碩士論文草稿生成，不以 IEEE 投稿格式為主要目標。**\n")
    for section in sections:
        lines.append(h(section.level, section.title))
        lines.append(md_escape_block(section.body))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_latex(sections: Iterable[Section]) -> str:
    body: List[str] = []
    for section in sections:
        if section.level == 1:
            body.append(f"\\chapter{{{latex_escape(section.title)}}}")
        elif section.level == 2:
            body.append(f"\\section{{{latex_escape(section.title)}}}")
        elif section.level == 3:
            body.append(f"\\subsection{{{latex_escape(section.title)}}}")
        else:
            body.append(f"\\paragraph{{{latex_escape(section.title)}}}")
        body.append(latex_paragraphs(section.body))

    return r'''
\documentclass[12pt,a4paper]{report}
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{geometry}
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
{\large 方法說明詳細版\\[2cm]}
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
    sections = build_sections()
    md_path = OUTPUT_DIR / "thesis_detailed_zh.md"
    tex_path = OUTPUT_DIR / "thesis_detailed_zh.tex"
    pdf_path = OUTPUT_DIR / "thesis_detailed_zh.pdf"

    md_path.write_text(build_markdown(sections), encoding="utf-8")
    tex_path.write_text(build_latex(sections), encoding="utf-8")

    xelatex = shutil.which("xelatex")
    if xelatex:
        subprocess.run(
            [xelatex, "-interaction=nonstopmode", tex_path.name],
            cwd=OUTPUT_DIR,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [xelatex, "-interaction=nonstopmode", tex_path.name],
            cwd=OUTPUT_DIR,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not pdf_path.exists():
            print("LaTeX was executed, but PDF was not produced. Check the .log file in outputs/papers.")
    else:
        print("xelatex not found; generated Markdown and LaTeX only.")

    print(f"Wrote {md_path}")
    print(f"Wrote {tex_path}")
    if pdf_path.exists():
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    write_outputs()
