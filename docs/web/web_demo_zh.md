# 本地 Web Demo 使用說明

本專案已加入一個零外部依賴的本地 web demo，方便公開展示、口試展示與系統解說。

## 啟動方式

先產生最新模擬輸出：

```bash
python3 scripts/run_demo.py
```

啟動 web demo：

```bash
python3 scripts/run_web_demo.py
```

開啟瀏覽器：

```text
http://127.0.0.1:8765
```

## Demo 可展示內容

- 以 `idle` 房間背景為基礎，透過 checkbox 組合冷氣、窗戶與照明狀態，不使用下拉式情境選單。
- 顯示目標區域的 temperature、humidity、illuminance 估計值。
- 顯示候選控制動作排序。
- 顯示本研究模型與 IDW baseline 的 MAE 比較。
- 顯示非連網裝置影響學習結果。
- 顯示 Public Dataset Comparison，把 SML2010 與 CU-BEMS 的 task-aligned benchmark 流程、限制與 head-to-head MAE 比較整理成可展示表格。
- 顯示窗戶在早上/中午/下午/晚上、陰天/晴天/雨天、春夏秋冬下的 48 組模擬表格。
- 提供 Direct Window Input，可直接輸入外部溫度、外部濕度、日照照度與開窗比例，不必使用列舉情境。
- 顯示可拖曳旋轉與縮放的 3D 三因子熱區預覽，並標示冷氣、窗戶與照明位置。
- 顯示三個環境因素的靜態等角投影 3D SVG 圖，方便放入論文或簡報。
- 左側提供 `Term Glossary` 名詞解釋，並在頁面中的技術詞彙加入 hover/tap tooltip，方便展示時直接解釋 IDW、MAE、LOO、Hybrid Residual、MCP 等術語。
- 左側提供 `ac_main`、`window_main`、`light_main` checkbox，可直接開關裝置並重新計算結果。
- 3D metric 也改為勾選式切換，不使用下拉式選單。
- 冷氣在 3D 預覽與靜態 SVG 中以牆面橫條表示，不再是單一點。
- 窗戶在 3D 預覽與靜態 SVG 中以牆面矩形表示，不再是單一點。
- 查詢任意座標點的三因子估計值。

## 對畢業展示的用途

若以「相關創新系統實作」作為畢業條件，此 web demo 可作為公開展示主體。

建議展示流程：

1. 說明問題：非連網家電無法直接回報狀態，但會影響室內環境。
2. 先保持所有 checkbox 關閉，展示無設備作用下的背景場。
3. 勾選 `ac_main`，展示冷氣影響學習結果與推薦排序變化。
4. 勾選 `light_main`，展示照明對照度場與 IDW baseline 比較的影響。
5. 使用 checkbox 組合冷氣、窗戶與照明，展示非連網裝置狀態改變後的環境影響。
6. 拖曳旋轉 3D 預覽，說明三個環境因素的空間分布與設備位置。
7. 展示窗戶矩陣，說明外部時段、天氣與季節如何影響靠窗區與中心區。
8. 切換到 Direct Window Input，輸入指定外部條件，展示不經列舉分類的窗戶影響估計。
9. 使用座標查詢，展示任意位置估計。
10. 展開 `Public Dataset Comparison`，說明 SML2010 與 CU-BEMS 不是完整 3D 場真值，而是共同可觀測任務比較。
11. 展開 `Term Glossary` 或 hover 頁面底線術語，快速補充名詞定義。
12. 說明同一套能力也可透過 MCP tools 與 Gemma/Ollama bridge 存取。

## 公開資料集比較展示

`Public Dataset Comparison` 區塊讀取下列既有輸出，不重新計算論文數字：

```text
outputs/data/public_benchmarks/sml2010_hybrid_twin_comparison.json
outputs/data/public_benchmarks/cu_bems_hybrid_twin_comparison.json
```

展示邏輯如下：

1. Raw public data 先用 `scripts/normalize_public_benchmark_data.py` 轉成 repo 的 normalized public templates。
2. `scripts/run_public_dataset_benchmark.py` 先在相同 task、horizon、target 上計算 `persistence` 與 `linear regression` baseline。
3. `scripts/run_public_dataset_model_comparison.py` 再把本研究模型映射成 public task 的 structured prior，並在相同 chronological `70/30` split 上 fit linear readout head。
4. Demo 表格逐列比較本研究映射模型、linear regression、persistence 的 MAE，並標出哪一個方法最佳。

展示時應強調：SML2010 與 CU-BEMS 缺少本研究需要的完整單房間 3D dense ground truth，因此不能拿來宣稱 full 3D field MAE；它們的角色是 public task-aligned external benchmark。

## 名詞解釋機制

Web demo 內建一份展示用 glossary。載入頁面後，系統會自動掃描可見文字，把已收錄的專有名詞加上底線提示；使用者可用滑鼠 hover 或鍵盤 focus 查看簡短說明。左側 `Term Glossary` 同步列出完整詞彙表，適合口試或展示時快速查找。

目前涵蓋的詞彙包含：

- 研究定位：`Sparse-Sensing`、`Spatial Digital Twin`、`non-networked appliance`、`appliance impact`。
- 模型方法：`bulk + local field`、`trilinear correction`、`power calibration`、`least squares`、`Hybrid Residual Correction`、`one-bounce diffuse reflection`。
- 評估指標：`IDW`、`baseline`、`MAE`、`RMSE`、`Correlation`、`LOO`、`ablation`。
- 驗證設計：`synthetic full-field`、`window matrix`、`task-aligned benchmark`、`SML2010`、`CU-BEMS`、`chronological split`、`structured prior`、`linear readout head`。
- 系統介面：`CLI`、`API`、`Web demo`、`MCP`、`Direct Window Input`。

## API 路由

- `/api/scenarios`
- `/api/scenario?name=idle`
- `/api/volume?name=idle`
- `/api/window_matrix`
- `/api/public_benchmarks`
- `/api/window_direct?outdoor_temperature=35&outdoor_humidity=82&sunlight_illuminance=18000&opening_ratio=0.45`
- `/api/rank_actions?name=idle`
- `/api/compare_baseline?name=light_only`
- `/api/learn_impacts?name=ac_only`
- `/api/sample?name=light_only&x=3&y=2&z=1.5`
- `/outputs/figures/<scenario>_<metric>_3d.svg`

## 目前限制

- Web demo 是本地展示用，不含登入與權限管理。
- Web demo 主操作以 `idle` 背景加 checkbox 覆寫設備狀態；內建標準案例與窗戶矩陣案例仍保留在 service/API 內。
- 可旋轉 3D 預覽使用 `/api/volume` 即時計算資料；靜態 3D SVG 使用 `scripts/run_demo.py` 產生於 `outputs/figures/` 的 `*_3d.svg` 檔案。
- 圖中方形標記代表點狀設備座標與啟用比例；冷氣以牆面橫條表示，窗戶以牆面矩形面表示。
- 尚未提供即時 ESP32 資料串流。
