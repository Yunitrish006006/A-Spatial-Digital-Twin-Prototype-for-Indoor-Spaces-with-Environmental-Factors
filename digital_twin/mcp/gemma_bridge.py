import argparse
import json
import re
from typing import Any, Callable, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from digital_twin.core.service import list_scenario_metadata, list_window_scenario_metadata
from digital_twin.mcp.mcp_server import LocalMCPServer, TOOLS as MCP_TOOLS


DEFAULT_MODEL = "gemma4:26b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEVICE_OVERRIDE_KEYS = ("ac_main", "window_main", "light_main")
FURNITURE_OVERRIDE_KEYS = ("cabinet_window", "sofa_main", "table_center")
AC_MODE_OPTIONS = {"cool", "dry", "heat", "fan"}
AC_SWING_OPTIONS = {"fixed", "swing"}
MCP_TOOL_NAMES = {tool["name"] for tool in MCP_TOOLS}
_BRIDGE_SERVER = LocalMCPServer()


ToolFunction = Callable[[Dict[str, Any]], Dict[str, Any]]


def ask_with_gemma(
    question: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    selected = select_tool(question=question, model=model, ollama_url=ollama_url)
    if selected["tool"] == "none":
        return selected.get("answer", "這個問題不需要呼叫數位孿生工具。")

    tool_result = execute_tool(selected["tool"], selected.get("arguments", {}))
    return summarize_with_gemma(
        question=question,
        tool_name=selected["tool"],
        tool_arguments=selected.get("arguments", {}),
        tool_result=tool_result,
        model=model,
        ollama_url=ollama_url,
    )


def select_tool(
    question: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> Dict[str, Any]:
    prompt = build_tool_selection_prompt(question)
    response = ollama_generate(prompt=prompt, model=model, ollama_url=ollama_url)
    parsed = parse_json_object(response)
    if parsed and parsed.get("tool") in available_tools():
        return parsed
    return heuristic_tool_selection(question)


def summarize_with_gemma(
    question: str,
    tool_name: str,
    tool_arguments: Dict[str, Any],
    tool_result: Dict[str, Any],
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    prompt = f"""你是一個室內環境數位孿生研究助理。
請根據工具輸出，用繁體中文回答使用者問題。
回答要直接、清楚、不要編造工具輸出以外的數據。

使用者問題：
{question}

呼叫工具：
{tool_name}

工具參數：
{json.dumps(tool_arguments, ensure_ascii=False, indent=2)}

工具輸出：
{json.dumps(tool_result, ensure_ascii=False, indent=2)}

請輸出回答："""
    return ollama_generate(prompt=prompt, model=model, ollama_url=ollama_url).strip()


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    tools = available_tools()
    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}")
    return tools[tool_name](arguments)


def _execute_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    response = _BRIDGE_SERVER.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
    )
    if response is None:
        return {}
    if "error" in response:
        raise ValueError(response["error"]["message"])
    return json.loads(response["result"]["content"][0]["text"])


def available_tools() -> Dict[str, ToolFunction]:
    tools = {name: (lambda arguments, tool_name=name: _execute_mcp_tool(tool_name, arguments)) for name in MCP_TOOL_NAMES}
    tools["none"] = lambda _arguments: {"message": "No tool was required."}
    return tools


def build_tool_selection_prompt(question: str) -> str:
    return f"""你要把使用者問題轉成一個工具呼叫。
只能輸出 JSON，不要輸出 Markdown，不要加解釋。

可用工具：
1. initialize_environment: 初始化房間基準、外部環境、設備與家具。arguments={{"baseline":{{"indoor_temperature":29,"indoor_humidity":67,"base_illuminance":90}},"environment":{{"outdoor_temperature":33,"outdoor_humidity":74,"sunlight_illuminance":32000}},"devices":[{{"name":"ac_main","kind":"ac","activation":0.0}}],"furniture":[{{"name":"cabinet_window","activation":1.0}}]}}
2. sample_point: 查指定座標在 elapsed_minutes 或 steady_state 下的溫度/濕度/照度。arguments={{"x":3,"y":2,"z":1.2,"elapsed_minutes":18}} 或 {{"x":3,"y":2,"z":1.2,"steady_state":true}}
3. learn_impacts: 建立或完成 before/after impact learning record。start arguments={{"device_name":"ac_main","device_state":{{"activation":0.85,"kind":"ac","ac_mode":"cool"}},"before_observations":{{...}}}}；finish arguments={{"phase":"finish","learning_record_id":"...","after_observations":{{...}}}}
4. run_window_direct: 直接提供窗戶外部條件。arguments={{"outdoor_temperature":35,"outdoor_humidity":82,"sunlight_illuminance":18000,"opening_ratio":0.45}}
5. rank_actions: 輸入指定座標與目標，依註冊設備排序控制動作。arguments={{"x":3,"y":2,"z":1.2,"target":{{"temperature":25,"humidity":58,"illuminance":500}}}}
6. none: 不需要工具。

輸出格式範例：
{{"tool":"rank_actions","arguments":{{"x":3,"y":2,"z":1.2,"target":{{"temperature":25,"humidity":58,"illuminance":500}}}}}}

使用者問題：
{question}
"""


def heuristic_tool_selection(question: str) -> Dict[str, Any]:
    lowered = question.lower()
    direct_window_arguments = _parse_direct_window_arguments(lowered)
    if direct_window_arguments:
        return {"tool": "run_window_direct", "arguments": direct_window_arguments}

    if any(keyword in lowered for keyword in ["初始化", "註冊", "register", "設備", "家具", "baseline"]):
        return {"tool": "initialize_environment", "arguments": {}}

    if any(keyword in lowered for keyword in ["推薦", "排序", "action", "rank", "開冷氣", "開窗", "開燈"]):
        numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", lowered)]
        point = {"x": 3.0, "y": 2.0, "z": 1.2}
        if len(numbers) >= 3:
            point = {"x": numbers[0], "y": numbers[1], "z": numbers[2]}
        return {"tool": "rank_actions", "arguments": point}

    if any(keyword in lowered for keyword in ["座標", "point", "sample", "x=", "y=", "z="]):
        numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", lowered)]
        if len(numbers) >= 3:
            return {"tool": "sample_point", "arguments": {"x": numbers[0], "y": numbers[1], "z": numbers[2]}}

    if any(keyword in lowered for keyword in ["學習", "影響", "非連網", "appliance impact", "learn"]):
        return {
            "tool": "learn_impacts",
            "arguments": {
                "device_name": _device_name_from_text(lowered),
                "device_state": {"activation": 1.0},
            },
        }

    return {"tool": "none", "answer": "這個問題沒有明確對應到目前的數位孿生工具。"}


def _parse_direct_window_arguments(text: str) -> Optional[Dict[str, float]]:
    direct_keywords = [
        "直接",
        "外部溫度",
        "室外溫度",
        "外面溫度",
        "outdoor",
        "sunlight",
        "illuminance",
        "lux",
        "lx",
        "開窗比例",
    ]
    if not (("窗戶" in text or "window" in text) and any(keyword in text for keyword in direct_keywords)):
        return None
    numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", text)]
    if len(numbers) < 3:
        return None
    arguments: Dict[str, float] = {
        "outdoor_temperature": numbers[0],
        "outdoor_humidity": numbers[1],
        "sunlight_illuminance": numbers[2],
    }
    if len(numbers) >= 4:
        opening_ratio = numbers[3] / 100.0 if numbers[3] > 1.0 else numbers[3]
        arguments["opening_ratio"] = opening_ratio
    if len(numbers) >= 5:
        arguments["indoor_temperature"] = numbers[4]
    if len(numbers) >= 6:
        arguments["indoor_humidity"] = numbers[5]
    return arguments


def _device_name_from_text(text: str) -> str:
    if any(keyword in text for keyword in ["冷氣", "ac", "air"]):
        return "ac_main"
    if any(keyword in text for keyword in ["窗戶", "window"]):
        return "window_main"
    if any(keyword in text for keyword in ["燈", "照明", "light"]):
        return "light_main"
    return "ac_main"


def _device_overrides(arguments: Dict[str, Any]) -> Dict[str, float]:
    overrides: Dict[str, float] = {}
    for key in DEVICE_OVERRIDE_KEYS:
        if key in arguments:
            overrides[key] = max(0.0, min(1.0, _required_number(arguments, key)))
    return overrides


def _furniture_overrides(arguments: Dict[str, Any]) -> Dict[str, float]:
    overrides: Dict[str, float] = {}
    for key in FURNITURE_OVERRIDE_KEYS:
        if key in arguments:
            overrides[key] = max(0.0, min(1.0, _required_number(arguments, key)))
    return overrides


def _device_metadata_overrides(arguments: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    ac_metadata: Dict[str, Any] = {}

    ac_mode = arguments.get("ac_mode")
    if ac_mode is not None:
        if not isinstance(ac_mode, str) or ac_mode not in AC_MODE_OPTIONS:
            raise ValueError("'ac_mode' must be one of cool, dry, heat, or fan.")
        ac_metadata["ac_mode"] = ac_mode

    horizontal_mode = arguments.get("ac_horizontal_mode")
    if horizontal_mode is not None:
        if not isinstance(horizontal_mode, str) or horizontal_mode not in AC_SWING_OPTIONS:
            raise ValueError("'ac_horizontal_mode' must be 'fixed' or 'swing'.")
        ac_metadata["horizontal_mode"] = horizontal_mode

    vertical_mode = arguments.get("ac_vertical_mode")
    if vertical_mode is not None:
        if not isinstance(vertical_mode, str) or vertical_mode not in AC_SWING_OPTIONS:
            raise ValueError("'ac_vertical_mode' must be 'fixed' or 'swing'.")
        ac_metadata["vertical_mode"] = vertical_mode

    if "ac_target_temperature" in arguments:
        ac_metadata["target_temperature"] = max(20.0, min(33.0, _required_number(arguments, "ac_target_temperature")))
    if "ac_horizontal_angle_deg" in arguments:
        ac_metadata["horizontal_angle_deg"] = max(
            -60.0,
            min(60.0, _required_number(arguments, "ac_horizontal_angle_deg")),
        )
    if "ac_vertical_angle_deg" in arguments:
        ac_metadata["vertical_angle_deg"] = max(
            0.0,
            min(40.0, _required_number(arguments, "ac_vertical_angle_deg")),
        )

    if not ac_metadata:
        return {}
    return {"ac_main": ac_metadata}


def _extra_devices(arguments: Dict[str, Any]) -> Optional[list]:
    value = arguments.get("extra_devices")
    return value if isinstance(value, list) else None


def _device_specs(arguments: Dict[str, Any]) -> Optional[list]:
    value = arguments.get("device_specs")
    return value if isinstance(value, list) else None


def find_scenario_name(text: str) -> Optional[str]:
    window_scenario = _find_window_scenario_from_tokens(text)
    if window_scenario:
        return window_scenario

    for scenario in list_scenario_metadata() + list_window_scenario_metadata():
        name = scenario["name"]
        if name in text:
            return name
    aliases = {
        "無設備": "idle",
        "冷氣": "ac_only",
        "開窗": "window_only",
        "窗戶": "window_only",
        "照明": "light_only",
        "燈": "light_only",
        "全部": "all_active",
        "全開": "all_active",
    }
    for alias, scenario_name in aliases.items():
        if alias in text:
            return scenario_name
    return None


def _mentions_window_matrix(text: str) -> bool:
    keywords = [
        "四季",
        "春季",
        "夏季",
        "秋季",
        "冬季",
        "晴天",
        "陰天",
        "雨天",
        "早上",
        "中午",
        "下午",
        "晚上",
        "window matrix",
        "窗戶矩陣",
    ]
    return ("窗戶" in text or "window" in text) and any(keyword in text for keyword in keywords)


def _is_window_matrix_scenario(scenario_name: str) -> bool:
    return scenario_name.startswith("window_") and scenario_name.count("_") == 3


def _find_window_scenario_from_tokens(text: str) -> Optional[str]:
    seasons = {
        "spring": "spring",
        "春季": "spring",
        "春天": "spring",
        "春": "spring",
        "summer": "summer",
        "夏季": "summer",
        "夏天": "summer",
        "夏": "summer",
        "autumn": "autumn",
        "fall": "autumn",
        "秋季": "autumn",
        "秋天": "autumn",
        "秋": "autumn",
        "winter": "winter",
        "冬季": "winter",
        "冬天": "winter",
        "冬": "winter",
    }
    weathers = {
        "cloudy": "cloudy",
        "陰天": "cloudy",
        "多雲": "cloudy",
        "sunny": "sunny",
        "晴天": "sunny",
        "晴": "sunny",
        "rainy": "rainy",
        "雨天": "rainy",
        "下雨": "rainy",
        "雨": "rainy",
    }
    times = {
        "morning": "morning",
        "早上": "morning",
        "上午": "morning",
        "noon": "noon",
        "中午": "noon",
        "afternoon": "afternoon",
        "下午": "afternoon",
        "night": "night",
        "晚上": "night",
        "夜晚": "night",
    }

    season = _first_alias_match(text, seasons)
    weather = _first_alias_match(text, weathers)
    time_of_day = _first_alias_match(text, times)
    if season and weather and time_of_day:
        return f"window_{season}_{weather}_{time_of_day}"
    return None


def _first_alias_match(text: str, aliases: Dict[str, str]) -> Optional[str]:
    for alias, value in aliases.items():
        if alias in text:
            return value
    return None


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def ollama_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    endpoint = ollama_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Could not connect to Ollama at {endpoint}: {exc}") from exc
    return body.get("response", "")


def _required_string(arguments: Dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"'{key}' must be a non-empty string.")
    return value


def _required_number(arguments: Dict[str, Any], key: str) -> float:
    value = arguments.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"'{key}' must be a number.")
    return float(value)


def _optional_number(arguments: Dict[str, Any], key: str, default: float) -> float:
    if key not in arguments:
        return default
    return _required_number(arguments, key)


def _optional_nullable_number(arguments: Dict[str, Any], key: str) -> Optional[float]:
    if key not in arguments:
        return None
    return _required_number(arguments, key)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask local Gemma through Ollama with digital twin tool access.")
    parser.add_argument("question", nargs="+", help="Question to ask Gemma.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name.")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama base URL.")
    parser.add_argument("--tool-only", action="store_true", help="Only print selected tool and raw tool output.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    question = " ".join(args.question)
    selected = select_tool(question=question, model=args.model, ollama_url=args.ollama_url)
    if args.tool_only:
        payload = {
            "selected": selected,
            "tool_result": None
            if selected["tool"] == "none"
            else execute_tool(selected["tool"], selected.get("arguments", {})),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(ask_with_gemma(question=question, model=args.model, ollama_url=args.ollama_url))


if __name__ == "__main__":
    main()
