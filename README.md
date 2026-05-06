# A Sparse-Sensing Spatial Digital Twin for Learning Environmental Impacts of Non-Networked Appliances in a Single Room

中文暫定題目：單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型

建議 GitHub repository 名稱：

`single-room-sparse-sensing-digital-twin`

這個專案實作了一個可直接執行的 Python 研究原型，用來學習非連網家電或環境裝置對單一房間三個環境參數造成的影響：

- 溫度 `T(x, y, z, t)`
- 濕度 `H(x, y, z, t)`
- 亮度 `L(x, y, z, t)`

英文題目中的三個環境因素明確定義為：

- Temperature
- Humidity
- Illuminance

## Thesis Sync Rule

本 repo 的論文相關產物必須同步維護。任何 AI 助手若修改中文論文、英文 IEEE 稿、簡報、圖表或 benchmark 敘述，都必須把這幾個產物一起更新：

- 中文論文
- 英文 / IEEE 論文
- 簡報
- 對應輸出檔與圖表

詳細規則見 [AGENTS.md](/Volumes/DataExtended/school/AGENTS.md)。

模型採用「連續影響場 + 高解析度離散採樣網格」的混合方式，並固定使用 8 顆角落感測器進行觀測與校正。研究重點是：即使冷氣、窗戶、照明等裝置本身沒有連網、沒有 API、也無法直接回報狀態，系統仍可透過環境感測資料學習其影響，並用於更準確地控制溫度、濕度與照度。MCP server 與 web demo 則作為同一套模型能力的互動式存取介面。

## 內容

- `digital_twin/core/`
  共用資料結構、情境定義、主 service 與 demo orchestration。
- `digital_twin/physics/`
  數學公式主模型、baseline、裝置影響學習與決策排序。
- `digital_twin/neural/`
  類神經網路殘差修正模型。
- `digital_twin/mcp/`
  MCP server 與 Gemma/Ollama bridge。
- `digital_twin/web/`
  Web UI 與 SVG/CSV/JSON 輸出。
- `scripts/run_demo.py`
  執行完整模擬、校正、情境評估與 SVG/JSON/CSV 匯出。
- `scripts/run_window_matrix.py`
  執行窗戶在早上/中午/下午/晚上、陰天/晴天/雨天、春夏秋冬下的 48 組模擬。
- `tests/`
  基本單元測試與行為驗證。
- `digital_twin/neural/hybrid_residual.py`
  混合式殘差神經網路實驗模組，以現有 `bulk + local field` 模型為主體，再用小型 MLP 學習剩餘誤差。
- `docs/thesis/`
  中文論文草稿、論文章節規劃、研究計畫與題目定位。
- `docs/models/`
  數學模型、參考模型、文獻閱讀與 hybrid residual neural network 說明。
- `docs/models/system_architecture_and_training_roadmap_zh.md`
  整理整個系統分層，並說明哪些部分適合先用資料訓練。
- `docs/mcp/`
  MCP server 與 Gemma/Ollama bridge 說明。
- `docs/web/`
  Web demo 啟動與展示說明。
- `docs/papers/`
  英文投稿稿與相關輸出。
- `docs/experiments/`
  baseline、窗戶矩陣、模擬結果與重複性分析。
- `docs/admin/`
  畢業條件、行政 checklist 與學校原始參考文件。
- `docs/thesis/thesis_guide_zh.md`
  將此原型對應到碩士論文撰寫的章節與方法說明。
- `docs/thesis/problem_statement_zh.md`
  說明本研究要解決的非連網家電環境影響學習問題。
- `docs/thesis/system_architecture_diagrams_zh.md`
  整理目前實作的整體分層架構、執行資料流、校正與學習流程，以及檔案結構圖。
- `docs/admin/graduation_requirements_checklist_zh.md`
  整理資工系碩士畢業條件、學位考試流程與口試文件 checklist。
- `docs/admin/oral_defense_playbook_zh.md`
  以實務角度整理口試前置條件、文件準備、口試當天與口試後 follow-up。
- `docs/admin/oral_defense_timeline_checklist_zh.md`
  一頁式 `D-60 / D-30 / D-14 / D-1 / D-day / D+7` 倒排待辦表。
- `docs/experiments/baseline_and_learning_results_zh.md`
  整理 IDW baseline 比較與非連網裝置影響學習結果。
- `docs/experiments/window_matrix_simulation_zh.md`
  說明窗戶在時段、天氣、季節矩陣下的 48 組模擬設定與結果。
- `docs/models/hybrid_residual_model_zh.md`
  說明 hybrid residual neural network 的定位、公式與實驗方式。
- `docs/web/web_demo_zh.md`
  說明本地 web demo 的啟動方式與公開展示流程。
- `docs/papers/ieee/`
  IEEE conference-style 英文論文初稿，包含 `paper.tex`、`references.bib` 與 `paper.pdf`。
- `scripts/build_thesis_docx.py` / `scripts/build_thesis_pdf.py`
  產生中文碩士論文初稿的 `docx`、`tex` 與 `pdf` 輸出。
- `scripts/build_thesis_pptx.py`
  產生中文論文報告用的 `pptx` 投影片與簡報大綱，包含短版與 30 分鐘版。
- `scripts/build_training_templates.py`
  產生真實實驗資料蒐集用的 CSV / JSON 模板。
- `scripts/build_public_dataset_benchmark_templates.py`
  產生公開資料集 benchmark 對齊模板。
- `scripts/normalize_public_benchmark_data.py`
  將 CU-BEMS 或 SML2010 正規化成 repo 既有模板可用的中介格式。
- `scripts/run_public_dataset_benchmark.py`
  對正規化後的公開資料集執行 shared-task benchmark，輸出 persistence 與線性回歸 baseline 比較結果。
- `scripts/run_public_dataset_model_comparison.py`
  將本研究的 hybrid digital twin 映射到相同 public tasks，並與 persistence / linear regression 做一對一比較。

## 快速開始

執行完整示範：

```bash
python3 scripts/run_demo.py
```

執行 48 組窗戶時段/天氣/季節矩陣：

```bash
python3 scripts/run_window_matrix.py
```

執行 hybrid residual neural network 實驗：

```bash
python3 scripts/run_hybrid_residual_experiment.py
```

執行測試：

```bash
python3 -m unittest discover -s tests
```

產生中文論文初稿：

```bash
python3 scripts/build_thesis_docx.py
python3 scripts/build_thesis_pdf.py
```

產生中文論文報告投影片：

```bash
python3 scripts/build_thesis_pptx.py
```

輸出檔包含：

- `outputs/papers/thesis_presentation_zh.pptx`
  短版簡報
- `outputs/papers/thesis_presentation_zh_30min.pptx`
  約 25 到 30 分鐘口試版簡報

匯出系統架構圖 SVG：

```bash
python3 scripts/build_architecture_diagrams.py
```

產生資料訓練模板：

```bash
python3 scripts/build_training_templates.py
```

正規化公開資料集 benchmark：

```bash
python3 scripts/build_public_dataset_benchmark_templates.py
python3 scripts/normalize_public_benchmark_data.py --dataset cu-bems
python3 scripts/normalize_public_benchmark_data.py --dataset sml2010
python3 scripts/run_public_dataset_benchmark.py --dataset cu-bems --horizons 15,60
python3 scripts/run_public_dataset_benchmark.py --dataset sml2010 --horizons 15,60
python3 scripts/run_public_dataset_model_comparison.py --dataset sml2010 --horizons 15,60
python3 scripts/run_public_dataset_model_comparison.py --dataset cu-bems --horizons 15,60
```

## MCP Server

本專案也可以作為本地 stdio MCP server 使用：

```bash
python3 scripts/run_mcp_server.py
```

目前 MCP server 已收斂為五個互動流程 tools：

- `initialize_environment`：初始化情境、註冊設備/家具、外部環境與室內 baseline。
- `sample_point`：查詢指定座標在特定 elapsed minutes 或 steady state 下的三因子估計。
- `learn_impacts`：建立或完成非連網裝置 before/after 觀測紀錄，用於學習 device impact。
- `run_window_direct`：直接輸入外部溫度、濕度、日照與開窗比例，執行窗戶影響模擬。
- `rank_actions`：輸入指定座標與目標值，依目前註冊設備排序候選操作。

詳細設定請見 `docs/mcp/mcp_service_zh.md`。

## Hybrid Residual Neural Network

若你想把目前的參數化數位孿生模型再往資料驅動方向延伸，專案內建一個不取代主模型的 hybrid residual neural network 實驗模組。它的形式是：

```text
F_final(p, t) = F_physics(p, t) + f_theta(features(p, t))
```

其中：

- `F_physics` 是目前的 `bulk + local field` 主模型
- `f_theta` 是小型 MLP，用來學習主模型在特定座標、設備組合與環境條件下的殘差

這個設計比純黑盒神經網路更適合目前題目，因為它保留了裝置影響函數、時間響應與感測器校正的可解釋性，同時允許你在論文中把 neural network 定位成「第二層殘差修正器」而非主體模型。詳細說明請見 `docs/models/hybrid_residual_model_zh.md`。

目前也支援可選的 Fourier low-pass denoising。實作上會先為 residual target 建立短時間軌跡，再只對 `temperature` 與 `humidity` 做頻域低通濾波，以降低短時擾動對 MLP 訓練的影響；`illuminance` 預設不做此處理，避免把有用的快速變化一起抹平。

## Gemma4 / Ollama Bridge

若本機 Ollama 已安裝 `gemma4:26b`，可讓 Gemma 透過本專案的 Python bridge 使用同一套數位孿生工具：

```bash
python3 scripts/ask_gemma.py "idle 情境下建議做什麼動作？"
```

只查看工具選擇與原始工具輸出：

```bash
python3 scripts/ask_gemma.py "idle 情境下建議做什麼動作？" --tool-only
```

詳細說明請見 `docs/mcp/gemma_ollama_bridge_zh.md`。

## Web Demo

本專案提供本地 web demo，可用於公開展示與口試說明：

```bash
python3 scripts/run_demo.py
python3 scripts/run_web_demo.py
```

開啟 `http://127.0.0.1:8765`。詳細說明請見 `docs/web/web_demo_zh.md`。

Web demo 內含可拖曳旋轉與縮放的 3D 三因子熱區預覽，並標示冷氣、窗戶與照明位置。冷氣以牆面橫條顯示、窗戶以牆面矩形顯示，不再只是單一點；左側提供每個裝置的 checkbox，可直接覆寫裝置啟用狀態並重新計算結果。頁面主操作已移除下拉式選單，設備與 metric 都改為勾選式控制。窗戶模擬除了 48 組列舉矩陣，也提供 direct input，可直接輸入外部溫度、外部濕度、日照照度與開窗比例。

## 輸出結果

執行後會在 `outputs/` 產生三類輸出：

- `outputs/data/`
  `validation_summary.json`、`window_matrix_summary.json`、`hybrid_residual_summary.json`、`hybrid_residual_checkpoint.json` 與各情境 `*.csv`。
- `outputs/data_templates/`
  真實感測器時序、裝置事件、室外環境與空間量測的資料模板。
- `outputs/data/normalized_public/`
  CU-BEMS 與 SML2010 等公開資料集轉換後的 benchmark 中介格式。
- `outputs/data/public_benchmarks/`
  公開資料集 shared-task benchmark 與本研究模型一對一 comparison 的 JSON 結果摘要。
- `outputs/figures/`
  每個情境的 2D 中高度切片熱圖與 `*_3d.svg` 等角投影 3D 熱區圖並標示家電位置；冷氣以橫條表示，窗戶以矩形面表示。
- `outputs/papers/`
  `thesis_draft_zh.docx`、`thesis_draft_zh.tex`、`thesis_draft_zh.pdf` 等中文論文輸出。

## 模型摘要

模型將房間狀態視為三個連續場，並對每類設備建立簡化影響函數：

- 冷氣：局部降溫、弱除濕、具方向性與時間響應
- 窗戶：引入日照並使溫濕度向外部環境漂移
- 照明：增加照度並帶來少量熱效應

感測器校正使用 8 顆角落節點對模型殘差擬合 trilinear 修正場，並在校正前先由感測器殘差估計 active device 的 power scale：

```text
C(x, y, z) = c0 + c1*X + c2*Y + c3*Z + c4*X*Y + c5*X*Z + c6*Y*Z + c7*X*Y*Z
```

其中 `X/Y/Z` 為正規化後的房間座標。這讓 8 顆角落感測器可支撐 8 參數校正，並比一階 affine 修正更能捕捉角落間的交互變化。目前標準場網格解析度為 `16 × 12 × 6`。
