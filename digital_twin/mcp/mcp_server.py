import json
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from digital_twin.core.service import (
    evaluate_window_direct,
    learn_scenario_impacts_from_observations,
    rank_scenario_point_actions,
    sample_scenario_point,
)


SERVER_NAME = "single-room-spatial-digital-twin"
SERVER_VERSION = "0.2.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
ROOT = Path(__file__).resolve().parents[2]
LEARNING_LOG_PATH = ROOT / "outputs" / "data" / "mcp_impact_learning_log.jsonl"

DEFAULT_DEVICE_NAMES = ("ac_main", "window_main", "light_main")
DEFAULT_FURNITURE_NAMES = ("cabinet_window", "sofa_main", "table_center")
DEFAULT_BASELINE = {
    "indoor_temperature": 29.0,
    "indoor_humidity": 67.0,
    "base_illuminance": 90.0,
}
DEFAULT_ENVIRONMENT = {
    "outdoor_temperature": 33.0,
    "outdoor_humidity": 74.0,
    "sunlight_illuminance": 32000.0,
    "daylight_factor": 0.95,
}


POINT_PROPERTIES = {
    "x": {"type": "number", "description": "X coordinate in meters."},
    "y": {"type": "number", "description": "Y coordinate in meters."},
    "z": {"type": "number", "description": "Z coordinate in meters."},
}

BASELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "indoor_temperature": {"type": "number"},
        "indoor_humidity": {"type": "number"},
        "base_illuminance": {"type": "number"},
    },
    "additionalProperties": False,
}

ENVIRONMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "outdoor_temperature": {"type": "number"},
        "outdoor_humidity": {"type": "number"},
        "sunlight_illuminance": {"type": "number"},
        "daylight_factor": {"type": "number"},
    },
    "additionalProperties": False,
}

TOOLS = [
    {
        "name": "initialize_environment",
        "description": "Register the room scenario, devices, furniture blockers, outdoor environment, and indoor baseline used by later MCP calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Base scenario name. Defaults to idle.",
                },
                "baseline": BASELINE_SCHEMA,
                "environment": ENVIRONMENT_SCHEMA,
                "devices": {
                    "type": "array",
                    "description": "Registered device specs. Supports built-in names or custom ac/window/light devices.",
                },
                "replace_existing_devices": {
                    "type": "boolean",
                    "description": "When true, built-in devices not present in devices are removed from the registered state.",
                },
                "furniture": {
                    "type": "array",
                    "description": "Registered furniture blockers or built-in furniture activation overrides.",
                },
                "elapsed_minutes": {"type": "number"},
                "steady_state_minutes": {"type": "number"},
                "use_hybrid_residual": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "sample_point",
        "description": "Estimate temperature, humidity, and illuminance at a registered-room point after a supplied elapsed time or at steady state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                **POINT_PROPERTIES,
                "elapsed_minutes": {"type": "number"},
                "steady_state": {"type": "boolean"},
                "use_hybrid_residual": {"type": "boolean"},
            },
            "required": ["x", "y", "z"],
            "additionalProperties": False,
        },
    },
    {
        "name": "learn_impacts",
        "description": "Start or finish a before/after observation record for learning a non-networked device impact.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "description": "start or finish. Defaults to start unless a learning_record_id and after_observations are supplied.",
                },
                "learning_record_id": {"type": "string"},
                "device_name": {"type": "string"},
                "device_state": {
                    "type": "object",
                    "description": "State to apply, for example activation, kind, power, ac_mode, target_temperature, or metadata.",
                },
                "sample_point": {
                    "type": "object",
                    "properties": POINT_PROPERTIES,
                    "additionalProperties": False,
                },
                "before_observations": {
                    "type": "object",
                    "description": "Real before readings keyed by sensor name. Required for computed learning unless already recorded in start.",
                },
                "after_observations": {
                    "type": "object",
                    "description": "Real after readings keyed by sensor name. Required to compute learned impact coefficients.",
                },
                "elapsed_minutes": {"type": "number"},
                "note": {"type": "string"},
                "use_hybrid_residual": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "run_window_direct",
        "description": "Run a direct window simulation from supplied outdoor temperature, humidity, sunlight, and opening ratio.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outdoor_temperature": {"type": "number"},
                "outdoor_humidity": {"type": "number"},
                "sunlight_illuminance": {"type": "number"},
                "opening_ratio": {"type": "number"},
                "baseline": BASELINE_SCHEMA,
                "elapsed_minutes": {"type": "number"},
                "update_environment": {
                    "type": "boolean",
                    "description": "When true, store this outdoor state and window opening as the registered environment.",
                },
            },
            "required": ["outdoor_temperature", "outdoor_humidity", "sunlight_illuminance"],
            "additionalProperties": False,
        },
    },
    {
        "name": "rank_actions",
        "description": "Rank registered-device actions for reaching a target at a specified point.",
        "inputSchema": {
            "type": "object",
            "properties": {
                **POINT_PROPERTIES,
                "target": {
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number"},
                        "humidity": {"type": "number"},
                        "illuminance": {"type": "number"},
                        "temperature_tolerance": {"type": "number"},
                        "humidity_tolerance": {"type": "number"},
                        "illuminance_tolerance": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
                "elapsed_minutes": {"type": "number"},
                "steady_state": {"type": "boolean"},
                "use_hybrid_residual": {"type": "boolean"},
            },
            "required": ["x", "y", "z"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class RegisteredEnvironment:
    scenario_name: str = "idle"
    baseline: Dict[str, float] = field(default_factory=lambda: deepcopy(DEFAULT_BASELINE))
    environment: Dict[str, float] = field(default_factory=lambda: deepcopy(DEFAULT_ENVIRONMENT))
    devices: List[Dict[str, object]] = field(default_factory=list)
    furniture: List[Dict[str, object]] = field(default_factory=list)
    furniture_overrides: Dict[str, float] = field(default_factory=dict)
    elapsed_minutes: float = 18.0
    steady_state_minutes: float = 120.0
    use_hybrid_residual: bool = False


class LocalMCPServer:
    def __init__(self) -> None:
        self.state = RegisteredEnvironment()
        self.learning_records: Dict[str, Dict[str, object]] = {}

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

        if tool_name == "initialize_environment":
            payload = self._initialize_environment(arguments)
        elif tool_name == "sample_point":
            payload = self._sample_point(arguments)
        elif tool_name == "learn_impacts":
            payload = self._learn_impacts(arguments)
        elif tool_name == "run_window_direct":
            payload = self._run_window_direct(arguments)
        elif tool_name == "rank_actions":
            payload = self._rank_actions(arguments)
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

    def _initialize_environment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.state.scenario_name = str(arguments.get("scenario_name") or "idle")
        self.state.baseline.update(_clean_number_map(arguments.get("baseline"), DEFAULT_BASELINE))
        self.state.environment.update(_clean_number_map(arguments.get("environment"), DEFAULT_ENVIRONMENT))
        self.state.devices = _device_specs_from_arguments(arguments)
        self.state.furniture, self.state.furniture_overrides = _furniture_specs_from_arguments(arguments)
        if "elapsed_minutes" in arguments:
            self.state.elapsed_minutes = max(0.0, _required_number(arguments, "elapsed_minutes"))
        if "steady_state_minutes" in arguments:
            self.state.steady_state_minutes = max(0.0, _required_number(arguments, "steady_state_minutes"))
        if "use_hybrid_residual" in arguments:
            self.state.use_hybrid_residual = bool(arguments["use_hybrid_residual"])
        return self._state_payload(status="INITIALIZED")

    def _sample_point(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        elapsed_minutes, mode = self._elapsed_minutes(arguments)
        result = sample_scenario_point(
            scenario_name=self.state.scenario_name,
            x=_required_number(arguments, "x"),
            y=_required_number(arguments, "y"),
            z=_required_number(arguments, "z"),
            furniture_overrides=self.state.furniture_overrides,
            indoor_temperature=self.state.baseline["indoor_temperature"],
            indoor_humidity=self.state.baseline["indoor_humidity"],
            base_illuminance=self.state.baseline["base_illuminance"],
            elapsed_minutes=elapsed_minutes,
            use_hybrid_residual=bool(arguments.get("use_hybrid_residual", self.state.use_hybrid_residual)),
            extra_furniture=self.state.furniture,
            device_specs=self.state.devices,
            outdoor_temperature=self.state.environment["outdoor_temperature"],
            outdoor_humidity=self.state.environment["outdoor_humidity"],
            sunlight_illuminance=self.state.environment["sunlight_illuminance"],
            daylight_factor=self.state.environment["daylight_factor"],
        )
        result["sampling_mode"] = mode
        return result

    def _learn_impacts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        phase = str(arguments.get("phase") or "").lower()
        if not phase:
            phase = "finish" if arguments.get("learning_record_id") and arguments.get("after_observations") else "start"
        if phase not in {"start", "finish"}:
            raise ValueError("'phase' must be 'start' or 'finish'.")
        if phase == "finish":
            return self._finish_learning(arguments)
        return self._start_learning(arguments)

    def _start_learning(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        device_name = _required_string(arguments, "device_name")
        device_state = deepcopy(arguments.get("device_state") or {"activation": 1.0})
        after_device_specs = _device_specs_with_state(self.state.devices, device_name, device_state)
        record_id = str(uuid4())
        elapsed_minutes, mode = self._elapsed_minutes(arguments)
        sample_point_payload = _optional_point(arguments.get("sample_point"))
        before_sample = None
        expected_after_sample = None
        if sample_point_payload:
            before_sample = self._sample_point({**sample_point_payload, "elapsed_minutes": elapsed_minutes})
            original_devices = self.state.devices
            self.state.devices = after_device_specs
            expected_after_sample = self._sample_point({**sample_point_payload, "elapsed_minutes": elapsed_minutes})
            self.state.devices = original_devices

        record = {
            "learning_record_id": record_id,
            "status": "RECORDING",
            "device_name": device_name,
            "device_state": device_state,
            "device_specs": after_device_specs,
            "baseline": deepcopy(self.state.baseline),
            "environment": deepcopy(self.state.environment),
            "furniture": deepcopy(self.state.furniture),
            "furniture_overrides": deepcopy(self.state.furniture_overrides),
            "elapsed_minutes": elapsed_minutes,
            "sampling_mode": mode,
            "before_observations": deepcopy(arguments.get("before_observations")),
            "note": arguments.get("note"),
        }
        self.learning_records[record_id] = record
        self.state.devices = after_device_specs
        _append_learning_log({"event": "start", **record})

        if arguments.get("before_observations") and arguments.get("after_observations"):
            return self._finish_learning(
                {
                    "learning_record_id": record_id,
                    "after_observations": arguments["after_observations"],
                    "use_hybrid_residual": arguments.get("use_hybrid_residual"),
                }
            )

        return {
            "status": "RECORDING",
            "learning_record_id": record_id,
            "message": "已套用指定設備狀態並開始記錄；提供 after_observations 後才會計算 learned impact coefficients。",
            "device_name": device_name,
            "device_state": device_state,
            "sampling_mode": mode,
            "before_sample": before_sample,
            "expected_after_sample": expected_after_sample,
            "needs": ["after_observations"],
        }

    def _finish_learning(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        record_id = _required_string(arguments, "learning_record_id")
        record = self.learning_records.get(record_id)
        if record is None:
            raise ValueError(f"Unknown learning_record_id: {record_id}")
        before_observations = arguments.get("before_observations") or record.get("before_observations")
        after_observations = arguments.get("after_observations")
        missing = []
        if not before_observations:
            missing.append("before_observations")
        if not after_observations:
            missing.append("after_observations")
        if missing:
            return {
                "status": "NEEDS_DATA",
                "learning_record_id": record_id,
                "missing": missing,
                "message": "learn impact 需要同一批感測器的 before/after readings；缺資料時只記錄事件，不計算係數。",
            }

        result = learn_scenario_impacts_from_observations(
            scenario_name=self.state.scenario_name,
            before_observations=before_observations,
            after_observations=after_observations,
            furniture_overrides=record.get("furniture_overrides") or {},
            indoor_temperature=(record.get("baseline") or DEFAULT_BASELINE)["indoor_temperature"],
            indoor_humidity=(record.get("baseline") or DEFAULT_BASELINE)["indoor_humidity"],
            base_illuminance=(record.get("baseline") or DEFAULT_BASELINE)["base_illuminance"],
            elapsed_minutes=float(record.get("elapsed_minutes") or self.state.elapsed_minutes),
            use_hybrid_residual=bool(arguments.get("use_hybrid_residual", self.state.use_hybrid_residual)),
            extra_furniture=record.get("furniture") or [],
            device_specs=record.get("device_specs") or self.state.devices,
            outdoor_temperature=(record.get("environment") or DEFAULT_ENVIRONMENT)["outdoor_temperature"],
            outdoor_humidity=(record.get("environment") or DEFAULT_ENVIRONMENT)["outdoor_humidity"],
            sunlight_illuminance=(record.get("environment") or DEFAULT_ENVIRONMENT)["sunlight_illuminance"],
            daylight_factor=(record.get("environment") or DEFAULT_ENVIRONMENT)["daylight_factor"],
        )
        payload = {
            "status": "LEARNED",
            "learning_record_id": record_id,
            **result,
        }
        record["status"] = "LEARNED"
        record["after_observations"] = deepcopy(after_observations)
        record["result"] = deepcopy(result)
        _append_learning_log({"event": "finish", "learning_record_id": record_id, "result": result})
        return payload

    def _run_window_direct(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        baseline = deepcopy(self.state.baseline)
        baseline.update(_clean_number_map(arguments.get("baseline"), DEFAULT_BASELINE))
        elapsed_minutes = _optional_number(arguments, "elapsed_minutes", self.state.elapsed_minutes)
        opening_ratio = _optional_number(arguments, "opening_ratio", 0.7)
        result = evaluate_window_direct(
            outdoor_temperature=_required_number(arguments, "outdoor_temperature"),
            outdoor_humidity=_required_number(arguments, "outdoor_humidity"),
            sunlight_illuminance=_required_number(arguments, "sunlight_illuminance"),
            opening_ratio=opening_ratio,
            furniture_overrides=self.state.furniture_overrides,
            indoor_temperature=baseline["indoor_temperature"],
            indoor_humidity=baseline["indoor_humidity"],
            base_illuminance=baseline["base_illuminance"],
            elapsed_minutes=elapsed_minutes,
            use_hybrid_residual=self.state.use_hybrid_residual,
            extra_furniture=self.state.furniture,
            device_specs=self.state.devices,
        )
        if bool(arguments.get("update_environment", False)):
            self.state.environment.update(
                {
                    "outdoor_temperature": _required_number(arguments, "outdoor_temperature"),
                    "outdoor_humidity": _required_number(arguments, "outdoor_humidity"),
                    "sunlight_illuminance": _required_number(arguments, "sunlight_illuminance"),
                }
            )
            self.state.baseline.update(baseline)
            self.state.elapsed_minutes = elapsed_minutes
            self.state.devices = _device_specs_with_state(
                self.state.devices,
                "window_main",
                {"activation": opening_ratio, "kind": "window"},
            )
            result["registered_environment_updated"] = True
        else:
            result["registered_environment_updated"] = False
        return result

    def _rank_actions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        elapsed_minutes, mode = self._elapsed_minutes(arguments)
        target = arguments.get("target") if isinstance(arguments.get("target"), dict) else {}
        result = rank_scenario_point_actions(
            scenario_name=self.state.scenario_name,
            x=_required_number(arguments, "x"),
            y=_required_number(arguments, "y"),
            z=_required_number(arguments, "z"),
            target_temperature=_optional_mapping_number(target, "temperature"),
            target_humidity=_optional_mapping_number(target, "humidity"),
            target_illuminance=_optional_mapping_number(target, "illuminance"),
            temperature_tolerance=_optional_mapping_number(target, "temperature_tolerance"),
            humidity_tolerance=_optional_mapping_number(target, "humidity_tolerance"),
            illuminance_tolerance=_optional_mapping_number(target, "illuminance_tolerance"),
            furniture_overrides=self.state.furniture_overrides,
            indoor_temperature=self.state.baseline["indoor_temperature"],
            indoor_humidity=self.state.baseline["indoor_humidity"],
            base_illuminance=self.state.baseline["base_illuminance"],
            elapsed_minutes=elapsed_minutes,
            use_hybrid_residual=bool(arguments.get("use_hybrid_residual", self.state.use_hybrid_residual)),
            extra_furniture=self.state.furniture,
            device_specs=self.state.devices,
            outdoor_temperature=self.state.environment["outdoor_temperature"],
            outdoor_humidity=self.state.environment["outdoor_humidity"],
            sunlight_illuminance=self.state.environment["sunlight_illuminance"],
            daylight_factor=self.state.environment["daylight_factor"],
        )
        result["sampling_mode"] = mode
        return result

    def _elapsed_minutes(self, arguments: Dict[str, Any]) -> tuple[float, str]:
        if bool(arguments.get("steady_state", False)):
            return self.state.steady_state_minutes, "steady_state"
        if "elapsed_minutes" in arguments:
            return max(0.0, _required_number(arguments, "elapsed_minutes")), "elapsed"
        return self.state.elapsed_minutes, "registered_default"

    def _state_payload(self, status: str) -> Dict[str, Any]:
        return {
            "status": status,
            "scenario_name": self.state.scenario_name,
            "baseline": deepcopy(self.state.baseline),
            "environment": deepcopy(self.state.environment),
            "registered_devices": deepcopy(self.state.devices),
            "registered_furniture": deepcopy(self.state.furniture),
            "furniture_overrides": deepcopy(self.state.furniture_overrides),
            "elapsed_minutes": self.state.elapsed_minutes,
            "steady_state_minutes": self.state.steady_state_minutes,
            "use_hybrid_residual": self.state.use_hybrid_residual,
            "available_tools": [tool["name"] for tool in TOOLS],
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


def _optional_mapping_number(mapping: Dict[str, Any], key: str) -> Optional[float]:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"'{key}' must be a number.")
    return float(value)


def _clean_number_map(payload: Any, defaults: Dict[str, float]) -> Dict[str, float]:
    if not isinstance(payload, dict):
        return {}
    cleaned = {}
    for key in defaults:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            if key in {"indoor_humidity", "outdoor_humidity"}:
                cleaned[key] = max(0.0, min(100.0, float(value)))
            elif key in {"base_illuminance", "sunlight_illuminance", "daylight_factor"}:
                cleaned[key] = max(0.0, float(value))
            else:
                cleaned[key] = float(value)
    return cleaned


def _device_specs_from_arguments(arguments: Dict[str, Any]) -> List[Dict[str, object]]:
    specs = deepcopy(arguments.get("devices") or [])
    if not isinstance(specs, list):
        specs = []
    if bool(arguments.get("replace_existing_devices", False)):
        registered = {str(item.get("name")) for item in specs if isinstance(item, dict) and item.get("name")}
        for name in DEFAULT_DEVICE_NAMES:
            if name not in registered:
                specs.append({"name": name, "removed": True})
    return [item for item in specs if isinstance(item, dict)]


def _furniture_specs_from_arguments(arguments: Dict[str, Any]) -> tuple[List[Dict[str, object]], Dict[str, float]]:
    specs = deepcopy(arguments.get("furniture") or [])
    if not isinstance(specs, list):
        specs = []
    extra_furniture: List[Dict[str, object]] = []
    overrides: Dict[str, float] = {}
    for item in specs:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name in DEFAULT_FURNITURE_NAMES and isinstance(item.get("activation"), (int, float)):
            overrides[str(name)] = max(0.0, min(1.0, float(item["activation"])))
        if name not in DEFAULT_FURNITURE_NAMES or "min_corner" in item or "max_corner" in item:
            extra_furniture.append(item)
    return extra_furniture, overrides


def _device_specs_with_state(
    existing_specs: List[Dict[str, object]],
    device_name: str,
    device_state: Dict[str, object],
) -> List[Dict[str, object]]:
    specs = deepcopy(existing_specs)
    update = deepcopy(device_state)
    update["name"] = device_name
    metadata = deepcopy(update.get("metadata") or {})
    for key in (
        "ac_mode",
        "target_temperature",
        "horizontal_mode",
        "horizontal_angle_deg",
        "vertical_mode",
        "vertical_angle_deg",
    ):
        if key in update:
            metadata[key] = update[key]
    if metadata:
        update["metadata"] = metadata
    for index, spec in enumerate(specs):
        if isinstance(spec, dict) and spec.get("name") == device_name:
            merged = deepcopy(spec)
            merged.update(update)
            specs[index] = merged
            break
    else:
        specs.append(update)
    return specs


def _optional_point(payload: Any) -> Optional[Dict[str, float]]:
    if not isinstance(payload, dict):
        return None
    return {
        "x": _required_number(payload, "x"),
        "y": _required_number(payload, "y"),
        "z": _required_number(payload, "z"),
    }


def _append_learning_log(payload: Dict[str, Any]) -> None:
    try:
        LEARNING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEARNING_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        return


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
