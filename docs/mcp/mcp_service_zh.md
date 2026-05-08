# MCP-Enabled 數位孿生服務設計與使用方式

本專案提供一個本地 stdio MCP server，讓支援 MCP 的 client 可以用標準工具介面呼叫單房間環境數位孿生。MCP 在本研究中不是預測模型，也不是新的通訊協定貢獻；它是把同一套 service layer 包成 AI client 可呼叫的工具入口。

## 目前 MCP 的定位

目前 MCP 介面已從早期的「驗證用工具集合」收斂為實際互動流程：

1. 先初始化 MCP session 的 runtime state，包含 base scenario、室內 baseline、外部邊界條件、設備、家具/遮蔽物、預設時間與 estimator 選擇。
2. 在已註冊環境中查詢任意座標的 temperature、humidity、illuminance。
3. 對非連網裝置建立 before/after 觀測紀錄，並在資料足夠時學習影響係數。
4. 對窗戶直接輸入外部溫度、濕度、日照與開窗比例。
5. 對指定座標 sample 與完整 temperature、humidity、illuminance 目標，根據目前註冊設備排序候選操作；缺少 sample 或任一目標因子時不產生推薦。

`run_demo.py`、`run_window_matrix.py`、`compare_baseline` 等仍存在於 service 或實驗腳本中，但它們不再作為 MCP 對外 tools 暴露。這樣可以避免教授誤解 MCP 是在列出實驗結果；MCP 的重點是讓使用者或 AI client 操作同一個 digital twin runtime。

## 啟動方式

在專案根目錄執行：

```bash
python3 scripts/run_mcp_server.py
```

此 server 使用 stdio transport，從標準輸入讀取 JSON-RPC 訊息，並從標準輸出回傳 JSON-RPC 結果。

## MCP Tools

### `initialize_environment`

初始化 MCP session 內的註冊狀態，包含基礎情境、室內 baseline、外部環境、設備與家具阻擋物。後續 `sample_point`、`learn_impacts`、`rank_actions` 都會使用這個註冊狀態。

初始化時可以設定的內容如下：

| 欄位 | 可以設定什麼 | 預設或限制 | 後續影響 |
| --- | --- | --- | --- |
| `scenario_name` | 選擇基礎情境，例如 `idle` 或其他內建情境名稱。 | 預設 `idle`；目前仍以標準單房間拓樸為基礎。 | 決定房間尺寸、內建裝置、內建家具與目標區域的起始模板。 |
| `baseline.indoor_temperature` | 初始室內溫度。 | 預設 29.0 °C。 | 作為溫度場 $T_0$，後續冷氣、窗戶與校正都在此基準上計算。 |
| `baseline.indoor_humidity` | 初始室內相對濕度。 | 預設 67.0%，並限制在 0--100%。 | 作為濕度場 $H_0$，影響除濕與外氣交換方向。 |
| `baseline.base_illuminance` | 初始室內背景照度。 | 預設 90.0 lux，負值會被截為 0。 | 作為照度場 $L_0$，窗戶、燈具與反射項都會疊加在此基準上。 |
| `environment.outdoor_temperature` | 室外溫度。 | 預設 33.0 °C。 | 影響窗戶造成的熱交換。 |
| `environment.outdoor_humidity` | 室外相對濕度。 | 預設 74.0%，並限制在 0--100%。 | 影響開窗後室內濕度是上升或下降。 |
| `environment.sunlight_illuminance` | 室外日照照度。 | 預設 32000.0 lux，負值會被截為 0。 | 影響窗戶直射光與照度反射來源。 |
| `environment.daylight_factor` | 日光進入室內的比例係數。 | 預設 0.95，負值會被截為 0。 | 調整外部日照轉換成室內照度的強度。 |
| `devices` | 註冊或覆寫設備。可用內建名稱 `ac_main`、`window_main`、`light_main`，也可新增 custom `ac`、`window`、`light`。 | `activation` 會限制在 0--1；`kind` 僅支援 `ac`、`window`、`light`。 | 後續 point sample、impact learning 與 action ranking 都依目前註冊設備計算。 |
| `replace_existing_devices` | 是否移除未列在 `devices` 中的內建設備。 | 預設 `false`。 | 若為 `true`，可建立只包含指定設備的 runtime 環境。 |
| `furniture` | 註冊或覆寫家具/遮蔽物。可用內建名稱 `cabinet_window`、`sofa_main`、`table_center`，也可用 `min_corner` / `max_corner` 新增自訂阻擋物。 | `activation` 會限制在 0--1；bounding box 會被限制在房間內。 | 影響光線遮蔽、冷氣/窗戶可見性、混合懲罰與照度反射。 |
| `elapsed_minutes` | 後續工具未指定時間時使用的預設 elapsed time。 | 預設 18.0 分鐘，最小為 0。 | 影響設備 dynamic activation 與查詢時間點。 |
| `steady_state_minutes` | 後續 `steady_state: true` 時使用的時間。 | 預設 120.0 分鐘，最小為 0。 | 代表接近準穩態的查詢時間。 |
| `use_hybrid_residual` | 後續工具是否預設使用 hybrid residual corrected field。 | 預設 `false`；只有存在 checkpoint 時才會套用。 | 影響 `sample_point` 與 `rank_actions` 的估計器選擇。 |

`devices` 中常用的設備欄位包括：`name`、`kind`、`activation`、`position`、`orientation`、`influence_radius`、`response_time_minutes`、`power`、`metadata`。冷氣可額外設定 `ac_mode`、`target_temperature`、`horizontal_angle_deg`、`vertical_angle_deg`；照明可設定 `illuminance_gain`；窗戶主要透過 `activation` 表示開窗比例。若要移除內建設備，可設定 `{"name": "light_main", "removed": true}`。

`furniture` 中常用的遮蔽物欄位包括：`name`、`kind`、`activation`、`min_corner`、`max_corner`、`block_strength`、`metadata`。若只要開關內建家具，只需提供 `name` 與 `activation`；若要新增自訂家具，則需提供 bounding box，例如 `min_corner: {"x": 1, "y": 1, "z": 0}` 與 `max_corner: {"x": 2, "y": 2, "z": 1}`。

輸入範例：

```json
{
  "scenario_name": "idle",
  "baseline": {
    "indoor_temperature": 28.0,
    "indoor_humidity": 64.0,
    "base_illuminance": 120.0
  },
  "environment": {
    "outdoor_temperature": 35.0,
    "outdoor_humidity": 82.0,
    "sunlight_illuminance": 18000.0,
    "daylight_factor": 0.82
  },
  "devices": [
    {
      "name": "ac_main",
      "kind": "ac",
      "activation": 0.0,
      "metadata": {
        "ac_mode": "cool",
        "target_temperature": 24.0
      }
    },
    {
      "name": "light_main",
      "kind": "light",
      "activation": 0.3,
      "illuminance_gain": 1.2
    }
  ],
  "furniture": [
    {
      "name": "cabinet_window",
      "activation": 1.0
    }
  ],
  "elapsed_minutes": 18.0,
  "steady_state_minutes": 120.0,
  "use_hybrid_residual": false
}
```

### `sample_point`

在目前註冊環境中查詢任意座標的三因子估計值。可指定 `elapsed_minutes`，也可用 `steady_state: true` 代表接近準穩態的時間。

輸入範例：

```json
{
  "x": 3.0,
  "y": 2.0,
  "z": 1.2,
  "elapsed_minutes": 18.0
}
```

或：

```json
{
  "x": 3.0,
  "y": 2.0,
  "z": 1.2,
  "steady_state": true
}
```

### `learn_impacts`

此工具用於正確處理非連網裝置 impact learning。它不是單純「跑一個情境」就宣稱已學習，而是建立或完成一筆 before/after 觀測紀錄。

第一步 `start`：輸入要開啟的設備與狀態，並盡量提供開啟前的真實 8 顆感測器讀值。

```json
{
  "device_name": "ac_main",
  "device_state": {
    "activation": 0.85,
    "kind": "ac",
    "ac_mode": "cool",
    "target_temperature": 22.0
  },
  "before_observations": {
    "floor_sw": {"temperature": 29.1, "humidity": 67.0, "illuminance": 90.0}
  },
  "sample_point": {
    "x": 5.0,
    "y": 2.0,
    "z": 1.5
  }
}
```

回傳會包含 `learning_record_id`。若尚未提供 `after_observations`，狀態會是 `RECORDING`，不會產生 learned coefficients。

第二步 `finish`：輸入同一批感測器在設備作用後的觀測值。

```json
{
  "phase": "finish",
  "learning_record_id": "record-id",
  "after_observations": {
    "floor_sw": {"temperature": 27.4, "humidity": 64.2, "illuminance": 90.0}
  }
}
```

只有同時具備 before/after observations 時，工具才會回傳 `learned_device_impacts`。若資料不足，回傳 `NEEDS_DATA`。

### `run_window_direct`

直接輸入外部窗戶條件，不經 48 組 season/weather/time preset。此工具適合接入天氣 API、手動輸入或其他非分類資料來源。

輸入範例：

```json
{
  "outdoor_temperature": 35.0,
  "outdoor_humidity": 82.0,
  "sunlight_illuminance": 18000.0,
  "opening_ratio": 0.45,
  "update_environment": true
}
```

`update_environment: true` 時，MCP session 會把該外部環境與窗戶開度更新為後續查詢使用的註冊狀態。

### `rank_actions`

輸入指定座標與目標三因子值，根據目前註冊設備產生候選操作，並依 comfort penalty 改善量排序。這已不再只針對預設 target zone，而是針對使用者指定的位置。

`rank_actions` 有明確前置條件：必須同時具備 point sample（`x`, `y`, `z`）與完整 target（`temperature`, `humidity`, `illuminance`）。`temperature_tolerance`、`humidity_tolerance` 與 `illuminance_tolerance` 可省略，省略時使用內建 comfort target 的容許範圍；但三個 target 值不可省略。若缺少 sample 或任一 target 欄位，工具會回傳錯誤，不輸出候選動作推薦。

輸入範例：

```json
{
  "x": 3.0,
  "y": 2.0,
  "z": 1.2,
  "target": {
    "temperature": 25.0,
    "humidity": 58.0,
    "illuminance": 500.0,
    "temperature_tolerance": 1.0,
    "humidity_tolerance": 6.0,
    "illuminance_tolerance": 120.0
  }
}
```

## 本地手動測試

```bash
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"manual","version":"0.1"}}}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"initialize_environment","arguments":{"baseline":{"indoor_temperature":28,"indoor_humidity":64,"base_illuminance":120},"devices":[{"name":"ac_main","kind":"ac","activation":0.85,"metadata":{"ac_mode":"cool","target_temperature":22}}]}}}' \
'{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"sample_point","arguments":{"x":5,"y":2,"z":1.5,"steady_state":true}}}' \
'{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"rank_actions","arguments":{"x":3,"y":2,"z":1.2,"target":{"temperature":25,"humidity":58,"illuminance":500}}}}' \
'{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"run_window_direct","arguments":{"outdoor_temperature":35,"outdoor_humidity":82,"sunlight_illuminance":18000,"opening_ratio":0.45,"update_environment":true}}}' \
| python3 scripts/run_mcp_server.py
```

## Claude Desktop 設定範例

若 MCP client 支援 stdio server，可加入類似設定：

```json
{
  "mcpServers": {
    "mcp-single-room-spatial-digital-twin": {
      "command": "python3",
      "args": [
        "/Volumes/DataExtended/school/scripts/run_mcp_server.py"
      ]
    }
  }
}
```

## 目前限制

- 目前是本地 stdio MCP server，不是遠端 HTTP MCP。
- 尚未加入 OAuth 或使用者權限控制。
- `initialize_environment` 目前以標準單房間拓樸為基礎，支援設備與家具註冊，但尚未完整開放任意房間 JSON 幾何。
- `learn_impacts` 需要真實 before/after 感測讀值才會產生可主張的 impact coefficients；缺資料時只記錄事件。
- 輸出以 JSON text content 為主，尚未提供 MCP resource 或圖片 resource。

## 後續可擴充方向

1. 將 `initialize_environment` 擴充為完整任意房間幾何輸入。
2. 加入 `export_heatmap` 或 MCP resource，回傳熱圖/照度圖資源。
3. 包成遠端 HTTP MCP server，部署到 Cloudflare Workers。
4. 加入 OAuth，讓遠端 MCP 可安全被不同 client 使用。
