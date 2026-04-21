import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_twin.core.demo import compare_sensors
from digital_twin.core.entities import (
    ComfortTarget,
    Device,
    Environment,
    Furniture,
    GridResolution,
    Room,
    Sensor,
    Vector3,
    Zone,
)
from digital_twin.core.scenarios import build_device
from digital_twin.physics.model import METRICS, DigitalTwinModel, FieldGrid
from digital_twin.web.render import (
    ensure_directory,
    export_field_csv,
    export_json,
    export_svg_heatmap,
    export_svg_volume_heatmap,
)


DEFAULT_ROOM_DESIGN = ROOT / "docs" / "templates" / "room_design_bedroom_01.json"
DEFAULT_WEEKLY_DATA = ROOT / "docs" / "requirements" / "bedroom_01_combined_room_and_weekly_simulation.json"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "data" / "bedroom_01_weekly"
DEFAULT_FIGURE_DIR = ROOT / "outputs" / "figures" / "bedroom_01_weekly"
DEFAULT_SIMULATION_RESOLUTION = "12x12x6"

SNAPSHOT_ORDER = ("morning_09_00", "afternoon_15_00", "night_22_00", "sleep_02_00")
SNAPSHOT_TIME = {
    "morning_09_00": "09:00",
    "afternoon_15_00": "15:00",
    "night_22_00": "22:00",
    "sleep_02_00": "02:00",
}
SNAPSHOT_TEMPERATURE_FRACTION = {
    "morning_09_00": 0.35,
    "afternoon_15_00": 1.0,
    "night_22_00": 0.45,
    "sleep_02_00": 0.0,
}
SNAPSHOT_SUNLIGHT_FRACTION = {
    "morning_09_00": 0.55,
    "afternoon_15_00": 0.95,
    "night_22_00": 0.0,
    "sleep_02_00": 0.0,
}


def main() -> None:
    args = _parse_args()
    room_design_path = Path(args.room_design)
    weekly_data_path = Path(args.weekly_data)
    output_dir = Path(args.output_dir)
    figure_dir = Path(args.figure_dir)

    room_design = _load_json(room_design_path)
    weekly_data = _load_json(weekly_data_path)
    bundle = _build_room_bundle(room_design)
    room_design_resolution = bundle["resolution"]
    bundle["resolution"] = _resolve_simulation_resolution(
        args.simulation_resolution,
        room_design_resolution,
    )

    ensure_directory(str(output_dir))
    ensure_directory(str(figure_dir))

    summary, representative = run_weekly_simulation(
        room_design=room_design,
        weekly_data=weekly_data,
        bundle=bundle,
        elapsed_minutes=args.elapsed_minutes,
        sleep_illuminance_target=args.sleep_illuminance_target,
        sleep_illuminance_tolerance=args.sleep_illuminance_tolerance,
    )
    summary["source"] = {
        "room_design": str(room_design_path),
        "weekly_data": str(weekly_data_path),
    }
    summary["room_design_grid_resolution"] = _resolution_dict(room_design_resolution)
    summary["assumptions"] = [
        "Physical room geometry, zones, devices, furniture, sensors, and comfort target come from the room-design-v1 file.",
        "Weekly sensor snapshots are used as observed corner-sensor inputs for trilinear residual correction and active-device calibration.",
        "Furniture entries with block_strength are treated as present obstacles during simulation.",
        "Snapshot outdoor temperature is interpolated from daily min/max weather_reference; outdoor humidity comes from the top-level weekly environment.",
        "Sleep snapshots use a time-segmented illuminance target, defaulting to 0 lux with a 5 lux tolerance.",
    ]

    output_path = output_dir / "weekly_simulation_summary.json"
    export_json(str(output_path), summary)

    if representative is not None and args.export_representative:
        snapshot_id, result, devices = representative
        export_field_csv(str(output_dir / f"{snapshot_id}_estimated_field.csv"), result.field)
        middle_slice = result.field.resolution.nz // 2
        for metric in METRICS:
            export_svg_heatmap(
                str(figure_dir / f"{snapshot_id}_{metric}_slice.svg"),
                result.field,
                metric,
                middle_slice,
                f"{snapshot_id} - {metric} middle slice",
            )
            export_svg_volume_heatmap(
                str(figure_dir / f"{snapshot_id}_{metric}_3d.svg"),
                result.field,
                metric,
                f"{snapshot_id} - {metric} 3D field",
                devices=devices,
            )

    print(f"Wrote {output_path}")
    if representative is not None and args.export_representative:
        print(f"Wrote representative field and figures for {representative[0]}")
    aggregate = summary["aggregate"]
    print("Aggregate estimated pillow MAE:", aggregate["estimated_pillow_mae"])
    print("Aggregate calibrated sensor MAE:", aggregate["estimated_sensor_mae"])


def run_weekly_simulation(
    room_design: Dict,
    weekly_data: Dict,
    bundle: Dict[str, object],
    elapsed_minutes: float,
    sleep_illuminance_target: float = 0.0,
    sleep_illuminance_tolerance: float = 5.0,
) -> Tuple[Dict, Optional[Tuple[str, object, List[Device]]]]:
    model = DigitalTwinModel()
    rows: List[Dict[str, object]] = []
    representative: Optional[Tuple[str, object, List[Device]]] = None
    representative_penalty = -1.0

    weekly_days = weekly_data.get("weekly_simulation", [])
    sensor_days_by_date = {
        item.get("date"): item
        for item in weekly_data.get("weekly_sensor_snapshots", [])
        if isinstance(item, dict)
    }

    for day in weekly_days:
        date = str(day.get("date", "unknown_date"))
        sensor_day = sensor_days_by_date.get(date, {})
        for snapshot_key in SNAPSHOT_ORDER:
            snapshot = day.get("daily_snapshots", {}).get(snapshot_key, {})
            sensor_readings = sensor_day.get("snapshots", {}).get(snapshot_key, [])
            if not snapshot or not sensor_readings:
                continue

            observed_sensors = _observed_sensors(sensor_readings)
            devices = _devices_for_snapshot(
                deepcopy(bundle["devices"]),
                snapshot,
            )
            environment = _environment_for_snapshot(weekly_data, day, snapshot_key)
            snapshot_elapsed = _elapsed_minutes(day.get("occupancy_pattern", {}), snapshot_key, elapsed_minutes)

            raw_result = model.simulate(
                room=bundle["room"],
                environment=environment,
                devices=devices,
                furniture=bundle["furniture"],
                sensors=bundle["sensors"],
                zones=bundle["zones"],
                elapsed_minutes=snapshot_elapsed,
                resolution=bundle["resolution"],
            )
            estimated_result = model.simulate(
                room=bundle["room"],
                environment=environment,
                devices=devices,
                furniture=bundle["furniture"],
                sensors=bundle["sensors"],
                zones=bundle["zones"],
                elapsed_minutes=snapshot_elapsed,
                resolution=bundle["resolution"],
                observed_sensors=observed_sensors,
            )

            pillow_observed = _pillow_observation(snapshot)
            raw_pillow = model.sample_point(
                point=bundle["comfort_position"],
                room=bundle["room"],
                environment=environment,
                devices=devices,
                furniture=bundle["furniture"],
                elapsed_minutes=snapshot_elapsed,
            )
            estimated_pillow = model.sample_point(
                point=bundle["comfort_position"],
                room=bundle["room"],
                environment=environment,
                devices=estimated_result.calibrated_devices,
                furniture=bundle["furniture"],
                elapsed_minutes=snapshot_elapsed,
                corrections=estimated_result.corrections,
            )
            comfort_target = _comfort_target_for_snapshot(
                bundle["comfort_target"],
                snapshot_key,
                sleep_illuminance_target=sleep_illuminance_target,
                sleep_illuminance_tolerance=sleep_illuminance_tolerance,
            )
            row = {
                "snapshot_id": f"{date}_{snapshot_key}",
                "date": date,
                "day": day.get("day"),
                "snapshot": snapshot_key,
                "snapshot_time": SNAPSHOT_TIME[snapshot_key],
                "time_segment": _time_segment(snapshot_key),
                "comfort_target": _comfort_target_dict(comfort_target),
                "elapsed_minutes": round(snapshot_elapsed, 4),
                "environment": _environment_dict(environment),
                "activations": {
                    "ac": round(float(snapshot.get("ac_activation", 0.0)), 4),
                    "window": round(float(snapshot.get("window_activation", 0.0)), 4),
                    "main_light": round(float(snapshot.get("main_light_activation", 0.0)), 4),
                    "desk_light": round(float(snapshot.get("desk_light_activation", 0.0)), 4),
                },
                "observed_pillow": _round_metrics(pillow_observed),
                "raw_pillow": _round_metrics(raw_pillow),
                "estimated_pillow": _round_metrics(estimated_pillow),
                "raw_pillow_abs_error": _metric_abs_error(raw_pillow, pillow_observed),
                "estimated_pillow_abs_error": _metric_abs_error(estimated_pillow, pillow_observed),
                "raw_sensor_mae": compare_sensors(raw_result.sensor_predictions, observed_sensors),
                "estimated_sensor_mae": compare_sensors(estimated_result.sensor_predictions, observed_sensors),
                "estimated_zone_averages": _round_zone_averages(estimated_result.zone_averages),
                "estimated_field_ranges": _field_ranges(estimated_result.field),
                "estimated_comfort_penalty": round(
                    _comfort_penalty(estimated_pillow, comfort_target),
                    4,
                ),
                "calibrated_devices": _calibrated_device_summary(estimated_result.calibrated_devices),
            }
            rows.append(row)

            penalty = float(row["estimated_comfort_penalty"])
            if representative is None or penalty > representative_penalty:
                representative_penalty = penalty
                representative = (str(row["snapshot_id"]), estimated_result, estimated_result.calibrated_devices)

    summary = {
        "room": _room_dict(bundle["room"]),
        "grid_resolution": _resolution_dict(bundle["resolution"]),
        "snapshot_count": len(rows),
        "aggregate": _aggregate(rows),
        "worst_snapshots": {
            "by_estimated_comfort_penalty": _top_rows(rows, "estimated_comfort_penalty"),
            "by_estimated_pillow_mae_total": _top_rows(rows, "estimated_pillow_mae_total"),
        },
        "snapshots": rows,
    }
    return summary, representative


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bedroom_01 weekly digital-twin simulation.")
    parser.add_argument("--room-design", default=str(DEFAULT_ROOM_DESIGN))
    parser.add_argument("--weekly-data", default=str(DEFAULT_WEEKLY_DATA))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--figure-dir", default=str(DEFAULT_FIGURE_DIR))
    parser.add_argument(
        "--elapsed-minutes",
        type=float,
        default=18.0,
        help="Fallback elapsed minutes when a snapshot has active devices but the schedule cannot infer elapsed time.",
    )
    parser.add_argument(
        "--simulation-resolution",
        default=DEFAULT_SIMULATION_RESOLUTION,
        help="Simulation grid as NxNyNz, for example 12x12x6. Use 'design' to keep the room-design grid.",
    )
    parser.add_argument(
        "--sleep-illuminance-target",
        type=float,
        default=0.0,
        help="Illuminance comfort target for sleep snapshots.",
    )
    parser.add_argument(
        "--sleep-illuminance-tolerance",
        type=float,
        default=5.0,
        help="Illuminance tolerance for sleep snapshots.",
    )
    parser.add_argument(
        "--no-representative",
        dest="export_representative",
        action="store_false",
        help="Skip representative field CSV and SVG figure export.",
    )
    parser.set_defaults(export_representative=True)
    return parser.parse_args()


def _resolve_simulation_resolution(value: str, design_resolution: GridResolution) -> GridResolution:
    if value.lower() == "design":
        return design_resolution
    try:
        nx, ny, nz = (int(item) for item in value.lower().split("x"))
    except ValueError as exc:
        raise SystemExit("--simulation-resolution must look like 12x12x6 or be 'design'.") from exc
    if nx <= 1 or ny <= 1 or nz <= 1:
        raise SystemExit("--simulation-resolution dimensions must be greater than 1.")
    return GridResolution(nx=nx, ny=ny, nz=nz)


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_room_bundle(payload: Dict) -> Dict[str, object]:
    room_payload = payload["room"]
    room = Room(
        name=str(room_payload["name"]),
        width=float(room_payload["width_m"]),
        length=float(room_payload["length_m"]),
        height=float(room_payload["height_m"]),
        base_temperature=float(room_payload["base_temperature_c"]),
        base_humidity=float(room_payload["base_humidity_pct"]),
        base_illuminance=float(room_payload["base_illuminance_lux"]),
    )
    resolution_payload = payload["grid_resolution"]
    resolution = GridResolution(
        nx=int(resolution_payload["nx"]),
        ny=int(resolution_payload["ny"]),
        nz=int(resolution_payload["nz"]),
    )
    sensors = [
        Sensor(name=str(item["name"]), position=_vector(item["position"]))
        for item in payload.get("sensors", [])
    ]
    zones = [
        Zone(
            name=str(item["name"]),
            min_corner=_vector(item["min_corner"]),
            max_corner=_vector(item["max_corner"]),
        )
        for item in payload.get("zones", [])
    ]
    devices = [_device_from_design(item) for item in payload.get("devices", [])]
    furniture = [_furniture_from_design(item) for item in payload.get("furniture", [])]
    comfort_payload = payload["comfort_target"]
    comfort_target = ComfortTarget(
        temperature=float(comfort_payload["temperature_c"]),
        temperature_tolerance=float(comfort_payload.get("temperature_tolerance_c", 1.0)),
        humidity=float(comfort_payload["humidity_pct"]),
        humidity_tolerance=float(comfort_payload.get("humidity_tolerance_pct", 6.0)),
        illuminance=float(comfort_payload["illuminance_lux"]),
        illuminance_tolerance=float(comfort_payload.get("illuminance_tolerance_lux", 60.0)),
    )
    return {
        "room": room,
        "resolution": resolution,
        "sensors": sensors,
        "zones": zones,
        "devices": devices,
        "furniture": furniture,
        "comfort_position": _vector(comfort_payload["position"]),
        "comfort_target": comfort_target,
    }


def _device_from_design(payload: Dict) -> Device:
    metadata = dict(payload.get("metadata") or {})
    if "target_temperature_c" in metadata and "target_temperature" not in metadata:
        metadata["target_temperature"] = metadata["target_temperature_c"]
    influence_radius = payload.get("influence_radius_m", payload.get("influence_radius"))
    return build_device(
        name=str(payload["name"]),
        kind=str(payload["kind"]),
        position=_vector(payload["position"]),
        orientation=_vector(payload["orientation"]),
        influence_radius=float(influence_radius) if influence_radius is not None else None,
        power=float(payload.get("power", 1.0)),
        activation=float(payload.get("activation", 0.0)),
        response_time_minutes=float(payload["response_time_minutes"])
        if "response_time_minutes" in payload
        else None,
        metadata=metadata,
    )


def _furniture_from_design(payload: Dict) -> Furniture:
    metadata = dict(payload.get("metadata") or {})
    block_strength = float(metadata.get("block_strength", payload.get("block_strength", 0.3)))
    metadata["block_strength"] = block_strength
    metadata.setdefault("window_block", block_strength)
    metadata.setdefault("light_block", min(0.98, block_strength * 1.05))
    metadata.setdefault("ac_block", max(0.05, block_strength * 0.9))
    metadata.setdefault("mixing_penalty", min(0.16, max(0.01, block_strength * 0.12)))
    metadata.setdefault("kind", str(payload.get("kind", "furniture")))
    return Furniture(
        name=str(payload["name"]),
        kind=str(payload.get("kind", "furniture")),
        min_corner=_vector(payload["min_corner"]),
        max_corner=_vector(payload["max_corner"]),
        activation=1.0,
        metadata=metadata,
    )


def _devices_for_snapshot(devices: List[Device], snapshot: Dict) -> List[Device]:
    activation_by_name = {
        "wall_ac": snapshot.get("ac_activation", 0.0),
        "south_window": snapshot.get("window_activation", 0.0),
        "main_ceiling_light": snapshot.get("main_light_activation", 0.0),
        "desk_lamp": snapshot.get("desk_light_activation", 0.0),
    }
    fallback_by_kind = {
        "ac": snapshot.get("ac_activation", 0.0),
        "window": snapshot.get("window_activation", 0.0),
    }
    for device in devices:
        if device.name in activation_by_name:
            device.activation = float(activation_by_name[device.name])
        elif device.kind in fallback_by_kind:
            device.activation = float(fallback_by_kind[device.kind])
    return devices


def _environment_for_snapshot(weekly_data: Dict, day: Dict, snapshot_key: str) -> Environment:
    weekly_environment = weekly_data.get("environment", {})
    weather = day.get("weather_reference", {})
    fallback_temp = float(weekly_environment.get("outdoor_temperature_c", 25.0))
    outdoor_min = float(weather.get("outdoor_min_c", fallback_temp))
    outdoor_max = float(weather.get("outdoor_max_c", fallback_temp))
    fraction = SNAPSHOT_TEMPERATURE_FRACTION[snapshot_key]
    outdoor_temperature = outdoor_min + (outdoor_max - outdoor_min) * fraction
    sunlight_fraction = SNAPSHOT_SUNLIGHT_FRACTION[snapshot_key]
    return Environment(
        outdoor_temperature=outdoor_temperature,
        outdoor_humidity=float(weekly_environment.get("outdoor_humidity_pct", 70.0)),
        sunlight_illuminance=float(weekly_environment.get("sunlight_illuminance_lux", 0.0))
        * sunlight_fraction,
        daylight_factor=float(weekly_environment.get("daylight_factor", 1.0)),
    )


def _time_segment(snapshot_key: str) -> str:
    if snapshot_key == "morning_09_00":
        return "morning"
    if snapshot_key == "afternoon_15_00":
        return "afternoon"
    if snapshot_key == "night_22_00":
        return "night"
    if snapshot_key == "sleep_02_00":
        return "sleep"
    return "custom"


def _comfort_target_for_snapshot(
    base_target: ComfortTarget,
    snapshot_key: str,
    sleep_illuminance_target: float,
    sleep_illuminance_tolerance: float,
) -> ComfortTarget:
    if snapshot_key != "sleep_02_00":
        return base_target
    return ComfortTarget(
        temperature=base_target.temperature,
        temperature_tolerance=base_target.temperature_tolerance,
        humidity=base_target.humidity,
        humidity_tolerance=base_target.humidity_tolerance,
        illuminance=max(0.0, float(sleep_illuminance_target)),
        illuminance_tolerance=max(0.1, float(sleep_illuminance_tolerance)),
        temperature_weight=base_target.temperature_weight,
        humidity_weight=base_target.humidity_weight,
        illuminance_weight=base_target.illuminance_weight,
    )


def _comfort_target_dict(target: ComfortTarget) -> Dict[str, float]:
    return {
        "temperature": round(target.temperature, 4),
        "temperature_tolerance": round(target.temperature_tolerance, 4),
        "humidity": round(target.humidity, 4),
        "humidity_tolerance": round(target.humidity_tolerance, 4),
        "illuminance": round(target.illuminance, 4),
        "illuminance_tolerance": round(target.illuminance_tolerance, 4),
        "temperature_weight": round(target.temperature_weight, 4),
        "humidity_weight": round(target.humidity_weight, 4),
        "illuminance_weight": round(target.illuminance_weight, 4),
    }


def _observed_sensors(readings: List[Dict]) -> Dict[str, Dict[str, float]]:
    return {
        str(item["name"]): {
            "temperature": float(item["temperature_c"]),
            "humidity": float(item["humidity_pct"]),
            "illuminance": float(item["illuminance_lux"]),
        }
        for item in readings
    }


def _pillow_observation(snapshot: Dict) -> Dict[str, float]:
    pillow = snapshot["pillow_position"]
    return {
        "temperature": float(pillow["temperature_c"]),
        "humidity": float(pillow["humidity_pct"]),
        "illuminance": float(pillow["illuminance_lux"]),
    }


def _elapsed_minutes(occupancy: Dict, snapshot_key: str, fallback: float) -> float:
    elapsed_values: List[float] = []
    snapshot_minutes = _to_minutes(SNAPSHOT_TIME[snapshot_key])
    for period_key in ("window_open_period", "main_light_on_period", "desk_light_on_period", "ac_on_period"):
        period = occupancy.get(period_key)
        if not isinstance(period, dict):
            continue
        start = period.get("start")
        end = period.get("end")
        if not start or not end or not _time_in_period(snapshot_minutes, _to_minutes(start), _to_minutes(end)):
            continue
        elapsed_values.append(_minutes_since_start(snapshot_minutes, _to_minutes(start)))
    if not elapsed_values:
        return max(0.0, float(fallback))
    return max(0.0, min(elapsed_values))


def _to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _time_in_period(value: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= value <= end
    return value >= start or value <= end


def _minutes_since_start(value: int, start: int) -> float:
    if value >= start:
        return float(value - start)
    return float(value + 24 * 60 - start)


def _vector(payload: Dict) -> Vector3:
    return Vector3(
        x=float(payload["x"]),
        y=float(payload["y"]),
        z=float(payload["z"]),
    )


def _room_dict(room: Room) -> Dict[str, float]:
    return {
        "name": room.name,
        "width": room.width,
        "length": room.length,
        "height": room.height,
        "base_temperature": room.base_temperature,
        "base_humidity": room.base_humidity,
        "base_illuminance": room.base_illuminance,
    }


def _resolution_dict(resolution: GridResolution) -> Dict[str, int]:
    return {"nx": resolution.nx, "ny": resolution.ny, "nz": resolution.nz}


def _environment_dict(environment: Environment) -> Dict[str, float]:
    return {
        "outdoor_temperature": round(environment.outdoor_temperature, 4),
        "outdoor_humidity": round(environment.outdoor_humidity, 4),
        "sunlight_illuminance": round(environment.sunlight_illuminance, 4),
        "daylight_factor": round(environment.daylight_factor, 4),
    }


def _round_metrics(values: Dict[str, float]) -> Dict[str, float]:
    return {metric: round(float(values[metric]), 4) for metric in METRICS}


def _metric_abs_error(estimated: Dict[str, float], observed: Dict[str, float]) -> Dict[str, float]:
    return {
        metric: round(abs(float(estimated[metric]) - float(observed[metric])), 4)
        for metric in METRICS
    }


def _round_zone_averages(values: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    return {name: _round_metrics(metrics) for name, metrics in values.items()}


def _field_ranges(field: FieldGrid) -> Dict[str, Dict[str, float]]:
    ranges: Dict[str, Dict[str, float]] = {}
    for metric in METRICS:
        values = field.values[metric]
        ranges[metric] = {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(sum(values) / float(len(values)), 4),
        }
    return ranges


def _comfort_penalty(values: Dict[str, float], target: ComfortTarget) -> float:
    temperature = _normalized_overage(values["temperature"], target.temperature, target.temperature_tolerance)
    humidity = _normalized_overage(values["humidity"], target.humidity, target.humidity_tolerance)
    illuminance = _normalized_overage(values["illuminance"], target.illuminance, target.illuminance_tolerance)
    return (
        target.temperature_weight * temperature
        + target.humidity_weight * humidity
        + target.illuminance_weight * illuminance
    )


def _normalized_overage(value: float, target: float, tolerance: float) -> float:
    tolerance = max(float(tolerance), 1e-9)
    return max(0.0, abs(float(value) - float(target)) - tolerance) / tolerance


def _calibrated_device_summary(devices: List[Device]) -> List[Dict[str, object]]:
    return [
        {
            "name": device.name,
            "kind": device.kind,
            "activation": round(device.activation, 4),
            "power": round(device.power, 4),
            "calibrated_power_scale": round(float(device.metadata.get("calibrated_power_scale", 1.0)), 4),
        }
        for device in devices
    ]


def _aggregate(rows: List[Dict[str, object]]) -> Dict[str, object]:
    if not rows:
        return {}

    for row in rows:
        row["estimated_pillow_mae_total"] = round(
            sum(float(row["estimated_pillow_abs_error"][metric]) for metric in METRICS),
            4,
        )

    return {
        "snapshot_count": len(rows),
        "raw_pillow_mae": _mean_metric_error(rows, "raw_pillow_abs_error"),
        "estimated_pillow_mae": _mean_metric_error(rows, "estimated_pillow_abs_error"),
        "raw_sensor_mae": _mean_metric_error(rows, "raw_sensor_mae"),
        "estimated_sensor_mae": _mean_metric_error(rows, "estimated_sensor_mae"),
        "mean_estimated_comfort_penalty": round(
            sum(float(row["estimated_comfort_penalty"]) for row in rows) / float(len(rows)),
            4,
        ),
        "by_time_segment": _aggregate_by_time_segment(rows),
    }


def _aggregate_by_time_segment(rows: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    output: Dict[str, Dict[str, object]] = {}
    for segment in ("morning", "afternoon", "night", "sleep"):
        segment_rows = [row for row in rows if row.get("time_segment") == segment]
        if not segment_rows:
            continue
        output[segment] = {
            "snapshot_count": len(segment_rows),
            "estimated_pillow_mae": _mean_metric_error(segment_rows, "estimated_pillow_abs_error"),
            "mean_estimated_comfort_penalty": round(
                sum(float(row["estimated_comfort_penalty"]) for row in segment_rows)
                / float(len(segment_rows)),
                4,
            ),
        }
    return output


def _mean_metric_error(rows: List[Dict[str, object]], key: str) -> Dict[str, float]:
    return {
        metric: round(
            sum(float(row[key][metric]) for row in rows) / float(len(rows)),
            4,
        )
        for metric in METRICS
    }


def _top_rows(rows: List[Dict[str, object]], key: str, limit: int = 5) -> List[Dict[str, object]]:
    return [
        {
            "snapshot_id": row["snapshot_id"],
            "time_segment": row["time_segment"],
            key: row[key],
            "comfort_target": row["comfort_target"],
            "estimated_pillow": row["estimated_pillow"],
            "observed_pillow": row["observed_pillow"],
            "estimated_pillow_abs_error": row["estimated_pillow_abs_error"],
        }
        for row in sorted(rows, key=lambda item: float(item.get(key, 0.0)), reverse=True)[:limit]
    ]


if __name__ == "__main__":
    main()
