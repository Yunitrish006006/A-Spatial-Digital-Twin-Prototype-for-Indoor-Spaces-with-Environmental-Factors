# An MCP-Enabled Lightweight Spatial Digital Twin Prototype for Learning the Environmental Impact of Non-Networked Appliances in a Single Room

中文暫定題目：基於 MCP 之單房間非連網家電環境影響學習與三因子控制數位孿生原型

建議 GitHub repository 名稱：

`mcp-single-room-spatial-digital-twin`

這個專案實作了一個可直接執行的 Python 研究原型，用來學習非連網家電或環境裝置對單一房間三個環境參數造成的影響：

- 溫度 `T(x, y, z, t)`
- 濕度 `H(x, y, z, t)`
- 亮度 `L(x, y, z, t)`

英文題目中的三個環境因素明確定義為：

- Temperature
- Humidity
- Illuminance

模型採用「連續影響場 + 離散採樣網格」的混合方式，並固定使用 8 顆角落感測器進行觀測與校正。研究重點是：即使冷氣、窗戶、照明等裝置本身沒有連網、沒有 API、也無法直接回報狀態，系統仍可透過環境感測資料學習其影響，並用於更準確地控制溫度、濕度與照度。系統同時提供 MCP server，讓支援 MCP 的 AI client 可以呼叫模型工具。

## 內容

- `digital_twin/`
  核心模型、情境定義、決策排序與輸出工具。
- `scripts/run_demo.py`
  執行完整模擬、校正、情境評估與 SVG/JSON/CSV 匯出。
- `scripts/run_window_matrix.py`
  執行窗戶在早上/中午/下午/晚上、陰天/晴天/雨天、春夏秋冬下的 48 組模擬。
- `tests/`
  基本單元測試與行為驗證。
- `docs/thesis_guide_zh.md`
  將此原型對應到碩士論文撰寫的章節與方法說明。
- `docs/problem_statement_zh.md`
  說明本研究要解決的非連網家電環境影響學習問題。
- `docs/graduation_requirements_checklist_zh.md`
  整理資工系碩士畢業條件、學位考試流程與口試文件 checklist。
- `docs/baseline_and_learning_results_zh.md`
  整理 IDW baseline 比較與非連網裝置影響學習結果。
- `docs/window_matrix_simulation_zh.md`
  說明窗戶在時段、天氣、季節矩陣下的 48 組模擬設定與結果。
- `docs/web_demo_zh.md`
  說明本地 web demo 的啟動方式與公開展示流程。
- `ieee_paper/`
  IEEE conference-style 英文論文初稿，包含 `paper.tex` 與 `references.bib`。

## 快速開始

執行完整示範：

```bash
python3 scripts/run_demo.py
```

執行 48 組窗戶時段/天氣/季節矩陣：

```bash
python3 scripts/run_window_matrix.py
```

執行測試：

```bash
python3 -m unittest discover -s tests
```

## MCP Server

本專案也可以作為本地 stdio MCP server 使用：

```bash
python3 scripts/run_mcp_server.py
```

目前提供八個 MCP tools：

- `list_scenarios`
- `list_window_scenarios`
- `run_scenario`
- `rank_actions`
- `sample_point`
- `compare_baseline`
- `learn_impacts`
- `run_window_matrix`

詳細設定請見 `docs/mcp_service_zh.md`。

## Gemma4 / Ollama Bridge

若本機 Ollama 已安裝 `gemma4:26b`，可讓 Gemma 透過本專案的 Python bridge 使用同一套數位孿生工具：

```bash
python3 scripts/ask_gemma.py "idle 情境下建議做什麼動作？"
```

只查看工具選擇與原始工具輸出：

```bash
python3 scripts/ask_gemma.py "idle 情境下建議做什麼動作？" --tool-only
```

詳細說明請見 `docs/gemma_ollama_bridge_zh.md`。

## Web Demo

本專案提供本地 web demo，可用於公開展示與口試說明：

```bash
python3 scripts/run_demo.py
python3 scripts/run_web_demo.py
```

開啟 `http://127.0.0.1:8765`。詳細說明請見 `docs/web_demo_zh.md`。

Web demo 內含可拖曳旋轉與縮放的 3D 三因子熱區預覽，並標示冷氣、窗戶與照明位置。冷氣以牆面橫條顯示、窗戶以牆面矩形顯示，不再只是單一點；左側提供每個裝置的 checkbox，可直接覆寫裝置啟用狀態並重新計算結果。頁面主操作已移除下拉式選單，設備與 metric 都改為勾選式控制。

## 輸出結果

執行後會在 `outputs/` 產生：

- `validation_summary.json`
  各情境的場重建誤差、區域平均值、感測器校正結果與動作排序。
- `window_matrix_summary.json`
  窗戶在 4 個時段、3 種天氣、4 個季節下的 48 組三因子模擬結果。
- `*.svg`
  每個情境的 2D 中高度切片熱圖，另有 `*_3d.svg` 等角投影 3D 熱區圖並標示家電位置；冷氣以橫條表示，窗戶以矩形面表示。
- `*.csv`
  每個情境的 3D 採樣網格資料，可直接拿去做論文圖表。

## 模型摘要

模型將房間狀態視為三個連續場，並對每類設備建立簡化影響函數：

- 冷氣：局部降溫、弱除濕、具方向性與時間響應
- 窗戶：引入日照並使溫濕度向外部環境漂移
- 照明：增加照度並帶來少量熱效應

感測器校正使用 8 顆角落節點對模型殘差擬合 affine 修正面：

```text
delta(x, y, z) = a0 + a1*x + a2*y + a3*z
```

這讓有限量測可以反映整體場的偏移與梯度變化。
