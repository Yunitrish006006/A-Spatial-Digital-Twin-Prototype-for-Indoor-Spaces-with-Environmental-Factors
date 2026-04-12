from pathlib import Path
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
from .entities import Furniture, Vector3
from .hybrid_residual import (
    HybridResidualModel,
    apply_hybrid_model_to_field,
    build_point_features,
    run_hybrid_residual_experiment as run_hybrid_residual_experiment_backend,
)
from .math_utils import clamp
from .model import DigitalTwinModel
from .recommendations import apply_action
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


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
HYBRID_CHECKPOINT_PATH = OUTPUTS / "hybrid_residual_checkpoint.json"
_HYBRID_MODEL_CACHE: Dict[str, object] = {"mtime": None, "model": None}


def list_scenario_metadata() -> List[Dict]:
    return [_scenario_metadata(scenario) for scenario in build_validation_scenarios()]


def list_window_scenario_metadata() -> List[Dict]:
    return [_scenario_metadata(scenario) for scenario in build_window_matrix_scenarios()]


def evaluate_scenario(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _evaluate_scenario_object(scenario, use_hybrid_residual=use_hybrid_residual)


def evaluate_window_direct(
    outdoor_temperature: float,
    outdoor_humidity: float,
    sunlight_illuminance: float,
    opening_ratio: float = 0.7,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: float = 70.0,
    daylight_factor: float = 0.95,
    elapsed_minutes: float = 18.0,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
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
    scenario = _scenario_with_overrides(
        scenario,
        None,
        None,
        furniture_overrides,
        extra_furniture=extra_furniture,
    )
    result = _evaluate_scenario_object(scenario, use_hybrid_residual=use_hybrid_residual)
    result["input"] = _window_direct_input_dict(
        scenario=scenario,
        opening_ratio=opening_ratio,
    )
    return result


def evaluate_window_direct_dashboard(
    outdoor_temperature: float,
    outdoor_humidity: float,
    sunlight_illuminance: float,
    opening_ratio: float = 0.7,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: float = 70.0,
    daylight_factor: float = 0.95,
    elapsed_minutes: float = 18.0,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
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
    scenario = _scenario_with_overrides(
        scenario,
        None,
        None,
        furniture_overrides,
        extra_furniture=extra_furniture,
    )
    result = _evaluate_dashboard_scenario_object(scenario, use_hybrid_residual=use_hybrid_residual)
    result["scenario"]["input"] = _window_direct_input_dict(
        scenario=scenario,
        opening_ratio=opening_ratio,
    )
    return result


def sample_window_direct_point(
    x: float,
    y: float,
    z: float,
    outdoor_temperature: float,
    outdoor_humidity: float,
    sunlight_illuminance: float,
    opening_ratio: float = 0.7,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: float = 70.0,
    daylight_factor: float = 0.95,
    elapsed_minutes: float = 18.0,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
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
    scenario = _scenario_with_overrides(
        scenario,
        None,
        None,
        furniture_overrides,
        extra_furniture=extra_furniture,
    )
    return _sample_scenario_object_point(
        scenario=scenario,
        x=x,
        y=y,
        z=z,
        use_hybrid_residual=use_hybrid_residual,
    )


def get_scenario_timeline(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    duration_minutes: float = 120.0,
    steps: int = 13,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _build_scenario_timeline(
        scenario,
        duration_minutes=duration_minutes,
        steps=steps,
        use_hybrid_residual=use_hybrid_residual,
    )


def get_window_direct_timeline(
    outdoor_temperature: float,
    outdoor_humidity: float,
    sunlight_illuminance: float,
    opening_ratio: float = 0.7,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: float = 70.0,
    daylight_factor: float = 0.95,
    elapsed_minutes: float = 18.0,
    duration_minutes: float = 120.0,
    steps: int = 13,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
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
    scenario = _scenario_with_overrides(
        scenario,
        None,
        None,
        furniture_overrides,
        extra_furniture=extra_furniture,
    )
    timeline = _build_scenario_timeline(
        scenario,
        duration_minutes=duration_minutes,
        steps=steps,
        use_hybrid_residual=use_hybrid_residual,
    )
    timeline["input"] = _window_direct_input_dict(scenario=scenario, opening_ratio=opening_ratio)
    return timeline


def _evaluate_dashboard_scenario_object(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict:
    return {
        "scenario": _evaluate_scenario_object(scenario, use_hybrid_residual=use_hybrid_residual),
        "ranking": _rank_scenario_object_actions(scenario, use_hybrid_residual=use_hybrid_residual),
        "baseline": _compare_scenario_object_baseline(scenario, use_hybrid_residual=use_hybrid_residual),
        "impacts": _learn_scenario_object_impacts(scenario, use_hybrid_residual=use_hybrid_residual),
        "volume": _get_scenario_object_volume(scenario, use_hybrid_residual=use_hybrid_residual),
        "timeline": _build_scenario_timeline(scenario, use_hybrid_residual=use_hybrid_residual),
    }


def _evaluate_scenario_object(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict:
    bundle = _build_estimation_bundle(scenario, use_hybrid_residual=use_hybrid_residual)
    model = bundle["model"]
    truth_result = bundle["truth_result"]
    observed_sensors = bundle["observed_sensors"]
    estimated_result = bundle["estimated_result"]
    estimated_field = bundle["field"]
    estimated_zone_averages = bundle["zone_averages"]
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
    before_devices = deepcopy(scenario.devices)
    for device in before_devices:
        device.activation = 0.0
    before_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=before_devices,
        furniture=scenario.furniture,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )
    before_observations = synthesize_sensor_observations(before_result.sensor_predictions, scenario.sensors)
    idw_field = build_idw_field(
        room=scenario.room,
        sensors=scenario.sensors,
        observed_sensors=observed_sensors,
        resolution=scenario.resolution,
    )
    idw_zone_averages = compute_idw_zone_averages(idw_field, scenario.zones)
    field_mae = compare_fields(estimated_field, truth_result.field)
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
        "furniture": [_furniture_dict(item) for item in scenario.furniture],
        "field_mae": field_mae,
        "idw_field_mae": idw_field_mae,
        "idw_zone_mae": compare_zone_averages(idw_zone_averages, truth_result.zone_averages),
        "baseline_comparison": compare_model_to_idw(field_mae, idw_field_mae),
        "zone_mae": compare_zone_averages(estimated_zone_averages, truth_result.zone_averages),
        "sensor_mae_before": compare_sensors(raw_nominal.sensor_predictions, observed_sensors),
        "sensor_mae_after": compare_sensors(estimated_result.sensor_predictions, observed_sensors),
        "device_power_calibration": _device_power_calibration(estimated_result.calibrated_devices),
        "learned_device_impacts": learn_active_device_impacts(
            model=model,
            room=scenario.room,
            scenario_devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            before_observations=before_observations,
            after_observations=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        ),
        "estimator": bundle["estimator"],
        "target_zone": scenario.target_zone_name,
        "target_zone_estimated": _round_metric_dict(estimated_zone_averages[scenario.target_zone_name]),
        "target_zone_truth": _round_metric_dict(truth_result.zone_averages[scenario.target_zone_name]),
        "zone_estimated": _round_zone_dict(estimated_zone_averages),
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


def run_hybrid_residual_experiment(
    include_window_matrix: bool = False,
    holdout_stride: int = 4,
    max_points_per_scenario: int = 96,
    hidden_dim: int = 10,
    epochs: int = 80,
    learning_rate: float = 0.018,
    l2: float = 1e-5,
    seed: int = 42,
) -> Dict:
    return run_hybrid_residual_experiment_backend(
        include_window_matrix=include_window_matrix,
        holdout_stride=holdout_stride,
        max_points_per_scenario=max_points_per_scenario,
        hidden_dim=hidden_dim,
        epochs=epochs,
        learning_rate=learning_rate,
        l2=l2,
        seed=seed,
    )


def get_scenario_volume(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _get_scenario_object_volume(scenario, use_hybrid_residual=use_hybrid_residual)


def rank_scenario_actions(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _rank_scenario_object_actions(scenario, use_hybrid_residual=use_hybrid_residual)


def sample_scenario_point(
    scenario_name: str,
    x: float,
    y: float,
    z: float,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _sample_scenario_object_point(scenario, x, y, z, use_hybrid_residual=use_hybrid_residual)


def compare_scenario_baseline(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _compare_scenario_object_baseline(scenario, use_hybrid_residual=use_hybrid_residual)


def learn_scenario_impacts(
    scenario_name: str,
    device_overrides: Optional[Dict[str, float]] = None,
    device_metadata_overrides: Optional[Dict[str, Dict[str, object]]] = None,
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    use_hybrid_residual: bool = False,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Dict:
    scenario = _scenario_with_overrides(
        _find_scenario(scenario_name),
        device_overrides,
        device_metadata_overrides,
        furniture_overrides,
        indoor_temperature,
        indoor_humidity,
        base_illuminance,
        elapsed_minutes,
        extra_furniture,
    )
    return _learn_scenario_object_impacts(scenario, use_hybrid_residual=use_hybrid_residual)


def _get_scenario_object_volume(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict:
    bundle = _build_estimation_bundle(scenario, use_hybrid_residual=use_hybrid_residual)
    estimated_result = bundle["estimated_result"]
    field = bundle["field"]
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
        "estimator": bundle["estimator"],
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
        "furniture": [
            _furniture_dict(item)
            for item in scenario.furniture
        ],
        "points": points,
    }


def _rank_scenario_object_actions(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict:
    bundle = _build_estimation_bundle(scenario, use_hybrid_residual=use_hybrid_residual)
    model = bundle["model"]
    estimated_result = bundle["estimated_result"]
    baseline_zone = bundle["zone_averages"][scenario.target_zone_name]
    corrections = estimated_result.corrections
    calibrated_devices = estimated_result.calibrated_devices or scenario.devices
    hybrid_model = bundle["hybrid_model"]
    baseline_score = _score_zone_values(baseline_zone, scenario.comfort_target)

    recommendations = []
    for action in scenario.candidate_actions:
        candidate_devices = apply_action(calibrated_devices, action)
        candidate = model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=candidate_devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
            corrections=corrections,
        )
        candidate_zone_averages = candidate.zone_averages
        if hybrid_model is not None:
            candidate_field = apply_hybrid_model_to_field(
                hybrid_model=hybrid_model,
                model=model,
                scenario=replace(scenario, devices=candidate_devices),
                estimated_field=candidate.field,
                calibrated_devices=candidate.calibrated_devices or candidate_devices,
            )
            candidate_zone_averages = model.compute_zone_averages(candidate_field, scenario.zones)
        candidate_zone = candidate_zone_averages[scenario.target_zone_name]
        candidate_penalty = _score_zone_values(candidate_zone, scenario.comfort_target)
        recommendations.append(
            {
                "name": action.name,
                "description": action.description,
                "improvement": round(baseline_score - candidate_penalty, 4),
                "resulting_penalty": round(candidate_penalty, 4),
                "resulting_zone_values": _round_metric_dict(candidate_zone),
            }
        )

    recommendations.sort(key=lambda item: item["improvement"], reverse=True)
    return {
        "scenario": scenario.name,
        "estimator": bundle["estimator"],
        "target_zone": scenario.target_zone_name,
        "recommendations": recommendations,
    }


def _sample_scenario_object_point(
    scenario: Scenario,
    x: float,
    y: float,
    z: float,
    use_hybrid_residual: bool = False,
) -> Dict:
    model = DigitalTwinModel()
    point = Vector3(x=x, y=y, z=z)
    _validate_point(scenario, point)
    bundle = _build_estimation_bundle(scenario, use_hybrid_residual=use_hybrid_residual)
    estimated_result = bundle["estimated_result"]
    values = model.sample_point(
        point=point,
        room=scenario.room,
        environment=scenario.environment,
        devices=estimated_result.calibrated_devices,
        furniture=scenario.furniture,
        elapsed_minutes=scenario.elapsed_minutes,
        corrections=estimated_result.corrections,
    )
    hybrid_model = bundle["hybrid_model"]
    if hybrid_model is not None:
        features = build_point_features(
            model=model,
            scenario=scenario,
            devices=estimated_result.calibrated_devices,
            point=point,
            estimated_values=values,
        )
        residuals = hybrid_model.predict(features)
        values = {
            "temperature": values["temperature"] + residuals["temperature"],
            "humidity": clamp(values["humidity"] + residuals["humidity"], 0.0, 100.0),
            "illuminance": max(0.0, values["illuminance"] + residuals["illuminance"]),
        }
    return {
        "scenario": scenario.name,
        "estimator": bundle["estimator"],
        "point": _vector_to_dict(point),
        "values": _round_metric_dict(values),
    }


def _compare_scenario_object_baseline(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict:
    bundle = _build_estimation_bundle(scenario, use_hybrid_residual=use_hybrid_residual)
    truth_result = bundle["truth_result"]
    observed_sensors = bundle["observed_sensors"]
    idw_field = build_idw_field(
        room=scenario.room,
        sensors=scenario.sensors,
        observed_sensors=observed_sensors,
        resolution=scenario.resolution,
    )
    model_mae = compare_fields(bundle["field"], truth_result.field)
    idw_mae = compare_fields(idw_field, truth_result.field)
    return {
        "scenario": scenario.name,
        "model": bundle["estimator"]["label"],
        "baseline": "inverse distance weighting",
        "estimator": bundle["estimator"],
        "comparison": compare_model_to_idw(model_mae, idw_mae),
    }


def _learn_scenario_object_impacts(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict:
    model = DigitalTwinModel()
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    before_devices = deepcopy(scenario.devices)
    for device in before_devices:
        device.activation = 0.0
    before_result = model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=before_devices,
        furniture=scenario.furniture,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )
    before_observations = synthesize_sensor_observations(before_result.sensor_predictions, scenario.sensors)
    return {
        "scenario": scenario.name,
        "description": "Learn active non-networked appliance impact coefficients from before/after sensor observations.",
        "estimator": _hybrid_estimator_status(use_hybrid_residual, _load_hybrid_residual_model() if use_hybrid_residual else None),
        "estimator_note": "Impact coefficients remain observation-driven. The hybrid residual estimator affects field reconstruction and ranking, but the coefficient fitting still uses before/after sensor deltas.",
        "learned_device_impacts": learn_active_device_impacts(
            model=model,
            room=scenario.room,
            scenario_devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            before_observations=before_observations,
            after_observations=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        ),
    }


def _score_zone_values(values: Dict[str, float], target) -> float:
    temp_penalty = _penalty(values["temperature"], target.temperature, target.temperature_tolerance)
    humidity_penalty = _penalty(values["humidity"], target.humidity, target.humidity_tolerance)
    lux_penalty = _penalty(values["illuminance"], target.illuminance, target.illuminance_tolerance)
    return (
        target.temperature_weight * temp_penalty
        + target.humidity_weight * humidity_penalty
        + target.illuminance_weight * lux_penalty
    )


def _penalty(value: float, target_value: float, tolerance: float) -> float:
    tolerance = max(tolerance, 1e-6)
    deviation = abs(value - target_value)
    if deviation <= tolerance:
        return 0.0
    return (deviation - tolerance) / tolerance


def _build_scenario_timeline(
    scenario: Scenario,
    duration_minutes: float = 120.0,
    steps: int = 13,
    use_hybrid_residual: bool = False,
) -> Dict:
    duration = max(0.0, float(duration_minutes))
    sample_count = max(2, int(steps))
    points: List[Dict] = []
    estimator = None
    for minute in _timeline_minutes(duration, sample_count):
        sampled_scenario = replace(scenario, elapsed_minutes=minute)
        bundle = _build_estimation_bundle(sampled_scenario, use_hybrid_residual=use_hybrid_residual)
        target_values = bundle["zone_averages"][sampled_scenario.target_zone_name]
        estimator = bundle["estimator"]
        points.append(
            {
                "elapsed_minutes": round(minute, 4),
                "target_zone_values": _round_metric_dict(target_values),
            }
        )
    return {
        "scenario": scenario.name,
        "target_zone": scenario.target_zone_name,
        "estimator": estimator or _hybrid_estimator_status(False, None),
        "current_elapsed_minutes": round(scenario.elapsed_minutes, 4),
        "duration_minutes": round(duration, 4),
        "steps": sample_count,
        "points": points,
    }


def _build_estimation_bundle(scenario: Scenario, use_hybrid_residual: bool = False) -> Dict[str, object]:
    model = DigitalTwinModel()
    truth_result = _simulate_truth(model, scenario)
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
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

    hybrid_model = _load_hybrid_residual_model() if use_hybrid_residual else None
    field = estimated_result.field
    zone_averages = estimated_result.zone_averages
    if hybrid_model is not None:
        field = apply_hybrid_model_to_field(
            hybrid_model=hybrid_model,
            model=model,
            scenario=scenario,
            estimated_field=estimated_result.field,
            calibrated_devices=estimated_result.calibrated_devices,
        )
        zone_averages = model.compute_zone_averages(field, scenario.zones)

    return {
        "model": model,
        "truth_result": truth_result,
        "observed_sensors": observed_sensors,
        "estimated_result": estimated_result,
        "field": field,
        "zone_averages": zone_averages,
        "hybrid_model": hybrid_model,
        "estimator": _hybrid_estimator_status(use_hybrid_residual, hybrid_model),
    }


def _load_hybrid_residual_model() -> Optional[HybridResidualModel]:
    global _HYBRID_MODEL_CACHE

    if not HYBRID_CHECKPOINT_PATH.exists():
        _HYBRID_MODEL_CACHE = {"mtime": None, "model": None}
        return None

    mtime = HYBRID_CHECKPOINT_PATH.stat().st_mtime
    if _HYBRID_MODEL_CACHE["mtime"] == mtime:
        return _HYBRID_MODEL_CACHE["model"]  # type: ignore[return-value]

    try:
        model = HybridResidualModel.load_json(str(HYBRID_CHECKPOINT_PATH))
    except (OSError, ValueError, KeyError, TypeError):
        _HYBRID_MODEL_CACHE = {"mtime": None, "model": None}
        return None

    _HYBRID_MODEL_CACHE = {"mtime": mtime, "model": model}
    return model


def _hybrid_estimator_status(requested: bool, hybrid_model: Optional[HybridResidualModel]) -> Dict[str, object]:
    applied = requested and hybrid_model is not None
    checkpoint_available = hybrid_model is not None
    if applied:
        label = "hybrid residual corrected field"
    else:
        label = "trilinear-corrected appliance influence field"
    return {
        "requested": requested,
        "applied": applied,
        "checkpoint_available": checkpoint_available,
        "checkpoint_path": str(HYBRID_CHECKPOINT_PATH) if checkpoint_available else None,
        "label": label,
    }


def _timeline_minutes(duration_minutes: float, steps: int) -> List[float]:
    if steps <= 1:
        return [0.0]
    if duration_minutes <= 0.0:
        return [0.0 for _ in range(steps)]
    interval = duration_minutes / float(steps - 1)
    return [interval * float(index) for index in range(steps)]


def _window_direct_input_dict(scenario: Scenario, opening_ratio: float) -> Dict:
    return {
        "mode": "direct",
        "opening_ratio": round(max(0.0, min(1.0, float(opening_ratio))), 4),
        "indoor_temperature": scenario.room.base_temperature,
        "indoor_humidity": scenario.room.base_humidity,
        "base_illuminance": scenario.room.base_illuminance,
        "elapsed_minutes": scenario.elapsed_minutes,
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
    furniture_overrides: Optional[Dict[str, float]] = None,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: Optional[float] = None,
    elapsed_minutes: Optional[float] = None,
    extra_furniture: Optional[List[Dict[str, object]]] = None,
) -> Scenario:
    if (
        not device_overrides
        and not device_metadata_overrides
        and not furniture_overrides
        and not extra_furniture
        and indoor_temperature is None
        and indoor_humidity is None
        and base_illuminance is None
        and elapsed_minutes is None
    ):
        return scenario
    updates = {}
    if device_overrides or device_metadata_overrides:
        devices = deepcopy(scenario.devices)
        for device in devices:
            if device_overrides and device.name in device_overrides:
                device.activation = max(0.0, min(1.0, float(device_overrides[device.name])))
            if device_metadata_overrides and device.name in device_metadata_overrides:
                device.metadata.update(deepcopy(device_metadata_overrides[device.name]))
        updates["devices"] = devices
    if furniture_overrides or extra_furniture:
        furniture = deepcopy(scenario.furniture)
        if furniture_overrides:
            for item in furniture:
                if item.name in furniture_overrides:
                    item.activation = max(0.0, min(1.0, float(furniture_overrides[item.name])))
        if extra_furniture:
            furniture.extend(_extra_furniture_from_specs(extra_furniture, scenario.room, furniture))
        updates["furniture"] = furniture
    room_updates = {}
    if indoor_temperature is not None:
        room_updates["base_temperature"] = float(indoor_temperature)
    if indoor_humidity is not None:
        room_updates["base_humidity"] = max(0.0, min(100.0, float(indoor_humidity)))
    if base_illuminance is not None:
        room_updates["base_illuminance"] = max(0.0, float(base_illuminance))
    if room_updates:
        updates["room"] = replace(scenario.room, **room_updates)
    if elapsed_minutes is not None:
        updates["elapsed_minutes"] = max(0.0, float(elapsed_minutes))
    return replace(scenario, **updates)


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
        "furniture": [
            _furniture_dict(item)
            for item in scenario.furniture
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


def _furniture_dict(item) -> Dict[str, object]:
    return {
        "name": item.name,
        "kind": item.kind,
        "activation": round(item.activation, 4),
        "min_corner": _vector_to_dict(item.min_corner),
        "max_corner": _vector_to_dict(item.max_corner),
        "center": _vector_to_dict(item.center),
        "size": _vector_to_dict(item.size),
        "metadata": deepcopy(item.metadata),
    }


def _extra_furniture_from_specs(
    specs: List[Dict[str, object]],
    room,
    existing_furniture,
) -> List[Furniture]:
    existing_names = {item.name for item in existing_furniture}
    created: List[Furniture] = []
    for index, spec in enumerate(specs):
        try:
            name = str(spec.get("name") or f"custom_furniture_{index + 1}")
            if name in existing_names:
                name = f"{name}_{index + 1}"
            min_corner = _vector_from_mapping(spec.get("min_corner"), default=Vector3(0.0, 0.0, 0.0))
            max_corner = _vector_from_mapping(spec.get("max_corner"), default=Vector3(0.8, 0.8, 0.8))
            x0 = clamp(min(min_corner.x, max_corner.x), 0.0, room.width)
            y0 = clamp(min(min_corner.y, max_corner.y), 0.0, room.length)
            z0 = clamp(min(min_corner.z, max_corner.z), 0.0, room.height)
            x1 = clamp(max(min_corner.x, max_corner.x), 0.0, room.width)
            y1 = clamp(max(min_corner.y, max_corner.y), 0.0, room.length)
            z1 = clamp(max(min_corner.z, max_corner.z), 0.0, room.height)
            if (x1 - x0) <= 1e-6 or (y1 - y0) <= 1e-6 or (z1 - z0) <= 1e-6:
                continue
            metadata = deepcopy(spec.get("metadata") or {})
            block_strength = clamp(float(metadata.get("block_strength", spec.get("block_strength", 0.3))), 0.05, 0.95)
            metadata["block_strength"] = block_strength
            metadata.setdefault("label", str(spec.get("label") or name))
            metadata.setdefault("kind", str(spec.get("kind") or "custom"))
            metadata.setdefault("window_block", block_strength)
            metadata.setdefault("light_block", min(0.98, block_strength * 1.05))
            metadata.setdefault("ac_block", max(0.05, block_strength * 0.9))
            metadata.setdefault("mixing_penalty", clamp(block_strength * 0.12, 0.01, 0.16))
            created.append(
                Furniture(
                    name=name,
                    kind=str(spec.get("kind") or metadata.get("kind") or "custom"),
                    min_corner=Vector3(x0, y0, z0),
                    max_corner=Vector3(x1, y1, z1),
                    activation=clamp(float(spec.get("activation", 1.0)), 0.0, 1.0),
                    metadata=metadata,
                )
            )
            existing_names.add(name)
        except (AttributeError, TypeError, ValueError):
            continue
    return created


def _dimension_items(keys, profiles) -> List[Dict]:
    return [{"name": key, "label": str(profiles[key]["zh"])} for key in keys]


def _simulate_truth(model: DigitalTwinModel, scenario: Scenario):
    truth_devices = apply_truth_adjustments(scenario.devices, scenario.truth_adjustments)
    return model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=truth_devices,
        furniture=scenario.furniture,
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


def _vector_from_mapping(payload, default: Vector3) -> Vector3:
    if not isinstance(payload, dict):
        return default
    try:
        return Vector3(
            x=float(payload.get("x", default.x)),
            y=float(payload.get("y", default.y)),
            z=float(payload.get("z", default.z)),
        )
    except (TypeError, ValueError):
        return default
