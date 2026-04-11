from dataclasses import replace
from typing import Dict, List, Optional
from copy import deepcopy

from .baselines import build_idw_field, compute_zone_averages as compute_idw_zone_averages
from .demo import (
    compare_fields,
    compare_model_to_idw,
    compare_sensors,
    compare_zone_averages,
    learn_active_device_impacts,
    synthesize_sensor_observations,
)
from .entities import Vector3
from .model import DigitalTwinModel
from .recommendations import rank_actions
from .scenarios import (
    SEASON_PROFILES,
    TIME_OF_DAY_PROFILES,
    WEATHER_PROFILES,
    WINDOW_SEASON_ORDER,
    WINDOW_TIME_ORDER,
    WINDOW_WEATHER_ORDER,
    Scenario,
    apply_truth_adjustments,
    build_direct_window_scenario,
    build_validation_scenarios,
    build_window_matrix_scenarios,
)


def list_scenario_metadata() -> List[Dict]:
    return [_scenario_metadata(scenario) for scenario in build_validation_scenarios()]


def list_window_scenario_metadata() -> List[Dict]:
    return [_scenario_metadata(scenario) for scenario in build_window_matrix_scenarios()]


def evaluate_scenario(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(_find_scenario(scenario_name), device_overrides, device_metadata_overrides)
    return _evaluate_scenario_object(scenario)


def evaluate_window_direct(
    outdoor_temperature: float,
    outdoor_humidity: float,
    sunlight_illuminance: float,
    opening_ratio: float = 0.7,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: float = 70.0,
    daylight_factor: float = 0.95,
    elapsed_minutes: float = 18.0,
) -> Dict:
    scenario = build_direct_window_scenario(
        outdoor_temperature=outdoor_temperature,
        outdoor_humidity=outdoor_humidity,
        sunlight_illuminance=sunlight_illuminance,
        opening_ratio=opening_ratio,
        indoor_temperature=indoor_temperature,
        indoor_humidity=indoor_humidity,
        base_illuminance=base_illuminance,
        daylight_factor=daylight_factor,
        elapsed_minutes=elapsed_minutes,
    )
    result = _evaluate_scenario_object(scenario)
    result["input"] = {
        "mode": "direct",
        "opening_ratio": round(max(0.0, min(1.0, float(opening_ratio))), 4),
        "indoor_temperature": scenario.room.base_temperature,
        "indoor_humidity": scenario.room.base_humidity,
        "base_illuminance": scenario.room.base_illuminance,
        "elapsed_minutes": scenario.elapsed_minutes,
    }
    return result


def _evaluate_scenario_object(scenario: Scenario) -> Dict:
    model = DigitalTwinModel()
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    raw_nominal = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )
    before_devices = deepcopy(scenario.devices)
    for device in before_devices:
        device.activation = 0.0
    before_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=before_devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )
    before_observations = synthesize_sensor_observations(before_result.sensor_predictions, scenario.sensors)
    estimated_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
        observed_sensors=observed_sensors,
    )
    idw_field = build_idw_field(
        room=scenario.room,
        sensors=scenario.sensors,
        observed_sensors=observed_sensors,
        resolution=scenario.resolution,
    )
    idw_zone_averages = compute_idw_zone_averages(idw_field, scenario.zones)
    field_mae = compare_fields(estimated_result.field, truth_result.field)
    idw_field_mae = compare_fields(idw_field, truth_result.field)
    return {
        "name": scenario.name,
        "description": scenario.description,
        "metadata": scenario.metadata,
        "environment": {
            "outdoor_temperature": scenario.environment.outdoor_temperature,
            "outdoor_humidity": scenario.environment.outdoor_humidity,
            "sunlight_illuminance": scenario.environment.sunlight_illuminance,
            "daylight_factor": scenario.environment.daylight_factor,
        },
        "field_mae": field_mae,
        "idw_field_mae": idw_field_mae,
        "idw_zone_mae": compare_zone_averages(idw_zone_averages, truth_result.zone_averages),
        "baseline_comparison": compare_model_to_idw(field_mae, idw_field_mae),
        "zone_mae": compare_zone_averages(estimated_result.zone_averages, truth_result.zone_averages),
        "sensor_mae_before": compare_sensors(raw_nominal.sensor_predictions, observed_sensors),
        "sensor_mae_after": compare_sensors(estimated_result.sensor_predictions, observed_sensors),
        "device_power_calibration": _device_power_calibration(estimated_result.calibrated_devices),
        "learned_device_impacts": learn_active_device_impacts(
            model=model,
            scenario_devices=scenario.devices,
            sensors=scenario.sensors,
            before_observations=before_observations,
            after_observations=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        ),
        "target_zone": scenario.target_zone_name,
        "target_zone_estimated": _round_metric_dict(estimated_result.zone_averages[scenario.target_zone_name]),
        "target_zone_truth": _round_metric_dict(truth_result.zone_averages[scenario.target_zone_name]),
        "zone_estimated": _round_zone_dict(estimated_result.zone_averages),
        "zone_truth": _round_zone_dict(truth_result.zone_averages),
        "corrections": {
            metric: {
                "model": "trilinear",
                "bias": round(correction.bias, 6),
                "x": round(correction.x, 6),
                "y": round(correction.y, 6),
                "z": round(correction.z, 6),
                "xy": round(correction.xy, 6),
                "xz": round(correction.xz, 6),
                "yz": round(correction.yz, 6),
                "xyz": round(correction.xyz, 6),
            }
            for metric, correction in estimated_result.corrections.items()
        },
    }


def evaluate_window_matrix() -> Dict:
    scenarios = build_window_matrix_scenarios()
    rows: List[Dict] = []
    for scenario in scenarios:
        result = evaluate_scenario(scenario.name)
        rows.append(
            {
                "name": result["name"],
                "description": result["description"],
                "metadata": result["metadata"],
                "environment": result["environment"],
                "target_zone": result["target_zone"],
                "target_zone_estimated": result["target_zone_estimated"],
                "window_zone_estimated": result["zone_estimated"]["window_zone"],
                "center_zone_estimated": result["zone_estimated"]["center_zone"],
                "door_side_zone_estimated": result["zone_estimated"]["door_side_zone"],
                "field_mae": result["field_mae"],
                "baseline_comparison": result["baseline_comparison"],
            }
        )

    return {
        "count": len(rows),
        "dimensions": {
            "seasons": _dimension_items(WINDOW_SEASON_ORDER, SEASON_PROFILES),
            "weathers": _dimension_items(WINDOW_WEATHER_ORDER, WEATHER_PROFILES),
            "times_of_day": _dimension_items(WINDOW_TIME_ORDER, TIME_OF_DAY_PROFILES),
        },
        "scenarios": rows,
    }


def get_scenario_volume(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict:
    model = DigitalTwinModel()
    scenario = _scenario_with_overrides(_find_scenario(scenario_name), device_overrides, device_metadata_overrides)
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    estimated_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
        observed_sensors=observed_sensors,
    )
    field = estimated_result.field
    points = []
    for iz in range(field.resolution.nz):
        for iy in range(field.resolution.ny):
            for ix in range(field.resolution.nx):
                point = field.point(ix, iy, iz)
                index = field.index(ix, iy, iz)
                points.append(
                    {
                        "x": round(point.x, 4),
                        "y": round(point.y, 4),
                        "z": round(point.z, 4),
                        "temperature": round(field.values["temperature"][index], 4),
                        "humidity": round(field.values["humidity"][index], 4),
                        "illuminance": round(field.values["illuminance"][index], 4),
                    }
                )

    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "room": {
            "width": scenario.room.width,
            "length": scenario.room.length,
            "height": scenario.room.height,
        },
        "resolution": {
            "nx": scenario.resolution.nx,
            "ny": scenario.resolution.ny,
            "nz": scenario.resolution.nz,
        },
        "devices": [
            {
                "name": device.name,
                "kind": device.kind,
                "activation": round(device.activation, 4),
                "power": round(device.power, 4),
                "calibrated_power_scale": round(float(device.metadata.get("calibrated_power_scale", 1.0)), 4),
                "position": _vector_to_dict(device.position),
                "geometry": _device_geometry(device),
                "metadata": _device_metadata(device),
            }
            for device in estimated_result.calibrated_devices
        ],
        "points": points,
    }


def rank_scenario_actions(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict:
    model = DigitalTwinModel()
    scenario = _scenario_with_overrides(_find_scenario(scenario_name), device_overrides, device_metadata_overrides)
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    ranked = rank_actions(
        model=model,
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        target_zone_name=scenario.target_zone_name,
        target=scenario.comfort_target,
        actions=scenario.candidate_actions,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
        observed_sensors=observed_sensors,
    )
    return {
        "scenario": scenario.name,
        "target_zone": scenario.target_zone_name,
        "recommendations": [
            {
                "name": item.name,
                "description": item.description,
                "improvement": round(item.improvement, 4),
                "resulting_penalty": round(item.resulting_penalty, 4),
                "resulting_zone_values": _round_metric_dict(item.resulting_zone_values),
            }
            for item in ranked
        ],
    }


def sample_scenario_point(
    scenario_name: str,
    x: float,
    y: float,
    z: float,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict:
    model = DigitalTwinModel()
    scenario = _scenario_with_overrides(_find_scenario(scenario_name), device_overrides, device_metadata_overrides)
    point = Vector3(x=x, y=y, z=z)
    _validate_point(scenario, point)
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    estimated_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
        observed_sensors=observed_sensors,
    )
    values = model.sample_point(
        point=point,
        room=scenario.room,
        environment=scenario.environment,
        devices=estimated_result.calibrated_devices,
        elapsed_minutes=scenario.elapsed_minutes,
        corrections=estimated_result.corrections,
    )
    return {
        "scenario": scenario.name,
        "point": _vector_to_dict(point),
        "values": _round_metric_dict(values),
    }


def compare_scenario_baseline(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict:
    model = DigitalTwinModel()
    scenario = _scenario_with_overrides(_find_scenario(scenario_name), device_overrides, device_metadata_overrides)
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    estimated_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
        observed_sensors=observed_sensors,
    )
    idw_field = build_idw_field(
        room=scenario.room,
        sensors=scenario.sensors,
        observed_sensors=observed_sensors,
        resolution=scenario.resolution,
    )
    model_mae = compare_fields(estimated_result.field, truth_result.field)
    idw_mae = compare_fields(idw_field, truth_result.field)
    return {
        "scenario": scenario.name,
        "model": "trilinear-corrected appliance influence field",
        "baseline": "inverse distance weighting",
        "comparison": compare_model_to_idw(model_mae, idw_mae),
    }


def learn_scenario_impacts(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
) -> Dict:
    model = DigitalTwinModel()
    scenario = _scenario_with_overrides(_find_scenario(scenario_name), device_overrides, device_metadata_overrides)
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    before_devices = deepcopy(scenario.devices)
    for device in before_devices:
        device.activation = 0.0
    before_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=before_devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )
    before_observations = synthesize_sensor_observations(before_result.sensor_predictions, scenario.sensors)
    return {
        "scenario": scenario.name,
        "description": "Learn active non-networked appliance impact coefficients from before/after sensor observations.",
        "learned_device_impacts": learn_active_device_impacts(
            model=model,
            scenario_devices=scenario.devices,
            sensors=scenario.sensors,
            before_observations=before_observations,
            after_observations=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        ),
    }


def _find_scenario(scenario_name: str) -> Scenario:
    scenarios = {scenario.name: scenario for scenario in _all_scenarios()}
    if scenario_name not in scenarios:
        available = ", ".join(sorted(scenarios))
        raise ValueError(f"Unknown scenario '{scenario_name}'. Available scenarios: {available}")
    return scenarios[scenario_name]


def _all_scenarios() -> List[Scenario]:
    return build_validation_scenarios() + build_window_matrix_scenarios()


def _scenario_with_overrides(
    scenario: Scenario,
    device_overrides: Optional[Dict[str, float]],
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]],
) -> Scenario:
    if not device_overrides and not device_metadata_overrides:
        return scenario
    devices = deepcopy(scenario.devices)
    for device in devices:
        if device_overrides and device.name in device_overrides:
            device.activation = max(0.0, min(1.0, float(device_overrides[device.name])))
        if device_metadata_overrides and device.name in device_metadata_overrides:
            device.metadata.update(deepcopy(device_metadata_overrides[device.name]))
    return replace(scenario, devices=devices)


def _scenario_metadata(scenario: Scenario) -> Dict:
    return {
        "name": scenario.name,
        "description": scenario.description,
        "target_zone": scenario.target_zone_name,
        "metadata": scenario.metadata,
        "devices": [
            {
                "name": device.name,
                "kind": device.kind,
                "activation": device.activation,
                "position": _vector_to_dict(device.position),
                "geometry": _device_geometry(device),
                "metadata": _device_metadata(device),
            }
            for device in scenario.devices
        ],
    }


def _device_geometry(device) -> Dict:
    if device.kind == "ac":
        return {
            "shape": "wall_bar",
            "plane": "x",
            "width": float(device.metadata.get("surface_width", 1.2)),
            "height": float(device.metadata.get("surface_height", 0.3)),
        }
    if device.kind == "window":
        return {
            "shape": "wall_rectangle",
            "plane": "x",
            "width": float(device.metadata.get("surface_width", 1.4)),
            "height": float(device.metadata.get("surface_height", 1.1)),
        }
    return {"shape": "point"}


def _device_power_calibration(devices) -> List[Dict]:
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


def _device_metadata(device) -> Dict[str, object]:
    metadata = deepcopy(device.metadata)
    metadata.pop("calibrated_power_scale", None)
    return metadata


def _dimension_items(keys, profiles) -> List[Dict]:
    return [{"name": key, "label": str(profiles[key]["zh"])} for key in keys]


def _simulate_truth(model: DigitalTwinModel, scenario: Scenario):
    truth_devices = apply_truth_adjustments(scenario.devices, scenario.truth_adjustments)
    return model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=truth_devices,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )


def _validate_point(scenario: Scenario, point: Vector3) -> None:
    if not (0.0 <= point.x <= scenario.room.width):
        raise ValueError(f"x must be between 0 and {scenario.room.width}.")
    if not (0.0 <= point.y <= scenario.room.length):
        raise ValueError(f"y must be between 0 and {scenario.room.length}.")
    if not (0.0 <= point.z <= scenario.room.height):
        raise ValueError(f"z must be between 0 and {scenario.room.height}.")


def _round_metric_dict(values: Dict[str, float]) -> Dict[str, float]:
    return {key: round(value, 4) for key, value in values.items()}


def _round_zone_dict(values: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    return {zone_name: _round_metric_dict(metrics) for zone_name, metrics in values.items()}


def _vector_to_dict(vector: Vector3) -> Dict[str, float]:
    return {"x": vector.x, "y": vector.y, "z": vector.z}
