import csv
import json
import tempfile
import unittest
from pathlib import Path
import sys
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from digital_twin.core.public_dataset_alignment import normalize_cu_bems_dataset, normalize_sml2010_dataset
from digital_twin.core.public_dataset_benchmark import run_public_dataset_benchmark


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class PublicDatasetBenchmarkTests(unittest.TestCase):
    def test_normalize_cu_bems_dataset_aggregates_zone_power_and_sensors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "cu-bems"
            output_dir = root / "normalized"
            input_dir.mkdir(parents=True, exist_ok=True)
            (input_dir / "2019Floor2.csv").write_text(
                "timestamp,Zone1_Temperature,Zone1_Humidity,Zone1_AmbientLight,Zone1_AC1_kW,Zone1_AC2_kW,Zone1_Lighting_kW,Zone1_Plug_kW\n"
                "2019-01-01 08:00:00,24.5,55.0,120.0,0.5,0.0,1.5,0.2\n"
                "2,99.0,99.0,999.0,9.0,9.0,9.0,9.0\n"
                "2019-01-01 08:01:00,24.2,54.5,135.0,1.0,0.5,2.0,0.4\n",
                encoding="utf-8",
            )

            summary = normalize_cu_bems_dataset(input_path=input_dir, output_dir=output_dir)

            sensor_rows = _read_csv_rows(output_dir / "corner_sensor_timeseries.csv")
            device_rows = _read_csv_rows(output_dir / "device_event_log.csv")
            auxiliary_rows = _read_csv_rows(output_dir / "auxiliary_features.csv")
            metadata = json.loads((output_dir / "scenario_metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["dataset"], "CU-BEMS")
            self.assertEqual(len(sensor_rows), 2)
            self.assertEqual(sensor_rows[0]["sensor_name"], "floor2_zone1_sensor")
            self.assertEqual(len(device_rows), 4)
            self.assertEqual(device_rows[1]["device_name"], "floor2_zone1_light_main")
            self.assertEqual(float(device_rows[2]["power"]), 1.5)
            self.assertEqual(float(device_rows[2]["activation"]), 1.0)
            self.assertEqual(len(auxiliary_rows), 2)
            self.assertEqual(auxiliary_rows[1]["plug_load_kw"], "0.4")
            self.assertEqual(metadata["counts"]["zones"], 1)
            self.assertEqual(summary["raw_timestamp_range"]["start"], "2019-01-01T08:00:00")

    def test_normalize_sml2010_dataset_creates_two_point_and_outdoor_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_dir = root / "sml2010"
            output_dir = root / "normalized"
            input_dir.mkdir(parents=True, exist_ok=True)
            (input_dir / "NEW-DATA-1.T15.txt").write_text(
                "# SML2010 sample\n"
                "01/04/2012;08:00:00;21.0;22.0;19.5;450;500;48.0;47.0;210.0;180.0;0.0;0;1.2;4000;2500;3200;350;0;0;0;18.0;65.0;7\n"
                "01/04/2012;13:00:00;23.0;24.0;26.0;500;540;45.0;44.0;420.0;390.0;0.0;0;2.0;15000;9000;12000;600;1;0;0;27.0;55.0;7\n",
                encoding="utf-8",
            )

            summary = normalize_sml2010_dataset(input_path=input_dir, output_dir=output_dir)

            sensor_rows = _read_csv_rows(output_dir / "corner_sensor_timeseries.csv")
            outdoor_rows = _read_csv_rows(output_dir / "outdoor_environment.csv")
            auxiliary_rows = _read_csv_rows(output_dir / "auxiliary_features.csv")
            metadata = json.loads((output_dir / "scenario_metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["dataset"], "SML2010")
            self.assertEqual(len(sensor_rows), 4)
            self.assertEqual(sensor_rows[0]["sensor_name"], "dining_room")
            self.assertEqual(sensor_rows[1]["sensor_name"], "room")
            self.assertEqual(len(outdoor_rows), 2)
            self.assertEqual(outdoor_rows[0]["time_of_day"], "morning")
            self.assertEqual(outdoor_rows[1]["weather"], "sunny")
            self.assertEqual(len(auxiliary_rows), 2)
            self.assertEqual(auxiliary_rows[1]["enthalpic_motor_1"], "1.0")
            self.assertEqual(metadata["counts"]["points"], 2)

    def test_run_cu_bems_benchmark_improves_over_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            dataset_dir = root / "cu_bems"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            self._write_cu_bems_normalized_fixture(dataset_dir)

            summary = run_public_dataset_benchmark("cu-bems", dataset_dir, horizons=[1])

            c1 = next(task for task in summary["tasks"] if task["task_id"] == "C1")
            c2 = next(task for task in summary["tasks"] if task["task_id"] == "C2")
            self.assertEqual(c1["status"], "ok")
            self.assertLess(
                c1["targets"]["temperature"]["linear_regression"]["mae"],
                c1["targets"]["temperature"]["persistence"]["mae"],
            )
            self.assertLess(
                c2["targets"]["illuminance"]["linear_regression"]["mae"],
                c2["targets"]["illuminance"]["persistence"]["mae"],
            )

    def test_run_cu_bems_benchmark_from_source_files_skips_invalid_timestamp_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            dataset_dir = root / "cu_bems"
            raw_dir = root / "raw"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_file = raw_dir / "2019Floor2.csv"
            raw_file.write_text(
                "Date,z1_AC1(kW),z1_Light(kW),z1_Plug(kW),z1_S1(degC),z1_S1(RH%),z1_S1(lux)\n"
                "2019-01-01 08:00:00,0.0,0.0,0.2,25.00,55.00,100.00\n"
                "2019-01-01 08:01:00,1.0,0.0,0.2,24.80,54.90,99.70\n"
                "2019-01-01 08:02:00,1.0,1.0,0.1,24.61,54.80,111.40\n"
                "2,9.0,9.0,9.0,99.00,99.00,999.00\n"
                "2019-01-01 08:03:00,0.0,1.0,0.1,24.615,54.802,123.25\n"
                "2019-01-01 08:04:00,0.0,0.0,0.2,24.620,54.806,122.95\n"
                "2019-01-01 08:05:00,1.2,0.0,0.2,24.390,54.690,122.65\n"
                "2019-01-01 08:06:00,1.2,1.3,0.2,24.160,54.574,138.25\n"
                "2019-01-01 08:07:00,0.0,1.3,0.1,24.165,54.576,153.70\n",
                encoding="utf-8",
            )
            (dataset_dir / "scenario_metadata.json").write_text(
                json.dumps(
                    {
                        "dataset": "CU-BEMS",
                        "source_files": [str(raw_file)],
                        "counts": {"zones": 1, "sensor_rows": 8, "device_rows": 16, "auxiliary_rows": 8},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            summary = run_public_dataset_benchmark("cu-bems", dataset_dir, horizons=[1])

            c1 = next(task for task in summary["tasks"] if task["task_id"] == "C1")
            c2 = next(task for task in summary["tasks"] if task["task_id"] == "C2")
            self.assertEqual(c1["status"], "ok")
            self.assertEqual(c2["status"], "ok")
            self.assertGreaterEqual(c1["sample_count"], 4)

    def test_run_sml2010_benchmark_improves_over_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            dataset_dir = root / "sml2010"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            self._write_sml2010_normalized_fixture(dataset_dir)

            summary = run_public_dataset_benchmark("sml2010", dataset_dir, horizons=[1])

            s1 = next(task for task in summary["tasks"] if task["task_id"] == "S1")
            s2 = next(task for task in summary["tasks"] if task["task_id"] == "S2")
            self.assertEqual(s1["status"], "ok")
            self.assertLess(
                s1["targets"]["dining_illuminance"]["linear_regression"]["mae"],
                s1["targets"]["dining_illuminance"]["persistence"]["mae"],
            )
            self.assertLess(
                s2["targets"]["room_temperature"]["linear_regression"]["mae"],
                s2["targets"]["room_temperature"]["persistence"]["mae"],
            )

    def _write_cu_bems_normalized_fixture(self, dataset_dir: Path) -> None:
        base_time = datetime(2019, 1, 1, 8, 0, 0)
        times = [base_time + timedelta(minutes=index) for index in range(12)]
        ac_power = [0.0, 1.0, 1.5, 0.0, 0.0, 1.2, 1.4, 0.0, 0.5, 0.0, 1.1, 0.0]
        light_power = [0.0, 0.0, 1.0, 1.5, 0.0, 0.0, 1.2, 1.6, 0.0, 0.0, 1.3, 1.7]
        plug_load = [0.2, 0.3, 0.1, 0.25, 0.15, 0.2, 0.35, 0.1, 0.2, 0.15, 0.25, 0.05]

        temperatures = [25.0]
        humidities = [55.0]
        illuminance = [120.0]
        for index in range(len(times) - 1):
            temperatures.append(temperatures[-1] - 0.4 * ac_power[index] + 0.05 * plug_load[index])
            humidities.append(humidities[-1] - 0.2 * ac_power[index] + 0.02 * plug_load[index])
            illuminance.append(illuminance[-1] + 12.0 * light_power[index] - 1.5 * plug_load[index])

        self._write_csv(
            dataset_dir / "corner_sensor_timeseries.csv",
            ["timestamp", "sensor_name", "x", "y", "z", "temperature_c", "humidity_pct", "illuminance_lux"],
            [
                {
                    "timestamp": times[index].strftime("%Y-%m-%dT%H:%M:%S"),
                    "sensor_name": "floor2_zone1_sensor",
                    "x": 3.0,
                    "y": 2.0,
                    "z": 2.8,
                    "temperature_c": round(temperatures[index], 6),
                    "humidity_pct": round(humidities[index], 6),
                    "illuminance_lux": round(illuminance[index], 6),
                }
                for index in range(len(times))
            ],
        )
        device_rows = []
        for index, stamp in enumerate(times):
            device_rows.append(
                {
                    "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "device_name": "floor2_zone1_ac_main",
                    "device_kind": "ac",
                    "event_type": "power_sample",
                    "is_active": 1 if ac_power[index] > 0 else 0,
                    "activation": ac_power[index] / 1.5 if ac_power[index] > 0 else 0.0,
                    "power": ac_power[index],
                    "mode": "",
                    "target_temperature_c": "",
                    "opening_ratio": "",
                    "horizontal_mode": "",
                    "horizontal_angle_deg": "",
                    "vertical_mode": "",
                    "vertical_angle_deg": "",
                    "x": 0.3,
                    "y": 2.0,
                    "z": 2.7,
                    "orientation_deg": 0.0,
                }
            )
            device_rows.append(
                {
                    "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "device_name": "floor2_zone1_light_main",
                    "device_kind": "light",
                    "event_type": "power_sample",
                    "is_active": 1 if light_power[index] > 0 else 0,
                    "activation": light_power[index] / 1.7 if light_power[index] > 0 else 0.0,
                    "power": light_power[index],
                    "mode": "",
                    "target_temperature_c": "",
                    "opening_ratio": "",
                    "horizontal_mode": "",
                    "horizontal_angle_deg": "",
                    "vertical_mode": "",
                    "vertical_angle_deg": "",
                    "x": 3.0,
                    "y": 2.0,
                    "z": 2.8,
                    "orientation_deg": 0.0,
                }
            )
        self._write_csv(
            dataset_dir / "device_event_log.csv",
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
            device_rows,
        )
        self._write_csv(
            dataset_dir / "outdoor_environment.csv",
            ["timestamp", "outdoor_temperature_c", "outdoor_humidity_pct", "sunlight_illuminance_lux", "daylight_factor", "season", "weather", "time_of_day"],
            [],
        )
        self._write_csv(
            dataset_dir / "auxiliary_features.csv",
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
            [
                {
                    "timestamp": times[index].strftime("%Y-%m-%dT%H:%M:%S"),
                    "dataset": "CU-BEMS",
                    "entity_id": "floor2_zone1",
                    "floor": 2,
                    "zone": 1,
                    "plug_load_kw": plug_load[index],
                    "notes": "fixture",
                }
                for index in range(len(times))
            ],
        )
        (dataset_dir / "scenario_metadata.json").write_text(json.dumps({"dataset": "CU-BEMS"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_sml2010_normalized_fixture(self, dataset_dir: Path) -> None:
        base_time = datetime(2012, 4, 1, 8, 0, 0)
        times = [base_time + timedelta(minutes=index) for index in range(12)]
        sunlight = [1000, 1500, 2000, 5000, 9000, 14000, 12000, 7000, 3000, 1000, 500, 200]
        outdoor_temp = [18.0, 18.5, 19.0, 20.0, 21.0, 23.0, 24.0, 23.0, 22.0, 20.5, 19.5, 19.0]
        outdoor_hum = [65.0, 64.0, 63.0, 61.0, 60.0, 58.0, 57.0, 58.5, 60.0, 62.0, 63.0, 64.0]
        rain = [0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0]
        wind = [1.0, 1.2, 1.4, 1.0, 0.8, 1.8, 2.2, 1.6, 1.1, 1.0, 0.9, 0.8]
        motors = [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0]

        dining_temp = [21.0]
        room_temp = [22.0]
        dining_hum = [48.0]
        room_hum = [47.0]
        dining_illum = [180.0]
        room_illum = [150.0]
        for index in range(len(times) - 1):
            dining_temp.append(dining_temp[-1] + 0.08 * (outdoor_temp[index] - dining_temp[-1]) + 0.0002 * sunlight[index] - 0.3 * rain[index])
            room_temp.append(room_temp[-1] + 0.06 * (outdoor_temp[index] - room_temp[-1]) + 0.00015 * sunlight[index] - 0.25 * rain[index])
            dining_hum.append(dining_hum[-1] + 0.1 * (outdoor_hum[index] - dining_hum[-1]) + 0.03 * rain[index])
            room_hum.append(room_hum[-1] + 0.08 * (outdoor_hum[index] - room_hum[-1]) + 0.025 * rain[index])
            dining_illum.append(dining_illum[-1] * 0.6 + 0.02 * sunlight[index] - 25.0 * rain[index])
            room_illum.append(room_illum[-1] * 0.7 + 0.015 * sunlight[index] - 20.0 * rain[index])

        sensor_rows = []
        for index, stamp in enumerate(times):
            sensor_rows.append(
                {
                    "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "sensor_name": "dining_room",
                    "x": 1.8,
                    "y": 2.0,
                    "z": 1.2,
                    "temperature_c": round(dining_temp[index], 6),
                    "humidity_pct": round(dining_hum[index], 6),
                    "illuminance_lux": round(dining_illum[index], 6),
                }
            )
            sensor_rows.append(
                {
                    "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "sensor_name": "room",
                    "x": 4.2,
                    "y": 2.0,
                    "z": 1.2,
                    "temperature_c": round(room_temp[index], 6),
                    "humidity_pct": round(room_hum[index], 6),
                    "illuminance_lux": round(room_illum[index], 6),
                }
            )
        self._write_csv(
            dataset_dir / "corner_sensor_timeseries.csv",
            ["timestamp", "sensor_name", "x", "y", "z", "temperature_c", "humidity_pct", "illuminance_lux"],
            sensor_rows,
        )
        self._write_csv(
            dataset_dir / "device_event_log.csv",
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
            [],
        )
        self._write_csv(
            dataset_dir / "outdoor_environment.csv",
            ["timestamp", "outdoor_temperature_c", "outdoor_humidity_pct", "sunlight_illuminance_lux", "daylight_factor", "season", "weather", "time_of_day"],
            [
                {
                    "timestamp": times[index].strftime("%Y-%m-%dT%H:%M:%S"),
                    "outdoor_temperature_c": outdoor_temp[index],
                    "outdoor_humidity_pct": outdoor_hum[index],
                    "sunlight_illuminance_lux": sunlight[index],
                    "daylight_factor": 0.95,
                    "season": "spring",
                    "weather": "rainy" if rain[index] > 0.1 else ("sunny" if sunlight[index] > 8000 else "cloudy"),
                    "time_of_day": "morning" if index < 4 else ("noon" if index < 7 else "afternoon"),
                }
                for index in range(len(times))
            ],
        )
        self._write_csv(
            dataset_dir / "auxiliary_features.csv",
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
            [
                {
                    "timestamp": times[index].strftime("%Y-%m-%dT%H:%M:%S"),
                    "dataset": "SML2010",
                    "entity_id": "global",
                    "co2_dining_ppm": 450 + index * 3,
                    "co2_room_ppm": 500 + index * 2,
                    "rain_ratio": rain[index],
                    "sun_dusk_flag": 0,
                    "wind_speed_m_s": wind[index],
                    "facade_west_lux": sunlight[index] * 0.5,
                    "facade_east_lux": sunlight[index] * 0.3,
                    "facade_south_lux": sunlight[index] * 0.4,
                    "sun_irradiance_w_m2": sunlight[index] / 20.0,
                    "forecast_temperature_c": outdoor_temp[index] + 0.5,
                    "enthalpic_motor_1": motors[index],
                    "enthalpic_motor_2": 0,
                    "enthalpic_motor_turbo": 0,
                    "day_of_week": 7,
                    "notes": "fixture",
                }
                for index in range(len(times))
            ],
        )
        (dataset_dir / "scenario_metadata.json").write_text(json.dumps({"dataset": "SML2010"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_csv(self, path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)