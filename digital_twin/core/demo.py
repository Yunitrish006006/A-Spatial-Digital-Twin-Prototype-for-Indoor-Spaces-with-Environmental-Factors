import os
from copy import deepcopy
from typing import Dict, List

from digital_twin.core.entities import Sensor
from digital_twin.core.scenarios import apply_truth_adjustments, build_validation_scenarios
from digital_twin.physics.baselines import build_idw_field, compute_zone_averages as compute_idw_zone_averages
from digital_twin.physics.learning import learn_active_device_impacts_from_observations
from digital_twin.physics.model import DigitalTwinModel, FieldGrid, METRICS
from digital_twin.physics.recommendations import rank_actions
from digital_twin.web.render import ensure_directory, export_field_csv, export_json, export_svg_heatmap, export_svg_volume_heatmap


def run_validation_suite(output_dir: str = "outputs") -> Dict:
    ensure_directory(output_dir)
    model = DigitalTwinModel()
    scenarios = build_validation_scenarios()
    summary = {"scenarios": []}

    for scenario in scenarios:
        truth_devices = apply_truth_adjustments(scenario.devices, scenario.truth_adjustments)
        truth_result = model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=truth_devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
        )
        observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)

        raw_nominal = model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
        )
        before_learning_devices = deactivate_devices(scenario.devices)
        before_learning_result = model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=before_learning_devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
        )
        before_learning_observations = synthesize_sensor_observations(
            before_learning_result.sensor_predictions,
            scenario.sensors,
        )
        estimated_result = model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
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
        learned_impacts = learn_active_device_impacts(
            model=model,
            room=scenario.room,
            scenario_devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            before_observations=before_learning_observations,
            after_observations=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        )

        recommendations = rank_actions(
            model=model,
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            target_zone_name=scenario.target_zone_name,
            target=scenario.comfort_target,
            actions=scenario.candidate_actions,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
            observed_sensors=observed_sensors,
        )

        export_field_csv(os.path.join(output_dir, f"{scenario.name}_field.csv"), estimated_result.field)
        middle_slice = scenario.resolution.nz // 2
        export_svg_heatmap(
            os.path.join(output_dir, f"{scenario.name}_temperature.svg"),
            estimated_result.field,
            "temperature",
            middle_slice,
            f"{scenario.description} - Temperature",
        )
        export_svg_volume_heatmap(
            os.path.join(output_dir, f"{scenario.name}_temperature_3d.svg"),
            estimated_result.field,
            "temperature",
            f"{scenario.description} - Temperature",
            devices=scenario.devices,
        )
        export_svg_heatmap(
            os.path.join(output_dir, f"{scenario.name}_humidity.svg"),
            estimated_result.field,
            "humidity",
            middle_slice,
            f"{scenario.description} - Humidity",
        )
        export_svg_volume_heatmap(
            os.path.join(output_dir, f"{scenario.name}_humidity_3d.svg"),
            estimated_result.field,
            "humidity",
            f"{scenario.description} - Humidity",
            devices=scenario.devices,
        )
        export_svg_heatmap(
            os.path.join(output_dir, f"{scenario.name}_illuminance.svg"),
            estimated_result.field,
            "illuminance",
            middle_slice,
            f"{scenario.description} - Illuminance",
        )
        export_svg_volume_heatmap(
            os.path.join(output_dir, f"{scenario.name}_illuminance_3d.svg"),
            estimated_result.field,
            "illuminance",
            f"{scenario.description} - Illuminance",
            devices=scenario.devices,
        )

        summary["scenarios"].append(
            {
                "name": scenario.name,
                "description": scenario.description,
                "field_mae": compare_fields(estimated_result.field, truth_result.field),
                "idw_field_mae": compare_fields(idw_field, truth_result.field),
                "idw_zone_mae": compare_zone_averages(idw_zone_averages, truth_result.zone_averages),
                "zone_mae": compare_zone_averages(estimated_result.zone_averages, truth_result.zone_averages),
                "sensor_mae_before": compare_sensors(raw_nominal.sensor_predictions, observed_sensors),
                "sensor_mae_after": compare_sensors(estimated_result.sensor_predictions, observed_sensors),
                "baseline_comparison": compare_model_to_idw(
                    model_mae=compare_fields(estimated_result.field, truth_result.field),
                    idw_mae=compare_fields(idw_field, truth_result.field),
                ),
                "learned_device_impacts": learned_impacts,
                "center_zone_estimated": estimated_result.zone_averages[scenario.target_zone_name],
                "center_zone_truth": truth_result.zone_averages[scenario.target_zone_name],
                "recommendations": [
                    {
                        "name": item.name,
                        "description": item.description,
                        "improvement": round(item.improvement, 4),
                        "resulting_zone_values": round_dict(item.resulting_zone_values),
                        "resulting_penalty": round(item.resulting_penalty, 4),
                    }
                    for item in recommendations
                ],
            }
        )

    export_json(os.path.join(output_dir, "validation_summary.json"), summary)
    return summary


def synthesize_sensor_observations(
    truth_predictions: Dict[str, Dict[str, float]], sensors: List[Sensor]
) -> Dict[str, Dict[str, float]]:
    observations: Dict[str, Dict[str, float]] = {}
    for index, sensor in enumerate(sensors):
        pattern = (index % 4) - 1.5
        observations[sensor.name] = {
            "temperature": truth_predictions[sensor.name]["temperature"] + 0.08 * pattern,
            "humidity": truth_predictions[sensor.name]["humidity"] + 0.3 * pattern,
            "illuminance": truth_predictions[sensor.name]["illuminance"] + 3.0 * pattern,
        }
    return observations


def learn_active_device_impacts(
    model: DigitalTwinModel,
    room,
    scenario_devices,
    furniture,
    sensors: List[Sensor],
    before_observations: Dict[str, Dict[str, float]],
    after_observations: Dict[str, Dict[str, float]],
    elapsed_minutes: float,
) -> List[Dict]:
    active_devices = [device for device in scenario_devices if device.activation > 0.0]
    learned = learn_active_device_impacts_from_observations(
        model=model,
        active_devices=active_devices,
        room=room,
        furniture=furniture,
        sensors=sensors,
        before_observations=before_observations,
        after_observations=after_observations,
        elapsed_minutes=elapsed_minutes,
    )
    return [
        {
            "device_name": impact.device_name,
            "metric_coefficients": round_dict(impact.metric_coefficients),
            "sensor_mae": round_dict(impact.sensor_mae),
            "sensor_observation_delta": round_dict(impact.sensor_observation_delta),
        }
        for impact in learned
    ]


def deactivate_devices(devices):
    deactivated = deepcopy(devices)
    for device in deactivated:
        device.activation = 0.0
    return deactivated


def compare_fields(estimated: FieldGrid, truth: FieldGrid) -> Dict[str, float]:
    return {
        metric: round(_mean_absolute_error(estimated.values[metric], truth.values[metric]), 4)
        for metric in METRICS
    }


def compare_zone_averages(
    estimated: Dict[str, Dict[str, float]], truth: Dict[str, Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    output: Dict[str, Dict[str, float]] = {}
    for zone_name, values in estimated.items():
        output[zone_name] = {}
        for metric in METRICS:
            output[zone_name][metric] = round(abs(values[metric] - truth[zone_name][metric]), 4)
    return output


def compare_sensors(
    estimated: Dict[str, Dict[str, float]], observed: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    output: Dict[str, float] = {}
    for metric in METRICS:
        values = []
        for sensor_name, metric_values in estimated.items():
            values.append(abs(metric_values[metric] - observed[sensor_name][metric]))
        output[metric] = round(sum(values) / float(len(values)), 4)
    return output


def round_dict(payload: Dict[str, float]) -> Dict[str, float]:
    return {key: round(value, 4) for key, value in payload.items()}


def compare_model_to_idw(model_mae: Dict[str, float], idw_mae: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    output: Dict[str, Dict[str, float]] = {}
    for metric in METRICS:
        improvement = idw_mae[metric] - model_mae[metric]
        percent = 0.0
        if idw_mae[metric] > 1e-9:
            percent = improvement / idw_mae[metric] * 100.0
        output[metric] = {
            "model_mae": round(model_mae[metric], 4),
            "idw_mae": round(idw_mae[metric], 4),
            "mae_reduction": round(improvement, 4),
            "mae_reduction_percent": round(percent, 2),
        }
    return output


def _mean_absolute_error(first: List[float], second: List[float]) -> float:
    if len(first) != len(second):
        raise ValueError("Field lengths must match.")
    return sum(abs(a - b) for a, b in zip(first, second)) / float(len(first))


def main() -> None:
    summary = run_validation_suite()
    print("Generated outputs in ./outputs")
    for scenario in summary["scenarios"]:
        best = scenario["recommendations"][0]
        print(
            f"- {scenario['name']}: best action={best['name']}, "
            f"field_mae={scenario['field_mae']}"
        )


if __name__ == "__main__":
    main()
