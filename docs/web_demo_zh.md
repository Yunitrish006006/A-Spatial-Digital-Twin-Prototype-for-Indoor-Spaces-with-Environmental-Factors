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

- 選擇 8 組標準情境。
- 顯示目標區域的 temperature、humidity、illuminance 估計值。
- 顯示候選控制動作排序。
- 顯示本研究模型與 IDW baseline 的 MAE 比較。
- 顯示非連網裝置影響學習結果。
- 顯示窗戶在早上/中午/下午/晚上、陰天/晴天/雨天、春夏秋冬下的 48 組模擬表格。
- 顯示可拖曳旋轉與縮放的 3D 三因子熱區預覽，並標示冷氣、窗戶與照明位置。
- 顯示三個環境因素的靜態等角投影 3D SVG 圖，方便放入論文或簡報。
- 查詢任意座標點的三因子估計值。

## 對畢業展示的用途

若以「相關創新系統實作」作為畢業條件，此 web demo 可作為公開展示主體。

建議展示流程：

1. 說明問題：非連網家電無法直接回報狀態，但會影響室內環境。
2. 選擇 `idle` 情境，展示系統如何推薦冷氣與照明。
3. 選擇 `ac_only` 情境，展示冷氣影響學習結果。
4. 選擇 `light_only` 情境，展示模型與 IDW baseline 的照度 MAE 差異。
5. 拖曳旋轉 3D 預覽，說明三個環境因素的空間分布與設備位置。
6. 展示窗戶矩陣，說明外部時段、天氣與季節如何影響靠窗區與中心區。
7. 使用座標查詢，展示任意位置估計。
8. 說明同一套能力也可透過 MCP tools 與 Gemma/Ollama bridge 存取。

## API 路由

- `/api/scenarios`
- `/api/scenario?name=idle`
- `/api/volume?name=idle`
- `/api/window_matrix`
- `/api/rank_actions?name=idle`
- `/api/compare_baseline?name=light_only`
- `/api/learn_impacts?name=ac_only`
- `/api/sample?name=light_only&x=3&y=2&z=1.5`
- `/outputs/<scenario>_<metric>_3d.svg`

## 目前限制

- Web demo 是本地展示用，不含登入與權限管理。
- 模型情境仍是內建標準案例與窗戶矩陣案例。
- 可旋轉 3D 預覽使用 `/api/volume` 即時計算資料；靜態 3D SVG 使用 `scripts/run_demo.py` 產生的 `*_3d.svg` 檔案。
- 圖中方形標記代表家電座標與啟用比例。
- 尚未提供即時 ESP32 資料串流。
