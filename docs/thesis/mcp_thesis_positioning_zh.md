# MCP 在論文中的輔助定位建議

## 建議題目

英文：

**A Sparse-Sensing Spatial Digital Twin for Learning Environmental Impacts of Non-Networked Appliances in a Single Room**

中文：

**單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型**

## 為什麼可以加入 MCP

本研究的核心是：在裝置本身沒有連網能力、沒有 API、也不能直接回報狀態時，透過室內環境感測資料學習該裝置對 temperature、humidity、illuminance 的影響。加入 MCP 後，研究不只是建立一個 Python 模擬程式，而是進一步把模型封裝成 AI agent 可呼叫的標準工具介面。

這讓論文多一個明確應用價值：

- 模型可被 LLM 或 AI agent 直接查詢。
- 環境模擬、座標估計與設備推薦可被工具化。
- 數位孿生不只是視覺化或離線模擬，而是可被互動式智慧系統使用。

## 研究主軸不要偏移

建議不要把 MCP 寫成整篇論文的唯一核心，因為 MCP 本身是通訊與工具協定，不是你的環境建模貢獻。

較穩定的定位是：

```text
Core contribution: learning appliance impact from environmental changes
Model contribution: single-room environmental field estimation
System contribution: interactive service interface, including MCP access
```

也就是：

- 主要研究：非連網裝置對溫度、濕度、照度造成的影響學習。
- 模型研究：溫度、濕度、照度空間場估計。
- 系統實作：MCP server 封裝模型能力。
- 應用展示：AI client 或 Gemma bridge 可使用工具查詢結果。

## 建議章節安排

### 第一章 緒論

新增一個問題意識：

傳統室內數位孿生模型多半假設裝置狀態可以由智慧家電、BMS 或 IoT API 取得。然而，在一般房間中仍有許多非連網裝置會影響環境，卻無法直接回報狀態。因此，本研究從有限環境感測資料學習裝置影響，並將模型封裝為 MCP tools，以提升數位孿生原型的可存取性與可整合性。

### 第二章 文獻探討

可加入一節：

**AI Agent Tool Interface and Model Context Protocol**

內容重點：

- LLM 與外部工具整合的需求。
- MCP 作為標準化 context/tool protocol 的角色。
- 本研究與既有 BIM dashboard、IoT platform 的差異。

### 第三章 系統架構與模型

建議把 MCP 放在系統架構後半段：

```text
Corner sensor observations
    ↓
Environmental change detection
    ↓
Appliance impact learning
    ↓
Sensor correction
    ↓
Environmental field estimation
    ↓
Decision ranking
    ↓
MCP tool interface
```

MCP tools 對應：

- `initialize_environment`
- `sample_point`
- `learn_impacts`
- `run_window_direct`
- `rank_actions`

### 第四章 MCP 服務與 AI Agent 存取流程

如果篇幅足夠，可以獨立成一章。若學校偏好模型導向，可併入第三章。

可寫內容：

- stdio MCP server 架構。
- JSON-RPC request / response 流程。
- tool schema 設計。
- tool result 如何被 AI client 使用。
- Gemma/Ollama bridge 作為非 MCP-native LLM 的整合案例。

### 第五章 模擬與系統驗證

除了原本的模型誤差，也加入 MCP 功能驗證：

- MCP server 是否能初始化環境、設備、家具與 baseline。
- MCP server 是否能在指定 elapsed time 或 steady state 查詢任意座標。
- MCP server 是否能建立 before/after impact learning record，並在資料足夠時輸出 learned coefficients。
- MCP server 是否能用 direct window data 執行窗戶模擬。
- MCP server 是否能針對指定座標與目標值回傳推薦排序。
- Gemma bridge 是否能根據自然語言選擇工具。

## 可宣稱的貢獻

建議寫成三點：

1. 提出一個針對非連網家電環境影響學習的單房間 spatial digital twin prototype。
2. 提出一個使用 8 顆角落感測器殘差進行 temperature、humidity、illuminance 空間場校正的流程。
3. 根據學習後的裝置影響，輸出三個環境變數的候選控制動作排序。
4. 將模型封裝為 MCP tools，使 AI client 能以標準化方式初始化環境、查詢座標估計、記錄裝置影響學習資料、輸入窗戶外部條件與取得指定點設備推薦。

## 不建議宣稱

避免寫：

- 本研究提出新的 MCP protocol。
- 本研究完成完整 agentic building management system。
- 本研究實現通用智慧建築 AI agent。
- 本研究取代 BIM 或 BMS 系統。

可以寫：

- 本研究實作帶有 MCP 介面的 prototype。
- 本研究展示數位孿生模型如何被 AI agent 以工具方式存取。
- 本研究提供後續遠端 MCP deployment 與實體感測整合基礎。

## 建議摘要句子

英文：

```text
The proposed prototype learns the environmental impact of non-networked appliances from limited corner sensor observations and estimates single-room temperature, humidity, and illuminance fields. A local service layer, including an MCP interface, exposes scenario execution, point-level estimation, and candidate action ranking without changing the core reduced-order estimator.
```

中文：

```text
本研究透過有限角落感測器觀測資料，學習非連網家電對單房間溫度、濕度與照度造成的環境影響，並估計其空間分布。除環境場估計模型外，本研究亦提供本地服務介面，其中包含 MCP 存取方式，使外部 AI client 能查詢情境、估計指定座標之環境狀態，並取得候選控制動作排序。
```
