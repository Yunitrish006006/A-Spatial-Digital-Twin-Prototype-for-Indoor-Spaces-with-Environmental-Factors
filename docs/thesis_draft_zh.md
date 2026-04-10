# 國立彰化師範大學

# 資訊工程學系碩士班

# 碩士論文初稿

# 基於 MCP 之單房間非連網家電環境影響學習與三因子控制數位孿生原型

An MCP-Enabled Lightweight Spatial Digital Twin Prototype for Learning the Environmental Impact of Non-Networked Appliances in a Single Room

研究生：林昀佑

指導教授：易昶霈

版本：論文初稿 v0.1

日期：2026 年 4 月 10 日


---


# 摘要

智慧建築與智慧居家系統通常需要掌握室內環境狀態，才能支援舒適度評估、能源管理與設備控制。然而，實際場域中仍有許多會影響環境的家電或環境裝置並沒有連網能力，也沒有 API 可直接回報自身狀態或運轉功率。例如傳統冷氣、手動窗戶與一般照明雖會改變室內環境，卻不一定能被系統直接讀取。若系統僅依賴智慧裝置回報，便難以建立完整且可用於控制決策的室內環境模型。

本研究以單一矩形房間為研究場域，提出一個基於有限角落感測器與連續影響場估計之三因子空間數位孿生原型。模型將室內狀態定義為溫度、濕度與照度三個空間場，並以冷氣、窗戶與照明之參數化影響函數描述非連網裝置對不同區域的影響。系統固定使用 8 顆角落感測器，即天花板四角與地面四角，每個節點量測溫度、濕度與照度，並以感測器殘差擬合 affine 校正場，以修正背景場與設備影響函數之偏差。

除空間場估計外，本研究亦建立裝置啟用前後感測資料之影響學習流程，透過最小平方法估計非連網裝置的環境影響係數，並根據目標區域的舒適度偏差輸出候選控制動作排序。為提升系統可存取性，本研究將模型能力封裝為本地 Model Context Protocol（MCP）服務，提供情境查詢、模擬、座標估計、baseline 比較、影響學習、窗戶時段/天氣/季節矩陣模擬與窗戶外部條件直接輸入模擬等工具。最後，本研究以 Python 原型、模擬案例、IDW baseline 比較、48 組窗戶矩陣、窗戶 direct input 與可旋轉 3D web demo 驗證模型之可解釋性與實作可行性。

關鍵字：空間數位孿生、非連網家電、室內環境建模、溫度、濕度、照度、MCP、角落感測器。


---


# Abstract

Smart building and smart home systems require an understanding of indoor environmental conditions to support comfort assessment, energy management, and device control. However, many appliances and environmental elements in real rooms are not network-connected and cannot directly report their states or operating power. Conventional air conditioners, manual windows, and ordinary lights may significantly affect indoor temperature, humidity, and illuminance, yet remain invisible to API-based control systems.

This thesis proposes an MCP-enabled lightweight spatial digital twin prototype for a single room. The proposed model represents the room state as three environmental fields: temperature, humidity, and illuminance. Parameterized influence functions are used to describe the effects of air conditioning, windows, and lighting, while eight corner sensor nodes are used to calibrate the estimated fields through an affine residual correction model. The system further learns environmental impact coefficients of non-networked appliances from before-and-after sensor observations, and ranks candidate control actions according to target-zone comfort improvement.

The prototype is implemented in Python and exposed through a local Model Context Protocol server, enabling AI clients to query scenarios, estimate point-level environmental states, compare against an IDW baseline, learn appliance impacts, and run a 48-case window simulation matrix across time of day, weather, and season. Simulation results and an interactive rotatable 3D web demo demonstrate the feasibility and interpretability of the proposed approach.

Keywords: spatial digital twin, non-networked appliances, indoor environment modeling, temperature, humidity, illuminance, MCP, corner sensors.


---


# 目錄

第一章 緒論

第二章 文獻探討

第三章 系統架構與數學模型

第四章 系統實作與 MCP 服務

第五章 模擬案例與結果分析

第六章 結論與未來工作

參考文獻

附錄


---


# 第一章 緒論

## 1.1 研究背景

智慧家庭與智慧建築系統逐漸被用於室內環境監控、能源管理與舒適度控制。這類系統通常需要知道空間中溫度、濕度與照度的分布，才能判斷使用者所在區域是否過熱、過暗或過於潮濕。然而，實際房間內不可能在每一個位置都布建感測器，因此系統往往只能取得少量離散點位資料。若僅依賴單點或少數點位量測，容易忽略同一空間中不同區域的環境差異。

另一方面，許多既有家電並不是智慧裝置。傳統冷氣、一般開關照明或手動窗戶可能無法連網，也無法主動回報開關狀態、出力或作用範圍。這些裝置雖然無法被直接讀取，卻會持續改變室內環境。若數位孿生模型只依賴智慧裝置 API，將無法完整描述一般房間中的環境變化。因此，本研究關注的核心問題是：如何透過有限感測器觀測資料，學習非連網裝置對空間環境造成的影響，並將此學習結果用於更準確的三因子控制推薦。

## 1.2 研究動機

- 只知道角落感測器數值時，仍需要估計房間中央、靠窗區與門側區的三因子狀態。
- 裝置沒有連網時，仍希望從環境變化中推估它是否對空間造成影響。
- 新增或啟用冷氣、窗戶、照明後，系統應能估計其對不同區域造成的變化。
- 學習裝置影響後，模型應能支援開冷氣、開窗或開燈等候選控制動作排序。
- 將模型封裝為 MCP tools 後，AI client 或 agent 可用標準化工具介面查詢與使用數位孿生能力。

## 1.3 研究問題

- RQ1：在只有 8 顆角落感測器的條件下，是否能建立單房間溫度、濕度與照度的空間估計模型？
- RQ2：在家電或環境裝置沒有連網狀態回報的情況下，是否能從環境感測資料學習其對空間不同區域的影響？
- RQ3：學習後的裝置影響模型是否能提升對三個環境變數的控制決策，例如選擇開冷氣、開窗或開燈？
- RQ4：將數位孿生模型封裝為 MCP tools 後，是否能讓 AI client 以標準化方式查詢、模擬與使用控制推薦能力？

## 1.4 研究範圍與限制

- 研究場域固定為單一矩形房間，不處理多房間或跨空間空氣交換。
- 感測器配置固定為天花板四角與地面四角，共 8 顆角落節點。
- 設備類型聚焦於冷氣、窗戶與照明。
- 模型為簡化動態模型，不追求 CFD 等級高精度流場。
- 濕度保留於模型中，但作為次核心變數處理。
- 控制功能只做候選動作排序，不做自動閉環控制。
- MCP 部分定位為本地 stdio server 與 AI-agent-accessible interface，不宣稱提出新的 MCP protocol。

## 1.5 預期貢獻

- 提出單房間三因子空間數位孿生原型，描述 temperature、humidity 與 illuminance 場。
- 建立可由 8 顆角落感測器校正的環境場估計流程。
- 建立非連網冷氣、窗戶與照明之參數化影響函數與影響學習流程。
- 提供目標區域導向的候選控制動作排序方法。
- 將模型封裝為 MCP tools，讓 AI client 能查詢情境、估計座標點與取得控制推薦。
- 提供可重現 Python 原型、48 組窗戶矩陣模擬、窗戶 direct input 模擬與可旋轉 3D web demo。


---


# 第二章 文獻探討

## 2.1 室內環境建模

室內環境建模常見目標包含熱舒適評估、能源管理、HVAC 控制與照明控制。高精度方法如 CFD 可描述細緻空氣流動與熱交換，但建模成本高、計算量大，且需要詳細邊界條件。本研究採用較輕量的連續影響場模型，以可解釋、低成本與易部署為主要設計取向。

## 2.2 空間插值與場估計

當感測器數量有限時，常見做法是以空間插值估計未量測位置。本研究加入 IDW 作為 baseline，並與 appliance influence model 比較。IDW 僅依據感測器距離權重重建場，不使用設備位置與方向資訊；本研究模型則將背景場、設備影響函數與感測器校正場結合，因此可在設備影響明顯時提供更可解釋的估計。

## 2.3 數位孿生與智慧建築

數位孿生通常表示實體系統在數位空間中的動態對應模型。在智慧建築中，數位孿生可整合 BIM、IoT 感測資料與設備控制資訊。本研究不建立完整 BIM/BMS 系統，而是聚焦於單房間、低成本感測器與非連網裝置條件下的簡化數位孿生原型。

## 2.4 非連網裝置影響學習

既有智慧家庭研究多半假設裝置能被直接讀取或控制。然而真實環境中，許多裝置沒有網路能力。此時系統需要從環境變化反推裝置影響。本研究將裝置啟用前後的感測器差異視為學習資料，使用裝置空間影響基底與最小平方法估計其對三個環境因素的影響係數。

## 2.5 MCP 與 AI Agent Tool Interface

Model Context Protocol（MCP）可讓外部模型或 AI client 以標準化工具介面存取系統能力。本研究將數位孿生原型封裝為本地 MCP server，使情境查詢、場估計、動作排序與座標查詢可被 AI agent 直接呼叫。MCP 在本研究中的定位是系統整合與展示介面，而非通訊協定本身的創新。


---


# 第三章 系統架構與數學模型

## 3.1 系統架構

本研究系統由五個主要模組組成：房間與設備設定、三因子影響場模型、角落感測器校正、非連網裝置影響學習、以及控制動作排序與 MCP 工具介面。整體流程為：輸入房間幾何、設備位置與外部環境條件後，模型先建立背景場，再加入設備影響函數，接著使用 8 顆角落感測器觀測值校正場估計，最後輸出任意座標或目標區域的三因子估計與候選控制動作排序。

## 3.2 房間、區域與感測器設定

標準房間尺寸設定為寬 6.0 m、長 4.0 m、高 3.0 m。感測器固定於地面四角與天花板四角，共 8 顆節點。每個節點皆假設可量測 temperature、humidity 與 illuminance。區域劃分包含 window_zone、center_zone 與 door_side_zone，用於比較不同空間區域受到設備影響的差異。

| 項目 | 設定 |
| --- | --- |
| 房間尺寸 | 6.0 m × 4.0 m × 3.0 m |
| 感測器數量 | 8 顆角落節點 |
| 三個環境因素 | Temperature, Humidity, Illuminance |
| 主要區域 | window_zone, center_zone, door_side_zone |
| 設備類型 | ac_main, window_main, light_main |

## 3.3 三因子場模型

本研究將室內狀態定義為三個空間與時間函數：

```text
T(x, y, z, t): temperature field
H(x, y, z, t): humidity field
L(x, y, z, t): illuminance field
```

任一環境因素 v 的估計場可表示為：

```text
F_v(x, y, z, t) = B_v(x, y, z) + Σ I_j,v(x, y, z, t) + C_v(x, y, z)
```

- B_v：背景場，描述無設備作用時的基本環境分布。
- I_j,v：第 j 個設備對環境因素 v 的影響函數。
- C_v：由感測器殘差推估出的校正場。

## 3.4 設備影響函數

- 冷氣：主要造成局部降溫，並帶有弱除濕效果；3D 視覺化中以牆面橫條表示。
- 窗戶：受外部溫度、外部濕度與日照條件影響，同時改變三個環境因素；3D 視覺化中以牆面矩形表示。
- 照明：主要提升照度，並產生少量熱效應；3D 視覺化中以點狀標記表示。

## 3.5 感測器校正模型

模型先預測 8 顆角落感測器位置的三因子值，再與觀測值比較得到殘差。對每一個環境因素，系統以 affine surface 擬合殘差：

```text
delta(x, y, z) = a0 + a1*x + a2*y + a3*z
```

此校正方式無法重建任意高頻局部變化，但能修正整體偏移與一階空間梯度，符合固定 8 顆角落感測器的低成本設計目標。

## 3.6 非連網裝置影響學習

對非連網裝置，系統不依賴裝置 API，而是由啟用前後的感測器變化估計影響係數。流程如下：

```text
before sensor observations
→ after sensor observations
→ sensor delta
→ device spatial basis
→ least-squares impact coefficient learning
```

## 3.7 控制動作排序

本研究不做閉環控制，而是對候選控制動作進行排序。系統針對每個候選動作模擬目標區域的三因子值，並依舒適度目標計算改善分數。若房間偏熱，冷氣動作通常獲得較高排序；若照度不足，照明動作通常獲得較高排序。


---


# 第四章 系統實作與 MCP 服務

## 4.1 Python 原型

本研究原型以 Python 實作，核心模組包含 entities、model、scenarios、learning、baselines、recommendations、service、mcp_server 與 web_demo。系統採零外部依賴設計，方便在本地環境快速執行與展示。

| 模組 | 功能 |
| --- | --- |
| entities.py | 定義房間、設備、感測器、區域與動作資料結構 |
| model.py | 建立三因子場、設備影響函數與感測器校正 |
| scenarios.py | 定義標準情境與窗戶矩陣情境 |
| learning.py | 由前後感測資料學習非連網裝置影響係數 |
| baselines.py | 建立 IDW baseline |
| service.py | 提供 MCP、Gemma bridge 與 web demo 共用服務介面 |
| web_demo.py | 提供本地可旋轉 3D web demo |

## 4.2 MCP Tools

本地 MCP server 提供下列 tools：

- list_scenarios：列出 8 組標準驗證情境。
- list_window_scenarios：列出 48 組窗戶時段/天氣/季節情境。
- run_scenario：執行情境並回傳重建誤差與目標區域估計。
- rank_actions：依目標區域舒適度改善排序候選動作。
- sample_point：估計指定座標的 temperature、humidity 與 illuminance。
- compare_baseline：比較本研究模型與 IDW baseline。
- learn_impacts：由前後感測資料學習非連網裝置影響。
- run_window_matrix：執行全部 48 組窗戶矩陣模擬。
- run_window_direct：直接輸入外部溫度、濕度、日照與開窗比例，執行窗戶影響模擬。

## 4.3 Gemma/Ollama Bridge

由於本機 Gemma 模型不一定是原生 MCP client，本研究提供 Python bridge 作為中介。Gemma 負責將自然語言問題轉成工具選擇，Python 執行數位孿生服務，最後再由 Gemma 根據工具輸出產生回答。此設計可展示非 MCP-native LLM 也能透過橋接方式使用同一套模型能力。

## 4.4 Web Demo

Web demo 以 idle 房間背景為基礎，透過 ac_main、window_main 與 light_main checkbox 組合設備狀態，不使用下拉式情境選單。3D 預覽可拖曳旋轉與縮放，並以牆面橫條標示冷氣、牆面矩形標示窗戶、點狀標記表示照明。Metric 亦以勾選式控制切換 temperature、humidity 與 illuminance。窗戶展示除列舉矩陣外，另提供 direct input 表單，讓使用者直接輸入外部溫度、濕度、日照與開窗比例。


---


# 第五章 模擬案例與結果分析

## 5.1 標準情境設定

本研究建立 8 組標準情境，包含無設備作用、僅冷氣、僅開窗、僅照明、冷氣與窗戶、窗戶與照明、冷氣與照明，以及三者同時作用。每組情境均輸出場重建誤差、區域平均值、感測器校正效果、IDW baseline 比較、非連網裝置影響學習與推薦排序。

| 情境 | 中央溫度 | 中央濕度 | 中央照度 | 最佳推薦 |
| --- | --- | --- | --- | --- |
| idle | 28.87 | 67.50 | 90.00 | ac_and_light |
| ac_only | 26.97 | 66.39 | 90.00 | turn_on_light |
| window_only | 29.14 | 67.85 | 208.41 | ac_and_light |
| light_only | 29.12 | 67.50 | 416.53 | turn_on_ac |
| all_active | 27.46 | 66.66 | 443.38 | turn_on_ac |

## 5.2 場重建誤差

8 組標準情境中，平均溫度 MAE 為 0.0626，平均濕度 MAE 為 0.1867，平均照度 MAE 為 3.5248。照度 MAE 較高，主要原因是照度場受燈具位置、窗戶日照與方向性影響較大，且數值尺度遠高於溫度與濕度。

## 5.3 IDW Baseline 比較

以 light_only 情境為例，本研究模型在照度 MAE 上相較 IDW baseline 降低約 94.90%。這表示只依靠角落感測器插值難以重建中央燈具造成的局部照度提升，而加入設備位置與影響函數後，可更有效描述設備作用。

## 5.4 非連網裝置影響學習

在 ac_only 情境中，模型學得冷氣對 temperature 的係數為負，對 humidity 的係數亦為負，對 illuminance 則接近零，符合冷氣降溫與弱除濕的模型假設。在 light_only 情境中，照明主要提升 illuminance，並帶來少量正向熱效應。這些結果顯示，即使裝置本身不回報狀態，仍可由環境感測變化估計其影響方向與相對強度。

## 5.5 窗戶時段、天氣、季節矩陣與直接輸入

本研究新增 48 組窗戶矩陣情境，組合 4 個時段、3 種天氣與 4 個季節。此矩陣可作為外部環境變數敏感度分析，用於說明窗戶在不同外部條件下對靠窗區與中心區的溫度、濕度與照度影響。

除列舉矩陣外，系統亦支援窗戶 direct input 模式。使用者可直接提供外部溫度、外部濕度、外部日照照度、開窗比例，以及可選的室內基準溫濕度。此模式適合接入即時天氣資料、手動量測資料或使用者指定條件，不必先將外部條件離散化為季節、天氣與時段分類。

| 情境 | 外部溫度 | 外部濕度 | 外部日照 | 窗戶區照度 |
| --- | --- | --- | --- | --- |
| window_summer_sunny_noon | 37.0 | 71.0 | 36000.0 | 223.9044 |
| window_winter_rainy_night | 11.0 | 78.0 | 15.2 | 68.8988 |
| window_spring_cloudy_morning | 21.5 | 70.0 | 5005.0 | 90.3925 |

## 5.6 可旋轉 3D 展示

Web demo 提供可旋轉 3D 預覽，使使用者可直接觀察三因子點雲、房間框線與設備幾何位置。冷氣以牆面橫條表示，窗戶以牆面矩形表示，照明以點狀標記表示。此展示有助於口試或公開展示時說明模型如何從設備位置與環境場估計區域影響。


---


# 第六章 結論與未來工作

## 6.1 結論

本研究建立一個 MCP-enabled 單房間三因子空間數位孿生原型，針對非連網家電或環境裝置對 temperature、humidity 與 illuminance 造成的影響進行建模、校正與學習。透過 8 顆角落感測器、設備影響函數與 affine 校正場，系統能估計房間內任意位置與指定區域的三因子狀態。模擬結果顯示，加入設備影響模型後，在冷氣、窗戶與照明等情境下能提供較 IDW baseline 更可解釋的場估計。

此外，本研究將模型封裝為 MCP server，並提供 Gemma/Ollama bridge 與 web demo，使數位孿生不只是離線模擬程式，而是可被 AI client 或使用者互動查詢的工具化系統。整體成果符合研究目標：在有限感測器與非連網裝置條件下，學習裝置對空間環境的影響，並用於更準確的控制動作推薦。

## 6.2 研究限制

- 目前結果主要來自文獻參數與合理物理假設模擬，尚未加入大量真實房間資料。
- 模型不處理多房間氣流、牆體熱容或完整流體動力學。
- 濕度模型採簡化耦合，驗證強度低於溫度與照度。
- MCP server 目前為本地 stdio 版本，尚未包含遠端部署、OAuth 或多使用者管理。
- 控制功能為推薦排序，尚未進入自動閉環控制。

## 6.3 未來工作

- 加入實體 ESP32 感測器資料，以校正與驗證模型參數。
- 擴充自訂房間 JSON 輸入，使系統可支援不同房間尺寸與設備位置。
- 加入更多環境變數，例如 CO2、PM2.5 或人體熱源。
- 將 MCP server 擴充為遠端 HTTP MCP，並加入權限控管。
- 進一步研究閉環控制，將推薦排序延伸為實際控制策略。
- 加入長時間資料以學習季節性與日夜週期變化。


---


# 參考文獻（待正式整理）

- ASHRAE Standard 55, Thermal Environmental Conditions for Human Occupancy.
- ISO 7730, Ergonomics of the thermal environment.
- Model Context Protocol documentation and tool interface specification.
- Indoor environmental quality, spatial interpolation, and smart building digital twin related literature.
- HVAC modeling, RC thermal models, PMV/PPD, and lighting simulation related literature.


---


# 附錄 A：原型執行方式

```text
python3 scripts/run_demo.py
python3 scripts/run_window_matrix.py
python3 scripts/run_web_demo.py
python3 scripts/run_mcp_server.py
```

# 附錄 B：Web Demo 操作

- 左側 checkbox 控制 ac_main、window_main 與 light_main。
- 3D 預覽可拖曳旋轉，滾輪縮放。
- Metric checkbox 可切換 temperature、humidity 與 illuminance。
- 窗戶矩陣表格展示 48 組時段、天氣與季節組合。
- Direct Window Input 表單可直接輸入外部溫度、濕度、日照與開窗比例。
- Point Sample 可查詢任意座標的三因子估計值。
