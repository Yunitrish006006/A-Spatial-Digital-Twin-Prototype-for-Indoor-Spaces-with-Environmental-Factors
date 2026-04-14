import argparse
import json
from pathlib import Path

from digital_twin.core.public_dataset_alignment import normalize_cu_bems_dataset, normalize_sml2010_dataset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = ROOT / "outputs" / "data" / "raw_public"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "data" / "normalized_public"


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize public benchmark datasets into repo-aligned templates.")
    parser.add_argument("--dataset", choices=("cu-bems", "sml2010", "all"), required=True)
    parser.add_argument("--input", dest="input_path", help="Optional dataset-specific input path.")
    parser.add_argument("--raw-root", default=str(DEFAULT_RAW_ROOT), help="Root directory that stores raw public datasets.")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory where normalized public benchmark files will be written.",
    )
    args = parser.parse_args()

    raw_root = Path(args.raw_root)
    output_root = Path(args.output_root)

    if args.dataset == "all":
        summaries = {
            "cu-bems": normalize_cu_bems_dataset(_resolve_input_path(args.input_path, raw_root / "cu-bems", "cu-bems"), output_root / "cu_bems"),
            "sml2010": normalize_sml2010_dataset(_resolve_input_path(args.input_path, raw_root / "sml2010", "sml2010"), output_root / "sml2010"),
        }
        print(json.dumps(summaries, ensure_ascii=False, indent=2))
        return

    input_path = _resolve_input_path(args.input_path, raw_root / args.dataset, args.dataset)
    if args.dataset == "cu-bems":
        summary = normalize_cu_bems_dataset(input_path, output_root / "cu_bems")
    else:
        summary = normalize_sml2010_dataset(input_path, output_root / "sml2010")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _resolve_input_path(explicit_input: str, default_path: Path, dataset: str) -> Path:
    if explicit_input:
        return Path(explicit_input)
    if default_path.exists():
        return default_path
    raise FileNotFoundError(f"No input path found for {dataset}. Expected {default_path} or pass --input.")


if __name__ == "__main__":
    main()