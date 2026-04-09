import os
from typing import Dict, List

from .entities import Sensor
from .model import DigitalTwinModel, FieldGrid, METRICS
from .recommendations import rank_actions
from .render import ensure_directory, export_field_csv, export_json, export_svg_heatmap
from .scenarios import apply_truth_adjustments, build_validation_scenarios


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

        recommendations = rank_actions(
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

        export_field_csv(os.path.join(output_dir, f"{scenario.name}_field.csv"), estimated_result.field)
        middle_slice = scenario.resolution.nz // 2
        export_svg_heatmap(
            os.path.join(output_dir, f"{scenario.name}_temperature.svg"),
            estimated_result.field,
            "temperature",
            middle_slice,
            f"{scenario.description} - Temperature",
        )
        export_svg_heatmap(
            os.path.join(output_dir, f"{scenario.name}_humidity.svg"),
            estimated_result.field,
            "humidity",
            middle_slice,
            f"{scenario.description} - Humidity",
        )
        export_svg_heatmap(
            os.path.join(output_dir, f"{scenario.name}_illuminance.svg"),
            estimated_result.field,
            "illuminance",
            middle_slice,
            f"{scenario.description} - Illuminance",
        )

        summary["scenarios"].append(
            {
                "name": scenario.name,
                "description": scenario.description,
                "field_mae": compare_fields(estimated_result.field, truth_result.field),
                "zone_mae": compare_zone_averages(estimated_result.zone_averages, truth_result.zone_averages),
                "sensor_mae_before": compare_sensors(raw_nominal.sensor_predictions, observed_sensors),
                "sensor_mae_after": compare_sensors(estimated_result.sensor_predictions, observed_sensors),
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
