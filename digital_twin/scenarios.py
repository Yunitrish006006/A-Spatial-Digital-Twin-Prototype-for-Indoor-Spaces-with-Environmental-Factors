from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .entities import (
    Action,
    ActionEffect,
    ComfortTarget,
    Device,
    Environment,
    Furniture,
    GridResolution,
    Room,
    Sensor,
    Vector3,
    Zone,
    create_corner_sensors,
)
from .recommendations import apply_action


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    room: Room
    environment: Environment
    devices: List[Device]
    furniture: List[Furniture]
    sensors: List[Sensor]
    zones: List[Zone]
    resolution: GridResolution
    elapsed_minutes: float
    truth_adjustments: List[ActionEffect]
    comfort_target: ComfortTarget
    candidate_actions: List[Action]
    target_zone_name: str
    metadata: Dict[str, str] = field(default_factory=dict)


def build_standard_room() -> Room:
    return Room(
        name="standard_room",
        width=6.0,
        length=4.0,
        height=3.0,
        base_temperature=29.0,
        base_humidity=67.0,
        base_illuminance=90.0,
    )


def build_standard_zones(room: Room) -> List[Zone]:
    return [
        Zone(
            name="window_zone",
            min_corner=Vector3(0.0, 0.8, 0.0),
            max_corner=Vector3(1.8, 3.2, 2.2),
        ),
        Zone(
            name="center_zone",
            min_corner=Vector3(2.0, 1.0, 0.0),
            max_corner=Vector3(4.2, 3.0, 2.2),
        ),
        Zone(
            name="door_side_zone",
            min_corner=Vector3(4.4, 0.4, 0.0),
            max_corner=Vector3(6.0, 3.6, 2.2),
        ),
    ]


def build_standard_devices() -> List[Device]:
    return [
        Device(
            name="ac_main",
            kind="ac",
            position=Vector3(5.4, 2.0, 2.75),
            orientation=Vector3(-1.0, 0.0, -0.25),
            influence_radius=3.2,
            power=1.0,
            activation=0.0,
            response_time_minutes=12.0,
            metadata={
                "cooling_delta": 8.5,
                "drying_delta": 5.0,
                "direction_floor": 0.25,
                "surface_width": 1.35,
                "surface_height": 0.32,
                "ac_mode": "cool",
                "target_temperature": 24.0,
                "horizontal_mode": "fixed",
                "horizontal_angle_deg": 0.0,
                "horizontal_swing_range_deg": 45.0,
                "horizontal_swing_period_minutes": 0.8,
                "vertical_mode": "fixed",
                "vertical_angle_deg": 15.0,
                "vertical_swing_angles_deg": [5.0, 15.0, 25.0, 35.0],
                "vertical_swing_period_minutes": 1.2,
            },
        ),
        Device(
            name="window_main",
            kind="window",
            position=Vector3(0.0, 2.0, 1.4),
            orientation=Vector3(1.0, 0.0, 0.0),
            influence_radius=2.6,
            power=1.0,
            activation=0.0,
            response_time_minutes=2.0,
            metadata={
                "thermal_exchange": 0.35,
                "humidity_exchange": 0.26,
                "solar_gain": 0.02,
                "direction_floor": 0.2,
                "surface_width": 1.55,
                "surface_height": 1.25,
            },
        ),
        Device(
            name="light_main",
            kind="light",
            position=Vector3(3.0, 2.0, 2.85),
            orientation=Vector3(0.0, 0.0, -1.0),
            influence_radius=2.4,
            power=1.0,
            activation=0.0,
            response_time_minutes=0.5,
            metadata={"illuminance_gain": 1050.0, "heat_gain": 0.8, "direction_floor": 0.4},
        ),
    ]


def build_standard_furniture() -> List[Furniture]:
    return [
        Furniture(
            name="cabinet_window",
            kind="cabinet",
            min_corner=Vector3(0.45, 1.15, 0.0),
            max_corner=Vector3(1.2, 2.85, 2.05),
            activation=0.0,
            metadata={
                "label": "Window Cabinet",
                "block_strength": 0.46,
                "window_block": 0.58,
                "light_block": 0.52,
                "ac_block": 0.18,
                "mixing_penalty": 0.04,
            },
        ),
        Furniture(
            name="sofa_main",
            kind="sofa",
            min_corner=Vector3(2.05, 0.95, 0.0),
            max_corner=Vector3(3.75, 1.95, 1.05),
            activation=0.0,
            metadata={
                "label": "Main Sofa",
                "block_strength": 0.28,
                "window_block": 0.16,
                "light_block": 0.21,
                "ac_block": 0.34,
                "mixing_penalty": 0.08,
            },
        ),
        Furniture(
            name="table_center",
            kind="table",
            min_corner=Vector3(2.2, 1.55, 0.0),
            max_corner=Vector3(3.85, 2.75, 0.82),
            activation=0.0,
            metadata={
                "label": "Center Table",
                "block_strength": 0.2,
                "window_block": 0.12,
                "light_block": 0.18,
                "ac_block": 0.14,
                "mixing_penalty": 0.03,
            },
        ),
    ]


def build_standard_environment() -> Environment:
    return Environment(
        outdoor_temperature=33.0,
        outdoor_humidity=74.0,
        sunlight_illuminance=32000.0,
        daylight_factor=0.95,
    )


SEASON_PROFILES = {
    "spring": {
        "zh": "春季",
        "indoor_temperature": 24.0,
        "indoor_humidity": 63.0,
        "outdoor_temperature": 23.0,
        "outdoor_humidity": 68.0,
        "sunlight_illuminance": 26000.0,
    },
    "summer": {
        "zh": "夏季",
        "indoor_temperature": 29.0,
        "indoor_humidity": 70.0,
        "outdoor_temperature": 33.0,
        "outdoor_humidity": 76.0,
        "sunlight_illuminance": 36000.0,
    },
    "autumn": {
        "zh": "秋季",
        "indoor_temperature": 25.0,
        "indoor_humidity": 62.0,
        "outdoor_temperature": 26.0,
        "outdoor_humidity": 64.0,
        "sunlight_illuminance": 28000.0,
    },
    "winter": {
        "zh": "冬季",
        "indoor_temperature": 19.0,
        "indoor_humidity": 58.0,
        "outdoor_temperature": 16.0,
        "outdoor_humidity": 66.0,
        "sunlight_illuminance": 19000.0,
    },
}


WEATHER_PROFILES = {
    "cloudy": {
        "zh": "陰天",
        "temperature_delta": 0.0,
        "humidity_delta": 2.0,
        "sunlight_factor": 0.35,
    },
    "sunny": {
        "zh": "晴天",
        "temperature_delta": 2.0,
        "humidity_delta": -5.0,
        "sunlight_factor": 1.0,
    },
    "rainy": {
        "zh": "雨天",
        "temperature_delta": -2.0,
        "humidity_delta": 12.0,
        "sunlight_factor": 0.08,
    },
}


TIME_OF_DAY_PROFILES = {
    "morning": {
        "zh": "早上",
        "temperature_delta": -1.5,
        "sunlight_factor": 0.55,
    },
    "noon": {
        "zh": "中午",
        "temperature_delta": 2.0,
        "sunlight_factor": 1.0,
    },
    "afternoon": {
        "zh": "下午",
        "temperature_delta": 1.0,
        "sunlight_factor": 0.72,
    },
    "night": {
        "zh": "晚上",
        "temperature_delta": -3.0,
        "sunlight_factor": 0.01,
    },
}


WINDOW_SEASON_ORDER = ("spring", "summer", "autumn", "winter")
WINDOW_WEATHER_ORDER = ("cloudy", "sunny", "rainy")
WINDOW_TIME_ORDER = ("morning", "noon", "afternoon", "night")
HIGH_PRECISION_GRID = GridResolution(nx=16, ny=12, nz=6)


def build_high_precision_resolution() -> GridResolution:
    return HIGH_PRECISION_GRID


def build_window_matrix_room(season: str) -> Room:
    profile = SEASON_PROFILES[season]
    return Room(
        name=f"window_matrix_{season}_room",
        width=6.0,
        length=4.0,
        height=3.0,
        base_temperature=float(profile["indoor_temperature"]),
        base_humidity=float(profile["indoor_humidity"]),
        base_illuminance=70.0,
    )


def build_window_matrix_environment(season: str, weather: str, time_of_day: str) -> Environment:
    season_profile = SEASON_PROFILES[season]
    weather_profile = WEATHER_PROFILES[weather]
    time_profile = TIME_OF_DAY_PROFILES[time_of_day]

    outdoor_temperature = (
        float(season_profile["outdoor_temperature"])
        + float(weather_profile["temperature_delta"])
        + float(time_profile["temperature_delta"])
    )
    outdoor_humidity = float(season_profile["outdoor_humidity"]) + float(weather_profile["humidity_delta"])
    sunlight_illuminance = (
        float(season_profile["sunlight_illuminance"])
        * float(weather_profile["sunlight_factor"])
        * float(time_profile["sunlight_factor"])
    )

    return Environment(
        outdoor_temperature=round(outdoor_temperature, 2),
        outdoor_humidity=round(max(0.0, min(100.0, outdoor_humidity)), 2),
        sunlight_illuminance=round(sunlight_illuminance, 2),
        daylight_factor=0.95,
    )


def build_comfort_target() -> ComfortTarget:
    return ComfortTarget(
        temperature=25.0,
        temperature_tolerance=1.0,
        humidity=58.0,
        humidity_tolerance=6.0,
        illuminance=500.0,
        illuminance_tolerance=120.0,
    )


def build_candidate_actions() -> List[Action]:
    return [
        Action(
            name="turn_on_ac",
            description="開啟冷氣至 85% 出力",
            effects=[ActionEffect(device_name="ac_main", activation=0.85)],
        ),
        Action(
            name="open_window",
            description="開窗至 70% 等效開啟程度",
            effects=[ActionEffect(device_name="window_main", activation=0.7)],
        ),
        Action(
            name="turn_on_light",
            description="開啟主要照明至 80% 亮度",
            effects=[ActionEffect(device_name="light_main", activation=0.8)],
        ),
        Action(
            name="ac_and_light",
            description="同時開啟冷氣與照明",
            effects=[
                ActionEffect(device_name="ac_main", activation=0.8),
                ActionEffect(device_name="light_main", activation=0.7),
            ],
        ),
    ]


def build_validation_scenarios() -> List[Scenario]:
    room = build_standard_room()
    sensors = create_corner_sensors(room)
    zones = build_standard_zones(room)
    environment = build_standard_environment()
    comfort_target = build_comfort_target()
    resolution = build_high_precision_resolution()
    actions = build_candidate_actions()

    scenario_definitions = [
        ("idle", "無設備作用", {"ac_main": 0.0, "window_main": 0.0, "light_main": 0.0}),
        ("ac_only", "僅冷氣作用", {"ac_main": 0.8, "window_main": 0.0, "light_main": 0.0}),
        ("window_only", "僅開窗作用", {"ac_main": 0.0, "window_main": 0.7, "light_main": 0.0}),
        ("light_only", "僅照明作用", {"ac_main": 0.0, "window_main": 0.0, "light_main": 0.8}),
        ("ac_window", "冷氣與窗戶同時作用", {"ac_main": 0.75, "window_main": 0.45, "light_main": 0.0}),
        ("window_light", "窗戶與照明同時作用", {"ac_main": 0.0, "window_main": 0.55, "light_main": 0.75}),
        ("ac_light", "冷氣與照明同時作用", {"ac_main": 0.75, "window_main": 0.0, "light_main": 0.75}),
        ("all_active", "冷氣、窗戶與照明同時作用", {"ac_main": 0.75, "window_main": 0.4, "light_main": 0.7}),
    ]

    truth_adjustments = [
        ActionEffect(device_name="ac_main", power_scale=1.08),
        ActionEffect(device_name="window_main", power_scale=0.92),
        ActionEffect(device_name="light_main", power_scale=1.05),
    ]

    scenarios: List[Scenario] = []
    for name, description, activation_map in scenario_definitions:
        devices = build_standard_devices()
        for device in devices:
            if device.name in activation_map:
                device.activation = activation_map[device.name]
        scenarios.append(
            Scenario(
                name=name,
                description=description,
                room=room,
                environment=environment,
                devices=devices,
                furniture=build_standard_furniture(),
                sensors=sensors,
                zones=zones,
                resolution=resolution,
                elapsed_minutes=18.0,
                truth_adjustments=truth_adjustments,
                comfort_target=comfort_target,
                candidate_actions=actions,
                target_zone_name="center_zone",
            )
        )
    return scenarios


def build_window_matrix_scenarios() -> List[Scenario]:
    comfort_target = build_comfort_target()
    resolution = build_high_precision_resolution()
    actions = build_candidate_actions()
    truth_adjustments = [ActionEffect(device_name="window_main", power_scale=0.92)]

    scenarios: List[Scenario] = []
    for season in WINDOW_SEASON_ORDER:
        room = build_window_matrix_room(season)
        sensors = create_corner_sensors(room)
        zones = build_standard_zones(room)
        for weather in WINDOW_WEATHER_ORDER:
            for time_of_day in WINDOW_TIME_ORDER:
                devices = build_standard_devices()
                for device in devices:
                    device.activation = 0.7 if device.name == "window_main" else 0.0

                environment = build_window_matrix_environment(season, weather, time_of_day)
                season_label = str(SEASON_PROFILES[season]["zh"])
                weather_label = str(WEATHER_PROFILES[weather]["zh"])
                time_label = str(TIME_OF_DAY_PROFILES[time_of_day]["zh"])
                scenarios.append(
                    Scenario(
                        name=f"window_{season}_{weather}_{time_of_day}",
                        description=f"窗戶模擬：{season_label}／{weather_label}／{time_label}",
                        room=room,
                        environment=environment,
                        devices=devices,
                        furniture=build_standard_furniture(),
                        sensors=sensors,
                        zones=zones,
                        resolution=resolution,
                        elapsed_minutes=18.0,
                        truth_adjustments=truth_adjustments,
                        comfort_target=comfort_target,
                        candidate_actions=actions,
                        target_zone_name="window_zone",
                        metadata={
                            "category": "window_matrix",
                            "season": season,
                            "season_zh": season_label,
                            "weather": weather,
                            "weather_zh": weather_label,
                            "time_of_day": time_of_day,
                            "time_of_day_zh": time_label,
                        },
                    )
                )
    return scenarios


def build_direct_window_scenario(
    outdoor_temperature: float,
    outdoor_humidity: float,
    sunlight_illuminance: float,
    opening_ratio: float = 0.7,
    indoor_temperature: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    base_illuminance: float = 70.0,
    daylight_factor: float = 0.95,
    elapsed_minutes: float = 18.0,
) -> Scenario:
    room = build_standard_room()
    room = Room(
        name="direct_window_room",
        width=room.width,
        length=room.length,
        height=room.height,
        base_temperature=room.base_temperature if indoor_temperature is None else float(indoor_temperature),
        base_humidity=room.base_humidity if indoor_humidity is None else max(0.0, min(100.0, float(indoor_humidity))),
        base_illuminance=max(0.0, float(base_illuminance)),
    )
    sensors = create_corner_sensors(room)
    zones = build_standard_zones(room)
    devices = build_standard_devices()
    furniture = build_standard_furniture()
    activation = max(0.0, min(1.0, float(opening_ratio)))
    for device in devices:
        device.activation = activation if device.name == "window_main" else 0.0

    environment = Environment(
        outdoor_temperature=float(outdoor_temperature),
        outdoor_humidity=max(0.0, min(100.0, float(outdoor_humidity))),
        sunlight_illuminance=max(0.0, float(sunlight_illuminance)),
        daylight_factor=max(0.0, float(daylight_factor)),
    )
    return Scenario(
        name="window_direct_input",
        description="窗戶直接輸入模擬：使用外部溫度、濕度、日照與開窗比例，不經列舉矩陣。",
        room=room,
        environment=environment,
        devices=devices,
        furniture=furniture,
        sensors=sensors,
        zones=zones,
        resolution=build_high_precision_resolution(),
        elapsed_minutes=max(0.0, float(elapsed_minutes)),
        truth_adjustments=[ActionEffect(device_name="window_main", power_scale=0.92)],
        comfort_target=build_comfort_target(),
        candidate_actions=build_candidate_actions(),
        target_zone_name="window_zone",
        metadata={
            "category": "window_direct_input",
            "input_mode": "direct",
        },
    )


def apply_truth_adjustments(devices: List[Device], adjustments: List[ActionEffect]) -> List[Device]:
    action = Action(name="truth", description="truth adjustments", effects=adjustments)
    return apply_action(devices, action)
