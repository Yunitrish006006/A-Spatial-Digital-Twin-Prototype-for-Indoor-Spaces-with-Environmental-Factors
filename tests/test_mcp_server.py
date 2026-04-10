import json
import unittest

from digital_twin.mcp_server import LocalMCPServer
from digital_twin.service import (
    evaluate_scenario,
    evaluate_window_direct,
    evaluate_window_matrix,
    get_scenario_volume,
    list_scenario_metadata,
    list_window_scenario_metadata,
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
        )
        self.assertEqual(result["name"], "window_direct_input")
        self.assertEqual(result["metadata"]["category"], "window_direct_input")
        self.assertEqual(result["input"]["mode"], "direct")
        self.assertEqual(result["input"]["opening_ratio"], 0.45)
        self.assertEqual(result["environment"]["outdoor_temperature"], 35.0)
        self.assertIn("window_zone", result["zone_estimated"])

    def test_sample_point_returns_three_metrics(self) -> None:
        result = sample_scenario_point("light_only", x=3.0, y=2.0, z=1.5)
        self.assertIn("temperature", result["values"])
        self.assertIn("humidity", result["values"])
        self.assertIn("illuminance", result["values"])

    def test_get_scenario_volume_returns_points_and_devices(self) -> None:
        result = get_scenario_volume("idle")
        self.assertEqual(result["scenario"], "idle")
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
