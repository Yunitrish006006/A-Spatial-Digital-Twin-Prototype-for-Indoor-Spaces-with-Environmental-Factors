from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Iterable, List
import shutil
import struct
import subprocess
from xml.sax.saxutils import escape
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUTS = ROOT / "outputs"
PAPERS = OUTPUTS / "papers"
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
        temp_dir = PAPER_ASSETS / ".ql_tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [qlmanage, "-t", "-s", "1800", "-o", str(temp_dir), str(source)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(completed.stderr or completed.stdout or "Failed to render figure asset via qlmanage.")
        rendered = temp_dir / f"{source.name}.png"
        if not rendered.exists():
            raise SystemExit(f"qlmanage did not produce expected PNG asset for {source}")
        shutil.move(str(rendered), str(target))
        return target
    target = PAPER_ASSETS / f"{asset_name}{source.suffix.lower()}"
    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        shutil.copy2(source, target)
    return target


def png_dimensions(path: Path) -> List[int]:
    with open(path, "rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unsupported PNG file: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return [int(width), int(height)]


def build_blocks() -> List[Block]:
    return [
        title("國立彰化師範大學\n資訊工程學系碩士班\n碩士論文初稿", 0),
        title("基於 MCP 之單房間非連網家電環境影響學習與三因子控制數位孿生原型", 1),
        paragraph("An MCP-Enabled Lightweight Spatial Digital Twin Prototype for Learning the Environmental Impact of Non-Networked Appliances in a Single Room", align="center"),
        paragraph("研究生：林昀佑", align="center"),
        paragraph("指導教授：易昶霈", align="center"),
        paragraph("版本：論文初稿 v0.2", align="center"),
        paragraph("日期：2026 年 4 月 15 日", align="center"),
        page_break(),
        heading("摘要", 1),
        paragraph(
            "智慧建築與智慧居家系統需要掌握室內環境狀態，才能支援舒適度評估、能源管理與設備控制。然而，實際房間中常見的冷氣、窗戶與照明往往沒有連網能力，也無法直接回報狀態；同時，房間內通常只能布建少量感測器，難以直接量測完整空間分布。這使得一般數位孿生若同時缺乏設備遙測與高密度量測，便難以對真實房間提供可用的環境估計與控制建議。"
        ),
        paragraph(
            "本研究以單一矩形房間為研究場域，提出一個基於有限角落感測器與連續影響場估計之三因子空間數位孿生原型。研究過程中，本研究先後比較純插值、僅局部影響場與資料驅動修正等作法，最終採用 bulk + local field 作為主模型，並以冷氣、窗戶與照明之參數化影響函數描述非連網裝置對不同區域的作用。系統固定使用 8 顆角落感測器，即天花板四角與地面四角，每個節點量測溫度、濕度與照度，並以感測器殘差進行主動設備 power scale 校準與 trilinear residual correction，以修正背景場與設備影響函數之偏差。在此基礎上，本研究再加入 hybrid residual neural network 延伸模組，以小型多層感知器學習主模型的剩餘誤差，而不直接取代原本的可解釋結構。"
        ),
        paragraph(
            "除空間場估計外，本研究亦建立裝置啟用前後感測資料之影響學習流程，透過最小平方法估計非連網裝置的環境影響係數，並根據目標區域的舒適度偏差輸出候選控制動作排序。為提升系統可存取性，本研究將模型能力封裝為本地 Model Context Protocol（MCP）服務。評估方面，本研究以 8 組標準情境、48 組窗戶矩陣、IDW baseline 比較與 hybrid residual held-out 測試驗證方法可行性；其中 base model 在標準情境下之平均 MAE 分別為溫度 0.0482、濕度 0.1763 與照度 2.1616，而 hybrid residual correction 在 held-out 情境下可進一步降低場重建誤差。"
        ),
        paragraph("關鍵字：空間數位孿生、非連網家電、室內環境建模、溫度、濕度、照度、MCP、角落感測器。"),
        page_break(),
        heading("Abstract", 1),
        paragraph(
            "Smart building and smart home systems require indoor environmental awareness to support comfort assessment, energy management, and device control. In ordinary rooms, however, influential appliances such as conventional air conditioners, manual windows, and ordinary lights often expose no telemetry, while only a small number of sensors can be installed. As a result, practical room-scale digital twins must work with both sparse observations and incomplete device-state information."
        ),
        paragraph(
            "This thesis proposes an MCP-enabled lightweight spatial digital twin prototype for a single room. The final design is a reduced-order bulk-plus-local field model with parameterized appliance influence functions, active-device power calibration, and trilinear residual correction from eight corner sensors. The system further learns environmental impact coefficients of non-networked appliances from before-and-after sensor observations, ranks candidate control actions according to target-zone comfort improvement, and extends the base estimator with an optional hybrid residual neural correction layer instead of replacing the base model with an end-to-end black-box predictor."
        ),
        paragraph(
            "The prototype is implemented in Python and exposed through a local Model Context Protocol server, enabling AI clients to query scenarios, estimate point-level environmental states, compare against an IDW baseline, learn appliance impacts, and run a 48-case window simulation matrix across time of day, weather, and season. Across the canonical scenarios, the base model achieves average MAE of 0.0482 for temperature, 0.1763 for humidity, and 2.1616 for illuminance, while the hybrid residual layer further reduces held-out field MAE. These results indicate that sparse corner sensing can still support an interpretable and trainable indoor twin when model structure, calibration, and learning are assigned to different layers."
        ),
        paragraph("Keywords: spatial digital twin, non-networked appliances, indoor environment modeling, temperature, humidity, illuminance, MCP, corner sensors."),
        page_break(),
        heading("目錄", 1),
        paragraph("第一章 緒論"),
        paragraph("第二章 文獻探討"),
        paragraph("第三章 系統架構與數學模型"),
        paragraph("第四章 系統實作與 MCP 服務"),
        paragraph("第五章 模擬案例與結果分析"),
        paragraph("第六章 結論與未來工作"),
        paragraph("參考文獻"),
        paragraph("附錄"),
        page_break(),
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
            "在原型開發初期，本研究曾嘗試將問題簡化為角落感測器插值或純局部影響場疊加，但很快發現兩個問題。第一，若只靠插值，模型雖能平滑填補空間，卻無法表達冷氣出風方向、窗邊日照或燈具位置等設備語意；第二，若只做局部場疊加，則容易出現設備附近變化明顯、全室平均狀態卻不合理的結果。這些實作經驗直接促成後續的 bulk + local field 架構、感測器校正流程，以及只把神經網路放在 residual correction 層的設計。"
        ),
        bullets(
            [
                "只知道角落感測器數值時，仍需要估計房間中央、靠窗區與門側區的三因子狀態。",
                "裝置沒有連網時，仍希望從環境變化中推估它是否對空間造成影響。",
                "新增或啟用冷氣、窗戶、照明後，系統應能估計其對不同區域造成的變化。",
                "學習裝置影響後，模型應能支援開冷氣、開窗或開燈等候選控制動作排序。",
                "將模型封裝為 MCP tools 後，AI client 或 agent 可用標準化工具介面查詢與使用數位孿生能力。",
            ]
        ),
        heading("1.3 研究問題", 2),
        bullets(
            [
                "RQ1：在只有 8 顆角落感測器的條件下，是否能建立單房間溫度、濕度與照度的空間估計模型？",
                "RQ2：在家電或環境裝置沒有連網狀態回報的情況下，是否能從環境感測資料學習其對空間不同區域的影響？",
                "RQ3：學習後的裝置影響模型是否能提升對三個環境變數的控制決策，例如選擇開冷氣、開窗或開燈？",
                "RQ4：將數位孿生模型封裝為 MCP tools 後，是否能讓 AI client 以標準化方式查詢、模擬與使用控制推薦能力？",
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
                "控制功能只做候選動作排序，不做自動閉環控制。",
                "MCP 部分定位為本地 stdio server 與 AI-agent-accessible interface，不宣稱提出新的 MCP protocol。",
            ]
        ),
        heading("1.5 預期貢獻", 2),
        bullets(
            [
                "提出一個以單房間、8 顆角落感測器為前提的三因子空間數位孿生原型，明確描述 temperature、humidity 與 illuminance 場。",
                "建立包含 bulk + local field、active device power calibration、trilinear correction 與裝置影響學習的可解釋估測流程。",
                "建立訓練資料組裝與 hybrid residual correction 路線，使真實感測資料可用於參數校正、影響學習與殘差修正，而非直接取代主模型。",
                "提出可對接 MCP、Web demo 與公開資料集 task-aligned benchmark 的研究原型與評估框架。",
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
            "在感測器數量有限的情況下，最直接的方法是使用空間插值估計未量測位置。本研究採用 inverse distance weighting（IDW）作為 baseline。IDW 的優點是實作簡單且不依賴設備先驗，但其估計完全由量測點距離決定，無法反映冷氣出風方向、窗戶位置、照明熱源或設備作用範圍等結構資訊。相較之下，zonal model 與 hybrid spatial model 提供了介於 well-mixed room model 與 CFD 之間的折衷途徑，可在維持較低計算成本的同時保留主要空間差異 [4][5][6]。因此，本研究將場模型設計為 bulk + local field：以 bulk state 描述房間整體平均狀態的時間收斂，以 local field 表示設備附近與特定區域的空間差異，藉此兼顧可解釋性與可計算性。"
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
            "Model Context Protocol（MCP）提供一種標準化工具介面，使外部模型或 AI client 能以一致方式呼叫系統能力。本研究將數位孿生原型封裝為本地 MCP server，使情境查詢、場估計、動作排序、點位取樣與窗戶條件模擬等功能，可被 AI agent 直接使用。需要強調的是，MCP 在本研究中的角色屬於系統整合與工具化封裝，用以驗證數位孿生模型可被外部 AI 系統操作，而非針對 MCP 通訊協定本身提出新方法。"
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
            "若希望讓不同方法在同一資料集上進行對比，較可行的作法不是要求所有方法都重建完整單房間 3D 空間場，而是採用 shared-task benchmark，也就是在相同資料集上只比較共同可觀測、共同可輸出的子任務。換言之，比較的單位應從「整個系統是否完全同構」改為「在同一份資料上，哪些輸入、哪些輸出、哪些評估指標是所有方法都能公平處理的」。在此原則下，本研究模型可以退化為 dataset-compatible mode：當資料集只有 zone-level 序列時，就比較區域平均值預測；當資料集只有兩個室內量測點時，就比較點位響應；當資料集缺少裝置狀態時，則只比較 background dynamics 或 comfort scoring，而不宣稱完成完整場重建。"
        ),
        paragraph(
            "具體而言，本研究可採兩層 benchmark 設計。第一層是 canonical synthetic benchmark，直接使用本研究的 8 組標準情境與 48 組窗戶矩陣，讓主模型、IDW baseline、移除設備先驗的純資料驅動模型，以及 hybrid residual correction 在完全相同的輸入、感測器配置與 ground truth 下比較 field MAE、zone MAE、sensor MAE 與推薦改善分數。第二層是 public task-aligned benchmark，亦即把公開資料集拆成與本研究相容的子任務：CU-BEMS 可用於比較 AC/lighting 事件前後的 zone-level temperature、humidity、illuminance 響應；SML2010 可用於比較窗戶/日照相關的溫濕度照度時序響應；Denmark IEQ 與 ASHRAE Global Thermal Comfort Database II 則適合比較舒適度目標函數、偏差分數或分類準確率。"
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
            "本研究系統由五個主要模組組成：房間與設備設定、三因子影響場模型、角落感測器校正、非連網裝置影響學習、以及控制動作排序與 MCP 工具介面。整體流程為：輸入房間幾何、設備位置與外部環境條件後，模型先建立背景場，再加入設備影響函數，接著使用 8 顆角落感測器觀測值校準 active device power scale 並建立 trilinear 校正場，最後輸出任意座標或目標區域的三因子估計與候選控制動作排序。"
        ),
        image(
            "outputs/figures/architecture/整體分層架構.svg",
            "圖 3-1 系統整體分層架構。此圖說明 Web、MCP/Gemma 入口如何共用 service layer，並串接主模型與 hybrid residual layer。",
            asset_name="fig_3_1_overall_architecture",
        ),
        image(
            "outputs/figures/architecture/主要執行資料流.svg",
            "圖 3-2 主要執行資料流。此圖對應一次 scenario 評估如何從輸入設定、場估計、校正、到 dashboard 與 MCP 輸出。",
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
            asset_name="fig_3_3_room_topology",
        ),
        heading("3.3 三因子場模型", 2),
        paragraph("本研究將室內狀態定義為三個空間與時間函數："),
        code("T(x, y, z, t): temperature field\nH(x, y, z, t): humidity field\nL(x, y, z, t): illuminance field"),
        paragraph("任一環境因素 v 的估計場可表示為："),
        code("F_v(x, y, z, t) = B_v^bulk(t) + B_v^local(x, y, z, t) + Σ I_j,v^local(x, y, z, t) + C_v(x, y, z)"),
        bullets(
            [
                "B_v^bulk：房間整體平均狀態，描述全室在時間軸上逐漸接近準穩態的平均變化。",
                "B_v^local：局部背景場，保留簡化垂直分層與空間差異。",
                "I_j,v^local：第 j 個設備對環境因素 v 的局部影響函數。",
                "C_v：由感測器殘差推估出的校正場。",
            ]
        ),
        paragraph(
            "其中 bulk 與 local 的分離是本研究模型的重要改良。若僅使用局部影響場，容易產生冷氣附近很冷，但房間遠端幾乎維持原溫的不合理結果；加入 bulk state 後，模型能同時表示整體房間平均溫濕度的時間響應，以及冷氣出風口、窗邊交換與照明附近的局部差異。此設計也更接近 reduced-order spatial twin 與 zonal or hybrid model 的方法定位 [4][6]。"
        ),
        heading("3.4 設備影響函數", 2),
        bullets(
            [
                "冷氣：主要造成局部降溫，並帶有弱除濕效果；3D 視覺化中以牆面橫條表示。",
                "窗戶：受外部溫度、外部濕度與日照條件影響，同時改變三個環境因素；3D 視覺化中以牆面矩形表示。",
                "照明：主要提升照度，並產生少量熱效應；3D 視覺化中以點狀標記表示。",
            ]
        ),
        heading("3.5 感測器校正模型", 2),
        paragraph(
            "模型先預測 8 顆角落感測器位置的三因子值，再與觀測值比較得到殘差。為提高環境估計精度，系統先以最小平方法估計 active device 的 power scale，使設備影響函數更接近觀測資料；接著對每一個環境因素，以 8 參數 trilinear correction 擬合角落殘差："
        ),
        code("C(x, y, z) = c0 + c1*X + c2*Y + c3*Z + c4*X*Y + c5*X*Z + c6*Y*Z + c7*X*Y*Z"),
        paragraph(
            "其中 X、Y、Z 為正規化後的房間座標。相較於一階 affine surface，trilinear correction 可使用 8 個角點支撐 8 個校正係數，除了整體偏移與一階梯度外，也能表示角落之間的交互變化。不過此方法仍無法重建任意高頻局部變化，因此其定位仍是低成本、可解釋的場校正方法。"
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
            "為了讓模型不只停留在手動指定參數，本研究將資料流程拆成原始紀錄層、對齊整併層、樣本建構層與模型訓練層。原始資料至少包含四類：角落感測器時序、裝置事件紀錄、室外環境時序，以及情境描述或額外空間量測。角落感測器時序紀錄 8 顆節點在各時間點的 temperature、humidity 與 illuminance；裝置事件紀錄保存冷氣、窗戶與燈的啟用狀態、模式、設定溫度與開窗比例；室外環境時序提供 outdoor temperature、outdoor humidity 與 sunlight；情境描述則記錄房間尺寸、目標區域、家具配置與採樣設定。"
        ),
        table(
            ["資料表", "主要欄位", "角色"],
            [
                ["corner_sensor_timeseries", "timestamp, sensor_name, x, y, z, temperature, humidity, illuminance", "提供 8 顆角落感測器觀測值，用於校正、裝置影響學習與真實資料 fine-tune"],
                ["device_event_log", "timestamp, device_name, device_kind, activation, mode, target_temperature, opening_ratio", "還原各時間點裝置狀態，並作為特徵與影響學習依據"],
                ["outdoor_environment", "timestamp, outdoor_temperature, outdoor_humidity, sunlight_illuminance, daylight_factor", "提供窗戶影響函數與時間條件所需的外部邊界"],
                ["scenario_metadata / spatial_probe_ground_truth", "房間尺寸、家具配置、目標區域、額外空間量測", "定義情境與提供較密集的監督標籤"],
            ],
        ),
        paragraph(
            "在資料對齊階段，系統會先以時間戳記為主鍵，將感測器時序、裝置事件與外部環境資料同步到同一時間軸。接著根據房間幾何與裝置配置，將每個時間點的狀態送入主模型，得到 F_v(x, y, z, t) 的 physics estimate。若為影響係數學習，則以裝置啟用前後的感測器差值建立 sensor delta；若為 hybrid residual neural network，則進一步在空間採樣點上建立 feature-target 配對。"
        ),
        paragraph("對於 hybrid residual 訓練，本研究在每個採樣點 p_i=(x_i, y_i, z_i) 與時間點 t_i 上組合特徵向量："),
        code(
            "φ_i = [x_i, y_i, z_i, t_i, indoor baseline, outdoor conditions,\n"
            "       F_temperature, F_humidity, F_illuminance,\n"
            "       device activations, device powers, influence envelopes]"
        ),
        paragraph("若採用目前的模擬訓練設定，標籤來自 truth field 與主模型估計值之差："),
        code("y_i^v = F_v^truth(p_i, t_i) - F_v(p_i, t_i)"),
        paragraph(
            "其中 v 分別代表 temperature、humidity 與 illuminance。換言之，神經網路不是直接學整個場，而是學主模型剩餘誤差。若未來接入真實資料，則可分成兩種層次：第一種只使用 8 顆角落感測器，將其作為參數校正、裝置影響學習與角落 residual fine-tune 的監督訊號；第二種則在有移動式量測或額外空間探針時，再擴充為更完整的空間 residual 訓練。這樣可避免只憑 8 個角落點就對全室高解析度場做過度宣稱。"
        ),
        paragraph(
            "整體而言，本研究的訓練資料流程可概括為：原始感測與事件資料先經時間對齊與情境整併，再由主模型產生 physics estimate，最後依任務不同分流為 least-squares impact learning、bulk parameter calibration 或 hybrid residual neural training。此設計的優點在於，即使未來資料來源從模擬切換到真實 ESP32 量測，資料進入訓練流程的接口仍可保持一致。"
        ),
        heading("3.8 Hybrid Residual Neural Network 延伸", 2),
        paragraph(
            "雖然主模型已具有可解釋的 bulk + local field 結構，但在設備交互作用、局部照度分布或窗邊複合邊界條件下，仍可能存在系統性殘差。為此，本研究不以純黑盒神經網路取代主模型，而是加入 hybrid residual neural network 作為第二層修正器："
        ),
        code("F_v^hybrid(x, y, z, t) = F_v(x, y, z, t) + R_v(x, y, z, t; θ_v)"),
        paragraph("其中 `F_v` 為第三章前述的 reduced-order 主模型，`R_v` 則由小型多層感知器近似其殘差。訓練目標定義為："),
        code("R_v*(x, y, z, t) = F_v^truth(x, y, z, t) - F_v(x, y, z, t)"),
        paragraph("其損失函數可表示為："),
        code("L(θ_v) = (1 / N) Σ_i ||R_v*(p_i, t_i) - R_v(p_i, t_i; θ_v)||^2 + λ||θ_v||^2"),
        paragraph(
            "本研究將座標、時間、室內外環境條件、主模型估計值、設備 activation、設備 power 與 influence envelope 作為輸入特徵，分別為溫度、濕度與照度訓練三個小型殘差網路。此設計的目的在於保留主模型可解釋性，同時以資料驅動方式修正其剩餘誤差。"
        ),
        heading("3.9 控制動作排序", 2),
        paragraph(
            "本研究不做閉環控制，而是對候選控制動作進行排序。系統針對每個候選動作模擬目標區域的三因子值，並依舒適度目標計算改善分數。若房間偏熱，冷氣動作通常獲得較高排序；若照度不足，照明動作通常獲得較高排序。"
        ),
        page_break(),
        heading("第四章 系統實作與 MCP 服務", 1),
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
                ["web_demo.py", "提供本地可旋轉 3D web demo"],
            ],
        ),
        heading("4.2 MCP Tools", 2),
        paragraph("本地 MCP server 提供下列 tools："),
        bullets(
            [
                "list_scenarios：列出 8 組標準驗證情境。",
                "list_window_scenarios：列出 48 組窗戶時段/天氣/季節情境。",
                "run_scenario：執行情境並回傳重建誤差與目標區域估計。",
                "rank_actions：依目標區域舒適度改善排序候選動作。",
                "sample_point：估計指定座標的 temperature、humidity 與 illuminance。",
                "compare_baseline：比較本研究模型與 IDW baseline。",
                "learn_impacts：由前後感測資料學習非連網裝置影響。",
                "run_window_matrix：執行全部 48 組窗戶矩陣模擬。",
                "run_window_direct：直接輸入外部溫度、濕度、日照與開窗比例，執行窗戶影響模擬。",
            ]
        ),
        heading("4.3 Gemma/Ollama Bridge", 2),
        paragraph(
            "本研究以本機 Ollama 上之 Gemma 模型作為語言介面，並以 Python bridge 串接數位孿生服務。實測顯示，本機 Gemma 可透過 Ollama 進行 tool calling；但 MCP 支援本質上來自主機端或 client/runtime 層，而非模型權重本身。因此本研究採用的設計是：由 Gemma 將自然語言請求轉為工具選擇，Python bridge 執行數位孿生服務或 MCP server 所提供的工具，再把工具輸出回送給 Gemma 生成最終回答。這樣的設計比直接宣稱模型原生支援 MCP 更準確，也更符合目前本地 AI agent 的實作方式。"
        ),
        heading("4.4 Web Demo", 2),
        paragraph(
            "Web demo 以 idle 房間背景為基礎，透過 ac_main、window_main 與 light_main checkbox 組合設備狀態，不使用下拉式情境選單。3D 預覽可拖曳旋轉與縮放，並以牆面橫條標示冷氣、牆面矩形標示窗戶、點狀標記表示照明。Metric 亦以勾選式控制切換 temperature、humidity 與 illuminance。左側固定欄位提供 Indoor Baseline 設定，使室內基準溫度、濕度與照度可直接調整；窗戶區則保留季節、天氣與時段 preset，並允許使用者手動覆寫外部溫度與開窗比例。互動式 3D 預覽上方另提供時間軸與播放控制，可觀察系統從啟動到接近準穩態的過程。最新版本的 Web UI 另外提供 estimator toggle，可在主模型與 hybrid residual corrected field 之間切換，並同步更新 target zone、recommendation ranking、baseline comparison、impact panel、3D volume、point sample 與 timeline。"
        ),
        page_break(),
        heading("第五章 模擬案例與結果分析", 1),
        heading("5.1 標準情境設定", 2),
        paragraph(
            "本研究建立 8 組標準情境，包含無設備作用、僅冷氣、僅開窗、僅照明、冷氣與窗戶、窗戶與照明、冷氣與照明，以及三者同時作用。每組情境均輸出場重建誤差、區域平均值、感測器校正效果、IDW baseline 比較、非連網裝置影響學習與推薦排序。"
        ),
        image(
            "outputs/figures/architecture/驗證與實驗流程圖.svg",
            "圖 5-1 驗證與實驗流程。此圖說明標準情境如何經由 truth adjustment、合成觀測、校正估測、baseline 比較與輸出摘要，形成第五章的實驗結果。",
            asset_name="fig_5_1_validation_flow",
        ),
        table(
            ["情境", "中央溫度", "中央濕度", "中央照度", "最佳推薦"],
            [
                ["idle", "28.84", "67.60", "90.00", "ac_and_light"],
                ["ac_only", "26.90", "66.46", "90.00", "turn_on_light"],
                ["window_only", "29.11", "67.95", "205.41", "ac_and_light"],
                ["light_only", "29.10", "67.60", "425.65", "turn_on_ac"],
                ["all_active", "27.40", "66.73", "449.65", "turn_on_ac"],
            ],
        ),
        heading("5.2 場重建誤差", 2),
        paragraph(
            "8 組標準情境中，平均溫度 MAE 為 0.0482，平均濕度 MAE 為 0.1763，平均照度 MAE 為 2.1616。照度 MAE 較高，主要原因是照度場受燈具位置、窗戶日照與方向性影響較大，且數值尺度遠高於溫度與濕度。相較於先前一階 affine 校正設定，trilinear correction 與 active device power scale 校準降低了三個環境因素的平均重建誤差。"
        ),
        heading("5.3 IDW Baseline 比較", 2),
        paragraph(
            "以 light_only 情境為例，本研究模型在照度 MAE 上相較 IDW baseline 降低約 97.73%。這表示只依靠角落感測器插值難以重建中央燈具造成的局部照度提升，而加入設備位置、影響函數、power scale 校準與 trilinear residual correction 後，可更有效描述設備作用。"
        ),
        heading("5.4 非連網裝置影響學習", 2),
        paragraph(
            "在 ac_only 情境中，模型學得冷氣對 temperature 的係數為負，對 humidity 的係數亦為負，對 illuminance 則接近零，符合冷氣降溫與弱除濕的模型假設。在 light_only 情境中，照明主要提升 illuminance，並帶來少量正向熱效應。這些結果顯示，即使裝置本身不回報狀態，仍可由環境感測變化估計其影響方向與相對強度。"
        ),
        heading("5.5 窗戶時段、天氣、季節矩陣與直接輸入", 2),
        paragraph(
            "本研究新增 48 組窗戶矩陣情境，組合 4 個時段、3 種天氣與 4 個季節。此矩陣可作為外部環境變數敏感度分析，用於說明窗戶在不同外部條件下對靠窗區與中心區的溫度、濕度與照度影響。"
        ),
        paragraph(
            "除列舉矩陣外，系統亦支援窗戶 direct input 模式。使用者可直接提供外部溫度、外部濕度、外部日照照度、開窗比例，以及可選的室內基準溫濕度。此模式適合接入即時天氣資料、手動量測資料或使用者指定條件，不必先將外部條件離散化為季節、天氣與時段分類。"
        ),
        table(
            ["情境", "外部溫度", "外部濕度", "外部日照", "窗戶區照度"],
            [
                ["window_summer_sunny_noon", "37.0", "71.0", "36000.0", "237.7066"],
                ["window_winter_rainy_night", "11.0", "78.0", "15.2", "68.9714"],
                ["window_spring_cloudy_morning", "21.5", "70.0", "5005.0", "92.3808"],
            ],
        ),
        heading("5.6 Hybrid Residual Neural Network 結果", 2),
        paragraph(
            "在目前預設的 held-out 測試設定下，hybrid residual neural network 以 6 個情境作為訓練資料，並以 `light_only` 與 `all_active` 作為測試情境。結果顯示，若將 hybrid residual correction 套用於主模型輸出，field MAE 可由 temperature `0.0473`、humidity `0.1764`、illuminance `2.3727`，分別降至 `0.0026`、`0.0043` 與 `0.2357`。對應改善比例約為溫度 `94.50%`、濕度 `97.56%` 與照度 `90.07%`。"
        ),
        paragraph(
            "此結果說明，將神經網路定位為殘差修正層，而非直接取代主模型，可在保留設備影響函數、時間響應與感測器校正可解釋性的前提下，進一步降低 held-out 情境的空間重建誤差。不過此結果仍建立於模擬資料與既定情境分割下，未來仍需以真實量測資料重新訓練與驗證。"
        ),
        heading("5.7 公開資料集對比策略", 2),
        paragraph(
            "若要回應不同方法在同一資料來源上的公平比較，本研究不主張所有實驗都必須直接對到同一個公開資料集，而是將比較拆成相容子任務。對完整 3D 空間場重建而言，目前仍以本研究的 canonical synthetic benchmark 最公平，因為只有這一層同時具備完整房間幾何、設備狀態、8 顆角落感測器配置與 dense ground truth。對公開資料集而言，則應退回資料集真正支援的輸出層級，例如區域平均值、點位時序響應或舒適度分數。"
        ),
        paragraph(
            "因此，CU-BEMS 比較適合用來對比 AC 與照明事件對 zone-level temperature、humidity 與 illuminance 的影響；SML2010 比較適合對比窗戶、日照與外氣條件造成的兩點溫濕度照度響應；ASHRAE 與住宅 IEQ 類資料則更適合對比舒適度目標函數與控制評分的合理性。這樣的 task-aligned benchmark 可以讓本研究與其他方法在相同輸入、相同輸出與相同指標下比較，而不需要誇大公開資料集與本研究場景完全一致。"
        ),
        heading("5.8 研究過程與實作挑戰", 2),
        paragraph(
            "本研究在實作過程中有三個直接影響最終模型設計的問題。第一，初期若僅使用 local field 疊加設備作用，會出現冷氣附近快速降溫、房間遠端卻幾乎維持原溫的不合理結果，因此後續必須加入 bulk state 描述全室平均狀態的時間收斂。第二，若只以 8 顆角落感測器直接監督整個 3D 場，則黑盒神經網路雖可能把角落點擬合得很好，但對室內中央、窗邊與家具後方的場仍缺乏足夠監督，因此本研究把神經網路限制在 residual correction 層，而不是直接取代主模型。第三，公開資料集與本研究情境在幾何、裝置標記與感測器拓樸上通常不一致，因此必須採用 task-aligned benchmark，不能直接把所有實驗都搬到同一公開資料集上比較。"
        ),
        paragraph(
            "這些困難也說明本研究的設計取捨不是任意拼接，而是由實作過程逐步收斂而來：bulk + local field 負責處理全室與局部差異，trilinear correction 負責利用有限角落感測器修正低階偏差，least-squares impact learning 負責從設備前後差異學習非連網裝置影響，hybrid residual neural network 則只處理主模型尚未吸收的系統性誤差。"
        ),
        heading("5.9 可旋轉 3D 展示", 2),
        paragraph(
            "Web demo 提供可旋轉 3D 預覽，使使用者可直接觀察三因子點雲、房間框線與設備幾何位置。冷氣以牆面橫條表示，窗戶以牆面矩形表示，照明以點狀標記表示。此展示有助於口試或公開展示時說明模型如何從設備位置與環境場估計區域影響。"
        ),
        page_break(),
        heading("第六章 結論與未來工作", 1),
        heading("6.1 結論", 2),
        paragraph(
            "本研究建立一個 MCP-enabled 單房間三因子空間數位孿生原型，針對非連網家電或環境裝置對 temperature、humidity 與 illuminance 造成的影響進行建模、校正與學習。透過 8 顆角落感測器、設備影響函數、active device power scale 校準與 trilinear 校正場，系統能估計房間內任意位置與指定區域的三因子狀態。模擬結果顯示，加入設備影響模型後，在冷氣、窗戶與照明等情境下能提供較 IDW baseline 更可解釋且更精細的場估計；進一步加入 hybrid residual neural correction 後，held-out 情境的場重建誤差可再顯著下降。"
        ),
        paragraph(
            "此外，本研究將模型封裝為 MCP server，並提供 Gemma/Ollama bridge 與 web demo，使數位孿生不只是離線模擬程式，而是可被 AI client 或使用者互動查詢的工具化系統。整體成果符合研究目標：在有限感測器與非連網裝置條件下，學習裝置對空間環境的影響，並用於更準確的控制動作推薦。"
        ),
        paragraph(
            "另一項結論是，公開資料集並非不能使用，而是必須依資料本身支援的任務層級進行比較。對完整 3D 場重建，本研究目前仍以 canonical synthetic benchmark 作為主要依據；對 zone-level 響應、兩點時序響應與舒適度評分，則可分別利用相容的公開資料建立 task-aligned benchmark。此作法比直接宣稱所有資料集都能完整驗證本研究系統更嚴謹。"
        ),
        heading("6.2 研究限制", 2),
        bullets(
            [
                "目前結果主要來自文獻參數與合理物理假設模擬，尚未加入大量真實房間資料。",
                "模型不處理多房間氣流、牆體熱容或完整流體動力學。",
                "濕度模型採簡化耦合，驗證強度低於溫度與照度。",
                "公開資料集多缺乏完整單房間幾何與 dense ground truth，因此無法直接作為 full-field benchmark。",
                "MCP server 目前為本地 stdio 版本，尚未包含遠端部署、OAuth 或多使用者管理。",
                "控制功能為推薦排序，尚未進入自動閉環控制。",
            ]
        ),
        heading("6.3 未來工作", 2),
        bullets(
            [
                "加入實體 ESP32 感測器資料，以校正與驗證模型參數。",
                "擴充自訂房間 JSON 輸入，使系統可支援不同房間尺寸與設備位置。",
                "加入更多環境變數，例如 CO2、PM2.5 或人體熱源。",
                "將 MCP server 擴充為遠端 HTTP MCP，並加入權限控管。",
                "進一步研究閉環控制，將推薦排序延伸為實際控制策略。",
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
        code("python3 scripts/run_demo.py\npython3 scripts/run_window_matrix.py\npython3 scripts/run_hybrid_residual_experiment.py\npython3 scripts/run_web_demo.py\npython3 scripts/run_mcp_server.py"),
        heading("附錄 B：Web Demo 操作", 1),
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
            ]
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


def page_break() -> Block:
    return {"type": "page_break"}


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
    if indent:
        ppr.append('<w:ind w:left="720" w:hanging="360"/>')
    ppr.append('<w:spacing w:after="120" w:line="360" w:lineRule="auto"/>')
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
  <dc:title>基於 MCP 之單房間非連網家電環境影響學習與三因子控制數位孿生原型</dc:title>
  <dc:creator>Codex generated draft</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
'''


def app_props_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex stdlib docx generator</Application>
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
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Microsoft JhengHei"/>
        <w:sz w:val="24"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Microsoft JhengHei"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr><w:b/><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Microsoft JhengHei"/><w:sz w:val="34"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:eastAsia="Microsoft JhengHei"/><w:sz w:val="20"/></w:rPr>
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
