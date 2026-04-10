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
- 顯示三個環境因素的中高度熱圖。
- 查詢任意座標點的三因子估計值。

## 對畢業展示的用途

若以「相關創新系統實作」作為畢業條件，此 web demo 可作為公開展示主體。

建議展示流程：

1. 說明問題：非連網家電無法直接回報狀態，但會影響室內環境。
2. 選擇 `idle` 情境，展示系統如何推薦冷氣與照明。
3. 選擇 `ac_only` 情境，展示冷氣影響學習結果。
4. 選擇 `light_only` 情境，展示模型與 IDW baseline 的照度 MAE 差異。
5. 切換熱圖，說明三個環境因素的空間分布。
6. 使用座標查詢，展示任意位置估計。
7. 說明同一套能力也可透過 MCP tools 與 Gemma/Ollama bridge 存取。

## API 路由

- `/api/scenarios`
- `/api/scenario?name=idle`
- `/api/rank_actions?name=idle`
- `/api/compare_baseline?name=light_only`
- `/api/learn_impacts?name=ac_only`
- `/api/sample?name=light_only&x=3&y=2&z=1.5`
- `/outputs/<scenario>_<metric>.svg`

## 目前限制

- Web demo 是本地展示用，不含登入與權限管理。
- 模型情境仍是內建標準案例。
- 熱圖使用 `scripts/run_demo.py` 產生的 SVG 檔案。
- 尚未提供即時 ESP32 資料串流。
