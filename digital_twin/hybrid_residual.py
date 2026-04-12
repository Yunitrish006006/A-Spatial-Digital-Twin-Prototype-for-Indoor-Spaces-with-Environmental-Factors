import json
import math
import random
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .demo import compare_fields, compare_zone_averages, synthesize_sensor_observations
from .entities import Device, Vector3
from .math_utils import clamp
from .model import DigitalTwinModel, FieldGrid, METRICS
from .scenarios import Scenario, apply_truth_adjustments, build_validation_scenarios, build_window_matrix_scenarios


DEVICE_ORDER = ("ac_main", "window_main", "light_main")
AC_MODE_ORDER = ("cool", "dry", "heat", "fan")


@dataclass(frozen=True)
class ResidualDataset:
    feature_names: List[str]
    features: List[List[float]]
    targets: Dict[str, List[float]]
    scenario_names: List[str]


@dataclass(frozen=True)
class ScalarResidualNetwork:
    feature_names: List[str]
    input_means: List[float]
    input_scales: List[float]
    target_mean: float
    target_scale: float
    hidden_weights: List[List[float]]
    hidden_biases: List[float]
    output_weights: List[float]
    output_bias: float

    def predict(self, features: Sequence[float]) -> float:
        normalized = self._normalize_features(features)
        hidden = []
        for weights, bias in zip(self.hidden_weights, self.hidden_biases):
            activation = bias
            for weight, value in zip(weights, normalized):
                activation += weight * value
            hidden.append(math.tanh(activation))
        output = self.output_bias
        for weight, value in zip(self.output_weights, hidden):
            output += weight * value
        return output * self.target_scale + self.target_mean

    def to_dict(self) -> Dict[str, object]:
        return {
            "feature_names": list(self.feature_names),
            "input_means": list(self.input_means),
            "input_scales": list(self.input_scales),
            "target_mean": self.target_mean,
            "target_scale": self.target_scale,
            "hidden_weights": [list(row) for row in self.hidden_weights],
            "hidden_biases": list(self.hidden_biases),
            "output_weights": list(self.output_weights),
            "output_bias": self.output_bias,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "ScalarResidualNetwork":
        return cls(
            feature_names=list(payload["feature_names"]),
            input_means=list(payload["input_means"]),
            input_scales=list(payload["input_scales"]),
            target_mean=float(payload["target_mean"]),
            target_scale=float(payload["target_scale"]),
            hidden_weights=[list(row) for row in payload["hidden_weights"]],
            hidden_biases=list(payload["hidden_biases"]),
            output_weights=list(payload["output_weights"]),
            output_bias=float(payload["output_bias"]),
        )

    def _normalize_features(self, features: Sequence[float]) -> List[float]:
        return [
            (float(value) - mean) / scale
            for value, mean, scale in zip(features, self.input_means, self.input_scales)
        ]


@dataclass(frozen=True)
class HybridResidualModel:
    feature_names: List[str]
    metric_models: Dict[str, ScalarResidualNetwork]

    def predict(self, features: Sequence[float]) -> Dict[str, float]:
        return {
            metric: model.predict(features)
            for metric, model in self.metric_models.items()
        }

    def to_dict(self) -> Dict[str, object]:
        return {
            "feature_names": list(self.feature_names),
            "metric_models": {
                metric: model.to_dict()
                for metric, model in self.metric_models.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "HybridResidualModel":
        metric_models = {
            metric: ScalarResidualNetwork.from_dict(model_payload)
            for metric, model_payload in dict(payload["metric_models"]).items()
        }
        return cls(
            feature_names=list(payload["feature_names"]),
            metric_models=metric_models,
        )

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)

    @classmethod
    def load_json(cls, path: str) -> "HybridResidualModel":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


def run_hybrid_residual_experiment(
    include_window_matrix: bool = False,
    holdout_stride: int = 4,
    max_points_per_scenario: int = 96,
    hidden_dim: int = 10,
    epochs: int = 80,
    learning_rate: float = 0.018,
    l2: float = 1e-5,
    seed: int = 42,
) -> Dict[str, object]:
    scenarios = build_validation_scenarios()
    if include_window_matrix:
        scenarios += build_window_matrix_scenarios()

    train_scenarios, test_scenarios = split_scenarios_for_experiment(scenarios, holdout_stride=holdout_stride)
    if not train_scenarios or not test_scenarios:
        raise ValueError("Hybrid residual experiment requires at least one train scenario and one test scenario.")

    train_dataset = build_residual_dataset(train_scenarios, max_points_per_scenario=max_points_per_scenario)
    test_dataset = build_residual_dataset(test_scenarios, max_points_per_scenario=max_points_per_scenario)
    hybrid_model, metric_training = train_hybrid_residual_model(
        train_dataset=train_dataset,
        test_dataset=test_dataset,
        hidden_dim=hidden_dim,
        epochs=epochs,
        learning_rate=learning_rate,
        l2=l2,
        seed=seed,
    )

    scenario_summaries = []
    baseline_field_totals = {metric: 0.0 for metric in METRICS}
    hybrid_field_totals = {metric: 0.0 for metric in METRICS}
    baseline_zone_totals = {metric: 0.0 for metric in METRICS}
    hybrid_zone_totals = {metric: 0.0 for metric in METRICS}

    for scenario in test_scenarios:
        scenario_result = evaluate_hybrid_model_on_scenario(hybrid_model, scenario)
        scenario_summaries.append(scenario_result)
        for metric in METRICS:
            baseline_field_totals[metric] += float(scenario_result["baseline_field_mae"][metric])
            hybrid_field_totals[metric] += float(scenario_result["hybrid_field_mae"][metric])
            baseline_zone_totals[metric] += float(scenario_result["baseline_target_zone_mae"][metric])
            hybrid_zone_totals[metric] += float(scenario_result["hybrid_target_zone_mae"][metric])

    scenario_count = float(len(test_scenarios))
    baseline_field_mae = {
        metric: round(baseline_field_totals[metric] / scenario_count, 4)
        for metric in METRICS
    }
    hybrid_field_mae = {
        metric: round(hybrid_field_totals[metric] / scenario_count, 4)
        for metric in METRICS
    }
    baseline_zone_mae = {
        metric: round(baseline_zone_totals[metric] / scenario_count, 4)
        for metric in METRICS
    }
    hybrid_zone_mae = {
        metric: round(hybrid_zone_totals[metric] / scenario_count, 4)
        for metric in METRICS
    }

    return {
        "configuration": {
            "include_window_matrix": include_window_matrix,
            "holdout_stride": holdout_stride,
            "max_points_per_scenario": max_points_per_scenario,
            "hidden_dim": hidden_dim,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "l2": l2,
            "seed": seed,
        },
        "feature_names": list(hybrid_model.feature_names),
        "dataset": {
            "train_scenarios": [scenario.name for scenario in train_scenarios],
            "test_scenarios": [scenario.name for scenario in test_scenarios],
            "train_samples": len(train_dataset.features),
            "test_samples": len(test_dataset.features),
        },
        "metric_training": metric_training,
        "baseline_test_field_mae": baseline_field_mae,
        "hybrid_test_field_mae": hybrid_field_mae,
        "field_mae_reduction": _metric_reduction(baseline_field_mae, hybrid_field_mae),
        "baseline_test_target_zone_mae": baseline_zone_mae,
        "hybrid_test_target_zone_mae": hybrid_zone_mae,
        "target_zone_mae_reduction": _metric_reduction(baseline_zone_mae, hybrid_zone_mae),
        "test_scenarios": scenario_summaries,
        "checkpoint": hybrid_model.to_dict(),
    }


def split_scenarios_for_experiment(
    scenarios: List[Scenario],
    holdout_stride: int = 4,
) -> Tuple[List[Scenario], List[Scenario]]:
    stride = max(2, int(holdout_stride))
    train_scenarios: List[Scenario] = []
    test_scenarios: List[Scenario] = []
    for index, scenario in enumerate(scenarios):
        if index % stride == stride - 1:
            test_scenarios.append(scenario)
        else:
            train_scenarios.append(scenario)
    return train_scenarios, test_scenarios


def build_residual_dataset(
    scenarios: List[Scenario],
    max_points_per_scenario: int = 96,
) -> ResidualDataset:
    model = DigitalTwinModel()
    feature_names = build_feature_names()
    features: List[List[float]] = []
    targets = {metric: [] for metric in METRICS}
    scenario_names: List[str] = []

    for scenario in scenarios:
        truth_result, estimated_result = _truth_and_estimated_results(model, scenario)
        selected_indices = _selected_field_indices(estimated_result.field, max_points_per_scenario)
        for index in selected_indices:
            point = _field_point_from_index(estimated_result.field, index)
            estimated_values = {
                metric: estimated_result.field.values[metric][index]
                for metric in METRICS
            }
            truth_values = {
                metric: truth_result.field.values[metric][index]
                for metric in METRICS
            }
            features.append(
                build_point_features(
                    model=model,
                    scenario=scenario,
                    devices=estimated_result.calibrated_devices,
                    point=point,
                    estimated_values=estimated_values,
                )
            )
            for metric in METRICS:
                targets[metric].append(truth_values[metric] - estimated_values[metric])
            scenario_names.append(scenario.name)

    return ResidualDataset(
        feature_names=feature_names,
        features=features,
        targets=targets,
        scenario_names=scenario_names,
    )


def build_feature_names() -> List[str]:
    names = [
        "x_norm",
        "y_norm",
        "z_norm",
        "elapsed_norm",
        "indoor_temperature",
        "indoor_humidity",
        "indoor_base_illuminance",
        "outdoor_temperature",
        "outdoor_humidity",
        "sunlight_illuminance",
        "daylight_factor",
        "estimated_temperature",
        "estimated_humidity",
        "estimated_illuminance",
    ]
    for device_name in DEVICE_ORDER:
        names.extend(
            [
                f"{device_name}_activation",
                f"{device_name}_power",
                f"{device_name}_envelope",
            ]
        )
    for mode in AC_MODE_ORDER:
        names.append(f"ac_mode_{mode}")
    return names


def build_point_features(
    model: DigitalTwinModel,
    scenario: Scenario,
    devices: List[Device],
    point: Vector3,
    estimated_values: Dict[str, float],
) -> List[float]:
    features = [
        point.x / max(scenario.room.width, 1e-9),
        point.y / max(scenario.room.length, 1e-9),
        point.z / max(scenario.room.height, 1e-9),
        min(max(scenario.elapsed_minutes / 120.0, 0.0), 1.5),
        scenario.room.base_temperature,
        scenario.room.base_humidity,
        scenario.room.base_illuminance,
        scenario.environment.outdoor_temperature,
        scenario.environment.outdoor_humidity,
        scenario.environment.sunlight_illuminance,
        scenario.environment.daylight_factor,
        estimated_values["temperature"],
        estimated_values["humidity"],
        estimated_values["illuminance"],
    ]

    devices_by_name = {device.name: device for device in devices}
    for device_name in DEVICE_ORDER:
        device = devices_by_name.get(device_name)
        if device is None:
            features.extend([0.0, 0.0, 0.0])
            continue
        features.extend(
            [
                device.activation,
                device.power,
                model.influence_envelope(device, point, scenario.elapsed_minutes),
            ]
        )

    ac_device = devices_by_name.get("ac_main")
    ac_mode = "cool"
    if ac_device is not None:
        ac_mode = str(ac_device.metadata.get("ac_mode", "cool")).lower()
    for mode in AC_MODE_ORDER:
        features.append(1.0 if ac_mode == mode else 0.0)
    return features


def train_hybrid_residual_model(
    train_dataset: ResidualDataset,
    test_dataset: ResidualDataset,
    hidden_dim: int = 10,
    epochs: int = 80,
    learning_rate: float = 0.018,
    l2: float = 1e-5,
    seed: int = 42,
) -> Tuple[HybridResidualModel, Dict[str, Dict[str, float]]]:
    metric_models: Dict[str, ScalarResidualNetwork] = {}
    metric_training: Dict[str, Dict[str, float]] = {}

    for metric_index, metric in enumerate(METRICS):
        model = _train_scalar_network(
            feature_names=train_dataset.feature_names,
            features=train_dataset.features,
            targets=train_dataset.targets[metric],
            hidden_dim=hidden_dim,
            epochs=epochs,
            learning_rate=learning_rate,
            l2=l2,
            seed=seed + 31 * (metric_index + 1),
        )
        metric_models[metric] = model

        train_predictions = [model.predict(features) for features in train_dataset.features]
        test_predictions = [model.predict(features) for features in test_dataset.features]
        train_mae = _mae(train_predictions, train_dataset.targets[metric])
        test_mae = _mae(test_predictions, test_dataset.targets[metric])
        baseline_test_mae = _mae([0.0 for _ in test_dataset.targets[metric]], test_dataset.targets[metric])
        metric_training[metric] = {
            "train_residual_mae": round(train_mae, 6),
            "test_residual_mae": round(test_mae, 6),
            "baseline_test_residual_mae": round(baseline_test_mae, 6),
            "residual_mae_reduction": round(baseline_test_mae - test_mae, 6),
        }

    return HybridResidualModel(
        feature_names=list(train_dataset.feature_names),
        metric_models=metric_models,
    ), metric_training


def evaluate_hybrid_model_on_scenario(
    hybrid_model: HybridResidualModel,
    scenario: Scenario,
) -> Dict[str, object]:
    model = DigitalTwinModel()
    truth_result, estimated_result = _truth_and_estimated_results(model, scenario)
    hybrid_field = apply_hybrid_model_to_field(
        hybrid_model=hybrid_model,
        model=model,
        scenario=scenario,
        estimated_field=estimated_result.field,
        calibrated_devices=estimated_result.calibrated_devices,
    )
    hybrid_zone_averages = model.compute_zone_averages(hybrid_field, scenario.zones)

    baseline_field_mae = compare_fields(estimated_result.field, truth_result.field)
    hybrid_field_mae = compare_fields(hybrid_field, truth_result.field)
    baseline_zone_mae = compare_zone_averages(
        {scenario.target_zone_name: estimated_result.zone_averages[scenario.target_zone_name]},
        {scenario.target_zone_name: truth_result.zone_averages[scenario.target_zone_name]},
    )[scenario.target_zone_name]
    hybrid_zone_mae = compare_zone_averages(
        {scenario.target_zone_name: hybrid_zone_averages[scenario.target_zone_name]},
        {scenario.target_zone_name: truth_result.zone_averages[scenario.target_zone_name]},
    )[scenario.target_zone_name]

    return {
        "name": scenario.name,
        "baseline_field_mae": baseline_field_mae,
        "hybrid_field_mae": hybrid_field_mae,
        "field_mae_reduction": _metric_reduction(baseline_field_mae, hybrid_field_mae),
        "baseline_target_zone_mae": baseline_zone_mae,
        "hybrid_target_zone_mae": hybrid_zone_mae,
        "target_zone_mae_reduction": _metric_reduction(baseline_zone_mae, hybrid_zone_mae),
    }


def apply_hybrid_model_to_field(
    hybrid_model: HybridResidualModel,
    model: DigitalTwinModel,
    scenario: Scenario,
    estimated_field: FieldGrid,
    calibrated_devices: List[Device],
) -> FieldGrid:
    corrected = deepcopy(estimated_field)
    total_points = len(estimated_field.values["temperature"])
    for index in range(total_points):
        point = _field_point_from_index(estimated_field, index)
        estimated_values = {
            metric: estimated_field.values[metric][index]
            for metric in METRICS
        }
        features = build_point_features(
            model=model,
            scenario=scenario,
            devices=calibrated_devices,
            point=point,
            estimated_values=estimated_values,
        )
        residuals = hybrid_model.predict(features)
        corrected.values["temperature"][index] = estimated_values["temperature"] + residuals["temperature"]
        corrected.values["humidity"][index] = clamp(
            estimated_values["humidity"] + residuals["humidity"],
            0.0,
            100.0,
        )
        corrected.values["illuminance"][index] = max(
            0.0,
            estimated_values["illuminance"] + residuals["illuminance"],
        )
    return corrected


def _truth_and_estimated_results(model: DigitalTwinModel, scenario: Scenario):
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
    return truth_result, estimated_result


def _selected_field_indices(field: FieldGrid, max_points_per_scenario: int) -> List[int]:
    total_points = len(field.values["temperature"])
    limit = max(1, min(total_points, int(max_points_per_scenario)))
    if limit >= total_points:
        return list(range(total_points))
    step = max(1, total_points // limit)
    indices = list(range(0, total_points, step))[:limit]
    if indices[-1] != total_points - 1:
        indices[-1] = total_points - 1
    return indices


def _field_point_from_index(field: FieldGrid, index: int) -> Vector3:
    plane = field.resolution.nx * field.resolution.ny
    iz = index // plane
    remainder = index % plane
    iy = remainder // field.resolution.nx
    ix = remainder % field.resolution.nx
    return field.point(ix, iy, iz)


def _train_scalar_network(
    feature_names: List[str],
    features: List[List[float]],
    targets: List[float],
    hidden_dim: int,
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
) -> ScalarResidualNetwork:
    if not features or not targets:
        raise ValueError("Residual network training requires non-empty features and targets.")
    if len(features) != len(targets):
        raise ValueError("Feature and target counts must match.")

    input_means = []
    input_scales = []
    input_dim = len(features[0])
    for index in range(input_dim):
        column = [sample[index] for sample in features]
        mean = sum(column) / float(len(column))
        variance = sum((value - mean) ** 2 for value in column) / float(len(column))
        input_means.append(mean)
        input_scales.append(max(math.sqrt(variance), 1e-6))

    target_mean = sum(targets) / float(len(targets))
    target_variance = sum((value - target_mean) ** 2 for value in targets) / float(len(targets))
    target_scale = max(math.sqrt(target_variance), 1e-6)

    normalized_features = [
        [(value - mean) / scale for value, mean, scale in zip(sample, input_means, input_scales)]
        for sample in features
    ]
    normalized_targets = [(value - target_mean) / target_scale for value in targets]

    rng = random.Random(seed)
    weight_scale = 0.18
    hidden_weights = [
        [rng.uniform(-weight_scale, weight_scale) for _ in range(input_dim)]
        for _ in range(hidden_dim)
    ]
    hidden_biases = [0.0 for _ in range(hidden_dim)]
    output_weights = [rng.uniform(-weight_scale, weight_scale) for _ in range(hidden_dim)]
    output_bias = 0.0

    indices = list(range(len(normalized_features)))
    for epoch in range(max(1, epochs)):
        rng.shuffle(indices)
        epoch_lr = learning_rate / (1.0 + 0.035 * epoch)
        for index in indices:
            sample = normalized_features[index]
            target = normalized_targets[index]

            hidden_linear = []
            hidden_activations = []
            for weights, bias in zip(hidden_weights, hidden_biases):
                linear = bias
                for weight, value in zip(weights, sample):
                    linear += weight * value
                hidden_linear.append(linear)
                hidden_activations.append(math.tanh(linear))

            prediction = output_bias
            for weight, activation in zip(output_weights, hidden_activations):
                prediction += weight * activation

            error = prediction - target

            output_gradients = [error * activation for activation in hidden_activations]
            hidden_linear_gradients = []
            for hidden_index, activation in enumerate(hidden_activations):
                derivative = 1.0 - activation * activation
                hidden_linear_gradients.append(error * output_weights[hidden_index] * derivative)

            for hidden_index in range(hidden_dim):
                output_weights[hidden_index] -= epoch_lr * (output_gradients[hidden_index] + l2 * output_weights[hidden_index])
            output_bias -= epoch_lr * error

            for hidden_index in range(hidden_dim):
                gradient = hidden_linear_gradients[hidden_index]
                hidden_biases[hidden_index] -= epoch_lr * gradient
                weights = hidden_weights[hidden_index]
                for feature_index in range(input_dim):
                    weights[feature_index] -= epoch_lr * (
                        gradient * sample[feature_index] + l2 * weights[feature_index]
                    )

    return ScalarResidualNetwork(
        feature_names=list(feature_names),
        input_means=input_means,
        input_scales=input_scales,
        target_mean=target_mean,
        target_scale=target_scale,
        hidden_weights=hidden_weights,
        hidden_biases=hidden_biases,
        output_weights=output_weights,
        output_bias=output_bias,
    )


def _metric_reduction(baseline: Dict[str, float], corrected: Dict[str, float]) -> Dict[str, float]:
    output: Dict[str, float] = {}
    for metric in METRICS:
        baseline_value = float(baseline[metric])
        corrected_value = float(corrected[metric])
        reduction = baseline_value - corrected_value
        percent = 0.0
        if baseline_value > 1e-9:
            percent = reduction / baseline_value * 100.0
        output[metric] = round(percent, 4)
    return output


def _mae(first: Sequence[float], second: Sequence[float]) -> float:
    if len(first) != len(second):
        raise ValueError("Lengths must match.")
    if not first:
        return 0.0
    return sum(abs(a - b) for a, b in zip(first, second)) / float(len(first))
