from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "data"
REPORT_JSON = DATA / "thesis_result_verification_report.json"
REPORT_MD = DATA / "thesis_result_verification_report.md"

THESIS_SOURCES = [
    ROOT / "docs" / "thesis" / "thesis_draft_zh.md",
    ROOT / "docs" / "papers" / "thesis" / "thesis_draft_zh.tex",
    ROOT / "docs" / "papers" / "ieee" / "paper.tex",
    ROOT / "scripts" / "build_thesis_docx.py",
    ROOT / "scripts" / "build_thesis_full_zh_stable.py",
]

METRICS = ("temperature", "humidity", "illuminance")


@dataclass(frozen=True)
class ResultSpec:
    result_name: str
    thesis_value: float
    evidence_file: Path
    compute: Callable[[], float]
    tolerance: float
    thesis_patterns: Sequence[str]
    suggested_script: str
    category: str
    needs_public_data: bool = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify thesis result numbers against reproducible output JSON.")
    parser.add_argument("--tolerance", type=float, default=None, help="Override all per-result tolerances.")
    args = parser.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    specs = _build_specs(args.tolerance)
    results = [_evaluate_spec(spec) for spec in specs]
    summary = _summarize(results)
    report = {
        "summary": summary,
        "source_files_checked": [str(path.relative_to(ROOT)) for path in THESIS_SOURCES],
        "results": results,
        "status_definitions": {
            "PASS": "The thesis value appears in at least one checked source file and matches computed evidence within tolerance.",
            "FAIL": "The thesis value appears in source files, evidence exists, but the computed value differs beyond tolerance.",
            "MISSING": "The thesis value or evidence is missing, so the claim is not currently verifiable from local outputs.",
        },
        "support_level_definitions": {
            "REPRODUCIBLE": "Computed from an existing local output JSON.",
            "DOCUMENT_ONLY": "Found in documents but no local evidence JSON was available.",
            "NEEDS_DATA": "Requires public/raw data or a missing generated output before verification.",
        },
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Wrote {REPORT_JSON.relative_to(ROOT)}")
    print(f"Wrote {REPORT_MD.relative_to(ROOT)}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _build_specs(tolerance_override: Optional[float]) -> List[ResultSpec]:
    tol4 = 1e-4 if tolerance_override is None else tolerance_override
    tol3 = 1e-3 if tolerance_override is None else tolerance_override
    specs: List[ResultSpec] = []

    specs.extend(
        [
            ResultSpec(
                result_name="validation_scenario_count",
                thesis_value=8.0,
                evidence_file=DATA / "validation_summary.json",
                compute=lambda: float(len(_read_json(DATA / "validation_summary.json").get("scenarios", []))),
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=["8 組標準情境", "eight canonical scenarios"],
                suggested_script="python3 scripts/run_demo.py",
                category="controlled_simulation",
            ),
            ResultSpec(
                result_name="window_matrix_case_count",
                thesis_value=48.0,
                evidence_file=DATA / "window_matrix_summary.json",
                compute=lambda: _json_metric(DATA / "window_matrix_summary.json", ["count"]),
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=["48 組窗戶矩陣", "48-case window simulation matrix"],
                suggested_script="python3 scripts/run_window_matrix.py",
                category="controlled_simulation",
            ),
            ResultSpec(
                result_name="hybrid_default_train_samples",
                thesis_value=576.0,
                evidence_file=DATA / "hybrid_residual_summary.json",
                compute=lambda: _json_metric(DATA / "hybrid_residual_summary.json", ["dataset", "train_samples"]),
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=["576 個訓練樣本", "576 training"],
                suggested_script="python3 scripts/run_hybrid_residual_experiment.py --fourier-denoise",
                category="controlled_simulation",
            ),
            ResultSpec(
                result_name="hybrid_default_test_samples",
                thesis_value=192.0,
                evidence_file=DATA / "hybrid_residual_summary.json",
                compute=lambda: _json_metric(DATA / "hybrid_residual_summary.json", ["dataset", "test_samples"]),
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=["192 個測試樣本", "192 test"],
                suggested_script="python3 scripts/run_hybrid_residual_experiment.py --fourier-denoise",
                category="controlled_simulation",
            ),
            ResultSpec(
                result_name="hybrid_loo_fold_count",
                thesis_value=8.0,
                evidence_file=DATA / "submission_readiness_summary.json",
                compute=lambda: _json_metric(DATA / "submission_readiness_summary.json", ["leave_one_scenario_out", "fold_count"]),
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=["8-fold", "leave-one-scenario-out"],
                suggested_script="python3 scripts/run_submission_readiness_experiments.py",
                category="controlled_simulation",
            ),
            ResultSpec(
                result_name="real_bedroom_snapshot_count",
                thesis_value=28.0,
                evidence_file=DATA / "bedroom_01_weekly" / "weekly_simulation_summary.json",
                compute=lambda: _json_metric(DATA / "bedroom_01_weekly" / "weekly_simulation_summary.json", ["snapshot_count"]),
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=["28 筆快照", "28 cases"],
                suggested_script="python3 scripts/run_bedroom_weekly_simulation.py",
                category="real_bedroom_snapshot",
            ),
        ]
    )

    for metric, value in {
        "temperature": 0.0474,
        "humidity": 0.1765,
        "illuminance": 2.0835,
    }.items():
        specs.append(
            ResultSpec(
                result_name=f"base_model_average_field_mae.{metric}",
                thesis_value=value,
                evidence_file=DATA / "validation_summary.json",
                compute=lambda metric=metric: _average_scenario_metric(DATA / "validation_summary.json", "field_mae", metric),
                tolerance=tol4,
                thesis_patterns=[f"{value:.4f}"],
                suggested_script="python3 scripts/run_demo.py",
                category="controlled_simulation",
            )
        )

    for metric, value in {
        "temperature": 0.1723,
        "humidity": 0.4633,
        "illuminance": 75.0516,
    }.items():
        specs.append(
            ResultSpec(
                result_name=f"idw_baseline_average_field_mae.{metric}",
                thesis_value=value,
                evidence_file=DATA / "validation_summary.json",
                compute=lambda metric=metric: _average_scenario_metric(DATA / "validation_summary.json", "idw_field_mae", metric),
                tolerance=tol4,
                thesis_patterns=[f"{value:.4f}"],
                suggested_script="python3 scripts/run_demo.py",
                category="controlled_simulation",
            )
        )

    for metric, value in {
        "temperature": 0.0023,
        "humidity": 0.0041,
        "illuminance": 0.1675,
    }.items():
        specs.append(
            ResultSpec(
                result_name=f"hybrid_residual_default_split_field_mae.{metric}",
                thesis_value=value,
                evidence_file=DATA / "hybrid_residual_summary.json",
                compute=lambda metric=metric: _json_metric(DATA / "hybrid_residual_summary.json", ["hybrid_test_field_mae", metric]),
                tolerance=tol4,
                thesis_patterns=[f"{value:.4f}"],
                suggested_script="python3 scripts/run_hybrid_residual_experiment.py --fourier-denoise",
                category="controlled_simulation",
            )
        )

    for metric, value in {
        "temperature": 0.0017,
        "humidity": 0.0055,
        "illuminance": 0.1581,
    }.items():
        specs.append(
            ResultSpec(
                result_name=f"hybrid_residual_loo_average_field_mae.{metric}",
                thesis_value=value,
                evidence_file=DATA / "submission_readiness_summary.json",
                compute=lambda metric=metric: _json_metric(
                    DATA / "submission_readiness_summary.json",
                    ["leave_one_scenario_out", "average_hybrid_field_mae", metric],
                ),
                tolerance=tol4,
                thesis_patterns=[f"{value:.4f}"],
                suggested_script="python3 scripts/run_submission_readiness_experiments.py",
                category="controlled_simulation",
            )
        )

    for prefix, evidence_key, values in [
        (
            "real_bedroom_pillow_mae_before",
            "raw_pillow_mae",
            {"temperature": 0.8967, "humidity": 4.1286, "illuminance": 358.6392},
        ),
        (
            "real_bedroom_pillow_mae_after",
            "estimated_pillow_mae",
            {"temperature": 0.1676, "humidity": 0.3939, "illuminance": 21.3753},
        ),
    ]:
        for metric, value in values.items():
            specs.append(
                ResultSpec(
                    result_name=f"{prefix}.{metric}",
                    thesis_value=value,
                    evidence_file=DATA / "bedroom_01_weekly" / "weekly_simulation_summary.json",
                    compute=lambda metric=metric, evidence_key=evidence_key: _json_metric(
                        DATA / "bedroom_01_weekly" / "weekly_simulation_summary.json",
                        ["aggregate", evidence_key, metric],
                    ),
                    tolerance=tol4 if metric != "illuminance" else tol3,
                    thesis_patterns=[f"{value:.4f}"],
                    suggested_script="python3 scripts/run_bedroom_weekly_simulation.py",
                    category="real_bedroom_snapshot",
                )
            )

    public_specs = [
        ("sml2010_public_task_count", 24, DATA / "public_benchmarks" / "sml2010_hybrid_twin_comparison.json", lambda: _public_stats("sml2010")["target_count"], ["SML2010 共 24", "24 個 target-horizon"]),
        ("sml2010_lowest_mae_count", 12, DATA / "public_benchmarks" / "sml2010_hybrid_twin_comparison.json", lambda: _public_stats("sml2010")["lowest_mae_count"], ["12 項取得最低 MAE"]),
        ("sml2010_better_than_linear_regression_count", 15, DATA / "public_benchmarks" / "sml2010_hybrid_twin_comparison.json", lambda: _public_stats("sml2010")["better_than_linear_regression_count"], ["15 項勝過 linear regression"]),
        ("sml2010_better_than_persistence_count", 14, DATA / "public_benchmarks" / "sml2010_hybrid_twin_comparison.json", lambda: _public_stats("sml2010")["better_than_persistence_count"], ["14 項勝過 persistence"]),
        ("cu_bems_public_task_count", 12, DATA / "public_benchmarks" / "cu_bems_hybrid_twin_comparison.json", lambda: _public_stats("cu_bems")["target_count"], ["CU-BEMS 共 12", "12 個 target-horizon"]),
        ("cu_bems_better_than_linear_regression_count", 9, DATA / "public_benchmarks" / "cu_bems_hybrid_twin_comparison.json", lambda: _public_stats("cu_bems")["better_than_linear_regression_count"], ["9 項 MAE 勝過 linear regression", "9 項勝過 linear regression"]),
        ("cu_bems_better_than_persistence_count", 0, DATA / "public_benchmarks" / "cu_bems_hybrid_twin_comparison.json", lambda: _public_stats("cu_bems")["better_than_persistence_count"], ["沒有任務勝過 persistence", "沒有任何一項勝過 persistence"]),
    ]
    for result_name, thesis_value, evidence_file, compute, patterns in public_specs:
        dataset = "sml2010" if result_name.startswith("sml2010") else "cu-bems"
        specs.append(
            ResultSpec(
                result_name=result_name,
                thesis_value=float(thesis_value),
                evidence_file=evidence_file,
                compute=compute,
                tolerance=0.0 if tolerance_override is None else tolerance_override,
                thesis_patterns=patterns,
                suggested_script=(
                    "python3 scripts/run_public_dataset_benchmark.py --dataset {dataset} --horizons 15,60 && "
                    "python3 scripts/run_public_dataset_model_comparison.py --dataset {dataset} --horizons 15,60"
                ).format(dataset=dataset),
                category="public_task_aligned_benchmark",
                needs_public_data=True,
            )
        )
    return specs


def _evaluate_spec(spec: ResultSpec) -> Dict[str, object]:
    thesis_sources = _find_thesis_sources(spec.thesis_patterns)
    missing_reasons = []
    computed_value: Optional[float] = None
    absolute_error: Optional[float] = None

    if not thesis_sources:
        missing_reasons.append(f"Thesis value/pattern not found: {list(spec.thesis_patterns)}")

    if not spec.evidence_file.exists():
        missing_reasons.append(f"Missing evidence file: {spec.evidence_file.relative_to(ROOT)}")
        return _result_payload(
            spec=spec,
            thesis_sources=thesis_sources,
            computed_value=None,
            absolute_error=None,
            status="MISSING",
            support_level="NEEDS_DATA" if spec.needs_public_data else "DOCUMENT_ONLY",
            missing_reasons=missing_reasons,
        )

    try:
        computed_value = float(spec.compute())
    except Exception as exc:  # noqa: BLE001 - report verification errors without hiding other rows.
        missing_reasons.append(f"Could not compute value from evidence: {exc}")
        return _result_payload(
            spec=spec,
            thesis_sources=thesis_sources,
            computed_value=None,
            absolute_error=None,
            status="MISSING",
            support_level="NEEDS_DATA" if spec.needs_public_data else "DOCUMENT_ONLY",
            missing_reasons=missing_reasons,
        )

    absolute_error = abs(float(spec.thesis_value) - computed_value)
    if missing_reasons:
        status = "MISSING"
    elif absolute_error <= spec.tolerance:
        status = "PASS"
    else:
        status = "FAIL"
    return _result_payload(
        spec=spec,
        thesis_sources=thesis_sources,
        computed_value=computed_value,
        absolute_error=absolute_error,
        status=status,
        support_level="REPRODUCIBLE",
        missing_reasons=missing_reasons,
    )


def _result_payload(
    spec: ResultSpec,
    thesis_sources: List[str],
    computed_value: Optional[float],
    absolute_error: Optional[float],
    status: str,
    support_level: str,
    missing_reasons: List[str],
) -> Dict[str, object]:
    return {
        "result_name": spec.result_name,
        "category": spec.category,
        "thesis_value": spec.thesis_value,
        "computed_value": computed_value,
        "absolute_error": absolute_error,
        "tolerance": spec.tolerance,
        "status": status,
        "support_level": support_level,
        "source_file": thesis_sources,
        "evidence_file": str(spec.evidence_file.relative_to(ROOT)),
        "suggested_script": spec.suggested_script,
        "missing_reason": missing_reasons,
    }


def _find_thesis_sources(patterns: Sequence[str]) -> List[str]:
    sources = []
    for path in THESIS_SOURCES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern in text for pattern in patterns):
            sources.append(str(path.relative_to(ROOT)))
    return sources


def _average_scenario_metric(path: Path, key: str, metric: str) -> float:
    payload = _read_json(path)
    scenarios = payload.get("scenarios", [])
    if not scenarios:
        raise ValueError("validation_summary.json has no scenarios")
    return sum(float(item[key][metric]) for item in scenarios) / float(len(scenarios))


def _json_metric(path: Path, keys: Sequence[str]) -> float:
    payload = _read_json(path)
    node = payload
    for key in keys:
        node = node[key]
    return float(node)


def _public_stats(dataset_key: str) -> Dict[str, int]:
    path = DATA / "public_benchmarks" / f"{dataset_key}_hybrid_twin_comparison.json"
    payload = _read_json(path)
    model_name = payload.get("mapped_model_name", "hybrid_digital_twin_readout")
    target_count = 0
    lowest_mae_count = 0
    better_than_linear_regression_count = 0
    better_than_persistence_count = 0
    for task in payload.get("tasks", []):
        if task.get("status") != "ok":
            continue
        for target in task.get("targets", {}).values():
            target_count += 1
            model_mae = float(target[model_name]["mae"])
            persistence_mae = float(target["persistence"]["mae"])
            linear_mae = float(target["linear_regression"]["mae"])
            if model_mae < linear_mae:
                better_than_linear_regression_count += 1
            if model_mae < persistence_mae:
                better_than_persistence_count += 1
            if model_mae < min(persistence_mae, linear_mae):
                lowest_mae_count += 1
    return {
        "target_count": target_count,
        "lowest_mae_count": lowest_mae_count,
        "better_than_linear_regression_count": better_than_linear_regression_count,
        "better_than_persistence_count": better_than_persistence_count,
    }


def _read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize(results: Sequence[Dict[str, object]]) -> Dict[str, int]:
    output = {"PASS": 0, "FAIL": 0, "MISSING": 0, "TOTAL": len(results)}
    for result in results:
        output[result["status"]] += 1
    return output


def _render_markdown(report: Dict[str, object]) -> str:
    lines = [
        "# Thesis Result Verification Report",
        "",
        "This report compares hard-coded thesis/paper values against local `outputs/data` evidence JSON files.",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| result_name | thesis_value | computed_value | abs_error | tolerance | status | support | evidence |",
            "|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for result in report["results"]:
        lines.append(
            "| {result_name} | {thesis_value} | {computed_value} | {absolute_error} | {tolerance} | {status} | {support_level} | `{evidence_file}` |".format(
                result_name=result["result_name"],
                thesis_value=_fmt(result["thesis_value"]),
                computed_value=_fmt(result["computed_value"]),
                absolute_error=_fmt(result["absolute_error"]),
                tolerance=_fmt(result["tolerance"]),
                status=result["status"],
                support_level=result["support_level"],
                evidence_file=result["evidence_file"],
            )
        )
    lines.extend(["", "## Missing Or Failed Details", ""])
    any_detail = False
    for result in report["results"]:
        if result["status"] == "PASS":
            continue
        any_detail = True
        lines.append(f"### {result['result_name']}")
        for reason in result["missing_reason"]:
            lines.append(f"- {reason}")
        lines.append(f"- suggested_script: `{result['suggested_script']}`")
        lines.append("")
    if not any_detail:
        lines.append("No missing or failed result rows.")
    return "\n".join(lines).strip() + "\n"


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


if __name__ == "__main__":
    main()
