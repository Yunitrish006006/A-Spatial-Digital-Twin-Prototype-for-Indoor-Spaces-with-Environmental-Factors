import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


SUPPORTED_DEVICE_KINDS = {"ac", "window", "light"}
STANDARD_SENSOR_POSITIONS = {
    "floor_sw": ("0", "0", "0"),
    "floor_se": ("width", "0", "0"),
    "floor_nw": ("0", "length", "0"),
    "floor_ne": ("width", "length", "0"),
    "ceiling_sw": ("0", "0", "height"),
    "ceiling_se": ("width", "0", "height"),
    "ceiling_nw": ("0", "length", "height"),
    "ceiling_ne": ("width", "length", "height"),
}


def _number(value, path: str, errors: List[str]) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    errors.append(f"{path} must be a number.")
    return 0.0


def _section(payload: Dict, name: str, errors: List[str]) -> Dict:
    value = payload.get(name)
    if isinstance(value, dict):
        return value
    errors.append(f"{name} must be an object.")
    return {}


def _list(payload: Dict, name: str, errors: List[str]) -> List:
    value = payload.get(name)
    if isinstance(value, list):
        return value
    errors.append(f"{name} must be an array.")
    return []


def _vector(value, path: str, errors: List[str]) -> Dict[str, float]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be a vector object with x, y, z.")
        return {"x": 0.0, "y": 0.0, "z": 0.0}
    return {
        axis: _number(value.get(axis), f"{path}.{axis}", errors)
        for axis in ("x", "y", "z")
    }


def _in_bounds(point: Dict[str, float], dims: Dict[str, float]) -> bool:
    return (
        0.0 <= point["x"] <= dims["width"]
        and 0.0 <= point["y"] <= dims["length"]
        and 0.0 <= point["z"] <= dims["height"]
    )


def _validate_unique_names(items: Iterable, section: str, errors: List[str]) -> None:
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{section}[{index}] must be an object.")
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{section}[{index}].name is required.")
            continue
        if name in seen:
            errors.append(f"{section} contains duplicate name: {name}.")
        seen.add(name)


def _validate_point(point: Dict[str, float], dims: Dict[str, float], path: str, errors: List[str]) -> None:
    if not _in_bounds(point, dims):
        errors.append(
            f"{path} is outside room bounds: "
            f"x 0..{dims['width']}, y 0..{dims['length']}, z 0..{dims['height']}."
        )


def _validate_box(item: Dict, dims: Dict[str, float], path: str, errors: List[str]) -> None:
    min_corner = _vector(item.get("min_corner"), f"{path}.min_corner", errors)
    max_corner = _vector(item.get("max_corner"), f"{path}.max_corner", errors)
    _validate_point(min_corner, dims, f"{path}.min_corner", errors)
    _validate_point(max_corner, dims, f"{path}.max_corner", errors)
    for axis in ("x", "y", "z"):
        if min_corner[axis] >= max_corner[axis]:
            errors.append(f"{path}.min_corner.{axis} must be smaller than max_corner.{axis}.")


def _expected_sensor_position(name: str, dims: Dict[str, float]) -> Tuple[float, float, float]:
    spec = STANDARD_SENSOR_POSITIONS[name]
    values = {"0": 0.0, "width": dims["width"], "length": dims["length"], "height": dims["height"]}
    return tuple(values[item] for item in spec)


def validate(payload: Dict) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    schema_version = payload.get("schema_version") or _section(payload, "metadata", errors).get("schema")
    if schema_version != "room-design-v1":
        errors.append("schema_version must be room-design-v1.")

    room = _section(payload, "room", errors)
    dims = {
        "width": _number(room.get("width_m"), "room.width_m", errors),
        "length": _number(room.get("length_m"), "room.length_m", errors),
        "height": _number(room.get("height_m"), "room.height_m", errors),
    }
    for key, value in dims.items():
        if value <= 0:
            errors.append(f"room.{key}_m must be greater than 0.")
    for field in ("name", "base_temperature_c", "base_humidity_pct", "base_illuminance_lux"):
        if field not in room:
            errors.append(f"room.{field} is required.")

    grid = _section(payload, "grid_resolution", errors)
    for field in ("nx", "ny", "nz"):
        value = _number(grid.get(field), f"grid_resolution.{field}", errors)
        if value <= 0 or int(value) != value:
            errors.append(f"grid_resolution.{field} must be a positive integer.")

    environment = _section(payload, "environment", errors)
    for field in ("outdoor_temperature_c", "outdoor_humidity_pct", "sunlight_illuminance_lux", "daylight_factor"):
        if field not in environment:
            errors.append(f"environment.{field} is required.")

    sensors = _list(payload, "sensors", errors)
    _validate_unique_names(sensors, "sensors", errors)
    if len(sensors) < 8:
        errors.append("sensors must include at least 8 sensors.")
    sensor_by_name = {item.get("name"): item for item in sensors if isinstance(item, dict)}
    for name in STANDARD_SENSOR_POSITIONS:
        sensor = sensor_by_name.get(name)
        if sensor is None:
            errors.append(f"standard corner sensor is missing: {name}.")
            continue
        position = _vector(sensor.get("position"), f"sensors.{name}.position", errors)
        _validate_point(position, dims, f"sensors.{name}.position", errors)
        expected = _expected_sensor_position(name, dims)
        actual = (position["x"], position["y"], position["z"])
        if any(abs(a - b) > 1e-6 for a, b in zip(actual, expected)):
            errors.append(f"sensors.{name}.position should be {expected}, got {actual}.")

    zones = _list(payload, "zones", errors)
    _validate_unique_names(zones, "zones", errors)
    if not zones:
        errors.append("zones must include at least one zone.")
    for index, zone in enumerate(zones):
        if isinstance(zone, dict):
            _validate_box(zone, dims, f"zones[{index}]", errors)

    devices = _list(payload, "devices", errors)
    _validate_unique_names(devices, "devices", errors)
    if not devices:
        errors.append("devices must include at least one device.")
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            errors.append(f"devices[{index}] must be an object.")
            continue
        kind = str(device.get("kind", "")).lower()
        if kind not in SUPPORTED_DEVICE_KINDS:
            errors.append(f"devices[{index}].kind must be one of {sorted(SUPPORTED_DEVICE_KINDS)}.")
        position = _vector(device.get("position"), f"devices[{index}].position", errors)
        _validate_point(position, dims, f"devices[{index}].position", errors)
        _vector(device.get("orientation"), f"devices[{index}].orientation", errors)
        activation = _number(device.get("activation"), f"devices[{index}].activation", errors)
        if not 0.0 <= activation <= 1.0:
            errors.append(f"devices[{index}].activation must be between 0.0 and 1.0.")
        if "influence_radius_m" in device and _number(device.get("influence_radius_m"), f"devices[{index}].influence_radius_m", errors) <= 0:
            errors.append(f"devices[{index}].influence_radius_m must be greater than 0.")

    furniture = _list(payload, "furniture", errors)
    _validate_unique_names(furniture, "furniture", errors)
    for index, item in enumerate(furniture):
        if isinstance(item, dict):
            _validate_box(item, dims, f"furniture[{index}]", errors)
            block_strength = item.get("block_strength")
            metadata_block_strength = item.get("metadata", {}).get("block_strength") if isinstance(item.get("metadata"), dict) else None
            if block_strength is not None:
                warnings.append(f"furniture[{index}].block_strength should be moved to metadata.block_strength for Python model compatibility.")
            if block_strength is None and metadata_block_strength is None:
                warnings.append(f"furniture[{index}] has no block_strength value.")

    comfort_target = _section(payload, "comfort_target", errors)
    if "position" in comfort_target:
        position = _vector(comfort_target.get("position"), "comfort_target.position", errors)
        _validate_point(position, dims, "comfort_target.position", errors)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate room-design-v1 JSON files.")
    parser.add_argument("paths", nargs="+", help="Room design JSON files to validate.")
    args = parser.parse_args()

    has_errors = False
    for raw_path in args.paths:
        path = Path(raw_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"{path}: invalid JSON: {exc}", file=sys.stderr)
            has_errors = True
            continue
        errors, warnings = validate(payload)
        if errors:
            has_errors = True
            print(f"{path}: INVALID")
            for error in errors:
                print(f"  error: {error}")
        else:
            print(f"{path}: OK")
        for warning in warnings:
            print(f"  warning: {warning}")
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
