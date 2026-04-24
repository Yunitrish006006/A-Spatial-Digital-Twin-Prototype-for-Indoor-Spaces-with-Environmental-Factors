from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

from build_thesis_docx import ensure_image_asset


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
PAPERS = OUTPUTS / "papers"
DATA = OUTPUTS / "data"
FIGURES = OUTPUTS / "figures"
ARCHITECTURE = FIGURES / "architecture"
PRESENTATION_PATH = PAPERS / "thesis_presentation_zh.pptx"
OUTLINE_PATH = ROOT / "docs" / "thesis" / "presentation_outline_zh.md"
LONG_PRESENTATION_PATH = PAPERS / "thesis_presentation_zh_30min.pptx"
LONG_OUTLINE_PATH = ROOT / "docs" / "thesis" / "presentation_outline_zh_30min.md"

BACKGROUND_COLOR = RGBColor(238, 242, 247)
HEADER_FILL = RGBColor(23, 37, 61)
HEADER_TEXT = RGBColor(255, 255, 255)
HEADER_SUBTITLE = RGBColor(211, 225, 241)
TITLE_COLOR = HEADER_TEXT
TEXT_COLOR = RGBColor(25, 32, 40)
ACCENT_COLOR = RGBColor(0, 83, 130)
MUTED_COLOR = RGBColor(70, 80, 92)
CARD_FILL = RGBColor(255, 255, 255)
CARD_LINE = RGBColor(124, 143, 165)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def average_field_mae(summary: dict) -> dict:
    scenarios = summary.get("scenarios", [])
    metrics = ("temperature", "humidity", "illuminance")
    return {
        metric: round(sum(item["field_mae"][metric] for item in scenarios) / max(len(scenarios), 1), 4)
        for metric in metrics
    }


def best_recommendations(summary: dict) -> List[Tuple[str, str]]:
    output = []
    for item in summary.get("scenarios", []):
        recommendations = item.get("recommendations", [])
        best = recommendations[0]["name"] if recommendations else "n/a"
        output.append((item["name"], best))
    return output[:5]


def scenario_map(summary: dict) -> dict:
    return {item["name"]: item for item in summary.get("scenarios", [])}


def init_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def style_slide(slide) -> None:
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = BACKGROUND_COLOR


def new_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    style_slide(slide)
    return slide


def add_title(slide, text: str, subtitle: str = "") -> None:
    header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.16))
    header.fill.solid()
    header.fill.fore_color.rgb = HEADER_FILL
    header.line.color.rgb = HEADER_FILL
    title_box = slide.shapes.add_textbox(Inches(0.58), Inches(0.17), Inches(12.2), Inches(0.62))
    frame = title_box.text_frame
    frame.clear()
    frame.word_wrap = True
    p = frame.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name = "PingFang TC"
    run.font.size = Pt(22 if len(text) > 24 else 24)
    run.font.bold = True
    run.font.color.rgb = TITLE_COLOR
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.75), Inches(12.1), Inches(0.34))
        sub_frame = sub_box.text_frame
        sub_frame.clear()
        sub_p = sub_frame.paragraphs[0]
        sub_run = sub_p.add_run()
        sub_run.text = subtitle
        sub_run.font.name = "PingFang TC"
        sub_run.font.size = Pt(11)
        sub_run.font.color.rgb = HEADER_SUBTITLE


def add_footer(slide, page: int) -> None:
    box = slide.shapes.add_textbox(Inches(12.25), Inches(7.0), Inches(0.6), Inches(0.25))
    frame = box.text_frame
    frame.clear()
    p = frame.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = str(page)
    run.font.name = "Arial"
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED_COLOR


def add_bullets(slide, left: float, top: float, width: float, height: float, items: Sequence[str], level0_size: int = 18) -> None:
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    for index, item in enumerate(items):
        p = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        p.text = item
        p.level = 0
        p.space_after = Pt(8)
        p.font.name = "PingFang TC"
        p.font.size = Pt(level0_size)
        p.font.color.rgb = TEXT_COLOR


def add_card(slide, left: float, top: float, width: float, height: float, title: str, body_lines: Sequence[str]) -> None:
    shape = slide.shapes.add_shape(1, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_FILL
    shape.line.color.rgb = CARD_LINE
    shape.line.width = Pt(1.2)
    frame = shape.text_frame
    frame.clear()
    frame.vertical_anchor = MSO_ANCHOR.TOP
    p = frame.paragraphs[0]
    p.text = title
    p.font.name = "PingFang TC"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_COLOR
    p.space_after = Pt(8)
    for line in body_lines:
        para = frame.add_paragraph()
        para.text = line
        para.font.name = "PingFang TC"
        para.font.size = Pt(13)
        para.font.color.rgb = TEXT_COLOR
        para.space_after = Pt(4)


def add_picture(slide, source: Path, left: float, top: float, width: float, height: float) -> None:
    png = ensure_image_asset({"path": str(source.relative_to(ROOT)), "asset_name": source.stem})
    slide.shapes.add_picture(str(png), Inches(left), Inches(top), width=Inches(width), height=Inches(height))


def add_two_column_title_body(slide, title: str, left_items: Sequence[str], right_image: Path, subtitle: str = "") -> None:
    add_title(slide, title, subtitle)
    add_bullets(slide, 0.8, 1.55, 5.0, 4.9, left_items, level0_size=18)
    add_picture(slide, right_image, 6.3, 1.45, 6.2, 4.9)


def build_presentation() -> Presentation:
    prs = init_presentation()
    validation_summary = read_json(DATA / "validation_summary.json")
    submission_summary = read_json(DATA / "submission_readiness_summary.json")
    window_summary = read_json(DATA / "window_matrix_summary.json")
    bedroom_summary = read_json(DATA / "bedroom_01_weekly" / "weekly_simulation_summary.json")
    avg_mae = average_field_mae(validation_summary)
    bedroom_aggregate = bedroom_summary["aggregate"]

    # Slide 1
    slide = new_slide(prs)
    add_title(
        slide,
        "單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型",
        "A Sparse-Sensing Spatial Digital Twin for Learning Environmental Impacts of Non-Networked Appliances in a Single Room",
    )
    add_bullets(
        slide,
        0.9,
        1.7,
        5.4,
        3.8,
        [
            "研究生：林昀佑",
            "指導教授：易昶霈教授、沈慧宇副教授",
            "系所：國立彰化師範大學資訊工程學系碩士班",
            "主題：以 8 顆角落感測器重建單房間溫度、濕度、照度場",
        ],
        level0_size=20,
    )
    add_picture(slide, ARCHITECTURE / "整體分層架構.svg", 6.7, 1.5, 5.6, 4.8)
    add_footer(slide, 1)

    # Slide 2
    slide = new_slide(prs)
    add_title(slide, "研究問題與動機")
    add_card(
        slide,
        0.7,
        1.5,
        3.8,
        3.9,
        "問題背景",
        [
            "一般房間內仍存在大量非連網裝置",
            "冷氣、窗戶、照明會改變環境",
            "但系統通常無法直接讀到其狀態",
        ],
    )
    add_card(
        slide,
        4.75,
        1.5,
        3.8,
        3.9,
        "核心挑戰",
        [
            "只有少量感測器，無法直接知道全室分布",
            "裝置可能新增、移動，家具也會阻擋傳遞",
            "早期純插值與 local-only 模型都出現不合理結果",
        ],
    )
    add_card(
        slide,
        8.8,
        1.5,
        3.8,
        3.9,
        "研究目標",
        [
            "重建三因子空間場",
            "學習非連網裝置對環境的影響",
            "以 Web 與工具介面提供查詢與決策能力",
        ],
    )
    add_footer(slide, 2)

    # Slide 3
    slide = new_slide(prs)
    add_title(slide, "系統架構")
    add_picture(slide, ARCHITECTURE / "整體分層架構.svg", 0.8, 1.4, 6.0, 5.2)
    add_bullets(
        slide,
        7.1,
        1.6,
        5.2,
        5.0,
        [
            "入口分成使用者互動層與 AI 工具呼叫層",
            "所有請求都先進入服務編排層",
            "後端主體為環境數位孿生核心與校正學習層",
            "hybrid residual 只作為 optional 第二層修正器",
        ],
        level0_size=17,
    )
    add_footer(slide, 3)

    # Slide 4
    slide = new_slide(prs)
    add_title(slide, "房間拓樸、感測器與目標區域")
    add_picture(slide, ARCHITECTURE / "房間感測器與目標區域配置.svg", 0.8, 1.4, 6.0, 5.3)
    add_card(
        slide,
        7.1,
        1.55,
        5.0,
        4.6,
        "固定設定",
        [
            "房間尺寸：6 m × 4 m × 3 m",
            "感測器：地面四角 + 天花板四角，共 8 顆",
            "區域：window_zone / center_zone / door_side_zone",
            "設備：ac_main / window_main / light_main",
            "採樣網格：16 × 12 × 6",
        ],
    )
    add_footer(slide, 4)

    # Slide 5
    slide = new_slide(prs)
    add_title(slide, "數學模型")
    add_card(
        slide,
        0.7,
        1.45,
        5.9,
        4.8,
        "核心表示式",
        [
            "F_v(x,y,z,t) = B_v^bulk(t) + B_v^local(x,y,z,t)",
            "                 + Σ I_j,v^local(x,y,z,t) + C_v(x,y,z)",
            "bulk：全室平均狀態",
            "local：設備附近與局部空間差異",
            "C_v：由角落感測器殘差擬合的 trilinear 校正場",
        ],
    )
    add_card(
        slide,
        6.85,
        1.45,
        5.8,
        4.8,
        "模型特點",
        [
            "冷氣、窗戶、照明都是模組化裝置",
            "家具會造成 obstacle-aware attenuation",
            "動態響應採一階收斂近似",
            "控制推薦在 target zone 上評分與排序",
        ],
    )
    add_footer(slide, 5)

    # Slide 6
    slide = new_slide(prs)
    add_title(slide, "感測器校正與影響學習")
    add_picture(slide, ARCHITECTURE / "感測器校正與學習流程.svg", 0.7, 1.35, 6.3, 5.25)
    add_bullets(
        slide,
        7.2,
        1.55,
        5.0,
        5.0,
        [
            "先用 8 顆角落感測器比較預測值與觀測值",
            "用殘差校準 active device power scale",
            "再擬合 trilinear residual correction",
            "before/after observations 另外用來學非連網裝置影響係數",
        ],
        level0_size=17,
    )
    add_footer(slide, 6)

    # Slide 7
    slide = new_slide(prs)
    add_title(slide, "系統實作與介面")
    add_card(
        slide,
        0.7,
        1.4,
        3.8,
        4.9,
        "MCP / Gemma",
        [
            "本地 stdio MCP server",
            "提供 scenario, ranking, point sample, baseline, impacts, window tools",
            "Gemma 透過 bridge 做 tool calling",
        ],
    )
    add_card(
        slide,
        4.75,
        1.4,
        3.8,
        4.9,
        "Web Demo",
        [
            "可旋轉 3D 預覽",
            "時間軸、播放、point sample",
            "裝置與家具都可模組化設定",
            "支援 hybrid estimator toggle",
        ],
    )
    add_card(
        slide,
        8.8,
        1.4,
        3.8,
        4.9,
        "輸入模式",
        [
            "標準情境 8 組",
            "窗戶矩陣 48 組",
            "窗戶 direct input",
            "自訂家具與自訂裝置",
        ],
    )
    add_footer(slide, 7)

    # Slide 8
    slide = new_slide(prs)
    add_title(slide, "驗證流程與比較原則")
    add_picture(slide, ARCHITECTURE / "驗證與實驗流程圖.svg", 0.8, 1.35, 5.8, 5.1)
    add_bullets(
        slide,
        6.95,
        1.5,
        5.25,
        5.2,
        [
            "synthetic full-field：8 組標準情境、truth-adjusted sensors、IDW 與消融",
            "hybrid residual：no-Fourier 對照與 LOO cross-validation",
            f"window matrix：{window_summary.get('count', 0)} 組外部邊界條件敏感度",
            f"真實 bedroom_01 快照：{bedroom_summary['snapshot_count']} 筆，檢查 pillow 位置",
            "public datasets：只作 task-aligned benchmark，不當 full-field 基準",
            "推薦排序：目前是 counterfactual simulation；有效性需介入實驗",
        ],
        level0_size=17,
    )
    add_footer(slide, 8)

    # Slide 9
    slide = new_slide(prs)
    add_title(slide, "主要結果：場重建與 baseline 比較")
    add_card(
        slide,
        0.7,
        1.45,
        3.7,
        2.0,
        "平均 Field MAE",
        [
            f"Temperature: {avg_mae['temperature']}",
            f"Humidity: {avg_mae['humidity']}",
            f"Illuminance: {avg_mae['illuminance']}",
        ],
    )
    add_card(
        slide,
        0.7,
        3.75,
        3.7,
        2.3,
        "標準情境",
        [
            f"驗證情境數：{len(validation_summary.get('scenarios', []))}",
            "比較項目：field / sensors / zones / IDW / recommendations",
        ],
    )
    add_picture(slide, FIGURES / "all_active_temperature_3d.svg", 4.7, 1.45, 3.8, 4.7)
    add_picture(slide, FIGURES / "window_only_illuminance_3d.svg", 8.7, 1.45, 3.8, 4.7)
    add_footer(slide, 9)

    # Slide 10
    slide = new_slide(prs)
    add_title(slide, "Hybrid Residual Neural Network 結果")
    default_hybrid = submission_summary["default_holdout_hybrid"]
    no_fourier = submission_summary["no_fourier_holdout_hybrid"]
    loo = submission_summary["leave_one_scenario_out"]
    add_card(
        slide,
        0.7,
        1.45,
        5.0,
        4.9,
        "Held-out + LOO",
        [
            f"Default samples: {default_hybrid['dataset']['train_samples']} / {default_hybrid['dataset']['test_samples']}",
            f"Default hybrid MAE: {default_hybrid['hybrid_test_field_mae']}",
            f"No-Fourier hybrid MAE: {no_fourier['hybrid_test_field_mae']}",
            f"LOO avg hybrid MAE: {loo['average_hybrid_field_mae']}",
            f"LOO reduction: T {loo['average_field_mae_reduction_percent']['temperature']:.2f}%, H {loo['average_field_mae_reduction_percent']['humidity']:.2f}%, L {loo['average_field_mae_reduction_percent']['illuminance']:.2f}%",
        ],
    )
    add_picture(slide, FIGURES / "submission" / "field_mae_comparison.png", 6.0, 1.35, 6.2, 3.1)
    add_bullets(
        slide,
        6.1,
        4.65,
        5.9,
        1.5,
        [
            "hybrid residual 是第二層修正器，不取代主模型",
            "LOO 結果證明標準情境 family 內殘差可學習，不代表任意房間泛化",
            "另以 bedroom_01 真實快照檢查 sparse calibration 對 pillow 點的改善",
        ],
        level0_size=15,
    )
    add_footer(slide, 10)

    # Slide 11
    slide = new_slide(prs)
    add_title(slide, "研究貢獻與資料策略")
    add_bullets(
        slide,
        0.9,
        1.55,
        11.4,
        5.3,
        [
            "提出以單房間、8 顆角落感測器為前提的三因子空間數位孿生原型",
            "以 bulk + local field、power calibration 與 trilinear correction 建立可解釋估測流程",
            "以 least-squares 學習非連網裝置影響，並用 hybrid residual 做第二層修正",
            "明確拆分 synthetic full-field、real sparse calibration、public task-aligned 與 intervention validation",
            "完整 3D 場比較以 canonical synthetic benchmark 為主",
            f"真實臥室快照校正後 pillow MAE: {bedroom_aggregate['estimated_pillow_mae']}",
            "公開資料集則採 task-aligned benchmark：CU-BEMS / SML2010 / ASHRAE 各比相容子任務",
        ],
        level0_size=18,
    )
    add_footer(slide, 11)

    # Slide 12
    slide = new_slide(prs)
    add_title(slide, "結論與未來工作")
    add_card(
        slide,
        0.8,
        1.6,
        5.7,
        4.8,
        "結論",
        [
            "有限角落感測器下仍可用分層式模型重建單房間三因子分布",
            "非連網裝置可透過環境變化進行影響學習與校正",
            "bedroom_01 7 天快照顯示校正後可改善未參與 fitting 的 pillow 點",
            "各資料來源支援的 claim boundary 已拆開說明",
            "模型已能輸出區域估計、反事實推薦排序與 AI 可查詢工具",
        ],
    )
    add_card(
        slide,
        6.8,
        1.6,
        5.7,
        4.8,
        "未來工作",
        [
            "擴大 ESP32 長期真實資料",
            "擴充 CO2 / PM2.5 等因子",
            "改進 multi-zone / partition 模型",
            "補足 dense real-room ground truth",
            "執行推薦動作 before/after 介入驗證",
            "研究遠端 MCP 與閉環控制",
        ],
    )
    add_footer(slide, 12)
    return prs


def build_presentation_30min() -> Presentation:
    prs = init_presentation()
    validation_summary = read_json(DATA / "validation_summary.json")
    submission_summary = read_json(DATA / "submission_readiness_summary.json")
    window_summary = read_json(DATA / "window_matrix_summary.json")
    bedroom_summary = read_json(DATA / "bedroom_01_weekly" / "weekly_simulation_summary.json")
    avg_mae = average_field_mae(validation_summary)
    scenarios = scenario_map(validation_summary)
    bedroom_aggregate = bedroom_summary["aggregate"]

    # 1 cover
    slide = new_slide(prs)
    add_title(
        slide,
        "單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型",
        "30 分鐘口試版簡報",
    )
    add_bullets(
        slide,
        0.9,
        1.7,
        5.4,
        4.0,
        [
            "研究生：林昀佑",
            "指導教授：易昶霈教授、沈慧宇副教授",
            "國立彰化師範大學資訊工程學系碩士班",
            "主題：單房間三因子數位孿生、非連網裝置影響學習、工具化服務介面",
        ],
        level0_size=20,
    )
    add_picture(slide, ARCHITECTURE / "整體分層架構.svg", 6.7, 1.5, 5.6, 4.8)
    add_footer(slide, 1)

    # 2 roadmap
    slide = new_slide(prs)
    add_title(slide, "報告流程")
    add_bullets(
        slide,
        1.0,
        1.55,
        11.0,
        5.4,
        [
            "1. 問題背景與研究動機",
            "2. 文獻定位與研究缺口",
            "3. 系統架構與數學模型",
            "4. 感測器校正、影響學習與 hybrid residual",
            "5. 實作系統、驗證設計與實驗結果",
            "6. 結論、限制與未來工作",
        ],
        level0_size=21,
    )
    add_footer(slide, 2)

    # 3 background
    slide = new_slide(prs)
    add_title(slide, "研究背景與問題")
    add_card(
        slide,
        0.7,
        1.45,
        3.8,
        4.8,
        "房間場景",
        [
            "真實房間通常只有少量感測器",
            "但使用者關心的是整個空間的舒適度",
            "不是單一點位數值",
        ],
    )
    add_card(
        slide,
        4.75,
        1.45,
        3.8,
        4.8,
        "非連網裝置",
        [
            "冷氣、窗戶、照明常無 API",
            "狀態不可直接讀取",
            "卻持續改變溫度、濕度、照度",
        ],
    )
    add_card(
        slide,
        8.8,
        1.45,
        3.8,
        4.8,
        "核心需求",
        [
            "重建全室三因子分布",
            "學習裝置對環境的影響",
            "支援控制推薦與 AI 查詢",
        ],
    )
    add_footer(slide, 3)

    # 4 questions and contributions
    slide = new_slide(prs)
    add_title(slide, "研究問題與貢獻")
    add_card(
        slide,
        0.75,
        1.45,
        5.6,
        4.9,
        "研究問題",
        [
            "RQ1：8 顆角落感測器能否重建單房間三因子空間場？",
            "RQ2：能否從環境資料學習非連網裝置影響？",
            "RQ3：學習後能否改善控制推薦？",
            "RQ4：能否將模型封裝成 MCP 可查詢工具？",
        ],
    )
    add_card(
        slide,
        6.7,
        1.45,
        5.9,
        4.9,
        "主要貢獻",
        [
            "single-room three-factor spatial digital twin",
            "power calibration + trilinear residual correction",
            "non-networked appliance impact learning",
            "hybrid residual + Fourier denoising",
            "task-aligned public benchmark strategy",
            "MCP / Gemma / Web 可互動原型",
        ],
    )
    add_footer(slide, 4)

    # 5 literature gap
    slide = new_slide(prs)
    add_title(slide, "文獻定位、研究缺口與比較原則")
    add_card(
        slide,
        0.7,
        1.45,
        3.8,
        5.0,
        "已有研究",
        [
            "房間尺度 IEQ 實驗",
            "有限感測器場重建",
            "hybrid thermal model",
            "建築 digital twin 平台",
        ],
    )
    add_card(
        slide,
        4.75,
        1.45,
        3.8,
        5.0,
        "常見不足",
        [
            "多只看熱環境或單雙因子",
            "少處理非連網裝置學習",
            "少將模型做成 AI 可查詢工具",
            "多半不是單房間低成本原型",
        ],
    )
    add_card(
        slide,
        8.8,
        1.45,
        3.8,
        5.0,
        "本研究定位",
        [
            "single-room",
            "limited corner sensors",
            "temperature + humidity + illuminance",
            "control-oriented + MCP-accessible",
            "public datasets only for aligned subtasks",
        ],
    )
    add_footer(slide, 5)

    # 6 architecture
    slide = new_slide(prs)
    add_title(slide, "整體系統架構")
    add_picture(slide, ARCHITECTURE / "整體分層架構.svg", 0.8, 1.35, 6.2, 5.3)
    add_bullets(
        slide,
        7.15,
        1.5,
        5.0,
        5.2,
        [
            "入口區分為人機互動層與 AI 工具呼叫層",
            "所有請求經服務編排後進入環境數位孿生核心",
            "校正與影響學習層負責修正稀疏感測誤差",
            "輸出為空間場估測、區域估測、動作排序與 3D 視覺化",
        ],
        level0_size=17,
    )
    add_footer(slide, 6)

    # 7 execution flow
    slide = new_slide(prs)
    add_title(slide, "主要執行資料流")
    add_picture(slide, ARCHITECTURE / "主要執行資料流.svg", 0.8, 1.35, 5.9, 5.25)
    add_bullets(
        slide,
        6.95,
        1.45,
        5.25,
        5.3,
        [
            "scenario 或 direct input 先進入 service",
            "套用 indoor baseline、裝置、家具與時間設定",
            "再做場估測、感測器校正與 dashboard 輸出",
            "MCP 和 Web 都走同一條執行路徑",
        ],
        level0_size=17,
    )
    add_footer(slide, 7)

    # 8 room topology
    slide = new_slide(prs)
    add_title(slide, "房間拓樸、感測器與目標區域")
    add_picture(slide, ARCHITECTURE / "房間感測器與目標區域配置.svg", 0.8, 1.35, 6.0, 5.3)
    add_card(
        slide,
        7.05,
        1.45,
        5.15,
        4.9,
        "固定研究設定",
        [
            "房間：6 × 4 × 3 m",
            "感測器：floor/ceiling 四角，共 8 顆",
            "區域：window / center / door-side",
            "核心裝置：ac_main / window_main / light_main",
            "解析度：16 × 12 × 6",
        ],
    )
    add_footer(slide, 8)

    # 9 devices and furniture
    slide = new_slide(prs)
    add_title(slide, "模組化裝置與家具阻擋")
    add_picture(slide, ARCHITECTURE / "可模組化裝置與家具架構.svg", 0.8, 1.35, 5.9, 5.1)
    add_bullets(
        slide,
        6.95,
        1.45,
        5.25,
        5.25,
        [
            "冷氣、窗戶、燈都可視為模組化裝置",
            "家具是可開關、可移動的阻擋物件",
            "阻擋效果會依幾何位置自適應調整",
            "Web 端可新增 custom devices 與 custom furniture",
        ],
        level0_size=17,
    )
    add_footer(slide, 9)

    # 10 math model
    slide = new_slide(prs)
    add_title(slide, "數學模型：bulk + local field")
    add_card(
        slide,
        0.75,
        1.4,
        6.0,
        5.0,
        "核心形式",
        [
            "F_v = B_v^bulk + B_v^local + Σ I_j,v^local + C_v",
            "B_v^bulk：全室平均狀態",
            "B_v^local：背景分層與空間差異",
            "I_j,v^local：設備局部影響函數",
            "C_v：感測器殘差校正場",
        ],
    )
    add_card(
        slide,
        7.0,
        1.4,
        5.2,
        5.0,
        "設計理由",
        [
            "避免只有冷氣附近變冷、全室仍近乎不變的不合理情況",
            "早期純插值與 local-only 版本都失敗過",
            "比 CFD 輕量",
            "比純插值更可解釋",
            "適合控制導向與即時服務化",
        ],
    )
    add_footer(slide, 10)

    # 11 calibration and learning
    slide = new_slide(prs)
    add_title(slide, "感測器校正與裝置影響學習")
    add_picture(slide, ARCHITECTURE / "感測器校正與學習流程.svg", 0.7, 1.3, 6.2, 5.3)
    add_card(
        slide,
        7.1,
        1.45,
        5.0,
        5.0,
        "兩條核心流程",
        [
            "1. 角落觀測殘差 → power calibration → trilinear correction",
            "2. before/after 觀測差值 → least-squares impact learning",
            "目標是讓模型可校正，也可學習非連網裝置影響",
        ],
    )
    add_footer(slide, 11)

    # 12 implementation interfaces
    slide = new_slide(prs)
    add_title(slide, "系統實作與介面")
    add_card(
        slide,
        0.7,
        1.45,
        3.85,
        4.9,
        "MCP",
        [
            "本地 stdio server",
            "scenario / ranking / baseline / point sample / window tools",
            "可被 VS Code 或其他 MCP client 連接",
        ],
    )
    add_card(
        slide,
        4.75,
        1.45,
        3.85,
        4.9,
        "Gemma / Ollama",
        [
            "Gemma 透過 bridge 做 tool calling",
            "MCP 支援來自主機與 runtime",
            "不是宣稱模型原生支援 MCP",
        ],
    )
    add_card(
        slide,
        8.8,
        1.45,
        3.8,
        4.9,
        "Web Demo",
        [
            "可旋轉 3D 預覽",
            "時間軸與播放",
            "裝置/家具模組化調整",
            "hybrid estimator toggle",
        ],
    )
    add_footer(slide, 12)

    # 13 validation design
    slide = new_slide(prs)
    add_title(slide, "驗證設計")
    add_picture(slide, ARCHITECTURE / "驗證與實驗流程圖.svg", 0.75, 1.35, 6.0, 5.2)
    add_bullets(
        slide,
        7.0,
        1.45,
        5.2,
        5.3,
        [
            "標準情境共 8 組",
            f"窗戶矩陣共 {window_summary.get('count', 0)} 組",
            "比較 corrected estimate 與 IDW baseline",
            "證據層級拆分 synthetic full-field、real sparse calibration、public task-aligned",
            f"真實 bedroom_01 快照共 {bedroom_summary['snapshot_count']} 筆",
            "公開資料集僅作 task-aligned benchmark，不直接當 full-field 基準",
            "推薦排序為 counterfactual simulation；實際效果需 before/after intervention",
        ],
        level0_size=16,
    )
    add_footer(slide, 13)

    # 14 scenarios and time/window settings
    slide = new_slide(prs)
    add_title(slide, "情境設計與輸入模式")
    add_card(
        slide,
        0.7,
        1.45,
        3.8,
        4.9,
        "標準情境",
        [
            "idle",
            "ac_only / window_only / light_only",
            "ac_window / window_light / ac_light",
            "all_active",
        ],
    )
    add_card(
        slide,
        4.75,
        1.45,
        3.8,
        4.9,
        "窗戶模式",
        [
            "四季 × 天氣 × 時段",
            "matrix evaluation",
            "也支援 direct outdoor input",
            "可分析窗邊區與中心區差異",
        ],
    )
    add_card(
        slide,
        8.8,
        1.45,
        3.8,
        4.9,
        "時間軸",
        [
            "所有 scenario 都有 elapsed time",
            "近似一階動態收斂",
            "Web 端可播放到 quasi-steady state",
        ],
    )
    add_footer(slide, 14)

    # 15 quantitative results
    slide = new_slide(prs)
    add_title(slide, "主要量化結果")
    add_card(
        slide,
        0.7,
        1.4,
        3.6,
        2.0,
        "平均 Field MAE",
        [
            f"Temperature: {avg_mae['temperature']}",
            f"Humidity: {avg_mae['humidity']}",
            f"Illuminance: {avg_mae['illuminance']}",
        ],
    )
    add_card(
        slide,
        0.7,
        3.7,
        3.6,
        2.4,
        "IDW 比較",
        [
            "IDW 可做 baseline",
            "但缺設備位置與方向資訊",
            "照度與局部熱區重建效果明顯較差",
        ],
    )
    add_picture(slide, FIGURES / "submission" / "field_mae_comparison.png", 4.55, 1.25, 7.7, 3.25)
    add_card(
        slide,
        4.6,
        4.75,
        7.7,
        1.35,
        "範例推薦結果",
        [
            f"真實臥室 raw pillow MAE: {bedroom_aggregate['raw_pillow_mae']}",
            f"校正後 pillow MAE: {bedroom_aggregate['estimated_pillow_mae']}",
            "推薦動作以實測 penalty 下降作為後續驗證指標",
        ],
    )
    add_footer(slide, 15)

    # 16 qualitative visual results
    slide = new_slide(prs)
    add_title(slide, "3D 視覺化結果")
    add_picture(slide, FIGURES / "all_active_temperature_3d.svg", 0.65, 1.5, 4.0, 4.8)
    add_picture(slide, FIGURES / "window_only_illuminance_3d.svg", 4.68, 1.5, 4.0, 4.8)
    add_picture(slide, FIGURES / "ac_only_temperature_3d.svg", 8.7, 1.5, 4.0, 4.8)
    add_footer(slide, 16)

    # 17 hybrid result
    slide = new_slide(prs)
    add_title(slide, "Hybrid Residual Neural Network 結果")
    default_hybrid = submission_summary["default_holdout_hybrid"]
    no_fourier = submission_summary["no_fourier_holdout_hybrid"]
    loo = submission_summary["leave_one_scenario_out"]
    add_card(
        slide,
        0.75,
        1.45,
        5.2,
        4.9,
        "Robustness checks",
        [
            f"Default samples: {default_hybrid['dataset']['train_samples']} / {default_hybrid['dataset']['test_samples']}",
            f"Default MAE: {default_hybrid['hybrid_test_field_mae']}",
            f"No-Fourier MAE: {no_fourier['hybrid_test_field_mae']}",
            f"LOO avg MAE: {loo['average_hybrid_field_mae']}",
            f"LOO reduction: {loo['average_field_mae_reduction_percent']}",
        ],
    )
    add_picture(slide, FIGURES / "submission" / "field_mae_comparison.png", 6.15, 1.35, 6.1, 3.0)
    add_bullets(
        slide,
        6.25,
        4.55,
        5.8,
        1.7,
        [
            "no-Fourier 對照顯示照度改善不是頻域處理造成",
            "LOO 降低單一 held-out split 過度樂觀的風險",
            "LOO 結果仍限標準情境 family，不等同任意房間泛化",
            "真實臥室快照已驗證 calibration，推薦有效性仍需介入實驗",
        ],
        level0_size=15,
    )
    add_footer(slide, 17)

    # 18 conclusion and future
    slide = new_slide(prs)
    add_title(slide, "結論、限制與未來工作")
    add_card(
        slide,
        0.7,
        1.45,
        3.85,
        4.9,
        "結論",
        [
            "單房間三因子數位孿生原型已可運作",
            "可估場、可校正、可學習、可推薦",
            "bedroom_01 快照顯示校正後 pillow 點 MAE 明顯下降",
            "資料比較需依任務層級切分",
            "hybrid residual 泛化仍需更多房間與 dense ground truth",
            "MCP 與 Web 展示已完成",
        ],
    )
    add_card(
        slide,
        4.75,
        1.45,
        3.85,
        4.9,
        "限制",
        [
            "已有小型真實臥室快照，但仍缺長期 dense field",
            "LOO hybrid 目前只支持標準情境 family 內殘差可學習",
            "不是 CFD 等級模型",
            "公開資料集缺乏 full-field ground truth",
            "推薦動作尚未完成真實介入式因果驗證",
        ],
    )
    add_card(
        slide,
        8.8,
        1.45,
        3.8,
        4.9,
        "未來工作",
        [
            "擴大 ESP32 長期真實資料",
            "加入 CO2 / PM2.5",
            "發展 multi-zone / partition model",
            "把 CU-BEMS / SML2010 / ASHRAE 納入 task-aligned benchmark",
            "執行推薦動作 before/after 介入驗證",
            "朝閉環控制與遠端 MCP 延伸",
        ],
    )
    add_footer(slide, 18)
    return prs


def build_outline() -> str:
    slides = [
        ("封面", ["題目、姓名、雙指導教授、研究定位"]),
        ("研究問題與動機", ["非連網裝置無法直接回報狀態", "有限感測器下仍需估計全室環境", "早期純插值與 local-only 模型都不合理"]),
        ("系統架構", ["入口分成使用者互動層與 AI 工具呼叫層", "服務編排、主模型與 residual 修正的分工"]),
        ("房間拓樸、感測器與目標區域", ["8 顆角落感測器", "三個主要區域與三個核心裝置"]),
        ("數學模型", ["bulk + local field", "trilinear correction", "裝置與家具模組化"]),
        ("感測器校正與影響學習", ["power calibration", "least-squares impact learning"]),
        ("系統實作與介面", ["MCP tools", "Gemma bridge", "Web demo"]),
        ("驗證流程與比較原則", ["synthetic full-field、real sparse calibration、public task-aligned、intervention validation 分層", "IDW baseline 比較與 synthetic ablation", "no-Fourier 與 LOO cross-validation", "48 組窗戶矩陣", "bedroom_01 7 天真實快照", "推薦動作 before/after 介入驗證方法"]),
        ("主要結果", ["平均 field MAE", "IDW / Base / LOO Hybrid 誤差比較", "真實臥室 pillow MAE 比較", "推薦排序目前為 counterfactual simulation", "3D 視覺化案例"]),
        ("Hybrid Residual 結果", ["default held-out、no-Fourier、LOO MAE", "train/test sample count", "研究定位不是黑盒替代", "LOO 結果限標準情境 family"]),
        ("研究貢獻與資料策略", ["三因子、有限感測器、非連網裝置、服務化", "canonical synthetic benchmark + real-bedroom snapshots + task-aligned public datasets", "明確列出每種資料支援的 claim boundary"]),
        ("結論與未來工作", ["長期真實資料、dense real-room ground truth、更多因子、multi-zone、推薦動作介入驗證、閉環控制"]),
    ]
    lines = ["# 論文報告投影片大綱", ""]
    for index, (title, bullets) in enumerate(slides, start=1):
        lines.append(f"## Slide {index}: {title}")
        lines.extend([f"- {item}" for item in bullets])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_outline_30min() -> str:
    slides = [
        ("封面", ["題目、姓名、雙指導教授、30 分鐘口試版"]),
        ("報告流程", ["背景、文獻、方法、實作、驗證、結論"]),
        ("研究背景與問題", ["非連網裝置造成空間影響但無法直接讀取", "有限感測器仍需估全室環境"]),
        ("研究問題與貢獻", ["RQ1-RQ4、主要技術貢獻、task-aligned benchmark 策略"]),
        ("文獻定位、研究缺口與比較原則", ["IEQ 實驗、場重建、hybrid model、digital twin 平台之差異", "公開資料集只比較相容子任務"]),
        ("整體系統架構", ["人機互動層與 AI 工具呼叫層共用服務編排入口"]),
        ("主要執行資料流", ["scenario 到 dashboard / MCP response 的流程"]),
        ("房間拓樸、感測器與目標區域", ["8 顆角落感測器與三個區域"]),
        ("模組化裝置與家具阻擋", ["裝置模組化、家具自適應阻擋"]),
        ("數學模型", ["bulk + local field + correction", "早期純插值與 local-only 模型失敗後的調整"]),
        ("感測器校正與裝置影響學習", ["power calibration 與 least squares"]),
        ("系統實作與介面", ["MCP、Gemma/Ollama、Web Demo"]),
        ("驗證設計", ["truth-adjusted simulation、IDW、synthetic ablation、window matrix", "證據層級：synthetic full-field、real sparse calibration、public task-aligned、intervention validation", "bedroom_01 7 天真實快照與 pillow 位置比較", "推薦動作 before/after intervention protocol", "no-Fourier 與 LOO cross-validation", "public datasets 僅作 task-aligned benchmark"]),
        ("情境設計與輸入模式", ["8 組 scenario、48 組窗戶矩陣、direct input、timeline"]),
        ("主要量化結果", ["平均 MAE、IDW/Base/LOO Hybrid 誤差圖", "真實臥室 raw vs corrected pillow MAE", "推薦有效性以 actual comfort-penalty reduction 驗證"]),
        ("3D 視覺化結果", ["溫度與照度熱區案例"]),
        ("Hybrid Residual 結果", ["default held-out、no-Fourier、LOO robustness checks", "train/test sample count 與 synthetic benchmark 限制", "LOO 結果限標準情境 family", "真實快照作為 sparse calibration 驗證"]),
        ("結論、限制與未來工作", ["目前完成度、真實快照限制、hybrid 泛化限制、推薦動作尚需介入驗證、task-aligned benchmark 與後續方向"]),
    ]
    lines = ["# 論文報告投影片大綱（30 分鐘版）", ""]
    for index, (title, bullets) in enumerate(slides, start=1):
        lines.append(f"## Slide {index}: {title}")
        lines.extend([f"- {item}" for item in bullets])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    PAPERS.mkdir(parents=True, exist_ok=True)
    prs = build_presentation()
    prs.save(PRESENTATION_PATH)
    prs_long = build_presentation_30min()
    prs_long.save(LONG_PRESENTATION_PATH)
    OUTLINE_PATH.write_text(build_outline(), encoding="utf-8")
    LONG_OUTLINE_PATH.write_text(build_outline_30min(), encoding="utf-8")
    print(f"Wrote {PRESENTATION_PATH}")
    print(f"Wrote {LONG_PRESENTATION_PATH}")
    print(f"Wrote {OUTLINE_PATH}")
    print(f"Wrote {LONG_OUTLINE_PATH}")


if __name__ == "__main__":
    main()
