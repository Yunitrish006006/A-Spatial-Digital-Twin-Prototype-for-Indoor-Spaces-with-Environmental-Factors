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
- 顯示窗戶在早上/中午/下午/晚上、陰天/晴天/雨天、春夏秋冬下的 48 組模擬表格。
- 提供 Direct Window Input，可直接輸入外部溫度、外部濕度、日照照度與開窗比例，不必使用列舉情境。
- 顯示可拖曳旋轉與縮放的 3D 三因子熱區預覽，並標示冷氣、窗戶與照明位置。
- 顯示三個環境因素的靜態等角投影 3D SVG 圖，方便放入論文或簡報。
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
10. 說明同一套能力也可透過 MCP tools 與 Gemma/Ollama bridge 存取。

## API 路由

- `/api/scenarios`
- `/api/scenario?name=idle`
- `/api/volume?name=idle`
- `/api/window_matrix`
- `/api/window_direct?outdoor_temperature=35&outdoor_humidity=82&sunlight_illuminance=18000&opening_ratio=0.45`
- `/api/rank_actions?name=idle`
- `/api/compare_baseline?name=light_only`
- `/api/learn_impacts?name=ac_only`
- `/api/sample?name=light_only&x=3&y=2&z=1.5`
- `/outputs/<scenario>_<metric>_3d.svg`

## 目前限制

- Web demo 是本地展示用，不含登入與權限管理。
- Web demo 主操作以 `idle` 背景加 checkbox 覆寫設備狀態；內建標準案例與窗戶矩陣案例仍保留在 service/API 內。
- 可旋轉 3D 預覽使用 `/api/volume` 即時計算資料；靜態 3D SVG 使用 `scripts/run_demo.py` 產生的 `*_3d.svg` 檔案。
- 圖中方形標記代表點狀設備座標與啟用比例；冷氣以牆面橫條表示，窗戶以牆面矩形面表示。
- 尚未提供即時 ESP32 資料串流。
