import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


CORNER_SENSOR_HEADERS = [
    "timestamp",
    "sensor_name",
    "x",
    "y",
    "z",
    "temperature_c",
    "humidity_pct",
    "illuminance_lux",
]

DEVICE_EVENT_HEADERS = [
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
]

OUTDOOR_HEADERS = [
    "timestamp",
    "outdoor_temperature_c",
    "outdoor_humidity_pct",
    "sunlight_illuminance_lux",
    "daylight_factor",
    "season",
    "weather",
    "time_of_day",
]

AUXILIARY_HEADERS = [
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
]

SML2010_COLUMNS = [
    "date",
    "time",
    "temperature_dining_c",
    "temperature_room_c",
    "forecast_temperature_c",
    "co2_dining_ppm",
    "co2_room_ppm",
    "humidity_dining_pct",
    "humidity_room_pct",
    "illuminance_dining_lux",
    "illuminance_room_lux",
    "rain_ratio",
    "sun_dusk_flag",
    "wind_speed_m_s",
    "sunlight_west_lux",
    "sunlight_east_lux",
    "sunlight_south_lux",
    "sun_irradiance_w_m2",
    "enthalpic_motor_1",
    "enthalpic_motor_2",
    "enthalpic_motor_turbo",
    "outdoor_temperature_c",
    "outdoor_humidity_pct",
    "day_of_week",
]

_CU_BEMS_SENSOR_POSITION = {"x": 3.0, "y": 2.0, "z": 2.8}
_CU_BEMS_DEVICE_POSITIONS = {
    "ac_main": {"x": 0.3, "y": 2.0, "z": 2.7, "orientation_deg": 0.0},
    "light_main": {"x": 3.0, "y": 2.0, "z": 2.8, "orientation_deg": 0.0},
}
_SML2010_SENSOR_POSITIONS = {
    "dining_room": {"x": 1.8, "y": 2.0, "z": 1.2},
    "room": {"x": 4.2, "y": 2.0, "z": 1.2},
}


def normalize_public_dataset(dataset: str, input_path: Path, output_root: Path) -> Dict[str, object]:
    dataset_key = dataset.strip().lower()
    if dataset_key == "cu-bems":
        return normalize_cu_bems_dataset(input_path=input_path, output_dir=output_root / "cu_bems")
    if dataset_key == "sml2010":
        return normalize_sml2010_dataset(input_path=input_path, output_dir=output_root / "sml2010")
    raise ValueError(f"Unsupported dataset: {dataset}")


def normalize_cu_bems_dataset(input_path: Path, output_dir: Path) -> Dict[str, object]:
    source_files = sorted(input_path.glob("*.csv"))
    if not source_files:
        raise FileNotFoundError(f"No CSV files found in {input_path}")

    sensor_rows: List[Dict[str, object]] = []
    device_samples: List[Dict[str, object]] = []
    outdoor_rows: List[Dict[str, object]] = []
    auxiliary_rows: List[Dict[str, object]] = []
    timestamps: List[str] = []
    zones_seen: Dict[str, Dict[str, object]] = {}

    for source_file in source_files:
        floor = _extract_floor_number(source_file.name)
        with source_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            if not headers:
                continue
            time_column = _infer_time_column(headers)
            zone_mapping = infer_cu_bems_zone_mapping(headers)
            for zone_number in zone_mapping:
                zone_id = _format_zone_id(floor, zone_number)
                zones_seen[zone_id] = {
                    "floor": floor,
                    "zone": zone_number,
                    "sensor_name": f"{zone_id}_sensor",
                }

            for row in reader:
                normalized_timestamp = _normalize_timestamp(row.get(time_column, ""))
                parsed_timestamp = _parse_timestamp(normalized_timestamp)
                if parsed_timestamp is None:
                    continue
                timestamp = parsed_timestamp.strftime("%Y-%m-%dT%H:%M:%S")
                timestamps.append(timestamp)
                for zone_number, mapping in zone_mapping.items():
                    zone_id = _format_zone_id(floor, zone_number)
                    sensor_name = f"{zone_id}_sensor"

                    temperature = _first_float(row, mapping["temperature"])
                    humidity = _first_float(row, mapping["humidity"])
                    illuminance = _first_float(row, mapping["illuminance"])
                    if any(value is not None for value in (temperature, humidity, illuminance)):
                        sensor_rows.append(
                            {
                                "timestamp": timestamp,
                                "sensor_name": sensor_name,
                                "x": _CU_BEMS_SENSOR_POSITION["x"],
                                "y": _CU_BEMS_SENSOR_POSITION["y"],
                                "z": _CU_BEMS_SENSOR_POSITION["z"],
                                "temperature_c": temperature,
                                "humidity_pct": humidity,
                                "illuminance_lux": illuminance,
                            }
                        )

                    ac_power = _sum_columns(row, mapping["ac_power"])
                    lighting_power = _sum_columns(row, mapping["lighting_power"])
                    plug_power = _sum_columns(row, mapping["plug_power"])

                    if mapping["ac_power"] and ac_power is not None:
                        device_samples.append(
                            {
                                "timestamp": timestamp,
                                "zone_id": zone_id,
                                "device_name": f"{zone_id}_ac_main",
                                "device_kind": "ac",
                                "power": ac_power,
                            }
                        )
                    if mapping["lighting_power"] and lighting_power is not None:
                        device_samples.append(
                            {
                                "timestamp": timestamp,
                                "zone_id": zone_id,
                                "device_name": f"{zone_id}_light_main",
                                "device_kind": "light",
                                "power": lighting_power,
                            }
                        )
                    if mapping["plug_power"] and plug_power is not None:
                        auxiliary_rows.append(
                            {
                                "timestamp": timestamp,
                                "dataset": "CU-BEMS",
                                "entity_id": zone_id,
                                "floor": floor,
                                "zone": zone_number,
                                "plug_load_kw": plug_power,
                                "notes": "zone-level plug load retained as auxiliary feature",
                            }
                        )

    device_rows = _finalize_device_rows(device_samples)
    generated_files = _write_normalized_outputs(
        output_dir=output_dir,
        sensor_rows=sensor_rows,
        device_rows=device_rows,
        outdoor_rows=outdoor_rows,
        auxiliary_rows=auxiliary_rows,
    )
    metadata = {
        "dataset": "CU-BEMS",
        "benchmark_mode": "single-zone device-response",
        "source_files": [str(path) for path in source_files],
        "raw_timestamp_range": _timestamp_range(timestamps),
        "counts": {
            "sensor_rows": len(sensor_rows),
            "device_rows": len(device_rows),
            "outdoor_rows": len(outdoor_rows),
            "auxiliary_rows": len(auxiliary_rows),
            "zones": len(zones_seen),
        },
        "zones": [zones_seen[key] for key in sorted(zones_seen)],
        "pseudo_geometry": {
            "room": {"width_m": 6.0, "depth_m": 4.0, "height_m": 3.0},
            "sensor": _CU_BEMS_SENSOR_POSITION,
            "ac_main": _CU_BEMS_DEVICE_POSITIONS["ac_main"],
            "light_main": _CU_BEMS_DEVICE_POSITIONS["light_main"],
            "target_zone": "center_zone",
        },
        "tasks": ["C1", "C2", "C3"],
        "unsupported": [
            "full 3D field MAE",
            "8-corner sensor calibration benchmark",
            "window direct-input benchmark without external weather backfill",
        ],
        "notes": [
            "One floor-zone with sensor data is treated as one pseudo sensor.",
            "All AC power columns in the same zone are aggregated into ac_main.",
            "Plug load is retained only as an auxiliary feature.",
        ],
    }
    return _finalize_summary(output_dir=output_dir, generated_files=generated_files, metadata=metadata)


def normalize_sml2010_dataset(input_path: Path, output_dir: Path) -> Dict[str, object]:
    if input_path.is_dir():
        source_files = sorted(input_path.glob("NEW-DATA-*.T15.txt")) or sorted(input_path.glob("*.txt"))
    else:
        source_files = [input_path]
    if not source_files:
        raise FileNotFoundError(f"No SML2010 files found in {input_path}")

    sensor_rows: List[Dict[str, object]] = []
    device_rows: List[Dict[str, object]] = []
    outdoor_rows: List[Dict[str, object]] = []
    auxiliary_rows: List[Dict[str, object]] = []
    timestamps: List[str] = []

    for source_file in source_files:
        for record in _read_sml2010_records(source_file):
            timestamp = _normalize_sml2010_timestamp(record["date"], record["time"])
            if not timestamp:
                continue
            timestamps.append(timestamp)

            sensor_rows.append(
                {
                    "timestamp": timestamp,
                    "sensor_name": "dining_room",
                    "x": _SML2010_SENSOR_POSITIONS["dining_room"]["x"],
                    "y": _SML2010_SENSOR_POSITIONS["dining_room"]["y"],
                    "z": _SML2010_SENSOR_POSITIONS["dining_room"]["z"],
                    "temperature_c": _to_float(record["temperature_dining_c"]),
                    "humidity_pct": _to_float(record["humidity_dining_pct"]),
                    "illuminance_lux": _to_float(record["illuminance_dining_lux"]),
                }
            )
            sensor_rows.append(
                {
                    "timestamp": timestamp,
                    "sensor_name": "room",
                    "x": _SML2010_SENSOR_POSITIONS["room"]["x"],
                    "y": _SML2010_SENSOR_POSITIONS["room"]["y"],
                    "z": _SML2010_SENSOR_POSITIONS["room"]["z"],
                    "temperature_c": _to_float(record["temperature_room_c"]),
                    "humidity_pct": _to_float(record["humidity_room_pct"]),
                    "illuminance_lux": _to_float(record["illuminance_room_lux"]),
                }
            )

            sunlight_values = [
                _to_float(record["sunlight_west_lux"]),
                _to_float(record["sunlight_east_lux"]),
                _to_float(record["sunlight_south_lux"]),
            ]
            sunlight_illuminance = max((value for value in sunlight_values if value is not None), default=0.0)
            parsed_timestamp = _parse_timestamp(timestamp)
            outdoor_rows.append(
                {
                    "timestamp": timestamp,
                    "outdoor_temperature_c": _to_float(record["outdoor_temperature_c"]),
                    "outdoor_humidity_pct": _to_float(record["outdoor_humidity_pct"]),
                    "sunlight_illuminance_lux": sunlight_illuminance,
                    "daylight_factor": 0.95 if sunlight_illuminance > 0.0 else 0.0,
                    "season": _infer_season(parsed_timestamp),
                    "weather": _infer_weather(
                        rain_ratio=_to_float(record["rain_ratio"]),
                        sunlight_illuminance=sunlight_illuminance,
                        sun_irradiance=_to_float(record["sun_irradiance_w_m2"]),
                    ),
                    "time_of_day": _infer_time_of_day(parsed_timestamp),
                }
            )
            auxiliary_rows.append(
                {
                    "timestamp": timestamp,
                    "dataset": "SML2010",
                    "entity_id": "global",
                    "co2_dining_ppm": _to_float(record["co2_dining_ppm"]),
                    "co2_room_ppm": _to_float(record["co2_room_ppm"]),
                    "rain_ratio": _to_float(record["rain_ratio"]),
                    "sun_dusk_flag": _to_float(record["sun_dusk_flag"]),
                    "wind_speed_m_s": _to_float(record["wind_speed_m_s"]),
                    "facade_west_lux": _to_float(record["sunlight_west_lux"]),
                    "facade_east_lux": _to_float(record["sunlight_east_lux"]),
                    "facade_south_lux": _to_float(record["sunlight_south_lux"]),
                    "sun_irradiance_w_m2": _to_float(record["sun_irradiance_w_m2"]),
                    "forecast_temperature_c": _to_float(record["forecast_temperature_c"]),
                    "enthalpic_motor_1": _to_float(record["enthalpic_motor_1"]),
                    "enthalpic_motor_2": _to_float(record["enthalpic_motor_2"]),
                    "enthalpic_motor_turbo": _to_float(record["enthalpic_motor_turbo"]),
                    "day_of_week": _to_float(record["day_of_week"]),
                    "notes": "two-point boundary-response benchmark",
                }
            )

    generated_files = _write_normalized_outputs(
        output_dir=output_dir,
        sensor_rows=sensor_rows,
        device_rows=device_rows,
        outdoor_rows=outdoor_rows,
        auxiliary_rows=auxiliary_rows,
    )
    metadata = {
        "dataset": "SML2010",
        "benchmark_mode": "two-point boundary-response",
        "source_files": [str(path) for path in source_files],
        "raw_timestamp_range": _timestamp_range(timestamps),
        "counts": {
            "sensor_rows": len(sensor_rows),
            "device_rows": len(device_rows),
            "outdoor_rows": len(outdoor_rows),
            "auxiliary_rows": len(auxiliary_rows),
            "points": 2,
        },
        "pseudo_geometry": {
            "room": {"width_m": 6.0, "depth_m": 4.0, "height_m": 3.0},
            "dining_room_sensor": _SML2010_SENSOR_POSITIONS["dining_room"],
            "room_sensor": _SML2010_SENSOR_POSITIONS["room"],
            "target_points": ["dining_room", "room"],
        },
        "tasks": ["S1", "S2", "S3"],
        "unsupported": [
            "explicit window on/off benchmark",
            "full 3D field MAE",
            "non-networked appliance coefficient learning from explicit appliance states",
        ],
        "notes": [
            "Date and Time are normalized into one timestamp column.",
            "Facade sunlight is retained as auxiliary features and also reduced to one scalar sunlight input.",
            "Enthalpic motors are retained as auxiliary HVAC or ventilation features only.",
        ],
    }
    return _finalize_summary(output_dir=output_dir, generated_files=generated_files, metadata=metadata)


def infer_cu_bems_zone_mapping(headers: Sequence[str]) -> Dict[int, Dict[str, object]]:
    groups: Dict[int, Dict[str, object]] = {}
    for header in headers:
        zone_number = _extract_zone_number(header)
        if zone_number is None:
            continue
        bucket = groups.setdefault(
            zone_number,
            {
                "temperature": None,
                "humidity": None,
                "illuminance": None,
                "ac_power": [],
                "lighting_power": [],
                "plug_power": [],
                "ambiguous_light": [],
            },
        )
        kind = _classify_cu_bems_header(header)
        if kind == "temperature" and bucket["temperature"] is None:
            bucket["temperature"] = header
        elif kind == "humidity" and bucket["humidity"] is None:
            bucket["humidity"] = header
        elif kind == "illuminance" and bucket["illuminance"] is None:
            bucket["illuminance"] = header
        elif kind == "ac_power":
            bucket["ac_power"].append(header)
        elif kind == "lighting_power":
            bucket["lighting_power"].append(header)
        elif kind == "plug_power":
            bucket["plug_power"].append(header)
        elif kind == "ambiguous_light":
            bucket["ambiguous_light"].append(header)

    for bucket in groups.values():
        ambiguous = list(bucket.pop("ambiguous_light"))
        if not ambiguous:
            continue
        if bucket["illuminance"] is None:
            bucket["illuminance"] = ambiguous.pop(0)
        bucket["lighting_power"].extend(ambiguous)
    return groups


def _write_normalized_outputs(
    output_dir: Path,
    sensor_rows: List[Dict[str, object]],
    device_rows: List[Dict[str, object]],
    outdoor_rows: List[Dict[str, object]],
    auxiliary_rows: List[Dict[str, object]],
) -> List[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: List[str] = []
    generated_files.append(str(_write_csv(output_dir / "corner_sensor_timeseries.csv", CORNER_SENSOR_HEADERS, sensor_rows)))
    generated_files.append(str(_write_csv(output_dir / "device_event_log.csv", DEVICE_EVENT_HEADERS, device_rows)))
    generated_files.append(str(_write_csv(output_dir / "outdoor_environment.csv", OUTDOOR_HEADERS, outdoor_rows)))
    generated_files.append(str(_write_csv(output_dir / "auxiliary_features.csv", AUXILIARY_HEADERS, auxiliary_rows)))
    return generated_files


def _finalize_summary(output_dir: Path, generated_files: List[str], metadata: Dict[str, object]) -> Dict[str, object]:
    scenario_metadata_path = output_dir / "scenario_metadata.json"
    scenario_metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "dataset": metadata["dataset"],
        "benchmark_mode": metadata["benchmark_mode"],
        "generated_files": generated_files + [str(scenario_metadata_path)],
        "counts": metadata["counts"],
        "raw_timestamp_range": metadata["raw_timestamp_range"],
        "source_files": metadata["source_files"],
    }
    summary_path = output_dir / "normalization_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["generated_files"].append(str(summary_path))
    return summary


def _write_csv(path: Path, headers: Sequence[str], rows: Iterable[Dict[str, object]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({header: _csv_value(row.get(header)) for header in headers})
    return path


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    return value


def _finalize_device_rows(device_samples: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    maxima: Dict[tuple, float] = {}
    for sample in device_samples:
        key = (sample["zone_id"], sample["device_kind"])
        maxima[key] = max(maxima.get(key, 0.0), float(sample["power"]))

    rows: List[Dict[str, object]] = []
    for sample in device_samples:
        device_name = str(sample["device_name"])
        zone_id = str(sample["zone_id"])
        device_kind = str(sample["device_kind"])
        pseudo_name = f"{device_kind}_main"
        coords = _CU_BEMS_DEVICE_POSITIONS[pseudo_name]
        max_power = maxima.get((zone_id, device_kind), 0.0)
        power = float(sample["power"])
        rows.append(
            {
                "timestamp": sample["timestamp"],
                "device_name": device_name,
                "device_kind": device_kind,
                "event_type": "power_sample",
                "is_active": 1 if power > 1e-6 else 0,
                "activation": round(power / max_power, 6) if max_power > 1e-9 else 0.0,
                "power": power,
                "mode": "",
                "target_temperature_c": "",
                "opening_ratio": "",
                "horizontal_mode": "",
                "horizontal_angle_deg": "",
                "vertical_mode": "",
                "vertical_angle_deg": "",
                "x": coords["x"],
                "y": coords["y"],
                "z": coords["z"],
                "orientation_deg": coords["orientation_deg"],
            }
        )
    return rows


def _extract_floor_number(name: str) -> int:
    match = re.search(r"FLOOR\s*([0-9]+)", name.upper())
    return int(match.group(1)) if match else 0


def _extract_zone_number(header: str) -> Optional[int]:
    normalized = _normalize_label(header)
    for pattern in (
        r"(?:^|_)ZONE_?([0-9]+)(?:_|$)",
        r"(?:^|_)Z_?([0-9]+)(?:_|$)",
        r"ZONE([0-9]+)",
        r"Z([0-9]+)",
    ):
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))
    return None


def _format_zone_id(floor: int, zone_number: int) -> str:
    return f"floor{floor}_zone{zone_number}"


def _infer_time_column(headers: Sequence[str]) -> str:
    for header in headers:
        label = _normalize_label(header)
        if "TIMESTAMP" in label or label == "TIME":
            return header
    return headers[0]


def _classify_cu_bems_header(header: str) -> Optional[str]:
    label = _normalize_label(header)
    if "TEMP" in label or "DEGC" in label:
        return "temperature"
    if any(token in label for token in ("HUMIDITY", "_RH", "RH_", "_H_", "_HUM")):
        return "humidity"
    if any(token in label for token in ("AMBIENT", "ILLUMINANCE", "LUX")):
        return "illuminance"
    if "PLUG" in label:
        return "plug_power"
    if "LIGHTING" in label:
        return "lighting_power"
    if re.search(r"(?:^|_)AC[0-9_]*(?:_|$)", label) or "AIRCON" in label or "AIR_CON" in label:
        return "ac_power"
    if "LIGHT" in label:
        return "ambiguous_light"
    return None


def _normalize_label(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _first_float(row: Dict[str, str], column: Optional[str]) -> Optional[float]:
    if not column:
        return None
    return _to_float(row.get(column))


def _sum_columns(row: Dict[str, str], columns: Sequence[str]) -> Optional[float]:
    values = [_to_float(row.get(column)) for column in columns]
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered)


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.upper() in {"NA", "NAN", "NULL", "NONE", "?"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_timestamp(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = _parse_timestamp(text)
    return parsed.strftime("%Y-%m-%dT%H:%M:%S") if parsed else text


def _normalize_sml2010_timestamp(date_text: str, time_text: str) -> str:
    combined = f"{date_text} {time_text}".strip()
    parsed = _parse_timestamp(combined)
    if parsed:
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
    return combined


def _parse_timestamp(text: str) -> Optional[datetime]:
    value = text.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _timestamp_range(timestamps: Sequence[str]) -> Dict[str, str]:
    if not timestamps:
        return {"start": "", "end": ""}
    return {"start": min(timestamps), "end": max(timestamps)}


def _read_sml2010_records(path: Path) -> List[Dict[str, str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload_lines = [line for line in lines if not line.startswith("#")]
    if not payload_lines:
        return []

    rows = [_split_sml2010_line(line) for line in payload_lines]
    if rows and _looks_like_sml2010_header(rows[0]):
        rows = rows[1:]

    records: List[Dict[str, str]] = []
    for row in rows:
        if len(row) < len(SML2010_COLUMNS):
            continue
        records.append({column: row[index] for index, column in enumerate(SML2010_COLUMNS)})
    return records


def _split_sml2010_line(line: str) -> List[str]:
    if ";" in line:
        return [value.strip() for value in line.split(";")]
    if "," in line:
        return [value.strip() for value in next(csv.reader([line]))]
    if "\t" in line:
        return [value.strip() for value in line.split("\t")]
    return re.split(r"\s+", line.strip())


def _looks_like_sml2010_header(row: Sequence[str]) -> bool:
    if not row:
        return False
    joined = " ".join(row).lower()
    return any(token in joined for token in ("date", "time", "fecha", "hora", "temper", "lighting"))


def _infer_season(parsed_timestamp: Optional[datetime]) -> str:
    if parsed_timestamp is None:
        return ""
    month = parsed_timestamp.month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def _infer_time_of_day(parsed_timestamp: Optional[datetime]) -> str:
    if parsed_timestamp is None:
        return ""
    hour = parsed_timestamp.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    return "night"


def _infer_weather(
    rain_ratio: Optional[float],
    sunlight_illuminance: float,
    sun_irradiance: Optional[float],
) -> str:
    if rain_ratio is not None and rain_ratio > 0.1:
        return "rainy"
    if sunlight_illuminance > 12000.0 or (sun_irradiance is not None and sun_irradiance > 400.0):
        return "sunny"
    return "cloudy"