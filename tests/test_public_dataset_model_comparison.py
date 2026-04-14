import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from digital_twin.core.public_dataset_benchmark import run_public_dataset_benchmark
from digital_twin.core.public_dataset_model_comparison import run_public_dataset_model_comparison
from digital_twin.neural.hybrid_residual import HybridResidualModel, ScalarResidualNetwork, build_feature_names
from tests.test_public_dataset_benchmark import PublicDatasetBenchmarkTests


class PublicDatasetModelComparisonTests(unittest.TestCase):
    def test_run_cu_bems_model_comparison_from_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            dataset_dir = root / "cu_bems"
            raw_dir = root / "raw"
            checkpoint_path = root / "zero_checkpoint.json"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
            self._write_zero_checkpoint(checkpoint_path)

            raw_file = raw_dir / "2019Floor2.csv"
            raw_file.write_text(
                "Date,z1_AC1(kW),z1_Light(kW),z1_Plug(kW),z1_S1(degC),z1_S1(RH%),z1_S1(lux)\n"
                "2019-01-01 08:00:00,0.0,0.0,0.2,25.00,55.00,100.00\n"
                "2019-01-01 08:01:00,1.0,0.0,0.2,24.80,54.90,99.70\n"
                "2019-01-01 08:02:00,1.0,1.0,0.1,24.61,54.80,111.40\n"
                "2,9.0,9.0,9.0,99.00,99.00,999.00\n"
                "2019-01-01 08:03:00,0.0,1.0,0.1,24.615,54.802,123.25\n"
                "2019-01-01 08:04:00,0.0,0.0,0.2,24.620,54.806,122.95\n"
                "2019-01-01 08:05:00,1.2,0.0,0.2,24.390,54.690,122.65\n"
                "2019-01-01 08:06:00,1.2,1.3,0.2,24.160,54.574,138.25\n"
                "2019-01-01 08:07:00,0.0,1.3,0.1,24.165,54.576,153.70\n",
                encoding="utf-8",
            )
            (dataset_dir / "scenario_metadata.json").write_text(
                json.dumps(
                    {
                        "dataset": "CU-BEMS",
                        "source_files": [str(raw_file)],
                        "counts": {"zones": 1, "sensor_rows": 8, "device_rows": 16, "auxiliary_rows": 8},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            baseline = run_public_dataset_benchmark("cu-bems", dataset_dir, horizons=[1])
            summary = run_public_dataset_model_comparison(
                dataset="cu-bems",
                input_dir=dataset_dir,
                horizons=[1],
                baseline_summary=baseline,
                checkpoint_path=checkpoint_path,
            )

            c1 = next(task for task in summary["tasks"] if task["task_id"] == "C1")
            self.assertEqual(c1["status"], "ok")
            self.assertIn("hybrid_digital_twin_readout", c1["targets"]["temperature"])

    def test_run_sml2010_model_comparison_from_normalized_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            dataset_dir = root / "sml2010"
            checkpoint_path = root / "zero_checkpoint.json"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            self._write_zero_checkpoint(checkpoint_path)

            fixture = PublicDatasetBenchmarkTests()
            fixture._write_sml2010_normalized_fixture(dataset_dir)

            baseline = run_public_dataset_benchmark("sml2010", dataset_dir, horizons=[1])
            summary = run_public_dataset_model_comparison(
                dataset="sml2010",
                input_dir=dataset_dir,
                horizons=[1],
                baseline_summary=baseline,
                checkpoint_path=checkpoint_path,
            )

            s2 = next(task for task in summary["tasks"] if task["task_id"] == "S2")
            self.assertEqual(s2["status"], "ok")
            self.assertIn("hybrid_digital_twin_readout", s2["targets"]["room_temperature"])

    def _write_zero_checkpoint(self, checkpoint_path: Path) -> None:
        feature_names = build_feature_names()
        metric_models = {}
        for metric in ("temperature", "humidity", "illuminance"):
            metric_models[metric] = ScalarResidualNetwork(
                feature_names=feature_names,
                input_means=[0.0 for _ in feature_names],
                input_scales=[1.0 for _ in feature_names],
                target_mean=0.0,
                target_scale=1.0,
                hidden_weights=[[0.0 for _ in feature_names]],
                hidden_biases=[0.0],
                output_weights=[0.0],
                output_bias=0.0,
            )
        HybridResidualModel(feature_names=feature_names, metric_models=metric_models).save_json(str(checkpoint_path))


if __name__ == "__main__":
    unittest.main()