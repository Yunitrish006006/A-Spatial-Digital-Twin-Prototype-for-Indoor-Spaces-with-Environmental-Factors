import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from digital_twin.baselines import build_idw_field
from digital_twin.demo import compare_sensors, synthesize_sensor_observations
from digital_twin.learning import learn_device_impact_from_sensor_delta
from digital_twin.model import DigitalTwinModel
from digital_twin.recommendations import rank_actions
from digital_twin.render import export_svg_volume_heatmap
from digital_twin.scenarios import (
    apply_truth_adjustments,
    build_candidate_actions,
    build_comfort_target,
    build_direct_window_scenario,
    build_standard_devices,
    build_standard_environment,
    build_standard_furniture,
    build_standard_room,
    build_standard_zones,
    build_window_matrix_scenarios,
)
from digital_twin.entities import ComfortTarget, Furniture, GridResolution, Vector3, create_corner_sensors


class DigitalTwinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = DigitalTwinModel()
        self.room = build_standard_room()
        self.environment = build_standard_environment()
        self.devices = build_standard_devices()
        self.furniture = build_standard_furniture()
        self.sensors = create_corner_sensors(self.room)
        self.zones = build_standard_zones(self.room)
        self.resolution = GridResolution(nx=10, ny=8, nz=4)
        self.elapsed_minutes = 18.0

    def test_idle_state_stays_near_baseline(self) -> None:
        result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        center = result.zone_averages["center_zone"]
        self.assertAlmostEqual(center["temperature"], self.room.base_temperature, delta=1.0)
        self.assertAlmostEqual(center["humidity"], self.room.base_humidity, delta=3.0)
        self.assertGreaterEqual(center["illuminance"], self.room.base_illuminance)

    def test_ac_lowers_center_temperature(self) -> None:
        off_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        devices = build_standard_devices()
        for device in devices:
            if device.name == "ac_main":
                device.activation = 0.85
        on_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        self.assertLess(
            on_result.zone_averages["center_zone"]["temperature"],
            off_result.zone_averages["center_zone"]["temperature"],
        )

    def test_ac_cools_whole_room_after_two_hours_in_hot_start(self) -> None:
        hot_room = replace(self.room, base_temperature=34.0)
        devices = build_standard_devices()
        ac_device = next(device for device in devices if device.name == "ac_main")
        ac_device.activation = 0.8
        ac_device.metadata.update({"ac_mode": "cool", "target_temperature": 24.0})

        result = self.model.simulate(
            room=hot_room,
            environment=self.environment,
            devices=devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=120.0,
            resolution=self.resolution,
        )
        self.assertLess(max(result.field.values["temperature"]), 31.0)
        self.assertLess(result.zone_averages["center_zone"]["temperature"], 30.0)

    def test_ac_heat_mode_raises_temperature_relative_to_cool_mode(self) -> None:
        point = Vector3(3.9, 2.0, 1.5)
        cool_devices = build_standard_devices()
        cool_ac = next(device for device in cool_devices if device.name == "ac_main")
        cool_ac.activation = 0.85
        cool_ac.metadata.update({"ac_mode": "cool", "target_temperature": 20.0})
        heat_devices = build_standard_devices()
        heat_ac = next(device for device in heat_devices if device.name == "ac_main")
        heat_ac.activation = 0.85
        heat_ac.metadata.update({"ac_mode": "heat", "target_temperature": 33.0})

        cool_values = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=cool_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        heat_values = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=heat_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        self.assertLess(cool_values["temperature"], heat_values["temperature"])

    def test_ac_dry_mode_reduces_humidity_more_than_cool_mode(self) -> None:
        point = Vector3(3.9, 2.0, 1.5)
        cool_devices = build_standard_devices()
        cool_ac = next(device for device in cool_devices if device.name == "ac_main")
        cool_ac.activation = 0.85
        cool_ac.metadata.update({"ac_mode": "cool", "target_temperature": 24.0})
        dry_devices = build_standard_devices()
        dry_ac = next(device for device in dry_devices if device.name == "ac_main")
        dry_ac.activation = 0.85
        dry_ac.metadata.update({"ac_mode": "dry", "target_temperature": 24.0})

        cool_values = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=cool_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        dry_values = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=dry_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        self.assertLess(dry_values["humidity"], cool_values["humidity"])

    def test_ac_horizontal_angle_biases_lateral_cooling(self) -> None:
        north_point = Vector3(4.0, 3.1, 1.4)
        south_point = Vector3(4.0, 0.9, 1.4)

        right_devices = build_standard_devices()
        right_ac = next(device for device in right_devices if device.name == "ac_main")
        right_ac.activation = 0.85
        right_ac.metadata.update({"ac_mode": "cool", "horizontal_mode": "fixed", "horizontal_angle_deg": 45.0})

        left_devices = build_standard_devices()
        left_ac = next(device for device in left_devices if device.name == "ac_main")
        left_ac.activation = 0.85
        left_ac.metadata.update({"ac_mode": "cool", "horizontal_mode": "fixed", "horizontal_angle_deg": -45.0})

        right_north = self.model.sample_point(
            point=north_point,
            room=self.room,
            environment=self.environment,
            devices=right_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        right_south = self.model.sample_point(
            point=south_point,
            room=self.room,
            environment=self.environment,
            devices=right_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        left_north = self.model.sample_point(
            point=north_point,
            room=self.room,
            environment=self.environment,
            devices=left_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        left_south = self.model.sample_point(
            point=south_point,
            room=self.room,
            environment=self.environment,
            devices=left_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        self.assertLess(right_north["temperature"], right_south["temperature"])
        self.assertLess(left_south["temperature"], left_north["temperature"])

    def test_ac_vertical_angle_biases_downward_cooling(self) -> None:
        low_point = Vector3(4.0, 2.0, 0.6)
        high_point = Vector3(4.0, 2.0, 2.3)

        shallow_devices = build_standard_devices()
        shallow_ac = next(device for device in shallow_devices if device.name == "ac_main")
        shallow_ac.activation = 0.85
        shallow_ac.metadata.update({"ac_mode": "cool", "vertical_mode": "fixed", "vertical_angle_deg": 5.0})

        steep_devices = build_standard_devices()
        steep_ac = next(device for device in steep_devices if device.name == "ac_main")
        steep_ac.activation = 0.85
        steep_ac.metadata.update({"ac_mode": "cool", "vertical_mode": "fixed", "vertical_angle_deg": 35.0})

        shallow_low = self.model.sample_point(
            point=low_point,
            room=self.room,
            environment=self.environment,
            devices=shallow_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        shallow_high = self.model.sample_point(
            point=high_point,
            room=self.room,
            environment=self.environment,
            devices=shallow_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        steep_low = self.model.sample_point(
            point=low_point,
            room=self.room,
            environment=self.environment,
            devices=steep_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        steep_high = self.model.sample_point(
            point=high_point,
            room=self.room,
            environment=self.environment,
            devices=steep_devices,
            furniture=self.furniture,
            elapsed_minutes=self.elapsed_minutes,
        )
        self.assertLess(steep_low["temperature"], shallow_low["temperature"])
        self.assertGreater(steep_high["temperature"], shallow_high["temperature"])

    def test_light_increases_center_illuminance(self) -> None:
        off_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        devices = build_standard_devices()
        for device in devices:
            if device.name == "light_main":
                device.activation = 0.8
        on_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        self.assertGreater(
            on_result.zone_averages["center_zone"]["illuminance"],
            off_result.zone_averages["center_zone"]["illuminance"],
        )

    def test_window_cabinet_blocks_window_heat_and_daylight(self) -> None:
        point = Vector3(1.5, 2.0, 1.4)
        devices = build_standard_devices()
        window = next(device for device in devices if device.name == "window_main")
        window.activation = 0.8
        cabinet = next(item for item in self.furniture if item.name == "cabinet_window")
        cabinet.activation = 1.0

        open_path = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=[],
            elapsed_minutes=30.0,
        )
        blocked_path = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=self.furniture,
            elapsed_minutes=30.0,
        )
        self.assertLess(blocked_path["illuminance"], open_path["illuminance"])
        self.assertLess(blocked_path["temperature"], open_path["temperature"])

    def test_sofa_blocks_ac_cooling_path(self) -> None:
        point = Vector3(3.5, 1.5, 0.9)
        devices = build_standard_devices()
        ac = next(device for device in devices if device.name == "ac_main")
        ac.activation = 0.85
        sofa = next(item for item in self.furniture if item.name == "sofa_main")
        sofa.activation = 1.0

        open_path = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=[],
            elapsed_minutes=45.0,
        )
        blocked_path = self.model.sample_point(
            point=point,
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=self.furniture,
            elapsed_minutes=45.0,
        )
        self.assertGreater(blocked_path["temperature"], open_path["temperature"])
        self.assertGreater(blocked_path["humidity"], open_path["humidity"])

    def test_taller_partition_blocks_cross_room_transfer_more_than_low_divider(self) -> None:
        devices = build_standard_devices()
        for device in devices:
            if device.name == "ac_main":
                device.activation = 0.85
                device.metadata.update({"ac_mode": "cool", "target_temperature": 24.0})
            elif device.name == "window_main":
                device.activation = 0.75
            elif device.name == "light_main":
                device.activation = 0.0

        low_divider = Furniture(
            name="low_divider",
            kind="partition",
            min_corner=Vector3(2.75, 0.2, 0.0),
            max_corner=Vector3(3.05, 3.8, 1.0),
            activation=1.0,
            metadata={"block_strength": 0.9, "ac_block": 0.9, "window_block": 0.9, "light_block": 0.9},
        )
        tall_partition = Furniture(
            name="tall_partition",
            kind="partition",
            min_corner=Vector3(2.75, 0.0, 0.0),
            max_corner=Vector3(3.05, 4.0, 2.85),
            activation=1.0,
            metadata={"block_strength": 0.9, "ac_block": 0.9, "window_block": 0.9, "light_block": 0.9},
        )

        low_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=[low_divider],
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=45.0,
            resolution=self.resolution,
        )
        tall_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=[tall_partition],
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=45.0,
            resolution=self.resolution,
        )
        self.assertGreater(
            tall_result.zone_averages["window_zone"]["temperature"],
            low_result.zone_averages["window_zone"]["temperature"],
        )

    def test_off_path_partition_blocks_less_than_center_partition(self) -> None:
        devices = build_standard_devices()
        for device in devices:
            if device.name == "ac_main":
                device.activation = 0.85
                device.metadata.update({"ac_mode": "cool", "target_temperature": 24.0})
            elif device.name == "window_main":
                device.activation = 0.75
            elif device.name == "light_main":
                device.activation = 0.0

        center_partition = Furniture(
            name="center_partition",
            kind="partition",
            min_corner=Vector3(2.75, 0.0, 0.0),
            max_corner=Vector3(3.05, 4.0, 2.85),
            activation=1.0,
            metadata={"block_strength": 0.9, "ac_block": 0.9, "window_block": 0.9, "light_block": 0.9},
        )
        edge_partition = Furniture(
            name="edge_partition",
            kind="partition",
            min_corner=Vector3(2.75, 0.0, 0.0),
            max_corner=Vector3(3.05, 1.0, 2.85),
            activation=1.0,
            metadata={"block_strength": 0.9, "ac_block": 0.9, "window_block": 0.9, "light_block": 0.9},
        )

        center_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=[center_partition],
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=45.0,
            resolution=self.resolution,
        )
        edge_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=[edge_partition],
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=45.0,
            resolution=self.resolution,
        )
        self.assertGreater(
            center_result.zone_averages["window_zone"]["temperature"],
            edge_result.zone_averages["window_zone"]["temperature"],
        )

    def test_sensor_calibration_reduces_sensor_error(self) -> None:
        truth_devices = apply_truth_adjustments(
            self.devices,
            [
                build_candidate_actions()[0].effects[0],
            ],
        )
        truth_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=truth_devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        observed = synthesize_sensor_observations(truth_result.sensor_predictions, self.sensors)
        before = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        after = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
            observed_sensors=observed,
        )
        mae_before = compare_sensors(before.sensor_predictions, observed)
        mae_after = compare_sensors(after.sensor_predictions, observed)
        self.assertLess(mae_after["temperature"], mae_before["temperature"])
        self.assertLess(mae_after["humidity"], mae_before["humidity"])
        self.assertLess(mae_after["illuminance"], mae_before["illuminance"])

    def test_trilinear_sensor_calibration_uses_corner_residuals(self) -> None:
        truth_devices = apply_truth_adjustments(
            self.devices,
            [
                build_candidate_actions()[0].effects[0],
                build_candidate_actions()[2].effects[0],
            ],
        )
        truth_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=truth_devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        observed = synthesize_sensor_observations(truth_result.sensor_predictions, self.sensors)
        after = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
            observed_sensors=observed,
        )
        mae_after = compare_sensors(after.sensor_predictions, observed)
        self.assertLess(mae_after["temperature"], 1e-5)
        self.assertLess(mae_after["humidity"], 1e-5)
        self.assertLess(mae_after["illuminance"], 1e-5)
        correction = after.corrections["temperature"]
        self.assertTrue(
            any(abs(value) > 1e-9 for value in [correction.xy, correction.xz, correction.yz, correction.xyz])
        )

    def test_idw_baseline_builds_field(self) -> None:
        observed = self.model.predict_sensors(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            elapsed_minutes=self.elapsed_minutes,
        )
        field = build_idw_field(self.room, self.sensors, observed, self.resolution)
        self.assertEqual(len(field.values["temperature"]), self.resolution.nx * self.resolution.ny * self.resolution.nz)
        self.assertGreater(field.values["humidity"][0], 0.0)

    def test_learn_device_impact_from_sensor_delta(self) -> None:
        before = self.model.predict_sensors(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            elapsed_minutes=self.elapsed_minutes,
        )
        devices = build_standard_devices()
        ac_device = next(device for device in devices if device.name == "ac_main")
        ac_device.activation = 0.85
        after = self.model.predict_sensors(
            room=self.room,
            environment=self.environment,
            devices=devices,
            furniture=self.furniture,
            sensors=self.sensors,
            elapsed_minutes=self.elapsed_minutes,
        )
        learned = learn_device_impact_from_sensor_delta(
            model=self.model,
            device=ac_device,
            room=self.room,
            furniture=self.furniture,
            sensors=self.sensors,
            before_observations=before,
            after_observations=after,
            elapsed_minutes=self.elapsed_minutes,
        )
        self.assertLess(learned.metric_coefficients["temperature"], 0.0)
        self.assertLess(learned.metric_coefficients["humidity"], 0.0)
        self.assertAlmostEqual(learned.metric_coefficients["illuminance"], 0.0, delta=1e-6)

    def test_recommendations_prioritize_ac_in_hot_room(self) -> None:
        comfort = ComfortTarget(
            temperature=25.0,
            temperature_tolerance=1.0,
            humidity=58.0,
            humidity_tolerance=6.0,
            illuminance=120.0,
            illuminance_tolerance=80.0,
            temperature_weight=1.1,
            humidity_weight=0.4,
            illuminance_weight=0.1,
        )
        actions = build_candidate_actions()
        recommendations = rank_actions(
            model=self.model,
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            target_zone_name="center_zone",
            target=comfort,
            actions=actions,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
            observed_sensors=self.model.predict_sensors(
                room=self.room,
                environment=self.environment,
                devices=self.devices,
                furniture=self.furniture,
                sensors=self.sensors,
                elapsed_minutes=self.elapsed_minutes,
            ),
        )
        self.assertEqual(recommendations[0].name, "turn_on_ac")

    def test_window_matrix_builds_48_time_weather_season_cases(self) -> None:
        scenarios = build_window_matrix_scenarios()
        names = {scenario.name for scenario in scenarios}
        self.assertEqual(len(scenarios), 48)
        self.assertIn("window_summer_sunny_noon", names)
        self.assertIn("window_winter_rainy_night", names)

    def test_window_matrix_environment_profiles_are_ordered(self) -> None:
        scenarios = {scenario.name: scenario for scenario in build_window_matrix_scenarios()}
        sunny_noon = scenarios["window_summer_sunny_noon"]
        rainy_night = scenarios["window_winter_rainy_night"]
        self.assertGreater(sunny_noon.environment.sunlight_illuminance, rainy_night.environment.sunlight_illuminance)
        self.assertGreater(sunny_noon.environment.outdoor_temperature, rainy_night.environment.outdoor_temperature)
        self.assertGreater(rainy_night.environment.outdoor_humidity, sunny_noon.environment.outdoor_humidity)

    def test_direct_window_scenario_uses_supplied_environment(self) -> None:
        scenario = build_direct_window_scenario(
            outdoor_temperature=35.0,
            outdoor_humidity=82.0,
            sunlight_illuminance=18000.0,
            opening_ratio=0.45,
            indoor_temperature=28.0,
            indoor_humidity=64.0,
        )
        self.assertEqual(scenario.name, "window_direct_input")
        self.assertEqual(scenario.metadata["input_mode"], "direct")
        self.assertEqual(scenario.environment.outdoor_temperature, 35.0)
        self.assertEqual(scenario.environment.outdoor_humidity, 82.0)
        self.assertEqual(scenario.environment.sunlight_illuminance, 18000.0)
        activations = {device.name: device.activation for device in scenario.devices}
        self.assertEqual(activations["window_main"], 0.45)
        self.assertEqual(activations["ac_main"], 0.0)
        self.assertEqual(activations["light_main"], 0.0)

    def test_export_svg_volume_heatmap_writes_3d_svg(self) -> None:
        result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
            furniture=self.furniture,
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=GridResolution(nx=4, ny=3, nz=2),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "temperature_3d.svg"
            export_svg_volume_heatmap(
                str(path),
                result.field,
                "temperature",
                "Temperature 3D",
                devices=build_standard_devices(),
            )
            content = path.read_text(encoding="utf-8")
        self.assertIn("<svg", content)
        self.assertIn("3D sampled field", content)
        self.assertIn("ac_main", content)
        self.assertIn("window_main", content)
        self.assertIn("light_main", content)
        self.assertIn("<polygon", content)


if __name__ == "__main__":
    unittest.main()
