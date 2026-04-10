from typing import Dict, List

from .entities import GridResolution, Room, Sensor, Vector3, Zone
from .math_utils import distance, spaced_values
from .model import FieldGrid, METRICS


def build_idw_field(
    room: Room,
    sensors: List[Sensor],
    observed_sensors: Dict[str, Dict[str, float]],
    resolution: GridResolution,
    power: float = 2.0,
    epsilon: float = 1e-6,
) -> FieldGrid:
    x_coords = spaced_values(room.width, resolution.nx)
    y_coords = spaced_values(room.length, resolution.ny)
    z_coords = spaced_values(room.height, resolution.nz)
    values = {metric: [] for metric in METRICS}

    for z in z_coords:
        for y in y_coords:
            for x in x_coords:
                point = Vector3(x, y, z)
                sample = sample_idw_point(point, sensors, observed_sensors, power=power, epsilon=epsilon)
                for metric in METRICS:
                    values[metric].append(sample[metric])

    return FieldGrid(
        resolution=resolution,
        x_coords=x_coords,
        y_coords=y_coords,
        z_coords=z_coords,
        values=values,
    )


def sample_idw_point(
    point: Vector3,
    sensors: List[Sensor],
    observed_sensors: Dict[str, Dict[str, float]],
    power: float = 2.0,
    epsilon: float = 1e-6,
) -> Dict[str, float]:
    for sensor in sensors:
        if distance(point, sensor.position) <= epsilon and sensor.name in observed_sensors:
            return {metric: observed_sensors[sensor.name][metric] for metric in METRICS}

    weighted = {metric: 0.0 for metric in METRICS}
    total_weight = 0.0
    for sensor in sensors:
        if sensor.name not in observed_sensors:
            continue
        separation = max(distance(point, sensor.position), epsilon)
        weight = 1.0 / (separation**power)
        total_weight += weight
        for metric in METRICS:
            weighted[metric] += observed_sensors[sensor.name][metric] * weight

    if total_weight <= 0.0:
        return {metric: 0.0 for metric in METRICS}
    return {metric: weighted[metric] / total_weight for metric in METRICS}


def compute_zone_averages(field: FieldGrid, zones: List[Zone]) -> Dict[str, Dict[str, float]]:
    zone_values: Dict[str, Dict[str, float]] = {}
    for zone in zones:
        collected = {metric: [] for metric in METRICS}
        for iz in range(field.resolution.nz):
            for iy in range(field.resolution.ny):
                for ix in range(field.resolution.nx):
                    point = field.point(ix, iy, iz)
                    if not zone.contains(point):
                        continue
                    index = field.index(ix, iy, iz)
                    for metric in METRICS:
                        collected[metric].append(field.values[metric][index])
        zone_values[zone.name] = {}
        for metric in METRICS:
            if collected[metric]:
                zone_values[zone.name][metric] = sum(collected[metric]) / float(len(collected[metric]))
            else:
                zone_values[zone.name][metric] = 0.0
    return zone_values
