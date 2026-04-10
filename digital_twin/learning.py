from dataclasses import dataclass
from typing import Dict, List

from .entities import Device, Sensor
from .math_utils import solve_linear_system
from .model import DigitalTwinModel, METRICS


@dataclass(frozen=True)
class LearnedImpact:
    device_name: str
    metric_coefficients: Dict[str, float]
    sensor_mae: Dict[str, float]
    sensor_observation_delta: Dict[str, float]


def learn_device_impact_from_sensor_delta(
    model: DigitalTwinModel,
    device: Device,
    sensors: List[Sensor],
    before_observations: Dict[str, Dict[str, float]],
    after_observations: Dict[str, Dict[str, float]],
    elapsed_minutes: float,
) -> LearnedImpact:
    basis_by_sensor = {
        sensor.name: model.influence_envelope(device, sensor.position, elapsed_minutes)
        for sensor in sensors
    }
    metric_coefficients: Dict[str, float] = {}
    sensor_mae: Dict[str, float] = {}
    sensor_observation_delta: Dict[str, float] = {}

    for metric in METRICS:
        numerator = 0.0
        denominator = 0.0
        deltas: List[float] = []
        for sensor in sensors:
            if sensor.name not in before_observations or sensor.name not in after_observations:
                continue
            observed_delta = after_observations[sensor.name][metric] - before_observations[sensor.name][metric]
            basis = basis_by_sensor[sensor.name]
            numerator += basis * observed_delta
            denominator += basis * basis
            deltas.append(observed_delta)

        coefficient = numerator / denominator if denominator > 1e-9 else 0.0
        metric_coefficients[metric] = coefficient
        sensor_observation_delta[metric] = sum(deltas) / float(len(deltas)) if deltas else 0.0

        errors = []
        for sensor in sensors:
            if sensor.name not in before_observations or sensor.name not in after_observations:
                continue
            observed_delta = after_observations[sensor.name][metric] - before_observations[sensor.name][metric]
            predicted_delta = coefficient * basis_by_sensor[sensor.name]
            errors.append(abs(predicted_delta - observed_delta))
        sensor_mae[metric] = sum(errors) / float(len(errors)) if errors else 0.0

    return LearnedImpact(
        device_name=device.name,
        metric_coefficients=metric_coefficients,
        sensor_mae=sensor_mae,
        sensor_observation_delta=sensor_observation_delta,
    )


def learn_active_device_impacts_from_observations(
    model: DigitalTwinModel,
    active_devices: List[Device],
    sensors: List[Sensor],
    before_observations: Dict[str, Dict[str, float]],
    after_observations: Dict[str, Dict[str, float]],
    elapsed_minutes: float,
    ridge: float = 1e-6,
) -> List[LearnedImpact]:
    if not active_devices:
        return []

    basis_by_sensor = {
        sensor.name: [
            model.influence_envelope(device, sensor.position, elapsed_minutes)
            for device in active_devices
        ]
        for sensor in sensors
    }

    coefficients_by_metric: Dict[str, List[float]] = {}
    mae_by_metric: Dict[str, float] = {}
    mean_delta_by_metric: Dict[str, float] = {}

    for metric in METRICS:
        normal_matrix = [[0.0 for _ in active_devices] for _ in active_devices]
        normal_vector = [0.0 for _ in active_devices]
        observed_deltas: List[float] = []

        for sensor in sensors:
            if sensor.name not in before_observations or sensor.name not in after_observations:
                continue
            features = basis_by_sensor[sensor.name]
            observed_delta = after_observations[sensor.name][metric] - before_observations[sensor.name][metric]
            observed_deltas.append(observed_delta)
            for row in range(len(active_devices)):
                normal_vector[row] += features[row] * observed_delta
                for column in range(len(active_devices)):
                    normal_matrix[row][column] += features[row] * features[column]

        for index in range(len(active_devices)):
            normal_matrix[index][index] += ridge

        if observed_deltas:
            coefficients = solve_linear_system(normal_matrix, normal_vector)
        else:
            coefficients = [0.0 for _ in active_devices]
        coefficients_by_metric[metric] = coefficients
        mean_delta_by_metric[metric] = sum(observed_deltas) / float(len(observed_deltas)) if observed_deltas else 0.0

        errors = []
        for sensor in sensors:
            if sensor.name not in before_observations or sensor.name not in after_observations:
                continue
            features = basis_by_sensor[sensor.name]
            observed_delta = after_observations[sensor.name][metric] - before_observations[sensor.name][metric]
            predicted_delta = sum(features[index] * coefficients[index] for index in range(len(active_devices)))
            errors.append(abs(predicted_delta - observed_delta))
        mae_by_metric[metric] = sum(errors) / float(len(errors)) if errors else 0.0

    learned: List[LearnedImpact] = []
    for device_index, device in enumerate(active_devices):
        learned.append(
            LearnedImpact(
                device_name=device.name,
                metric_coefficients={
                    metric: coefficients_by_metric[metric][device_index]
                    for metric in METRICS
                },
                sensor_mae=dict(mae_by_metric),
                sensor_observation_delta=dict(mean_delta_by_metric),
            )
        )
    return learned


def summarize_device_truth_coefficients(device: Device) -> Dict[str, float]:
    if device.kind == "ac":
        return {
            "temperature": -device.metadata.get("cooling_delta", 8.0) * device.power,
            "humidity": -device.metadata.get("drying_delta", 4.0) * device.power,
            "illuminance": 0.0,
        }
    if device.kind == "window":
        return {
            "temperature": device.metadata.get("thermal_exchange", 0.28) * device.power,
            "humidity": device.metadata.get("humidity_exchange", 0.24) * device.power,
            "illuminance": device.metadata.get("solar_gain", 0.018) * device.power,
        }
    if device.kind == "light":
        return {
            "temperature": device.metadata.get("heat_gain", 0.9) * device.power,
            "humidity": 0.0,
            "illuminance": device.metadata.get("illuminance_gain", 950.0) * device.power,
        }
    return {metric: 0.0 for metric in METRICS}
