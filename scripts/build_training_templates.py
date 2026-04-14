import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "data_templates"


def write_csv_template(filename: str, headers: list[str]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
    return path


def write_json_template(filename: str, payload: object) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    generated = [
        write_csv_template(
            "corner_sensor_timeseries_template.csv",
            [
                "timestamp",
                "sensor_name",
                "x",
                "y",
                "z",
                "temperature_c",
                "humidity_pct",
                "illuminance_lux",
            ],
        ),
        write_csv_template(
            "device_event_log_template.csv",
            [
                "timestamp",
                "device_name",
                "device_kind",
                "event_type",
                "is_active",
                "activation",
                "power",
                "mode",
                "target_temperature_c",
                "opening_ratio",
                "horizontal_mode",
                "horizontal_angle_deg",
                "vertical_mode",
                "vertical_angle_deg",
                "x",
                "y",
                "z",
                "orientation_deg",
            ],
        ),
        write_csv_template(
            "outdoor_environment_template.csv",
            [
                "timestamp",
                "outdoor_temperature_c",
                "outdoor_humidity_pct",
                "sunlight_illuminance_lux",
                "daylight_factor",
                "season",
                "weather",
                "time_of_day",
            ],
        ),
        write_csv_template(
            "spatial_probe_ground_truth_template.csv",
            [
                "timestamp",
                "point_name",
                "x",
                "y",
                "z",
                "temperature_c",
                "humidity_pct",
                "illuminance_lux",
            ],
        ),
        write_json_template(
            "scenario_metadata_template.json",
            {
                "room": {
                    "width_m": 6.0,
                    "depth_m": 4.0,
                    "height_m": 3.0,
                },
                "sampling": {
                    "grid_x": 16,
                    "grid_y": 12,
                    "grid_z": 6,
                    "elapsed_minutes": 60,
                },
                "indoor_baseline": {
                    "temperature_c": 29.0,
                    "humidity_pct": 63.0,
                    "base_illuminance_lux": 180.0,
                },
                "target_zone": "center",
                "notes": "Fill this file once per experiment run to align sensor, device, and outdoor logs.",
            },
        ),
    ]

    print("Wrote training data templates:")
    for path in generated:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
