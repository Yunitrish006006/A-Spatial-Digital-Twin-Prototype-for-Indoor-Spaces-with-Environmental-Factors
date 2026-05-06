import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from digital_twin.mcp.gemma_bridge import (
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
        parsed = parse_json_object('```json\n{"tool":"initialize_environment","arguments":{}}\n```')
        self.assertEqual(parsed["tool"], "initialize_environment")

    def test_find_chinese_scenario_alias(self) -> None:
        self.assertEqual(find_scenario_name("請問冷氣情境"), "ac_only")
        self.assertEqual(find_scenario_name("全部設備全開"), "all_active")

    def test_find_window_matrix_scenario_from_chinese_tokens(self) -> None:
        self.assertEqual(find_scenario_name("夏季晴天中午窗戶結果"), "window_summer_sunny_noon")

    def test_heuristic_selects_rank_actions(self) -> None:
        selected = heuristic_tool_selection("座標 3 2 1.2 推薦什麼動作")
        self.assertEqual(selected["tool"], "rank_actions")
        self.assertEqual(selected["arguments"], {"x": 3.0, "y": 2.0, "z": 1.2})

    def test_heuristic_selects_initialize_environment(self) -> None:
        selected = heuristic_tool_selection("幫我初始化設備家具跟 baseline")
        self.assertEqual(selected["tool"], "initialize_environment")

    def test_heuristic_selects_impact_learning(self) -> None:
        selected = heuristic_tool_selection("學習非連網冷氣影響")
        self.assertEqual(selected["tool"], "learn_impacts")
        self.assertEqual(selected["arguments"]["device_name"], "ac_main")

    def test_heuristic_selects_direct_window_input(self) -> None:
        selected = heuristic_tool_selection("窗戶直接用外部溫度35 濕度82 日照18000 開窗比例45% 模擬")
        self.assertEqual(selected["tool"], "run_window_direct")
        self.assertEqual(selected["arguments"]["outdoor_temperature"], 35.0)
        self.assertEqual(selected["arguments"]["outdoor_humidity"], 82.0)
        self.assertEqual(selected["arguments"]["sunlight_illuminance"], 18000.0)
        self.assertEqual(selected["arguments"]["opening_ratio"], 0.45)

    def test_execute_rank_actions_tool(self) -> None:
        result = execute_tool("rank_actions", {"x": 3.0, "y": 2.0, "z": 1.2})
        self.assertEqual(result["scenario"], "idle")
        self.assertEqual(result["point"], {"x": 3.0, "y": 2.0, "z": 1.2})
        self.assertGreater(len(result["recommendations"]), 0)

    def test_execute_initialize_then_sample_tool(self) -> None:
        initialized = execute_tool(
            "initialize_environment",
            {
                "devices": [
                    {
                        "name": "ac_main",
                        "kind": "ac",
                        "activation": 0.85,
                        "metadata": {"ac_mode": "cool", "target_temperature": 22.0},
                    }
                ]
            },
        )
        self.assertEqual(initialized["status"], "INITIALIZED")
        result = execute_tool("sample_point", {"x": 5.0, "y": 2.0, "z": 1.5, "steady_state": True})
        self.assertEqual(result["sampling_mode"], "steady_state")
        self.assertIn("temperature", result["values"])

    def test_execute_learn_impacts_tool(self) -> None:
        result = execute_tool("learn_impacts", {"device_name": "ac_main", "device_state": {"activation": 0.85}})
        self.assertEqual(result["status"], "RECORDING")
        self.assertIn("learning_record_id", result)

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
        result = execute_tool("sample_point", {"x": 3, "y": 2, "z": 1.5})
        json.dumps(result, ensure_ascii=False)
        self.assertIn("illuminance", result["values"])


if __name__ == "__main__":
    unittest.main()
