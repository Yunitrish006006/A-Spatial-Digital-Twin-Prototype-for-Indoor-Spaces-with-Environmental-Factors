import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .entities import Device, Environment, GridResolution, Room, Sensor, Vector3, Zone
from .math_utils import clamp, distance, dot, normalize, solve_linear_system, spaced_values, subtract


METRICS = ("temperature", "humidity", "illuminance")


@dataclass(frozen=True)
class AffineCorrection:
    bias: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def evaluate(self, point: Vector3) -> float:
        return self.bias + self.x * point.x + self.y * point.y + self.z * point.z


@dataclass
class FieldGrid:
    resolution: GridResolution
    x_coords: List[float]
    y_coords: List[float]
    z_coords: List[float]
    values: Dict[str, List[float]] = field(default_factory=dict)

    def index(self, ix: int, iy: int, iz: int) -> int:
        return iz * self.resolution.ny * self.resolution.nx + iy * self.resolution.nx + ix

    def point(self, ix: int, iy: int, iz: int) -> Vector3:
        return Vector3(self.x_coords[ix], self.y_coords[iy], self.z_coords[iz])

    def layer_matrix(self, metric: str, z_index: int) -> List[List[float]]:
        rows: List[List[float]] = []
        for iy in range(self.resolution.ny):
            row: List[float] = []
            for ix in range(self.resolution.nx):
                row.append(self.values[metric][self.index(ix, iy, z_index)])
            rows.append(row)
        return rows

    def metric_points(self, metric: str) -> List[float]:
        return self.values[metric]


@dataclass
class SimulationResult:
    field: FieldGrid
    sensor_predictions: Dict[str, Dict[str, float]]
    zone_averages: Dict[str, Dict[str, float]]
    corrections: Dict[str, AffineCorrection]


class DigitalTwinModel:
    def simulate(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        sensors: List[Sensor],
        zones: List[Zone],
        elapsed_minutes: float,
        resolution: GridResolution,
        observed_sensors: Optional[Dict[str, Dict[str, float]]] = None,
        corrections: Optional[Dict[str, AffineCorrection]] = None,
    ) -> SimulationResult:
        if corrections is None:
            corrections = self.fit_corrections(
                room=room,
                environment=environment,
                devices=devices,
                sensors=sensors,
                observed_sensors=observed_sensors,
                elapsed_minutes=elapsed_minutes,
            )

        field = self.build_field(
            room=room,
            environment=environment,
            devices=devices,
            elapsed_minutes=elapsed_minutes,
            resolution=resolution,
            corrections=corrections,
        )
        sensor_predictions = self.predict_sensors(
            room=room,
            environment=environment,
            devices=devices,
            sensors=sensors,
            elapsed_minutes=elapsed_minutes,
            corrections=corrections,
        )
        zone_averages = self.compute_zone_averages(field, zones)
        return SimulationResult(
            field=field,
            sensor_predictions=sensor_predictions,
            zone_averages=zone_averages,
            corrections=corrections,
        )

    def fit_corrections(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        sensors: List[Sensor],
        observed_sensors: Optional[Dict[str, Dict[str, float]]],
        elapsed_minutes: float,
    ) -> Dict[str, AffineCorrection]:
        default_corrections = {metric: AffineCorrection() for metric in METRICS}
        if not observed_sensors:
            return default_corrections

        predicted = self.predict_sensors(
            room=room,
            environment=environment,
            devices=devices,
            sensors=sensors,
            elapsed_minutes=elapsed_minutes,
            corrections=default_corrections,
        )
        corrections: Dict[str, AffineCorrection] = {}
        for metric in METRICS:
            residuals: List[float] = []
            positions: List[Vector3] = []
            for sensor in sensors:
                if sensor.name not in observed_sensors:
                    continue
                residuals.append(observed_sensors[sensor.name][metric] - predicted[sensor.name][metric])
                positions.append(sensor.position)
            corrections[metric] = self._fit_affine_surface(positions, residuals)
        return corrections

    def build_field(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        elapsed_minutes: float,
        resolution: GridResolution,
        corrections: Optional[Dict[str, AffineCorrection]] = None,
    ) -> FieldGrid:
        corrections = corrections or {metric: AffineCorrection() for metric in METRICS}
        x_coords = spaced_values(room.width, resolution.nx)
        y_coords = spaced_values(room.length, resolution.ny)
        z_coords = spaced_values(room.height, resolution.nz)
        values = {metric: [] for metric in METRICS}

        for z in z_coords:
            for y in y_coords:
                for x in x_coords:
                    point = Vector3(x, y, z)
                    sample = self.sample_point(
                        point=point,
                        room=room,
                        environment=environment,
                        devices=devices,
                        elapsed_minutes=elapsed_minutes,
                        corrections=corrections,
                    )
                    for metric in METRICS:
                        values[metric].append(sample[metric])

        return FieldGrid(
            resolution=resolution,
            x_coords=x_coords,
            y_coords=y_coords,
            z_coords=z_coords,
            values=values,
        )

    def predict_sensors(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        sensors: List[Sensor],
        elapsed_minutes: float,
        corrections: Optional[Dict[str, AffineCorrection]] = None,
    ) -> Dict[str, Dict[str, float]]:
        predictions: Dict[str, Dict[str, float]] = {}
        for sensor in sensors:
            predictions[sensor.name] = self.sample_point(
                point=sensor.position,
                room=room,
                environment=environment,
                devices=devices,
                elapsed_minutes=elapsed_minutes,
                corrections=corrections,
            )
        return predictions

    def sample_point(
        self,
        point: Vector3,
        room: Room,
        environment: Environment,
        devices: List[Device],
        elapsed_minutes: float,
        corrections: Optional[Dict[str, AffineCorrection]] = None,
    ) -> Dict[str, float]:
        corrections = corrections or {metric: AffineCorrection() for metric in METRICS}
        values = self._background_field(point, room)
        for device in devices:
            delta = self._device_delta(
                point=point,
                room=room,
                environment=environment,
                device=device,
                elapsed_minutes=elapsed_minutes,
            )
            for metric in METRICS:
                values[metric] += delta[metric]

        values["temperature"] += corrections["temperature"].evaluate(point)
        values["humidity"] += corrections["humidity"].evaluate(point)
        values["illuminance"] += corrections["illuminance"].evaluate(point)

        values["humidity"] = clamp(values["humidity"], 0.0, 100.0)
        values["illuminance"] = max(0.0, values["illuminance"])
        return values

    def compute_zone_averages(self, field: FieldGrid, zones: List[Zone]) -> Dict[str, Dict[str, float]]:
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

    def _background_field(self, point: Vector3, room: Room) -> Dict[str, float]:
        normalized_height = 0.0
        if room.height > 0.0:
            normalized_height = point.z / room.height
        return {
            "temperature": room.base_temperature + 0.8 * (normalized_height - 0.5),
            "humidity": room.base_humidity - 3.0 * (normalized_height - 0.5),
            "illuminance": room.base_illuminance,
        }

    def _device_delta(
        self,
        point: Vector3,
        room: Room,
        environment: Environment,
        device: Device,
        elapsed_minutes: float,
    ) -> Dict[str, float]:
        envelope = self._influence_envelope(device, point, elapsed_minutes)
        if envelope <= 0.0:
            return {metric: 0.0 for metric in METRICS}

        if device.kind == "ac":
            cooling_delta = device.metadata.get("cooling_delta", 8.0)
            drying_delta = device.metadata.get("drying_delta", 4.0)
            return {
                "temperature": -cooling_delta * device.power * envelope,
                "humidity": -drying_delta * device.power * envelope,
                "illuminance": 0.0,
            }

        if device.kind == "window":
            thermal_exchange = device.metadata.get("thermal_exchange", 0.28)
            humidity_exchange = device.metadata.get("humidity_exchange", 0.24)
            solar_gain = device.metadata.get("solar_gain", 0.018)
            return {
                "temperature": (
                    (environment.outdoor_temperature - room.base_temperature)
                    * thermal_exchange
                    * device.power
                    * envelope
                ),
                "humidity": (
                    (environment.outdoor_humidity - room.base_humidity)
                    * humidity_exchange
                    * device.power
                    * envelope
                ),
                "illuminance": (
                    environment.sunlight_illuminance
                    * environment.daylight_factor
                    * solar_gain
                    * device.power
                    * envelope
                ),
            }

        if device.kind == "light":
            illuminance_gain = device.metadata.get("illuminance_gain", 950.0)
            heat_gain = device.metadata.get("heat_gain", 0.9)
            return {
                "temperature": heat_gain * device.power * envelope,
                "humidity": 0.0,
                "illuminance": illuminance_gain * device.power * envelope,
            }

        return {metric: 0.0 for metric in METRICS}

    def _influence_envelope(self, device: Device, point: Vector3, elapsed_minutes: float) -> float:
        dynamic_level = self._dynamic_activation(device, elapsed_minutes)
        if dynamic_level <= 0.0:
            return 0.0

        radius = max(device.influence_radius, 0.1)
        separation = distance(device.position, point)
        radial = math.exp(-separation / radius)

        orientation = normalize(device.orientation)
        direction_floor = device.metadata.get("direction_floor", 0.35)
        if orientation == Vector3(0.0, 0.0, 0.0):
            directional = 1.0
        else:
            toward_point = normalize(subtract(point, device.position))
            directional = direction_floor + (1.0 - direction_floor) * max(0.0, dot(orientation, toward_point))

        return dynamic_level * radial * directional

    def _dynamic_activation(self, device: Device, elapsed_minutes: float) -> float:
        if device.activation <= 0.0:
            return 0.0
        time_constant = max(device.response_time_minutes, 0.1)
        return device.activation * (1.0 - math.exp(-elapsed_minutes / time_constant))

    def _fit_affine_surface(self, positions: List[Vector3], residuals: List[float]) -> AffineCorrection:
        if len(positions) < 4 or len(residuals) < 4:
            return AffineCorrection()

        matrix = [[0.0 for _ in range(4)] for _ in range(4)]
        vector = [0.0 for _ in range(4)]
        for position, residual in zip(positions, residuals):
            features = [1.0, position.x, position.y, position.z]
            for i in range(4):
                vector[i] += features[i] * residual
                for j in range(4):
                    matrix[i][j] += features[i] * features[j]

        for index in range(4):
            matrix[index][index] += 1e-8

        coefficients = solve_linear_system(matrix, vector)
        return AffineCorrection(
            bias=coefficients[0],
            x=coefficients[1],
            y=coefficients[2],
            z=coefficients[3],
        )
