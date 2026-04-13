import argparse
import json
import re
from typing import Any, Callable, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from digital_twin.core.service import (
    compare_scenario_baseline,
    evaluate_scenario,
    evaluate_window_direct,
    evaluate_window_matrix,
    learn_scenario_impacts,
    list_scenario_metadata,
    list_window_scenario_metadata,
    rank_scenario_actions,
    sample_scenario_point,
)


DEFAULT_MODEL = "gemma4:26b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEVICE_OVERRIDE_KEYS = ("ac_main", "window_main", "light_main")
FURNITURE_OVERRIDE_KEYS = ("cabinet_window", "sofa_main", "table_center")
AC_MODE_OPTIONS = {"cool", "dry", "heat", "fan"}
AC_SWING_OPTIONS = {"fixed", "swing"}


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


def available_tools() -> Dict[str, ToolFunction]:
    return {
        "list_scenarios": lambda _arguments: {"scenarios": list_scenario_metadata()},
        "list_window_scenarios": lambda _arguments: {"scenarios": list_window_scenario_metadata()},
        "run_scenario": lambda arguments: evaluate_scenario(
            _required_string(arguments, "scenario_name"),
            _device_overrides(arguments),
            _device_metadata_overrides(arguments),
            _furniture_overrides(arguments),
        ),
        "rank_actions": lambda arguments: rank_scenario_actions(
            _required_string(arguments, "scenario_name"),
            _device_overrides(arguments),
            _device_metadata_overrides(arguments),
            _furniture_overrides(arguments),
        ),
        "sample_point": lambda arguments: sample_scenario_point(
            scenario_name=_required_string(arguments, "scenario_name"),
            x=_required_number(arguments, "x"),
            y=_required_number(arguments, "y"),
            z=_required_number(arguments, "z"),
            device_overrides=_device_overrides(arguments),
            device_metadata_overrides=_device_metadata_overrides(arguments),
            furniture_overrides=_furniture_overrides(arguments),
        ),
        "compare_baseline": lambda arguments: compare_scenario_baseline(
            _required_string(arguments, "scenario_name"),
            _device_overrides(arguments),
            _device_metadata_overrides(arguments),
            _furniture_overrides(arguments),
        ),
        "learn_impacts": lambda arguments: learn_scenario_impacts(
            _required_string(arguments, "scenario_name"),
            _device_overrides(arguments),
            _device_metadata_overrides(arguments),
            _furniture_overrides(arguments),
        ),
        "run_window_matrix": lambda _arguments: evaluate_window_matrix(),
        "run_window_direct": lambda arguments: evaluate_window_direct(
            outdoor_temperature=_required_number(arguments, "outdoor_temperature"),
            outdoor_humidity=_required_number(arguments, "outdoor_humidity"),
            sunlight_illuminance=_required_number(arguments, "sunlight_illuminance"),
            opening_ratio=_optional_number(arguments, "opening_ratio", 0.7),
            furniture_overrides=_furniture_overrides(arguments),
            indoor_temperature=_optional_nullable_number(arguments, "indoor_temperature"),
            indoor_humidity=_optional_nullable_number(arguments, "indoor_humidity"),
            base_illuminance=_optional_number(arguments, "base_illuminance", 70.0),
            daylight_factor=_optional_number(arguments, "daylight_factor", 0.95),
            elapsed_minutes=_optional_number(arguments, "elapsed_minutes", 18.0),
        ),
        "none": lambda _arguments: {"message": "No tool was required."},
    }


def build_tool_selection_prompt(question: str) -> str:
    scenarios = ", ".join(scenario["name"] for scenario in list_scenario_metadata())
    window_scenarios = ", ".join(scenario["name"] for scenario in list_window_scenario_metadata())
    return f"""你要把使用者問題轉成一個工具呼叫。
只能輸出 JSON，不要輸出 Markdown，不要加解釋。

可用工具：
1. list_scenarios: 列出內建情境。arguments={{}}
2. list_window_scenarios: 列出 48 個窗戶時段/天氣/季節情境。arguments={{}}
3. run_scenario: 執行情境。arguments={{"scenario_name":"情境名稱","ac_main":0到1,"window_main":0到1,"light_main":0到1,"cabinet_window":0到1,"sofa_main":0到1,"table_center":0到1,"ac_mode":"cool|dry|heat|fan","ac_target_temperature":20到33,"ac_horizontal_mode":"fixed|swing","ac_horizontal_angle_deg":-60到60,"ac_vertical_mode":"fixed|swing","ac_vertical_angle_deg":0到40}}
4. rank_actions: 排序設備候選動作。arguments 與 run_scenario 相同。
5. sample_point: 查詢座標估計值。arguments={{"scenario_name":"情境名稱","x":數字,"y":數字,"z":數字}}，也可附加 run_scenario 的可選冷氣、設備與家具參數。
6. compare_baseline: 比較本研究模型與 IDW baseline。arguments 與 run_scenario 相同。
7. learn_impacts: 從前後感測資料學習非連網裝置影響。arguments 與 run_scenario 相同。
8. run_window_matrix: 執行全部 48 個窗戶矩陣模擬。arguments={{}}
9. run_window_direct: 直接提供窗戶外部條件並執行窗戶模擬。arguments={{"outdoor_temperature":數字,"outdoor_humidity":數字,"sunlight_illuminance":數字,"opening_ratio":0到1數字,"cabinet_window":0到1,"sofa_main":0到1,"table_center":0到1}}
10. none: 不需要工具。

可用情境名稱：
{scenarios}

可用窗戶矩陣情境名稱：
{window_scenarios}

輸出格式範例：
{{"tool":"rank_actions","arguments":{{"scenario_name":"idle"}}}}

使用者問題：
{question}
"""


def heuristic_tool_selection(question: str) -> Dict[str, Any]:
    lowered = question.lower()
    scenario = find_scenario_name(lowered) or "idle"
    direct_window_arguments = _parse_direct_window_arguments(lowered)
    if direct_window_arguments:
        return {"tool": "run_window_direct", "arguments": direct_window_arguments}

    if _mentions_window_matrix(lowered):
        if _is_window_matrix_scenario(scenario) and any(
            keyword in lowered for keyword in ["模擬", "run", "誤差", "mae", "結果"]
        ):
            return {"tool": "run_scenario", "arguments": {"scenario_name": scenario}}
        if any(keyword in lowered for keyword in ["列出", "清單", "有哪些", "list"]):
            return {"tool": "list_window_scenarios", "arguments": {}}
        return {"tool": "run_window_matrix", "arguments": {}}

    if any(keyword in lowered for keyword in ["座標", "point", "sample", "x=", "y=", "z="]):
        numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", lowered)]
        if len(numbers) >= 3:
            return {
                "tool": "sample_point",
                "arguments": {"scenario_name": scenario, "x": numbers[0], "y": numbers[1], "z": numbers[2]},
            }

    if any(keyword in lowered for keyword in ["推薦", "排序", "action", "rank", "開冷氣", "開窗", "開燈"]):
        return {"tool": "rank_actions", "arguments": {"scenario_name": scenario}}

    if any(keyword in lowered for keyword in ["baseline", "idw", "比較模型", "基準", "誤差比較"]):
        return {"tool": "compare_baseline", "arguments": {"scenario_name": scenario}}

    if any(keyword in lowered for keyword in ["學習", "影響", "非連網", "appliance impact", "learn"]):
        return {"tool": "learn_impacts", "arguments": {"scenario_name": scenario}}

    if any(keyword in lowered for keyword in ["情境", "scenario", "有哪些"]):
        return {"tool": "list_scenarios", "arguments": {}}

    if any(keyword in lowered for keyword in ["模擬", "run", "誤差", "mae", "結果"]):
        return {"tool": "run_scenario", "arguments": {"scenario_name": scenario}}

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
