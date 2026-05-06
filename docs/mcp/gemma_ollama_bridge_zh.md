# Gemma4 + Ollama 串接說明

本機已確認可用 Ollama 呼叫：

```text
gemma4:26b
```

此專案新增了一個本地橋接腳本，讓 Gemma 負責理解自然語言，Python 負責呼叫數位孿生工具。

## 架構

```text
User question
    ↓
Gemma4 via Ollama
    ↓
JSON tool selection
    ↓
Python digital twin service
    ↓
Tool result
    ↓
Gemma4 generates final answer
```

Gemma 本身不是 MCP client，因此它不能「自己」直接呼叫 MCP tool。這裡的做法是用 Python bridge 當中介：

- Gemma 選工具。
- Python 執行工具。
- Gemma 根據工具結果回答。

這是目前最穩定的本地整合方式。

## 使用方式

查詢建議動作：

```bash
python3 scripts/ask_gemma.py "座標 x=3 y=2 z=1.2 建議做什麼動作？"
```

只看工具選擇與原始工具輸出：

```bash
python3 scripts/ask_gemma.py "座標 x=3 y=2 z=1.2 建議做什麼動作？" --tool-only
```

查詢座標點：

```bash
python3 scripts/ask_gemma.py "座標 x=3 y=2 z=1.5 的溫度濕度照度是多少？"
```

直接輸入窗戶外部資料：

```bash
python3 scripts/ask_gemma.py "窗戶直接用外部溫度35 濕度82 日照18000 開窗比例45% 模擬" --tool-only
```

啟動 impact learning record：

```bash
python3 scripts/ask_gemma.py "學習非連網冷氣影響" --tool-only
```

指定其他 Ollama model：

```bash
python3 scripts/ask_gemma.py "座標 x=3 y=2 z=1.2 建議做什麼動作？" --model gemma4:26b
```

## 可用工具

Bridge 透過同一個 `LocalMCPServer` 呼叫目前 MCP server 暴露的五個 tools：

- `initialize_environment`
- `sample_point`
- `learn_impacts`
- `run_window_direct`
- `rank_actions`

## 和 MCP server 的關係

目前專案有兩種使用方式：

1. `scripts/run_mcp_server.py`
   作為 MCP server，給 Claude Desktop、Codex 或其他 MCP client 呼叫。
2. `scripts/ask_gemma.py`
   作為 Ollama/Gemma bridge，讓本機 Gemma 可以間接使用同一套數位孿生工具。

兩者最後都走同一套 MCP server 與 `digital_twin/core/service.py`，因此模型結果一致。

## 目前限制

- Gemma 的工具選擇是 prompt-based JSON selection，不是原生 MCP tool calling。
- 若 Gemma 回傳非 JSON，bridge 會使用簡單 heuristic fallback。
- 目前 bridge 的自然語言解析只覆蓋初始化、指定點查詢、impact learning、direct window input 與指定點 action ranking。
- `gemma4:26b` 第一次呼叫會有冷啟動時間。

## 後續可加強

1. 改用 Ollama `/api/chat` 的 tools 格式，如果模型與 Ollama 版本支援 tool calling。
2. 將 `ask_gemma.py` 改成互動式 REPL。
3. 加入自訂房間 JSON 輸入。
4. 讓 Gemma 產生論文分析段落，並強制引用 tool result。
