import csv
import json
import math
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

from digital_twin.core.public_dataset_alignment import _extract_floor_number, _first_float, _infer_time_column, _normalize_timestamp, _parse_timestamp, _sum_columns, infer_cu_bems_zone_mapping
from digital_twin.core.math_utils import solve_linear_system


def run_public_dataset_benchmark(
    dataset: str,
    input_dir: Path,
    horizons: Sequence[int] = (15,),
) -> Dict[str, object]:
    dataset_key = dataset.strip().lower()
    if dataset_key == "cu-bems":
        return _run_cu_bems_benchmark(input_dir=input_dir, horizons=horizons)
    if dataset_key == "sml2010":
        return _run_sml2010_benchmark(input_dir=input_dir, horizons=horizons)
    raise ValueError(f"Unsupported dataset: {dataset}")


def write_public_dataset_benchmark_summary(summary: Dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _run_cu_bems_benchmark(input_dir: Path, horizons: Sequence[int]) -> Dict[str, object]:
    metadata = _read_optional_json(input_dir / "scenario_metadata.json")

    source_files = [Path(path) for path in metadata.get("source_files", []) if Path(path).exists()]
    if source_files:
        return _run_cu_bems_benchmark_from_source_files(
            input_dir=input_dir,
            horizons=horizons,
            metadata=metadata,
            source_files=source_files,
        )

    sensor_rows = _read_csv_rows(input_dir / "corner_sensor_timeseries.csv")
    device_rows = _read_csv_rows(input_dir / "device_event_log.csv")
    auxiliary_rows = _read_csv_rows(input_dir / "auxiliary_features.csv")

    records_by_zone = _load_cu_bems_records(sensor_rows, device_rows, auxiliary_rows)
    tasks: List[Dict[str, object]] = []
    for horizon in horizons:
        c1_samples = _build_cu_bems_response_samples(records_by_zone, horizon, task_id="C1")
        tasks.append(
            _evaluate_task(
                task_id="C1",
                dataset="CU-BEMS",
                horizon_minutes=horizon,
                feature_names=["temperature", "humidity", "ac_power", "plug_load", "ac_active"],
                target_names=["temperature", "humidity"],
                samples=c1_samples,
            )
        )
        c2_samples = _build_cu_bems_response_samples(records_by_zone, horizon, task_id="C2")
        tasks.append(
            _evaluate_task(
                task_id="C2",
                dataset="CU-BEMS",
                horizon_minutes=horizon,
                feature_names=["illuminance", "lighting_power", "plug_load", "light_active"],
                target_names=["illuminance"],
                samples=c2_samples,
            )
        )
        c3_samples = _build_cu_bems_event_delta_samples(records_by_zone, horizon)
        tasks.append(
            _evaluate_task(
                task_id="C3",
                dataset="CU-BEMS",
                horizon_minutes=horizon,
                feature_names=[
                    "temperature",
                    "humidity",
                    "illuminance",
                    "ac_power",
                    "lighting_power",
                    "plug_load",
                    "event_direction",
                    "event_kind_ac",
                    "event_kind_light",
                ],
                target_names=["temperature", "humidity", "illuminance"],
                samples=c3_samples,
                min_samples=10,
            )
        )

    return {
        "dataset": "CU-BEMS",
        "benchmark_mode": "single-zone device-response",
        "input_dir": str(input_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "horizons": list(horizons),
        "counts": {
            "zones": len(records_by_zone),
            "sensor_rows": len(sensor_rows),
            "device_rows": len(device_rows),
            "auxiliary_rows": len(auxiliary_rows),
        },
        "metadata": metadata,
        "tasks": tasks,
    }


def _run_cu_bems_benchmark_from_source_files(
    input_dir: Path,
    horizons: Sequence[int],
    metadata: Dict[str, object],
    source_files: Sequence[Path],
) -> Dict[str, object]:
    task_specs = {
        "C1": {
            "feature_names": ["temperature", "humidity", "ac_power", "plug_load", "ac_active"],
            "target_names": ["temperature", "humidity"],
            "min_samples": 4,
        },
        "C2": {
            "feature_names": ["illuminance", "lighting_power", "plug_load", "light_active"],
            "target_names": ["illuminance"],
            "min_samples": 4,
        },
        "C3": {
            "feature_names": [
                "temperature",
                "humidity",
                "illuminance",
                "ac_power",
                "lighting_power",
                "plug_load",
                "event_direction",
                "event_kind_ac",
                "event_kind_light",
            ],
            "target_names": ["temperature", "humidity", "illuminance"],
            "min_samples": 10,
        },
    }
    sample_counts = _count_cu_bems_samples_from_source_files(source_files=source_files, horizons=horizons)
    evaluators: Dict[Tuple[str, int], _StreamingTaskEvaluator] = {}
    for horizon in horizons:
        for task_id, spec in task_specs.items():
            sample_count = sample_counts.get((task_id, horizon), 0)
            if sample_count >= int(spec["min_samples"]):
                evaluators[(task_id, horizon)] = _StreamingTaskEvaluator(
                    task_id=task_id,
                    dataset="CU-BEMS",
                    horizon_minutes=horizon,
                    feature_names=spec["feature_names"],
                    target_names=spec["target_names"],
                    sample_count=sample_count,
                )

    if evaluators:
        def consume(task_id: str, horizon: int, sample: Dict[str, object]) -> None:
            evaluator = evaluators.get((task_id, horizon))
            if evaluator is not None:
                evaluator.consume(sample)

        _stream_cu_bems_samples_from_source_files(
            source_files=source_files,
            horizons=horizons,
            on_sample=consume,
        )

    tasks: List[Dict[str, object]] = []
    for horizon in horizons:
        for task_id in ("C1", "C2", "C3"):
            spec = task_specs[task_id]
            sample_count = sample_counts.get((task_id, horizon), 0)
            if sample_count < int(spec["min_samples"]):
                tasks.append(
                    {
                        "task_id": task_id,
                        "dataset": "CU-BEMS",
                        "horizon_minutes": horizon,
                        "status": "insufficient_samples",
                        "sample_count": sample_count,
                        "min_samples_required": int(spec["min_samples"]),
                        "feature_names": list(spec["feature_names"]),
                        "target_names": list(spec["target_names"]),
                    }
                )
                continue
            tasks.append(evaluators[(task_id, horizon)].summary())

    counts = metadata.get("counts", {}) if isinstance(metadata.get("counts"), dict) else {}
    zones = metadata.get("zones", []) if isinstance(metadata.get("zones"), list) else []
    return {
        "dataset": "CU-BEMS",
        "benchmark_mode": "single-zone device-response",
        "input_dir": str(input_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "horizons": list(horizons),
        "counts": {
            "zones": int(counts.get("zones", len(zones))),
            "sensor_rows": int(counts.get("sensor_rows", 0)),
            "device_rows": int(counts.get("device_rows", 0)),
            "auxiliary_rows": int(counts.get("auxiliary_rows", 0)),
        },
        "metadata": metadata,
        "tasks": tasks,
    }


def _run_sml2010_benchmark(input_dir: Path, horizons: Sequence[int]) -> Dict[str, object]:
    sensor_rows = _read_csv_rows(input_dir / "corner_sensor_timeseries.csv")
    outdoor_rows = _read_csv_rows(input_dir / "outdoor_environment.csv")
    auxiliary_rows = _read_csv_rows(input_dir / "auxiliary_features.csv")
    metadata = _read_optional_json(input_dir / "scenario_metadata.json")

    records = _load_sml2010_records(sensor_rows, outdoor_rows, auxiliary_rows)
    tasks: List[Dict[str, object]] = []
    for horizon in horizons:
        s1_samples = _build_sml2010_response_samples(records, horizon, task_id="S1")
        tasks.append(
            _evaluate_task(
                task_id="S1",
                dataset="SML2010",
                horizon_minutes=horizon,
                feature_names=[
                    "dining_illuminance",
                    "room_illuminance",
                    "outdoor_temperature",
                    "outdoor_humidity",
                    "sunlight_illuminance",
                    "rain_ratio",
                    "wind_speed",
                    "sun_irradiance",
                ],
                target_names=["dining_illuminance", "room_illuminance"],
                samples=s1_samples,
            )
        )
        s2_samples = _build_sml2010_response_samples(records, horizon, task_id="S2")
        tasks.append(
            _evaluate_task(
                task_id="S2",
                dataset="SML2010",
                horizon_minutes=horizon,
                feature_names=[
                    "dining_temperature",
                    "room_temperature",
                    "dining_humidity",
                    "room_humidity",
                    "outdoor_temperature",
                    "outdoor_humidity",
                    "sunlight_illuminance",
                    "rain_ratio",
                    "wind_speed",
                    "forecast_temperature",
                    "enthalpic_motor_1",
                    "enthalpic_motor_2",
                    "enthalpic_motor_turbo",
                ],
                target_names=["dining_temperature", "room_temperature", "dining_humidity", "room_humidity"],
                samples=s2_samples,
            )
        )
        s3_samples = _build_sml2010_event_delta_samples(records, horizon)
        tasks.append(
            _evaluate_task(
                task_id="S3",
                dataset="SML2010",
                horizon_minutes=horizon,
                feature_names=[
                    "dining_temperature",
                    "room_temperature",
                    "dining_humidity",
                    "room_humidity",
                    "dining_illuminance",
                    "room_illuminance",
                    "delta_outdoor_temperature",
                    "delta_outdoor_humidity",
                    "delta_sunlight",
                    "delta_rain",
                    "delta_wind",
                ],
                target_names=[
                    "dining_temperature",
                    "room_temperature",
                    "dining_humidity",
                    "room_humidity",
                    "dining_illuminance",
                    "room_illuminance",
                ],
                samples=s3_samples,
                min_samples=10,
            )
        )

    return {
        "dataset": "SML2010",
        "benchmark_mode": "two-point boundary-response",
        "input_dir": str(input_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "horizons": list(horizons),
        "counts": {
            "records": len(records),
            "sensor_rows": len(sensor_rows),
            "outdoor_rows": len(outdoor_rows),
            "auxiliary_rows": len(auxiliary_rows),
        },
        "metadata": metadata,
        "tasks": tasks,
    }


def _load_cu_bems_records(
    sensor_rows: Sequence[Dict[str, str]],
    device_rows: Sequence[Dict[str, str]],
    auxiliary_rows: Sequence[Dict[str, str]],
) -> Dict[str, List[Dict[str, float]]]:
    records: Dict[str, Dict[datetime, Dict[str, float]]] = {}
    for row in sensor_rows:
        timestamp = _parse_timestamp(row["timestamp"])
        zone_id = _extract_zone_id_from_sensor(row["sensor_name"])
        record = records.setdefault(zone_id, {}).setdefault(timestamp, _base_cu_bems_record(timestamp))
        record["temperature"] = _to_float(row.get("temperature_c"))
        record["humidity"] = _to_float(row.get("humidity_pct"))
        record["illuminance"] = _to_float(row.get("illuminance_lux"))

    for row in device_rows:
        timestamp = _parse_timestamp(row["timestamp"])
        zone_id, device_kind = _extract_zone_and_kind_from_device_name(row["device_name"])
        record = records.setdefault(zone_id, {}).setdefault(timestamp, _base_cu_bems_record(timestamp))
        power = _to_float(row.get("power")) or 0.0
        if device_kind == "ac":
            record["ac_power"] += power
        elif device_kind == "light":
            record["lighting_power"] += power

    for row in auxiliary_rows:
        timestamp = _parse_timestamp(row["timestamp"])
        zone_id = row.get("entity_id", "")
        if not zone_id:
            continue
        record = records.setdefault(zone_id, {}).setdefault(timestamp, _base_cu_bems_record(timestamp))
        record["plug_load"] = _to_float(row.get("plug_load_kw")) or 0.0

    finalized: Dict[str, List[Dict[str, float]]] = {}
    for zone_id, mapping in records.items():
        rows = [mapping[key] for key in sorted(mapping)]
        finalized[zone_id] = [row for row in rows if row["temperature"] is not None]
    return finalized


def _load_sml2010_records(
    sensor_rows: Sequence[Dict[str, str]],
    outdoor_rows: Sequence[Dict[str, str]],
    auxiliary_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, float]]:
    records: Dict[datetime, Dict[str, float]] = {}
    for row in sensor_rows:
        timestamp = _parse_timestamp(row["timestamp"])
        record = records.setdefault(timestamp, _base_sml2010_record(timestamp))
        sensor_name = row.get("sensor_name", "")
        if sensor_name == "dining_room":
            record["dining_temperature"] = _to_float(row.get("temperature_c"))
            record["dining_humidity"] = _to_float(row.get("humidity_pct"))
            record["dining_illuminance"] = _to_float(row.get("illuminance_lux"))
        elif sensor_name == "room":
            record["room_temperature"] = _to_float(row.get("temperature_c"))
            record["room_humidity"] = _to_float(row.get("humidity_pct"))
            record["room_illuminance"] = _to_float(row.get("illuminance_lux"))

    for row in outdoor_rows:
        timestamp = _parse_timestamp(row["timestamp"])
        record = records.setdefault(timestamp, _base_sml2010_record(timestamp))
        record["outdoor_temperature"] = _to_float(row.get("outdoor_temperature_c"))
        record["outdoor_humidity"] = _to_float(row.get("outdoor_humidity_pct"))
        record["sunlight_illuminance"] = _to_float(row.get("sunlight_illuminance_lux")) or 0.0
        record["daylight_factor"] = _to_float(row.get("daylight_factor")) or 0.0

    for row in auxiliary_rows:
        timestamp = _parse_timestamp(row["timestamp"])
        record = records.setdefault(timestamp, _base_sml2010_record(timestamp))
        record["rain_ratio"] = _to_float(row.get("rain_ratio")) or 0.0
        record["wind_speed"] = _to_float(row.get("wind_speed_m_s")) or 0.0
        record["sun_irradiance"] = _to_float(row.get("sun_irradiance_w_m2")) or 0.0
        record["forecast_temperature"] = _to_float(row.get("forecast_temperature_c")) or 0.0
        record["enthalpic_motor_1"] = _to_float(row.get("enthalpic_motor_1")) or 0.0
        record["enthalpic_motor_2"] = _to_float(row.get("enthalpic_motor_2")) or 0.0
        record["enthalpic_motor_turbo"] = _to_float(row.get("enthalpic_motor_turbo")) or 0.0
        record["facade_west_lux"] = _to_float(row.get("facade_west_lux")) or 0.0
        record["facade_east_lux"] = _to_float(row.get("facade_east_lux")) or 0.0
        record["facade_south_lux"] = _to_float(row.get("facade_south_lux")) or 0.0

    rows = [records[key] for key in sorted(records)]
    return [row for row in rows if row["dining_temperature"] is not None and row["room_temperature"] is not None]


def _build_cu_bems_response_samples(
    records_by_zone: Dict[str, List[Dict[str, float]]],
    horizon_minutes: int,
    task_id: str,
) -> List[Dict[str, object]]:
    samples: List[Dict[str, object]] = []
    for zone_records in records_by_zone.values():
        lookup = {row["timestamp_dt"]: row for row in zone_records}
        for record in zone_records:
            future = lookup.get(record["timestamp_dt"] + timedelta(minutes=horizon_minutes))
            if future is None:
                continue
            if task_id == "C1":
                if any(value is None for value in (record["temperature"], record["humidity"], future["temperature"], future["humidity"])):
                    continue
                samples.append(
                    {
                        "features": [
                            record["temperature"] or 0.0,
                            record["humidity"] or 0.0,
                            record["ac_power"] or 0.0,
                            record["plug_load"] or 0.0,
                            1.0 if (record["ac_power"] or 0.0) > 1e-9 else 0.0,
                        ],
                        "targets": {
                            "temperature": future["temperature"],
                            "humidity": future["humidity"],
                        },
                        "persistence": {
                            "temperature": record["temperature"],
                            "humidity": record["humidity"],
                        },
                        "context": {
                            "origin": dict(record),
                            "future": dict(future),
                        },
                    }
                )
            elif task_id == "C2":
                if record["illuminance"] is None or future["illuminance"] is None:
                    continue
                samples.append(
                    {
                        "features": [
                            record["illuminance"] or 0.0,
                            record["lighting_power"] or 0.0,
                            record["plug_load"] or 0.0,
                            1.0 if (record["lighting_power"] or 0.0) > 1e-9 else 0.0,
                        ],
                        "targets": {"illuminance": future["illuminance"]},
                        "persistence": {"illuminance": record["illuminance"]},
                        "context": {
                            "origin": dict(record),
                            "future": dict(future),
                        },
                    }
                )
    return samples


def _build_cu_bems_event_delta_samples(
    records_by_zone: Dict[str, List[Dict[str, float]]],
    horizon_minutes: int,
) -> List[Dict[str, object]]:
    samples: List[Dict[str, object]] = []
    for zone_records in records_by_zone.values():
        lookup = {row["timestamp_dt"]: row for row in zone_records}
        for previous, current in zip(zone_records, zone_records[1:]):
            event_kind = _detect_cu_bems_event(previous, current)
            if event_kind is None:
                continue
            future = lookup.get(current["timestamp_dt"] + timedelta(minutes=horizon_minutes))
            if future is None:
                continue
            if any(
                value is None
                for value in (
                    previous["temperature"],
                    previous["humidity"],
                    previous["illuminance"],
                    future["temperature"],
                    future["humidity"],
                    future["illuminance"],
                )
            ):
                continue
            direction = 1.0 if event_kind.endswith("_on") else -1.0
            samples.append(
                {
                    "features": [
                        previous["temperature"] or 0.0,
                        previous["humidity"] or 0.0,
                        previous["illuminance"] or 0.0,
                        current["ac_power"] or 0.0,
                        current["lighting_power"] or 0.0,
                        current["plug_load"] or 0.0,
                        direction,
                        1.0 if event_kind.startswith("ac") else 0.0,
                        1.0 if event_kind.startswith("light") else 0.0,
                    ],
                    "targets": {
                        "temperature": (future["temperature"] or 0.0) - (previous["temperature"] or 0.0),
                        "humidity": (future["humidity"] or 0.0) - (previous["humidity"] or 0.0),
                        "illuminance": (future["illuminance"] or 0.0) - (previous["illuminance"] or 0.0),
                    },
                    "persistence": {
                        "temperature": 0.0,
                        "humidity": 0.0,
                        "illuminance": 0.0,
                    },
                    "context": {
                        "previous": dict(previous),
                        "current": dict(current),
                        "future": dict(future),
                        "event_kind": event_kind,
                    },
                }
            )
    return samples


def _count_cu_bems_samples_from_source_files(
    source_files: Sequence[Path],
    horizons: Sequence[int],
) -> Dict[Tuple[str, int], int]:
    counts: Dict[Tuple[str, int], int] = defaultdict(int)

    def count_sample(task_id: str, horizon: int, sample: Dict[str, object]) -> None:
        del sample
        counts[(task_id, horizon)] += 1

    _stream_cu_bems_samples_from_source_files(
        source_files=source_files,
        horizons=horizons,
        on_sample=count_sample,
    )
    return counts


def _stream_cu_bems_samples_from_source_files(
    source_files: Sequence[Path],
    horizons: Sequence[int],
    on_sample: Callable[[str, int, Dict[str, object]], None],
) -> None:
    ordered_horizons = sorted({int(value) for value in horizons if int(value) > 0})
    if not ordered_horizons:
        return

    max_horizon = max(ordered_horizons)
    recent_by_zone: Dict[str, Dict[datetime, Dict[str, float]]] = defaultdict(dict)
    recent_order_by_zone: Dict[str, Deque[datetime]] = defaultdict(deque)
    previous_by_zone: Dict[str, Dict[str, float]] = {}
    pending_events: Dict[Tuple[str, int], Deque[Tuple[datetime, Dict[str, float], Dict[str, float], str]]] = defaultdict(deque)

    for source_file in sorted(source_files):
        floor = _extract_floor_number(source_file.name)
        with source_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            if not headers:
                continue
            time_column = _infer_time_column(headers)
            zone_mapping = infer_cu_bems_zone_mapping(headers)

            for row in reader:
                normalized_timestamp = _normalize_timestamp(row.get(time_column, ""))
                try:
                    timestamp_dt = _parse_timestamp(normalized_timestamp)
                except ValueError:
                    continue

                for zone_number, mapping in zone_mapping.items():
                    zone_id = f"floor{floor}_zone{zone_number}"
                    record = {
                        "timestamp_dt": timestamp_dt,
                        "temperature": _first_float(row, mapping["temperature"]),
                        "humidity": _first_float(row, mapping["humidity"]),
                        "illuminance": _first_float(row, mapping["illuminance"]),
                        "ac_power": _sum_columns(row, mapping["ac_power"]) or 0.0,
                        "lighting_power": _sum_columns(row, mapping["lighting_power"]) or 0.0,
                        "plug_load": _sum_columns(row, mapping["plug_power"]) or 0.0,
                    }
                    if record["temperature"] is None:
                        continue

                    zone_recent = recent_by_zone[zone_id]
                    zone_order = recent_order_by_zone[zone_id]
                    zone_recent[timestamp_dt] = record
                    zone_order.append(timestamp_dt)

                    for horizon in ordered_horizons:
                        previous_record = zone_recent.get(timestamp_dt - timedelta(minutes=horizon))
                        if previous_record is not None:
                            if all(
                                value is not None
                                for value in (
                                    previous_record["temperature"],
                                    previous_record["humidity"],
                                    record["temperature"],
                                    record["humidity"],
                                )
                            ):
                                on_sample(
                                    "C1",
                                    horizon,
                                    {
                                        "features": [
                                            previous_record["temperature"] or 0.0,
                                            previous_record["humidity"] or 0.0,
                                            previous_record["ac_power"] or 0.0,
                                            previous_record["plug_load"] or 0.0,
                                            1.0 if (previous_record["ac_power"] or 0.0) > 1e-9 else 0.0,
                                        ],
                                        "targets": {
                                            "temperature": record["temperature"],
                                            "humidity": record["humidity"],
                                        },
                                        "persistence": {
                                            "temperature": previous_record["temperature"],
                                            "humidity": previous_record["humidity"],
                                        },
                                        "context": {
                                            "origin": dict(previous_record),
                                            "future": dict(record),
                                        },
                                    },
                                )
                            if previous_record["illuminance"] is not None and record["illuminance"] is not None:
                                on_sample(
                                    "C2",
                                    horizon,
                                    {
                                        "features": [
                                            previous_record["illuminance"] or 0.0,
                                            previous_record["lighting_power"] or 0.0,
                                            previous_record["plug_load"] or 0.0,
                                            1.0 if (previous_record["lighting_power"] or 0.0) > 1e-9 else 0.0,
                                        ],
                                        "targets": {"illuminance": record["illuminance"]},
                                        "persistence": {"illuminance": previous_record["illuminance"]},
                                        "context": {
                                            "origin": dict(previous_record),
                                            "future": dict(record),
                                        },
                                    },
                                )

                        queue = pending_events[(zone_id, horizon)]
                        while queue and queue[0][0] < timestamp_dt:
                            queue.popleft()
                        while queue and queue[0][0] == timestamp_dt:
                            _, event_previous, event_current, event_kind = queue.popleft()
                            if any(
                                value is None
                                for value in (
                                    event_previous["temperature"],
                                    event_previous["humidity"],
                                    event_previous["illuminance"],
                                    record["temperature"],
                                    record["humidity"],
                                    record["illuminance"],
                                )
                            ):
                                continue
                            on_sample(
                                "C3",
                                horizon,
                                {
                                    "features": [
                                        event_previous["temperature"] or 0.0,
                                        event_previous["humidity"] or 0.0,
                                        event_previous["illuminance"] or 0.0,
                                        event_current["ac_power"] or 0.0,
                                        event_current["lighting_power"] or 0.0,
                                        event_current["plug_load"] or 0.0,
                                        1.0 if event_kind.endswith("_on") else -1.0,
                                        1.0 if event_kind.startswith("ac") else 0.0,
                                        1.0 if event_kind.startswith("light") else 0.0,
                                    ],
                                    "targets": {
                                        "temperature": (record["temperature"] or 0.0) - (event_previous["temperature"] or 0.0),
                                        "humidity": (record["humidity"] or 0.0) - (event_previous["humidity"] or 0.0),
                                        "illuminance": (record["illuminance"] or 0.0) - (event_previous["illuminance"] or 0.0),
                                    },
                                    "persistence": {
                                        "temperature": 0.0,
                                        "humidity": 0.0,
                                        "illuminance": 0.0,
                                    },
                                    "context": {
                                        "previous": dict(event_previous),
                                        "current": dict(event_current),
                                        "future": dict(record),
                                        "event_kind": event_kind,
                                    },
                                },
                            )

                    previous_record = previous_by_zone.get(zone_id)
                    if previous_record is not None:
                        event_kind = _detect_cu_bems_event(previous_record, record)
                        if event_kind is not None:
                            for horizon in ordered_horizons:
                                pending_events[(zone_id, horizon)].append(
                                    (timestamp_dt + timedelta(minutes=horizon), previous_record, record, event_kind)
                                )
                    previous_by_zone[zone_id] = record

                    cutoff = timestamp_dt - timedelta(minutes=max_horizon)
                    while zone_order and zone_order[0] < cutoff:
                        expired_timestamp = zone_order.popleft()
                        zone_recent.pop(expired_timestamp, None)


def _build_sml2010_response_samples(
    records: Sequence[Dict[str, float]],
    horizon_minutes: int,
    task_id: str,
) -> List[Dict[str, object]]:
    lookup = {row["timestamp_dt"]: row for row in records}
    samples: List[Dict[str, object]] = []
    for record in records:
        future = lookup.get(record["timestamp_dt"] + timedelta(minutes=horizon_minutes))
        if future is None:
            continue
        if task_id == "S1":
            samples.append(
                {
                    "features": [
                        record["dining_illuminance"] or 0.0,
                        record["room_illuminance"] or 0.0,
                        record["outdoor_temperature"] or 0.0,
                        record["outdoor_humidity"] or 0.0,
                        record["sunlight_illuminance"] or 0.0,
                        record["rain_ratio"] or 0.0,
                        record["wind_speed"] or 0.0,
                        record["sun_irradiance"] or 0.0,
                    ],
                    "targets": {
                        "dining_illuminance": future["dining_illuminance"],
                        "room_illuminance": future["room_illuminance"],
                    },
                    "persistence": {
                        "dining_illuminance": record["dining_illuminance"],
                        "room_illuminance": record["room_illuminance"],
                    },
                    "context": {
                        "origin": dict(record),
                        "future": dict(future),
                    },
                }
            )
        elif task_id == "S2":
            samples.append(
                {
                    "features": [
                        record["dining_temperature"] or 0.0,
                        record["room_temperature"] or 0.0,
                        record["dining_humidity"] or 0.0,
                        record["room_humidity"] or 0.0,
                        record["outdoor_temperature"] or 0.0,
                        record["outdoor_humidity"] or 0.0,
                        record["sunlight_illuminance"] or 0.0,
                        record["rain_ratio"] or 0.0,
                        record["wind_speed"] or 0.0,
                        record["forecast_temperature"] or 0.0,
                        record["enthalpic_motor_1"] or 0.0,
                        record["enthalpic_motor_2"] or 0.0,
                        record["enthalpic_motor_turbo"] or 0.0,
                    ],
                    "targets": {
                        "dining_temperature": future["dining_temperature"],
                        "room_temperature": future["room_temperature"],
                        "dining_humidity": future["dining_humidity"],
                        "room_humidity": future["room_humidity"],
                    },
                    "persistence": {
                        "dining_temperature": record["dining_temperature"],
                        "room_temperature": record["room_temperature"],
                        "dining_humidity": record["dining_humidity"],
                        "room_humidity": record["room_humidity"],
                    },
                    "context": {
                        "origin": dict(record),
                        "future": dict(future),
                    },
                }
            )
    return samples


def _build_sml2010_event_delta_samples(
    records: Sequence[Dict[str, float]],
    horizon_minutes: int,
) -> List[Dict[str, object]]:
    lookup = {row["timestamp_dt"]: row for row in records}
    samples: List[Dict[str, object]] = []
    for previous, current in zip(records, records[1:]):
        delta_sunlight = (current["sunlight_illuminance"] or 0.0) - (previous["sunlight_illuminance"] or 0.0)
        delta_rain = (current["rain_ratio"] or 0.0) - (previous["rain_ratio"] or 0.0)
        delta_outdoor_temperature = (current["outdoor_temperature"] or 0.0) - (previous["outdoor_temperature"] or 0.0)
        delta_outdoor_humidity = (current["outdoor_humidity"] or 0.0) - (previous["outdoor_humidity"] or 0.0)
        delta_wind = (current["wind_speed"] or 0.0) - (previous["wind_speed"] or 0.0)
        if not _is_sml2010_boundary_event(
            delta_sunlight=delta_sunlight,
            delta_rain=delta_rain,
            delta_outdoor_temperature=delta_outdoor_temperature,
        ):
            continue
        future = lookup.get(current["timestamp_dt"] + timedelta(minutes=horizon_minutes))
        if future is None:
            continue
        samples.append(
            {
                "features": [
                    previous["dining_temperature"] or 0.0,
                    previous["room_temperature"] or 0.0,
                    previous["dining_humidity"] or 0.0,
                    previous["room_humidity"] or 0.0,
                    previous["dining_illuminance"] or 0.0,
                    previous["room_illuminance"] or 0.0,
                    delta_outdoor_temperature,
                    delta_outdoor_humidity,
                    delta_sunlight,
                    delta_rain,
                    delta_wind,
                ],
                "targets": {
                    "dining_temperature": (future["dining_temperature"] or 0.0) - (previous["dining_temperature"] or 0.0),
                    "room_temperature": (future["room_temperature"] or 0.0) - (previous["room_temperature"] or 0.0),
                    "dining_humidity": (future["dining_humidity"] or 0.0) - (previous["dining_humidity"] or 0.0),
                    "room_humidity": (future["room_humidity"] or 0.0) - (previous["room_humidity"] or 0.0),
                    "dining_illuminance": (future["dining_illuminance"] or 0.0) - (previous["dining_illuminance"] or 0.0),
                    "room_illuminance": (future["room_illuminance"] or 0.0) - (previous["room_illuminance"] or 0.0),
                },
                "persistence": {
                    "dining_temperature": 0.0,
                    "room_temperature": 0.0,
                    "dining_humidity": 0.0,
                    "room_humidity": 0.0,
                    "dining_illuminance": 0.0,
                    "room_illuminance": 0.0,
                },
                "context": {
                    "previous": dict(previous),
                    "current": dict(current),
                    "future": dict(future),
                    "delta_outdoor_temperature": delta_outdoor_temperature,
                    "delta_outdoor_humidity": delta_outdoor_humidity,
                    "delta_sunlight": delta_sunlight,
                    "delta_rain": delta_rain,
                    "delta_wind": delta_wind,
                },
            }
        )
    return samples


def _evaluate_task(
    task_id: str,
    dataset: str,
    horizon_minutes: int,
    feature_names: Sequence[str],
    target_names: Sequence[str],
    samples: Sequence[Dict[str, object]],
    min_samples: int = 4,
) -> Dict[str, object]:
    if len(samples) < min_samples:
        return {
            "task_id": task_id,
            "dataset": dataset,
            "horizon_minutes": horizon_minutes,
            "status": "insufficient_samples",
            "sample_count": len(samples),
            "min_samples_required": min_samples,
            "feature_names": list(feature_names),
            "target_names": list(target_names),
        }

    split_index = max(1, min(len(samples) - 1, int(len(samples) * 0.7)))
    train_samples = list(samples[:split_index])
    test_samples = list(samples[split_index:])
    train_features = [list(sample["features"]) for sample in train_samples]
    test_features = [list(sample["features"]) for sample in test_samples]

    targets_summary: Dict[str, Dict[str, object]] = {}
    for target_name in target_names:
        train_targets = [float(sample["targets"][target_name]) for sample in train_samples]
        test_targets = [float(sample["targets"][target_name]) for sample in test_samples]
        persistence_predictions = [float(sample["persistence"][target_name]) for sample in test_samples]

        coefficients = _fit_linear_regression(train_features, train_targets)
        regression_predictions = [_predict_linear_regression(coefficients, features) for features in test_features]

        persistence_metrics = _metric_summary(test_targets, persistence_predictions)
        regression_metrics = _metric_summary(test_targets, regression_predictions)
        targets_summary[target_name] = {
            "persistence": persistence_metrics,
            "linear_regression": regression_metrics,
            "mae_reduction_vs_persistence": round(
                persistence_metrics["mae"] - regression_metrics["mae"],
                6,
            ),
        }

    return {
        "task_id": task_id,
        "dataset": dataset,
        "horizon_minutes": horizon_minutes,
        "status": "ok",
        "sample_count": len(samples),
        "train_samples": len(train_samples),
        "test_samples": len(test_samples),
        "feature_names": list(feature_names),
        "target_names": list(target_names),
        "targets": targets_summary,
    }


class _StreamingTaskEvaluator:
    def __init__(
        self,
        task_id: str,
        dataset: str,
        horizon_minutes: int,
        feature_names: Sequence[str],
        target_names: Sequence[str],
        sample_count: int,
    ) -> None:
        self.task_id = task_id
        self.dataset = dataset
        self.horizon_minutes = horizon_minutes
        self.feature_names = list(feature_names)
        self.target_names = list(target_names)
        self.sample_count = sample_count
        self.train_samples = max(1, min(sample_count - 1, int(sample_count * 0.7)))
        self.test_samples = sample_count - self.train_samples
        self._processed_samples = 0
        self._width = len(self.feature_names) + 1
        self._normal_matrix = [[0.0 for _ in range(self._width)] for _ in range(self._width)]
        self._target_vectors = {target_name: [0.0 for _ in range(self._width)] for target_name in self.target_names}
        self._coefficients: Optional[Dict[str, List[float]]] = None
        self._persistence_metrics = {target_name: _OnlineMetricAccumulator() for target_name in self.target_names}
        self._regression_metrics = {target_name: _OnlineMetricAccumulator() for target_name in self.target_names}

    def consume(self, sample: Dict[str, object]) -> None:
        self._processed_samples += 1
        features = [float(value) for value in sample["features"]]
        if self._processed_samples <= self.train_samples:
            self._accumulate_training_sample(features, sample)
            if self._processed_samples == self.train_samples:
                self._coefficients = {
                    target_name: solve_linear_system(self._normal_matrix, self._target_vectors[target_name])
                    for target_name in self.target_names
                }
            return

        if self._coefficients is None:
            self._coefficients = {
                target_name: solve_linear_system(self._normal_matrix, self._target_vectors[target_name])
                for target_name in self.target_names
            }

        row = [1.0] + features
        targets = sample["targets"]
        persistence = sample["persistence"]
        for target_name in self.target_names:
            actual = float(targets[target_name])
            persistence_prediction = float(persistence[target_name])
            regression_prediction = float(sum(weight * value for weight, value in zip(self._coefficients[target_name], row)))
            self._persistence_metrics[target_name].add(actual, persistence_prediction)
            self._regression_metrics[target_name].add(actual, regression_prediction)

    def summary(self) -> Dict[str, object]:
        targets_summary: Dict[str, Dict[str, object]] = {}
        for target_name in self.target_names:
            persistence_metrics = self._persistence_metrics[target_name].summary()
            regression_metrics = self._regression_metrics[target_name].summary()
            targets_summary[target_name] = {
                "persistence": persistence_metrics,
                "linear_regression": regression_metrics,
                "mae_reduction_vs_persistence": round(
                    persistence_metrics["mae"] - regression_metrics["mae"],
                    6,
                ),
            }
        return {
            "task_id": self.task_id,
            "dataset": self.dataset,
            "horizon_minutes": self.horizon_minutes,
            "status": "ok",
            "sample_count": self.sample_count,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
            "feature_names": self.feature_names,
            "target_names": self.target_names,
            "targets": targets_summary,
        }

    def _accumulate_training_sample(self, features: Sequence[float], sample: Dict[str, object]) -> None:
        row = [1.0] + list(features)
        for row_index in range(self._width):
            for column_index in range(self._width):
                self._normal_matrix[row_index][column_index] += row[row_index] * row[column_index]
        targets = sample["targets"]
        for target_name in self.target_names:
            target_value = float(targets[target_name])
            for row_index in range(self._width):
                self._target_vectors[target_name][row_index] += row[row_index] * target_value


class _OnlineMetricAccumulator:
    def __init__(self) -> None:
        self.count = 0
        self.absolute_error_sum = 0.0
        self.squared_error_sum = 0.0
        self.actual_sum = 0.0
        self.predicted_sum = 0.0
        self.actual_squared_sum = 0.0
        self.predicted_squared_sum = 0.0
        self.cross_sum = 0.0

    def add(self, actual: float, predicted: float) -> None:
        self.count += 1
        error = actual - predicted
        self.absolute_error_sum += abs(error)
        self.squared_error_sum += error * error
        self.actual_sum += actual
        self.predicted_sum += predicted
        self.actual_squared_sum += actual * actual
        self.predicted_squared_sum += predicted * predicted
        self.cross_sum += actual * predicted

    def summary(self) -> Dict[str, float]:
        if self.count == 0:
            return {"mae": 0.0, "rmse": 0.0, "correlation": 0.0}
        numerator = (self.count * self.cross_sum) - (self.actual_sum * self.predicted_sum)
        denominator_left = (self.count * self.actual_squared_sum) - (self.actual_sum * self.actual_sum)
        denominator_right = (self.count * self.predicted_squared_sum) - (self.predicted_sum * self.predicted_sum)
        denominator = math.sqrt(max(denominator_left, 0.0) * max(denominator_right, 0.0))
        correlation = numerator / denominator if denominator > 1e-9 else 0.0
        return {
            "mae": round(self.absolute_error_sum / float(self.count), 6),
            "rmse": round(math.sqrt(self.squared_error_sum / float(self.count)), 6),
            "correlation": round(correlation, 6),
        }


def _fit_linear_regression(features: Sequence[Sequence[float]], targets: Sequence[float], ridge: float = 1e-6) -> List[float]:
    width = len(features[0]) + 1
    normal_matrix = [[0.0 for _ in range(width)] for _ in range(width)]
    normal_vector = [0.0 for _ in range(width)]
    for feature_row, target in zip(features, targets):
        row = [1.0] + [float(value) for value in feature_row]
        for row_index in range(width):
            normal_vector[row_index] += row[row_index] * float(target)
            for column_index in range(width):
                normal_matrix[row_index][column_index] += row[row_index] * row[column_index]
    for index in range(width):
        normal_matrix[index][index] += ridge
    return solve_linear_system(normal_matrix, normal_vector)


def _predict_linear_regression(coefficients: Sequence[float], features: Sequence[float]) -> float:
    return float(coefficients[0] + sum(weight * value for weight, value in zip(coefficients[1:], features)))


def _metric_summary(actual: Sequence[float], predicted: Sequence[float]) -> Dict[str, float]:
    if not actual:
        return {"mae": 0.0, "rmse": 0.0, "correlation": 0.0}
    absolute_errors = [abs(first - second) for first, second in zip(actual, predicted)]
    squared_errors = [(first - second) ** 2 for first, second in zip(actual, predicted)]
    return {
        "mae": round(sum(absolute_errors) / float(len(absolute_errors)), 6),
        "rmse": round(math.sqrt(sum(squared_errors) / float(len(squared_errors))), 6),
        "correlation": round(_pearson_correlation(actual, predicted), 6),
    }


def _pearson_correlation(first: Sequence[float], second: Sequence[float]) -> float:
    if len(first) < 2 or len(first) != len(second):
        return 0.0
    mean_first = sum(first) / float(len(first))
    mean_second = sum(second) / float(len(second))
    numerator = sum((left - mean_first) * (right - mean_second) for left, right in zip(first, second))
    denominator_left = math.sqrt(sum((value - mean_first) ** 2 for value in first))
    denominator_right = math.sqrt(sum((value - mean_second) ** 2 for value in second))
    denominator = denominator_left * denominator_right
    if denominator <= 1e-9:
        return 0.0
    return numerator / denominator


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_optional_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _base_cu_bems_record(timestamp_dt: datetime) -> Dict[str, float]:
    return {
        "timestamp_dt": timestamp_dt,
        "temperature": None,
        "humidity": None,
        "illuminance": None,
        "ac_power": 0.0,
        "lighting_power": 0.0,
        "plug_load": 0.0,
    }


def _base_sml2010_record(timestamp_dt: datetime) -> Dict[str, float]:
    return {
        "timestamp_dt": timestamp_dt,
        "dining_temperature": None,
        "room_temperature": None,
        "dining_humidity": None,
        "room_humidity": None,
        "dining_illuminance": None,
        "room_illuminance": None,
        "outdoor_temperature": 0.0,
        "outdoor_humidity": 0.0,
        "sunlight_illuminance": 0.0,
        "daylight_factor": 0.0,
        "rain_ratio": 0.0,
        "wind_speed": 0.0,
        "sun_irradiance": 0.0,
        "forecast_temperature": 0.0,
        "enthalpic_motor_1": 0.0,
        "enthalpic_motor_2": 0.0,
        "enthalpic_motor_turbo": 0.0,
        "facade_west_lux": 0.0,
        "facade_east_lux": 0.0,
        "facade_south_lux": 0.0,
    }


def _extract_zone_id_from_sensor(sensor_name: str) -> str:
    return sensor_name[: -len("_sensor")] if sensor_name.endswith("_sensor") else sensor_name


def _extract_zone_and_kind_from_device_name(device_name: str) -> tuple[str, str]:
    if device_name.endswith("_ac_main"):
        return device_name[: -len("_ac_main")], "ac"
    if device_name.endswith("_light_main"):
        return device_name[: -len("_light_main")], "light"
    return device_name, "unknown"


def _detect_cu_bems_event(previous: Dict[str, float], current: Dict[str, float]) -> Optional[str]:
    previous_ac = previous["ac_power"] or 0.0
    current_ac = current["ac_power"] or 0.0
    if previous_ac <= 1e-9 < current_ac:
        return "ac_on"
    if previous_ac > 1e-9 >= current_ac:
        return "ac_off"

    previous_light = previous["lighting_power"] or 0.0
    current_light = current["lighting_power"] or 0.0
    if previous_light <= 1e-9 < current_light:
        return "light_on"
    if previous_light > 1e-9 >= current_light:
        return "light_off"
    return None


def _is_sml2010_boundary_event(
    delta_sunlight: float,
    delta_rain: float,
    delta_outdoor_temperature: float,
) -> bool:
    return abs(delta_sunlight) >= 2500.0 or abs(delta_rain) >= 0.2 or abs(delta_outdoor_temperature) >= 1.0


def _parse_timestamp(value: str) -> datetime:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value}")


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)