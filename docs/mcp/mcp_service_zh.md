# MCP-Enabled 數位孿生服務設計與使用方式

本專案已加入一個本地 stdio MCP server，可讓支援 MCP 的 client 直接呼叫單房間數位孿生模型。若將 MCP 納入論文主題，建議定位為「AI-agent-accessible interface」，也就是讓模型可被 AI client 以標準工具介面使用，而不是把整篇論文改成通訊協定研究。

## 為什麼適合做成 MCP

本研究原型的核心能力很適合包成 MCP tools：

- 查詢內建模擬情境。
- 執行情境並回傳重建誤差。
- 取得冷氣、窗戶、照明等候選動作排序。
- 查詢房間任意座標的 temperature、humidity、illuminance 估計值。
- 比較本研究模型與 IDW baseline。
- 學習非連網裝置啟用前後造成的環境影響係數。
- 執行窗戶在時段、天氣、季節組合下的 48 組模擬矩陣。
- 直接提供窗戶外部條件，例如外部溫度、濕度、日照與開窗比例，立即估計三因子區域影響。

MCP 化後，模型不只是 Python script，而是可以被 AI client 當作外部工具呼叫。

## 啟動方式

在專案根目錄執行：

```bash
python3 scripts/run_mcp_server.py
```

此 server 使用 stdio transport，會從標準輸入讀取 JSON-RPC 訊息，並從標準輸出回傳 JSON-RPC 結果。

## MCP Tools

### `list_scenarios`

列出內建的 8 組驗證情境。

輸入：

```json
{}
```

### `list_window_scenarios`

列出 48 組窗戶矩陣情境，包含早上/中午/下午/晚上、陰天/晴天/雨天、春夏秋冬。

輸入：

```json
{}
```

### `run_scenario`

執行指定情境，回傳場重建誤差、感測器校正前後誤差、目標區域估計值。

輸入：

```json
{
  "scenario_name": "idle"
}
```

### `rank_actions`

針對指定情境，依舒適度改善分數排序候選設備動作。

輸入：

```json
{
  "scenario_name": "idle"
}
```

### `sample_point`

估計指定座標的三個環境因素。

輸入：

```json
{
  "scenario_name": "light_only",
  "x": 3.0,
  "y": 2.0,
  "z": 1.5
}
```

### `compare_baseline`

比較本研究的 appliance influence model 與 IDW baseline。

輸入：

```json
{
  "scenario_name": "light_only"
}
```

### `learn_impacts`

從裝置啟用前後的感測器觀測差異，估計 active non-networked appliance 的影響係數。

輸入：

```json
{
  "scenario_name": "ac_only"
}
```

### `run_window_matrix`

一次執行全部 48 組窗戶矩陣模擬，回傳每組情境的外部條件、窗戶區、中心區與門側區估計值。

輸入：

```json
{}
```

### `run_window_direct`

不使用列舉矩陣，直接由使用者提供外部條件建立窗戶模擬。此工具適合接入實際天氣 API、手動輸入或其他非分類資料來源。

輸入：

```json
{
  "outdoor_temperature": 35.0,
  "outdoor_humidity": 82.0,
  "sunlight_illuminance": 18000.0,
  "opening_ratio": 0.45,
  "indoor_temperature": 28.0,
  "indoor_humidity": 64.0
}
```

## 可用情境名稱

- `idle`
- `ac_only`
- `window_only`
- `light_only`
- `ac_window`
- `window_light`
- `ac_light`
- `all_active`

窗戶矩陣情境使用以下命名格式：

```text
window_<season>_<weather>_<time>
```

例如：

- `window_summer_sunny_noon`
- `window_winter_rainy_night`

## 本地手動測試

可用下面的 JSON-RPC 訊息手動測試：

```bash
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"manual","version":"0.1"}}}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"rank_actions","arguments":{"scenario_name":"idle"}}}' \
'{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"run_window_matrix","arguments":{}}}' \
'{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"run_window_direct","arguments":{"outdoor_temperature":35,"outdoor_humidity":82,"sunlight_illuminance":18000,"opening_ratio":0.45}}}' \
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
- 模型情境仍以內建標準案例、窗戶矩陣案例與窗戶 direct input 為主，尚未開放任意房間 JSON 輸入。
- 輸出以 JSON text content 為主，尚未提供 MCP resource 或圖片 resource。

## 後續可擴充方向

1. 加入 `create_room_simulation` tool，讓 client 傳入自訂房間、設備與外部環境。
2. 加入 `export_heatmap` tool，讓 MCP 回傳 SVG 熱圖檔案路徑或 resource。
3. 包成遠端 HTTP MCP server，部署到 Cloudflare Workers。
4. 加入 OAuth，讓遠端 MCP 可安全被不同 client 使用。
