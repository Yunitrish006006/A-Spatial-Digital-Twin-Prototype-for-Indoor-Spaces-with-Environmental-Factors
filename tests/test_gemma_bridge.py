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

    def test_find_window_matrix_scenario_from_chinese_tokens(self) -> None:
        self.assertEqual(find_scenario_name("夏季晴天中午窗戶結果"), "window_summer_sunny_noon")

    def test_heuristic_selects_rank_actions(self) -> None:
        selected = heuristic_tool_selection("idle 情境推薦什麼動作")
        self.assertEqual(selected["tool"], "rank_actions")
        self.assertEqual(selected["arguments"]["scenario_name"], "idle")

    def test_heuristic_selects_baseline_comparison(self) -> None:
        selected = heuristic_tool_selection("light_only 跟 IDW baseline 誤差比較")
        self.assertEqual(selected["tool"], "compare_baseline")
        self.assertEqual(selected["arguments"]["scenario_name"], "light_only")

    def test_heuristic_selects_impact_learning(self) -> None:
        selected = heuristic_tool_selection("ac_only 學習非連網冷氣影響")
        self.assertEqual(selected["tool"], "learn_impacts")
        self.assertEqual(selected["arguments"]["scenario_name"], "ac_only")

    def test_heuristic_selects_window_matrix(self) -> None:
        selected = heuristic_tool_selection("幫我跑窗戶早上中午下午晚上陰天晴天雨天四季模擬")
        self.assertEqual(selected["tool"], "run_window_matrix")

    def test_heuristic_selects_direct_window_input(self) -> None:
        selected = heuristic_tool_selection("窗戶直接用外部溫度35 濕度82 日照18000 開窗比例45% 模擬")
        self.assertEqual(selected["tool"], "run_window_direct")
        self.assertEqual(selected["arguments"]["outdoor_temperature"], 35.0)
        self.assertEqual(selected["arguments"]["outdoor_humidity"], 82.0)
        self.assertEqual(selected["arguments"]["sunlight_illuminance"], 18000.0)
        self.assertEqual(selected["arguments"]["opening_ratio"], 0.45)

    def test_heuristic_selects_specific_window_scenario(self) -> None:
        selected = heuristic_tool_selection("夏季晴天中午窗戶結果")
        self.assertEqual(selected["tool"], "run_scenario")
        self.assertEqual(selected["arguments"]["scenario_name"], "window_summer_sunny_noon")

    def test_execute_rank_actions_tool(self) -> None:
        result = execute_tool("rank_actions", {"scenario_name": "idle"})
        self.assertEqual(result["scenario"], "idle")
        self.assertGreater(len(result["recommendations"]), 0)

    def test_execute_learn_impacts_tool(self) -> None:
        result = execute_tool("learn_impacts", {"scenario_name": "ac_only"})
        self.assertEqual(result["scenario"], "ac_only")
        self.assertGreater(len(result["learned_device_impacts"]), 0)

    def test_execute_window_matrix_tool(self) -> None:
        result = execute_tool("run_window_matrix", {})
        self.assertEqual(result["count"], 48)

    def test_execute_window_direct_tool(self) -> None:
        result = execute_tool(
            "run_window_direct",
            {
                "outdoor_temperature": 35.0,
                "outdoor_humidity": 82.0,
                "sunlight_illuminance": 18000.0,
                "opening_ratio": 0.45,
            },
        )
        self.assertEqual(result["name"], "window_direct_input")
        self.assertEqual(result["input"]["opening_ratio"], 0.45)

    def test_tool_output_is_json_serializable(self) -> None:
        result = execute_tool("sample_point", {"scenario_name": "light_only", "x": 3, "y": 2, "z": 1.5})
        json.dumps(result, ensure_ascii=False)
        self.assertIn("illuminance", result["values"])


if __name__ == "__main__":
    unittest.main()
