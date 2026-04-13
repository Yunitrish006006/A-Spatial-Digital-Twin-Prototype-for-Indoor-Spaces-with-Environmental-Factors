import json
import sys
from typing import Any, Dict, Optional

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


SERVER_NAME = "single-room-spatial-digital-twin"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
DEVICE_OVERRIDE_KEYS = ("ac_main", "window_main", "light_main")
FURNITURE_OVERRIDE_KEYS = ("cabinet_window", "sofa_main", "table_center")
AC_MODE_OPTIONS = {"cool", "dry", "heat", "fan"}
AC_SWING_OPTIONS = {"fixed", "swing"}

SCENARIO_OVERRIDE_PROPERTIES = {
    "ac_main": {
        "type": "number",
        "description": "Optional AC activation override from 0.0 to 1.0.",
    },
    "window_main": {
        "type": "number",
        "description": "Optional window activation override from 0.0 to 1.0.",
    },
    "light_main": {
        "type": "number",
        "description": "Optional lighting activation override from 0.0 to 1.0.",
    },
    "cabinet_window": {
        "type": "number",
        "description": "Optional furniture blocker activation for the window-side cabinet from 0.0 to 1.0.",
    },
    "sofa_main": {
        "type": "number",
        "description": "Optional furniture blocker activation for the main sofa from 0.0 to 1.0.",
    },
    "table_center": {
        "type": "number",
        "description": "Optional furniture blocker activation for the center table from 0.0 to 1.0.",
    },
    "ac_mode": {
        "type": "string",
        "description": "Optional AC mode: cool, dry, heat, or fan.",
    },
    "ac_target_temperature": {
        "type": "number",
        "description": "Optional AC target temperature in Celsius, clamped to 20 to 33.",
    },
    "ac_horizontal_mode": {
        "type": "string",
        "description": "Optional AC left/right mode: fixed or swing.",
    },
    "ac_horizontal_angle_deg": {
        "type": "number",
        "description": "Optional fixed left/right angle in degrees, clamped to -60 to 60.",
    },
    "ac_vertical_mode": {
        "type": "string",
        "description": "Optional AC up/down mode: fixed or swing.",
    },
    "ac_vertical_angle_deg": {
        "type": "number",
        "description": "Optional fixed up/down angle in degrees, clamped to 0 to 40.",
    },
    "extra_devices": {
        "type": "array",
        "description": "Optional custom device specs to append, for example extra AC units, windows, or lights.",
    },
    "device_specs": {
        "type": "array",
        "description": "Optional authoritative or partial device spec overrides for built-in or custom devices, including remove or duplicate behavior.",
    },
}


TOOLS = [
    {
        "name": "list_scenarios",
        "description": "List built-in room digital twin validation scenarios.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "list_window_scenarios",
        "description": "List the 48 window scenarios across morning/noon/afternoon/night, cloudy/sunny/rainy, and four seasons.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "run_scenario",
        "description": "Run a scenario and return reconstruction error, sensor calibration error, and target-zone estimates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Scenario name, for example idle, ac_only, window_only, light_only, or all_active.",
                },
                **SCENARIO_OVERRIDE_PROPERTIES,
            },
            "required": ["scenario_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "rank_actions",
        "description": "Rank candidate appliance actions by target-zone comfort improvement for a scenario.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Scenario name to evaluate.",
                },
                **SCENARIO_OVERRIDE_PROPERTIES,
            },
            "required": ["scenario_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sample_point",
        "description": "Estimate temperature, humidity, and illuminance at a point in a scenario.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string"},
                "x": {"type": "number", "description": "X coordinate in meters."},
                "y": {"type": "number", "description": "Y coordinate in meters."},
                "z": {"type": "number", "description": "Z coordinate in meters."},
                **SCENARIO_OVERRIDE_PROPERTIES,
            },
            "required": ["scenario_name", "x", "y", "z"],
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_baseline",
        "description": "Compare the appliance influence model against an inverse distance weighting baseline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Scenario name to evaluate.",
                },
                **SCENARIO_OVERRIDE_PROPERTIES,
            },
            "required": ["scenario_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "learn_impacts",
        "description": "Learn active non-networked appliance impact coefficients from before/after sensor observations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Scenario name with active appliances.",
                },
                **SCENARIO_OVERRIDE_PROPERTIES,
            },
            "required": ["scenario_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_window_matrix",
        "description": "Run all 48 window-only time/weather/season simulations and return target-zone estimates.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "run_window_direct",
        "description": "Run a window-only simulation from directly supplied outdoor temperature, humidity, sunlight, and opening ratio.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outdoor_temperature": {"type": "number", "description": "Outdoor temperature in Celsius."},
                "outdoor_humidity": {"type": "number", "description": "Outdoor relative humidity in percent."},
                "sunlight_illuminance": {"type": "number", "description": "Outdoor sunlight illuminance in lux."},
                "opening_ratio": {
                    "type": "number",
                    "description": "Equivalent window opening ratio from 0.0 to 1.0. Defaults to 0.7.",
                },
                "cabinet_window": {
                    "type": "number",
                    "description": "Optional furniture blocker activation for the window-side cabinet from 0.0 to 1.0.",
                },
                "sofa_main": {
                    "type": "number",
                    "description": "Optional furniture blocker activation for the main sofa from 0.0 to 1.0.",
                },
                "table_center": {
                    "type": "number",
                    "description": "Optional furniture blocker activation for the center table from 0.0 to 1.0.",
                },
                "indoor_temperature": {
                    "type": "number",
                    "description": "Optional indoor baseline temperature in Celsius.",
                },
                "indoor_humidity": {
                    "type": "number",
                    "description": "Optional indoor baseline relative humidity in percent.",
                },
                "base_illuminance": {
                    "type": "number",
                    "description": "Optional indoor baseline illuminance in lux. Defaults to 70.",
                },
                "daylight_factor": {
                    "type": "number",
                    "description": "Optional daylight transmission factor. Defaults to 0.95.",
                },
                "elapsed_minutes": {
                    "type": "number",
                    "description": "Optional elapsed minutes after opening the window. Defaults to 18.",
                },
                "extra_devices": {
                    "type": "array",
                    "description": "Optional custom device specs to append, for example extra AC units, windows, or lights.",
                },
            },
            "required": ["outdoor_temperature", "outdoor_humidity", "sunlight_illuminance"],
            "additionalProperties": False,
        },
    },
]


class LocalMCPServer:
    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method")
        message_id = message.get("id")

        if method == "notifications/initialized":
            return None

        try:
            result = self._dispatch(method, message.get("params") or {})
            return {"jsonrpc": "2.0", "id": message_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32000,
                    "message": str(exc),
                },
            }

    def _dispatch(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if method == "initialize":
            return {
                "protocolVersion": params.get("protocolVersion", DEFAULT_PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": TOOLS}
        if method == "tools/call":
            return self._call_tool(params)
        raise ValueError(f"Unsupported MCP method: {method}")

    def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}

        if tool_name == "list_scenarios":
            payload = list_scenario_metadata()
        elif tool_name == "list_window_scenarios":
            payload = list_window_scenario_metadata()
        elif tool_name == "run_scenario":
            payload = evaluate_scenario(
                _required_string(arguments, "scenario_name"),
                _device_overrides(arguments),
                _device_metadata_overrides(arguments),
                _furniture_overrides(arguments),
                extra_devices=_extra_devices(arguments),
                device_specs=_device_specs(arguments),
            )
        elif tool_name == "rank_actions":
            payload = rank_scenario_actions(
                _required_string(arguments, "scenario_name"),
                _device_overrides(arguments),
                _device_metadata_overrides(arguments),
                _furniture_overrides(arguments),
                extra_devices=_extra_devices(arguments),
                device_specs=_device_specs(arguments),
            )
        elif tool_name == "sample_point":
            payload = sample_scenario_point(
                scenario_name=_required_string(arguments, "scenario_name"),
                x=_required_number(arguments, "x"),
                y=_required_number(arguments, "y"),
                z=_required_number(arguments, "z"),
                device_overrides=_device_overrides(arguments),
                device_metadata_overrides=_device_metadata_overrides(arguments),
                furniture_overrides=_furniture_overrides(arguments),
                extra_devices=_extra_devices(arguments),
                device_specs=_device_specs(arguments),
            )
        elif tool_name == "compare_baseline":
            payload = compare_scenario_baseline(
                _required_string(arguments, "scenario_name"),
                _device_overrides(arguments),
                _device_metadata_overrides(arguments),
                _furniture_overrides(arguments),
                extra_devices=_extra_devices(arguments),
                device_specs=_device_specs(arguments),
            )
        elif tool_name == "learn_impacts":
            payload = learn_scenario_impacts(
                _required_string(arguments, "scenario_name"),
                _device_overrides(arguments),
                _device_metadata_overrides(arguments),
                _furniture_overrides(arguments),
                extra_devices=_extra_devices(arguments),
                device_specs=_device_specs(arguments),
            )
        elif tool_name == "run_window_matrix":
            payload = evaluate_window_matrix()
        elif tool_name == "run_window_direct":
            payload = evaluate_window_direct(
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
                extra_devices=_extra_devices(arguments),
                device_specs=_device_specs(arguments),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=False, indent=2),
                }
            ],
            "isError": False,
        }


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


def _device_overrides(arguments: Dict[str, Any]) -> Dict[str, float]:
    overrides: Dict[str, float] = {}
    for key in DEVICE_OVERRIDE_KEYS:
        if key in arguments:
            overrides[key] = max(0.0, min(1.0, _required_number(arguments, key)))
    return overrides


def _furniture_overrides(arguments: Dict[str, Any]) -> Dict[str, float]:
    overrides: Dict[str, float] = {}
    for key in FURNITURE_OVERRIDE_KEYS:
        if key in arguments and arguments[key] is not None:
            overrides[key] = max(0.0, min(1.0, float(arguments[key])))
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


def serve_stdio() -> None:
    server = LocalMCPServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = server.handle_message(json.loads(line))
        if response is None:
            continue
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main() -> None:
    serve_stdio()


if __name__ == "__main__":
    main()
