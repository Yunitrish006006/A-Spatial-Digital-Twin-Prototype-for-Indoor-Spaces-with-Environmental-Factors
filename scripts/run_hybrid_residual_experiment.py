import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_twin.service import run_hybrid_residual_experiment


def main() -> None:
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    result = run_hybrid_residual_experiment(
        include_window_matrix=False,
        holdout_stride=4,
        max_points_per_scenario=96,
        hidden_dim=10,
        epochs=80,
        learning_rate=0.018,
        l2=1e-5,
        seed=42,
    )

    summary_path = os.path.join(output_dir, "hybrid_residual_summary.json")
    checkpoint_path = os.path.join(output_dir, "hybrid_residual_checkpoint.json")

    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump({key: value for key, value in result.items() if key != "checkpoint"}, handle, ensure_ascii=False, indent=2)

    with open(checkpoint_path, "w", encoding="utf-8") as handle:
        json.dump(result["checkpoint"], handle, ensure_ascii=False, indent=2)

    print(f"Wrote {summary_path}")
    print(f"Wrote {checkpoint_path}")
    print("Field MAE reduction (%):")
    for metric, reduction in result["field_mae_reduction"].items():
        print(f"  {metric}: {reduction}")


if __name__ == "__main__":
    main()
