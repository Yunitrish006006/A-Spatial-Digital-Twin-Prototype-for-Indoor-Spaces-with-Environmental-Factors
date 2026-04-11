import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .entities import Device, Environment, GridResolution, Room, Sensor, Vector3, Zone
from .math_utils import clamp, distance, dot, normalize, solve_linear_system, spaced_values, subtract


METRICS = ("temperature", "humidity", "illuminance")


@dataclass(frozen=True)
class TrilinearCorrection:
    bias: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    xy: float = 0.0
    xz: float = 0.0
    yz: float = 0.0
    xyz: float = 0.0
    room_width: float = 1.0
    room_length: float = 1.0
    room_height: float = 1.0

    def evaluate(self, point: Vector3) -> float:
        nx = clamp(point.x / max(self.room_width, 1e-9), 0.0, 1.0)
        ny = clamp(point.y / max(self.room_length, 1e-9), 0.0, 1.0)
        nz = clamp(point.z / max(self.room_height, 1e-9), 0.0, 1.0)
        return (
            self.bias
            + self.x * nx
            + self.y * ny
            + self.z * nz
            + self.xy * nx * ny
            + self.xz * nx * nz
            + self.yz * ny * nz
            + self.xyz * nx * ny * nz
        )


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
    corrections: Dict[str, TrilinearCorrection]
    calibrated_devices: List[Device] = field(default_factory=list)


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
        corrections: Optional[Dict[str, TrilinearCorrection]] = None,
    ) -> SimulationResult:
        calibrated_devices = devices
        if observed_sensors and corrections is None:
            calibrated_devices = self.calibrate_active_device_powers(
                room=room,
                environment=environment,
                devices=devices,
                sensors=sensors,
                observed_sensors=observed_sensors,
                elapsed_minutes=elapsed_minutes,
            )
        if corrections is None:
            corrections = self.fit_corrections(
                room=room,
                environment=environment,
                devices=calibrated_devices,
                sensors=sensors,
                observed_sensors=observed_sensors,
                elapsed_minutes=elapsed_minutes,
            )

        field = self.build_field(
            room=room,
            environment=environment,
            devices=calibrated_devices,
            elapsed_minutes=elapsed_minutes,
            resolution=resolution,
            corrections=corrections,
        )
        sensor_predictions = self.predict_sensors(
            room=room,
            environment=environment,
            devices=calibrated_devices,
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
            calibrated_devices=calibrated_devices,
        )

    def calibrate_active_device_powers(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        sensors: List[Sensor],
        observed_sensors: Dict[str, Dict[str, float]],
        elapsed_minutes: float,
    ) -> List[Device]:
        active_devices = [device for device in devices if device.activation > 0.0 and device.power > 0.0]
        if not active_devices:
            return devices

        default_corrections = {metric: TrilinearCorrection() for metric in METRICS}
        predicted = self.predict_sensors(
            room=room,
            environment=environment,
            devices=devices,
            sensors=sensors,
            elapsed_minutes=elapsed_minutes,
            corrections=default_corrections,
        )
        rows: List[List[float]] = []
        targets: List[float] = []
        for sensor in sensors:
            if sensor.name not in observed_sensors:
                continue
            for metric in METRICS:
                row = [
                    self._device_delta(
                        point=sensor.position,
                        room=room,
                        environment=environment,
                        device=device,
                        elapsed_minutes=elapsed_minutes,
                    )[metric]
                    for device in active_devices
                ]
                if max((abs(value) for value in row), default=0.0) <= 1e-9:
                    continue
                rows.append(row)
                targets.append(observed_sensors[sensor.name][metric] - predicted[sensor.name][metric])

        if not rows:
            return devices

        count = len(active_devices)
        matrix = [[0.0 for _ in range(count)] for _ in range(count)]
        vector = [0.0 for _ in range(count)]
        for row, target in zip(rows, targets):
            for i in range(count):
                vector[i] += row[i] * target
                for j in range(count):
                    matrix[i][j] += row[i] * row[j]

        for index in range(count):
            matrix[index][index] += 1e-6

        delta_scales = solve_linear_system(matrix, vector)
        calibrated = deepcopy(devices)
        calibrated_by_name = {device.name: device for device in calibrated}
        for device, delta_scale in zip(active_devices, delta_scales):
            calibrated_device = calibrated_by_name[device.name]
            scale = clamp(1.0 + 0.65 * delta_scale, 0.25, 1.75)
            calibrated_device.power *= scale
            calibrated_device.metadata["calibrated_power_scale"] = scale
        return calibrated

    def fit_corrections(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        sensors: List[Sensor],
        observed_sensors: Optional[Dict[str, Dict[str, float]]],
        elapsed_minutes: float,
    ) -> Dict[str, TrilinearCorrection]:
        default_corrections = {metric: TrilinearCorrection() for metric in METRICS}
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
        corrections: Dict[str, TrilinearCorrection] = {}
        for metric in METRICS:
            residuals: List[float] = []
            positions: List[Vector3] = []
            for sensor in sensors:
                if sensor.name not in observed_sensors:
                    continue
                residuals.append(observed_sensors[sensor.name][metric] - predicted[sensor.name][metric])
                positions.append(sensor.position)
            corrections[metric] = self._fit_trilinear_correction(room, positions, residuals)
        return corrections

    def build_field(
        self,
        room: Room,
        environment: Environment,
        devices: List[Device],
        elapsed_minutes: float,
        resolution: GridResolution,
        corrections: Optional[Dict[str, TrilinearCorrection]] = None,
    ) -> FieldGrid:
        corrections = corrections or {metric: TrilinearCorrection() for metric in METRICS}
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
        corrections: Optional[Dict[str, TrilinearCorrection]] = None,
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
        corrections: Optional[Dict[str, TrilinearCorrection]] = None,
    ) -> Dict[str, float]:
        corrections = corrections or {metric: TrilinearCorrection() for metric in METRICS}
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
            return self._ac_delta(point, room, environment, device, envelope)

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
        return self.influence_envelope(device, point, elapsed_minutes)

    def influence_envelope(self, device: Device, point: Vector3, elapsed_minutes: float) -> float:
        dynamic_level = self._dynamic_activation(device, elapsed_minutes)
        if dynamic_level <= 0.0:
            return 0.0

        radius = max(device.influence_radius, 0.1)
        separation = distance(device.position, point)
        radial = math.exp(-separation / radius)

        orientation = normalize(self._effective_device_orientation(device, elapsed_minutes))
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

    def _ac_delta(
        self,
        point: Vector3,
        room: Room,
        environment: Environment,
        device: Device,
        envelope: float,
    ) -> Dict[str, float]:
        mode = str(device.metadata.get("ac_mode", "cool")).lower()
        setpoint = clamp(float(device.metadata.get("target_temperature", 24.0)), 20.0, 33.0)
        cooling_delta = float(device.metadata.get("cooling_delta", 8.0))
        drying_delta = float(device.metadata.get("drying_delta", 4.0))
        if mode == "dry":
            demand = clamp((room.base_temperature - setpoint + 2.0) / 10.0, 0.15, 1.0)
            return {
                "temperature": -0.52 * cooling_delta * demand * device.power * envelope,
                "humidity": -1.35 * drying_delta * demand * device.power * envelope,
                "illuminance": 0.0,
            }
        if mode == "heat":
            demand = clamp((setpoint - room.base_temperature + 3.0) / 12.0, 0.0, 1.0)
            return {
                "temperature": 0.92 * cooling_delta * demand * device.power * envelope,
                "humidity": -0.32 * drying_delta * max(demand, 0.2) * device.power * envelope,
                "illuminance": 0.0,
            }
        if mode == "fan":
            normalized_height = 0.0 if room.height <= 0.0 else (point.z / room.height) - 0.5
            return {
                "temperature": -0.42 * normalized_height * device.power * envelope,
                "humidity": 1.45 * normalized_height * device.power * envelope,
                "illuminance": 0.0,
            }

        demand = clamp((room.base_temperature - setpoint + 3.0) / 12.0, 0.05, 1.0)
        return {
            "temperature": -cooling_delta * demand * device.power * envelope,
            "humidity": -drying_delta * (0.55 + 0.45 * demand) * device.power * envelope,
            "illuminance": 0.0,
        }

    def _effective_device_orientation(self, device: Device, elapsed_minutes: float) -> Vector3:
        if device.kind != "ac":
            return device.orientation
        horizontal_angle = self._ac_horizontal_angle(device, elapsed_minutes)
        vertical_angle = self._ac_vertical_angle(device, elapsed_minutes)
        return self._ac_orientation_from_angles(horizontal_angle, vertical_angle)

    def _ac_horizontal_angle(self, device: Device, elapsed_minutes: float) -> float:
        mode = str(device.metadata.get("horizontal_mode", "fixed")).lower()
        fixed_angle = float(device.metadata.get("horizontal_angle_deg", 0.0))
        if mode != "swing":
            return clamp(fixed_angle, -60.0, 60.0)
        swing_range = clamp(float(device.metadata.get("horizontal_swing_range_deg", 45.0)), 5.0, 60.0)
        period = max(float(device.metadata.get("horizontal_swing_period_minutes", 0.8)), 0.1)
        return swing_range * math.sin((2.0 * math.pi * elapsed_minutes) / period)

    def _ac_vertical_angle(self, device: Device, elapsed_minutes: float) -> float:
        mode = str(device.metadata.get("vertical_mode", "fixed")).lower()
        fixed_angle = float(device.metadata.get("vertical_angle_deg", 15.0))
        if mode != "swing":
            return clamp(fixed_angle, 0.0, 40.0)
        raw_angles = device.metadata.get("vertical_swing_angles_deg", [5.0, 15.0, 25.0, 35.0])
        angles = [clamp(float(angle), 0.0, 40.0) for angle in raw_angles] if isinstance(raw_angles, list) else [5.0, 15.0, 25.0, 35.0]
        if not angles:
            angles = [15.0]
        period = max(float(device.metadata.get("vertical_swing_period_minutes", 1.2)), 0.1)
        segment = period / float(len(angles))
        index = int((elapsed_minutes % period) / segment) % len(angles)
        return angles[index]

    def _ac_orientation_from_angles(self, horizontal_angle_deg: float, vertical_angle_deg: float) -> Vector3:
        horizontal = math.radians(clamp(horizontal_angle_deg, -60.0, 60.0))
        vertical = math.radians(clamp(vertical_angle_deg, 0.0, 40.0))
        return Vector3(
            x=-math.cos(vertical) * math.cos(horizontal),
            y=math.sin(horizontal) * math.cos(vertical),
            z=-math.sin(vertical),
        )

    def _fit_trilinear_correction(
        self,
        room: Room,
        positions: List[Vector3],
        residuals: List[float],
    ) -> TrilinearCorrection:
        if len(positions) < 4 or len(residuals) < 4:
            return TrilinearCorrection()

        feature_count = 8 if len(positions) >= 8 and len(residuals) >= 8 else 4
        matrix = [[0.0 for _ in range(feature_count)] for _ in range(feature_count)]
        vector = [0.0 for _ in range(feature_count)]
        for position, residual in zip(positions, residuals):
            features = self._correction_features(room, position, feature_count)
            for i in range(feature_count):
                vector[i] += features[i] * residual
                for j in range(feature_count):
                    matrix[i][j] += features[i] * features[j]

        for index in range(feature_count):
            matrix[index][index] += 1e-8

        coefficients = solve_linear_system(matrix, vector)
        padded = coefficients + [0.0] * (8 - len(coefficients))
        return TrilinearCorrection(
            bias=padded[0],
            x=padded[1],
            y=padded[2],
            z=padded[3],
            xy=padded[4],
            xz=padded[5],
            yz=padded[6],
            xyz=padded[7],
            room_width=room.width,
            room_length=room.length,
            room_height=room.height,
        )

    def _correction_features(self, room: Room, point: Vector3, feature_count: int) -> List[float]:
        nx = clamp(point.x / max(room.width, 1e-9), 0.0, 1.0)
        ny = clamp(point.y / max(room.length, 1e-9), 0.0, 1.0)
        nz = clamp(point.z / max(room.height, 1e-9), 0.0, 1.0)
        features = [1.0, nx, ny, nz, nx * ny, nx * nz, ny * nz, nx * ny * nz]
        return features[:feature_count]
