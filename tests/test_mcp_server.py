import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from digital_twin.core.service import (
    compare_scenario_baseline,
    evaluate_scenario,
    evaluate_window_direct,
    evaluate_window_direct_dashboard,
    evaluate_window_matrix,
    get_scenario_volume,
    get_scenario_timeline,
    get_window_direct_timeline,
    learn_scenario_impacts,
    list_scenario_metadata,
    list_window_scenario_metadata,
    rank_scenario_actions,
    sample_window_direct_point,
    sample_scenario_point,
)
from digital_twin.mcp.mcp_server import LocalMCPServer


SENSOR_NAMES = (
    "floor_sw",
    "floor_se",
    "floor_nw",
    "floor_ne",
    "ceiling_sw",
    "ceiling_se",
    "ceiling_nw",
    "ceiling_ne",
)


def _constant_sensor_observations(temperature: float, humidity: float, illuminance: float) -> dict:
    return {
        name: {
            "temperature": temperature,
            "humidity": humidity,
            "illuminance": illuminance,
        }
        for name in SENSOR_NAMES
    }


class ServiceTests(unittest.TestCase):
    def test_list_scenarios_returns_standard_cases(self) -> None:
        scenarios = list_scenario_metadata()
        names = {scenario["name"] for scenario in scenarios}
        self.assertIn("idle", names)
        self.assertIn("all_active", names)
        idle = next(item for item in scenarios if item["name"] == "idle")
        self.assertEqual({item["name"] for item in idle["furniture"]}, {"cabinet_window", "sofa_main", "table_center"})

    def test_list_window_scenarios_returns_48_cases(self) -> None:
        scenarios = list_window_scenario_metadata()
        names = {scenario["name"] for scenario in scenarios}
        self.assertEqual(len(scenarios), 48)
        self.assertIn("window_summer_sunny_noon", names)

    def test_evaluate_scenario_returns_errors_and_zone_values(self) -> None:
        result = evaluate_scenario("idle")
        self.assertEqual(result["name"], "idle")
        self.assertIn("field_mae", result)
        self.assertIn("target_zone_estimated", result)
        self.assertIn("estimator", result)

    def test_evaluate_scenario_can_request_hybrid_estimator(self) -> None:
        result = evaluate_scenario("idle", use_hybrid_residual=True)
        self.assertTrue(result["estimator"]["requested"])
        self.assertIn("label", result["estimator"])

    def test_evaluate_window_scenario_returns_window_metadata(self) -> None:
        result = evaluate_scenario("window_summer_sunny_noon")
        self.assertEqual(result["name"], "window_summer_sunny_noon")
        self.assertEqual(result["target_zone"], "window_zone")
        self.assertEqual(result["metadata"]["season_zh"], "夏季")

    def test_evaluate_window_matrix_returns_summary(self) -> None:
        result = evaluate_window_matrix()
        self.assertEqual(result["count"], 48)
        self.assertEqual(len(result["scenarios"]), 48)

    def test_evaluate_window_direct_returns_supplied_input(self) -> None:
        result = evaluate_window_direct(
            outdoor_temperature=35.0,
            outdoor_humidity=82.0,
            sunlight_illuminance=18000.0,
            opening_ratio=0.45,
            indoor_temperature=28.0,
            indoor_humidity=64.0,
            base_illuminance=140.0,
        )
        self.assertEqual(result["name"], "window_direct_input")
        self.assertEqual(result["metadata"]["category"], "window_direct_input")
        self.assertEqual(result["input"]["mode"], "direct")
        self.assertEqual(result["input"]["opening_ratio"], 0.45)
        self.assertEqual(result["input"]["base_illuminance"], 140.0)
        self.assertEqual(result["environment"]["outdoor_temperature"], 35.0)
        self.assertIn("window_zone", result["zone_estimated"])

    def test_evaluate_window_direct_cools_room_when_outdoor_is_colder(self) -> None:
        result = evaluate_window_direct(
            outdoor_temperature=11.0,
            outdoor_humidity=70.0,
            sunlight_illuminance=0.0,
            opening_ratio=0.7,
            indoor_temperature=19.0,
            indoor_humidity=60.0,
        )
        self.assertLess(result["zone_estimated"]["window_zone"]["temperature"], 19.0)
        self.assertLess(result["zone_estimated"]["center_zone"]["temperature"], 19.0)

    def test_evaluate_window_direct_dashboard_returns_main_panels(self) -> None:
        result = evaluate_window_direct_dashboard(
            outdoor_temperature=11.0,
            outdoor_humidity=70.0,
            sunlight_illuminance=0.0,
            opening_ratio=0.7,
            indoor_temperature=19.0,
            indoor_humidity=60.0,
        )
        self.assertIn("scenario", result)
        self.assertIn("ranking", result)
        self.assertIn("baseline", result)
        self.assertIn("impacts", result)
        self.assertIn("volume", result)
        self.assertEqual(result["scenario"]["input"]["indoor_temperature"], 19.0)
        self.assertLess(result["scenario"]["zone_estimated"]["window_zone"]["temperature"], 19.0)

    def test_ac_metadata_override_changes_zone_estimate(self) -> None:
        cool = evaluate_scenario(
            "ac_only",
            device_metadata_overrides={"ac_main": {"ac_mode": "cool", "target_temperature": 20.0}},
        )
        heat = evaluate_scenario(
            "ac_only",
            device_metadata_overrides={"ac_main": {"ac_mode": "heat", "target_temperature": 33.0}},
        )
        self.assertLess(cool["target_zone_estimated"]["temperature"], heat["target_zone_estimated"]["temperature"])

    def test_elapsed_minutes_changes_active_scenario_estimate(self) -> None:
        early = evaluate_scenario("ac_only", elapsed_minutes=1.0)
        late = evaluate_scenario("ac_only", elapsed_minutes=120.0)
        self.assertGreater(early["target_zone_estimated"]["temperature"], late["target_zone_estimated"]["temperature"])

    def test_evaluate_scenario_supports_indoor_baseline_override(self) -> None:
        default = evaluate_scenario("idle")
        custom = evaluate_scenario(
            "idle",
            indoor_temperature=21.0,
            indoor_humidity=54.0,
            base_illuminance=150.0,
        )
        self.assertLess(custom["target_zone_estimated"]["temperature"], default["target_zone_estimated"]["temperature"])
        self.assertLess(custom["target_zone_estimated"]["humidity"], default["target_zone_estimated"]["humidity"])
        self.assertGreater(custom["target_zone_estimated"]["illuminance"], default["target_zone_estimated"]["illuminance"])

    def test_sample_point_returns_three_metrics(self) -> None:
        result = sample_scenario_point("light_only", x=3.0, y=2.0, z=1.5)
        self.assertIn("temperature", result["values"])
        self.assertIn("humidity", result["values"])
        self.assertIn("illuminance", result["values"])

    def test_sample_window_direct_point_uses_direct_window_state(self) -> None:
        result = sample_window_direct_point(
            x=0.8,
            y=2.0,
            z=1.2,
            outdoor_temperature=11.0,
            outdoor_humidity=70.0,
            sunlight_illuminance=0.0,
            opening_ratio=0.7,
            indoor_temperature=19.0,
            indoor_humidity=60.0,
        )
        self.assertEqual(result["scenario"], "window_direct_input")
        self.assertLess(result["values"]["temperature"], 19.0)

    def test_get_scenario_timeline_shows_settling_trend(self) -> None:
        result = get_scenario_timeline("ac_only", elapsed_minutes=45.0, duration_minutes=60.0, steps=7)
        self.assertEqual(result["scenario"], "ac_only")
        self.assertEqual(len(result["points"]), 7)
        self.assertIn("estimator", result)
        self.assertGreater(
            result["points"][0]["target_zone_values"]["temperature"],
            result["points"][-1]["target_zone_values"]["temperature"],
        )

    def test_get_window_direct_timeline_tracks_current_elapsed_minutes(self) -> None:
        result = get_window_direct_timeline(
            outdoor_temperature=11.0,
            outdoor_humidity=70.0,
            sunlight_illuminance=0.0,
            opening_ratio=0.7,
            indoor_temperature=19.0,
            indoor_humidity=60.0,
            elapsed_minutes=30.0,
            duration_minutes=60.0,
            steps=7,
        )
        self.assertEqual(result["scenario"], "window_direct_input")
        self.assertEqual(result["current_elapsed_minutes"], 30.0)
        self.assertGreater(
            result["points"][0]["target_zone_values"]["temperature"],
            result["points"][-1]["target_zone_values"]["temperature"],
        )

    def test_get_scenario_volume_returns_points_and_devices(self) -> None:
        result = get_scenario_volume("idle")
        self.assertEqual(result["scenario"], "idle")
        self.assertIn("estimator", result)
        resolution = result["resolution"]
        self.assertEqual(len(result["points"]), resolution["nx"] * resolution["ny"] * resolution["nz"])
        self.assertEqual(resolution, {"nx": 16, "ny": 12, "nz": 6})
        self.assertEqual({device["name"] for device in result["devices"]}, {"ac_main", "window_main", "light_main"})
        self.assertEqual({item["name"] for item in result["furniture"]}, {"cabinet_window", "sofa_main", "table_center"})
        self.assertIn("temperature", result["points"][0])
        ac = next(device for device in result["devices"] if device["name"] == "ac_main")
        window = next(device for device in result["devices"] if device["name"] == "window_main")
        self.assertEqual(ac["geometry"]["shape"], "wall_bar")
        self.assertEqual(window["geometry"]["shape"], "wall_rectangle")

    def test_furniture_overrides_change_volume_furniture_activation(self) -> None:
        result = get_scenario_volume("idle", furniture_overrides={"cabinet_window": 1.0, "sofa_main": 0.5})
        activations = {item["name"]: item["activation"] for item in result["furniture"]}
        self.assertEqual(activations["cabinet_window"], 1.0)
        self.assertEqual(activations["sofa_main"], 0.5)
        self.assertEqual(activations["table_center"], 0.0)

    def test_furniture_override_blocks_window_effect_at_sample_point(self) -> None:
        open_point = sample_scenario_point(
            "window_only",
            x=1.5,
            y=2.0,
            z=1.4,
        )
        blocked_point = sample_scenario_point(
            "window_only",
            x=1.5,
            y=2.0,
            z=1.4,
            furniture_overrides={"cabinet_window": 1.0},
        )
        self.assertLess(blocked_point["values"]["illuminance"], open_point["values"]["illuminance"])
        self.assertLess(blocked_point["values"]["temperature"], open_point["values"]["temperature"])

    def test_extra_furniture_can_be_appended_from_web_payload(self) -> None:
        extra_furniture = [
            {
                "name": "custom_furniture_1",
                "kind": "custom",
                "activation": 1.0,
                "min_corner": {"x": 1.8, "y": 1.4, "z": 0.0},
                "max_corner": {"x": 2.8, "y": 2.6, "z": 1.6},
                "metadata": {"label": "Desk Divider", "block_strength": 0.4},
            }
        ]
        volume = get_scenario_volume("window_only", extra_furniture=extra_furniture)
        self.assertIn("custom_furniture_1", {item["name"] for item in volume["furniture"]})
        baseline = sample_scenario_point("window_only", x=2.4, y=2.0, z=1.0)
        blocked = sample_scenario_point(
            "window_only",
            x=2.4,
            y=2.0,
            z=1.0,
            extra_furniture=extra_furniture,
        )
        self.assertLess(blocked["values"]["illuminance"], baseline["values"]["illuminance"])

    def test_extra_devices_can_be_appended_from_web_payload(self) -> None:
        extra_devices = [
            {
                "name": "extra_ac_1",
                "kind": "ac",
                "activation": 1.0,
                "power": 1.1,
                "influence_radius": 2.8,
                "position": {"x": 4.8, "y": 2.0, "z": 2.6},
                "metadata": {"label": "Extra AC", "ac_mode": "cool", "target_temperature": 22.0},
            }
        ]
        volume = get_scenario_volume("idle", extra_devices=extra_devices)
        self.assertIn("extra_ac_1", {item["name"] for item in volume["devices"]})
        baseline = sample_scenario_point("idle", x=4.5, y=2.0, z=1.4)
        cooled = sample_scenario_point(
            "idle",
            x=4.5,
            y=2.0,
            z=1.4,
            extra_devices=extra_devices,
        )
        self.assertLess(cooled["values"]["temperature"], baseline["values"]["temperature"])

    def test_device_specs_can_edit_and_remove_built_in_devices(self) -> None:
        baseline = sample_scenario_point("idle", x=3.0, y=2.0, z=1.2)
        adjusted = sample_scenario_point(
            "idle",
            x=3.0,
            y=2.0,
            z=1.2,
            device_specs=[
                {"name": "light_main", "removed": True},
                {
                    "name": "ac_main",
                    "power": 1.3,
                    "activation": 1.0,
                    "position": {"x": 3.8, "y": 2.0, "z": 2.6},
                },
            ],
        )
        volume = get_scenario_volume(
            "idle",
            device_specs=[
                {"name": "light_main", "removed": True},
                {
                    "name": "ac_main",
                    "power": 1.3,
                    "activation": 1.0,
                    "position": {"x": 3.8, "y": 2.0, "z": 2.6},
                },
            ],
        )
        self.assertNotIn("light_main", {item["name"] for item in volume["devices"]})
        self.assertLess(adjusted["values"]["temperature"], baseline["values"]["temperature"])

    def test_device_overrides_change_volume_device_activation(self) -> None:
        result = get_scenario_volume("idle", {"ac_main": 0.8, "window_main": 0.7, "light_main": 0.0})
        activations = {device["name"]: device["activation"] for device in result["devices"]}
        self.assertEqual(activations["ac_main"], 0.8)
        self.assertEqual(activations["window_main"], 0.7)
        self.assertEqual(activations["light_main"], 0.0)

    def test_get_scenario_volume_returns_ac_metadata_overrides(self) -> None:
        result = get_scenario_volume(
            "idle",
            {"ac_main": 0.85},
            {
                "ac_main": {
                    "ac_mode": "dry",
                    "target_temperature": 22.0,
                    "horizontal_mode": "swing",
                    "vertical_mode": "fixed",
                    "vertical_angle_deg": 25.0,
                }
            },
        )
        ac = next(device for device in result["devices"] if device["name"] == "ac_main")
        self.assertEqual(ac["metadata"]["ac_mode"], "dry")
        self.assertEqual(ac["metadata"]["target_temperature"], 22.0)
        self.assertEqual(ac["metadata"]["horizontal_mode"], "swing")
        self.assertEqual(ac["metadata"]["vertical_mode"], "fixed")
        self.assertEqual(ac["metadata"]["vertical_angle_deg"], 25.0)

    def test_sample_point_supports_hybrid_estimator_flag(self) -> None:
        result = sample_scenario_point("light_only", x=3.0, y=2.0, z=1.5, use_hybrid_residual=True)
        self.assertTrue(result["estimator"]["requested"])
        self.assertIn("temperature", result["values"])

    def test_rank_actions_supports_hybrid_estimator_flag(self) -> None:
        result = rank_scenario_actions("idle", use_hybrid_residual=True)
        self.assertTrue(result["estimator"]["requested"])

    def test_learn_impacts_reports_estimator_note(self) -> None:
        result = learn_scenario_impacts("ac_only", use_hybrid_residual=True)
        self.assertTrue(result["estimator"]["requested"])
        self.assertIn("observation-driven", result["estimator_note"])


class MCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = LocalMCPServer()

    def test_initialize(self) -> None:
        response = self.server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        )
        self.assertEqual(response["result"]["serverInfo"]["name"], "single-room-spatial-digital-twin")
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list(self) -> None:
        response = self.server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "initialize_environment",
                "rank_actions",
                "sample_point",
                "learn_impacts",
                "run_window_direct",
            },
        )
        initialize = next(tool for tool in response["result"]["tools"] if tool["name"] == "initialize_environment")
        self.assertIn("devices", initialize["inputSchema"]["properties"])
        self.assertIn("furniture", initialize["inputSchema"]["properties"])

    def test_initialize_environment_registers_baseline_devices_and_furniture(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "initialize_environment",
                    "arguments": {
                        "baseline": {
                            "indoor_temperature": 28.0,
                            "indoor_humidity": 64.0,
                            "base_illuminance": 120.0,
                        },
                        "environment": {
                            "outdoor_temperature": 35.0,
                            "outdoor_humidity": 82.0,
                            "sunlight_illuminance": 18000.0,
                        },
                        "devices": [
                            {
                                "name": "ac_main",
                                "kind": "ac",
                                "activation": 0.85,
                                "metadata": {"ac_mode": "cool", "target_temperature": 22.0},
                            }
                        ],
                        "furniture": [{"name": "cabinet_window", "activation": 1.0}],
                    },
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "INITIALIZED")
        self.assertEqual(payload["baseline"]["indoor_temperature"], 28.0)
        self.assertEqual(payload["environment"]["outdoor_temperature"], 35.0)
        self.assertEqual(payload["furniture_overrides"]["cabinet_window"], 1.0)
        self.assertEqual(payload["registered_devices"][0]["name"], "ac_main")

    def test_sample_point_uses_elapsed_time_and_steady_state(self) -> None:
        self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 31,
                "method": "tools/call",
                "params": {
                    "name": "initialize_environment",
                    "arguments": {
                        "devices": [
                            {
                                "name": "ac_main",
                                "kind": "ac",
                                "activation": 0.85,
                                "metadata": {"ac_mode": "cool", "target_temperature": 22.0},
                            }
                        ],
                        "steady_state_minutes": 120.0,
                    },
                },
            }
        )
        early_response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 32,
                "method": "tools/call",
                "params": {
                    "name": "sample_point",
                    "arguments": {"x": 5.0, "y": 2.0, "z": 1.5, "elapsed_minutes": 1.0},
                },
            }
        )
        steady_response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 33,
                "method": "tools/call",
                "params": {
                    "name": "sample_point",
                    "arguments": {"x": 5.0, "y": 2.0, "z": 1.5, "steady_state": True},
                },
            }
        )
        early = json.loads(early_response["result"]["content"][0]["text"])
        steady = json.loads(steady_response["result"]["content"][0]["text"])
        self.assertEqual(steady["sampling_mode"], "steady_state")
        self.assertGreater(early["values"]["temperature"], steady["values"]["temperature"])

    def test_rank_actions_tool_call_uses_point_target(self) -> None:
        self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 34,
                "method": "tools/call",
                "params": {
                    "name": "initialize_environment",
                    "arguments": {
                        "devices": [
                            {"name": "light_main", "kind": "light", "activation": 0.0},
                            {"name": "ac_main", "kind": "ac", "activation": 0.0},
                        ]
                    },
                },
            }
        )
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 35,
                "method": "tools/call",
                "params": {
                    "name": "rank_actions",
                    "arguments": {
                        "x": 3.0,
                        "y": 2.0,
                        "z": 1.3,
                        "target": {"temperature": 25.0, "humidity": 58.0, "illuminance": 500.0},
                    },
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["point"], {"x": 3.0, "y": 2.0, "z": 1.3})
        self.assertIn("current_values", payload)
        self.assertGreater(len(payload["recommendations"]), 0)
        self.assertIn("effects", payload["recommendations"][0])

    def test_learn_impacts_start_records_without_fake_coefficients(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 36,
                "method": "tools/call",
                "params": {
                    "name": "learn_impacts",
                    "arguments": {
                        "device_name": "ac_main",
                        "device_state": {"activation": 0.85, "kind": "ac", "ac_mode": "cool"},
                        "sample_point": {"x": 5.0, "y": 2.0, "z": 1.5},
                    },
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "RECORDING")
        self.assertIn("learning_record_id", payload)
        self.assertEqual(payload["needs"], ["after_observations"])
        self.assertNotIn("learned_device_impacts", payload)

    def test_learn_impacts_finish_uses_supplied_before_after_observations(self) -> None:
        before = _constant_sensor_observations(29.0, 67.0, 90.0)
        after = _constant_sensor_observations(27.0, 64.0, 90.0)
        start_response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 37,
                "method": "tools/call",
                "params": {
                    "name": "learn_impacts",
                    "arguments": {
                        "device_name": "ac_main",
                        "device_state": {"activation": 0.85, "kind": "ac", "ac_mode": "cool"},
                        "before_observations": before,
                    },
                },
            }
        )
        record_id = json.loads(start_response["result"]["content"][0]["text"])["learning_record_id"]
        finish_response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 38,
                "method": "tools/call",
                "params": {
                    "name": "learn_impacts",
                    "arguments": {
                        "phase": "finish",
                        "learning_record_id": record_id,
                        "after_observations": after,
                    },
                },
            }
        )
        payload = json.loads(finish_response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "LEARNED")
        self.assertEqual(payload["observation_source"], "user_supplied")
        self.assertGreater(len(payload["learned_device_impacts"]), 0)

    def test_run_window_direct_tool_call(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "run_window_direct",
                    "arguments": {
                        "outdoor_temperature": 35.0,
                        "outdoor_humidity": 82.0,
                        "sunlight_illuminance": 18000.0,
                        "opening_ratio": 0.45,
                        "update_environment": True,
                    },
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["name"], "window_direct_input")
        self.assertEqual(payload["input"]["opening_ratio"], 0.45)
        self.assertEqual(payload["target_zone"], "window_zone")
        self.assertTrue(payload["registered_environment_updated"])

    def test_window_direct_uses_registered_extra_device(self) -> None:
        self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "initialize_environment",
                    "arguments": {
                        "devices": [
                            {
                                "name": "extra_light_1",
                                "kind": "light",
                                "activation": 1.0,
                                "power": 1.0,
                                "position": {"x": 2.8, "y": 2.0, "z": 2.7},
                                "metadata": {"label": "Task Light", "illuminance_gain": 1200.0},
                            }
                        ],
                    },
                },
            }
        )
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "run_window_direct",
                    "arguments": {
                        "outdoor_temperature": 30.0,
                        "outdoor_humidity": 70.0,
                        "sunlight_illuminance": 0.0,
                        "opening_ratio": 0.3,
                    },
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertGreater(payload["zone_estimated"]["center_zone"]["illuminance"], 70.0)


if __name__ == "__main__":
    unittest.main()
