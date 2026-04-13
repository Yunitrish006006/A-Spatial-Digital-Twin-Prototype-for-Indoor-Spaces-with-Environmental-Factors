from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_twin.core.service import evaluate_window_matrix
from digital_twin.web.render import ensure_directory, export_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 48 window-only season/weather/time simulations.")
    parser.add_argument("--output-dir", default="outputs/data", help="Directory for the JSON summary.")
    args = parser.parse_args()

    ensure_directory(args.output_dir)
    payload = evaluate_window_matrix()
    output_path = Path(args.output_dir) / "window_matrix_summary.json"
    export_json(str(output_path), payload)
    print(f"Wrote {payload['count']} window matrix simulations to {output_path}")


if __name__ == "__main__":
    main()
