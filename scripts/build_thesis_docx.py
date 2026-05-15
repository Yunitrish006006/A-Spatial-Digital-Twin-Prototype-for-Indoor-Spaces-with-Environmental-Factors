# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Iterable, List
import shutil
import struct
import subprocess
import tempfile
from xml.sax.saxutils import escape
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUTS = ROOT / "outputs"
PAPERS = DOCS / "papers" / "thesis"
ARCHITECTURE = OUTPUTS / "figures" / "architecture"
PAPER_ASSETS = PAPERS / "assets"


Block = Dict[str, object]


def ensure_image_asset(block: Block) -> Path:
    source = ROOT / str(block["path"])
    if not source.exists():
        raise FileNotFoundError(f"Missing figure source: {source}")
    PAPER_ASSETS.mkdir(parents=True, exist_ok=True)
    asset_name = str(block.get("asset_name", source.stem))
    if source.suffix.lower() == ".svg":
        target = PAPER_ASSETS / f"{asset_name}.png"
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            return target
        qlmanage = shutil.which("qlmanage")
        if qlmanage is None:
            raise SystemExit("qlmanage not found. It is required to convert SVG figures into PNG assets.")
        with tempfile.TemporaryDirectory(prefix="thesis_ql_", dir="/private/tmp") as temp_name:
            temp_dir = Path(temp_name)
            render_source = source
            svg_text = source.read_text(encoding="utf-8", errors="ignore")
            if 'width="1600" height="900" viewBox="0 0 1600 900"' in svg_text:
                padded_source = temp_dir / source.name
                padded_source.write_text(
                    svg_text.replace('width="1600" height="900"', 'width="1600" height="1600"', 1),
                    encoding="utf-8",
                )
                render_source = padded_source
            completed = subprocess.run(
                [qlmanage, "-t", "-s", "1800", "-o", str(temp_dir), str(render_source)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise SystemExit(completed.stderr or completed.stdout or "Failed to render figure asset via qlmanage.")
            rendered = temp_dir / f"{render_source.name}.png"
            if not rendered.exists():
                png_candidates = sorted(temp_dir.glob("*.png"))
                if len(png_candidates) == 1:
                    rendered = png_candidates[0]
                else:
                    raise SystemExit(f"qlmanage did not produce expected PNG asset for {source}")
            shutil.move(str(rendered), str(target))
        crop_png_to_content(target)
        return target
    target = PAPER_ASSETS / f"{asset_name}{source.suffix.lower()}"
    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        shutil.copy2(source, target)
    return target


def crop_png_to_content(path: Path, padding: int = 24) -> None:
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
        bbox = ImageChops.difference(rgb, background).getbbox()
        if not bbox:
            return
        left = max(0, bbox[0] - padding)
        top = max(0, bbox[1] - padding)
        right = min(rgb.width, bbox[2] + padding)
        bottom = min(rgb.height, bbox[3] + padding)
        if (left, top, right, bottom) == (0, 0, rgb.width, rgb.height):
            return
        rgb.crop((left, top, right, bottom)).save(path)


def png_dimensions(path: Path) -> List[int]:
    with open(path, "rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unsupported PNG file: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return [int(width), int(height)]


def build_blocks() -> List[Block]:
    return [
        title("國立彰化師範大學\n資訊工程學系碩士班\n碩士論文完整版", 0),
        title("單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型", 1),
        paragraph("A Sparse-Sensing Spatial Digital Twin for Learning Environmental Impacts of Non-Networked Appliances in a Single Room", align="center"),
        paragraph("研究生：林昀佑", align="center"),
        paragraph("指導教授：易昶霈 教授、沈慧宇 副教授", align="center"),
        paragraph("版本：中文完整稿 v1.0", align="center"),
        paragraph("日期：2026 年 5 月 4 日", align="center"),
        page_break(),
        heading("審定書", 1),
        paragraph("國立彰化師範大學資訊工程學系碩士班"),
        paragraph("碩士論文審定書"),
        paragraph("單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型"),
        paragraph("研究生：林昀佑"),
        paragraph("本論文業經審查及口試合格，特此證明。"),
        paragraph("論文考試委員會召集人："),
        paragraph("委員："),
        paragraph("委員："),
        paragraph("指導教授：易昶霈 博士"),
        paragraph("共同指導教授：沈慧宇 副教授"),
        paragraph("所長："),
        paragraph("中華民國 115 年 月"),
        page_break(),
        heading("誌謝", 1),
        paragraph("本研究能夠完成，首先感謝指導教授易昶霈教授與沈慧宇副教授在研究方向、方法與寫作上的指導與支持，以及各位口試委員的指正與建議。感謝求學過程中幫助我的各位師長所提供的學習環境，也感謝家人的支持與包容。"),
        paragraph("林昀佑 謹誌於"),
        paragraph("國立彰化師範大學資訊工程學系（所）"),
        paragraph("中華民國 115 年 5 月"),
        page_break(),
        heading("摘要", 1),
        paragraph(
            "智慧建築與智慧居家系統需要掌握室內環境狀態，才能支援舒適度評估、能源管理與設備控制。然而，一般房間中的冷氣、窗戶與照明常不具備連網遙測能力，室內也通常只能布建少量感測器，難以直接取得完整空間分布。本研究以單一矩形房間為場域，提出以 8 顆角落感測器支援之三因子空間數位孿生原型，針對 temperature、humidity 與 illuminance 建立變數專屬的 reduced-order nominal model：溫度以熱交換與熱源項描述，濕度以水氣交換與除濕項描述，照度以燈具光束幾何、窗戶日照 envelope、遮蔽與 single-bounce diffuse reflection 描述。系統再結合冷氣、窗戶與照明的參數化影響函數、active-device power calibration 與 trilinear residual correction，從稀疏觀測修正空間場估計；並以 hybrid residual neural network 學習主模型剩餘誤差，而不以純黑盒模型取代可解釋結構。"
        ),
        paragraph(
            "評估採分層證據設計，分別檢查受控完整場重建、公開資料相容子任務與真實稀疏校正。8 組標準情境中，base model 的平均 field MAE 為溫度 0.0474、濕度 0.1765、照度 2.0269，低於 IDW baseline 的 0.1723、0.4633、54.9052；hybrid residual leave-one-scenario-out 平均進一步降至 0.0017、0.0059、0.1407。7 天 real-bedroom snapshot 中，pillow 參考點校正後 MAE 由 0.8967°C、4.1286% 與 309.0142 lux 降至 0.1676°C、0.3939% 與 16.6450 lux。公開資料集 SML2010 與 CU-BEMS 僅作 task-aligned benchmark，不宣稱 full 3D dense-field 驗證；SML2010 的 24 個任務中有 12 項取得最低 MAE，CU-BEMS 的 12 個任務中有 9 項優於 linear regression 但 0 項優於 persistence。結果顯示，稀疏角落感測在搭配變數專屬物理結構、校正與殘差學習時，可支援可解釋且可訓練的室內環境場估計；推薦動作目前仍屬模型反事實排序，實際因果改善需後續 before/after 介入驗證。"
        ),
        paragraph("關鍵字：空間數位孿生、稀疏感測、非連網家電、室內環境建模、溫度、濕度、照度、角落感測器。"),
        page_break(),
        heading("Abstract", 1),
        paragraph(
            "Smart building and smart home systems require indoor environmental awareness for comfort assessment, energy management, and device control. In ordinary rooms, however, air conditioners, manual windows, and lights often expose no telemetry, while only a small number of sensors can be installed. This thesis proposes a sparse-sensing spatial digital twin for a single rectangular room using eight corner sensors. The model uses variable-specific reduced-order nominal structures: temperature is represented by thermal exchange and heat-source terms, humidity by moisture exchange and dehumidification terms, and illuminance by lamp beam geometry, window daylight envelopes, obstruction, and a lightweight single-bounce diffuse reflection approximation. Parameterized appliance influence functions, active-device power calibration, and trilinear residual correction are used to estimate the room field from sparse observations, and a hybrid residual neural network learns remaining systematic error without replacing the interpretable base model."
        ),
        paragraph(
            "The evaluation separates controlled full-field reconstruction, public task-aligned benchmarks, and real sparse-calibration checks. Across eight canonical scenarios, the base model achieves average field MAE of 0.0474/0.1765/2.0269 for temperature, humidity, and illuminance, compared with 0.1723/0.4633/54.9052 for IDW. Leave-one-scenario-out hybrid residual correction further reduces MAE to 0.0017/0.0059/0.1407. In a seven-day real-bedroom snapshot, pillow-point calibration error is reduced from 0.8967°C, 4.1286%, and 309.0142 lux to 0.1676°C, 0.3939%, and 16.6450 lux. SML2010 and CU-BEMS are used only as compatible task-aligned external benchmarks rather than dense 3-D spatial ground truth: the mapped model obtains the lowest MAE in 12 of 24 SML2010 tasks, and outperforms linear regression in 9 of 12 CU-BEMS tasks but never outperforms persistence on CU-BEMS. These results show that sparse corner sensing can support an interpretable and trainable indoor environmental field estimator when physical structure, calibration, and residual learning are assigned complementary roles. Action recommendations remain model-based counterfactual rankings and require future before/after intervention validation for causal claims."
        ),
        paragraph("Keywords: spatial digital twin, sparse sensing, non-networked appliances, indoor environment modeling, temperature, humidity, illuminance, corner sensors."),
        page_break(),
        heading("目錄", 1),
        paragraph("摘要……I"),
        paragraph("Abstract……II"),
        paragraph("誌謝……III"),
        paragraph("目錄……IV"),
        paragraph("表目錄……V"),
        paragraph("圖目錄……VI"),
        paragraph("第一章 緒論…… 1"),
        paragraph("  1.1 研究背景…… 1"),
        paragraph("  1.2 研究動機…… 1"),
        paragraph("  1.3 研究問題…… 2"),
        paragraph("  1.4 研究範圍與限制…… 2"),
        paragraph("  1.5 預期貢獻…… 2"),
        paragraph("第二章 文獻探討…… 3"),
        paragraph("  2.1 室內環境建模…… 3"),
        paragraph("  2.2 空間插值與場估計…… 3"),
        paragraph("  2.3 數位孿生與智慧建築…… 3"),
        paragraph("  2.4 房間尺度室內因子實驗研究…… 4"),
        paragraph("  2.5 非連網裝置影響學習…… 4"),
        paragraph("  2.6 MCP 與 AI Agent Tool Interface…… 5"),
        paragraph("  2.7 與相似研究之差異定位…… 5"),
        paragraph("  2.8 公開資料與訓練資料適用性…… 6"),
        paragraph("第三章 系統架構與數學模型…… 7"),
        paragraph("  3.1 系統架構…… 7"),
        paragraph("  3.2 房間、區域與感測器設定…… 7"),
        paragraph("  3.3 三因子場模型…… 8"),
        paragraph("    3.3.1 共用符號與 Indoor Baseline…… 8"),
        paragraph("    3.3.2 溫度場模型…… 8"),
        paragraph("    3.3.3 濕度場模型…… 8"),
        paragraph("    3.3.4 照度場模型…… 9"),
        paragraph("  3.4 設備影響函數…… 8"),
        paragraph("  3.5 感測器校正模型…… 9"),
        paragraph("    3.5.1 8 點場推估的可證明範圍…… 9"),
        paragraph("  3.6 非連網裝置影響學習…… 9"),
        paragraph("  3.7 訓練資料組裝流程…… 9"),
        paragraph("    3.7.1 學習與訓練資料流…… 10"),
        paragraph("    3.7.2 訓練完成後的推論與推薦資料流…… 10"),
        paragraph("  3.8 Hybrid Residual Neural Network 延伸…… 10"),
        paragraph("  3.9 控制動作排序…… 10"),
        paragraph("  3.10 方法選擇理由與限制…… 10"),
        paragraph("第四章 系統實作與服務介面…… 11"),
        paragraph("  4.1 Python 原型…… 11"),
        paragraph("  4.2 MCP Tools…… 11"),
        paragraph("  4.3 Gemma/Ollama Bridge…… 12"),
        paragraph("  4.4 Web Demo 與展示輔助介面…… 12"),
        paragraph("第五章 模擬案例與結果分析…… 13"),
        paragraph("  5.1 標準情境設定…… 13"),
        paragraph("  5.2 【實驗 E1】標準情境場重建誤差…… 13"),
        paragraph("  5.3 【實驗 E2】IDW Baseline 比較…… 14"),
        paragraph("  5.4 【實驗 E3】消融分析與可重現性補強…… 14"),
        paragraph("  5.5 【實驗 E4】非連網裝置影響學習…… 14"),
        paragraph("  5.6 【實驗 E5】窗戶時段、天氣、季節矩陣與直接輸入…… 14"),
        paragraph("  5.7 【實驗 E6】Hybrid Residual Neural Network 結果…… 15"),
        paragraph("  5.8 【實驗 E7】真實臥室快照驗證與【驗證方案 E8】推薦動作驗證方法…… 16"),
        paragraph("  5.9 【實驗 E9】公開資料集執行流程與 Task-Aligned Benchmark 結果…… 17"),
        paragraph("  5.10 研究過程與實作挑戰…… 19"),
        paragraph("  5.11 展示 D1：可旋轉 3D 展示（非量化實驗）…… 19"),
        paragraph("第六章 結論與未來工作…… 19"),
        paragraph("  6.1 結論…… 19"),
        paragraph("  6.2 研究限制…… 19"),
        paragraph("  6.3 未來工作…… 19"),
        paragraph("參考文獻…… 20"),
        paragraph("附錄 A 原型執行方式…… 22"),
        paragraph("附錄 B Web Demo 操作與公開比較展示…… 22"),
        paragraph("附錄 C 名詞解釋…… 23"),
        page_break(),
        heading("表目錄", 1),
        paragraph("表 2-1 相似研究差異比較…… 5"),
        paragraph("表 2-2 公開資料集概覽與適用性…… 6"),
        paragraph("表 2-3 Task-aligned benchmark 設計…… 6"),
        paragraph("表 3-1 房間與感測器設定…… 7"),
        paragraph("表 3-2 訓練資料表格說明…… 9"),
        paragraph("表 4-1 核心模組一覽…… 11"),
        paragraph("表 4-2 learn_impacts 事件記錄欄位…… 11"),
        paragraph("表 4-3 initialize_environment 可設定內容…… 11"),
        paragraph("表 4-4 Web demo 展示輔助區塊…… 12"),
        paragraph("表 5-1 標準情境結果摘要…… 13"),
        paragraph("表 5-2 IDW 與本研究 field MAE 比較…… 14"),
        paragraph("表 5-3 消融實驗平均 field MAE…… 14"),
        paragraph("表 5-4 窗戶矩陣情境節選…… 15"),
        paragraph("表 5-5 Hybrid residual robustness checks…… 15"),
        paragraph("表 5-6 真實臥室快照 MAE 與分時舒適度…… 16"),
        paragraph("表 5-7 推薦動作介入驗證指標…… 17"),
        paragraph("表 5-8 公開資料集比較執行流程與 claim boundary…… 17"),
        paragraph("表 5-9 公開資料集任務代號與比較目的…… 18"),
        paragraph("表 5-10 SML2010 任務族群優劣勢拆解…… 18"),
        paragraph("表 5-11 CU-BEMS 任務族群優劣勢拆解…… 18"),
        page_break(),
        heading("圖目錄", 1),
        paragraph("圖 3-1 系統整體抽象樹狀架構…… 7"),
        paragraph("圖 3-2 主要執行資料流…… 7"),
        paragraph("圖 3-3 房間感測器與目標區域配置…… 8"),
        paragraph("圖 3-4 感測器校正與影響學習流程…… 9"),
        paragraph("圖 3-5 模型學習、推論與推薦資料流…… 10"),
        paragraph("圖 5-1 驗證與實驗流程…… 13"),
        paragraph("圖 5-2 三裝置同時作用溫度場 3D 點雲（all_active）…… 13"),
        paragraph("圖 5-3 僅冷氣作用溫度場 3D 點雲（ac_only）…… 14"),
        paragraph("圖 5-4 僅燈具作用照度場 3D 點雲（light_only）…… 14"),
        paragraph("圖 5-5 IDW、Base 與 LOO Hybrid field MAE 比較…… 15"),
        paragraph("圖 5-6 SML2010 S1/S2/S3 任務族群拆解…… 18"),
        paragraph("圖 5-7 CU-BEMS C1/C2/C3 任務族群拆解…… 18"),
        paragraph("圖 5-8 三裝置全開溫度場 3D 點雲（5.11 節）…… 19"),
        paragraph("圖 5-9 僅開窗溫度場 3D 點雲（window_only）…… 19"),
        paragraph("圖 5-10 僅燈具照度場 3D 點雲（light_only，5.11 節）…… 19"),
        page_break(),
        raw_latex(r"\clearpage\pagenumbering{arabic}"),
        heading("第一章 緒論", 1),
        heading("1.1 研究背景", 2),
        paragraph(
            "智慧家庭與智慧建築系統逐漸被用於室內環境監控、能源管理與舒適度控制。這類系統通常需要知道空間中溫度、濕度與照度的分布，才能判斷使用者所在區域是否過熱、過暗或過於潮濕。然而，實際房間內不可能在每一個位置都布建感測器，因此系統往往只能取得少量離散點位資料。若僅依賴單點或少數點位量測，容易忽略同一空間中不同區域的環境差異。"
        ),
        paragraph(
            "另一方面，許多既有家電並不是智慧裝置。傳統冷氣、一般開關照明或手動窗戶可能無法連網，也無法主動回報開關狀態、出力或作用範圍。這些裝置雖然無法被直接讀取，卻會持續改變室內環境。若數位孿生模型只依賴智慧裝置 API，將無法完整描述一般房間中的環境變化。因此，本研究關注的核心問題是：如何透過有限感測器觀測資料，學習非連網裝置對空間環境造成的影響，並將此學習結果用於更準確的三因子控制推薦。"
        ),
        heading("1.2 研究動機", 2),
        paragraph(
            "在原型開發初期，本研究曾嘗試將問題簡化為角落感測器插值或純局部影響場疊加，但很快發現兩個問題。第一，若只靠插值，模型雖能平滑填補空間，卻無法表達冷氣出風方向、窗邊日照或燈具位置等設備語意；第二，若只做局部場疊加，則容易出現設備附近變化明顯、全室平均狀態卻不合理的結果。這些實作經驗直接促成後續的變數專屬 nominal model、感測器校正流程，以及只把神經網路放在 residual correction 層的設計。"
        ),
        bullets(
            [
                "只知道角落感測器數值時，仍需要估計房間中央、靠窗區與門側區的三因子狀態。",
                "裝置沒有連網時，仍希望從環境變化中推估它是否對空間造成影響。",
                "新增或啟用冷氣、窗戶、照明後，系統應能估計其對不同區域造成的變化。",
                "學習裝置影響後，模型應能在已指定 point/cluster sample 與三因子目標時，支援開冷氣、開窗或開燈等候選控制動作排序。",
                "將模型封裝為標準化工具介面後，AI client 或 agent 可查詢與使用數位孿生能力。",
            ]
        ),
        heading("1.3 研究問題", 2),
        bullets(
            [
                "RQ1：在只有 8 顆角落感測器的條件下，是否能建立單房間溫度、濕度與照度的空間估計模型？",
                "RQ2：在家電或環境裝置沒有連網狀態回報的情況下，是否能從環境感測資料學習其對空間不同區域的影響？",
                "RQ3：學習後的裝置影響模型，是否能在明確 point/cluster sample 與溫度、濕度、照度目標下，依三因子偏差輸出候選控制動作排序，例如選擇開冷氣、開窗或開燈，且推薦動作的實際可行性應如何透過介入式 before/after 實驗驗證？",
                "RQ4：將數位孿生模型封裝為標準化工具介面後，是否能讓 AI client 查詢、模擬與使用控制推薦能力？",
            ]
        ),
        heading("1.4 研究範圍與限制", 2),
        bullets(
            [
                "研究場域固定為單一矩形房間，不處理多房間或跨空間空氣交換。",
                "感測器配置固定為天花板四角與地面四角，共 8 顆角落節點。",
                "設備類型聚焦於冷氣、窗戶與照明。",
                "模型為簡化動態模型，不追求 CFD 等級高精度流場。",
                "濕度保留於模型中，但作為次核心變數處理。",
                "控制功能只做候選動作排序，不做自動閉環控制；推薦動作的真實因果效果需透過後續介入實驗驗證。",
                "MCP 部分定位為本地 stdio server 與 AI-agent-accessible interface，不宣稱提出新的 MCP protocol。",
            ]
        ),
        heading("1.5 預期貢獻", 2),
        bullets(
            [
                "提出一個以單房間、8 顆角落感測器為前提的三因子空間數位孿生原型，明確描述 temperature、humidity 與 illuminance 場。",
                "建立包含變數專屬 nominal model、active device power calibration、trilinear correction 與裝置影響學習的可解釋估測流程。",
                "建立訓練資料組裝與 hybrid residual correction 路線，使真實感測資料可用於參數校正、影響學習與殘差修正，而非直接取代主模型。",
                "提出可對接 MCP、Web demo 與公開資料集 task-aligned benchmark 的研究原型與評估框架，並明確區分 synthetic full-field、real sparse calibration、public task-aligned benchmark 與 intervention validation 各自支援的主張範圍。",
            ]
        ),
        page_break(),
        heading("第二章 文獻探討", 1),
        heading("2.1 室內環境建模", 2),
        paragraph(
            "室內環境建模的主要目的，在於描述空間中熱舒適、能源使用與設備控制之間的關係。高精度方法如 computational fluid dynamics（CFD）雖可細緻描述空氣流動、傳熱與邊界交換，但通常需要大量幾何細節、材料參數與邊界條件，計算成本亦相對較高。相較之下，reduced-order model、grey-box thermal model 與控制導向動態模型著重於以較少參數捕捉主要動態，並保留參數辨識與即時推估能力，因此更適合用於建築控制、預測與數位孿生原型 [1][2][3]。基於此，本研究不追求 CFD 等級的高解析流場，而採用偏向控制導向與可解釋性的簡化空間模型。"
        ),
        heading("2.2 空間插值與場估計", 2),
        paragraph(
            "在感測器數量有限的情況下，最直接的方法是使用空間插值估計未量測位置。本研究採用 inverse distance weighting（IDW）作為 baseline。IDW 的優點是實作簡單且不依賴設備先驗，但其估計完全由量測點距離決定，無法反映冷氣出風方向、窗戶位置、照明熱源或設備作用範圍等結構資訊。相較之下，zonal model、reduced-order model 與 hybrid spatial model 提供了介於 well-mixed room model 與 CFD 之間的折衷途徑，可在維持較低計算成本的同時保留主要空間差異 [4][5][6]。因此，本研究不是把同一個 bulk/local 物理假設套用到所有環境量，而是將主模型拆成變數專屬 nominal model：溫度採熱交換與熱源近似，濕度採水氣交換與除濕近似，照度採燈具光束幾何、窗戶日照 envelope、遮蔽與反射近似；三者再共用稀疏感測 residual correction 框架。"
        ),
        heading("2.3 數位孿生與智慧建築", 2),
        paragraph(
            "數位孿生通常被視為實體系統在數位空間中的動態對應模型，其核心價值在於將感測資料、系統狀態與分析模型整合為可更新、可查詢且可推估的數位映射。在智慧建築領域中，數位孿生常與 BIM、IoT 感測、設備監控與能源管理系統結合，用於營運最佳化與狀態預測。近年的建築數位孿生回顧指出，多數研究著重於平台架構、資料整合與建築尺度的決策支援，但對於少量感測器條件下之單房間空間場重建與設備影響推估，討論仍相對有限 [7]。因此，本研究的定位並非建構完整 BIM/BMS 平台，而是針對單房間、低成本感測器與非連網裝置場景提出一個可運作的簡化數位孿生原型。"
        ),
        heading("2.4 房間尺度室內因子實驗研究", 2),
        paragraph(
            "若將文獻範圍收斂到房間尺度的實驗研究，可以發現溫度、濕度與照度並不是彼此孤立的環境因子。Chinazzo 等人以 office-like test room 為實驗場域，控制不同室溫與日光照度條件，研究 visual perception 與 thermal perception 之間的交互作用，指出日照與室溫會共同影響受試者的感知結果 [18][19]。Lan 等人則在教室條件下同時調整熱環境與照明參數，分析其對學習表現與主觀感受的影響，顯示 thermal and visual environments 可在同一受控場域中被聯合操控與評估 [20]。這類研究雖不以數位孿生為主，但提供了重要前提：房間內三因子至少在實驗設計層級上具備共同量測與共同分析的必要性。"
        ),
        paragraph(
            "另一類與本研究更接近的工作，是冷氣、開窗或通風策略對房間環境的實驗或現地量測。Kuwahara 等人在大學實驗室中比較空調運轉與自然通風策略，量測溫度、相對濕度與 CO2 變化，用於評估室內環境與舒適 [21]。Zhou 等人則對綠建築辦公室進行長期 field study，追蹤 thermal environment、relative humidity、CO2 與 visual environment，並結合使用者滿意度調查 [22]。Wang 等人針對寒冷地區住宅建築的冬季室內環境品質進行實測，指出低能耗住宅中的室溫與相對濕度仍可能出現不理想分布 [23]。這些研究共同說明，房間尺度的 IEQ 實驗並不罕見，而且冷氣、通風與外氣條件確實會使房間內部環境產生可量測差異。"
        ),
        paragraph(
            "然而，現有房間尺度實驗研究多半聚焦於舒適評估、單一場域量測，或多因子對認知與滿意度的影響，較少進一步處理有限感測器下的空間場重建、非連網裝置影響學習，以及可被外部 AI 系統查詢的工具化服務。Geng 等人對綠建築辦公室進行大規模與長期 IEQ 比較，Lee 等人則分析研究機構中不同工作型態與 IEQ 的關係 [24][25]；這些研究證明房間內溫度、濕度、照度與舒適度之間具有實際研究基礎，但尚未形成單房間、三因子、8 顆角落感測器、設備影響學習與控制推薦整合於同一原型的做法。基於此，本研究並非宣稱房間室內因子實驗是全新問題，而是主張：本研究將既有 IEQ 實驗研究常見的環境因子量測，進一步推展為可估場、可校正、可學習與可服務化的單房間數位孿生方法。"
        ),
        heading("2.5 非連網裝置影響學習", 2),
        paragraph(
            "既有智慧家庭與智慧建築研究，常預設設備可由網路介面直接讀取或控制。然而在一般居住空間中，傳統冷氣、手動窗戶與一般照明往往不具備可直接讀取的連網能力。此時，若系統仍希望掌握設備對環境的作用，就必須從感測到的環境變化反推設備影響。近期研究顯示，有限感測器搭配 data assimilation、hybrid model 或感測配置分析，確實能對室內溫濕度場進行重建，並評估量測點配置對重建品質的影響 [5][8][9]。本研究延續此方向，將裝置啟用前後的感測器差異視為學習訊號，並利用裝置空間影響基底與最小平方法估計其對溫度、濕度與照度的影響係數，以支援後續的場估計與控制推薦。"
        ),
        heading("2.6 MCP 與 AI Agent Tool Interface", 2),
        paragraph(
            "Model Context Protocol（MCP）提供一種標準化工具介面，使外部模型或 AI client 能以一致方式呼叫系統能力。本研究將數位孿生原型封裝為本地 MCP server，但其角色不是執行論文驗證實驗，而是提供實際互動流程：先初始化 MCP session 的 runtime state，包含 base scenario、室內 baseline、外部邊界條件、註冊設備、家具/遮蔽物、預設時間與 estimator 選擇，再查詢指定座標於特定時間或準穩態下的三因子估計，並可建立 before/after 裝置影響學習紀錄、直接輸入窗戶外部資料，以及在指定座標 sample 與完整溫度、濕度、照度目標都存在時排序控制候選動作。需要強調的是，MCP 在本研究中的角色屬於系統整合與工具化封裝，用以驗證數位孿生模型可被外部 AI 系統操作，而非針對 MCP 通訊協定本身提出新方法。"
        ),
        heading("2.7 與相似研究之差異定位", 2),
        paragraph(
            "若從研究方法的相似性來看，本研究最接近的文獻不是一般性的 building digital twin 平台論文，而是有限感測器室內場重建、控制導向簡化熱模型，以及 hybrid thermal surrogate 這三類研究。Qian 等人以資料同化方法重建實際住宅房間中的溫濕度分布，重點在於以有限量測重建連續場並分析量測配置 [8]；Huljak 等人聚焦於空調房間中的 hybrid 溫度模型，強調以 physics-based 與 surrogate model 共同描述空調空間中的溫度分布 [5]；Megri 等人則以 DOMA 動態 zonal model 處理時間變化與熱舒適預測 [6]。這三類工作與本研究皆有明顯關聯，但關注點不同。"
        ),
        paragraph(
            "本研究的具體定位是：在不做 CFD、不追求完整 BIM 平台，也不假設家電可回報狀態的前提下，建立一個可由 8 顆角落感測器校正、可學習非連網裝置影響、並可透過 MCP 與 Web 互動使用的單房間三因子數位孿生原型。換言之，本研究刻意把問題收斂在「單房間、有限角落感測器、溫濕度照度三因子、非連網家電影響學習、控制推薦、可工具化服務」這個組合上。從目前檢視到的相似研究來看，尚未看到與本研究完全同構的公開論文。"
        ),
        table(
            ["研究", "相似處", "主要差異"],
            [
                ["Qian et al. (2025) [8]", "有限觀測下重建室內溫濕度分布", "未把照度、非連網家電影響學習與 MCP 工具化整合在同一系統"],
                ["Huljak et al. (2025) [5]", "使用 hybrid 溫度模型處理空調房間", "主變數偏溫度，且依賴較強的建物邊界條件與物理模擬流程"],
                ["Megri et al. (2022) [6]", "強調動態 zonal / transient prediction", "目標偏熱舒適分析，不處理照度與非連網裝置學習"],
                ["Chen & Wen (2007) [9]", "討論感測器配置與 zonal model", "重點在感測器設計，不是建立可互動的單房間數位孿生原型"],
                ["Cespedes-Cubides & Jradi (2024) [7]", "界定 building digital twin 的整體脈絡", "屬綜述，不提供本研究這種單房間三因子可執行原型"],
            ],
        ),
        heading("2.8 公開資料與訓練資料適用性", 2),
        paragraph(
            "若從資料角度來看，公開資料集確實可作為本研究的輔助比對來源，但沒有任何一套資料能直接等價取代本研究的標準情境。原因在於，本研究同時要求單房間空間拓樸、8 顆角落感測器前提、三因子場估計、冷氣/窗戶/照明的裝置狀態，以及可移動家具阻擋。現有公開資料大多只滿足其中一部分。"
        ),
        table(
            ["資料集", "可用欄位", "適合用途", "限制"],
            [
                ["CU-BEMS [12]", "溫度、濕度、照度、AC/lighting power、zone-level series", "可用於驗證裝置狀態與環境量測的時間關聯", "多區商辦資料，不是單房間 8 角落感測器拓樸"],
                ["Appliances Energy Prediction [13]", "多房間溫溼度、室外氣象、燈光用電", "可用於室內外條件與用電關聯分析", "缺空間幾何與單房間場分布標記"],
                ["SML2010 [14]", "兩處室內溫度/濕度/照度、日照與室外條件", "可用於窗戶日照與室內響應的時序比對", "量測點有限，且非完整單房間空間場"],
                ["Occupancy Detection [15]", "溫度、濕度、照度、CO2", "可用於感測器前處理與環境變化偵測", "不含裝置資訊與空間拓樸"],
                ["Denmark IEQ dataset [16]", "房間層級 operative temperature、RH、CO2、occupancy", "可用於真實住宅 IEQ 波動比對", "缺照度與設備狀態"],
                ["ASHRAE Global Thermal Comfort Database II [17]", "大規模熱舒適與環境量測", "可用於舒適目標與控制評分合理性參考", "不是空間場重建資料，也不對應單房間幾何"],
            ],
        ),
        paragraph(
            "因此，本研究目前採取的資料策略是：以可控制的模擬情境作為主要訓練與驗證來源，以公開資料集作為外部合理性檢查與未來真實資料接軌的準備。具體而言，若要替本研究的 hybrid residual neural network 增加真實資料，現階段最有價值的是 CU-BEMS、SML2010 與住宅 IEQ 類資料；若要補強舒適度控制目標的依據，則 ASHRAE Global Thermal Comfort Database II 比較適合作為外部參考。"
        ),
        paragraph(
            "具體而言，本研究可採兩層 benchmark 設計。第一層是 canonical synthetic benchmark，直接使用本研究的 8 組標準情境與 48 組窗戶矩陣，讓主模型、IDW baseline、移除設備先驗的純資料驅動模型，以及 hybrid residual correction 在完全相同的輸入、感測器配置與 ground truth 下比較 field MAE、zone MAE、sensor MAE 與推薦改善分數。第二層是 public task-aligned benchmark，亦即把公開資料集拆成與本研究相容的子任務：CU-BEMS 可用於比較 AC/lighting 事件前後的 zone-level temperature、humidity、illuminance 響應；SML2010 可用於比較窗戶/日照相關的溫濕度照度時序響應；Denmark IEQ 與 ASHRAE Global Thermal Comfort Database II 則適合比較舒適度目標函數、偏差分數或分類準確率。"
        ),
        paragraph(
            "除上述兩層 benchmark 外，推薦動作本身仍需要第三層介入式驗證。此層不再只比較模型估測誤差，而是要求研究者實際執行系統排序第一的動作，並量測介入前後目標位置或目標區域的 comfort penalty 是否下降。換言之，場估計驗證回答「模型是否看得準」，介入驗證則回答「模型建議的動作是否真的讓房間更接近舒適目標」。"
        ),
        table(
            ["benchmark 層級", "資料來源", "比較任務", "本研究模型模式", "建議指標"],
            [
                ["canonical synthetic", "8 組標準情境", "完整場重建、裝置影響學習、推薦排序", "full spatial mode", "field MAE、zone MAE、sensor MAE、improvement score"],
                ["canonical synthetic", "48 組窗戶矩陣", "外部邊界條件敏感度分析", "full spatial window mode", "field MAE、zone deviation、趨勢一致性"],
                ["public task-aligned", "CU-BEMS", "AC 與照明事件後的區域響應", "single-zone dataset-compatible mode", "MAE、RMSE、delta MAE、correlation"],
                ["public task-aligned", "SML2010", "兩點日照與外氣條件響應", "two-point dataset-compatible mode", "MAE、RMSE、delta MAE"],
                ["public task-aligned", "Denmark IEQ / ASHRAE", "舒適度評分與控制目標合理性", "comfort-only mode", "score error、accuracy、F1、AUROC"],
            ],
        ),
        page_break(),
        heading("第三章 系統架構與數學模型", 1),
        heading("3.1 系統架構", 2),
        paragraph(
            "本研究系統由五個主要模組組成：房間與設備設定、三因子影響場模型、角落感測器校正、非連網裝置影響學習、以及控制動作排序與 MCP 工具介面。為了避免把互動入口誤認為模型本體，圖 3-1 先以 top-down 樹狀圖整理系統責任邊界：情境與觀測層提供房間、感測器、外部邊界與時間狀態；估測與學習層負責三因子場模型、校正與殘差學習；服務與決策層則把同一套 estimator path 暴露給腳本、Web demo 與 MCP/Gemma bridge。整體流程為：輸入房間幾何、設備位置與外部環境條件後，模型先建立背景場，再加入設備影響函數，接著使用 8 顆角落感測器觀測值校準 active device power scale 並建立 trilinear 校正場，最後輸出任意座標或目標區域的三因子估計；只有在已有 point/cluster sample 與完整三因子目標時，才進一步輸出候選控制動作排序。"
        ),
        image(
            "outputs/figures/architecture/整體分層架構.svg",
            "圖 3-1 系統整體抽象樹狀架構。此圖以 top-down tree 呈現情境與觀測、估測與學習、服務與決策三個責任域，並標示 MCP/Gemma bridge 屬於工具介面層而非主模型核心。",
            asset_name="fig_3_1_overall_architecture",
        ),
        image(
            "outputs/figures/architecture/主要執行資料流.svg",
            "圖 3-2 主要執行資料流。此圖對應一次 runtime request 如何從輸入設定、場估計、校正，到 dashboard 或 MCP 輸出。",
            width_inches=6.5,
            asset_name="fig_3_2_execution_flow",
        ),
        heading("3.2 房間、區域與感測器設定", 2),
        paragraph(
            "標準房間尺寸設定為寬 6.0 m、長 4.0 m、高 3.0 m。感測器固定於地面四角與天花板四角，共 8 顆節點。每個節點皆假設可量測 temperature、humidity 與 illuminance。區域劃分包含 window_zone、center_zone 與 door_side_zone，用於比較不同空間區域受到設備影響的差異。"
        ),
        table(
            ["項目", "設定"],
            [
                ["房間尺寸", "6.0 m × 4.0 m × 3.0 m"],
                ["感測器數量", "8 顆角落節點"],
                ["採樣網格", "16 × 12 × 6"],
                ["三個環境因素", "Temperature, Humidity, Illuminance"],
                ["主要區域", "window_zone, center_zone, door_side_zone"],
                ["設備類型", "ac_main, window_main, light_main"],
            ],
        ),
        image(
            "outputs/figures/architecture/房間感測器與目標區域配置.svg",
            "圖 3-3 房間感測器與目標區域配置。8 顆角落感測器、3 個主要區域與 3 個核心裝置共同構成單房間數位孿生的標準拓樸。",
            width_inches=6.5,
            asset_name="fig_3_3_room_topology",
        ),
        heading("3.3 三因子場模型", 2),
        paragraph("本研究將室內狀態定義為三個空間與時間函數："),
        math(r"T(\mathbf{p},t),\quad H(\mathbf{p},t),\quad L(\mathbf{p},t)"),
        paragraph(
            "為避免把不同物理性質的環境量硬套到同一個公式，本研究將估測流程拆成兩層。第一層是依變數而異的 nominal model $N_v(\\mathbf{p},t)$，負責描述該變數的主要物理趨勢；第二層是由 8 顆角落感測器提供的 residual correction $C_v(\\mathbf{p},t)$，負責吸收低階空間偏差。因此任一環境因素 $v\\in\\{T,H,L\\}$ 的最終估計值皆寫成："
        ),
        math(r"\hat{F}_v(\mathbf{p},t)=N_v(\mathbf{p},t)+C_v(\mathbf{p},t)"),
        table(
            ["符號", "詳細意義", "單位或備註"],
            [
                ["$\\hat{F}_v(\\mathbf{p},t)$", "環境因素 $v$ 在位置 $\\mathbf{p}$ 與時間 $t$ 的最終估計值。", "溫度為 °C、濕度為 %RH、照度為 lux。"],
                ["$v$", "被估計的環境因素索引。", "$v\\in\\{T,H,L\\}$，分別代表 temperature、humidity、illuminance。"],
                ["$T(\\mathbf{p},t)$", "位置 $\\mathbf{p}$、時間 $t$ 的溫度場。", "單位為 °C。"],
                ["$H(\\mathbf{p},t)$", "位置 $\\mathbf{p}$、時間 $t$ 的相對濕度場。", "單位為 %RH，後續以 $\\mathrm{clip}_{[0,100]}$ 限制在 0 到 100。"],
                ["$L(\\mathbf{p},t)$", "位置 $\\mathbf{p}$、時間 $t$ 的照度場。", "單位為 lux，後續以 $\\max\\{0,\\cdot\\}$ 避免負照度。"],
                ["$\\mathbf{p}=(x,y,z)$", "查詢點或採樣點的三維座標。", "單位為 m，座標系統與房間設計檔一致。"],
                ["$x,y,z$", "分別為房間寬度方向、長度方向與高度方向座標。", "原點位於房間地面西南角。"],
                ["$t$", "情境經過時間、設備啟動後時間或 demo 時間軸上的查詢時間。", "單位依實作通常為 s 或 min；論文公式只表示相對時間。"],
                ["$N_v(\\mathbf{p},t)$", "變數專屬 nominal model 輸出，負責描述該變數主要物理趨勢。", "溫度、濕度、照度各自使用不同公式。"],
                ["$C_v(\\mathbf{p},t)$", "由 8 顆角落感測器 residual 形成的校正場。", "用於修正 nominal model 的低階空間偏差。"],
            ],
        ),
        heading("3.3.1 共用符號與 Indoor Baseline", 3),
        paragraph(
            "其中 $T$ 代表 temperature，$H$ 代表 relative humidity，$L$ 代表 illuminance。$C_v$ 的三線性形式在 3.5 節定義；本節先定義三個不同的 nominal model。為了讓公式可讀，本研究先定義共用的幾何與裝置符號。令查詢點為 $\\mathbf{p}=(x,y,z)$，房間高度為 $H_r$，則正規化垂直位置為："
        ),
        math(r"\zeta=\frac{z}{H_r}-\frac{1}{2}"),
        paragraph(
            "本節公式中的 baseline 指的是 indoor baseline，即房間在目標設備作用尚未加入、且尚未套用角落感測器 residual correction 前的室內基準狀態，不是第 5 章用來比較方法優劣的 IDW baseline，也不是公開資料集中的 persistence 或 linear regression baseline。具體而言，本研究將室內基準狀態寫成："
        ),
        math(r"\mathbf{b}_0=(T_0,H_0,L_0)"),
        paragraph(
            "$T_0$、$H_0$ 與 $L_0$ 分別代表該次情境的起始室內溫度、相對濕度與照度。若有真實部署資料，且可取得設備啟用前或查詢前的穩定參考時間 $t_{\\mathrm{ref}}$，則可由 8 顆角落感測器的平均值初始化："
        ),
        math(
            r"\begin{aligned}"
            r"T_0&=\frac{1}{|\mathcal{S}|}\sum_{s\in\mathcal{S}}O_T(\mathbf{p}_s,t_{\mathrm{ref}}),\\"
            r"H_0&=\frac{1}{|\mathcal{S}|}\sum_{s\in\mathcal{S}}O_H(\mathbf{p}_s,t_{\mathrm{ref}}),\\"
            r"L_0&=\frac{1}{|\mathcal{S}|}\sum_{s\in\mathcal{S}}O_L(\mathbf{p}_s,t_{\mathrm{ref}})"
            r"\end{aligned}"
        ),
        paragraph(
            "其中 $\\mathcal{S}$ 為 8 顆角落感測器集合，$O_v$ 為實際觀測值。若沒有啟用前觀測資料，則 baseline 由房間設計檔或情境設定提供；本研究標準房間預設為 $T_0=29.0^\\circ\\mathrm{C}$、$H_0=67.0\\%$、$L_0=90.0$ lux。Web demo 左側的 Indoor Baseline 欄位即是讓使用者直接指定這三個基準值。後續所有冷氣、窗戶與照明項，都是在此室內基準狀態上增加或減少的偏移量。"
        ),
        paragraph(
            "第 $j$ 個裝置的時間啟用量與空間影響 envelope 分別定義為："
        ),
        math(r"A_j(t)=a_j\left(1-e^{-t/\tau_j}\right)"),
        math(
            r"\begin{aligned}"
            r"E_j(\mathbf{p},t)&=A_j(t)R_j(\mathbf{p})D_j(\mathbf{p},t)V_j(\mathbf{p}),\\"
            r"R_j(\mathbf{p})&=\exp(-\|\mathbf{p}-\mathbf{p}_j\|/r_j)"
            r"\end{aligned}"
        ),
        paragraph(
            "$A_j(t)$ 描述裝置由剛啟動到接近準穩態的時間響應；$R_j$ 是距離衰減；$D_j$ 是方向性項，例如冷氣出風方向或燈具照射方向；$V_j$ 是家具或牆面造成的可見性／遮蔽項；$r_j$ 是裝置影響半徑。這個 envelope 是三個變數共用的空間結構，但各變數如何使用它並不相同。"
        ),
        table(
            ["符號", "詳細意義", "單位或備註"],
            [
                ["$T_0,H_0,L_0$", "Indoor baseline，即設備作用與 residual correction 前的起始室內溫度、相對濕度與照度。", "分別為 °C、%RH、lux。"],
                ["$\\mathbf{b}_0$", "三個 baseline 值組成的向量。", "$\\mathbf{b}_0=(T_0,H_0,L_0)$。"],
                ["$\\mathcal{S}$", "角落感測器集合。", "本研究固定為 8 顆。"],
                ["$s$", "感測器索引。", "$s\\in\\mathcal{S}$。"],
                ["$\\mathbf{p}_s$", "第 $s$ 顆感測器的位置。", "位於地面四角或天花板四角。"],
                ["$t_{\\mathrm{ref}}$", "用來初始化 baseline 的參考時間。", "應選在設備作用尚未加入或狀態穩定時。"],
                ["$O_v(\\mathbf{p}_s,t_{\\mathrm{ref}})$", "感測器在位置 $\\mathbf{p}_s$、時間 $t_{\\mathrm{ref}}$ 對變數 $v$ 的實際觀測值。", "作為 baseline 或 residual 的資料來源。"],
                ["$z,H_r,\\zeta$", "$z$ 為查詢點高度，$H_r$ 為房間高度，$\\zeta=z/H_r-1/2$ 為中心化高度。", "$\\zeta>0$ 表示偏上層，$\\zeta<0$ 表示偏下層。"],
                ["$j$", "裝置索引。", "例如冷氣、窗戶或燈具。"],
                ["$A_j(t)$", "第 $j$ 個裝置在時間 $t$ 的有效啟用量。", "由 $a_j$ 與 $\\tau_j$ 控制。"],
                ["$a_j$", "裝置啟用強度或穩態比例。", "常介於 0 到 1；也可視為經校正後的強度尺度。"],
                ["$\\tau_j$", "裝置接近穩態的時間常數。", "愈大代表影響累積愈慢。"],
                ["$E_j(\\mathbf{p},t)$", "裝置在位置 $\\mathbf{p}$、時間 $t$ 的空間影響 envelope。", "結合時間響應、距離、方向與遮蔽。"],
                ["$R_j(\\mathbf{p})$", "距離衰減項。", "$\\exp(-\\|\\mathbf{p}-\\mathbf{p}_j\\|/r_j)$。"],
                ["$D_j(\\mathbf{p},t)$", "方向性或朝向權重。", "用於冷氣出風方向、窗戶日照方向或燈具照射方向。"],
                ["$V_j(\\mathbf{p})$", "可見性或遮蔽項。", "0 表示完全遮蔽，1 表示未遮蔽，中間值表示部分遮蔽。"],
                ["$\\mathbf{p}_j$", "第 $j$ 個裝置的位置。", "與房間座標同單位 m。"],
                ["$r_j$", "第 $j$ 個裝置的作用半徑或衰減尺度。", "單位為 m。"],
                ["$P_j$", "第 $j$ 個裝置的 power scale。", "可由感測器資料校正，用來修正預設設備強度。"],
                ["$k^{g},k^{s}$", "全室平均響應與空間局部響應的簡化增益係數。", "$g$ 表示 global，$s$ 表示 spatial/local。"],
                ["$M(t)$", "房間混合係數。", "用於調整垂直分層項的強度。"],
            ],
        ),
        heading("3.3.2 溫度場模型", 3),
        paragraph("溫度場的 nominal model 採用熱交換與熱源近似，先分成 indoor baseline、全室平均響應、局部空間響應與垂直分層四個部分："),
        math(
            r"\begin{aligned}"
            r"N_T(\mathbf{p},t)=T_0+B_T(t)+S_T(\mathbf{p},t)+\gamma_T M(t)\zeta"
            r"\end{aligned}"
        ),
        math(
            r"\begin{aligned}"
            r"B_T(t)=&\,B_{\mathrm{ac},T}(t)+B_{\mathrm{win},T}(t)+B_{\mathrm{light},T}(t),\\"
            r"S_T(\mathbf{p},t)=&\,S_{\mathrm{ac},T}(\mathbf{p},t)+S_{\mathrm{win},T}(\mathbf{p},t)+S_{\mathrm{light},T}(\mathbf{p},t)"
            r"\end{aligned}"
        ),
        paragraph(
            "其中 $B_T$ 表示全室平均熱響應，$S_T$ 表示設備附近的局部熱影響，$\\gamma_T M(t)\\zeta$ 表示垂直溫度分層。三個主要裝置的溫度項可展開為："
        ),
        math(
            r"\begin{aligned}"
            r"B_{\mathrm{ac},T}(t)&=s_m k_{\mathrm{ac},T}^{g}d_TP_{\mathrm{ac}}A_{\mathrm{ac}}(t),\\"
            r"S_{\mathrm{ac},T}(\mathbf{p},t)&=s_m k_{\mathrm{ac},T}^{s}d_TP_{\mathrm{ac}}E_{\mathrm{ac}}(\mathbf{p},t)"
            r"\end{aligned}"
        ),
        math(
            r"\begin{aligned}"
            r"B_{\mathrm{win},T}(t)&=k_{\mathrm{win},T}^{g}(T_{\mathrm{out}}-T_0)P_{\mathrm{win}}A_{\mathrm{win}}(t),\\"
            r"S_{\mathrm{win},T}(\mathbf{p},t)&=k_{\mathrm{win},T}^{s}(T_{\mathrm{out}}-T_0)P_{\mathrm{win}}E_{\mathrm{win}}(\mathbf{p},t)"
            r"\end{aligned}"
        ),
        math(
            r"\begin{aligned}"
            r"B_{\mathrm{light},T}(t)&=k_{\mathrm{light},T}^{g}P_{\mathrm{light}}A_{\mathrm{light}}(t),\\"
            r"S_{\mathrm{light},T}(\mathbf{p},t)&=k_{\mathrm{light},T}^{s}P_{\mathrm{light}}E_{\mathrm{light}}(\mathbf{p},t)"
            r"\end{aligned}"
        ),
        paragraph(
            "其中 $s_m$ 由冷氣模式決定，冷房或除濕時為負，加熱時為正，送風模式不產生全室熱量變化；$d_T$ 代表冷氣設定溫度與室內基準溫度形成的需求量。此式的重點是：溫度使用熱交換與熱源項，不使用照度的光學項。"
        ),
        table(
            ["溫度公式符號", "詳細意義", "物理角色"],
            [
                ["$N_T(\\mathbf{p},t)$", "溫度 nominal estimate。", "在尚未加上角落 residual correction 前，模型對位置 $\\mathbf{p}$ 的溫度估計。"],
                ["$B_T(t)$", "全室平均溫度響應。", "描述設備或窗戶造成的整體室溫偏移，不區分房間內不同位置。"],
                ["$S_T(\\mathbf{p},t)$", "局部溫度響應。", "描述冷氣出風口、窗邊或燈具附近與其他位置不同的局部熱影響。"],
                ["$\\gamma_T$", "垂直溫度分層係數。", "控制上層與下層溫度差的強度。"],
                ["$M(t)$", "混合係數。", "與 $\\gamma_T\\zeta$ 相乘，用來調整分層效果隨時間或混合狀態的變化。"],
                ["$\\zeta$", "中心化高度。", "使垂直項在房間中層附近為 0，上層與下層分別呈現正負偏移。"],
                ["$B_{\\mathrm{ac},T},S_{\\mathrm{ac},T}$", "冷氣造成的全室與局部溫度項。", "通常為降溫；符號由 $s_m$ 與冷氣模式決定。"],
                ["$B_{\\mathrm{win},T},S_{\\mathrm{win},T}$", "窗戶造成的全室與局部溫度項。", "由室外與室內基準溫差 $T_{\\mathrm{out}}-T_0$ 決定升溫或降溫。"],
                ["$B_{\\mathrm{light},T},S_{\\mathrm{light},T}$", "照明造成的全室與局部熱項。", "表示燈具發熱對溫度的低階近似。"],
                ["$s_m$", "冷氣模式符號。", "冷房或除濕為負、加熱為正、送風近似為 0。"],
                ["$d_T$", "冷氣溫度需求量。", "表示冷氣設定溫度與目前 indoor baseline 之間的差距強度。"],
                ["$k_{\\mathrm{ac},T}^{g},k_{\\mathrm{win},T}^{g},k_{\\mathrm{light},T}^{g}$", "溫度全室響應增益。", "決定各裝置對 $B_T(t)$ 的影響大小。"],
                ["$k_{\\mathrm{ac},T}^{s},k_{\\mathrm{win},T}^{s},k_{\\mathrm{light},T}^{s}$", "溫度局部響應增益。", "決定各裝置對 $S_T(\\mathbf{p},t)$ 的影響大小。"],
                ["$P_{\\mathrm{ac}},P_{\\mathrm{win}},P_{\\mathrm{light}}$", "冷氣、窗戶與照明的 power scale。", "由預設值或感測器 calibration 給定，用來修正裝置實際強度。"],
                ["$A_{\\mathrm{ac}},A_{\\mathrm{win}},A_{\\mathrm{light}}$", "冷氣、窗戶與照明的時間啟用量。", "表示設備影響隨 elapsed time 逐漸累積。"],
                ["$E_{\\mathrm{ac}},E_{\\mathrm{win}},E_{\\mathrm{light}}$", "冷氣、窗戶與照明的空間 envelope。", "表示位置、方向與遮蔽造成的局部影響差異。"],
            ],
        ),
        heading("3.3.3 濕度場模型", 3),
        paragraph("濕度場的 nominal model 不直接套用熱場公式，而是使用水氣交換與冷氣除濕近似。其結構同樣分成 indoor baseline、全室平均響應、局部空間響應與垂直濕度梯度："),
        math(
            r"\begin{aligned}"
            r"N_H(\mathbf{p},t)=\mathrm{clip}_{[0,100]}\{H_0+B_H(t)+S_H(\mathbf{p},t)-\gamma_H M(t)\zeta\}"
            r"\end{aligned}"
        ),
        math(
            r"\begin{aligned}"
            r"B_H(t)=&-k_{\mathrm{ac},H}^{g}d_HP_{\mathrm{ac}}A_{\mathrm{ac}}(t)"
            r"+k_{\mathrm{win},H}^{g}(H_{\mathrm{out}}-H_0)P_{\mathrm{win}}A_{\mathrm{win}}(t),\\"
            r"S_H(\mathbf{p},t)=&-k_{\mathrm{ac},H}^{s}d_HP_{\mathrm{ac}}E_{\mathrm{ac}}(\mathbf{p},t)"
            r"+k_{\mathrm{win},H}^{s}(H_{\mathrm{out}}-H_0)P_{\mathrm{win}}E_{\mathrm{win}}(\mathbf{p},t)"
            r"\end{aligned}"
        ),
        paragraph(
            "其中 $H_0$ 為室內基準相對濕度，$H_{\\mathrm{out}}$ 為室外相對濕度，$d_H$ 為除濕需求量。冷氣項為負值，表示除濕；窗戶項由 $(H_{\\mathrm{out}}-H_0)$ 決定正負，表示外氣較濕時提高室內濕度，外氣較乾時降低室內濕度。此處並未主張完整求解水氣質量守恆或 psychrometric model，而是使用控制導向的低階近似，再交由角落感測器 residual 校正吸收模型偏差。"
        ),
        table(
            ["濕度公式符號", "詳細意義", "物理角色"],
            [
                ["$N_H(\\mathbf{p},t)$", "濕度 nominal estimate。", "在尚未加上角落 residual correction 前，模型對位置 $\\mathbf{p}$ 的相對濕度估計。"],
                ["$\\mathrm{clip}_{[0,100]}$", "上下界截斷函數。", "確保相對濕度不低於 0% 且不高於 100%。"],
                ["$H_0$", "室內基準相對濕度。", "設備作用前或查詢前的室內濕度起點。"],
                ["$B_H(t)$", "全室平均濕度響應。", "描述冷氣除濕或窗戶換氣對全室濕度的平均影響。"],
                ["$S_H(\\mathbf{p},t)$", "局部濕度響應。", "描述冷氣附近、窗邊等位置的濕度變化差異。"],
                ["$\\gamma_H$", "垂直濕度梯度係數。", "控制高度造成的濕度分層強度。"],
                ["$-\\gamma_H M(t)\\zeta$", "濕度垂直項。", "使用負號表示目前模型假設上層與下層濕度梯度方向與溫度項不同。"],
                ["$k_{\\mathrm{ac},H}^{g},k_{\\mathrm{ac},H}^{s}$", "冷氣除濕的全室與局部增益。", "增益越大，冷氣對濕度下降的影響越強。"],
                ["$k_{\\mathrm{win},H}^{g},k_{\\mathrm{win},H}^{s}$", "窗戶換氣的全室與局部濕度增益。", "增益越大，室外濕度與室內基準濕度的差異越容易傳入室內。"],
                ["$d_H$", "除濕需求量。", "表示冷氣除濕作用的有效強度。"],
                ["$H_{\\mathrm{out}}-H_0$", "室外與室內基準濕度差。", "大於 0 表示外氣較濕、開窗傾向增加濕度；小於 0 表示外氣較乾、開窗傾向降低濕度。"],
                ["$P_{\\mathrm{ac}},P_{\\mathrm{win}}$", "冷氣與窗戶的 power scale。", "校正冷氣除濕強度與窗戶換氣強度。"],
                ["$A_{\\mathrm{ac}},A_{\\mathrm{win}}$", "冷氣與窗戶的時間啟用量。", "描述除濕或換氣影響隨時間累積。"],
                ["$E_{\\mathrm{ac}},E_{\\mathrm{win}}$", "冷氣與窗戶的空間 envelope。", "描述不同位置受冷氣或窗戶濕度影響的程度。"],
            ],
        ),
        heading("3.3.4 照度場模型", 3),
        paragraph("照度場的 nominal model 採用燈具光束、日照、遮蔽與反射近似，不使用溫濕度的全室混合項："),
        math(
            r"N_L(\mathbf{p},t)=\max\{0,L_0+L_{\mathrm{win}}^{\mathrm{dir}}(\mathbf{p},t)+L_{\mathrm{light}}^{\mathrm{dir}}(\mathbf{p},t)+L_{\mathrm{win}}^{\mathrm{amb}}(\mathbf{p},t)+I^{\mathrm{refl}}(\mathbf{p},t)\}"
        ),
        math(
            r"\begin{aligned}"
            r"L_{\mathrm{win}}^{\mathrm{dir}}(\mathbf{p},t)&=S_{\mathrm{out}}d_f k_{\mathrm{sol}}P_{\mathrm{win}}E_{\mathrm{win}}(\mathbf{p},t),\\"
            r"L_{\mathrm{light}}^{\mathrm{dir}}(\mathbf{p},t)&=G_{\mathrm{light}}P_{\mathrm{light}}A_{\mathrm{light}}(t)\Phi_{\mathrm{light}}(\mathbf{p})Q_{\mathrm{light}}(\mathbf{p})V_{\mathrm{light}}(\mathbf{p}),\\"
            r"L_{\mathrm{win}}^{\mathrm{amb}}(\mathbf{p},t)&=\beta_{\mathrm{amb}}L_0P_{\mathrm{win}}A_{\mathrm{win}}(t)"
            r"\exp(-\|\mathbf{p}-\mathbf{p}_{\mathrm{win}}\|/(1.8r_{\mathrm{win}}))"
            r"\end{aligned}"
        ),
        math(
            r"\Phi_{\mathrm{light}}(\mathbf{p})=\eta_{\mathrm{floor}}+(1-\eta_{\mathrm{floor}})"
            r"\max(0,\mathbf{o}_{\mathrm{light}}\cdot\hat{\mathbf{r}}_{\mathrm{light}\to p})^{\alpha},\qquad "
            r"Q_{\mathrm{light}}(\mathbf{p})=\frac{d_{\mathrm{ref}}^2}{\|\mathbf{p}-\mathbf{p}_{\mathrm{light}}\|^2+\epsilon d_{\mathrm{ref}}^2}"
        ),
        paragraph(
            "其中 $L_0$ 為室內基準照度，$S_{\\mathrm{out}}$ 為外部日照照度，$d_f$ 為 daylight factor，$k_{\\mathrm{sol}}$ 為窗戶日照增益，$G_{\\mathrm{light}}$ 為燈具照度增益，$\\Phi_{\\mathrm{light}}$ 為由光束角推得的 cosine 方向權重，$Q_{\\mathrm{light}}$ 為參考距離正規化後的距離衰減，$V_{\\mathrm{light}}$ 為燈具到查詢點的遮蔽或可見性，$\\beta_{\\mathrm{amb}}$ 為窗邊散射背景光係數。$I^{\\mathrm{refl}}$ 是 3.4 節定義的 single-bounce diffuse reflection。標準情境中的窗戶日照仍使用 envelope daylight 近似；本研究曾測試以窗戶面積與 aperture view factor 取代預設窗戶項，但在目前 8 組標準情境會增加 window family 的照度誤差，因此保留為可選模式而不作為本文預設結果。照度模型的重點在於光源位置、方向性、距離衰減、遮蔽與表面反射，因此它與溫度、濕度的熱交換或水氣交換公式不同。"
        ),
        table(
            ["照度公式符號", "詳細意義", "光學或模型角色"],
            [
                ["$N_L(\\mathbf{p},t)$", "照度 nominal estimate。", "在尚未加上角落 residual correction 前，模型對位置 $\\mathbf{p}$ 的照度估計。"],
                ["$\\max\\{0,\\cdot\\}$", "非負截斷。", "避免因校正或負項造成物理上不合理的負照度。"],
                ["$L_0$", "室內基準照度。", "沒有新增窗戶或燈具作用前的背景照度。"],
                ["$L_{\\mathrm{win}}^{\\mathrm{dir}}$", "窗戶直射或主要入射光項。", "表示外部日照經窗戶進入室內後對查詢點的直接貢獻。"],
                ["$L_{\\mathrm{light}}^{\\mathrm{dir}}$", "燈具直射光項。", "以燈具啟用量、光束方向、距離衰減與遮蔽估計查詢點的直接照度。"],
                ["$L_{\\mathrm{win}}^{\\mathrm{amb}}$", "窗邊環境散射光項。", "補足窗戶附近非直射但仍與開窗、外光相關的背景亮度。"],
                ["$I^{\\mathrm{refl}}(\\mathbf{p},t)$", "單次漫反射項。", "由牆面、地板、天花板與家具表面作為次級反射面，補足 indirect fill light。"],
                ["$S_{\\mathrm{out}}$", "外部日照照度。", "室外光源強度；天氣、時段或外部資料會改變此值。"],
                ["$d_f$", "daylight factor。", "表示外部日照進入室內後的比例或衰減。"],
                ["$k_{\\mathrm{sol}}$", "窗戶日照增益。", "調整窗戶直射光項的強度。"],
                ["$G_{\\mathrm{light}}$", "燈具照度增益。", "調整燈具直射光項的強度。"],
                ["$\\Phi_{\\mathrm{light}}$", "燈具方向權重。", "由燈具朝向與查詢點方向的 cosine 投影計算，光束角決定衰減指數。"],
                ["$Q_{\\mathrm{light}}$", "燈具距離衰減。", "以參考距離正規化的 inverse-square 近似，避免遠端或近端量級失控。"],
                ["$V_{\\mathrm{light}}$", "燈具可見性或遮蔽項。", "家具遮擋燈具到查詢點的路徑時降低直接照度。"],
                ["$\\eta_{\\mathrm{floor}}$", "方向權重下限。", "避免光束邊緣被硬切為 0，保留少量散射近似。"],
                ["$\\alpha$", "光束角對應的 cosine 指數。", "光束越窄，方向衰減越快；光束越寬，照度分布越平滑。"],
                ["$d_{\\mathrm{ref}}$", "燈具 photometric reference distance。", "作為距離衰減的正規化尺度。"],
                ["$\\beta_{\\mathrm{amb}}$", "窗邊散射背景光係數。", "控制窗邊 ambient light 對室內照度的補償程度。"],
                ["$\\mathbf{p}_{\\mathrm{win}}$", "窗戶位置。", "用於計算查詢點離窗戶的距離。"],
                ["$r_{\\mathrm{win}}$", "窗戶影響半徑。", "控制 $L_{\\mathrm{win}}^{\\mathrm{amb}}$ 隨距離衰減的速度。"],
                ["$1.8r_{\\mathrm{win}}$", "窗邊散射光的衰減尺度。", "比直接窗戶 envelope 稍長，用來表示散射光比直射項更平滑。"],
            ],
        ),
        paragraph(
            "因此，本研究的主張不是「溫度、濕度、照度都遵守同一套 bulk + local 物理定律」，而是「三種變數各自先由符合其物理特性的低階 nominal model 產生估計，再共用 8 點 sparse-sensor residual correction」。這樣可同時保留可解釋性、低運算成本，以及由真實感測資料校正的能力。"
        ),
        heading("3.4 設備影響函數", 2),
        bullets(
            [
                "冷氣：主要造成局部降溫，並帶有弱除濕效果；3D 視覺化中以牆面橫條表示。",
                "窗戶：受外部溫度、外部濕度與日照條件影響，同時改變三個環境因素；3D 視覺化中以牆面矩形表示。",
                "照明：主要提升照度，並產生少量熱效應；3D 視覺化中以點狀標記表示。",
            ]
        ),
        paragraph(
            "對照度而言，若只使用窗戶與照明的直接項，再乘上遮蔽衰減，常會低估牆面、地板與家具附近的間接回填亮度。若改用完整 radiosity 或 ray tracing，則需要更細的表面材質、反射模型與幾何資訊，且計算成本明顯提高，與本研究稀疏感測、低成本原型的定位不符。因此本研究僅在 illuminance 路徑加入一個 lightweight single-bounce diffuse reflection 近似："
        ),
        math(
            r"I^{\text{refl}}(\mathbf{p},t) = \sum_{s} \rho_s \bar{I}_s A_s^{\text{rel}}"
            r" e^{-\|\mathbf{p}-\mathbf{c}_s\|/\ell_s}"
            r" \max(0,\,\mathbf{n}_s \cdot \hat{\mathbf{r}}_{s\to p})\, V_s(\mathbf{p})"
        ),
        paragraph(
            "其中 $s$ 代表 floor、ceiling、四面牆與啟用中的家具表面；$\\rho_s$ 為表面反射率；$\\bar{I}_s$ 為該表面中心由 direct light 接收到的照度；$A_s^{\\text{rel}}$ 為正規化後的面積因子；$\\ell_s$ 為衰減長度；$V_s(\\mathbf{p})$ 則延用既有遮蔽邏輯。這個公式的目的不是做高保真光學渲染，而是在不引入完整光傳輸模擬的前提下，補足 direct light 對 indirect fill light 的低估。"
        ),
        table(
            ["反射公式符號", "詳細意義", "模型角色"],
            [
                ["$I^{\\text{refl}}(\\mathbf{p},t)$", "查詢點收到的單次漫反射照度。", "加到照度 nominal model 中，補足 indirect fill light。"],
                ["$\\sum_s$", "對所有候選反射表面加總。", "包含 floor、ceiling、四面牆，以及啟用中的家具表面。"],
                ["$s$", "反射表面索引。", "每個 $s$ 對應一個具有位置、法向量與面積的表面。"],
                ["$\\rho_s$", "表面 $s$ 的反射率。", "0 表示完全不反射，1 表示理想全反射；本研究使用簡化參數。"],
                ["$\\bar{I}_s$", "表面 $s$ 中心接收到的 direct illuminance。", "表示該表面被窗戶或燈具照亮後可作為次級光源的強度。"],
                ["$A_s^{\\text{rel}}$", "相對面積因子。", "面積越大的表面可提供較多反射貢獻；經正規化避免量級失控。"],
                ["$\\mathbf{c}_s$", "表面 $s$ 的中心點。", "用來計算表面中心到查詢點的距離。"],
                ["$\\ell_s$", "表面 $s$ 的反射衰減長度。", "值越大表示反射光衰減越慢。"],
                ["$e^{-\\|\\mathbf{p}-\\mathbf{c}_s\\|/\\ell_s}$", "距離衰減項。", "查詢點離反射表面越遠，該表面的回填照度越弱。"],
                ["$\\mathbf{n}_s$", "表面 $s$ 的外法向量或有效反射方向。", "用於判斷查詢點是否位於該表面可反射的方向。"],
                ["$\\hat{\\mathbf{r}}_{s\\to p}$", "由表面中心指向查詢點的單位向量。", "與 $\\mathbf{n}_s$ 做內積以計算方向投影。"],
                ["$\\max(0,\\mathbf{n}_s\\cdot\\hat{\\mathbf{r}}_{s\\to p})$", "Lambertian 方向投影近似。", "若查詢點在表面背向側，貢獻被截為 0。"],
                ["$V_s(\\mathbf{p})$", "反射面到查詢點之間的可見性或遮蔽項。", "家具或牆面遮擋時降低反射貢獻。"],
            ],
        ),
        paragraph(
            "換言之，本研究對 illuminance 的設計取捨是：保留 direct source、directionality 與 obstruction 的可解釋結構，再另外加上一個單次漫反射近似，使牆、地板、天花板與家具能作為次級發光面回填照度。這樣既能維持與現有影響場模型一致的參數化形式，也比 full radiosity 更適合目前的單房間數位孿生原型。"
        ),
        heading("3.5 感測器校正模型", 2),
        paragraph(
            "模型先預測 8 顆角落感測器位置的三因子值，再與觀測值比較得到殘差。為提高環境估計精度，系統先以最小平方法估計 active device 的 power scale，使設備影響函數更接近觀測資料；接著對每一個環境因素，以 8 參數 trilinear correction 擬合角落殘差："
        ),
        math(r"C(\mathbf{p}) = c_0 + c_1 X + c_2 Y + c_3 Z + c_4 XY + c_5 XZ + c_6 YZ + c_7 XYZ"),
        paragraph(
            "其中 X、Y、Z 為正規化後的房間座標。相較於一階 affine surface，trilinear correction 可使用 8 個角點支撐 8 個校正係數，除了整體偏移與一階梯度外，也能表示角落之間的交互變化。不過此方法仍無法重建任意高頻局部變化，因此其定位仍是低成本、可解釋的場校正方法。"
        ),
        table(
            ["校正公式符號", "詳細意義", "模型角色"],
            [
                ["$C(\\mathbf{p})$", "某一環境因素在查詢點的三線性 residual correction。", "加回 nominal model 以修正低階空間偏差。"],
                ["$X,Y,Z$", "正規化房間座標，分別由 $x/W$、$y/L$、$z/H$ 得到。", "皆介於 0 到 1，表示查詢點在房間內的相對位置。"],
                ["$c_0$", "常數項。", "修正整體偏移，也就是所有角點共同偏高或偏低的部分。"],
                ["$c_1X,c_2Y,c_3Z$", "三個一階空間梯度項。", "修正沿寬度、長度與高度方向的線性偏差。"],
                ["$c_4XY,c_5XZ,c_6YZ$", "兩兩交互項。", "修正兩個方向同時變化時的低階彎曲或角落差異。"],
                ["$c_7XYZ$", "三方向交互項。", "修正需要同時考慮 x、y、z 三方向的角落差異。"],
                ["$c_0,\\ldots,c_7$", "8 個三線性校正係數。", "由 8 顆角落感測器 residual 決定或等價地由 8 個 Lagrange basis 權重表示。"],
            ],
        ),
        heading("3.5.1 8 點場推估的可證明範圍", 3),
        paragraph(
            "本研究必須先區分「取得資料」與「推估資料」：8 顆角落感測器以外的位置並沒有被直接量測，系統輸出的其他採樣點數值是由物理先驗模型加上角落 residual correction 推估而得。因此，本研究不宣稱只靠 8 點可以無條件還原任意真實室內場；可嚴謹證明的是，在明確模型假設下，8 個角點可唯一決定一個三線性 residual correction，且該 correction 對三線性 residual 完全正確，對平滑 residual 則具有可寫出的誤差界。"
        ),
        paragraph(
            "首先說明不可證明的部分。若不對真實場加入任何平滑性、物理模型或函數族假設，僅由 8 個角落值無法唯一決定房間內任一非角落點的值。理由是：對任一非感測點 $\\mathbf{p}^{*}$，可構造一個連續 bump function $g(\\mathbf{p})$，使其在 8 個角落皆為 0，但在 $\\mathbf{p}^{*}$ 為 1。則任意一個場 $f(\\mathbf{p})$ 與另一個場 $f(\\mathbf{p})+\\alpha g(\\mathbf{p})$ 在 8 顆感測器上完全相同，卻在 $\\mathbf{p}^{*}$ 相差 $\\alpha$。因此，若沒有額外假設，任何演算法都無法由同一組 8 點觀測唯一判斷 $\\mathbf{p}^{*}$ 的真值。這也說明本研究必須把主張寫成條件式推估，而不是任意場重建定理。"
        ),
        paragraph(
            "在本研究的條件式模型中，令房間為 $\\Omega=[0,W]\\times[0,L]\\times[0,H]$，正規化座標為 $X=x/W$、$Y=y/L$、$Z=z/H$。對任一環境因素 $v$，主模型先給出 nominal estimate $N_v(\\mathbf{p},t)$，8 個角落感測器在角點 $\\mathbf{p}_{abc}$（$a,b,c\\in\\{0,1\\}$）提供觀測 $O_v(\\mathbf{p}_{abc},t)$，角落殘差定義為："
        ),
        math(r"r_{abc}^{v}(t)=O_v(\mathbf{p}_{abc},t)-N_v(\mathbf{p}_{abc},t)"),
        paragraph(
            "三線性校正場使用 8 個角點殘差作為權重基底。令 $\\ell_0(s)=1-s$、$\\ell_1(s)=s$，則任一室內點的 residual correction 為："
        ),
        math(r"C_v(X,Y,Z,t)=\sum_{a,b,c\in\{0,1\}} r_{abc}^{v}(t)\,\ell_a(X)\ell_b(Y)\ell_c(Z)"),
        paragraph("最後任一採樣點或查詢點的推估值為："),
        math(r"\hat{F}_v(\mathbf{p},t)=N_v(\mathbf{p},t)+C_v(X,Y,Z,t)"),
        table(
            ["8 點推估符號", "詳細意義", "推估或證明中的角色"],
            [
                ["$\\Omega=[0,W]\\times[0,L]\\times[0,H]$", "房間的三維定義域。", "$W,L,H$ 分別為房間寬度、長度與高度。"],
                ["$X=x/W,Y=y/L,Z=z/H$", "將實際座標轉成 0 到 1 的正規化座標。", "讓八個角點可寫成 0 或 1 的組合。"],
                ["$a,b,c\\in\\{0,1\\}$", "角點索引。", "a 對應 x 方向，b 對應 y 方向，c 對應 z 方向。"],
                ["$\\mathbf{p}_{abc}$", "由索引 $a,b,c$ 指定的房間角點。", "例如 $\\mathbf{p}_{000}$ 是原點角，$\\mathbf{p}_{111}$ 是對角天花板角。"],
                ["$O_v(\\mathbf{p}_{abc},t)$", "角點感測器對第 v 個環境因素的觀測。", "8 點推估的實測輸入。"],
                ["$N_v(\\mathbf{p}_{abc},t)$", "主模型在同一角點的 nominal estimate。", "用來和觀測值相減得到 residual。"],
                ["$r_{abc}^{v}(t)$", "角點 residual。", "等於觀測值減去 nominal estimate，是三線性校正的資料來源。"],
                ["$\\ell_0(s)=1-s,\\ell_1(s)=s$", "一維線性 Lagrange basis。", "在座標為 0 或 1 的角點上會選出對應角點權重。"],
                ["$\\ell_a(X)\\ell_b(Y)\\ell_c(Z)$", "三維角點權重。", "所有 8 個權重在房間內非負且總和為 1。"],
                ["$C_v(X,Y,Z,t)$", "由 8 個角點 residual 加權得到的三線性校正值。", "使模型在角點與觀測一致，並在室內做低階補間。"],
                ["$\\hat{F}_v$", "校正後的最終估計。", "等於 nominal estimate 加上 trilinear residual correction。"],
            ],
        ),
        paragraph(
            "此公式也可解讀為對 8 個角落 residual 做 convex combination：當 $0\\le X,Y,Z\\le1$ 時，所有權重 $\\ell_a(X)\\ell_b(Y)\\ell_c(Z)$ 皆非負，且權重和為 1。因此校正值不會由任一單點無限制外插，而是在 8 個角落 residual 的包絡內進行低階空間補間。"
        ),
        paragraph(
            "命題一（角點一致性）。對任一角點 $\\mathbf{p}_{abc}$，三線性校正滿足 $C_v(\\mathbf{p}_{abc},t)=r_{abc}^{v}(t)$，因此 $\\hat{F}_v(\\mathbf{p}_{abc},t)=O_v(\\mathbf{p}_{abc},t)$。證明如下：在角點上，$X$、$Y$、$Z$ 皆為 0 或 1；對應的 $\\ell_a$ 為 1，其餘同軸基底為 0，因此上式求和只剩下對應角點的 residual。故校正後模型在 8 顆感測器位置與觀測一致。實作中為數值穩定在 normal equation 加入極小 regularization，因此角點一致性在浮點誤差範圍內成立。"
        ),
        paragraph(
            "命題二（三線性 residual 的唯一與完全重建）。若真實 residual $R_v(\\mathbf{p},t)=F_v^{\\text{true}}(\\mathbf{p},t)-N_v(\\mathbf{p},t)$ 屬於三線性函數空間"
        ),
        math(r"\mathcal{V}=\mathrm{span}\{1,X,Y,Z,XY,XZ,YZ,XYZ\}"),
        paragraph(
            "則 8 個角點 residual 可唯一決定 $R_v$，且 $C_v(\\mathbf{p},t)=R_v(\\mathbf{p},t)$ 對所有 $\\mathbf{p}\\in\\Omega$ 成立。證明重點是：$\\mathcal{V}$ 的維度為 8，而 8 個角點的取值形成一組 unisolvent interpolation conditions。若存在兩個三線性函數在所有角點取值相同，兩者相減得到一個在 8 個角點全為 0 的三線性函數；依前述 Lagrange basis 表示法，其 8 個基底係數皆為 0，因此差函數恆為 0，唯一性成立。由於 $C_v$ 與 $R_v$ 在 8 個角點取值相同且同屬 $\\mathcal{V}$，故兩者在整個房間內相同。"
        ),
        paragraph(
            "命題三（平滑 residual 的誤差界）。若真實 residual $R_v$ 不一定是三線性，但在房間內具有連續二階偏導，且"
        ),
        math(r"M_{xx}=\sup_{\Omega}|\partial^2 R_v/\partial x^2|,\quad M_{yy}=\sup_{\Omega}|\partial^2 R_v/\partial y^2|,\quad M_{zz}=\sup_{\Omega}|\partial^2 R_v/\partial z^2|"),
        paragraph("則三線性補間誤差可由下式界定："),
        math(r"|R_v(\mathbf{p},t)-C_v(\mathbf{p},t)|\le \frac{W^2}{8}M_{xx}+\frac{L^2}{8}M_{yy}+\frac{H^2}{8}M_{zz}"),
        table(
            ["誤差界符號", "詳細意義", "為什麼重要"],
            [
                ["$R_v(\\mathbf{p},t)$", "真實 residual，也就是真實場與 nominal estimate 的差。", "若它很平滑，8 點三線性校正較容易接近真實 residual。"],
                ["$\\mathcal{V}$", "三線性函數空間。", "包含常數、一階項與交互項，共 8 個基底。"],
                ["$M_{xx},M_{yy},M_{zz}$", "真實 residual 在 x、y、z 方向二階偏導的最大絕對值。", "代表 residual 的曲率或彎曲程度；值越大，8 點補間可能誤差越大。"],
                ["$\\partial^2R_v/\\partial x^2$", "residual 沿 x 方向的二階變化率。", "衡量 residual 是否有無法由線性 x 項捕捉的彎曲。"],
                ["$\\sup_{\\Omega}$", "在整個房間定義域內取最大上界。", "確保誤差界對房間內任一點都成立。"],
                ["$W^2/8,L^2/8,H^2/8$", "房間尺寸造成的補間誤差尺度。", "房間越大、且 residual 曲率越高，角點補間的最壞情況誤差越大。"],
                ["$|R_v-C_v|$", "真實 residual 與三線性校正 residual 的絕對誤差。", "這是 8 點推估能否接近真實場的關鍵誤差項。"],
            ],
        ),
        paragraph(
            "此誤差界可由一維線性補間誤差推得。對任一方向的一維線性補間，誤差上界為 $h^2\\sup|f''|/8$；三線性補間是 x、y、z 三個方向線性補間算子的張量積，且線性補間算子在 sup norm 下不放大函數最大值。因此三維誤差可分解為三個方向的一維補間誤差加總。此結果說明：8 點推估的準確度取決於主模型剩餘 residual 的平滑程度與曲率大小；若主模型已吸收主要設備影響，使 residual 只剩低頻偏移或緩慢梯度，8 點三線性校正可以提供有界且可解釋的估計；若 residual 含有強烈局部尖峰、遮蔽邊界或高頻變化，單靠 8 點無法保證準確，需額外空間探針、移動式量測或 hybrid residual 訓練資料補強。"
        ),
        image(
            "outputs/figures/architecture/感測器校正與學習流程.svg",
            "圖 3-4 感測器校正與影響學習流程。此圖說明真值模擬、角落觀測、設備 power calibration、trilinear residual correction，以及 least-squares impact learning 之間的關係。",
            asset_name="fig_3_4_sensor_calibration_learning",
        ),
        heading("3.6 非連網裝置影響學習", 2),
        paragraph("對非連網裝置，系統不依賴裝置 API，而是由啟用前後的感測器變化估計影響係數。流程如下："),
        code("before sensor observations\n→ after sensor observations\n→ sensor delta\n→ device spatial basis\n→ least-squares impact coefficient learning"),
        heading("3.7 訓練資料組裝流程", 2),
        paragraph(
            "為了讓模型不只停留在手動指定參數，本研究將資料流程拆成原始紀錄層、對齊整併層、樣本建構層與模型訓練層。原始資料至少包含四類：角落感測器時序、裝置事件紀錄、室外環境時序，以及情境描述或額外空間量測。角落感測器時序紀錄 8 顆節點在各時間點的 temperature、humidity 與 illuminance；裝置事件紀錄保存冷氣、窗戶與燈的啟用狀態、模式、設定溫度、風量、左右/上下出風角度、固定或擺動設定與開窗比例；室外環境時序提供 outdoor temperature、outdoor humidity 與 sunlight；情境描述則記錄房間尺寸、目標區域、家具配置與採樣設定。"
        ),
        table(
            ["資料表", "主要欄位", "角色"],
            [
                ["corner_sensor_timeseries", "timestamp, sensor_name, x, y, z, temperature, humidity, illuminance", "提供 8 顆角落感測器觀測值，用於校正、裝置影響學習與真實資料 fine-tune"],
                ["device_event_log", "timestamp, device_name, device_kind, activation, mode, target_temperature, fan_speed, fan_strength, horizontal_mode, horizontal_angle_deg, vertical_mode, vertical_angle_deg, opening_ratio", "還原各時間點裝置狀態，並作為特徵與影響學習依據"],
                ["outdoor_environment", "timestamp, outdoor_temperature, outdoor_humidity, sunlight_illuminance, daylight_factor", "提供窗戶影響函數與時間條件所需的外部邊界"],
                ["scenario_metadata / spatial_probe_ground_truth", "房間尺寸、家具配置、目標區域、額外空間量測", "定義情境與提供較密集的監督標籤"],
            ],
        ),
        paragraph(
            "在資料對齊階段，系統會先以時間戳記為主鍵，將感測器時序、裝置事件與外部環境資料同步到同一時間軸。接著根據房間幾何與裝置配置，將每個時間點的狀態送入主模型，得到 $F_v(\\mathbf{p},t)$ 的 physics estimate。若為影響係數學習，則以裝置啟用前後的感測器差值建立 sensor delta；若為 hybrid residual neural network，則進一步在空間採樣點上建立 feature-target 配對。"
        ),
        paragraph("對於 hybrid residual 訓練，本研究在每個採樣點 $\\mathbf{p}_i=(x_i, y_i, z_i)$ 與時間點 $t_i$ 上組合特徵向量："),
        math(
            r"\begin{aligned}"
            r"\boldsymbol{\varphi}_i = [&x_i,\, y_i,\, z_i,\, t_i,\, "
            r"\text{indoor baseline},\, \text{outdoor conditions},\\"
            r"&F_{\text{temp}},\, F_{\text{hum}},\, F_{\text{illum}},\, "
            r"\text{device activations},\\"
            r"&\text{device powers},\, \text{influence envelopes}]"
            r"\end{aligned}"
        ),
        table(
            ["訓練特徵符號", "詳細意義", "輸入資訊來源"],
            [
                ["$i$", "訓練樣本索引。", "每個樣本對應一個採樣點與一個時間。"],
                ["$\\boldsymbol{\\varphi}_i$", "第 $i$ 筆樣本的特徵向量。", "作為 hybrid residual neural network 的輸入。"],
                ["$x_i,y_i,z_i$", "第 $i$ 筆樣本的三維座標。", "來自採樣網格、角落感測器或額外 probe 點。"],
                ["$t_i$", "第 $i$ 筆樣本的 elapsed time。", "來自情境時間軸或真實資料時間戳對齊後的相對時間。"],
                ["indoor baseline", "$T_0,H_0,L_0$ 等室內起始狀態。", "由情境設定或設備啟用前感測器平均值取得。"],
                ["outdoor conditions", "$T_{\\mathrm{out}},H_{\\mathrm{out}},S_{\\mathrm{out}}$ 等外部邊界條件。", "由情境、天氣 preset 或外部資料取得。"],
                ["$F_{\\text{temp}},F_{\\text{hum}},F_{\\text{illum}}$", "主模型對三個環境因素的估計值。", "由 nominal model 加校正流程產生。"],
                ["device activations / control state", "冷氣、窗戶、照明等裝置的啟用狀態或控制比例；冷氣另包含模式、設定溫度、風量與出風方向。", "來自 device event log 或 scenario state。"],
                ["device powers", "各裝置的 power scale 或校正後作用強度。", "由預設參數或 active-device calibration 取得。"],
                ["influence envelopes", "各裝置在採樣點的 $E_j(\\mathbf{p}_i,t_i)$。", "由距離、方向與遮蔽模型計算。"],
            ],
        ),
        paragraph("若採用目前的模擬訓練設定，標籤來自 truth field 與主模型估計值之差："),
        math(r"y_i^v = F_v^{\text{truth}}(\mathbf{p}_i, t_i) - F_v(\mathbf{p}_i, t_i)"),
        table(
            ["標籤公式符號", "詳細意義", "訓練角色"],
            [
                ["$y_i^v$", "第 $i$ 筆樣本、第 $v$ 個環境因素的 residual label。", "神經網路要學習的目標值。"],
                ["$F_v^{\\text{truth}}(\\mathbf{p}_i,t_i)$", "在模擬設定下可取得的 truth field。", "作為監督標籤來源；真實部署若無 dense ground truth 則不能直接取得。"],
                ["$F_v(\\mathbf{p}_i,t_i)$", "主模型在同一點同一時間的估計值。", "與 truth field 相減後得到剩餘誤差。"],
                ["$v$", "環境因素索引。", "temperature、humidity 與 illuminance 會分別建立 label。"],
            ],
        ),
        paragraph(
            "其中 v 分別代表 temperature、humidity 與 illuminance。換言之，神經網路不是直接學整個場，而是學主模型剩餘誤差。若未來接入真實資料，則可分成兩種層次：第一種只使用 8 顆角落感測器，將其作為參數校正、裝置影響學習與角落 residual fine-tune 的監督訊號；第二種則在有移動式量測或額外空間探針時，再擴充為更完整的空間 residual 訓練。這樣可避免只憑 8 個角落點就對全室高解析度場做過度宣稱。"
        ),
        paragraph(
            "在目前的實作中，hybrid residual 訓練可選擇再加入 Fourier low-pass denoising。具體作法是：先針對同一採樣點沿 elapsed time 建立一段短 residual trace，再將該 trace 做 discrete Fourier transform、套用低通遮罩，最後以 inverse transform 還原較平滑的 residual target。根據目前實驗，此做法對 temperature 幾乎不改變結果，對 humidity 有小幅改善，但若直接套用到 illuminance 則會抹去有用的快速變化，因此目前只對 temperature 與 humidity 啟用。這個設計來自三個環境因子的物理特性差異：temperature 與 humidity 主要受熱容量、空氣混合、水氣交換與除濕作用影響，時間變化通常較平滑，高頻成分較可能是感測雜訊或短時擾動；illuminance 則直接受燈具開關、窗戶日照、遮蔽邊界、家具陰影與反射路徑影響，場值可能在短時間內出現物理上有意義的跳變。因此，照度 residual 的高頻部分不應被一律視為雜訊，否則會削弱模型對光源與遮蔽快速變化的學習能力。"
        ),
        paragraph(
            "相較於以固定時間窗做積分或區間平均的平滑方式，Fourier low-pass denoising 更適合目前題目。兩者都能降低短時振盪，但時間窗積分本質上屬於時間域中的固定 box filter，若視窗太小則去噪不足，若視窗太大則容易同時模糊瞬態響應與局部轉折，甚至造成較明顯的 lag。相對地，Fourier 低通是直接在頻域中抑制高頻成分，再還原回時間域，因此可以在保留低頻主趨勢的同時，仍然取得對應目前時間點的 denoised residual endpoint。換言之，它不是把時間資訊丟掉，而是在保留時間位置的前提下降低高頻擾動。"
        ),
        paragraph(
            "整體而言，本研究的訓練資料流程可概括為：原始感測與事件資料先經時間對齊與情境整併，再由主模型產生 physics estimate，最後依任務不同分流為 least-squares impact learning、nominal model parameter calibration 或 hybrid residual neural training。此設計的優點在於，即使資料來源從模擬擴大到真實房間快照或長期 ESP32 量測，資料進入訓練流程的接口仍可保持一致。"
        ),
        image(
            "outputs/figures/architecture/模型學習推論與推薦資料流.svg",
            "圖 3-5 模型學習、推論與推薦資料流。訓練端將原始感測、裝置事件、外部環境與情境資料轉為 scenario state，再分流為 impact learning 與 hybrid residual learning；推論端則使用同一個 scenario state 執行三因子估測，並以反事實模擬排序推薦動作。",
            width_inches=6.5,
            asset_name="fig_3_5_training_inference_flow",
        ),
        heading("3.7.1 學習與訓練資料流", 3),
        paragraph(
            "為避免把「資料如何進入模型」說成單一黑箱步驟，本研究將學習流程拆成資料輸入、時間與空間對齊、情境狀態組裝、主模型估計、任務分流與模型輸出六個階段，如圖 3-5 左側所示。此處的學習包含兩種不同任務：第一種是非連網裝置 impact learning，目標是從 before/after sensor delta 學出裝置影響係數；第二種是 hybrid residual learning，目標是讓神經網路學習主模型剩餘誤差。"
        ),
        code(
            "raw sensor / event / outdoor / scenario data\n"
            "→ time alignment and unit/coordinate normalization\n"
            "→ scenario state assembly\n"
            "→ reduced-order nominal estimate and sparse calibration\n"
            "→ task branch: impact learning or hybrid residual learning\n"
            "→ learned coefficients, checkpoint, and validation summary"
        ),
        table(
            ["階段", "資料如何進入", "處理流程", "輸出"],
            [
                [
                    "1. Raw input",
                    "角落感測器時序、裝置事件、外部環境、房間/情境描述；若是 synthetic benchmark，另有 dense truth field 或 spatial probe labels。",
                    "保留原始 timestamp、座標、裝置狀態、室外溫濕度與日照條件。",
                    "可追溯的原始紀錄。",
                ],
                [
                    "2. 對齊與正規化",
                    "將不同來源資料依 timestamp 對齊，並統一座標、單位與欄位名稱。",
                    "檢查點位是否在房間內；濕度限制在 0--100%；照度與 daylight factor 不允許為負；裝置 activation 限制在 0--1。",
                    "同一時間軸上的 normalized records。",
                ],
                [
                    "3. 情境狀態組裝",
                    "baseline、outdoor conditions、device states、furniture blockers、elapsed time 與 room geometry 進入 scenario state。",
                    "建立可被 service layer、web demo 與 MCP 共用的 runtime state。",
                    "一個完整 scenario object 或 MCP registered state。",
                ],
                [
                    "4. 主模型估計與校正",
                    "scenario state 進入溫度、濕度、照度各自的 nominal model。",
                    "計算設備 dynamic activation、influence envelope、照度 reflection；若有角落觀測，先校正 active-device power scale，再建立 trilinear residual correction。",
                    "校正後 base estimate $F_v(\\mathbf{p},t)$。",
                ],
                [
                    "5A. Impact learning 分支",
                    "同一裝置啟用前後的 8 顆角落感測器觀測值。",
                    "計算 sensor delta，建立 device spatial basis，使用 least-squares 解出各環境因素的 impact coefficients。",
                    "learned device impact coefficients 與 learning record。",
                ],
                [
                    "5B. Hybrid residual 分支",
                    "採樣點座標、時間、baseline、外部環境、設備狀態、device powers、influence envelopes 與主模型估計值。",
                    "建立特徵向量 $\\boldsymbol{\\varphi}_i$；以 $F_v^{\\text{truth}}-F_v$ 作為 residual label；temperature/humidity 可先做 Fourier low-pass denoising，illuminance 保留原始 residual。",
                    "三個環境因素各自的 residual network parameters $\\boldsymbol{\\theta}_v$。",
                ],
                [
                    "6. 訓練完成與驗證",
                    "訓練結果與 held-out / LOO split。",
                    "輸出 field MAE、sample count、no-Fourier 對照、LOO 平均與 checkpoint。",
                    "summary JSON、hybrid residual checkpoint、論文驗證報告可重現的數字來源。",
                ],
            ],
        ),
        paragraph(
            "因此，訓練完成後實際保留下來的不是一個取代全部物理模型的黑盒，而是三類可被後續推論使用的結果：校正後的主模型參數與 power scale、由 before/after 資料得到的裝置影響係數，以及 optional hybrid residual checkpoint。主模型仍負責主要物理趨勢；learned impact 與 hybrid residual 只補上非連網裝置作用與系統性殘差。"
        ),
        heading("3.7.2 訓練完成後的推論與推薦資料流", 3),
        paragraph(
            "模型訓練完成後，使用者或 MCP client 的輸入不會直接丟進神經網路得到答案，而是先被轉成與訓練階段一致的 scenario state，如圖 3-5 右側所示。接著系統先跑可解釋主模型，再視設定套用 sparse correction 與 hybrid residual，最後才輸出指定點或區域的三因子預測。推薦動作不是在只有房間狀態時自動產生；系統必須先取得一個決策採樣範圍，也就是單一指定座標的 point sample，或由多個採樣點、目標區域形成的 cluster sample。接著使用者必須給出 temperature、humidity 與 illuminance 三因子的要求與容許範圍。只有 sample scope 與完整三因子目標都存在時，系統才會對候選動作建立反事實情境並排序；若缺少任一項，流程應停在 point / zone prediction，或由工具回報缺少 sample / target，不產生推薦動作。"
        ),
        code(
            "runtime input: baseline + outdoor conditions + devices + furniture + time\n"
            "→ scenario override and validation\n"
            "→ nominal temperature/humidity/illuminance estimate\n"
            "→ sparse correction and optional hybrid residual\n"
            "→ point or zone prediction\n"
            "→ sample scope: point sample or cluster/zone sample\n"
            "→ three-factor requirement: target + tolerances for T/H/L\n"
            "→ if scope and target are complete: counterfactual actions\n"
            "→ comfort penalty reduction ranking"
        ),
        table(
            ["階段", "輸入", "處理流程", "輸出"],
            [
                [
                    "1. Runtime input",
                    "MCP initialize、web demo、script 或 API 傳入 baseline、外部環境、設備狀態、家具與 elapsed/steady-state。",
                    "使用 `_scenario_with_overrides` 或 MCP registered state 建立目前房間狀態。",
                    "可推論的 scenario state。",
                ],
                [
                    "2. 主模型推論",
                    "scenario state 與查詢點 $\\mathbf{p}$。",
                    "分別計算 $N_T$、$N_H$、$N_L$；溫度處理熱交換，濕度處理水氣交換與除濕，照度處理直射、遮蔽與 single-bounce reflection。",
                    "未套用 residual neural correction 的 base prediction。",
                ],
                [
                    "3. 稀疏校正",
                    "8 顆角落感測器觀測值或已註冊 baseline / calibration state。",
                    "使用角落 residual 進行 active-device power calibration 與 trilinear residual correction，使模型在感測器位置貼近觀測。",
                    "校正後的 $F_T,F_H,F_L$。",
                ],
                [
                    "4. Optional hybrid residual",
                    "若 `use_hybrid_residual=true` 且 checkpoint 存在，使用與訓練相同的特徵欄位。",
                    "對查詢點建立 $\\boldsymbol{\\varphi}$，由 $R_v(\\mathbf{p},t;\\boldsymbol{\\theta}_v)$ 預測 residual，並加回主模型。",
                    "$F_v^{\\text{hybrid}}=F_v+R_v$。",
                ],
                [
                    "5. Point / cluster sample",
                    "指定座標、單點 sample，或由多點/目標區域形成的 cluster sample。",
                    "若是 `sample_point`，直接回傳該點 temperature、humidity、illuminance；若是 zone / cluster summary，對範圍內採樣點做平均或統計。",
                    "目前採樣範圍的 $\\mathbf{q}_{\\mathrm{base}}=(q_T,q_H,q_L)$ 與 estimator 狀態。",
                ],
                [
                    "6. Recommendation precondition",
                    "sample scope、三因子目標 $g_T,g_H,g_L$、容許範圍 $\\delta_T,\\delta_H,\\delta_L$ 與權重 $w_T,w_H,w_L$。",
                    "檢查 sample scope 是否存在，且 temperature、humidity、illuminance 三個目標是否完整；缺少時只回傳估測，不輸出推薦。",
                    "`READY_TO_RANK` 或明確缺項錯誤；缺項時沒有 recommendations 輸出。",
                ],
                [
                    "7. Candidate action simulation",
                    "目前註冊設備與候選動作，例如冷氣冷房/除濕/暖房/送風、設定溫度、風量、左右/上下風向、固定或擺動、開窗或開燈。",
                    "只在 `READY_TO_RANK` 時，對每個候選動作建立反事實 scenario，把裝置 activation 或 metadata 改成候選狀態，重新執行同一條推論流程。",
                    "每個候選動作後的 $\\mathbf{q}_a=(q_T,q_H,q_L)$。",
                ],
                [
                    "8. Recommendation ranking",
                    "目前狀態 $\\mathbf{q}_{\\mathrm{base}}$、動作後狀態 $\\mathbf{q}_a$、舒適目標 $g_m$、容許範圍 $\\delta_m$ 與權重 $w_m$。",
                    "先算目前 penalty，再算每個候選動作後的 penalty；排序分數為 $P(\\mathbf{q}_{\\mathrm{base}})-P(\\mathbf{q}_a)$。",
                    "依預測改善量排序的推薦動作清單、預測改善值與注意事項。",
                ],
            ],
        ),
        paragraph(
            "這條推論流程也說明本研究的推薦動作不是規則表，也不是 LLM 直接猜測，而是由同一套數位孿生模型對候選動作做反事實模擬。若排名第一的動作是開冷氣，代表模型預測在目前 baseline、外部環境、家具遮蔽、設備狀態、指定 sample scope 與三因子目標下，開冷氣後該目標點或目標區域的 comfort penalty 下降最多；但它仍需 5.8 節的 before/after 介入實驗才能證明真實因果改善。"
        ),
        heading("3.8 Hybrid Residual Neural Network 延伸", 2),
        paragraph(
            "雖然主模型已具有可解釋的變數專屬 nominal model 結構，但在設備交互作用、局部照度分布或窗邊複合邊界條件下，仍可能存在系統性殘差。為此，本研究不以純黑盒神經網路取代主模型，而是加入 hybrid residual neural network 作為第二層修正器："
        ),
        math(r"F_v^{\text{hybrid}}(\mathbf{p},t) = F_v(\mathbf{p},t) + R_v(\mathbf{p},t;\,\boldsymbol{\theta}_v)"),
        paragraph("其中 $F_v$ 為第三章前述的 reduced-order 主模型，$R_v$ 則由小型多層感知器近似其殘差。訓練目標定義為："),
        math(r"R_v^*(\mathbf{p},t) = F_v^{\text{truth}}(\mathbf{p},t) - F_v(\mathbf{p},t)"),
        paragraph("其損失函數可表示為："),
        math(r"\mathcal{L}(\boldsymbol{\theta}_v) = \frac{1}{N}\sum_{i=1}^{N}\bigl\|R_v^*(\mathbf{p}_i,t_i) - R_v(\mathbf{p}_i,t_i;\boldsymbol{\theta}_v)\bigr\|^2 + \lambda\|\boldsymbol{\theta}_v\|^2"),
        table(
            ["Hybrid residual 符號", "詳細意義", "訓練或推論角色"],
            [
                ["$F_v^{\\text{hybrid}}$", "套用 neural residual 後的最終 hybrid estimate。", "等於主模型輸出加上神經網路預測的剩餘誤差。"],
                ["$F_v$", "第三章前述 reduced-order 主模型輸出。", "提供可解釋的 baseline estimate。"],
                ["$R_v(\\mathbf{p},t;\\boldsymbol{\\theta}_v)$", "第 $v$ 個環境因素的神經殘差模型。", "由 MLP 預測主模型尚未吸收的 residual。"],
                ["$\\boldsymbol{\\theta}_v$", "第 $v$ 個殘差網路的可訓練參數。", "不同環境因素各自訓練一組參數。"],
                ["$R_v^*$", "理想 residual target。", "由 truth field 減去主模型估計值形成。"],
                ["$N$", "訓練樣本數。", "例如 default split 中的訓練或測試樣本數會分開統計。"],
                ["$i$", "樣本索引。", "從 1 到 $N$。"],
                ["$\\|\\cdot\\|^2$", "平方誤差。", "懲罰預測 residual 與目標 residual 的差距。"],
                ["$\\lambda$", "L2 regularization 權重。", "控制模型參數大小，降低過擬合風險。"],
                ["$\\lambda\\|\\boldsymbol{\\theta}_v\\|^2$", "參數懲罰項。", "鼓勵殘差網路保持較平滑、較小幅度的修正。"],
            ],
        ),
        paragraph(
            "本研究將座標、時間、室內外環境條件、主模型估計值、設備 activation、設備 power 與 influence envelope 作為輸入特徵，分別為溫度、濕度與照度訓練三個小型殘差網路。若啟用頻域去噪，temperature 與 humidity 會先將 $R_v^*$ 沿短時間軌跡做 Fourier low-pass denoising，再送入 MLP 訓練；illuminance 則保留原始 residual target。此設計的目的在於保留主模型可解釋性，同時尊重三因子的物理差異：溫度與濕度 residual 較適合被平滑為低頻趨勢，照度 residual 則需保留由光源、日照、遮蔽與反射造成的短時結構。"
        ),
        heading("3.9 控制動作排序", 2),
        paragraph(
            "本研究不做閉環控制，而是對候選控制動作進行排序。此排序不是無條件推薦，而是在明確的決策採樣範圍與三因子要求下才被定義。採樣範圍可是一個指定座標 point sample，也可是一組由目標區域或使用者選定點組成的 cluster sample；三因子要求則必須同時包含溫度、濕度與照度的目標值與容許範圍。若缺少採樣範圍或缺少任一環境因子的目標，系統只能回傳估測結果，不應輸出候選動作推薦。"
        ),
        paragraph(
            "具體而言，系統先以目前感測資料校正模型，取得採樣範圍目前三因子估計值並計算 baseline comfort penalty。若採樣範圍是單點，$K=1$；若是 cluster 或 target zone，則以 $K$ 個空間採樣點的平均代表該範圍。接著，對每一個候選動作建立反事實情境：例如將冷氣 activation 調至 0.85，同時設定冷房/除濕/暖房/送風模式、目標溫度、fan speed / fan strength、左右與上下出風角度及 fixed/swing 狀態；或將窗戶開啟至 0.7、主要照明調至 0.8，再重新模擬該採樣範圍的溫度、濕度與照度。候選動作分數定義為 baseline penalty 減去動作後預測 penalty，因此分數愈高代表模型預期改善愈大。"
        ),
        paragraph("令決策採樣範圍為："),
        math(r"S=\{\mathbf{p}_k\}_{k=1}^{K}"),
        paragraph("在第 $m$ 個環境因素上，採樣範圍的估計值定義為："),
        math(r"q_m(S)=\frac{1}{K}\sum_{k=1}^{K}F_m(\mathbf{p}_k,t)"),
        paragraph("其中 point sample 是 $K=1$ 的特殊情況；cluster sample 或 target zone 則是 $K>1$ 的空間聚合。三因子目標向量與容許範圍分別寫成："),
        math(r"\mathbf{g}=(g_T,g_H,g_L),\qquad \boldsymbol{\delta}=(\delta_T,\delta_H,\delta_L)"),
        paragraph("comfort penalty 對每個因子使用目標值與容許範圍計算，可寫成："),
        math(r"P(\mathbf{q}(S))=\sum_{m\in\{T,H,L\}} w_m \max\left(0,\frac{|q_m(S)-g_m|-\delta_m}{\delta_m}\right)"),
        paragraph("候選動作 $a$ 的排序分數定義為："),
        math(r"\mathrm{score}(a)=P(\mathbf{q}_{\mathrm{base}}(S))-P(\mathbf{q}_{a}(S))"),
        table(
            ["控制排序符號", "詳細意義", "排序中的角色"],
            [
                ["$m$", "comfort penalty 中的環境因素索引。", "$m\\in\\{T,H,L\\}$，分別對應溫度、濕度與照度。"],
                ["$S$", "推薦排序使用的決策採樣範圍。", "可為單一 point sample，也可為 cluster sample 或 target zone。"],
                ["$K$", "採樣範圍中的點數。", "$K=1$ 代表單點；$K>1$ 代表區域或群集平均。"],
                ["$\\mathbf{p}_k$", "採樣範圍中的第 $k$ 個座標點。", "每個點都在同一個房間座標系中。"],
                ["$\\mathbf{q}(S)$", "由採樣範圍 $S$ 聚合出的三因子估計向量。", "可寫成 $(q_T(S),q_H(S),q_L(S))$。"],
                ["$q_m(S)$", "採樣範圍中第 $m$ 個環境因素的估計值。", "由目前模型或反事實動作模擬後對 $S$ 聚合得到。"],
                ["$g_m$", "第 $m$ 個環境因素的舒適目標值。", "例如目標溫度、目標濕度或目標照度。"],
                ["$\\delta_m$", "第 $m$ 個環境因素的可接受容許範圍。", "偏差小於此範圍時不產生 penalty。"],
                ["$w_m$", "第 $m$ 個環境因素的權重。", "用來表示溫度、濕度與照度在決策中的重要程度。"],
                ["$P(\\mathbf{q}(S))$", "採樣範圍 $S$ 的 comfort penalty。", "值越小表示該點或群集越接近舒適目標。"],
                ["$\\mathbf{q}_{\\mathrm{base}}(S)$", "尚未套用候選動作時，採樣範圍 $S$ 的目前狀態估計。", "用來計算 baseline penalty。"],
                ["$\\mathbf{q}_a(S)$", "套用候選動作 $a$ 後，採樣範圍 $S$ 的反事實估計。", "由模型重新模擬得到，不是實際控制後的量測值。"],
                ["$\\mathrm{score}(a)$", "候選動作 $a$ 的改善分數。", "分數越高，表示模型預期該動作越能降低 comfort penalty。"],
            ],
        ),
        paragraph(
            "若預測值落在容許範圍內，該因子 penalty 為 0；若超出容許範圍，則以超出量除以容許範圍後乘上對應權重。此設計避免微小偏差被過度懲罰，也使不同量綱的溫度、濕度與照度可被加總。需要注意的是，這裡的推薦排序屬於 model-based counterfactual simulation，並不等同於已完成實際控制驗證；而且在數學上只有當 $S$、$\\mathbf{g}$ 與 $\\boldsymbol{\\delta}$ 都完整時才有定義。"
        ),
        heading("3.10 方法選擇理由與限制", 2),
        paragraph(
            "為避免方法堆疊流於任意組合，本研究將每一個方法都對應到明確的研究需求。整體選擇邏輯是：先用可解釋的變數專屬 nominal model 描述室內溫度、濕度與照度的主要趨勢，再用稀疏感測器的 residual correction 修正房間現況，最後才以資料驅動模型處理主模型無法完整描述的剩餘誤差。表 3-5 整理各方法的使用原因、解決問題與限制。"
        ),
        table(
            ["方法", "使用原因", "解決的問題", "限制或注意事項"],
            [
                [
                    "Indoor Baseline",
                    "需要一個設備作用與感測器修正之前的室內起始狀態。",
                    "將 T0、H0、L0 作為溫度、濕度與照度場的共同參考點，避免模型每次都從任意絕對值重新估計。",
                    "若 baseline 來自預設值或使用者輸入而非實測前置資料，後續估計會帶有基準偏差；因此它不是比較方法中的 IDW 或 persistence baseline。",
                ],
                [
                    "變數專屬 nominal model",
                    "溫度、濕度與照度的物理特性不同，不能用同一組 bulk/local 公式硬套三個變數。",
                    "讓溫度處理熱交換與垂直梯度，濕度處理除濕與外氣交換，照度處理直射、環境光與反射。",
                    "此模型是 reduced-order approximation，不等同於 CFD、完整濕空氣熱力模型或光線追跡。",
                ],
                [
                    "Dynamic activation",
                    "冷氣、開窗與照明的影響不會在動作發生瞬間完全達到穩態。",
                    "用 Aj(t)=aj(1-exp(-t/tauj)) 表示設備影響隨時間漸進，使 before/after 與短時間模擬更合理。",
                    "需要指定或校正時間常數 tauj；若設備實際響應高度非線性，單一時間常數只能近似主要趨勢。",
                ],
                [
                    "Influence envelope",
                    "設備效果會隨距離、方向與遮蔽而衰減，需要比全室均勻假設更細的空間描述。",
                    "以距離衰減、方向投影與遮蔽係數描述局部作用範圍，讓冷氣出風口、窗邊與燈具附近可呈現不同影響強度。",
                    "無法解析亂流、微尺度陰影與複雜反射；其目的在於提供可計算且可校正的低階空間先驗。",
                ],
                [
                    "Active-device power calibration",
                    "設備預設功率與實際房間反應可能不同，需要由感測器 residual 回推修正。",
                    "用已知啟動設備的觀測誤差調整效果強度，降低模型參數與實際場之間的落差。",
                    "若多個設備同時啟動且影響高度共線，校正可能病態；因此需要配合事件紀錄與感測器位置檢查。",
                ],
                [
                    "Trilinear residual correction",
                    "只有 8 個採集點時，不能聲稱完整知道全場，但可以在低階平滑假設下推估角點包圍盒內的 residual。",
                    "用 8 點角點 residual 建立三線性修正場，使模型在感測器位置貼合觀測值，並可給出低階場的誤差界線。",
                    "它不能證明高頻局部尖峰被重建；因此本文僅主張接近主要空間趨勢，而非完全等同真實連續場。",
                ],
                [
                    "Least-squares impact learning",
                    "非連網裝置沒有 API 回報狀態，只能從事件前後的感測變化學習其影響。",
                    "以 before/after delta 建立線性觀測方程，估計未知裝置對溫度、濕度與照度的方向與大小。",
                    "需要事件可分離且雜訊受控；若多個未知動作重疊，學到的是混合效果而非單一裝置效果。",
                ],
                [
                    "One-bounce diffuse reflection",
                    "照度若只看直射光，會低估牆面與家具反射造成的間接照明。",
                    "用一次漫反射近似補上間接光，使窗戶與燈具之外的區域不會被估得過暗。",
                    "此方法不是完整 radiosity 或 ray tracing；反射率與遮蔽幾何仍需以簡化參數表示。",
                ],
                [
                    "Hybrid residual neural network",
                    "可解釋主模型仍可能留下系統性殘差，需要資料驅動方式補償。",
                    "讓小型 MLP 學習 truth field 與主模型估計值之差，在保留主模型結構的同時改善殘差。",
                    "需要獨立驗證資料避免過擬合；它是第二層修正器，不是用黑盒模型取代物理先驗。",
                ],
                [
                    "Fourier low-pass denoising",
                    "溫度與濕度受熱容量、空氣混合與水氣交換影響，時間響應相對平滑，residual 中的高頻成分較常是短時雜訊或擾動。",
                    "在頻域抑制高頻成分並保留低頻趨勢，讓 temperature/humidity residual target 更接近可重現的環境變化。",
                    "本文不將它套用於照度 residual，因為照度受燈具開關、日照、遮蔽、陰影與反射影響，快速變化本身可能是有物理意義的訊號。",
                ],
                [
                    "IDW baseline",
                    "需要一個簡單、無設備物理先驗的比較對象，才能量化本研究模型的附加價值。",
                    "用距離加權插值作為傳統稀疏感測場估計基準，對照 device-aware model 的改善幅度。",
                    "IDW 不理解設備狀態、方向、時間響應或遮蔽；它是比較 baseline，不是本文主模型。",
                ],
                [
                    "公開資料集 task-aligned benchmark",
                    "本研究資料規模有限，需要用公開資料補強方法在外部資料上的可比較性。",
                    "將公開資料切成與本研究相近的預測或重建任務，檢查模型相對於 baseline 的表現。",
                    "公開資料通常缺少本研究的 3D 座標、8 點拓樸與裝置事件，因此只能支持任務層級比較，不能直接證明完整三維場重建。",
                ],
                [
                    "Web demo 與 MCP 介面",
                    "研究成果需要可展示、可查詢，也需要讓教授或使用者能看到模型輸入與輸出如何連動。",
                    "提供 3D 場視覺化、名詞解釋、公開資料比較與 tool-based 查詢，協助驗證展示與口試說明。",
                    "它是服務與展示層，不是主要科學貢獻；論文主張仍需回到模型、實驗與誤差分析。",
                ],
            ],
        ),
        paragraph(
            "因此，若被問到「為什麼不用單純插值」或「為什麼不用同一公式描述三個因子」，本研究的回答是：單純插值缺少設備與時間響應資訊，而單一公式會忽略溫度、濕度與照度的物理差異。本研究採用分層方法，是為了在可解釋性、稀疏感測可行性、展示互動性與資料驅動修正之間取得平衡。"
        ),
        page_break(),
        heading("第四章 系統實作與服務介面", 1),
        heading("4.1 Python 原型", 2),
        paragraph(
            "本研究原型以 Python 實作，核心模組包含 entities、model、scenarios、learning、hybrid_residual、baselines、recommendations、service、mcp_server 與 web_demo。系統採零外部依賴設計，方便在本地環境快速執行與展示。"
        ),
        table(
            ["模組", "功能"],
            [
                ["entities.py", "定義房間、設備、感測器、區域與動作資料結構"],
                ["model.py", "建立三因子場、設備影響函數與感測器校正"],
                ["scenarios.py", "定義標準情境與窗戶矩陣情境"],
                ["learning.py", "由前後感測資料學習非連網裝置影響係數"],
                ["hybrid_residual.py", "訓練與套用 hybrid residual neural network"],
                ["baselines.py", "建立 IDW baseline"],
                ["service.py", "提供 MCP、Gemma bridge 與 web demo 共用服務介面"],
                ["web_demo.py", "提供本地可旋轉 3D web demo、Term Glossary 與公開資料集比較展示"],
            ],
        ),
        heading("4.2 MCP Tools", 2),
        paragraph("本地 MCP server 目前保留五個互動流程 tools："),
        bullets(
            [
                "initialize_environment：初始化 MCP session 的 runtime state，包含 base scenario、室內 baseline、外部環境、註冊設備、家具阻擋物、預設時間與 estimator 選擇。",
                "sample_point：估計指定座標在特定 elapsed minutes 或 steady state 下的 temperature、humidity 與 illuminance，用於補足非感測點狀態。",
                "learn_impacts：針對某個非連網設備建立 before/after observation record；只有同時具備開啟前與開啟後的真實感測讀值時，才計算 learned impact coefficients。",
                "run_window_direct：直接輸入外部溫度、濕度、日照與開窗比例，執行窗戶影響模擬，並可更新目前 MCP session 的外部環境。",
                "rank_actions：輸入指定座標 sample 與完整目標三因子值，根據目前註冊設備產生候選操作並依 comfort penalty 改善量排序；缺少 sample 或任一三因子目標時不產生推薦。",
            ]
        ),
        paragraph(
            "其中 learn_impacts 的資料化流程可分為 start、record 與 finish 三步。start 階段輸入的動作不是單純的 action name，而是要套用到裝置上的 `device_state`；例如冷氣可包含 activation、模式、設定溫度、風速或風量、水平/垂直出風角度與 fixed/swing 擺動設定。系統會把 `device_state` 合併到目前註冊設備，形成新的 `device_specs`，並以 `learning_record_id` 建立一筆 `RECORDING` 狀態的事件紀錄。record 內容保存當時的 device_name、device_state、device_specs、室內 baseline、外部邊界、家具遮蔽、elapsed time、sampling mode、before_observations 與 optional note。finish 階段再輸入同一批感測器的 after_observations，系統以 after minus before 取得各感測器的 $\\Delta T,\\Delta H,\\Delta L$，並以設備 influence envelope 作為設計矩陣估計 learned_device_impacts。若缺少 before 或 after readings，工具只保留事件紀錄，不輸出係數。"
        ),
        paragraph("表 4-2 learn_impacts 事件記錄欄位"),
        table(
            ["欄位", "資料內容", "用途"],
            [
                ["learning_record_id", "每次 start 產生的唯一編號", "finish 時把 after observations 接回同一筆事件"],
                ["device_name", "被操作的設備名稱，例如 ac_main", "指定要學習哪個非連網裝置"],
                ["device_state", "activation、kind、power 與 AC mode/setpoint/fan/airflow 等操作狀態", "描述這次實際套用的裝置動作"],
                ["device_specs", "合併 device_state 後的完整設備清單", "後續 sample 與 impact learning 使用的 runtime device state"],
                ["baseline / environment", "室內溫濕照度基準與室外溫濕度、日照", "保留事件發生時的環境條件"],
                ["furniture / furniture_overrides", "家具與遮蔽物狀態", "保留當時的空間遮蔽條件"],
                ["elapsed_minutes / sampling_mode", "裝置作用時間或 steady-state 設定", "決定 dynamic activation 與 influence envelope"],
                ["before_observations / after_observations", "同一批感測器前後的 temperature、humidity、illuminance", "計算 $\\Delta y = y_{\\mathrm{after}}-y_{\\mathrm{before}}$"],
                ["result", "metric_coefficients、sensor_mae、sensor_observation_delta", "儲存學到的裝置影響係數與誤差摘要"],
            ],
        ),
        paragraph(
            "其中 initialize_environment 是 MCP runtime 的起點，不是單純把場景名稱設為 idle。它會建立後續工具共用的 session state，因此必須清楚區分哪些項目是在初始化時註冊，哪些是後續查詢才輸入。表 4-3 列出目前初始化可設定的內容。"
        ),
        paragraph("表 4-3 initialize_environment 可設定內容"),
        table(
            ["欄位", "可設定內容", "後續影響"],
            [
                ["scenario_name", "選擇基礎情境，例如 idle 或其他內建情境。", "決定標準房間模板、內建設備、內建家具與基礎拓樸。"],
                ["baseline.indoor_temperature", "起始室內溫度，預設 29.0°C。", "作為溫度場 $T_0$，後續冷氣與窗戶影響都在此基準上疊加。"],
                ["baseline.indoor_humidity", "起始室內相對濕度，預設 67.0%。", "作為濕度場 $H_0$，決定除濕與外氣交換方向。"],
                ["baseline.base_illuminance", "起始室內背景照度，預設 90.0 lux。", "作為照度場 $L_0$，窗戶日照、燈具與反射項會疊加其上。"],
                ["environment.outdoor_temperature", "室外溫度，預設 33.0°C。", "影響窗戶造成的熱交換。"],
                ["environment.outdoor_humidity", "室外相對濕度，預設 74.0%。", "影響開窗後室內濕度上升或下降。"],
                ["environment.sunlight_illuminance", "室外日照照度，預設 32000 lux。", "影響窗戶直射光與 single-bounce reflection 的光源強度。"],
                ["environment.daylight_factor", "日光進入室內的比例係數，預設 0.95。", "調整外部日照轉成室內照度的強度。"],
                ["devices", "註冊或覆寫 ac_main、window_main、light_main，也可新增 custom ac/window/light。常用欄位包含 name、kind、activation、position、orientation、influence_radius、response_time_minutes、power、metadata；冷氣可加 ac_mode、target_temperature、fan_speed、fan_strength、horizontal_mode、horizontal_angle_deg、vertical_mode、vertical_angle_deg 與 swing 週期/角度序列。", "後續 sample_point、learn_impacts 與 rank_actions 會依目前註冊設備計算。"],
                ["replace_existing_devices", "若為 true，未列入 devices 的內建設備會被標記移除。", "可建立只包含指定設備的 runtime 環境。"],
                ["furniture", "註冊或覆寫 cabinet_window、sofa_main、table_center，也可用 min_corner/max_corner 新增自訂家具或遮蔽物。", "影響照度遮蔽、單次反射、冷氣/窗戶可見性與混合懲罰。"],
                ["elapsed_minutes", "後續工具未指定時間時使用的預設 elapsed time，預設 18 分鐘。", "影響 dynamic activation 與指定時間點的 point sample。"],
                ["steady_state_minutes", "後續使用 steady_state: true 時的代表時間，預設 120 分鐘。", "用於查詢接近準穩態後的三因子估計。"],
                ["use_hybrid_residual", "是否預設使用 hybrid residual corrected field。", "影響後續 sample_point 與 rank_actions 的估計器選擇；若無 checkpoint 則回到主模型。"],
            ],
        ),
        paragraph(
            "因此，若教授問「initialize 到底初始化什麼」，可回答：它是在 MCP session 中註冊一個可被後續工具共用的房間 runtime state，包含室內初始基準、外部邊界條件、目前設備狀態、家具遮蔽狀態、查詢時間預設值與估計器選擇。它尚未代表完成實驗驗證，也不是重新建立任意 BIM 幾何；目前仍以本研究標準單房間拓樸為基礎。"
        ),
        paragraph(
            "早期用於驗證或展示的 list_scenarios、run_scenario、compare_baseline 與 run_window_matrix 仍可由實驗腳本或 web demo 使用，但不再作為 MCP 對外工具。此重構使 MCP 的定位更接近實際 runtime：先註冊環境，再查點位、記錄學習資料、輸入窗戶資料與排序控制動作。"
        ),
        heading("4.3 Gemma/Ollama Bridge", 2),
        paragraph(
            "本研究以本機 Ollama 上之 Gemma 模型作為語言介面，並以 Python bridge 串接數位孿生服務。實測顯示，本機 Gemma 可透過 Ollama 進行 tool calling；但 MCP 支援本質上來自主機端或 client/runtime 層，而非模型權重本身。因此本研究採用的設計是：由 Gemma 將自然語言請求轉為工具選擇，Python bridge 執行數位孿生服務或 MCP server 所提供的工具，再把工具輸出回送給 Gemma 生成最終回答。這樣的設計比直接宣稱模型原生支援 MCP 更準確，也更符合目前本地 AI agent 的實作方式。"
        ),
        heading("4.4 Web Demo 與展示輔助介面", 2),
        paragraph(
            "Web demo 以 idle 房間背景為基礎，透過 ac_main、window_main 與 light_main checkbox 組合設備狀態，不使用下拉式情境選單。3D 預覽可拖曳旋轉與縮放，並以牆面橫條標示冷氣、牆面矩形標示窗戶、點狀標記表示照明。Metric 亦以勾選式控制切換 temperature、humidity 與 illuminance。左側固定欄位提供 Indoor Baseline 設定，使室內基準溫度、濕度與照度可直接調整；窗戶區則保留季節、天氣與時段 preset，並允許使用者手動覆寫外部溫度與開窗比例。互動式 3D 預覽上方另提供時間軸與播放控制，可觀察系統從啟動到接近準穩態的過程。最新版本的 Web UI 另外提供 estimator toggle，可在主模型與 hybrid residual corrected field 之間切換，並同步更新 target zone、recommendation ranking、baseline comparison、impact panel、3D volume、point sample 與 timeline。"
        ),
        paragraph(
            "為了讓口試或展示時能直接解釋技術名詞，Web demo 新增 Term Glossary。此區塊列出 sparse sensing、spatial digital twin、IDW、MAE、RMSE、LOO、hybrid residual correction、task-aligned benchmark、structured prior 與 linear readout head 等詞彙，頁面文字中的關鍵術語也會自動加上 hover/tap tooltip。此設計的目的不是改變模型本身，而是降低展示時對聽眾背景知識的依賴，使模型、資料與指標能在同一頁面中被說明。"
        ),
        paragraph(
            "Web demo 也新增 Public Dataset Comparison 區塊。此區塊讀取 outputs/data/public_benchmarks/sml2010_hybrid_twin_comparison.json 與 outputs/data/public_benchmarks/cu_bems_hybrid_twin_comparison.json，不重新計算論文數字；後端路由為 /api/public_benchmarks。頁面會依資料集列出 benchmark mode、資料量、unsupported claims、執行流程說明，以及每個 task/horizon/target 的 MAE 對比與最佳方法。展示時應強調：公開資料集比較只支援 shared observable tasks，不能被解讀為 full 3D dense-field validation。"
        ),
        paragraph("表 4-4 列出 Web demo 最新展示輔助區塊。"),
        table(
            ["區塊", "呈現內容", "展示用途"],
            [
                ["Term Glossary", "常見研究名詞與 inline tooltip", "讓聽眾即時理解模型、指標與資料比較術語"],
                ["Public Dataset Comparison", "SML2010、CU-BEMS 的任務流程、限制與 MAE 對比", "說明公開資料比較如何執行，以及哪些主張不可由公開資料支持"],
                ["/api/public_benchmarks", "輸出 demo 使用的公開 benchmark JSON 摘要", "使 demo、論文表格與既有實驗輸出維持一致資料來源"],
            ],
        ),
        page_break(),
        heading("第五章 模擬案例與結果分析", 1),
        heading("5.1 標準情境設定", 2),
        paragraph(
            "本研究建立 8 組標準情境，包含無設備作用、僅冷氣、僅開窗、僅照明、冷氣與窗戶、窗戶與照明、冷氣與照明，以及三者同時作用。每組情境均輸出場重建誤差、區域平均值、感測器校正效果、IDW baseline 比較、非連網裝置影響學習與推薦排序。"
        ),
        paragraph(
            "表 5-1 的最佳推薦表示在目前 comfort target 與模型估測下，哪一個候選動作具有最高預測改善量。此表用來檢查推薦模組是否能依情境輸出合理排序，但仍屬模擬與反事實評估；若要宣稱推薦動作在真實房間中有效，需依 5.8 節所述介入式驗證方法量測實際改善量。"
        ),
        paragraph(
            "為避免將不同資料來源支持的主張混在一起，本章採用分層驗證邏輯。8 組標準情境、消融實驗與 leave-one-scenario-out hybrid residual 測試用於驗證受控條件下的完整 3D 場重建與模型元件貢獻；48 組窗戶矩陣用於檢查外部邊界條件敏感度；bedroom_01 真實快照用於檢查稀疏感測校正是否能改善未參與校正的 pillow 參考點；SML2010 與 CU-BEMS 僅作 public task-aligned benchmark，用於外部資料的相容子任務比較。換言之，synthetic benchmark 回答「完整場是否能在受控真值下重建」，真實快照回答「校正管線是否能吸收真實觀測並改善保留點」，公開資料集回答「模型在相容任務上的外部定位」，推薦介入實驗才回答「建議動作是否真的造成舒適度改善」。"
        ),
        paragraph(
            "實驗標記總覽。本章後續以 E1--E9 標記實驗或驗證項目。E1--E6 為 controlled simulation 或 model robustness experiment，E7 為真實臥室 sparse-calibration check，E8 是尚未完成實測的推薦介入驗證方案，E9 為 public task-aligned benchmark。Web demo、MCP 與可旋轉 3D 展示屬於服務介面與展示輔助，不列為獨立量化實驗。"
        ),
        table(
            ["標記", "名稱", "資料來源", "主要比較或輸出", "可支持主張", "限制"],
            [
                ["實驗 E1", "標準情境 full-field 重建", "8 組 controlled synthetic scenarios", "Base field MAE、zone MAE、sensor MAE", "受控條件下可重建完整 3D 場", "非真實 dense ground truth"],
                ["實驗 E2", "IDW baseline 比較", "E1 同一組情境與 8 顆角落感測器", "Base model 與 IDW field MAE", "設備先驗、校準與場模型比純空間插值更適合有設備作用情境", "IDW 只是無設備語意 baseline，不代表所有空間插值上限"],
                ["實驗 E3", "消融與可重現性", "E1 同一 synthetic setup", "raw、no reflection、no calibration、no trilinear、full base", "說明反射、校準與 trilinear correction 的個別貢獻與限制", "trilinear 目標是感測點一致性，不保證 dense MAE 單調下降"],
                ["實驗 E4", "非連網裝置影響學習", "controlled before/after synthetic observations", "learned impact coefficients、推薦排序", "可由環境變化學出裝置影響方向與相對強度", "不是實測因果控制"],
                ["實驗 E5", "窗戶矩陣與 direct input", "48 組 season/weather/time/window cases", "window-zone 與 center-zone estimates", "外部溫濕度、日照與開窗比例會改變估測場", "不是實際天氣部署或長期監測"],
                ["實驗 E6", "Hybrid residual robustness", "default split、no-Fourier、8-fold leave-one-scenario-out", "hybrid field MAE、train/test samples", "標準情境 family 內 residual 可學習，且不是只依賴單一切分", "不代表任意房間或任意家具配置泛化"],
                ["實驗 E7", "真實臥室快照 sparse calibration", "bedroom_01，7 天 28 snapshots", "raw vs corrected pillow MAE", "真實稀疏觀測可改善未參與校正的 pillow 參考點", "只有單一 pillow reference，沒有 dense 3D ground truth"],
                ["驗證方案 E8", "推薦動作 before/after 介入", "尚待實測", "actual improvement、success rate、top-1 regret", "定義未來如何驗證推薦是否真的造成改善", "目前只完成 protocol，不列為已完成結果"],
                ["實驗 E9", "Public task-aligned benchmark", "SML2010、CU-BEMS", "persistence、linear regression、本研究 mapped readout", "提供外部資料相容子任務上的定位與比較", "不能宣稱 full 3D field、8-corner calibration 或完整非連網裝置學習"],
            ],
        ),
        paragraph(
            "因此，本文後續提到「實驗」時，E1--E7 與 E9 代表已產生數值輸出的實驗或 benchmark；E8 僅代表推薦控制的實測 protocol；Web demo 與 MCP 則屬展示與服務介面，不直接作為量化實驗證據。"
        ),
        image(
            "outputs/figures/architecture/驗證與實驗流程圖.svg",
            "圖 5-1 驗證與實驗流程。此圖說明標準情境如何經由 truth adjustment、合成觀測、校正估測、baseline 比較與輸出摘要，形成第五章的實驗結果。",
            asset_name="fig_5_1_validation_flow",
        ),
        paragraph("表 5-1 標準情境結果摘要"),
        table(
            ["情境", "中央溫度", "中央濕度", "中央照度", "最佳推薦"],
            [
                ["idle", "28.84", "67.60", "90.00", "ac_and_light"],
                ["ac_only", "25.56", "65.75", "90.00", "turn_on_light"],
                ["window_only", "29.51", "68.42", "214.60", "ac_and_light"],
                ["light_only", "29.11", "67.60", "452.99", "turn_on_ac"],
                ["all_active", "26.39", "66.34", "478.82", "turn_on_ac"],
            ],
        ),
        heading("5.2 【實驗 E1】標準情境場重建誤差", 2),
        paragraph(
            "本研究採用平均絕對誤差（Mean Absolute Error, MAE）作為主要精度指標，定義如下，其中 ŷᵢ 為模型在第 i 個網格點的預測值，yᵢ 為對應的模擬基準值，n 為評估點總數。MAE 直接反映預測值與基準值之間的平均偏差幅度，數值愈低代表場重建愈準確，且因不進行平方放大，對少數離群點較不敏感，適合作為室內場重建的評估基準。"
        ),
        math(r"\text{MAE} = \frac{1}{n}\sum_{i=1}^{n}\left|\hat{y}_i - y_i\right|"),
        paragraph(
            "8 組標準情境中，平均溫度 MAE 為 0.0474，平均濕度 MAE 為 0.1765，平均照度 MAE 為 2.0269；各因子的最大 MAE 分別為 0.0481、0.1770 與 2.2990。照度 MAE 仍高於溫度與濕度，主要原因是照度場受燈具位置、窗戶日照、遮蔽與方向性影響較大，且數值尺度遠高於溫度與濕度。"
        ),
        paragraph(
            "這表示新增的反射公式補足了牆面、地板、天花板與家具造成的間接回填亮度，使非直射區域不再被系統性低估。另一方面，溫度與濕度指標維持在小幅誤差範圍內，也說明照度反射項主要作用在預期的 illuminance 路徑，而沒有不必要地擾動其他兩個環境因素。"
        ),
        image(
            "outputs/figures/all_active_temperature_3d.svg",
            "圖 5-2 三裝置同時作用（all\\_active）之溫度場 3D 點雲視圖。每點為一個 16×12×6 網格樣本，顏色由藍綠（低溫）至橙紅（高溫）映射溫度分布。冷氣區域明顯偏藍，靠窗與靠燈區域則居溫度中高端。",
            asset_name="fig_5_2_all_active_temp_3d",
        ),
        image(
            "outputs/figures/ac_only_temperature_3d.svg",
            "圖 5-3 僅冷氣作用（ac\\_only）之溫度場 3D 點雲視圖。冷氣氣流影響區域（後牆靠左側）溫度明顯下降，距冷氣較遠的靠窗區域溫度相對較高，展示溫度 nominal model 對全室熱響應與局部梯度的同時建模能力。",
            asset_name="fig_5_3_ac_only_temp_3d",
        ),
        image(
            "outputs/figures/light_only_illuminance_3d.svg",
            "圖 5-4 僅燈具作用（light\\_only）之照度場 3D 點雲視圖。燈具正下方的測點照度最高（黃橙色），底層四角與遠端則由間接反射賦予少量回填亮度，顏色實現正確的照度衰減樣態。",
            asset_name="fig_5_4_light_only_illum_3d",
        ),
        heading("5.3 【實驗 E2】IDW Baseline 比較", 2),
        paragraph(
            "IDW（Inverse Distance Weighting，反距離加權插值）是最基本的空間插值法：給定 8 顆角落感測器的量測值，對任一查詢點以距離的倒數為權重加權平均。此方法不需要任何關於設備位置或物理模型的知識，僅依賴量測點的空間分布進行推算。本節以 IDW 作為零成本 baseline，驗證本研究模型加入設備影響函數、power scale 校準與 trilinear residual correction 後的實質改善幅度。"
        ),
        paragraph(
            "表 5-2 列出 8 組情境下，IDW 與本研究模型（base model）的 field MAE 及改善比例。"
        ),
        table(
            ["情境", "因子", "本研究 MAE", "IDW MAE", "改善 (%)"],
            [
                ["idle",        "溫度",  "0.0470", "0.1242", "62.2%"],
                ["idle",        "濕度",  "0.1762", "0.4656", "62.2%"],
                ["idle",        "照度",  "1.7625", "1.3210", "−33.4% ▲"],
                ["ac\\_only",   "溫度",  "0.0481", "0.2536", "81.0%"],
                ["ac\\_only",   "照度",  "1.7625", "1.3210", "−33.4% ▲"],
                ["window\\_only","照度", "2.1121", "59.2620","96.4%"],
                ["light\\_only", "溫度", "0.0470", "0.1232", "61.9%"],
                ["light\\_only", "照度", "2.2990", "69.7248","96.7%"],
                ["window\\_light","照度","2.0877","110.5221","98.1%"],
                ["ac\\_light",  "照度",  "2.2537", "65.3733","96.6%"],
                ["all\\_active","溫度",  "0.0479", "0.1896", "74.7%"],
                ["all\\_active","照度",  "2.0525", "93.5832","97.8%"],
            ],
        ),
        paragraph(
            "結果說明如下。在溫度與濕度方面，所有情境的改善率均達 61–81%，原因是本研究模型加入冷氣對全室與局部溫濕度的設備影響函數，使有設備的情境（ac\\_only、ac\\_window、ac\\_light、all\\_active）能正確描述冷氣區域的降溫效果，而純 IDW 因僅依靠角落感測值做全場推算，對冷氣作用區域估計不準。"
        ),
        paragraph(
            "在照度方面，有光源（窗戶或燈具）的情境改善幅度極大（96–99%），原因是照度具有強烈的點源衰減特性：燈具正下方的照度極高，角落卻很低，IDW 用角落感測值插值中央會嚴重低估；而本研究模型使用直接照度公式加 single-bounce diffuse reflection，能正確重建燈具中心的高照度峰值。對照地，idle 與 ac\\_only（無窗無燈）的照度改善為負，這是預期現象：在無主動光源情境下，照度全場平坦，IDW 插值本身即有合理表現，本研究模型的設備驅動照度項此時不起作用，反而略高於 IDW 的平坦估計。此結果反映本研究照度建模設計的目標：在有光源時大幅提升精度，而非在無光源情境下多此一舉。"
        ),
        paragraph(
            "值得注意的是，本研究目前的照度估計完全依賴物理模型推算（設備位置、功率、反射係數），並未使用任何實測照度感測器回饋。若系統部署時，角落感測器本身即具備照度量測能力（例如採用光照感測元件的多合一環境感測器），則可將實測角落照度值引入 trilinear residual correction，使模型的照度殘差直接對齊真實量測，從根本上消除物理假設帶來的系統性偏差。換言之，本研究現有的照度誤差並非方法的根本限制，而是感測器配置選擇的結果，一旦取得真實光照量測資料，即可透過既有的 residual correction 管線加以修正，實現更高精度的照度場重建。"
        ),
        heading("5.4 【實驗 E3】消融分析與可重現性補強", 2),
        paragraph(
            "為回應 IEEE conference 審稿時可能關注的 overfitting 與 synthetic leakage 問題，本研究新增 submission readiness 實驗。所有消融實驗均使用相同的 6.0 m × 4.0 m × 3.0 m 房間、8 顆角落感測器、16×12×6 網格、8 組標準情境、18 分鐘 settling interval，以及固定的 deterministic truth adjustment。合成觀測只由 truth sensor prediction 加上固定 index-based perturbation 產生：temperature 加上 0.08((i mod 4) − 1.5)，humidity 加上 0.3((i mod 4) − 1.5)，illuminance 加上 3.0((i mod 4) − 1.5)。此設計使每次實驗可完全重現，也避免把 nominal estimator 的輸出直接當作訓練標籤。"
        ),
        paragraph(
            "表 5-3 顯示各消融版本在 8 組標準情境上的平均 field MAE。raw nominal 表示不使用角落感測回饋；no reflection 移除照度 single-bounce diffuse reflection；no calibration 移除 active-device power calibration；no trilinear 保留 power calibration 但不套用 trilinear residual correction；full base 則為目前主模型。結果顯示，移除設備感測回饋或反射近似會明顯增加照度誤差；no trilinear 在本組 synthetic dense-field MAE 上反而較低，表示 trilinear correction 更應被解讀為角落感測一致性修正，而非保證所有 synthetic dense field 指標皆單調下降的步驟。"
        ),
        table(
            ["Variant", "Temperature", "Humidity", "Illuminance"],
            [
                ["IDW baseline", "0.1723", "0.4633", "54.9052"],
                ["raw nominal", "0.1312", "0.0842", "3.5183"],
                ["no reflection", "0.0472", "0.1762", "2.4296"],
                ["no calibration", "0.0493", "0.1772", "3.3631"],
                ["no trilinear", "0.0446", "0.0274", "0.9849"],
                ["full base", "0.0474", "0.1765", "2.0269"],
            ],
        ),
        paragraph(
            "因此，本研究在後續 hybrid residual 評估中不只報告單一 6/2 held-out split，也加入 leave-one-scenario-out cross-validation、train/test sample count 與 no-Fourier 對照，以降低僅憑單一切分得到過度漂亮結果的風險。可重現腳本包含 scripts/run_demo.py、scripts/run_hybrid_residual_experiment.py 與 scripts/run_submission_readiness_experiments.py。"
        ),
        heading("5.5 【實驗 E4】非連網裝置影響學習", 2),
        paragraph(
            "在 ac_only 情境中，模型學得冷氣對 temperature 的係數為負，對 humidity 的係數亦為負，對 illuminance 則接近零，符合冷氣降溫與弱除濕的模型假設。在 light_only 情境中，照明主要提升 illuminance，並帶來少量正向熱效應。這些結果顯示，即使裝置本身不回報狀態，仍可由環境感測變化估計其影響方向與相對強度。"
        ),
        heading("5.6 【實驗 E5】窗戶時段、天氣、季節矩陣與直接輸入", 2),
        paragraph(
            "本研究新增 48 組窗戶矩陣情境，組合 4 個時段、3 種天氣與 4 個季節。此矩陣可作為外部環境變數敏感度分析，用於說明窗戶在不同外部條件下對靠窗區與中心區的溫度、濕度與照度影響。"
        ),
        paragraph(
            "除列舉矩陣外，系統亦支援窗戶 direct input 模式。使用者可直接提供外部溫度、外部濕度、外部日照照度、開窗比例，以及可選的室內基準溫濕度。此模式適合接入即時天氣資料、手動量測資料或使用者指定條件，不必先將外部條件離散化為季節、天氣與時段分類。"
        ),
        paragraph("表 5-4 列出窗戶矩陣中的三個代表情境。"),
        table(
            ["情境", "外部溫度", "外部濕度", "外部日照", "窗戶區照度"],
            [
                ["window_summer_sunny_noon", "37.0", "71.0", "36000.0", "243.7090"],
                ["window_winter_rainy_night", "11.0", "78.0", "15.2", "68.9740"],
                ["window_spring_cloudy_morning", "21.5", "70.0", "5005.0", "93.2172"],
            ],
        ),
        heading("5.7 【實驗 E6】Hybrid Residual Neural Network 結果", 2),
        paragraph(
            "在目前預設的 held-out 測試設定下，hybrid residual neural network 以 6 個情境作為訓練資料，並以 light\\_only 與 all\\_active 作為測試情境（與 5.2 節的 8 組全集平均為不同子集）。此切分包含 576 個訓練樣本與 192 個測試樣本。若對 temperature 與 humidity residual trace 啟用 Fourier low-pass denoising，並保留 illuminance 原始 residual，則 hybrid residual correction 套用於主模型輸出後，field MAE 可由 temperature 0.0474、humidity 0.1765、illuminance 2.1757，分別降至 0.0020、0.0051 與 0.1370。對應改善比例約為溫度 95.78%、濕度 97.11% 與照度 93.70%。"
        ),
        paragraph(
            "為檢查 Fourier denoising 是否造成主要降幅，本研究另外關閉 Fourier low-pass denoising 重跑相同切分；結果為 temperature 0.0021、humidity 0.0057、illuminance 0.1370。此結果顯示，頻域低通主要對 humidity 有小幅穩定效果，而照度改善主要來自 residual model 對結構性偏差的學習，不是由頻域處理造成。進一步的 leave-one-scenario-out 設定中，每一 fold 以 7 個情境訓練、1 個情境測試，平均每 fold 為 672 個訓練樣本與 96 個測試樣本；8-fold 平均 hybrid field MAE 為 temperature 0.0017、humidity 0.0059、illuminance 0.1407，對應改善比例約為 96.41%、96.66% 與 93.06%。"
        ),
        paragraph(
            "表 5-5 彙整預設切分、no-Fourier 對照與 LOO cross-validation。圖 5-5 則將 IDW、base model 與 LOO hybrid 的平均 field MAE 以 log-scale 顯示，避免照度量級過大而掩蓋溫度與濕度差異。"
        ),
        table(
            ["設定", "Train/Test samples", "Base MAE (T/H/L)", "Hybrid MAE (T/H/L)"],
            [
                ["default 6/2 held-out", "576 / 192", "0.0474 / 0.1765 / 2.1757", "0.0020 / 0.0051 / 0.1370"],
                ["no-Fourier held-out", "576 / 192", "0.0474 / 0.1765 / 2.1757", "0.0021 / 0.0057 / 0.1370"],
                ["leave-one-scenario-out avg.", "672 / 96 per fold", "0.0474 / 0.1765 / 2.0269", "0.0017 / 0.0059 / 0.1407"],
            ],
        ),
        image(
            "docs/papers/thesis/assets/field_mae_comparison.png",
            "圖 5-5 IDW、base model 與 LOO hybrid residual correction 的平均 field MAE 比較。圖中使用 log-scale y-axis，數值為 8 組標準情境平均。",
            asset_name="field_mae_comparison",
        ),
        heading("5.8 【實驗 E7】真實臥室快照驗證", 2),
        paragraph(
            "除 canonical synthetic benchmark 與 public task-aligned benchmark 外，本研究也將使用者提供的 bedroom_01 真實房間快照資料納入初步驗證。該房間尺寸為 4.0 m × 4.6 m × 3.2 m，包含壁掛式冷氣、東南向窗戶、主燈、桌燈、床、書桌與收納櫃。資料涵蓋 2026-04-14 至 2026-04-20 共 7 天，每天包含 09:00、15:00、22:00 與 02:00 四個快照，共 28 筆時間點。每筆快照提供 8 顆角落感測器的 temperature、humidity、illuminance 觀測、裝置 activation、外部邊界條件，以及 pillow 位置的參考觀測值。"
        ),
        paragraph(
            "本節比較 raw reduced-order model 與套用 active-device power calibration + trilinear residual correction 後的估計結果。8 顆角落感測器觀測值用於校正，因此校正後 corner sensor MAE 為 0 是預期結果，代表模型與稀疏感測點一致，不能單獨解讀為 dense field validation。相對地，pillow 位置未參與校正，可作為獨立局部檢查點。結果顯示，pillow 位置的 MAE 由 raw model 的 temperature 0.8967°C、humidity 4.1286%、illuminance 309.0142 lux，下降至校正後的 0.1676°C、0.3939% 與 16.6450 lux，顯示同一套 sparse-sensor calibration 管線可實際吸收真實房間觀測並改善非感測點估計。"
        ),
        paragraph(
            "另外，本研究在真實臥室資料中加入分時 comfort target。一般時段沿用 pillow 位置原始 comfort target；sleep_02_00 快照則將照度目標設為 0 lux，容許範圍為 5 lux，以避免將睡眠時合理的黑暗狀態誤判為不舒適。分時後 sleep segment 的平均 comfort penalty 為 0.0000，而最差 penalty 轉移至 morning segment，表示舒適度評分已能反映不同使用情境。"
        ),
        table(
            ["比較項目", "Temp. MAE", "Hum. MAE", "Illum. MAE", "Comfort penalty"],
            [
                ["Raw pillow all", "0.8967", "4.1286", "309.0142", "--"],
                ["Corrected pillow all", "0.1676", "0.3939", "16.6450", "0.0911"],
                ["Corrected morning", "0.2372", "0.3695", "8.6247", "0.2371"],
                ["Corrected afternoon", "0.1358", "0.4890", "11.2235", "0.0812"],
                ["Corrected night", "0.0913", "0.2193", "46.6993", "0.0459"],
                ["Corrected sleep", "0.2060", "0.4979", "0.0326", "0.0000"],
            ],
        ),
        paragraph(
            "此資料仍屬小型初步驗證：它提供真實 sparse observations 與單一 pillow reference point，但沒有完整 dense spatial ground truth。因此，本研究仍以 synthetic benchmark 報告 full-field MAE，以真實臥室快照驗證 calibration pipeline 的實用性，兩者分別回答不同層級的問題。此限制也意味著 hybrid residual 在標準情境 family 內的漂亮降幅，應被解讀為結構性殘差可學習性的證據，而不是對任意房間、任意家具配置或任意天氣序列的無條件泛化保證。"
        ),
        heading("5.8.1 【驗證方案 E8】推薦動作實際介入驗證方法", 3),
        paragraph(
            "上述 bedroom_01 一週資料能驗證的是模型是否可利用真實稀疏感測資料改善非感測點估計；它尚未直接驗證推薦動作是否具有因果改善效果。為此，本研究將推薦動作驗證定義為介入式 before/after 實驗：先量測介入前 8 顆角落感測器與目標參考點，使用校正後模型輸出候選動作排序，實際執行排名第一的動作，等待固定 settling interval（建議先採 18 至 30 分鐘），再量測介入後狀態。若介入後實測 comfort penalty 下降，且改善方向與模型預測一致，才可視為該次推薦有效。"
        ),
        paragraph(
            "此驗證方法建議至少記錄四類數值：第一，介入前實測 penalty；第二，系統對每個候選動作預測的 penalty 與 predicted improvement；第三，介入後實測 penalty；第四，predicted improvement 與 actual improvement 的差距。若同一初始條件可測試多個候選動作，則可進一步比較預測排名與實測排名的一致性。"
        ),
        table(
            ["指標", "定義", "用途"],
            [
                ["actual improvement", "penalty_before - measured_penalty_after", "判斷實際是否變舒適"],
                ["success rate", "actual improvement > 0 的比例", "衡量推薦成功率"],
                ["prediction error", "abs(predicted improvement - actual improvement)", "衡量預測改善量準確度"],
                ["direction accuracy", "三因子改善方向是否一致", "檢查建議方向是否合理"],
                ["top-1 regret", "實測最佳動作與推薦第一名的改善差距", "衡量排序代價"],
            ],
        ),
        paragraph(
            "因此，本研究目前可主張的範圍是：校正後模型能在真實臥室快照中改善 pillow 參考點估計，並能根據 comfort penalty 對候選動作輸出反事實排序；推薦動作的實際有效性則應由上述介入實驗補足。此寫法可避免將估測準確度與控制因果效果混為一談。"
        ),
        heading("5.9 【實驗 E9】公開資料集執行流程與 Task-Aligned Benchmark 結果", 2),
        paragraph(
            "為驗證模型在非合成資料上的外部可比性，本研究以 SML2010 與 CU-BEMS 兩個公開資料集執行 task-aligned benchmark，並以 MAE、RMSE 與 Pearson Correlation 三項指標進行評估。MAE 衡量平均絕對誤差，RMSE 對尖峰偏差更敏感，Correlation 則反映模型是否能正確追蹤時序趨勢，三者共同提供較完整的評估視角。預測目標為下一個 15 分鐘或 60 分鐘時步的感測值，比較對象為 persistence（以上一時步值作預測）與 linear regression 兩個 baseline。"
        ),
        paragraph(
            "公開資料集比較的重點，是把其他論文或公開資料的可觀測欄位轉換成與本研究相容的子任務，而不是假設它們直接具備本研究所需的完整房間幾何、8 顆角落感測器、設備三維位置與 dense field ground truth。實作上，本研究先用 normalize_public_benchmark_data.py 將 raw public data 轉為 repo 內部 normalized public templates，再用 run_public_dataset_benchmark.py 在相同 task、horizon 與 target 上建立 persistence 與 linear regression baseline。接著，run_public_dataset_model_comparison.py 將 DigitalTwinModel 與 hybrid residual checkpoint 映射為 public task 可用的 structured prior，並在與 baseline 完全相同的 chronological 70/30 split 上訓練一個小型 linear readout head，輸出 hybrid_digital_twin_readout。"
        ),
        paragraph(
            "因此，本節的「本研究」數字不是 physics model zero-shot 直接輸出，也不是另行切分資料後得到的不可比結果，而是同一 train/test split、同一 target、同一 horizon 下的正式 head-to-head comparison。Web demo 的 Public Dataset Comparison 區塊則讀取同一批 JSON 輸出，將這些流程、限制與 MAE 結果整理成展示表格。"
        ),
        paragraph("表 5-8 列出公開資料集比較的執行流程與可宣稱範圍。"),
        table(
            ["步驟", "執行方式", "輸出或限制"],
            [
                ["資料正規化", "normalize_public_benchmark_data.py 將 raw SML2010/CU-BEMS 轉為 normalized public templates", "保留公開資料可觀測欄位，不補造完整 3D dense field"],
                ["Baseline 建立", "run_public_dataset_benchmark.py 在相同 task、horizon、target 上計算 persistence 與 linear regression", "採 chronological 70/30 split，避免時序洩漏"],
                ["模型映射", "run_public_dataset_model_comparison.py 將 DigitalTwinModel + hybrid residual checkpoint 映射為 structured prior", "使用 pseudo room、pseudo device 與 boundary/device-response 特徵"],
                ["Readout 訓練", "在 baseline 相同的訓練切分上 fit small linear readout head", "輸出 hybrid_digital_twin_readout，與 baseline 逐 target 比較"],
                ["展示與重現", "Web demo 透過 /api/public_benchmarks 讀取既有 JSON 輸出", "demo 不重新計算數字，避免展示數字與論文不一致"],
                ["Claim boundary", "公開資料只作 shared observable task benchmark", "不能宣稱 full 3D field MAE、8-corner calibration 或完整非連網裝置係數學習"],
            ],
        ),
        paragraph(
            "SML2010 在本研究中被映射為 two-point boundary-response benchmark。資料包含 dining room 與 room 兩個室內點位、室外溫濕度、日照與天氣相關欄位，適合評估窗邊或 facade 條件變化後的兩點時序響應；但它不包含完整單房間幾何、明確窗戶開關狀態、完整 3D 場真值，也不能支援非連網裝置影響係數的直接學習。CU-BEMS 則被映射為 single-zone device-response benchmark；每個 floor-zone 被視為一個 pseudo zone，AC power 與 lighting power 被轉換為 bounded device activations，用於評估 zone-level 溫度、濕度與照度響應。它的優點是資料量大且含裝置用電欄位，限制則是多區商辦資料不等於本研究的單房間 8 角落感測拓樸。"
        ),
        heading("5.9.1 任務代號與圖表閱讀方式", 3),
        paragraph(
            "為避免把所有 benchmark row 混在同一張表中而難以判讀，本研究將公開資料集任務改以 task family 呈現。每個 task family 都獨立報告三個比例：本研究是否取得最低 MAE、是否勝過 linear regression、是否勝過 persistence。這三個比例分別回答不同問題：最低 MAE 代表該任務上三者中誤差最小；勝過 linear regression 表示 structured prior 是否比一般線性讀出更有幫助；勝過 persistence 則是最嚴格的短視窗時序檢查，因為 persistence 直接沿用上一時步值，常在高時間慣性的資料中非常強。"
        ),
        table(
            ["任務", "資料集", "比較目的", "主要限制"],
            [
                ["S1", "SML2010", "純日照/照度邊界響應；檢查 daylight mapping 是否能處理兩點照度預測", "短視窗照度慣性強，且公開資料缺實際窗戶幾何與遮蔽資訊"],
                ["S2", "SML2010", "溫度與濕度邊界響應；檢查外氣與室內兩點的熱濕響應", "濕度量測尺度與本研究簡化濕度模型不完全對齊"],
                ["S3", "SML2010", "facade event delta response；檢查邊界或日照事件後的變化方向與長視窗響應", "仍只是兩點時序任務，不是完整 3D 場驗證"],
                ["C1", "CU-BEMS", "AC power 相關的 zone-level 溫濕度響應", "商辦 zone-level 資料時間慣性強，persistence 很難勝過"],
                ["C2", "CU-BEMS", "lighting power 相關的 zone-level 照度響應", "大型商辦照度受排程、遮陽、自然光與多燈具共同影響"],
                ["C3", "CU-BEMS", "compound event delta response；檢查裝置用電與環境變化的共同響應", "仍缺本研究所需的單房間幾何、8 點拓樸與 dense field truth"],
            ],
        ),
        heading("5.9.2 SML2010：S1/S2/S3 任務族群拆解", 3),
        image(
            "outputs/figures/public_benchmarks/sml2010_task_breakdown.svg",
            "圖 5-6 SML2010 S1/S2/S3 任務族群拆解。每個任務族群分別顯示本研究映射模型取得最低 MAE、勝過 linear regression 與勝過 persistence 的比例，並列出優勢或劣勢原因。",
            width_inches=6.1,
            asset_name="fig_5_6_sml2010_task_breakdown",
        ),
        table(
            ["任務族群", "結果摘要", "為什麼表現較好或較差", "論文可宣稱範圍"],
            [
                ["S1 純照度", "4 個 target-horizon 任務中，最低 MAE 0/4，勝過 linear regression 2/4，勝過 persistence 0/4。代表案例為 15min dining_illuminance：本研究 MAE 5.346，高於 persistence 3.418。", "S1 是純日照/照度任務，15 分鐘內照度通常高度延續上一時步；公開資料又缺少實際窗戶、遮蔽與燈具幾何，因此模型 daylight mapping 會引入額外誤差。", "S1 是本研究在 public benchmark 的明確劣勢；不能宣稱本模型優於短視窗照度 persistence。"],
                ["S2 溫濕度", "8 個任務中，最低 MAE 2/8，勝過 linear regression 2/8，勝過 persistence 4/8。優勢集中在長視窗溫度，例如 60min dining_temperature 本研究 MAE 0.156，低於 linear regression 0.192。", "溫度在 60 分鐘視窗受外氣與熱邊界條件影響，structured prior 較能提供方向；但濕度在 SML2010 中有量測尺度與基準偏移問題，簡化濕度模型容易高估。", "可主張長視窗溫度任務有優勢；不能把 S2 解讀成溫度、濕度都全面勝出。"],
                ["S3 複合事件", "12 個任務中，最低 MAE 10/12，勝過 linear regression 11/12，勝過 persistence 10/12。60 分鐘 horizon 下 6 個 target 全部同時勝過兩個 baseline。", "S3 是 facade event delta response，任務重點是事件後的變化方向。persistence 只延續上一時步，對 delta 任務缺少方向資訊；本研究的邊界條件、日照與響應特徵提供較有效的事件先驗。", "S3 是本研究在公開資料上的主要優勢，可用來支持 structured prior 對事件/邊界變化與長視窗響應有幫助。"],
            ],
        ),
        paragraph(
            "整體統計上，SML2010 共包含 24 個 target-horizon 任務，本研究映射模型在 12 項取得最低 MAE，15 項勝過 linear regression，14 項勝過 persistence。此結果不能簡化成「公開資料集全面勝出」；更精確的說法是：S3 這類事件/邊界變化任務是主要優勢，S2 的長視窗溫度有部分優勢，而 S1 短視窗純照度是明確劣勢。"
        ),
        paragraph(
            "從物理意義來看，這個結果與本研究模型設計一致。模型不是為了最佳化一般自回歸時序預測，而是把外部邊界、設備作用、空間位置與變數專屬響應拆開處理；因此當任務需要知道事件造成的方向與長視窗環境響應時較有利，當任務只需要複製上一時步照度時則不佔優勢。"
        ),
        heading("5.9.3 CU-BEMS：C1/C2/C3 任務族群拆解", 3),
        image(
            "outputs/figures/public_benchmarks/cu_bems_task_breakdown.svg",
            "圖 5-7 CU-BEMS C1/C2/C3 任務族群拆解。CU-BEMS 呈現出與 SML2010 不同的型態：本研究常能勝過 linear regression，但在高時間慣性的商辦 zone-level 任務中未勝過 persistence。",
            width_inches=6.1,
            asset_name="fig_5_7_cu_bems_task_breakdown",
        ),
        table(
            ["任務族群", "結果摘要", "為什麼表現較好或較差", "論文可宣稱範圍"],
            [
                ["C1 AC 溫濕度", "4 個 target-horizon 任務中，最低 MAE 0/4，勝過 linear regression 3/4，勝過 persistence 0/4。代表案例為 15min temperature：本研究 MAE 0.282，略低於 linear regression 0.288，但高於 persistence 0.262。", "AC power 與 plug load 可提供裝置狀態線索，因此 structured prior 能補強線性讀出；但 zone-level 溫濕度短時間自相關很強，上一時步觀測已是極強 baseline。", "可主張對 linear regression 有補強效果；不能宣稱優於 persistence。"],
                ["C2 照度", "2 個任務中，最低 MAE 0/2，勝過 linear regression 0/2，勝過 persistence 0/2。15min illuminance 本研究 MAE 7.700，高於 linear regression 1.794 與 persistence 1.363。", "商辦照度受排程、遮陽、自然光、多燈具與區域平均方式共同影響，與本研究單房間照度幾何假設不一致；照度短視窗又容易被 persistence 捕捉。", "C2 是明確劣勢，提醒照度模型不能未經校正就外推到大型商辦區域。"],
                ["C3 複合事件", "6 個任務中，最低 MAE 0/6，勝過 linear regression 6/6，勝過 persistence 0/6。代表案例為 60min illuminance：本研究 MAE 5.728，低於 linear regression 7.093，但高於 persistence 4.509。", "事件 delta 任務讓 device power 與環境響應特徵變得有用，因此能穩定勝過 linear regression；但 CU-BEMS zone-level 資料時間慣性非常強，persistence 仍在 MAE 上最佳。", "可宣稱本研究特徵對 compound event readout 有幫助；不能把 CU-BEMS 解讀為完整 3D spatial twin 驗證。"],
            ],
        ),
        paragraph(
            "CU-BEMS 呈現與 SML2010 不同的結果。12 個 target-horizon 任務中，本研究映射模型有 9 項 MAE 勝過 linear regression，但沒有任何一項勝過 persistence。這表示在大規模 zone-level building operation forecasting 中，資料本身的時間慣性非常強，上一時步觀測值往往已是極強 baseline；本研究模型的優勢較適合解讀為 structured prior 對 linear readout 的補強，而不是全面取代 persistence。"
        ),
        heading("5.9.4 綜合判讀與 Claim Boundary", 3),
        paragraph(
            "綜合兩個資料集，本研究在公開資料上的主要優勢不是「所有任務都比 baseline 好」，而是「當任務包含事件、邊界變化或長視窗響應時，變數專屬 structured prior 能提供比一般 linear regression 更有用的特徵」。最強證據是 SML2010 S3：15 分鐘 horizon 下 6 個 target 中有 5 項勝過 linear regression、4 項勝過 persistence；60 分鐘 horizon 下 6 個 target 全部同時勝過兩個 baseline。"
        ),
        paragraph(
            "公開資料上的主要劣勢也必須直接寫清楚。第一，短視窗純照度任務常由 persistence 佔優，因為照度在相鄰時間點高度相似，直接沿用上一時步即可得到低 MAE；若模型額外估計日照或燈具幾何，反而可能增加誤差。第二，CU-BEMS 這類商辦 zone-level forecasting 有很強的時間慣性，因此即使本研究能勝過 linear regression，也不代表能勝過 persistence。第三，SML2010 濕度任務存在量測尺度與本研究濕度模型基準對齊問題，因此不能把溫度上的優勢直接外推到濕度。"
        ),
        paragraph(
            "需要特別說明的是，task-aligned benchmark 採用的是「下一時步預測」框架（15min 或 60min 視窗），而本研究的核心使用情境並非短視窗自回歸預測，而是在設備達到準穩態後的空間場估計。實際應用中，使用者先啟動冷氣或開窗，系統再估計若干分鐘後整個房間的三因子空間分布，並據此輸出控制動作推薦。此類穩態導向估計不依賴前一時步值作為主要訊號，而是依賴設備配置、外部環境條件與物理影響函數。因此，persistence 在短視窗下的優勢屬於不同任務假設的產物，並不代表本研究模型在其實際設計目標上的劣勢。本研究進行 task-aligned benchmark 的目的，是為了在共同可比的框架下提供外部資料集的相對定位，而非宣稱本研究的主要評估對象是次步預測誤差。"
        ),
        heading("5.10 研究過程與實作挑戰", 2),
        paragraph(
            "本研究在實作過程中有三個直接影響最終模型設計的問題。第一，初期若僅使用局部影響場疊加設備作用，會出現冷氣附近快速降溫、房間遠端卻幾乎維持原溫的不合理結果，因此後續必須在溫度與濕度 nominal model 中加入全室平均響應與垂直分層近似；照度則改以燈具光束幾何、窗戶日照 envelope、遮蔽與反射近似處理，而不套用同一個全室混合模型。第二，若只以 8 顆角落感測器直接監督整個 3D 場，則黑盒神經網路雖可能把角落點擬合得很好，但對室內中央、窗邊與家具後方的場仍缺乏足夠監督，因此本研究把神經網路限制在 residual correction 層，而不是直接取代主模型。第三，公開資料集與本研究情境在幾何、裝置標記與感測器拓樸上通常不一致，因此必須採用 task-aligned benchmark，不能直接把所有實驗都搬到同一公開資料集上比較。"
        ),
        paragraph(
            "這些困難也說明本研究的設計取捨不是任意拼接，而是由實作過程逐步收斂而來：變數專屬 nominal model 負責處理溫度、濕度與照度各自的主要物理趨勢，single-bounce diffuse reflection 負責補足 direct lighting 對間接回填亮度的低估，trilinear correction 負責利用有限角落感測器修正低階偏差，least-squares impact learning 負責從設備前後差異學習非連網裝置影響，hybrid residual neural network 則只處理主模型尚未吸收的系統性誤差。"
        ),
        heading("5.11 展示 D1：可旋轉 3D 展示（非量化實驗）", 2),
        paragraph(
            "Web demo 提供可旋轉 3D 預覽，使使用者可直接觀察三因子點雲、房間框線與設備幾何位置。冷氣以牆面橫條表示，窗戶以牆面矩形表示，照明以點狀標記表示。圖 5-8 至 5-10 為靜態輸出之三因子場 3D 點雲，展示三種代表情境：三裝置全開、單獨窗戶、單獨燈具。此展示有助於口試或公開展示時說明模型如何從設備位置與環境場估計區域影響。"
        ),
        image(
            "outputs/figures/all_active_temperature_3d.svg",
            "圖 5-8 三裝置同時作用（all\\_active）溫度場 3D 點雲。顏色由藍綠至橙紅對映 26.02–27.16 °C 範圍；設備位置用帶邊框的標記表示。",
            asset_name="fig_5_8_all_active_temp_3d",
        ),
        image(
            "outputs/figures/window_only_temperature_3d.svg",
            "圖 5-9 僅開窗（window\\_only）溫度場 3D 點雲。靠窗區域溫度最高，造成區域溫度梯度。可與 all\\_active 情境對比，觀察冷氣介入後對窗邊高溫的抑制效果。",
            asset_name="fig_5_9_window_only_temp_3d",
        ),
        image(
            "outputs/figures/light_only_illuminance_3d.svg",
            "圖 5-10 僅燈具作用（light\\_only）照度場 3D 點雲。燈具正下方照度最高，遠端補有少量的 single-bounce diffuse 回填；此情境也是 5.7 節 held-out 測試集之一。",
            asset_name="fig_5_10_light_only_illum_3d",
        ),
        page_break(),
        heading("第六章 結論與未來工作", 1),
        heading("6.1 結論", 2),
        paragraph(
            "本研究建立一個面向非連網家電環境影響學習的單房間三因子空間數位孿生原型，針對 temperature、humidity 與 illuminance 的空間變化進行建模、校正與學習。透過 8 顆角落感測器、設備影響函數、active device power scale 校準、single-bounce diffuse reflection 與 trilinear 校正場，系統能估計房間內任意位置與指定區域的三因子狀態。模擬結果顯示，加入設備影響模型與照度反射近似後，在冷氣、窗戶與照明等情境下能提供較 IDW baseline 更可解釋且更精細的場估計；新增的消融實驗也說明反射、校準與 trilinear correction 在不同指標上扮演不同角色。進一步加入只作用於 temperature / humidity residual trace 的 Fourier low-pass denoising 與 hybrid residual neural correction 後，預設 held-out 與 leave-one-scenario-out 情境的場重建誤差皆可再顯著下降。"
        ),
        paragraph(
            "此外，本研究將模型封裝為 MCP server，並提供 Gemma/Ollama bridge 與 web demo，使數位孿生不只是離線模擬程式，而是可被 AI client 或使用者互動查詢的工具化系統。整體成果符合研究目標：在有限感測器與非連網裝置條件下，學習裝置對空間環境的影響，並在 sample scope 與三因子目標明確時用於更可解釋的控制動作推薦排序。"
        ),
        paragraph(
            "在公開資料集 task-aligned benchmark 方面，本研究以 MAE、RMSE 與 Pearson Correlation 三項指標，對比 persistence 與 linear regression 兩個 baseline。SML2010 共 24 個 target-horizon 任務中，本研究映射模型有 12 項取得最低 MAE，並在 S3 facade event delta 的 60 分鐘 horizon 中對 6 個 target 全部優於兩個 baseline；這說明物理結構與 boundary/event response 先驗在長視窗變化任務中具明確價值。CU-BEMS 則提供相反提醒：在 12 個 target-horizon 任務中，本研究映射模型有 9 項勝過 linear regression，但沒有任何一項勝過 persistence，表示高時間慣性的大規模 zone-level building forecasting 不一定能由本研究模型取代簡單時間延續策略。劣勢主要集中於短視窗純照度任務與外部資料濕度尺度不匹配。此分析說明本研究的優勢來自模型結構對裝置、邊界與空間響應的顯式建模，而非針對一般純時序預測最佳化。"
        ),
        paragraph(
            "另一項結論是，公開資料集並非不能使用，而是必須依資料本身支援的任務層級進行比較。對完整 3D 場重建，本研究目前仍以 canonical synthetic benchmark 作為主要依據；對 zone-level 響應、兩點時序響應與舒適度評分，則可分別利用相容的公開資料建立 task-aligned benchmark。此作法比直接宣稱所有資料集都能完整驗證本研究系統更嚴謹，也使後續 IEEE 稿件能從中文論文抽取一致的資料、數字與 claim boundary。"
        ),
        paragraph(
            "真實臥室快照驗證進一步補足了純模擬實驗的不足。7 天、28 筆快照結果顯示，當 8 顆角落感測器提供真實觀測時，校正後模型能將未參與校正的 pillow 位置估計誤差降至 0.1676°C、0.3939% 與 16.6450 lux。此結果不等同於完整 3D 場 ground truth，但已證明本研究的 sparse-sensor calibration pipeline 可直接接入真實房間資料。"
        ),
        paragraph(
            "對推薦動作而言，本研究目前完成的是模型導向的反事實排序與驗證方法設計，而非真實閉環控制。推薦前必須先指定 point/cluster sample 與完整溫度、濕度、照度目標；實際因果驗證應以介入前後量測為準，檢查排名第一的動作是否帶來正的 actual improvement，並比較 predicted improvement 與 measured improvement 是否一致。"
        ),
        heading("6.2 研究限制", 2),
        bullets(
            [
                "目前已加入小型真實臥室快照驗證，但仍缺乏長期連續部署資料與 dense spatial ground truth。",
                "Hybrid residual 的 leave-one-scenario-out 結果證明標準情境 family 內的殘差可學習，但尚未證明可直接泛化到任意房間幾何、家具配置或使用者行為。",
                "模型不處理多房間氣流、牆體熱容或完整流體動力學。",
                "濕度模型採簡化耦合，驗證強度低於溫度與照度；在外部資料集（SML2010）中存在系統性基準偏差，需進一步對齊量測尺度。",
                "短視窗（15min）純照度預測上，persistence baseline 因照度短期穩定性而具優勢，本研究的物理估計引入額外誤差。",
                "公開資料集多缺乏完整單房間幾何與 dense ground truth，因此無法直接作為 full-field benchmark。",
                "MCP server 目前為本地 stdio 版本，尚未包含遠端部署、OAuth 或多使用者管理。",
                "控制功能目前為具前置條件的推薦排序：必須先有 point/cluster sample 與三因子目標，且尚未完成真實介入式因果驗證，也尚未進入自動閉環控制。",
            ]
        ),
        heading("6.3 未來工作", 2),
        bullets(
            [
                "擴大實體 ESP32 感測器部署，收集更長期且自動化的真實房間資料。",
                "擴充自訂房間 JSON 輸入，使系統可支援不同房間尺寸與設備位置。",
                "為角落感測器加入照度量測通道（如光照感測元件），使角落光照資料可直接引入 trilinear residual correction，從而消除目前物理照度模型的系統性偏差，實現照度場的自我校正。",
                "加入更多環境變數，例如 CO2、PM2.5 或人體熱源。",
                "將 MCP server 擴充為遠端 HTTP MCP，並加入權限控管。",
                "依 before/after 介入驗證方法實測推薦動作，先固定 point/cluster sample 與三因子目標，再量化 actual improvement、success rate 與 top-1 regret。",
                "進一步研究閉環控制，將已驗證的推薦排序延伸為實際控制策略。",
                "加入長時間資料以學習季節性與日夜週期變化。",
                "以真實量測資料重新訓練與驗證 hybrid residual neural network，檢驗其在真實房間中的泛化能力。",
            ]
        ),
        page_break(),
        heading("參考文獻", 1),
        bullets(
            [
                "[1] Per Bacher, Henrik Madsen, Identifying suitable models for the heat dynamics of buildings, Energy and Buildings, vol. 43, no. 7, pp. 1511-1522, 2011. DOI: 10.1016/j.enbuild.2011.02.005",
                "[2] Petri Hietaharju, Mika Ruusunen, Kauko Leiviska, A Dynamic Model for Indoor Temperature Prediction in Buildings, Energies, vol. 11, no. 6, 1477, 2018. DOI: 10.3390/en11061477",
                "[3] Gargya Gokhale, Bert Claessens, Chris Develder, Physics informed neural networks for control oriented thermal modeling of buildings, Applied Energy, vol. 314, 118852, 2022. DOI: 10.1016/j.apenergy.2022.118852",
                "[4] E. J. Teshome, F. Haghighat, Zonal Models for Indoor Air Flow - A Critical Review, International Journal of Ventilation, vol. 3, no. 2, pp. 119-129, 2004. DOI: 10.1080/14733315.2004.11683908",
                "[5] Boris Huljak, Juan A. Acero, Zin H. Kyaw, Francisco Chinesta, Hybrid models for simulating indoor temperature distribution in air-conditioned spaces, Frontiers in Built Environment, vol. 11, 1690062, 2025. DOI: 10.3389/fbuil.2025.1690062",
                "[6] Ahmed Megri, Yao Yu, Rui Miao, Xiaoou Hu, A new dynamic zOnal model with air-diffuser (DOMA) - Application to thermal comfort prediction, Indoor and Built Environment, vol. 31, no. 7, pp. 1738-1757, 2022. DOI: 10.1177/1420326X211060486",
                "[7] Andres Sebastian Cespedes-Cubides, Muhyiddine Jradi, A review of building digital twins to improve energy efficiency in the building operational stage, Energy Informatics, vol. 7, article 11, 2024. DOI: 10.1186/s42162-024-00313-7",
                "[8] Weixin Qian, Chenxi Li, Hu Gao, Lei Zhuang, Yanyu Lu, Site Hu, Jing Liu, Estimating indoor air temperature and humidity distributions by data assimilation with finite observations: Validation using an actual residential room, Building and Environment, vol. 269, 112495, 2025. DOI: 10.1016/j.buildenv.2024.112495",
                "[9] Y. Lisa Chen, Jin Wen, Application of zonal model on indoor air sensor network design, Proceedings of SPIE, vol. 6529, 652911, 2007. DOI: 10.1117/12.716356",
                "[10] D. Shepard, A Two-Dimensional Interpolation Function for Irregularly-Spaced Data, Proceedings of the 1968 ACM National Conference, pp. 517-524, 1968.",
                "[11] Model Context Protocol, Model Context Protocol Documentation, https://modelcontextprotocol.io/ , accessed 2026-04-10.",
                "[12] Gopal Chitalia, Manisa Pipattanasomporn, CU-BEMS, smart building electricity consumption and indoor environmental sensor datasets, Scientific Data, vol. 7, article 290, 2020. DOI: 10.1038/s41597-020-00582-3",
                "[13] Luis Candanedo, Appliances Energy Prediction [Dataset], UCI Machine Learning Repository, 2017. DOI: 10.24432/C5VC8G",
                "[14] Pablo Romeu-Guallart, Francisco Zamora-Martinez, SML2010 [Dataset], UCI Machine Learning Repository, 2014. DOI: 10.24432/C5RS3S",
                "[15] Luis Candanedo, Occupancy Detection [Dataset], UCI Machine Learning Repository, 2016. DOI: 10.24432/C5X01N",
                "[16] Kamilla Heimar Andersen, Hicham Johra, Anna Marszal-Pomianowska, Per Kvols Heiselberg, Henrik N. Knudsen, Dataset of room-level indoor environmental quality measurements and occupancy ground truth for five residential apartments in Denmark [Dataset], Zenodo, 2024. DOI: 10.5281/zenodo.10761326",
                "[17] V. Foldvary Licina, T. Cheung, H. Zhang, R. de Dear, T. Parkinson, E. Arens, et al., Development of the ASHRAE Global Thermal Comfort Database II, Building and Environment, vol. 142, pp. 502-512, 2018. DOI: 10.1016/j.buildenv.2018.06.022",
                "[18] G. Chinazzo, J. Wienold, M. Andersen, Influence of indoor temperature and daylight illuminance on visual perception, Lighting Research and Technology, vol. 52, no. 8, pp. 998-1020, 2020. DOI: 10.1177/1477153519859609",
                "[19] G. Chinazzo, J. Wienold, M. Andersen, Daylight affects human thermal perception, Scientific Reports, vol. 9, article 13695, 2019. DOI: 10.1038/s41598-019-48963-y",
                "[20] Lan et al., Experimental study on the impact of indoor lighting and thermal environment on university students' learning performance in summer, Energy and Buildings, vol. 331, 115774, 2025. DOI: 10.1016/j.enbuild.2025.115774",
                "[21] K. Kuwahara et al., Studying the Indoor Environment and Comfort of a University Laboratory: Air-Conditioning Operation and Natural Ventilation Used as a Countermeasure against COVID-19, Buildings, vol. 12, no. 7, 953, 2022. DOI: 10.3390/buildings12070953",
                "[22] Yan Zhou, Jianmin Cai, Yiwen Xu, Indoor environmental quality and energy use evaluation of a three-star green office building in China with field study, Journal of Building Physics, vol. 45, no. 2, pp. 163-190, 2021. DOI: 10.1177/1744259120944604",
                "[23] Z. Wang, Q. Xue, Y. Ji, Z. Yu, Indoor environment quality in a low-energy residential building in winter in Harbin, Building and Environment, vol. 135, pp. 194-201, 2018. DOI: 10.1016/j.buildenv.2018.03.012",
                "[24] Y. Geng, B. Lin, Y. Zhu, Comparative study on indoor environment quality of green office buildings with different levels of energy use intensity, Building and Environment, vol. 168, 106482, 2020. DOI: 10.1016/j.buildenv.2019.106482",
                "[25] J. Lee et al., A Comparative Field Study of Indoor Environment Quality and Work Productivity between Job Types in a Research Institute in Korea, International Journal of Environmental Research and Public Health, vol. 19, no. 21, 14332, 2022. DOI: 10.3390/ijerph192114332",
            ]
        ),
        page_break(),
        heading("附錄 A：原型執行方式", 1),
        code("python3 scripts/run_demo.py\npython3 scripts/run_window_matrix.py\npython3 scripts/run_hybrid_residual_experiment.py\npython3 scripts/run_submission_readiness_experiments.py\npython3 scripts/run_web_demo.py\npython3 scripts/run_mcp_server.py"),
        heading("附錄 B：Web Demo 操作與公開比較展示", 1),
        bullets(
            [
                "左側 checkbox 控制 ac_main、window_main 與 light_main。",
                "3D 預覽可拖曳旋轉，滾輪縮放。",
                "Metric checkbox 可切換 temperature、humidity 與 illuminance。",
                "左側 Indoor Baseline 可直接調整室內基準溫度、濕度與照度。",
                "左側 Estimator toggle 可切換主模型與 hybrid residual corrected field。",
                "窗戶區可選季節、天氣與時段 preset，並手動覆寫外部溫度與開窗比例。",
                "時間軸可播放從啟動到接近準穩態的變化。",
                "Point Sample 可查詢任意座標的三因子估計值。",
                "左側 Term Glossary 可展開名詞解釋；頁面中的重要術語也會以 hover/tap tooltip 顯示簡短定義。",
                "Public Dataset Comparison 可展開 SML2010 與 CU-BEMS 的 task-aligned benchmark，比較 persistence、linear regression 與 hybrid_digital_twin_readout 的 MAE。",
                "Public Dataset Comparison 讀取 /api/public_benchmarks，該 API 來自既有 JSON 輸出，不在展示時重新計算論文數字。",
                "展示時需明確說明：公開資料集支援的是 shared observable tasks，不是完整 3D dense field MAE 或 8 顆角落感測器校正驗證。",
            ]
        ),
        heading("附錄 C：名詞解釋", 1),
        table(
            ["名詞", "本文用法"],
            [
                ["Sparse-Sensing", "以少量感測點推估整個房間或目標區域的環境狀態。本文固定以 8 顆角落感測器作為主要前提。"],
                ["Spatial Digital Twin", "可依房間幾何、設備位置與感測資料更新的室內空間數位模型，用來估計任意點或區域的環境狀態。"],
                ["Non-networked Appliance", "無法透過網路直接回報狀態或功率的設備，例如傳統冷氣、手動窗戶或普通照明。"],
                ["Appliance Impact", "設備啟用後對 temperature、humidity、illuminance 造成的方向、幅度與空間分布影響。"],
                ["Variable-Specific Nominal Model", "依溫度、濕度與照度的不同物理特性建立低階主模型；溫度偏熱交換與熱源，濕度偏水氣交換與除濕，照度偏燈具光束幾何、窗戶日照 envelope、遮蔽與反射。"],
                ["Indoor Baseline", "模型中的室內基準狀態 $(T_0,H_0,L_0)$；代表設備作用與 residual correction 前的起始溫度、濕度與照度，不是 IDW 或 persistence 這類比較方法。"],
                ["IDW", "Inverse Distance Weighting，反距離加權插值；本文作為不含設備物理先驗的 baseline。"],
                ["MAE", "Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。"],
                ["RMSE", "Root Mean Square Error，均方根誤差；比 MAE 更重視尖峰或離群偏差。"],
                ["Correlation", "Pearson correlation，用於衡量預測與真值是否同向變化；在事件 delta 任務中可反映趨勢追蹤能力。"],
                ["Trilinear Correction", "利用 8 個角落感測器殘差對房間內任意點做三線性殘差校正。"],
                ["Power Calibration", "依 active device 附近感測器殘差調整設備影響強度，使模型估計更貼近觀測。"],
                ["Least Squares", "最小平方法；本文用於從設備前後感測差異估計非連網裝置影響係數。"],
                ["Hybrid Residual Correction", "保留主物理模型，再用小型 neural network 學習主模型尚未吸收的剩餘誤差。"],
                ["Fourier Low-Pass Denoising", "對 temperature 與 humidity residual trace 做低通濾波，降低高頻雜訊對 residual training 的影響；不套用於 illuminance，因為照度可能因光源、日照與遮蔽產生有物理意義的快速變化。"],
                ["One-Bounce Diffuse Reflection", "照度模型中的簡化反射近似，讓地板、牆面、天花板或家具表面提供間接回填亮度。"],
                ["LOO", "Leave-One-Scenario-Out，以每次留下一個情境測試、其餘情境訓練的交叉驗證方式。"],
                ["Ablation", "消融實驗；移除某個模型元件後比較指標變化，用來判斷元件貢獻。"],
                ["Task-Aligned Benchmark", "只選擇公開資料集可支援且與本研究相容的子任務做比較，不把公開資料誤當完整 3D 真值。"],
                ["Chronological Split", "依時間順序切分 train/test，避免未來資料流入訓練造成時序洩漏。"],
                ["Structured Prior", "把本研究物理模型與 hybrid checkpoint 轉成 public task 可用的結構化先驗特徵。"],
                ["Linear Readout Head", "接在 structured prior 後方的小型線性輸出層；在相同 train split 上訓練後與 baseline 比較。"],
                ["Persistence", "以上一個時間點的觀測值作為下一時間點預測的 baseline。"],
                ["Linear Regression", "使用公開資料特徵訓練的線性迴歸 baseline。"],
                ["MCP", "Model Context Protocol；本文用於將數位孿生能力封裝成 AI client 可呼叫的工具介面。"],
                ["Direct Window Input", "不使用季節/天氣/時段 preset，而是直接輸入外部溫度、濕度、日照與開窗比例進行模擬。"],
                ["Point Sample", "推薦或查詢使用的單一指定座標樣本；若只查估測值，不需要目標；若要推薦動作，還必須提供完整三因子目標。"],
                ["Cluster Sample", "由多個座標點或 target zone 組成的採樣範圍；推薦排序會先聚合此範圍的溫度、濕度與照度，再計算 comfort penalty。"],
                ["Recommendation Preconditions", "推薦動作的必要前置條件：sample scope 必須存在，且 temperature、humidity、illuminance 三因子的目標與容許範圍必須可定義；缺少時不產生推薦。"],
            ],
        ),
    ]


def heading(text: str, level: int) -> Block:
    return {"type": "heading", "text": text, "level": level}


def title(text: str, level: int) -> Block:
    return {"type": "title", "text": text, "level": level}


def paragraph(text: str, align: str = "left") -> Block:
    return {"type": "paragraph", "text": text, "align": align}


def bullets(items: Iterable[str]) -> Block:
    return {"type": "bullets", "items": list(items)}


def code(text: str) -> Block:
    return {"type": "code", "text": text}


def table(headers: List[str], rows: List[List[str]]) -> Block:
    return {"type": "table", "headers": headers, "rows": rows}


def image(path: str, caption: str, width_inches: float = 5.8, asset_name: str = "") -> Block:
    return {
        "type": "image",
        "path": path,
        "caption": caption,
        "width_inches": width_inches,
        "asset_name": asset_name,
    }


def math(latex: str, display: bool = True) -> Block:
    """A LaTeX math block. display=True for block equations, False for inline."""
    return {"type": "math", "latex": latex, "display": display}


def page_break() -> Block:
    return {"type": "page_break"}


def raw_latex(content: str) -> Block:
    return {"type": "raw_latex", "content": content}


def write_markdown(path: Path, blocks: List[Block]) -> None:
    lines: List[str] = []
    for block in blocks:
        kind = block["type"]
        if kind == "title":
            lines.append("# " + str(block["text"]).replace("\n", "\n\n# "))
        elif kind == "heading":
            level = int(block["level"])
            lines.append("#" * level + " " + str(block["text"]))
        elif kind == "paragraph":
            lines.append(str(block["text"]))
        elif kind == "bullets":
            lines.extend("- " + item for item in block["items"])
        elif kind == "code":
            lines.append("```text")
            lines.append(str(block["text"]))
            lines.append("```")
        elif kind == "table":
            headers = [str(item) for item in block["headers"]]
            rows = [[str(cell) for cell in row] for row in block["rows"]]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows:
                lines.append("| " + " | ".join(row) + " |")
        elif kind == "image":
            image_path = ROOT / str(block["path"])
            relative_path = image_path.relative_to(ROOT)
            markdown_target = Path("..") / ".." / relative_path
            caption = str(block["caption"])
            lines.append(f"![{caption}]({markdown_target.as_posix()})")
            lines.append(f"*{caption}*")
        elif kind == "math":
            latex = str(block["latex"])
            if block.get("display", True):
                lines.append("$$" + latex + "$$")
            else:
                lines.append("$" + latex + "$")
        elif kind == "raw_latex":
            pass  # PDF-only; skip in Markdown
        elif kind == "page_break":
            lines.append("\n---\n")
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_docx(path: Path, blocks: List[Block]) -> None:
    image_registry: Dict[str, Dict[str, object]] = {}
    document_xml = build_document_xml(blocks, image_registry)
    files = {
        "[Content_Types].xml": content_types_xml(bool(image_registry)),
        "_rels/.rels": package_rels_xml(),
        "docProps/core.xml": core_props_xml(),
        "docProps/app.xml": app_props_xml(),
        "word/document.xml": document_xml,
        "word/_rels/document.xml.rels": document_rels_xml(image_registry),
        "word/styles.xml": styles_xml(),
        "word/settings.xml": settings_xml(),
    }
    for item in image_registry.values():
        asset_path = Path(str(item["asset_path"]))
        files[f"word/media/{item['media_name']}"] = asset_path.read_bytes()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            if isinstance(content, bytes):
                archive.writestr(name, content)
            else:
                archive.writestr(name, content.encode("utf-8"))


def build_document_xml(blocks: List[Block], image_registry: Dict[str, Dict[str, object]]) -> str:
    body_parts: List[str] = []
    for block in blocks:
        kind = block["type"]
        if kind == "title":
            body_parts.append(docx_paragraph(str(block["text"]), style="Title", align="center", bold=True))
        elif kind == "heading":
            level = int(block["level"])
            body_parts.append(docx_paragraph(str(block["text"]), style=f"Heading{min(level, 3)}", bold=True))
        elif kind == "paragraph":
            body_parts.append(docx_paragraph(str(block["text"]), align=str(block.get("align", "left"))))
        elif kind == "bullets":
            for item in block["items"]:
                body_parts.append(docx_paragraph("• " + str(item), indent=True))
        elif kind == "code":
            for line in str(block["text"]).splitlines():
                body_parts.append(docx_paragraph(line, style="Code"))
        elif kind == "table":
            body_parts.append(docx_table([block["headers"]] + block["rows"]))
        elif kind == "image":
            body_parts.append(docx_image_paragraph(block, image_registry))
            body_parts.append(docx_paragraph(str(block["caption"]), align="center"))
        elif kind == "math":
            # Render as plain text in docx (no MathML support without external libs)
            latex = str(block["latex"])
            body_parts.append(docx_paragraph(latex, align="center"))
        elif kind == "raw_latex":
            pass  # PDF-only; skip in DOCX
        elif kind == "page_break":
            body_parts.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    body_parts.append(section_properties_xml())
    body = "\n".join(body_parts)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:xml="http://www.w3.org/XML/1998/namespace" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    {body}
  </w:body>
</w:document>
'''


def docx_paragraph(
    text: str,
    style: str = "Normal",
    align: str = "left",
    bold: bool = False,
    indent: bool = False,
) -> str:
    ppr = []
    if style != "Normal":
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align != "left":
        ppr.append(f'<w:jc w:val="{align}"/>')
        ppr.append('<w:ind w:firstLine="0"/>')  # no first-line indent for centered/right text
    if indent:
        ppr.append('<w:ind w:left="720" w:hanging="360" w:firstLine="0"/>')
    ppr.append('<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>')
    rpr = '<w:rPr><w:b/></w:rPr>' if bold else ""
    lines = escape(text).split("\n")
    run_text = '<w:br/>'.join(f'<w:t xml:space="preserve">{line}</w:t>' for line in lines)
    return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr><w:r>{rpr}{run_text}</w:r></w:p>'


def docx_table(rows: List[List[object]]) -> str:
    table_rows = []
    for row_index, row in enumerate(rows):
        cells = []
        for cell in row:
            text = str(cell)
            bold = row_index == 0
            cells.append(
                "<w:tc>"
                '<w:tcPr><w:tcW w:w="2200" w:type="dxa"/></w:tcPr>'
                f"{docx_paragraph(text, bold=bold)}"
                "</w:tc>"
            )
        table_rows.append("<w:tr>" + "".join(cells) + "</w:tr>")
    borders = (
        '<w:tblBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="999999"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="999999"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="999999"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="999999"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="999999"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="999999"/>'
        "</w:tblBorders>"
    )
    return f'<w:tbl><w:tblPr>{borders}</w:tblPr>{"".join(table_rows)}</w:tbl>'


def docx_image_paragraph(block: Block, image_registry: Dict[str, Dict[str, object]]) -> str:
    asset_path = ensure_image_asset(block)
    registry_key = str(asset_path)
    if registry_key not in image_registry:
        image_index = len(image_registry) + 1
        image_registry[registry_key] = {
            "rel_id": f"rId{image_index}",
            "media_name": f"image{image_index}{asset_path.suffix.lower()}",
            "asset_path": asset_path,
            "doc_id": image_index,
        }
    entry = image_registry[registry_key]
    width_px, height_px = png_dimensions(asset_path)
    max_width_inches = float(block.get("width_inches", 5.8))
    max_width_emu = int(max_width_inches * 914400)
    original_width_emu = max(width_px, 1) * 9525
    scale = min(1.0, max_width_emu / float(original_width_emu))
    extent_x = int(original_width_emu * scale)
    extent_y = int(max(height_px, 1) * 9525 * scale)
    name = escape(str(block.get("caption", "figure")))
    return (
        '<w:p>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr>'
        '<w:r><w:drawing>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{extent_x}" cy="{extent_y}"/>'
        f'<wp:docPr id="{entry["doc_id"]}" name="{name}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic>'
        '<pic:nvPicPr>'
        f'<pic:cNvPr id="{entry["doc_id"]}" name="{name}"/>'
        '<pic:cNvPicPr/>'
        '</pic:nvPicPr>'
        '<pic:blipFill>'
        f'<a:blip r:embed="{entry["rel_id"]}"/>'
        '<a:stretch><a:fillRect/></a:stretch>'
        '</pic:blipFill>'
        '<pic:spPr>'
        '<a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{extent_x}" cy="{extent_y}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '</pic:spPr>'
        '</pic:pic>'
        '</a:graphicData></a:graphic>'
        '</wp:inline>'
        '</w:drawing></w:r>'
        '</w:p>'
    )


def section_properties_xml() -> str:
    return (
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr>"
    )


def content_types_xml(has_png: bool = False) -> str:
    png_default = '\n  <Default Extension="png" ContentType="image/png"/>' if has_png else ""
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {png_default}
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
'''


def package_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'''


def document_rels_xml(image_registry: Dict[str, Dict[str, object]]) -> str:
    relationships = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    relationships.append('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">')
    for item in image_registry.values():
        relationships.append(
            f'<Relationship Id="{item["rel_id"]}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{item["media_name"]}"/>'
        )
    relationships.append("</Relationships>")
    return "\n".join(relationships)


def core_props_xml() -> str:
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型</dc:title>
  <dc:creator>Yun-You Lin</dc:creator>
  <cp:lastModifiedBy>Yun-You Lin</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
'''


def app_props_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Thesis document generator</Application>
</Properties>
'''


def settings_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:defaultTabStop w:val="720"/>
</w:settings>
'''


def styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:line="360" w:lineRule="auto" w:before="0" w:after="0"/>
        <w:ind w:firstLine="480"/>
      </w:pPr>
    </w:pPrDefault>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="PingFang TC" w:cs="PingFang TC"/>
        <w:sz w:val="24"/>
        <w:szCs w:val="24"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto" w:before="0" w:after="0"/>
      <w:ind w:firstLine="480"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="PingFang TC" w:cs="PingFang TC"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:pPr>
      <w:jc w:val="center"/>
      <w:spacing w:line="360" w:lineRule="auto" w:before="0" w:after="240"/>
      <w:ind w:firstLine="0"/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="PingFang TC" w:cs="PingFang TC"/>
      <w:sz w:val="34"/>
      <w:szCs w:val="34"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto" w:before="480" w:after="240"/>
      <w:ind w:firstLine="0"/>
    </w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto" w:before="360" w:after="120"/>
      <w:ind w:firstLine="0"/>
    </w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto" w:before="240" w:after="120"/>
      <w:ind w:firstLine="0"/>
    </w:pPr>
    <w:rPr><w:b/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="240" w:lineRule="auto" w:before="0" w:after="0"/>
      <w:ind w:firstLine="0"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:eastAsia="PingFang TC" w:cs="PingFang TC"/>
      <w:sz w:val="20"/>
      <w:szCs w:val="20"/>
    </w:rPr>
  </w:style>
</w:styles>
'''


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    PAPERS.mkdir(parents=True, exist_ok=True)
    blocks = build_blocks()
    markdown_path = DOCS / "thesis" / "thesis_draft_zh.md"
    docx_path = PAPERS / "thesis_draft_zh.docx"
    write_markdown(markdown_path, blocks)
    write_docx(docx_path, blocks)
    print(f"Wrote {markdown_path}")
    print(f"Wrote {docx_path}")


if __name__ == "__main__":
    main()
