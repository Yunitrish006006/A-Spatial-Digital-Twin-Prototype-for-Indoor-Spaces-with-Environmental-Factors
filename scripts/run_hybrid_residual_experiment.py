import json
import os
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_twin.core.service import run_hybrid_residual_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-window-matrix", action="store_true")
    parser.add_argument("--holdout-stride", type=int, default=4)
    parser.add_argument("--max-points-per-scenario", type=int, default=96)
    parser.add_argument("--hidden-dim", type=int, default=10)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.018)
    parser.add_argument("--l2", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fourier-denoise", action="store_true")
    parser.add_argument("--spectral-timeline-steps", type=int, default=9)
    parser.add_argument("--spectral-keep-frequency-ratio", type=float, default=0.35)
    parser.add_argument("--spectral-min-keep-bins", type=int, default=1)
    parser.add_argument("--spectral-metrics", default="temperature,humidity")
    args = parser.parse_args()

    output_dir = "outputs/data"
    os.makedirs(output_dir, exist_ok=True)

    result = run_hybrid_residual_experiment(
        include_window_matrix=args.include_window_matrix,
        holdout_stride=args.holdout_stride,
        max_points_per_scenario=args.max_points_per_scenario,
        hidden_dim=args.hidden_dim,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        seed=args.seed,
        use_fourier_denoising=args.fourier_denoise,
        spectral_timeline_steps=args.spectral_timeline_steps,
        spectral_keep_frequency_ratio=args.spectral_keep_frequency_ratio,
        spectral_min_keep_bins=args.spectral_min_keep_bins,
        spectral_metrics=[item.strip() for item in args.spectral_metrics.split(",") if item.strip()],
    )

    summary_path = os.path.join(output_dir, "hybrid_residual_summary.json")
    checkpoint_path = os.path.join(output_dir, "hybrid_residual_checkpoint.json")

    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump({key: value for key, value in result.items() if key != "checkpoint"}, handle, ensure_ascii=False, indent=2)

    with open(checkpoint_path, "w", encoding="utf-8") as handle:
        json.dump(result["checkpoint"], handle, ensure_ascii=False, indent=2)

    print(f"Wrote {summary_path}")
    print(f"Wrote {checkpoint_path}")
    print("Configuration:")
    print(json.dumps(result["configuration"], ensure_ascii=False, indent=2))
    print("Field MAE reduction (%):")
    for metric, reduction in result["field_mae_reduction"].items():
        print(f"  {metric}: {reduction}")


if __name__ == "__main__":
    main()
