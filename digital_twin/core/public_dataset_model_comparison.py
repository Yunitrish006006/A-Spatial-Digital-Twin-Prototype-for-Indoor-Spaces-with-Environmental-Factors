import json
import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from digital_twin.core.entities import Environment, Room, Vector3
from digital_twin.core.math_utils import clamp, solve_linear_system
from digital_twin.core.public_dataset_benchmark import (
    _build_cu_bems_event_delta_samples,
    _build_cu_bems_response_samples,
    _build_sml2010_event_delta_samples,
    _build_sml2010_response_samples,
    _load_cu_bems_records,
    _load_sml2010_records,
    _read_csv_rows,
    _read_optional_json,
    _stream_cu_bems_samples_from_source_files,
    run_public_dataset_benchmark,
)
from digital_twin.core.scenarios import build_device
from digital_twin.neural.hybrid_residual import HybridResidualModel, build_point_features
from digital_twin.physics.model import DigitalTwinModel


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_ROOT = ROOT / "outputs" / "data" / "public_benchmarks"
DEFAULT_CHECKPOINT_PATH = ROOT / "outputs" / "data" / "hybrid_residual_checkpoint.json"
_CU_BEMS_POINT = Vector3(3.0, 2.0, 2.8)
_SML_POINTS = {
    "dining_room": Vector3(1.8, 2.0, 1.2),
    "room": Vector3(4.2, 2.0, 1.2),
}


@dataclass(frozen=True)
class _PseudoScenario:
    room: Room
    environment: Environment
    furniture: List[object]
    elapsed_minutes: float


class _OnlineMetricAccumulator:
    def __init__(self) -> None:
        self.count = 0
        self.absolute_error_sum = 0.0
        self.squared_error_sum = 0.0
        self.actual_sum = 0.0
        self.predicted_sum = 0.0
        self.actual_squared_sum = 0.0
        self.predicted_squared_sum = 0.0
        self.cross_sum = 0.0

    def add(self, actual: float, predicted: float) -> None:
        self.count += 1
        error = actual - predicted
        self.absolute_error_sum += abs(error)
        self.squared_error_sum += error * error
        self.actual_sum += actual
        self.predicted_sum += predicted
        self.actual_squared_sum += actual * actual
        self.predicted_squared_sum += predicted * predicted
        self.cross_sum += actual * predicted

    def summary(self) -> Dict[str, float]:
        if self.count == 0:
            return {"mae": 0.0, "rmse": 0.0, "correlation": 0.0}
        numerator = (self.count * self.cross_sum) - (self.actual_sum * self.predicted_sum)
        denominator_left = (self.count * self.actual_squared_sum) - (self.actual_sum * self.actual_sum)
        denominator_right = (self.count * self.predicted_squared_sum) - (self.predicted_sum * self.predicted_sum)
        denominator = math.sqrt(max(denominator_left, 0.0) * max(denominator_right, 0.0))
        correlation = numerator / denominator if denominator > 1e-9 else 0.0
        return {
            "mae": round(self.absolute_error_sum / float(self.count), 6),
            "rmse": round(math.sqrt(self.squared_error_sum / float(self.count)), 6),
            "correlation": round(correlation, 6),
        }


class _MappedReadoutEvaluator:
    def __init__(
        self,
        task_id: str,
        dataset: str,
        horizon_minutes: int,
        target_names: Sequence[str],
        feature_names: Sequence[str],
        sample_count: int,
    ) -> None:
        self.task_id = task_id
        self.dataset = dataset
        self.horizon_minutes = horizon_minutes
        self.target_names = list(target_names)
        self.feature_names = list(feature_names)
        self.sample_count = int(sample_count)
        self.train_samples = max(1, min(self.sample_count - 1, int(self.sample_count * 0.7)))
        self.test_samples = self.sample_count - self.train_samples
        self._processed_samples = 0
        self._width = len(self.feature_names) + 1
        self._normal_matrix = [[0.0 for _ in range(self._width)] for _ in range(self._width)]
        self._target_vectors = {target_name: [0.0 for _ in range(self._width)] for target_name in self.target_names}
        self._coefficients: Optional[Dict[str, List[float]]] = None
        self._metrics = {target_name: _OnlineMetricAccumulator() for target_name in self.target_names}

    def consume(self, features: Sequence[float], targets: Dict[str, float]) -> None:
        self._processed_samples += 1
        row = [1.0] + [float(value) for value in features]
        if self._processed_samples <= self.train_samples:
            for row_index in range(self._width):
                for column_index in range(self._width):
                    self._normal_matrix[row_index][column_index] += row[row_index] * row[column_index]
            for target_name in self.target_names:
                target_value = float(targets[target_name])
                for row_index in range(self._width):
                    self._target_vectors[target_name][row_index] += row[row_index] * target_value
            if self._processed_samples == self.train_samples:
                self._coefficients = {
                    target_name: solve_linear_system(self._normal_matrix, self._target_vectors[target_name])
                    for target_name in self.target_names
                }
            return

        if self._coefficients is None:
            self._coefficients = {
                target_name: solve_linear_system(self._normal_matrix, self._target_vectors[target_name])
                for target_name in self.target_names
            }

        for target_name in self.target_names:
            prediction = float(sum(weight * value for weight, value in zip(self._coefficients[target_name], row)))
            self._metrics[target_name].add(float(targets[target_name]), prediction)

    def summary(self, baseline_task: Dict[str, object], model_name: str) -> Dict[str, object]:
        if baseline_task.get("status") != "ok":
            payload = dict(baseline_task)
            payload["mapped_model_name"] = model_name
            payload["mapped_feature_names"] = list(self.feature_names)
            return payload

        merged_targets: Dict[str, Dict[str, object]] = {}
        for target_name in self.target_names:
            baseline_target = baseline_task["targets"][target_name]
            mapped_metrics = self._metrics[target_name].summary()
            persistence_mae = float(baseline_target["persistence"]["mae"])
            linear_mae = float(baseline_target["linear_regression"]["mae"])
            merged_targets[target_name] = {
                "persistence": baseline_target["persistence"],
                "linear_regression": baseline_target["linear_regression"],
                model_name: mapped_metrics,
                "linear_regression_vs_persistence_mae_reduction": baseline_target["mae_reduction_vs_persistence"],
                f"{model_name}_vs_persistence_mae_reduction": round(persistence_mae - mapped_metrics["mae"], 6),
                f"{model_name}_vs_linear_regression_mae_reduction": round(linear_mae - mapped_metrics["mae"], 6),
            }

        return {
            "task_id": self.task_id,
            "dataset": self.dataset,
            "horizon_minutes": self.horizon_minutes,
            "status": "ok",
            "sample_count": self.sample_count,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
            "feature_names": baseline_task["feature_names"],
            "target_names": self.target_names,
            "mapped_model_name": model_name,
            "mapped_feature_names": list(self.feature_names),
            "targets": merged_targets,
        }


class MappedHybridPublicPredictor:
    def __init__(self, checkpoint_path: Optional[Path] = None) -> None:
        self.model = DigitalTwinModel()
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else DEFAULT_CHECKPOINT_PATH
        self.hybrid_model = HybridResidualModel.load_json(str(self.checkpoint_path)) if self.checkpoint_path.exists() else None
        self.model_name = "hybrid_digital_twin_readout"

    def feature_names(self, dataset: str, task_id: str) -> List[str]:
        dataset_key = dataset.strip().lower()
        if dataset_key == "cu-bems":
            if task_id == "C1":
                return [
                    "physics_temperature",
                    "physics_humidity",
                    "hybrid_temperature",
                    "hybrid_humidity",
                    "ac_activation",
                    "plug_load_scaled",
                ]
            if task_id == "C2":
                return [
                    "physics_illuminance",
                    "hybrid_illuminance",
                    "light_activation",
                    "plug_load_scaled",
                ]
            return [
                "physics_temperature_delta",
                "physics_humidity_delta",
                "physics_illuminance_delta",
                "hybrid_temperature_delta",
                "hybrid_humidity_delta",
                "hybrid_illuminance_delta",
                "event_direction",
                "event_kind_ac",
                "event_kind_light",
            ]

        if task_id == "S1":
            return [
                "physics_dining_illuminance",
                "physics_room_illuminance",
                "hybrid_dining_illuminance",
                "hybrid_room_illuminance",
                "boundary_activation",
                "sunlight_scaled",
                "rain_ratio",
                "wind_scaled",
            ]
        if task_id == "S2":
            return [
                "physics_dining_temperature",
                "physics_room_temperature",
                "physics_dining_humidity",
                "physics_room_humidity",
                "hybrid_dining_temperature",
                "hybrid_room_temperature",
                "hybrid_dining_humidity",
                "hybrid_room_humidity",
                "boundary_activation",
                "motor_level",
                "outdoor_temperature_gap",
                "outdoor_humidity_gap",
            ]
        return [
            "physics_dining_temperature_delta",
            "physics_room_temperature_delta",
            "physics_dining_humidity_delta",
            "physics_room_humidity_delta",
            "physics_dining_illuminance_delta",
            "physics_room_illuminance_delta",
            "hybrid_dining_temperature_delta",
            "hybrid_room_temperature_delta",
            "hybrid_dining_humidity_delta",
            "hybrid_room_humidity_delta",
            "hybrid_dining_illuminance_delta",
            "hybrid_room_illuminance_delta",
            "delta_outdoor_temperature",
            "delta_outdoor_humidity",
            "delta_sunlight",
            "delta_rain",
            "delta_wind",
        ]

    def build_features(self, dataset: str, task_id: str, sample: Dict[str, object], horizon_minutes: int) -> List[float]:
        dataset_key = dataset.strip().lower()
        context = sample["context"]
        if dataset_key == "cu-bems":
            if task_id == "C1":
                predictions = self._predict_cu_bems_absolute(context["origin"], include_ac=True, include_light=False, horizon_minutes=horizon_minutes)
                return [
                    predictions["physics"]["temperature"],
                    predictions["physics"]["humidity"],
                    predictions["hybrid"]["temperature"],
                    predictions["hybrid"]["humidity"],
                    self._bounded_activation(float(context["origin"].get("ac_power") or 0.0), reference=18.0),
                    self._bounded_activation(float(context["origin"].get("plug_load") or 0.0), reference=8.0),
                ]
            if task_id == "C2":
                predictions = self._predict_cu_bems_absolute(context["origin"], include_ac=False, include_light=True, horizon_minutes=horizon_minutes)
                return [
                    predictions["physics"]["illuminance"],
                    predictions["hybrid"]["illuminance"],
                    self._bounded_activation(float(context["origin"].get("lighting_power") or 0.0), reference=12.0),
                    self._bounded_activation(float(context["origin"].get("plug_load") or 0.0), reference=8.0),
                ]
            predictions = self._predict_cu_bems_event(context, horizon_minutes=horizon_minutes)
            event_kind = str(context["event_kind"])
            return [
                predictions["physics"]["temperature"],
                predictions["physics"]["humidity"],
                predictions["physics"]["illuminance"],
                predictions["hybrid"]["temperature"],
                predictions["hybrid"]["humidity"],
                predictions["hybrid"]["illuminance"],
                1.0 if event_kind.endswith("_on") else -1.0,
                1.0 if event_kind.startswith("ac") else 0.0,
                1.0 if event_kind.startswith("light") else 0.0,
            ]

        if task_id == "S1":
            predictions, control = self._predict_sml2010_absolute(context["origin"], include_hvac=False, horizon_minutes=horizon_minutes)
            return [
                predictions["physics"]["dining_illuminance"],
                predictions["physics"]["room_illuminance"],
                predictions["hybrid"]["dining_illuminance"],
                predictions["hybrid"]["room_illuminance"],
                control["boundary_activation"],
                control["sunlight_scaled"],
                control["rain_ratio"],
                control["wind_scaled"],
            ]
        if task_id == "S2":
            predictions, control = self._predict_sml2010_absolute(context["origin"], include_hvac=True, horizon_minutes=horizon_minutes)
            return [
                predictions["physics"]["dining_temperature"],
                predictions["physics"]["room_temperature"],
                predictions["physics"]["dining_humidity"],
                predictions["physics"]["room_humidity"],
                predictions["hybrid"]["dining_temperature"],
                predictions["hybrid"]["room_temperature"],
                predictions["hybrid"]["dining_humidity"],
                predictions["hybrid"]["room_humidity"],
                control["boundary_activation"],
                control["motor_level"],
                control["outdoor_temperature_gap"],
                control["outdoor_humidity_gap"],
            ]
        predictions, deltas = self._predict_sml2010_event(context, horizon_minutes=horizon_minutes)
        return [
            predictions["physics"]["dining_temperature"],
            predictions["physics"]["room_temperature"],
            predictions["physics"]["dining_humidity"],
            predictions["physics"]["room_humidity"],
            predictions["physics"]["dining_illuminance"],
            predictions["physics"]["room_illuminance"],
            predictions["hybrid"]["dining_temperature"],
            predictions["hybrid"]["room_temperature"],
            predictions["hybrid"]["dining_humidity"],
            predictions["hybrid"]["room_humidity"],
            predictions["hybrid"]["dining_illuminance"],
            predictions["hybrid"]["room_illuminance"],
            deltas["delta_outdoor_temperature"],
            deltas["delta_outdoor_humidity"],
            deltas["delta_sunlight"],
            deltas["delta_rain"],
            deltas["delta_wind"],
        ]

    def _predict_cu_bems_absolute(
        self,
        origin: Dict[str, float],
        include_ac: bool,
        include_light: bool,
        horizon_minutes: int,
    ) -> Dict[str, Dict[str, float]]:
        room = Room(
            name="cu_bems_pseudo_room",
            width=6.0,
            length=4.0,
            height=3.0,
            base_temperature=float(origin.get("temperature") or 25.0),
            base_humidity=float(origin.get("humidity") or 55.0),
            base_illuminance=max(float(origin.get("illuminance") or 90.0), 0.0),
        )
        environment = Environment(
            outdoor_temperature=room.base_temperature,
            outdoor_humidity=room.base_humidity,
            sunlight_illuminance=max(room.base_illuminance, 0.0),
            daylight_factor=0.15,
        )
        devices = []
        if include_ac:
            ac_activation = self._bounded_activation(float(origin.get("ac_power") or 0.0), reference=18.0)
            if ac_activation > 0.0:
                devices.append(
                    build_device(
                        name="ac_main",
                        kind="ac",
                        position=Vector3(0.3, 2.0, 2.7),
                        activation=ac_activation,
                        power=1.0,
                        metadata={
                            "ac_mode": "cool",
                            "target_temperature": clamp(room.base_temperature - 2.0, 20.0, 26.0),
                        },
                    )
                )
        if include_light:
            # 支援多燈裝置：自動偵測所有 lighting_power 欄位
            light_keys = [k for k in origin.keys() if k.startswith("lighting_power")]
            if not light_keys and "lighting_power" in origin:
                light_keys = ["lighting_power"]
            n_lights = len(light_keys)
            for i, key in enumerate(light_keys):
                power_val = float(origin.get(key) or 0.0)
                activation = self._bounded_activation(power_val, reference=12.0)
                # 預設照度角（光散開範圍）120度，可依資料集自訂
                direction_angle_deg = 120.0
                # 若 origin 有對應欄位可自動帶入
                angle_key = key.replace("power", "angle_deg")
                if angle_key in origin:
                    try:
                        direction_angle_deg = float(origin[angle_key])
                    except Exception:
                        pass
                if activation > 0.0:
                    x = 1.0 + (4.0 * i / max(n_lights - 1, 1)) if n_lights > 1 else 3.0
                    devices.append(
                        build_device(
                            name=f"light_{i+1}",
                            kind="light",
                            position=Vector3(x, 2.0, 2.85),
                            activation=activation,
                            power=1.0,
                            metadata={
                                "direction_angle_deg": direction_angle_deg,
                            },
                        )
                    )
        physics = self.model.sample_point(
            point=_CU_BEMS_POINT,
            room=room,
            environment=environment,
            devices=devices,
            furniture=[],
            elapsed_minutes=float(horizon_minutes),
        )
        hybrid = self._apply_hybrid(room, environment, devices, _CU_BEMS_POINT, float(horizon_minutes), physics)
        return {"physics": physics, "hybrid": hybrid}

    def _predict_cu_bems_event(self, context: Dict[str, object], horizon_minutes: int) -> Dict[str, Dict[str, float]]:
        previous = context["previous"]
        current = context["current"]
        room = Room(
            name="cu_bems_event_room",
            width=6.0,
            length=4.0,
            height=3.0,
            base_temperature=float(previous.get("temperature") or 25.0),
            base_humidity=float(previous.get("humidity") or 55.0),
            base_illuminance=max(float(previous.get("illuminance") or 90.0), 0.0),
        )
        environment = Environment(
            outdoor_temperature=room.base_temperature,
            outdoor_humidity=room.base_humidity,
            sunlight_illuminance=max(room.base_illuminance, 0.0),
            daylight_factor=0.15,
        )
        devices = []
        ac_activation = self._bounded_activation(float(current.get("ac_power") or 0.0), reference=18.0)
        if ac_activation > 0.0:
            devices.append(
                build_device(
                    name="ac_main",
                    kind="ac",
                    position=Vector3(0.3, 2.0, 2.7),
                    activation=ac_activation,
                    power=1.0,
                    metadata={
                        "ac_mode": "cool",
                        "target_temperature": clamp(room.base_temperature - 2.0, 20.0, 26.0),
                    },
                )
            )
        light_activation = self._bounded_activation(float(current.get("lighting_power") or 0.0), reference=12.0)
        if light_activation > 0.0:
            devices.append(
                build_device(
                    name="light_main",
                    kind="light",
                    position=Vector3(3.0, 2.0, 2.85),
                    activation=light_activation,
                    power=1.0,
                )
            )
        physics_absolute = self.model.sample_point(
            point=_CU_BEMS_POINT,
            room=room,
            environment=environment,
            devices=devices,
            furniture=[],
            elapsed_minutes=float(horizon_minutes),
        )
        hybrid_absolute = self._apply_hybrid(room, environment, devices, _CU_BEMS_POINT, float(horizon_minutes), physics_absolute)
        return {
            "physics": {
                metric: physics_absolute[metric] - float(previous.get(metric) or 0.0)
                for metric in ("temperature", "humidity", "illuminance")
            },
            "hybrid": {
                metric: hybrid_absolute[metric] - float(previous.get(metric) or 0.0)
                for metric in ("temperature", "humidity", "illuminance")
            },
        }

    def _predict_sml2010_absolute(
        self,
        origin: Dict[str, float],
        include_hvac: bool,
        horizon_minutes: int,
    ) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
        dining_temperature = float(origin.get("dining_temperature") or 22.0)
        room_temperature = float(origin.get("room_temperature") or dining_temperature)
        dining_humidity = float(origin.get("dining_humidity") or 50.0)
        room_humidity = float(origin.get("room_humidity") or dining_humidity)
        dining_illuminance = max(float(origin.get("dining_illuminance") or 70.0), 0.0)
        room_illuminance = max(float(origin.get("room_illuminance") or dining_illuminance), 0.0)
        room = Room(
            name="sml2010_pseudo_room",
            width=6.0,
            length=4.0,
            height=3.0,
            base_temperature=(dining_temperature + room_temperature) / 2.0,
            base_humidity=(dining_humidity + room_humidity) / 2.0,
            base_illuminance=(dining_illuminance + room_illuminance) / 2.0,
        )
        sunlight = max(float(origin.get("sunlight_illuminance") or 0.0), 0.0)
        environment = Environment(
            outdoor_temperature=float(origin.get("outdoor_temperature") or room.base_temperature),
            outdoor_humidity=float(origin.get("outdoor_humidity") or room.base_humidity),
            sunlight_illuminance=sunlight,
            daylight_factor=clamp(float(origin.get("daylight_factor") or 0.0), 0.0, 1.2),
        )
        boundary_activation, motor_level = self._sml_boundary_controls(origin, room)
        devices = []
        if boundary_activation > 0.0:
            devices.append(
                build_device(
                    name="window_main",
                    kind="window",
                    position=Vector3(0.0, 2.0, 1.4),
                    activation=boundary_activation,
                    power=1.0,
                )
            )
        if include_hvac and motor_level > 0.0:
            devices.append(
                build_device(
                    name="ac_main",
                    kind="ac",
                    position=Vector3(5.4, 2.0, 2.75),
                    activation=motor_level,
                    power=1.0,
                    metadata={
                        "ac_mode": "dry",
                        "target_temperature": clamp(float(origin.get("forecast_temperature") or room.base_temperature), 20.0, 28.0),
                    },
                )
            )

        physics_outputs: Dict[str, float] = {}
        hybrid_outputs: Dict[str, float] = {}
        for point_name, point in _SML_POINTS.items():
            physics = self.model.sample_point(
                point=point,
                room=room,
                environment=environment,
                devices=devices,
                furniture=[],
                elapsed_minutes=float(horizon_minutes),
            )
            hybrid = self._apply_hybrid(room, environment, devices, point, float(horizon_minutes), physics)
            prefix = "dining" if point_name == "dining_room" else "room"
            physics_outputs[f"{prefix}_temperature"] = physics["temperature"]
            physics_outputs[f"{prefix}_humidity"] = physics["humidity"]
            physics_outputs[f"{prefix}_illuminance"] = physics["illuminance"]
            hybrid_outputs[f"{prefix}_temperature"] = hybrid["temperature"]
            hybrid_outputs[f"{prefix}_humidity"] = hybrid["humidity"]
            hybrid_outputs[f"{prefix}_illuminance"] = hybrid["illuminance"]

        controls = {
            "boundary_activation": boundary_activation,
            "motor_level": motor_level,
            "sunlight_scaled": self._bounded_activation(sunlight, reference=18000.0),
            "rain_ratio": float(origin.get("rain_ratio") or 0.0),
            "wind_scaled": self._bounded_activation(float(origin.get("wind_speed") or 0.0), reference=4.0),
            "outdoor_temperature_gap": (float(origin.get("outdoor_temperature") or room.base_temperature) - room.base_temperature) / 12.0,
            "outdoor_humidity_gap": (float(origin.get("outdoor_humidity") or room.base_humidity) - room.base_humidity) / 25.0,
        }
        return {"physics": physics_outputs, "hybrid": hybrid_outputs}, controls

    def _predict_sml2010_event(
        self,
        context: Dict[str, object],
        horizon_minutes: int,
    ) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
        previous = deepcopy(context["previous"])
        current = deepcopy(context["current"])
        predictions, _ = self._predict_sml2010_absolute(current, include_hvac=True, horizon_minutes=horizon_minutes)
        previous_values = {
            "dining_temperature": float(previous.get("dining_temperature") or 0.0),
            "room_temperature": float(previous.get("room_temperature") or 0.0),
            "dining_humidity": float(previous.get("dining_humidity") or 0.0),
            "room_humidity": float(previous.get("room_humidity") or 0.0),
            "dining_illuminance": float(previous.get("dining_illuminance") or 0.0),
            "room_illuminance": float(previous.get("room_illuminance") or 0.0),
        }
        delta_predictions = {
            kind: {
                key: values[key] - previous_values[key]
                for key in previous_values
            }
            for kind, values in predictions.items()
        }
        deltas = {
            "delta_outdoor_temperature": float(context.get("delta_outdoor_temperature") or 0.0) / 8.0,
            "delta_outdoor_humidity": float(context.get("delta_outdoor_humidity") or 0.0) / 20.0,
            "delta_sunlight": float(context.get("delta_sunlight") or 0.0) / 12000.0,
            "delta_rain": float(context.get("delta_rain") or 0.0),
            "delta_wind": float(context.get("delta_wind") or 0.0) / 4.0,
        }
        return delta_predictions, deltas

    def _apply_hybrid(
        self,
        room: Room,
        environment: Environment,
        devices: List[object],
        point: Vector3,
        elapsed_minutes: float,
        estimated_values: Dict[str, float],
    ) -> Dict[str, float]:
        corrected = dict(estimated_values)
        if self.hybrid_model is None:
            return corrected
        scenario = _PseudoScenario(room=room, environment=environment, furniture=[], elapsed_minutes=elapsed_minutes)
        residuals = self.hybrid_model.predict(
            build_point_features(
                model=self.model,
                scenario=scenario,
                devices=devices,
                point=point,
                estimated_values=estimated_values,
            )
        )
        corrected["temperature"] = estimated_values["temperature"] + residuals["temperature"]
        corrected["humidity"] = clamp(estimated_values["humidity"] + residuals["humidity"], 0.0, 100.0)
        corrected["illuminance"] = max(0.0, estimated_values["illuminance"] + residuals["illuminance"])
        return corrected

    def _sml_boundary_controls(self, origin: Dict[str, float], room: Room) -> Tuple[float, float]:
        sunlight_scaled = self._bounded_activation(float(origin.get("sunlight_illuminance") or 0.0), reference=18000.0)
        wind_scaled = self._bounded_activation(float(origin.get("wind_speed") or 0.0), reference=4.0)
        rain_ratio = clamp(float(origin.get("rain_ratio") or 0.0), 0.0, 1.0)
        motor_level = clamp(
            (
                float(origin.get("enthalpic_motor_1") or 0.0)
                + float(origin.get("enthalpic_motor_2") or 0.0)
                + float(origin.get("enthalpic_motor_turbo") or 0.0)
            )
            / 3.0,
            0.0,
            1.0,
        )
        thermal_gap = self._bounded_activation(
            abs(float(origin.get("outdoor_temperature") or room.base_temperature) - room.base_temperature),
            reference=8.0,
        )
        activation = clamp(
            0.12 + 0.36 * sunlight_scaled + 0.18 * wind_scaled + 0.18 * thermal_gap + 0.16 * motor_level - 0.1 * rain_ratio,
            0.05,
            1.0,
        )
        return activation, motor_level

    def _bounded_activation(self, value: float, reference: float) -> float:
        reference = max(reference, 1e-6)
        return clamp(1.0 - math.exp(-max(float(value), 0.0) / reference), 0.0, 1.0)


def run_public_dataset_model_comparison(
    dataset: str,
    input_dir: Path,
    horizons: Sequence[int] = (15,),
    baseline_summary: Optional[Dict[str, object]] = None,
    baseline_summary_path: Optional[Path] = None,
    checkpoint_path: Optional[Path] = None,
) -> Dict[str, object]:
    baseline = _resolve_baseline_summary(
        dataset=dataset,
        input_dir=input_dir,
        horizons=horizons,
        baseline_summary=baseline_summary,
        baseline_summary_path=baseline_summary_path,
    )
    predictor = MappedHybridPublicPredictor(checkpoint_path=checkpoint_path)
    dataset_key = dataset.strip().lower()
    if dataset_key == "cu-bems":
        return _run_cu_bems_model_comparison(input_dir=input_dir, baseline=baseline, predictor=predictor, horizons=horizons)
    if dataset_key == "sml2010":
        return _run_sml2010_model_comparison(input_dir=input_dir, baseline=baseline, predictor=predictor, horizons=horizons)
    raise ValueError(f"Unsupported dataset: {dataset}")


def write_public_dataset_model_comparison(summary: Dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _resolve_baseline_summary(
    dataset: str,
    input_dir: Path,
    horizons: Sequence[int],
    baseline_summary: Optional[Dict[str, object]],
    baseline_summary_path: Optional[Path],
) -> Dict[str, object]:
    if baseline_summary is not None:
        return baseline_summary
    if baseline_summary_path is not None and baseline_summary_path.exists():
        return json.loads(baseline_summary_path.read_text(encoding="utf-8"))
    return run_public_dataset_benchmark(dataset=dataset, input_dir=input_dir, horizons=horizons)


def _run_cu_bems_model_comparison(
    input_dir: Path,
    baseline: Dict[str, object],
    predictor: MappedHybridPublicPredictor,
    horizons: Sequence[int],
) -> Dict[str, object]:
    metadata = _read_optional_json(input_dir / "scenario_metadata.json")
    source_files = [Path(path) for path in metadata.get("source_files", []) if Path(path).exists()]
    if source_files:
        tasks = _run_cu_bems_comparison_from_source_files(source_files, baseline, predictor, horizons)
    else:
        sensor_rows = _read_csv_rows(input_dir / "corner_sensor_timeseries.csv")
        device_rows = _read_csv_rows(input_dir / "device_event_log.csv")
        auxiliary_rows = _read_csv_rows(input_dir / "auxiliary_features.csv")
        records_by_zone = _load_cu_bems_records(sensor_rows, device_rows, auxiliary_rows)
        tasks = _run_cu_bems_comparison_from_samples(records_by_zone, baseline, predictor, horizons)

    return {
        "dataset": baseline["dataset"],
        "benchmark_mode": baseline["benchmark_mode"],
        "input_dir": str(input_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "horizons": list(horizons),
        "counts": baseline["counts"],
        "metadata": baseline.get("metadata", {}),
        "mapped_model_name": predictor.model_name,
        "mapped_model_checkpoint": str(predictor.checkpoint_path) if predictor.checkpoint_path.exists() else "",
        "mapping_notes": [
            "Uses DigitalTwinModel plus the trained hybrid residual checkpoint as a structured prior.",
            "Fits a small linear readout head on the same chronological 70/30 split used by the public benchmark baselines.",
            "CU-BEMS power values are converted to bounded device activations rather than treated as direct geometry-aware kW inputs.",
        ],
        "tasks": tasks,
    }


def _run_cu_bems_comparison_from_samples(
    records_by_zone: Dict[str, List[Dict[str, float]]],
    baseline: Dict[str, object],
    predictor: MappedHybridPublicPredictor,
    horizons: Sequence[int],
) -> List[Dict[str, object]]:
    baseline_lookup = _task_lookup(baseline)
    output: List[Dict[str, object]] = []
    for horizon in horizons:
        for task_id in ("C1", "C2", "C3"):
            baseline_task = baseline_lookup[(task_id, horizon)]
            if baseline_task.get("status") != "ok":
                payload = dict(baseline_task)
                payload["mapped_model_name"] = predictor.model_name
                payload["mapped_feature_names"] = predictor.feature_names("cu-bems", task_id)
                output.append(payload)
                continue
            if task_id == "C1":
                samples = _build_cu_bems_response_samples(records_by_zone, horizon, task_id="C1")
            elif task_id == "C2":
                samples = _build_cu_bems_response_samples(records_by_zone, horizon, task_id="C2")
            else:
                samples = _build_cu_bems_event_delta_samples(records_by_zone, horizon)
            evaluator = _MappedReadoutEvaluator(
                task_id=task_id,
                dataset="CU-BEMS",
                horizon_minutes=horizon,
                target_names=baseline_task["target_names"],
                feature_names=predictor.feature_names("cu-bems", task_id),
                sample_count=int(baseline_task["sample_count"]),
            )
            for sample in samples:
                evaluator.consume(
                    features=predictor.build_features("cu-bems", task_id, sample, horizon),
                    targets=sample["targets"],
                )
            output.append(evaluator.summary(baseline_task, predictor.model_name))
    return output


def _run_cu_bems_comparison_from_source_files(
    source_files: Sequence[Path],
    baseline: Dict[str, object],
    predictor: MappedHybridPublicPredictor,
    horizons: Sequence[int],
) -> List[Dict[str, object]]:
    baseline_lookup = _task_lookup(baseline)
    evaluators: Dict[Tuple[str, int], _MappedReadoutEvaluator] = {}
    for horizon in horizons:
        for task_id in ("C1", "C2", "C3"):
            baseline_task = baseline_lookup[(task_id, horizon)]
            if baseline_task.get("status") != "ok":
                continue
            evaluators[(task_id, horizon)] = _MappedReadoutEvaluator(
                task_id=task_id,
                dataset="CU-BEMS",
                horizon_minutes=horizon,
                target_names=baseline_task["target_names"],
                feature_names=predictor.feature_names("cu-bems", task_id),
                sample_count=int(baseline_task["sample_count"]),
            )

    def consume(task_id: str, horizon: int, sample: Dict[str, object]) -> None:
        evaluator = evaluators.get((task_id, horizon))
        if evaluator is None:
            return
        evaluator.consume(
            features=predictor.build_features("cu-bems", task_id, sample, horizon),
            targets=sample["targets"],
        )

    _stream_cu_bems_samples_from_source_files(source_files=source_files, horizons=horizons, on_sample=consume)

    output: List[Dict[str, object]] = []
    for horizon in horizons:
        for task_id in ("C1", "C2", "C3"):
            baseline_task = baseline_lookup[(task_id, horizon)]
            evaluator = evaluators.get((task_id, horizon))
            if evaluator is None:
                payload = dict(baseline_task)
                payload["mapped_model_name"] = predictor.model_name
                payload["mapped_feature_names"] = predictor.feature_names("cu-bems", task_id)
                output.append(payload)
                continue
            output.append(evaluator.summary(baseline_task, predictor.model_name))
    return output


def _run_sml2010_model_comparison(
    input_dir: Path,
    baseline: Dict[str, object],
    predictor: MappedHybridPublicPredictor,
    horizons: Sequence[int],
) -> Dict[str, object]:
    sensor_rows = _read_csv_rows(input_dir / "corner_sensor_timeseries.csv")
    outdoor_rows = _read_csv_rows(input_dir / "outdoor_environment.csv")
    auxiliary_rows = _read_csv_rows(input_dir / "auxiliary_features.csv")
    records = _load_sml2010_records(sensor_rows, outdoor_rows, auxiliary_rows)
    baseline_lookup = _task_lookup(baseline)
    tasks: List[Dict[str, object]] = []

    for horizon in horizons:
        for task_id in ("S1", "S2", "S3"):
            baseline_task = baseline_lookup[(task_id, horizon)]
            if baseline_task.get("status") != "ok":
                payload = dict(baseline_task)
                payload["mapped_model_name"] = predictor.model_name
                payload["mapped_feature_names"] = predictor.feature_names("sml2010", task_id)
                tasks.append(payload)
                continue

            if task_id == "S1":
                samples = _build_sml2010_response_samples(records, horizon, task_id="S1")
            elif task_id == "S2":
                samples = _build_sml2010_response_samples(records, horizon, task_id="S2")
            else:
                samples = _build_sml2010_event_delta_samples(records, horizon)

            evaluator = _MappedReadoutEvaluator(
                task_id=task_id,
                dataset="SML2010",
                horizon_minutes=horizon,
                target_names=baseline_task["target_names"],
                feature_names=predictor.feature_names("sml2010", task_id),
                sample_count=int(baseline_task["sample_count"]),
            )
            for sample in samples:
                evaluator.consume(
                    features=predictor.build_features("sml2010", task_id, sample, horizon),
                    targets=sample["targets"],
                )
            tasks.append(evaluator.summary(baseline_task, predictor.model_name))

    return {
        "dataset": baseline["dataset"],
        "benchmark_mode": baseline["benchmark_mode"],
        "input_dir": str(input_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "horizons": list(horizons),
        "counts": baseline["counts"],
        "metadata": baseline.get("metadata", {}),
        "mapped_model_name": predictor.model_name,
        "mapped_model_checkpoint": str(predictor.checkpoint_path) if predictor.checkpoint_path.exists() else "",
        "mapping_notes": [
            "Uses a pseudo single-room boundary-coupling mapping with window and HVAC proxy devices.",
            "Fits a small linear readout head on the same chronological 70/30 split used by the public benchmark baselines.",
            "Enthalpic motor features modulate a generic HVAC proxy rather than being claimed as explicit window states.",
        ],
        "tasks": tasks,
    }


def _task_lookup(summary: Dict[str, object]) -> Dict[Tuple[str, int], Dict[str, object]]:
    lookup: Dict[Tuple[str, int], Dict[str, object]] = {}
    for task in summary["tasks"]:
        lookup[(task["task_id"], int(task["horizon_minutes"]))] = task
    return lookup