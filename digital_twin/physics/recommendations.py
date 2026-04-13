from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List

from digital_twin.core.entities import Action, ComfortTarget, Device, Environment, Furniture, GridResolution, Room, Sensor, Zone
from digital_twin.physics.model import DigitalTwinModel, METRICS


@dataclass(frozen=True)
class ActionScore:
    name: str
    description: str
    improvement: float
    resulting_zone_values: Dict[str, float]
    resulting_penalty: float


def apply_action(devices: List[Device], action: Action) -> List[Device]:
    updated_devices = deepcopy(devices)
    devices_by_name = {device.name: device for device in updated_devices}
    for effect in action.effects:
        device = devices_by_name.get(effect.device_name)
        if device is None:
            continue
        if effect.activation is not None:
            device.activation = effect.activation
        device.power *= effect.power_scale
        device.metadata.update(effect.metadata_updates)
    return updated_devices


def score_zone(values: Dict[str, float], target: ComfortTarget) -> float:
    temp_penalty = _penalty(values["temperature"], target.temperature, target.temperature_tolerance)
    humidity_penalty = _penalty(values["humidity"], target.humidity, target.humidity_tolerance)
    lux_penalty = _penalty(values["illuminance"], target.illuminance, target.illuminance_tolerance)
    return (
        target.temperature_weight * temp_penalty
        + target.humidity_weight * humidity_penalty
        + target.illuminance_weight * lux_penalty
    )


def rank_actions(
    model: DigitalTwinModel,
    room: Room,
    environment: Environment,
    devices: List[Device],
    furniture: List[Furniture],
    sensors: List[Sensor],
    zones: List[Zone],
    target_zone_name: str,
    target: ComfortTarget,
    actions: List[Action],
    elapsed_minutes: float,
    resolution: GridResolution,
    observed_sensors: Dict[str, Dict[str, float]],
) -> List[ActionScore]:
    baseline = model.simulate(
        room=room,
        environment=environment,
        devices=devices,
        furniture=furniture,
        sensors=sensors,
        zones=zones,
        elapsed_minutes=elapsed_minutes,
        resolution=resolution,
        observed_sensors=observed_sensors,
    )
    corrections = baseline.corrections
    calibrated_devices = baseline.calibrated_devices or devices
    baseline_zone = baseline.zone_averages[target_zone_name]
    baseline_penalty = score_zone(baseline_zone, target)

    results: List[ActionScore] = []
    for action in actions:
        candidate_devices = apply_action(calibrated_devices, action)
        candidate = model.simulate(
            room=room,
            environment=environment,
            devices=candidate_devices,
            furniture=furniture,
            sensors=sensors,
            zones=zones,
            elapsed_minutes=elapsed_minutes,
            resolution=resolution,
            corrections=corrections,
        )
        candidate_zone = candidate.zone_averages[target_zone_name]
        candidate_penalty = score_zone(candidate_zone, target)
        results.append(
            ActionScore(
                name=action.name,
                description=action.description,
                improvement=baseline_penalty - candidate_penalty,
                resulting_zone_values=candidate_zone,
                resulting_penalty=candidate_penalty,
            )
        )

    results.sort(key=lambda item: item.improvement, reverse=True)
    return results


def _penalty(value: float, target_value: float, tolerance: float) -> float:
    tolerance = max(tolerance, 1e-6)
    deviation = abs(value - target_value)
    if deviation <= tolerance:
        return 0.0
    return (deviation - tolerance) / tolerance
