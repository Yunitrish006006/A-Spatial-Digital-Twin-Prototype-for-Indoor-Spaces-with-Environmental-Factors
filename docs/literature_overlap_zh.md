# 論文題目與研究重複性初步查核

查核日期：2026-04-10

## 查核題目

**A Lightweight Spatial Digital Twin Prototype for Single-Room Temperature, Humidity, and Illuminance Estimation Using Corner Sensor Calibration**

## 初步結論

目前未查到與原始題目或修正後題目完全相同的論文題名。不過，研究方向與下列領域高度相關：

- 建築或室內環境 digital twin
- BIM + IoT 感測資料整合
- 室內舒適度監測
- thermal comfort 與 lighting control
- temperature / humidity control system
- digital twin classroom 或 smart campus

因此，本研究並非完全沒有人做過相近方向。較安全的論文定位應該避免宣稱「首創室內環境 digital twin」，而是主張以下差異化貢獻：

1. 針對單房間建立輕量化 spatial digital twin prototype。
2. 明確同時估計 temperature、humidity、illuminance 三個空間場。
3. 固定使用 8 顆角落感測器進行場校正。
4. 以設備影響函數推估冷氣、窗戶與照明對區域參數的影響。
5. 以可解釋的舒適度改善分數輸出候選設備動作排序。

## 查核方式

本次採用以下方式進行初步查核：

1. 以完整英文題目加引號進行網路搜尋。
2. 使用關鍵字組合搜尋：
   - `spatial digital twin temperature humidity illuminance single room`
   - `indoor digital twin temperature humidity illuminance`
   - `single room digital twin temperature humidity`
   - `digital twin classroom lighting thermal comfort humidity`
3. 使用 Crossref API 查詢相近題名。
4. 檢視相近文獻的研究目標、變數、場域與方法。

Crossref 查詢中未出現完全同名題目。最接近的題名包含 temperature/humidity controller、temperature/humidity digital twin、spatial digital twin 等，但未同時覆蓋本研究的「single room + spatial field + temperature/humidity/illuminance + fixed corner sensors + equipment action ranking」組合。

## 高相關文獻

| 文獻 | 相似處 | 與本研究差異 | 重複風險 |
| --- | --- | --- | --- |
| Yan, 2024, *A Temperature and Humidity Control System based on Digital Twin* | 使用 digital twin 處理溫度與濕度控制 | 未聚焦照度、角落感測器空間場重建、設備影響排序 | 中 |
| Villa et al., 2021, *IoT Open-Source Architecture for the Maintenance of Building Facilities* | BIM/IoT 整合，監測 room temperature、humidity、luminosity | 目標是設施維護與 BIM dashboard，不是單房間空間場估計模型 | 中 |
| Lin and Wu, 2025, *Indoor Comfort Assessment Based on Digital Twin Platform* | 同時處理 thermal comfort、air quality、lighting，且屬 indoor comfort digital twin | 偏 BIM/Unity 平台與即時控制，非 8 角落感測器的連續場估計 | 中高 |
| *Adaptive Lighting and Thermal Comfort Control Strategies in Digital Twin Classroom via Deep Reinforcement Learning*, 2026 | digital twin classroom、lighting 與 thermal comfort control | 偏高密度 IoT、DALI、HVAC、deep reinforcement learning，不是輕量化角落感測器模型 | 高 |
| *A Smart Campus' Digital Twin for Sustainable Comfort Monitoring*, 2020 | smart campus、BIM、IoT、thermal/visual/air quality comfort | 場域較大，偏校園與 BIM workflow，不是單房間三因子影響場 | 中 |
| Almadhor et al., 2025, *Digital twin based deep learning framework for personalized thermal comfort prediction and energy efficient operation in smart buildings* | digital twin、thermal comfort、HVAC control | 偏個人化熱舒適與深度學習，不處理照度空間場與固定角落感測器 | 中 |

## 建議修正後的論文定位

為降低撞題風險，建議將題目與摘要中的重點放在「有限角落感測器」與「空間影響場估計」，而不只寫 digital twin 或 environmental factors。

採用英文題目：

**A Lightweight Spatial Digital Twin Prototype for Single-Room Temperature, Humidity, and Illuminance Estimation Using Corner Sensor Calibration**

此題目比原本更清楚地表達：

- lightweight prototype
- single-room
- temperature, humidity, illuminance
- estimation
- corner sensor calibration

若要保留設備影響與決策推薦，也可以使用更完整版本：

**A Lightweight Spatial Digital Twin Prototype for Single-Room Environmental Field Estimation and Appliance Impact Ranking**

## 建議摘要差異化寫法

建議在摘要中加入以下句型：

```text
Unlike BIM-centered or reinforcement-learning-based building digital twin systems,
this study focuses on a lightweight single-room spatial field estimation method
using only eight corner-mounted sensor nodes.
```

中文意思是：

本研究不同於以 BIM 平台或強化學習控制為主的建築數位孿生系統，而是聚焦於只使用 8 個角落感測節點的輕量化單房間空間場估計方法。

## 避免重複的研究邊界

論文中應避免過度宣稱：

- 不要說「第一個 indoor digital twin」。
- 不要說「第一個 temperature/humidity/illuminance digital twin」。
- 不要把貢獻寫成「完整智慧建築控制系統」。
- 不要主張已達到 high-fidelity physical simulation。

論文中可以合理主張：

- 提出一個輕量化單房間 spatial digital twin prototype。
- 使用固定 8 角落感測器進行三因子空間場校正。
- 建立冷氣、窗戶與照明的簡化影響函數。
- 輸出可解釋的候選設備動作排序。

## 參考來源

- EUDL: *A Temperature and Humidity Control System based on Digital Twin*, DOI: 10.4108/eai.15-9-2023.2340892  
  https://eudl.eu/doi/10.4108/eai.15-9-2023.2340892
- MDPI Applied Sciences: *IoT Open-Source Architecture for the Maintenance of Building Facilities*, DOI: 10.3390/app11125374  
  https://www.mdpi.com/2076-3417/11/12/5374
- IAARC ISARC 2025: *Indoor Comfort Assessment Based on Digital Twin Platform*, DOI: 10.22260/ISARC2025/0170  
  https://www.iaarc.org/publications/2025_proceedings_of_the_42nd_isarc_montreal_canada/indoor_comfort_assessment_based_on_digital_twin_platform.html
- MDPI Electronics: *Adaptive Lighting and Thermal Comfort Control Strategies in Digital Twin Classroom via Deep Reinforcement Learning*  
  https://www.mdpi.com/2079-9292/15/4/873
- MDPI Sustainability: *A Smart Campus' Digital Twin for Sustainable Comfort Monitoring*  
  https://www.mdpi.com/2071-1050/12/21/9196
- Nature Scientific Reports: *Digital twin based deep learning framework for personalized thermal comfort prediction and energy efficient operation in smart buildings*  
  https://www.nature.com/articles/s41598-025-10086-y
- Nature Scientific Reports: *A sensor-fused BIM-based intelligent control system for energy-efficient indoor environmental regulation using deep actor-critic reinforcement learning*  
  https://www.nature.com/articles/s41598-025-30460-0

## 查核限制

本查核只能代表公開網路、Crossref 與可搜尋學術頁面的初步結果，不能取代正式的 Turnitin、iThenticate、學校論文系統或付費資料庫查重。若要正式確認，後續仍應以學校指定的論文比對系統為準。
