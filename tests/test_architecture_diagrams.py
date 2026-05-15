import unittest
import xml.etree.ElementTree as ET

from scripts import build_architecture_diagrams


class ArchitectureDiagramTests(unittest.TestCase):
    def test_system_abstraction_tree_renders_valid_svg(self):
        svg = build_architecture_diagrams.svg_overall_architecture()

        ET.fromstring(svg)
        self.assertIn("系統整體抽象樹狀架構", svg)
        self.assertIn("情境與觀測層", svg)
        self.assertIn("估測與學習層", svg)
        self.assertIn("MCP + Gemma bridge", svg)


if __name__ == "__main__":
    unittest.main()
