import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from digital_twin.web.web_demo import (
    INDEX_HTML,
    _query_bool,
    _query_custom_devices,
    _query_custom_furniture,
    _query_device_specs,
    _query_device_metadata_overrides,
    _query_device_overrides,
    _query_furniture_overrides,
    _query_float,
    _query_name,
)


class WebDemoTests(unittest.TestCase):
    def test_index_contains_core_sections(self) -> None:
        self.assertIn("IDW Baseline Comparison", INDEX_HTML)
        self.assertIn("Learned Non-Networked Appliance Impact", INDEX_HTML)
        self.assertNotIn("Window Season/Weather/Time Matrix", INDEX_HTML)
        self.assertIn("Direct Window Input", INDEX_HTML)
        self.assertIn("windowDirectResult", INDEX_HTML)
        self.assertIn("Time Evolution", INDEX_HTML)
        self.assertIn("timelineCharts", INDEX_HTML)
        self.assertIn("elapsedMinutes", INDEX_HTML)
        self.assertIn("elapsedMinutesValue", INDEX_HTML)
        self.assertIn("Rotatable 3D Field Preview", INDEX_HTML)
        self.assertIn("Preview Timeline", INDEX_HTML)
        self.assertIn("preview-timeline", INDEX_HTML)
        self.assertIn("playbackSpeedControls", INDEX_HTML)
        self.assertIn("elapsedPlayButton", INDEX_HTML)
        self.assertIn("Play Timeline", INDEX_HTML)
        self.assertIn("Reset To 0", INDEX_HTML)
        self.assertIn("elapsedTimelineStatus", INDEX_HTML)
        self.assertIn("volumeCanvas", INDEX_HTML)
        self.assertIn("Devices", INDEX_HTML)
        self.assertIn("deviceControls", INDEX_HTML)
        self.assertIn("Custom Devices", INDEX_HTML)
        self.assertIn("customDeviceList", INDEX_HTML)
        self.assertIn("addCustomDeviceButton", INDEX_HTML)
        self.assertIn("clearCustomDeviceButton", INDEX_HTML)
        self.assertIn("customDeviceKindControls", INDEX_HTML)
        self.assertIn("Preset Bundles", INDEX_HTML)
        self.assertIn("presetControls", INDEX_HTML)
        self.assertIn("Duplicate", INDEX_HTML)
        self.assertIn("Reset", INDEX_HTML)
        self.assertIn("metricControls", INDEX_HTML)
        self.assertIn("Indoor Baseline", INDEX_HTML)
        self.assertIn("baselineIndoorTemperature", INDEX_HTML)
        self.assertIn("baselineIndoorHumidity", INDEX_HTML)
        self.assertIn("baselineIlluminance", INDEX_HTML)
        self.assertIn("Hybrid Residual Correction", INDEX_HTML)
        self.assertIn("useHybridResidual", INDEX_HTML)
        self.assertIn("hybridEstimatorStatus", INDEX_HTML)
        self.assertIn("estimatorStatus", INDEX_HTML)
        self.assertIn("Window Controls", INDEX_HTML)
        self.assertIn("sidebar-form-grid", INDEX_HTML)
        self.assertIn("Furniture Blocking", INDEX_HTML)
        self.assertIn("furnitureControls", INDEX_HTML)
        self.assertIn("Custom Furniture", INDEX_HTML)
        self.assertIn("customFurnitureList", INDEX_HTML)
        self.assertIn("addCustomFurniture", INDEX_HTML)
        self.assertIn("clearCustomFurniture", INDEX_HTML)
        self.assertIn("Drag a custom furniture box to reposition it on the floor plane", INDEX_HTML)
        self.assertIn("moveCustomFurnitureFromDrag", INDEX_HTML)
        self.assertIn("findCustomFurnitureHandle", INDEX_HTML)
        self.assertIn("snapToGrid", INDEX_HTML)
        self.assertIn("customFurnitureCollides", INDEX_HTML)
        self.assertIn("Center X", INDEX_HTML)
        self.assertIn("Base Z", INDEX_HTML)
        self.assertIn("Height Z", INDEX_HTML)
        self.assertIn("Outdoor Season", INDEX_HTML)
        self.assertIn("windowSeasonControls", INDEX_HTML)
        self.assertIn("windowWeatherControls", INDEX_HTML)
        self.assertIn("windowTimeControls", INDEX_HTML)
        self.assertIn("Apply Outdoor Preset", INDEX_HTML)
        self.assertIn("directOutdoorTemperature", INDEX_HTML)
        self.assertIn("directOpening", INDEX_HTML)
        self.assertNotIn("directOutdoorHumidity", INDEX_HTML)
        self.assertNotIn("directSunlight", INDEX_HTML)
        self.assertNotIn("directIndoorTemperature", INDEX_HTML)
        self.assertNotIn("directIndoorHumidity", INDEX_HTML)
        self.assertIn("AC Mode", INDEX_HTML)
        self.assertIn("acTargetTemperature", INDEX_HTML)
        self.assertIn("Left / Right Swing", INDEX_HTML)
        self.assertIn("Up / Down Swing", INDEX_HTML)
        self.assertNotIn("<select", INDEX_HTML)
        self.assertIn("MCP-Enabled Digital Twin Demo", INDEX_HTML)

    def test_query_name_defaults_to_idle(self) -> None:
        self.assertEqual(_query_name(""), "idle")
        self.assertEqual(_query_name("name=light_only"), "light_only")

    def test_query_float_defaults_on_invalid_input(self) -> None:
        self.assertEqual(_query_float({"x": ["2.5"]}, "x", 3.0), 2.5)
        self.assertEqual(_query_float({"x": ["bad"]}, "x", 3.0), 3.0)

    def test_query_bool_parses_common_flags(self) -> None:
        self.assertTrue(_query_bool({"use_hybrid_residual": ["1"]}, "use_hybrid_residual"))
        self.assertTrue(_query_bool({"use_hybrid_residual": ["true"]}, "use_hybrid_residual"))
        self.assertFalse(_query_bool({"use_hybrid_residual": ["0"]}, "use_hybrid_residual"))
        self.assertFalse(_query_bool({}, "use_hybrid_residual"))

    def test_query_device_overrides(self) -> None:
        overrides = _query_device_overrides("name=idle&ac_main=0.8&window_main=0&light_main=1")
        self.assertEqual(overrides["ac_main"], 0.8)
        self.assertEqual(overrides["window_main"], 0.0)
        self.assertEqual(overrides["light_main"], 1.0)

    def test_query_device_metadata_overrides(self) -> None:
        overrides = _query_device_metadata_overrides(
            "name=idle&ac_mode=heat&ac_target_temperature=40&ac_horizontal_mode=swing"
            "&ac_horizontal_angle_deg=90&ac_vertical_mode=fixed&ac_vertical_angle_deg=-10"
        )
        self.assertEqual(overrides["ac_main"]["ac_mode"], "heat")
        self.assertEqual(overrides["ac_main"]["target_temperature"], 33.0)
        self.assertEqual(overrides["ac_main"]["horizontal_mode"], "swing")
        self.assertEqual(overrides["ac_main"]["horizontal_angle_deg"], 60.0)
        self.assertEqual(overrides["ac_main"]["vertical_mode"], "fixed")
        self.assertEqual(overrides["ac_main"]["vertical_angle_deg"], 0.0)

    def test_query_furniture_overrides(self) -> None:
        overrides = _query_furniture_overrides("name=idle&cabinet_window=1&sofa_main=0.5&table_center=0")
        self.assertEqual(overrides["cabinet_window"], 1.0)
        self.assertEqual(overrides["sofa_main"], 0.5)
        self.assertEqual(overrides["table_center"], 0.0)

    def test_query_custom_furniture(self) -> None:
        payload = _query_custom_furniture(
            'name=idle&custom_furniture=[{"name":"custom_furniture_1","kind":"custom","activation":1,'
            '"min_corner":{"x":1.0,"y":1.0,"z":0.0},"max_corner":{"x":2.0,"y":2.0,"z":1.2},'
            '"metadata":{"label":"Desk Divider","block_strength":0.35}}]'
        )
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "custom_furniture_1")
        self.assertEqual(payload[0]["metadata"]["label"], "Desk Divider")

    def test_query_custom_devices(self) -> None:
        payload = _query_custom_devices(
            'name=idle&custom_devices=[{"name":"custom_device_ac_1","kind":"ac","activation":1,'
            '"power":1.1,"influence_radius":2.8,"position":{"x":4.8,"y":2.0,"z":2.6},'
            '"metadata":{"label":"Extra AC","ac_mode":"cool","target_temperature":22}}]'
        )
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "custom_device_ac_1")
        self.assertEqual(payload[0]["kind"], "ac")
        self.assertEqual(payload[0]["metadata"]["label"], "Extra AC")

    def test_query_device_specs(self) -> None:
        payload = _query_device_specs(
            'name=idle&device_specs=[{"name":"ac_main","kind":"ac","activation":0.6,"power":1.2,'
            '"influence_radius":3.1,"position":{"x":5.0,"y":2.0,"z":2.7},"metadata":{"label":"Main AC"}}]'
        )
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "ac_main")
        self.assertEqual(payload[0]["power"], 1.2)
        self.assertEqual(payload[0]["metadata"]["label"], "Main AC")


if __name__ == "__main__":
    unittest.main()
