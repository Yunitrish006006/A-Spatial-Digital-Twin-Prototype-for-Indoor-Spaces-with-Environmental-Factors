import json
import sys
from typing import Any, Dict, Optional

from .service import (
    evaluate_scenario,
    list_scenario_metadata,
    rank_scenario_actions,
    sample_scenario_point,
)


SERVER_NAME = "single-room-spatial-digital-twin"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


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
        "name": "run_scenario",
        "description": "Run a scenario and return reconstruction error, sensor calibration error, and target-zone estimates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Scenario name, for example idle, ac_only, window_only, light_only, or all_active.",
                }
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
                }
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
            },
            "required": ["scenario_name", "x", "y", "z"],
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
        elif tool_name == "run_scenario":
            payload = evaluate_scenario(_required_string(arguments, "scenario_name"))
        elif tool_name == "rank_actions":
            payload = rank_scenario_actions(_required_string(arguments, "scenario_name"))
        elif tool_name == "sample_point":
            payload = sample_scenario_point(
                scenario_name=_required_string(arguments, "scenario_name"),
                x=_required_number(arguments, "x"),
                y=_required_number(arguments, "y"),
                z=_required_number(arguments, "z"),
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
