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


PAYLOAD = {
    "notes": [
        "This template aligns public datasets with the repo's existing training templates.",
        "Use shared-task benchmarks for CU-BEMS and SML2010 instead of forcing full 3D field reconstruction.",
        "Pseudo geometry is only for interface consistency and should not be reported as true room geometry.",
    ],
    "repo_templates": {
        "corner_sensor_timeseries": "outputs/data_templates/corner_sensor_timeseries_template.csv",
        "device_event_log": "outputs/data_templates/device_event_log_template.csv",
        "outdoor_environment": "outputs/data_templates/outdoor_environment_template.csv",
        "scenario_metadata": "outputs/data_templates/scenario_metadata_template.json",
        "spatial_probe_ground_truth": "outputs/data_templates/spatial_probe_ground_truth_template.csv",
        "auxiliary_features": "outputs/data_templates/public_benchmark_auxiliary_features_template.csv",
    },
    "datasets": [
        {
            "name": "CU-BEMS",
            "benchmark_mode": "single-zone device-response",
            "raw_layout": {
                "file_pattern": "outputs/data/raw_public/cu-bems/{year}Floor{floor}.csv",
                "time_column": "timestamp",
                "column_strategy": [
                    "headers are floor-specific and zone-prefixed",
                    "aggregate all AC power columns in the same zone into ac_main",
                    "map one lighting column per zone to light_main when available",
                    "keep plug load as an auxiliary feature rather than a controlled device",
                ],
            },
            "pseudo_geometry": {
                "room": {"width_m": 6.0, "depth_m": 4.0, "height_m": 3.0},
                "sensor": {"x": 3.0, "y": 2.0, "z": 2.8},
                "ac_main": {"x": 0.3, "y": 2.0, "z": 2.7},
                "light_main": {"x": 3.0, "y": 2.0, "z": 2.8},
                "target_zone": "center_zone",
            },
            "field_mapping": {
                "temperature": "zone temperature -> corner_sensor_timeseries.temperature_c",
                "humidity": "zone humidity -> corner_sensor_timeseries.humidity_pct",
                "illuminance": "zone ambient light -> corner_sensor_timeseries.illuminance_lux",
                "ac_power": "sum(zone AC columns) -> device_event_log.power",
                "lighting_power": "zone lighting kW -> device_event_log.power",
                "plug_power": "zone plug load kW -> auxiliary feature",
            },
            "benchmark_tasks": [
                {
                    "id": "C1",
                    "name": "AC response benchmark",
                    "outputs": ["zone temperature", "zone humidity"],
                    "metrics": ["MAE", "RMSE"],
                },
                {
                    "id": "C2",
                    "name": "Lighting response benchmark",
                    "outputs": ["zone illuminance"],
                    "metrics": ["MAE", "RMSE"],
                },
                {
                    "id": "C3",
                    "name": "Event delta benchmark",
                    "outputs": ["post-event delta"],
                    "metrics": ["delta_MAE", "correlation"],
                },
            ],
            "unsupported": [
                "full 3D field MAE",
                "8-corner sensor calibration benchmark",
                "window direct-input benchmark without external weather backfill",
            ],
        },
        {
            "name": "SML2010",
            "benchmark_mode": "two-point boundary-response",
            "raw_layout": {
                "file_pattern": "outputs/data/raw_public/sml2010/NEW-DATA-*.T15.txt",
                "time_columns": ["Date", "Time"],
                "parsing_notes": [
                    "the raw file starts with commented header lines in Spanish",
                    "parse by column order if the exported file does not preserve English names",
                ],
            },
            "pseudo_geometry": {
                "room": {"width_m": 6.0, "depth_m": 4.0, "height_m": 3.0},
                "dining_room_sensor": {"x": 1.8, "y": 2.0, "z": 1.2},
                "room_sensor": {"x": 4.2, "y": 2.0, "z": 1.2},
                "target_points": ["dining_room", "room"],
            },
            "field_mapping": {
                "indoor_temperature_dining": "corner_sensor_timeseries.temperature_c where sensor_name=dining_room",
                "indoor_temperature_room": "corner_sensor_timeseries.temperature_c where sensor_name=room",
                "indoor_humidity_dining": "corner_sensor_timeseries.humidity_pct where sensor_name=dining_room",
                "indoor_humidity_room": "corner_sensor_timeseries.humidity_pct where sensor_name=room",
                "indoor_light_dining": "corner_sensor_timeseries.illuminance_lux where sensor_name=dining_room",
                "indoor_light_room": "corner_sensor_timeseries.illuminance_lux where sensor_name=room",
                "outdoor_temperature": "outdoor_environment.outdoor_temperature_c",
                "outdoor_humidity": "outdoor_environment.outdoor_humidity_pct",
                "sunlight_facades": "outdoor_environment.sunlight_illuminance_lux plus facade-specific auxiliary features",
                "sun_irradiance": "outdoor_environment.sun_irradiance_w_m2",
                "rain": "outdoor_environment.rain_ratio",
                "wind": "outdoor_environment.wind_speed_m_s",
                "enthalpic_motors": "auxiliary HVAC or ventilation features; do not map directly to window_main",
            },
            "benchmark_tasks": [
                {
                    "id": "S1",
                    "name": "Daylight response benchmark",
                    "outputs": ["dining_room illuminance", "room illuminance"],
                    "metrics": ["MAE", "RMSE"],
                },
                {
                    "id": "S2",
                    "name": "Thermal-humidity benchmark",
                    "outputs": ["dining_room temperature", "room temperature", "dining_room humidity", "room humidity"],
                    "metrics": ["MAE", "RMSE"],
                },
                {
                    "id": "S3",
                    "name": "Boundary event delta benchmark",
                    "outputs": ["post-event delta"],
                    "metrics": ["delta_MAE"],
                },
            ],
            "unsupported": [
                "explicit window on/off benchmark",
                "full 3D field MAE",
                "non-networked appliance coefficient learning from explicit appliance states",
            ],
        },
    ],
}


def main() -> None:
    generated = [
        write_csv_template(
            "public_benchmark_auxiliary_features_template.csv",
            [
                "timestamp",
                "dataset",
                "entity_id",
                "floor",
                "zone",
                "plug_load_kw",
                "co2_dining_ppm",
                "co2_room_ppm",
                "rain_ratio",
                "sun_dusk_flag",
                "wind_speed_m_s",
                "facade_west_lux",
                "facade_east_lux",
                "facade_south_lux",
                "sun_irradiance_w_m2",
                "forecast_temperature_c",
                "enthalpic_motor_1",
                "enthalpic_motor_2",
                "enthalpic_motor_turbo",
                "day_of_week",
                "notes",
            ],
        )
    ]
    output_path = OUTPUT_DIR / "public_dataset_alignment_template.json"
    output_path.write_text(json.dumps(PAYLOAD, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generated.append(output_path)
    for path in generated:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()