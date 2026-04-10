from typing import Dict, List

from .demo import compare_fields, compare_sensors, compare_zone_averages, synthesize_sensor_observations
from .entities import Vector3
from .model import DigitalTwinModel
from .recommendations import rank_actions
from .scenarios import Scenario, apply_truth_adjustments, build_validation_scenarios


def list_scenario_metadata() -> List[Dict]:
    return [
        {
            "name": scenario.name,
            "description": scenario.description,
            "target_zone": scenario.target_zone_name,
            "devices": [
                {
                    "name": device.name,
                    "kind": device.kind,
                    "activation": device.activation,
                    "position": _vector_to_dict(device.position),
                }
                for device in scenario.devices
            ],
        }
        for scenario in build_validation_scenarios()
    ]


def evaluate_scenario(scenario_name: str) -> Dict:
    model = DigitalTwinModel()
    scenario = _find_scenario(scenario_name)
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
    return {
        "name": scenario.name,
        "description": scenario.description,
        "field_mae": compare_fields(estimated_result.field, truth_result.field),
        "zone_mae": compare_zone_averages(estimated_result.zone_averages, truth_result.zone_averages),
        "sensor_mae_before": compare_sensors(raw_nominal.sensor_predictions, observed_sensors),
        "sensor_mae_after": compare_sensors(estimated_result.sensor_predictions, observed_sensors),
        "target_zone": scenario.target_zone_name,
        "target_zone_estimated": _round_metric_dict(estimated_result.zone_averages[scenario.target_zone_name]),
        "target_zone_truth": _round_metric_dict(truth_result.zone_averages[scenario.target_zone_name]),
        "corrections": {
            metric: {
                "bias": round(correction.bias, 6),
                "x": round(correction.x, 6),
                "y": round(correction.y, 6),
                "z": round(correction.z, 6),
            }
            for metric, correction in estimated_result.corrections.items()
        },
    }


def rank_scenario_actions(scenario_name: str) -> Dict:
    model = DigitalTwinModel()
    scenario = _find_scenario(scenario_name)
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


def sample_scenario_point(scenario_name: str, x: float, y: float, z: float) -> Dict:
    model = DigitalTwinModel()
    scenario = _find_scenario(scenario_name)
    point = Vector3(x=x, y=y, z=z)
    _validate_point(scenario, point)
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    corrections = model.fit_corrections(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        sensors=scenario.sensors,
        observed_sensors=observed_sensors,
        elapsed_minutes=scenario.elapsed_minutes,
    )
    values = model.sample_point(
        point=point,
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        elapsed_minutes=scenario.elapsed_minutes,
        corrections=corrections,
    )
    return {
        "scenario": scenario.name,
        "point": _vector_to_dict(point),
        "values": _round_metric_dict(values),
    }


def _find_scenario(scenario_name: str) -> Scenario:
    scenarios = {scenario.name: scenario for scenario in build_validation_scenarios()}
    if scenario_name not in scenarios:
        available = ", ".join(sorted(scenarios))
        raise ValueError(f"Unknown scenario '{scenario_name}'. Available scenarios: {available}")
    return scenarios[scenario_name]


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


def _vector_to_dict(vector: Vector3) -> Dict[str, float]:
    return {"x": vector.x, "y": vector.y, "z": vector.z}
