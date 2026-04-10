import json
import unittest

from digital_twin.gemma_bridge import (
    execute_tool,
    find_scenario_name,
    heuristic_tool_selection,
    parse_json_object,
)


class GemmaBridgeTests(unittest.TestCase):
    def test_parse_json_object_from_plain_text(self) -> None:
        parsed = parse_json_object('{"tool":"rank_actions","arguments":{"scenario_name":"idle"}}')
        self.assertEqual(parsed["tool"], "rank_actions")
        self.assertEqual(parsed["arguments"]["scenario_name"], "idle")

    def test_parse_json_object_from_code_fence(self) -> None:
        parsed = parse_json_object('```json\n{"tool":"list_scenarios","arguments":{}}\n```')
        self.assertEqual(parsed["tool"], "list_scenarios")

    def test_find_chinese_scenario_alias(self) -> None:
        self.assertEqual(find_scenario_name("請問冷氣情境"), "ac_only")
        self.assertEqual(find_scenario_name("全部設備全開"), "all_active")

    def test_heuristic_selects_rank_actions(self) -> None:
        selected = heuristic_tool_selection("idle 情境推薦什麼動作")
        self.assertEqual(selected["tool"], "rank_actions")
        self.assertEqual(selected["arguments"]["scenario_name"], "idle")

    def test_execute_rank_actions_tool(self) -> None:
        result = execute_tool("rank_actions", {"scenario_name": "idle"})
        self.assertEqual(result["scenario"], "idle")
        self.assertGreater(len(result["recommendations"]), 0)

    def test_tool_output_is_json_serializable(self) -> None:
        result = execute_tool("sample_point", {"scenario_name": "light_only", "x": 3, "y": 2, "z": 1.5})
        json.dumps(result, ensure_ascii=False)
        self.assertIn("illuminance", result["values"])


if __name__ == "__main__":
    unittest.main()
