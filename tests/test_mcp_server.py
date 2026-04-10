import json
import unittest

from digital_twin.mcp_server import LocalMCPServer
from digital_twin.service import evaluate_scenario, list_scenario_metadata, sample_scenario_point


class ServiceTests(unittest.TestCase):
    def test_list_scenarios_returns_standard_cases(self) -> None:
        scenarios = list_scenario_metadata()
        names = {scenario["name"] for scenario in scenarios}
        self.assertIn("idle", names)
        self.assertIn("all_active", names)

    def test_evaluate_scenario_returns_errors_and_zone_values(self) -> None:
        result = evaluate_scenario("idle")
        self.assertEqual(result["name"], "idle")
        self.assertIn("field_mae", result)
        self.assertIn("target_zone_estimated", result)

    def test_sample_point_returns_three_metrics(self) -> None:
        result = sample_scenario_point("light_only", x=3.0, y=2.0, z=1.5)
        self.assertIn("temperature", result["values"])
        self.assertIn("humidity", result["values"])
        self.assertIn("illuminance", result["values"])


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
        self.assertEqual(names, {"list_scenarios", "run_scenario", "rank_actions", "sample_point"})

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


if __name__ == "__main__":
    unittest.main()
