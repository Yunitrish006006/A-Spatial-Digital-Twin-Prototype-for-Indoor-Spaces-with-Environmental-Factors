import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_twin.core.demo import compare_fields, synthesize_sensor_observations
from digital_twin.core.scenarios import apply_truth_adjustments, build_validation_scenarios
from digital_twin.neural.hybrid_residual import (
    SpectralDenoisingConfig,
    build_residual_dataset,
    evaluate_hybrid_model_on_scenario,
    run_hybrid_residual_experiment,
    train_hybrid_residual_model,
)
from digital_twin.physics.baselines import build_idw_field
from digital_twin.physics.model import DigitalTwinModel, METRICS, TrilinearCorrection


OUTPUT_DATA = ROOT / "outputs" / "data"
OUTPUT_FIGURES = ROOT / "outputs" / "figures" / "submission"
IEEE_ASSETS = ROOT / "docs" / "papers" / "ieee" / "assets"
THESIS_ASSETS = ROOT / "docs" / "papers" / "thesis" / "assets"


class NoReflectionModel(DigitalTwinModel):
    def _reflected_illuminance(self, *args, **kwargs) -> float:
        return 0.0


def mean_metrics(rows: Iterable[Dict[str, float]]) -> Dict[str, float]:
    collected = {metric: [] for metric in METRICS}
    for row in rows:
        for metric in METRICS:
            collected[metric].append(float(row[metric]))
    return {
        metric: round(sum(values) / float(len(values)), 4)
        for metric, values in collected.items()
        if values
    }


def percent_reduction(before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
    output = {}
    for metric in METRICS:
        base = float(before[metric])
        value = 0.0 if abs(base) <= 1e-9 else (base - float(after[metric])) / base * 100.0
        output[metric] = round(value, 2)
    return output


def _truth_result(model: DigitalTwinModel, scenario):
    truth_devices = apply_truth_adjustments(scenario.devices, scenario.truth_adjustments)
    return model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=truth_devices,
        furniture=scenario.furniture,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
    )


def _estimated_with_variant(variant: str, scenario, truth_result):
    model: DigitalTwinModel = NoReflectionModel() if variant == "no_reflection" else DigitalTwinModel()
    observed_sensors = synthesize_sensor_observations(truth_result.sensor_predictions, scenario.sensors)
    default_corrections = {metric: TrilinearCorrection() for metric in METRICS}

    if variant == "raw_nominal":
        return model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
        )

    if variant == "no_calibration":
        corrections = model.fit_corrections(
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            observed_sensors=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        )
        return model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
            corrections=corrections,
        )

    if variant == "no_trilinear":
        calibrated_devices = model.calibrate_active_device_powers(
            room=scenario.room,
            environment=scenario.environment,
            devices=scenario.devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            observed_sensors=observed_sensors,
            elapsed_minutes=scenario.elapsed_minutes,
        )
        return model.simulate(
            room=scenario.room,
            environment=scenario.environment,
            devices=calibrated_devices,
            furniture=scenario.furniture,
            sensors=scenario.sensors,
            zones=scenario.zones,
            elapsed_minutes=scenario.elapsed_minutes,
            resolution=scenario.resolution,
            corrections=default_corrections,
        )

    return model.simulate(
        room=scenario.room,
        environment=scenario.environment,
        devices=scenario.devices,
        furniture=scenario.furniture,
        sensors=scenario.sensors,
        zones=scenario.zones,
        elapsed_minutes=scenario.elapsed_minutes,
        resolution=scenario.resolution,
        observed_sensors=observed_sensors,
    )


def run_base_ablation() -> Dict[str, object]:
    scenarios = build_validation_scenarios()
    truth_model = DigitalTwinModel()
    variants = [
        ("raw_nominal", "Nominal model without sensor feedback"),
        ("no_reflection", "Full estimator without one-bounce illuminance reflection"),
        ("no_calibration", "Sensor residual correction without active-device power calibration"),
        ("no_trilinear", "Active-device power calibration without trilinear residual correction"),
        ("full_base", "Full base estimator"),
    ]

    per_scenario = []
    for scenario in scenarios:
        truth = _truth_result(truth_model, scenario)
        row = {"name": scenario.name, "variants": {}}
        for variant, _description in variants:
            if variant == "full_base":
                estimated = _estimated_with_variant("full_base", scenario, truth)
            else:
                estimated = _estimated_with_variant(variant, scenario, truth)
            row["variants"][variant] = compare_fields(estimated.field, truth.field)

        idw_field = build_idw_field(
            room=scenario.room,
            sensors=scenario.sensors,
            observed_sensors=synthesize_sensor_observations(truth.sensor_predictions, scenario.sensors),
            resolution=scenario.resolution,
        )
        row["variants"]["idw"] = compare_fields(idw_field, truth.field)
        per_scenario.append(row)

    averaged = {
        variant: mean_metrics(item["variants"][variant] for item in per_scenario)
        for variant, _description in variants
    }
    averaged["idw"] = mean_metrics(item["variants"]["idw"] for item in per_scenario)
    return {
        "scenario_count": len(scenarios),
        "variants": {
            variant: {"description": description, "average_field_mae": averaged[variant]}
            for variant, description in variants
        }
        | {
            "idw": {
                "description": "Inverse-distance weighting using the same eight corner observations",
                "average_field_mae": averaged["idw"],
            }
        },
        "per_scenario": per_scenario,
    }


def run_leave_one_scenario_out(
    max_points_per_scenario: int = 96,
    hidden_dim: int = 10,
    epochs: int = 80,
    learning_rate: float = 0.018,
    l2: float = 1e-5,
    seed: int = 42,
) -> Dict[str, object]:
    scenarios = build_validation_scenarios()
    spectral_denoising = SpectralDenoisingConfig(
        enabled=True,
        timeline_steps=9,
        keep_frequency_ratio=0.35,
        min_keep_bins=1,
        metrics=("temperature", "humidity"),
    )
    folds = []
    baseline_totals = {metric: 0.0 for metric in METRICS}
    hybrid_totals = {metric: 0.0 for metric in METRICS}

    for holdout_index, holdout_scenario in enumerate(scenarios):
        train_scenarios = [
            scenario for index, scenario in enumerate(scenarios) if index != holdout_index
        ]
        test_scenarios = [holdout_scenario]
        train_dataset = build_residual_dataset(
            train_scenarios,
            max_points_per_scenario=max_points_per_scenario,
            spectral_denoising=spectral_denoising,
        )
        test_dataset = build_residual_dataset(
            test_scenarios,
            max_points_per_scenario=max_points_per_scenario,
        )
        hybrid_model, metric_training = train_hybrid_residual_model(
            train_dataset=train_dataset,
            test_dataset=test_dataset,
            hidden_dim=hidden_dim,
            epochs=epochs,
            learning_rate=learning_rate,
            l2=l2,
            seed=seed + holdout_index * 97,
        )
        evaluation = evaluate_hybrid_model_on_scenario(hybrid_model, holdout_scenario)
        for metric in METRICS:
            baseline_totals[metric] += float(evaluation["baseline_field_mae"][metric])
            hybrid_totals[metric] += float(evaluation["hybrid_field_mae"][metric])
        folds.append(
            {
                "holdout_scenario": holdout_scenario.name,
                "train_scenarios": [scenario.name for scenario in train_scenarios],
                "train_samples": len(train_dataset.features),
                "test_samples": len(test_dataset.features),
                "metric_training": metric_training,
                "baseline_field_mae": evaluation["baseline_field_mae"],
                "hybrid_field_mae": evaluation["hybrid_field_mae"],
                "field_mae_reduction": evaluation["field_mae_reduction"],
            }
        )

    fold_count = float(len(folds))
    baseline_average = {
        metric: round(baseline_totals[metric] / fold_count, 4)
        for metric in METRICS
    }
    hybrid_average = {
        metric: round(hybrid_totals[metric] / fold_count, 4)
        for metric in METRICS
    }
    return {
        "fold_count": len(folds),
        "configuration": {
            "max_points_per_scenario": max_points_per_scenario,
            "hidden_dim": hidden_dim,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "l2": l2,
            "seed": seed,
            "spectral_denoising": spectral_denoising.to_dict(),
        },
        "average_baseline_field_mae": baseline_average,
        "average_hybrid_field_mae": hybrid_average,
        "average_field_mae_reduction_percent": percent_reduction(baseline_average, hybrid_average),
        "folds": folds,
    }


def render_error_comparison(summary: Dict[str, object]) -> Path:
    OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
    base = summary["base_ablation"]["variants"]["full_base"]["average_field_mae"]
    idw = summary["base_ablation"]["variants"]["idw"]["average_field_mae"]
    loo = summary["leave_one_scenario_out"]["average_hybrid_field_mae"]
    groups = [
        ("Temperature", [idw["temperature"], base["temperature"], loo["temperature"]]),
        ("Humidity", [idw["humidity"], base["humidity"], loo["humidity"]]),
        ("Illum.", [idw["illuminance"], base["illuminance"], loo["illuminance"]]),
    ]
    labels = ["IDW", "Base", "LOO Hybrid"]
    colors = ["#8f6b2f", "#1f6f8b", "#8a2d3b"]
    width = 920
    height = 440
    margin_left = 88
    margin_bottom = 82
    plot_width = width - margin_left - 32
    plot_height = height - 86 - margin_bottom
    axis_min = 1e-3
    axis_max = 100.0
    log_min = math.log10(axis_min)
    log_span = math.log10(axis_max) - log_min

    def scale(value: float) -> float:
        clipped = max(float(value), axis_min)
        return plot_height * (math.log10(clipped) - log_min) / log_span

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="34" y="38" font-family="Arial" font-size="22" font-weight="700" fill="#202020">Field MAE comparison</text>',
        '<text x="34" y="64" font-family="Arial" font-size="13" fill="#555">Average over the eight canonical scenarios; log-scale y-axis; hybrid uses leave-one-scenario-out evaluation.</text>',
    ]
    axis_y = height - margin_bottom
    svg.append(f'<line x1="{margin_left}" y1="{axis_y}" x2="{width - 24}" y2="{axis_y}" stroke="#222" stroke-width="1.2"/>')
    svg.append(f'<line x1="{margin_left}" y1="{86}" x2="{margin_left}" y2="{axis_y}" stroke="#222" stroke-width="1.2"/>')
    for value in (0.001, 0.01, 0.1, 1.0, 10.0, 100.0):
        y = axis_y - scale(value)
        svg.append(f'<line x1="{margin_left - 5}" y1="{y:.1f}" x2="{width - 24}" y2="{y:.1f}" stroke="#e6e6e6" stroke-width="1"/>')
        svg.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" font-family="Arial" font-size="11" fill="#555" text-anchor="end">{value:g}</text>')

    group_width = plot_width / len(groups)
    bar_width = 42
    for group_index, (group_name, values) in enumerate(groups):
        group_x = margin_left + group_index * group_width + group_width * 0.18
        for value_index, value in enumerate(values):
            x = group_x + value_index * (bar_width + 10)
            bar_height = scale(value)
            y = axis_y - bar_height
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="{colors[value_index]}" rx="2"/>')
            svg.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 6:.1f}" font-family="Arial" font-size="10" fill="#333" text-anchor="middle">{value:.3g}</text>')
        svg.append(f'<text x="{group_x + 78:.1f}" y="{axis_y + 28}" font-family="Arial" font-size="13" font-weight="700" fill="#333" text-anchor="middle">{group_name}</text>')

    legend_x = margin_left
    for index, label in enumerate(labels):
        x = legend_x + index * 126
        svg.append(f'<rect x="{x}" y="{height - 34}" width="15" height="15" fill="{colors[index]}"/>')
        svg.append(f'<text x="{x + 22}" y="{height - 22}" font-family="Arial" font-size="12" fill="#333">{label}</text>')
    svg.append('</svg>')

    svg_path = OUTPUT_FIGURES / "field_mae_comparison.svg"
    svg_path.write_text("\n".join(svg), encoding="utf-8")
    png_path = OUTPUT_FIGURES / "field_mae_comparison.png"
    _render_chart_png(groups, labels, colors, png_path)
    for target_dir in (IEEE_ASSETS, THESIS_ASSETS):
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png_path, target_dir / "field_mae_comparison.png")
    return png_path


def _render_chart_png(groups, labels, colors, png_path: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        _render_svg_to_png(OUTPUT_FIGURES / "field_mae_comparison.svg", png_path)
        return

    scale_factor = 2
    width = 920
    height = 440
    margin_left = 88
    margin_bottom = 82
    plot_width = width - margin_left - 32
    plot_height = height - 86 - margin_bottom
    axis_y = height - margin_bottom
    axis_min = 1e-3
    axis_max = 100.0
    log_min = math.log10(axis_min)
    log_span = math.log10(axis_max) - log_min

    def sx(value: float) -> int:
        return int(round(value * scale_factor))

    def sy(value: float) -> int:
        return int(round(value * scale_factor))

    def scale_value(value: float) -> float:
        clipped = max(float(value), axis_min)
        return plot_height * (math.log10(clipped) - log_min) / log_span

    def hex_to_rgb(value: str) -> tuple:
        stripped = value.lstrip("#")
        return tuple(int(stripped[index : index + 2], 16) for index in (0, 2, 4))

    def font(size: int, bold: bool = False):
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/SFNS.ttf",
        ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size * scale_factor)
            except OSError:
                continue
        return ImageFont.load_default()

    def text(draw, xy, content, fill, font_obj, anchor=None):
        draw.text((sx(xy[0]), sy(xy[1])), content, fill=fill, font=font_obj, anchor=anchor)

    image = Image.new("RGBA", (sx(width), sy(height)), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font = font(22, bold=True)
    subtitle_font = font(13)
    tick_font = font(11)
    label_font = font(13, bold=True)
    value_font = font(10)
    legend_font = font(12)

    text(draw, (34, 38), "Field MAE comparison", (32, 32, 32), title_font)
    text(
        draw,
        (34, 64),
        "Average over the eight canonical scenarios; log-scale y-axis; hybrid uses leave-one-scenario-out evaluation.",
        (85, 85, 85),
        subtitle_font,
    )

    draw.line((sx(margin_left), sy(axis_y), sx(width - 24), sy(axis_y)), fill=(34, 34, 34), width=sx(1.2))
    draw.line((sx(margin_left), sy(86), sx(margin_left), sy(axis_y)), fill=(34, 34, 34), width=sx(1.2))
    for value in (0.001, 0.01, 0.1, 1.0, 10.0, 100.0):
        y = axis_y - scale_value(value)
        draw.line((sx(margin_left - 5), sy(y), sx(width - 24), sy(y)), fill=(230, 230, 230), width=sx(1))
        text(draw, (margin_left - 10, y + 4), f"{value:g}", (85, 85, 85), tick_font, anchor="ra")

    group_width = plot_width / len(groups)
    bar_width = 42
    for group_index, (group_name, values) in enumerate(groups):
        group_x = margin_left + group_index * group_width + group_width * 0.18
        for value_index, value in enumerate(values):
            x = group_x + value_index * (bar_width + 10)
            bar_height = scale_value(value)
            y = axis_y - bar_height
            draw.rounded_rectangle(
                (sx(x), sy(y), sx(x + bar_width), sy(axis_y)),
                radius=sx(2),
                fill=hex_to_rgb(colors[value_index]),
            )
            text(draw, (x + bar_width / 2, y - 6), f"{value:.3g}", (51, 51, 51), value_font, anchor="ms")
        text(draw, (group_x + 78, axis_y + 28), group_name, (51, 51, 51), label_font, anchor="mm")

    legend_x = margin_left
    for index, label in enumerate(labels):
        x = legend_x + index * 126
        draw.rectangle((sx(x), sy(height - 34), sx(x + 15), sy(height - 19)), fill=hex_to_rgb(colors[index]))
        text(draw, (x + 22, height - 22), label, (51, 51, 51), legend_font)

    image.save(png_path)


def _render_svg_to_png(svg_path: Path, png_path: Path) -> None:
    qlmanage = shutil.which("qlmanage")
    if qlmanage is None:
        raise SystemExit("qlmanage not found. It is required to render SVG figures into PNG.")
    temp_dir = png_path.parent / ".ql_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    completed = subprocess.run(
        [qlmanage, "-t", "-s", "1800", "-o", str(temp_dir), str(svg_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or completed.stdout or "Failed to render SVG via qlmanage.")
    rendered = temp_dir / f"{svg_path.name}.png"
    if not rendered.exists():
        candidates = sorted(temp_dir.glob("*.png"))
        if len(candidates) != 1:
            raise SystemExit(f"qlmanage did not produce expected PNG for {svg_path}.")
        rendered = candidates[0]
    shutil.move(str(rendered), str(png_path))
    shutil.rmtree(temp_dir)


def main() -> None:
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    base_ablation = run_base_ablation()
    default_hybrid = run_hybrid_residual_experiment(use_fourier_denoising=True)
    no_fourier_hybrid = run_hybrid_residual_experiment(use_fourier_denoising=False)
    loo = run_leave_one_scenario_out()
    summary = {
        "base_ablation": base_ablation,
        "default_holdout_hybrid": {
            "configuration": default_hybrid["configuration"],
            "dataset": default_hybrid["dataset"],
            "baseline_test_field_mae": default_hybrid["baseline_test_field_mae"],
            "hybrid_test_field_mae": default_hybrid["hybrid_test_field_mae"],
            "field_mae_reduction": default_hybrid["field_mae_reduction"],
        },
        "no_fourier_holdout_hybrid": {
            "configuration": no_fourier_hybrid["configuration"],
            "dataset": no_fourier_hybrid["dataset"],
            "baseline_test_field_mae": no_fourier_hybrid["baseline_test_field_mae"],
            "hybrid_test_field_mae": no_fourier_hybrid["hybrid_test_field_mae"],
            "field_mae_reduction": no_fourier_hybrid["field_mae_reduction"],
        },
        "leave_one_scenario_out": loo,
    }
    figure_path = render_error_comparison(summary)
    summary["figures"] = {
        "field_mae_comparison_png": str(figure_path.relative_to(ROOT)),
        "field_mae_comparison_svg": str((OUTPUT_FIGURES / "field_mae_comparison.svg").relative_to(ROOT)),
    }
    output_path = OUTPUT_DATA / "submission_readiness_summary.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
    print(f"Wrote {figure_path.relative_to(ROOT)}")
    print("Leave-one-scenario-out average field MAE:")
    print(json.dumps(loo["average_hybrid_field_mae"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
