import unittest

from digital_twin.demo import compare_sensors, synthesize_sensor_observations
from digital_twin.model import DigitalTwinModel
from digital_twin.recommendations import rank_actions
from digital_twin.scenarios import (
    apply_truth_adjustments,
    build_candidate_actions,
    build_comfort_target,
    build_standard_devices,
    build_standard_environment,
    build_standard_room,
    build_standard_zones,
)
from digital_twin.entities import ComfortTarget, GridResolution, create_corner_sensors


class DigitalTwinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = DigitalTwinModel()
        self.room = build_standard_room()
        self.environment = build_standard_environment()
        self.devices = build_standard_devices()
        self.sensors = create_corner_sensors(self.room)
        self.zones = build_standard_zones(self.room)
        self.resolution = GridResolution(nx=10, ny=8, nz=4)
        self.elapsed_minutes = 18.0

    def test_idle_state_stays_near_baseline(self) -> None:
        result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
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
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        self.assertLess(
            on_result.zone_averages["center_zone"]["temperature"],
            off_result.zone_averages["center_zone"]["temperature"],
        )

    def test_light_increases_center_illuminance(self) -> None:
        off_result = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
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
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        self.assertGreater(
            on_result.zone_averages["center_zone"]["illuminance"],
            off_result.zone_averages["center_zone"]["illuminance"],
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
            sensors=self.sensors,
            zones=self.zones,
            elapsed_minutes=self.elapsed_minutes,
            resolution=self.resolution,
        )
        after = self.model.simulate(
            room=self.room,
            environment=self.environment,
            devices=self.devices,
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
                sensors=self.sensors,
                elapsed_minutes=self.elapsed_minutes,
            ),
        )
        self.assertEqual(recommendations[0].name, "turn_on_ac")


if __name__ == "__main__":
    unittest.main()
