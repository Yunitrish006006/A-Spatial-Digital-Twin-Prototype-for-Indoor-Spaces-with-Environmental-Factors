import unittest

from digital_twin.web_demo import INDEX_HTML, _query_device_overrides, _query_float, _query_name


class WebDemoTests(unittest.TestCase):
    def test_index_contains_core_sections(self) -> None:
        self.assertIn("IDW Baseline Comparison", INDEX_HTML)
        self.assertIn("Learned Non-Networked Appliance Impact", INDEX_HTML)
        self.assertIn("Window Season/Weather/Time Matrix", INDEX_HTML)
        self.assertIn("Direct Window Input", INDEX_HTML)
        self.assertIn("windowDirectResult", INDEX_HTML)
        self.assertIn("Rotatable 3D Field Preview", INDEX_HTML)
        self.assertIn("volumeCanvas", INDEX_HTML)
        self.assertIn("Device Toggles", INDEX_HTML)
        self.assertIn("deviceControls", INDEX_HTML)
        self.assertIn("metricControls", INDEX_HTML)
        self.assertNotIn("<select", INDEX_HTML)
        self.assertIn("MCP-Enabled Digital Twin Demo", INDEX_HTML)

    def test_query_name_defaults_to_idle(self) -> None:
        self.assertEqual(_query_name(""), "idle")
        self.assertEqual(_query_name("name=light_only"), "light_only")

    def test_query_float_defaults_on_invalid_input(self) -> None:
        self.assertEqual(_query_float({"x": ["2.5"]}, "x", 3.0), 2.5)
        self.assertEqual(_query_float({"x": ["bad"]}, "x", 3.0), 3.0)

    def test_query_device_overrides(self) -> None:
        overrides = _query_device_overrides("name=idle&ac_main=0.8&window_main=0&light_main=1")
        self.assertEqual(overrides["ac_main"], 0.8)
        self.assertEqual(overrides["window_main"], 0.0)
        self.assertEqual(overrides["light_main"], 1.0)


if __name__ == "__main__":
    unittest.main()
