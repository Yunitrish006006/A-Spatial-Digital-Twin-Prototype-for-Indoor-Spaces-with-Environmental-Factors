from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DATA = ROOT / "outputs" / "data"
RAW_PUBLIC = OUTPUT_DATA / "raw_public"
NORMALIZED_PUBLIC = OUTPUT_DATA / "normalized_public"
PUBLIC_BENCHMARKS = OUTPUT_DATA / "public_benchmarks"

SML2010_ZIP_URL = "https://archive.ics.uci.edu/static/public/274/sml2010.zip"
SML2010_DOI_URL = "https://doi.org/10.24432/C5RS3S"
CU_BEMS_FIGSHARE_API = "https://api.figshare.com/v2/articles/11726517"
CU_BEMS_FIGSHARE_URL = (
    "https://figshare.com/articles/dataset/"
    "CU-BEMS_Smart_Building_Electricity_Consumption_and_Indoor_Environmental_Sensor_Datasets/11726517"
)

SML2010_REQUIRED_FILES = ["NEW-DATA-1.T15.txt", "NEW-DATA-2.T15.txt"]
CU_BEMS_REQUIRED_FILES = [
    *(f"2018Floor{floor}.csv" for floor in range(1, 8)),
    *(f"2019Floor{floor}.csv" for floor in range(1, 8)),
]

SUMMARY_FILES = [
    "validation_summary.json",
    "window_matrix_summary.json",
    "hybrid_residual_summary.json",
    "hybrid_residual_checkpoint.json",
    "submission_readiness_summary.json",
    "bedroom_01_weekly/weekly_simulation_summary.json",
]


@dataclass
class DatasetStatus:
    dataset: str
    status: str
    raw_dir: str
    normalized_dir: str
    missing_raw_files: List[str]
    missing_normalized_files: List[str]
    source_url: str
    license_note: str
    action: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare and audit local data paths required by thesis result verification."
    )
    parser.add_argument(
        "--dataset",
        choices=("all", "sml2010", "cu-bems"),
        default="all",
        help="Which public dataset to check or download.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Attempt to download missing public datasets from their public sources.",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize public raw datasets after they are present locally.",
    )
    args = parser.parse_args()

    for directory in (OUTPUT_DATA, RAW_PUBLIC, NORMALIZED_PUBLIC, PUBLIC_BENCHMARKS):
        directory.mkdir(parents=True, exist_ok=True)

    datasets = ["sml2010", "cu-bems"] if args.dataset == "all" else [args.dataset]
    dataset_reports = []
    for dataset in datasets:
        if dataset == "sml2010":
            if args.download:
                _ensure_sml2010_downloaded()
            status = _check_sml2010()
            if args.normalize and status.status == "READY":
                _normalize_dataset("sml2010")
                status = _check_sml2010()
        else:
            if args.download:
                _ensure_cu_bems_downloaded()
            status = _check_cu_bems()
            if args.normalize and status.status == "READY":
                _normalize_dataset("cu-bems")
                status = _check_cu_bems()
        dataset_reports.append(status)

    summary_report = _check_summary_outputs()
    report = {
        "output_data_dir": str(OUTPUT_DATA.relative_to(ROOT)),
        "public_benchmark_dir": str(PUBLIC_BENCHMARKS.relative_to(ROOT)),
        "download_attempted": args.download,
        "normalize_attempted": args.normalize,
        "datasets": [status.__dict__ for status in dataset_reports],
        "summary_outputs": summary_report,
        "notes": [
            "Raw public datasets are intentionally stored under outputs/data/raw_public and ignored by git.",
            "Small summary JSON files may be kept as verification evidence, but large raw public datasets should not be committed.",
            "If public raw files are unavailable, public benchmark verification should be reported as NEEDS_DATA/MISSING rather than fabricated.",
        ],
    }
    _write_report(report)
    _print_report(report)


def _check_sml2010() -> DatasetStatus:
    raw_dir = RAW_PUBLIC / "sml2010"
    normalized_dir = NORMALIZED_PUBLIC / "sml2010"
    missing_raw = _missing(raw_dir, SML2010_REQUIRED_FILES)
    missing_normalized = _missing(
        normalized_dir,
        [
            "corner_sensor_timeseries.csv",
            "outdoor_environment.csv",
            "auxiliary_features.csv",
            "scenario_metadata.json",
            "normalization_summary.json",
        ],
    )
    status = "READY" if not missing_raw else "NEEDS_DATA"
    if not missing_raw and missing_normalized:
        status = "RAW_READY_NORMALIZATION_MISSING"
    action = (
        "Run: python3 scripts/normalize_public_benchmark_data.py --dataset sml2010"
        if status == "RAW_READY_NORMALIZATION_MISSING"
        else "Ready for public benchmark scripts."
        if status == "READY"
        else (
            "Place NEW-DATA-1.T15.txt and NEW-DATA-2.T15.txt under "
            "outputs/data/raw_public/sml2010, or rerun this script with --download."
        )
    )
    return DatasetStatus(
        dataset="SML2010",
        status=status,
        raw_dir=str(raw_dir.relative_to(ROOT)),
        normalized_dir=str(normalized_dir.relative_to(ROOT)),
        missing_raw_files=missing_raw,
        missing_normalized_files=missing_normalized,
        source_url=SML2010_DOI_URL,
        license_note="UCI Machine Learning Repository; CC BY 4.0.",
        action=action,
    )


def _check_cu_bems() -> DatasetStatus:
    raw_dir = RAW_PUBLIC / "cu-bems"
    normalized_dir = NORMALIZED_PUBLIC / "cu_bems"
    missing_raw = _missing(raw_dir, CU_BEMS_REQUIRED_FILES)
    missing_normalized = _missing(
        normalized_dir,
        [
            "corner_sensor_timeseries.csv",
            "device_event_log.csv",
            "auxiliary_features.csv",
            "scenario_metadata.json",
            "normalization_summary.json",
        ],
    )
    status = "READY" if not missing_raw else "NEEDS_DATA"
    if not missing_raw and missing_normalized:
        status = "RAW_READY_NORMALIZATION_MISSING"
    action = (
        "Run: python3 scripts/normalize_public_benchmark_data.py --dataset cu-bems"
        if status == "RAW_READY_NORMALIZATION_MISSING"
        else "Ready for public benchmark scripts."
        if status == "READY"
        else (
            "Place 2018Floor1.csv through 2019Floor7.csv under outputs/data/raw_public/cu-bems, "
            "or rerun this script with --download."
        )
    )
    return DatasetStatus(
        dataset="CU-BEMS",
        status=status,
        raw_dir=str(raw_dir.relative_to(ROOT)),
        normalized_dir=str(normalized_dir.relative_to(ROOT)),
        missing_raw_files=missing_raw,
        missing_normalized_files=missing_normalized,
        source_url=CU_BEMS_FIGSHARE_URL,
        license_note="figshare dataset, version 6; CC BY 4.0.",
        action=action,
    )


def _ensure_sml2010_downloaded() -> None:
    raw_dir = RAW_PUBLIC / "sml2010"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not _missing(raw_dir, SML2010_REQUIRED_FILES):
        return
    zip_path = raw_dir / "sml2010.zip"
    if not zip_path.exists():
        print(f"Downloading SML2010 from {SML2010_ZIP_URL}")
        _download_file(SML2010_ZIP_URL, zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            name = Path(member).name
            if name in SML2010_REQUIRED_FILES:
                target = raw_dir / name
                with archive.open(member) as source, target.open("wb") as handle:
                    handle.write(source.read())
    missing = _missing(raw_dir, SML2010_REQUIRED_FILES)
    if missing:
        raise SystemExit(f"SML2010 download completed but required files are still missing: {missing}")


def _ensure_cu_bems_downloaded() -> None:
    raw_dir = RAW_PUBLIC / "cu-bems"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not _missing(raw_dir, CU_BEMS_REQUIRED_FILES):
        return
    metadata_path = raw_dir / "article_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        print(f"Downloading CU-BEMS metadata from {CU_BEMS_FIGSHARE_API}")
        with urllib.request.urlopen(CU_BEMS_FIGSHARE_API, timeout=60) as response:
            metadata = json.loads(response.read().decode("utf-8"))
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    files_by_name = {item["name"]: item for item in metadata.get("files", [])}
    for filename in CU_BEMS_REQUIRED_FILES:
        target = raw_dir / filename
        if target.exists():
            continue
        item = files_by_name.get(filename)
        if not item:
            raise SystemExit(f"CU-BEMS metadata does not list required file: {filename}")
        print(f"Downloading CU-BEMS {filename} from figshare")
        _download_file(item["download_url"], target)
        expected_md5 = item.get("supplied_md5")
        if expected_md5 and _md5(target) != expected_md5:
            target.unlink(missing_ok=True)
            raise SystemExit(f"MD5 mismatch for {filename}; download removed.")


def _normalize_dataset(dataset: str) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from digital_twin.core.public_dataset_alignment import normalize_cu_bems_dataset, normalize_sml2010_dataset

    if dataset == "sml2010":
        normalize_sml2010_dataset(RAW_PUBLIC / "sml2010", NORMALIZED_PUBLIC / "sml2010")
        return
    normalize_cu_bems_dataset(RAW_PUBLIC / "cu-bems", NORMALIZED_PUBLIC / "cu_bems")


def _check_summary_outputs() -> Dict[str, Dict[str, object]]:
    output: Dict[str, Dict[str, object]] = {}
    for relative in SUMMARY_FILES:
        path = OUTPUT_DATA / relative
        output[relative] = {
            "exists": path.exists(),
            "path": str(path.relative_to(ROOT)),
            "suggested_script": _suggest_script_for_summary(relative),
        }
    output["public_benchmarks/sml2010_hybrid_twin_comparison.json"] = {
        "exists": (PUBLIC_BENCHMARKS / "sml2010_hybrid_twin_comparison.json").exists(),
        "path": "outputs/data/public_benchmarks/sml2010_hybrid_twin_comparison.json",
        "suggested_script": "python3 scripts/run_public_dataset_model_comparison.py --dataset sml2010 --horizons 15,60",
    }
    output["public_benchmarks/cu_bems_hybrid_twin_comparison.json"] = {
        "exists": (PUBLIC_BENCHMARKS / "cu_bems_hybrid_twin_comparison.json").exists(),
        "path": "outputs/data/public_benchmarks/cu_bems_hybrid_twin_comparison.json",
        "suggested_script": "python3 scripts/run_public_dataset_model_comparison.py --dataset cu-bems --horizons 15,60",
    }
    return output


def _suggest_script_for_summary(relative: str) -> str:
    return {
        "validation_summary.json": "python3 scripts/run_demo.py",
        "window_matrix_summary.json": "python3 scripts/run_window_matrix.py",
        "hybrid_residual_summary.json": "python3 scripts/run_hybrid_residual_experiment.py --fourier-denoise",
        "hybrid_residual_checkpoint.json": "python3 scripts/run_hybrid_residual_experiment.py --fourier-denoise",
        "submission_readiness_summary.json": "python3 scripts/run_submission_readiness_experiments.py",
        "bedroom_01_weekly/weekly_simulation_summary.json": "python3 scripts/run_bedroom_weekly_simulation.py",
    }.get(relative, "")


def _missing(directory: Path, filenames: Iterable[str]) -> List[str]:
    return [filename for filename in filenames if not (directory / filename).exists()]


def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    temp.replace(target)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_report(report: Dict[str, object]) -> None:
    json_path = OUTPUT_DATA / "experiment_data_preparation_report.json"
    md_path = OUTPUT_DATA / "experiment_data_preparation_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Experiment Data Preparation Report", ""]
    for dataset in report["datasets"]:
        lines.append(f"## {dataset['dataset']}")
        lines.append(f"- status: {dataset['status']}")
        lines.append(f"- raw_dir: `{dataset['raw_dir']}`")
        lines.append(f"- normalized_dir: `{dataset['normalized_dir']}`")
        lines.append(f"- source: {dataset['source_url']}")
        lines.append(f"- license: {dataset['license_note']}")
        lines.append(f"- action: {dataset['action']}")
        if dataset["missing_raw_files"]:
            lines.append(f"- missing_raw_files: {', '.join(dataset['missing_raw_files'])}")
        if dataset["missing_normalized_files"]:
            lines.append(f"- missing_normalized_files: {', '.join(dataset['missing_normalized_files'])}")
        lines.append("")
    lines.append("## Summary Outputs")
    for name, item in report["summary_outputs"].items():
        lines.append(
            f"- `{name}`: {'exists' if item['exists'] else 'missing'}; "
            f"suggested: `{item['suggested_script']}`"
        )
    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _print_report(report: Dict[str, object]) -> None:
    print("Experiment data preparation report")
    for dataset in report["datasets"]:
        print(f"- {dataset['dataset']}: {dataset['status']} ({dataset['action']})")
    missing = [name for name, item in report["summary_outputs"].items() if not item["exists"]]
    if missing:
        print("Missing summary outputs:")
        for name in missing:
            print(f"  - {name}: {report['summary_outputs'][name]['suggested_script']}")
    else:
        print("All checked summary outputs exist.")


if __name__ == "__main__":
    main()
