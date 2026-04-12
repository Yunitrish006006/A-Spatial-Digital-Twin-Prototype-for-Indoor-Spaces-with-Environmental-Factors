import json
import unittest

from digital_twin.mcp_server import LocalMCPServer
from digital_twin.service import (
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


class ServiceTests(unittest.TestCase):
    def test_list_scenarios_returns_standard_cases(self) -> None:
        scenarios = list_scenario_metadata()
        names = {scenario["name"] for scenario in scenarios}
        self.assertIn("idle", names)
        self.assertIn("all_active", names)

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
        self.assertIn("temperature", result["points"][0])
        ac = next(device for device in result["devices"] if device["name"] == "ac_main")
        window = next(device for device in result["devices"] if device["name"] == "window_main")
        self.assertEqual(ac["geometry"]["shape"], "wall_bar")
        self.assertEqual(window["geometry"]["shape"], "wall_rectangle")

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
                "list_scenarios",
                "list_window_scenarios",
                "run_scenario",
                "rank_actions",
                "sample_point",
                "compare_baseline",
                "learn_impacts",
                "run_window_matrix",
                "run_window_direct",
            },
        )

    def test_tool_call(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "rank_actions", "arguments": {"scenario_name": "idle"}},
            }
        )
        content = response["result"]["content"][0]["text"]
        payload = json.loads(content)
        self.assertEqual(payload["scenario"], "idle")
        self.assertGreater(len(payload["recommendations"]), 0)

    def test_run_scenario_tool_call_accepts_ac_overrides(self) -> None:
        cool_response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 31,
                "method": "tools/call",
                "params": {
                    "name": "run_scenario",
                    "arguments": {
                        "scenario_name": "idle",
                        "ac_main": 0.85,
                        "ac_mode": "cool",
                        "ac_target_temperature": 20.0,
                    },
                },
            }
        )
        heat_response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 32,
                "method": "tools/call",
                "params": {
                    "name": "run_scenario",
                    "arguments": {
                        "scenario_name": "idle",
                        "ac_main": 0.85,
                        "ac_mode": "heat",
                        "ac_target_temperature": 33.0,
                    },
                },
            }
        )
        cool_payload = json.loads(cool_response["result"]["content"][0]["text"])
        heat_payload = json.loads(heat_response["result"]["content"][0]["text"])
        self.assertLess(cool_payload["target_zone_estimated"]["temperature"], heat_payload["target_zone_estimated"]["temperature"])

    def test_compare_baseline_tool_call(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "compare_baseline", "arguments": {"scenario_name": "light_only"}},
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["scenario"], "light_only")
        self.assertIn("comparison", payload)

    def test_learn_impacts_tool_call(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "learn_impacts", "arguments": {"scenario_name": "ac_only"}},
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["scenario"], "ac_only")
        self.assertGreater(len(payload["learned_device_impacts"]), 0)

    def test_run_window_matrix_tool_call(self) -> None:
        response = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "run_window_matrix", "arguments": {}},
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["count"], 48)
        self.assertEqual(payload["scenarios"][0]["metadata"]["category"], "window_matrix")

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
                    },
                },
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["name"], "window_direct_input")
        self.assertEqual(payload["input"]["opening_ratio"], 0.45)
        self.assertEqual(payload["target_zone"], "window_zone")


if __name__ == "__main__":
    unittest.main()
