import argparse
from pathlib import Path

from digital_twin.core.public_dataset_benchmark import run_public_dataset_benchmark, write_public_dataset_benchmark_summary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_ROOT = ROOT / "outputs" / "data" / "normalized_public"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "data" / "public_benchmarks"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run shared-task benchmarks on normalized public datasets.")
    parser.add_argument("--dataset", choices=("cu-bems", "sml2010", "all"), required=True)
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument(
        "--horizons",
        default="15",
        help="Comma-separated forecast horizons in minutes, for example 15 or 15,60.",
    )
    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    horizons = [int(value.strip()) for value in args.horizons.split(",") if value.strip()]

    datasets = ["cu-bems", "sml2010"] if args.dataset == "all" else [args.dataset]
    for dataset in datasets:
        input_dir = input_root / dataset.replace("-", "_")
        summary = run_public_dataset_benchmark(dataset=dataset, input_dir=input_dir, horizons=horizons)
        output_path = output_root / f"{dataset.replace('-', '_')}_benchmark_summary.json"
        write_public_dataset_benchmark_summary(summary, output_path)
        print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()