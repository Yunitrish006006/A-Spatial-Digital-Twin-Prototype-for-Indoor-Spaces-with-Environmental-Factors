from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "data"
NORMALIZED_PUBLIC = DATA / "normalized_public"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run thesis experiment pipeline and result verification.")
    parser.add_argument("--download-public", action="store_true", help="Allow prepare_experiment_data.py to download public raw datasets.")
    parser.add_argument("--normalize-public", action="store_true", help="Normalize public raw datasets if available.")
    parser.add_argument("--skip-public", action="store_true", help="Skip public benchmark scripts even if normalized data exists.")
    parser.add_argument(
        "--skip-submission-readiness",
        action="store_true",
        help="Skip scripts/run_submission_readiness_experiments.py; LOO values may remain stale or MISSING.",
    )
    parser.add_argument(
        "--skip-bedroom",
        action="store_true",
        help="Skip scripts/run_bedroom_weekly_simulation.py; real-bedroom values may remain stale or MISSING.",
    )
    args = parser.parse_args()

    failures: List[str] = []
    prepare_command = ["python3", "scripts/prepare_experiment_data.py"]
    if args.download_public:
        prepare_command.append("--download")
    if args.normalize_public:
        prepare_command.append("--normalize")
    _run(prepare_command, failures)

    _run(["python3", "scripts/run_demo.py"], failures)
    _run(["python3", "scripts/run_window_matrix.py"], failures)
    _run(["python3", "scripts/run_hybrid_residual_experiment.py", "--fourier-denoise"], failures)

    if not args.skip_submission_readiness:
        _run(["python3", "scripts/run_submission_readiness_experiments.py"], failures)

    if not args.skip_bedroom:
        _run(["python3", "scripts/run_bedroom_weekly_simulation.py"], failures)

    if args.skip_public:
        print("Skipping public benchmark scripts because --skip-public was provided.")
    elif _public_normalized_data_ready():
        _run(["python3", "scripts/run_public_dataset_benchmark.py", "--dataset", "all", "--horizons", "15,60"], failures)
        _run(
            [
                "python3",
                "scripts/run_public_dataset_model_comparison.py",
                "--dataset",
                "all",
                "--horizons",
                "15,60",
                "--checkpoint",
                "outputs/data/hybrid_residual_checkpoint.json",
            ],
            failures,
        )
    else:
        print(
            "Public normalized datasets are missing; skipping public benchmark scripts. "
            "Verification will mark public benchmark rows as MISSING/NEEDS_DATA if evidence JSON is absent."
        )

    _run(["python3", "scripts/verify_thesis_results.py"], failures)

    if failures:
        print("\nSome experiment steps failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)


def _run(command: Sequence[str], failures: List[str]) -> None:
    print(f"\n$ {' '.join(command)}")
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/school_pycache")
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, check=False)
    if completed.returncode != 0:
        failures.append(f"{' '.join(command)} exited with {completed.returncode}")


def _public_normalized_data_ready() -> bool:
    required = [
        NORMALIZED_PUBLIC / "sml2010" / "corner_sensor_timeseries.csv",
        NORMALIZED_PUBLIC / "sml2010" / "scenario_metadata.json",
        NORMALIZED_PUBLIC / "cu_bems" / "corner_sensor_timeseries.csv",
        NORMALIZED_PUBLIC / "cu_bems" / "scenario_metadata.json",
    ]
    return all(path.exists() for path in required)


if __name__ == "__main__":
    main()
