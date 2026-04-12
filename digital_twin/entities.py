from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Room:
    name: str
    width: float
    length: float
    height: float
    base_temperature: float
    base_humidity: float
    base_illuminance: float


@dataclass(frozen=True)
class Environment:
    outdoor_temperature: float
    outdoor_humidity: float
    sunlight_illuminance: float
    daylight_factor: float = 1.0


@dataclass(frozen=True)
class Zone:
    name: str
    min_corner: Vector3
    max_corner: Vector3

    def contains(self, point: Vector3) -> bool:
        return (
            self.min_corner.x <= point.x <= self.max_corner.x
            and self.min_corner.y <= point.y <= self.max_corner.y
            and self.min_corner.z <= point.z <= self.max_corner.z
        )


@dataclass(frozen=True)
class Sensor:
    name: str
    position: Vector3


@dataclass
class Device:
    name: str
    kind: str
    position: Vector3
    orientation: Vector3
    influence_radius: float
    power: float = 1.0
    activation: float = 0.0
    response_time_minutes: float = 5.0
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class Furniture:
    name: str
    kind: str
    min_corner: Vector3
    max_corner: Vector3
    activation: float = 0.0
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def center(self) -> Vector3:
        return Vector3(
            x=(self.min_corner.x + self.max_corner.x) / 2.0,
            y=(self.min_corner.y + self.max_corner.y) / 2.0,
            z=(self.min_corner.z + self.max_corner.z) / 2.0,
        )

    @property
    def size(self) -> Vector3:
        return Vector3(
            x=max(0.0, self.max_corner.x - self.min_corner.x),
            y=max(0.0, self.max_corner.y - self.min_corner.y),
            z=max(0.0, self.max_corner.z - self.min_corner.z),
        )


@dataclass(frozen=True)
class GridResolution:
    nx: int
    ny: int
    nz: int


@dataclass(frozen=True)
class ComfortTarget:
    temperature: float
    temperature_tolerance: float
    humidity: float
    humidity_tolerance: float
    illuminance: float
    illuminance_tolerance: float
    temperature_weight: float = 1.0
    humidity_weight: float = 0.45
    illuminance_weight: float = 0.9


@dataclass(frozen=True)
class ActionEffect:
    device_name: str
    activation: Optional[float] = None
    power_scale: float = 1.0
    metadata_updates: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    name: str
    description: str
    effects: List[ActionEffect]


def create_corner_sensors(room: Room) -> List[Sensor]:
    corners = [
        ("floor_sw", Vector3(0.0, 0.0, 0.0)),
        ("floor_se", Vector3(room.width, 0.0, 0.0)),
        ("floor_nw", Vector3(0.0, room.length, 0.0)),
        ("floor_ne", Vector3(room.width, room.length, 0.0)),
        ("ceiling_sw", Vector3(0.0, 0.0, room.height)),
        ("ceiling_se", Vector3(room.width, 0.0, room.height)),
        ("ceiling_nw", Vector3(0.0, room.length, room.height)),
        ("ceiling_ne", Vector3(room.width, room.length, room.height)),
    ]
    return [Sensor(name=name, position=position) for name, position in corners]
