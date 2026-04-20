import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from digital_twin.core.scenarios import build_validation_scenarios
from digital_twin.neural.hybrid_residual import (
    HybridResidualModel,
    apply_fourier_low_pass_filter,
    build_residual_dataset,
    run_hybrid_residual_experiment,
)


class HybridResidualTests(unittest.TestCase):
    def test_fourier_low_pass_filter_suppresses_high_frequency_component(self) -> None:
        raw_signal = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
        filtered = apply_fourier_low_pass_filter(raw_signal, keep_frequency_ratio=0.2, min_keep_bins=1)

        self.assertEqual(len(filtered), len(raw_signal))
        self.assertLess(max(abs(value) for value in filtered), 0.35)

    def test_residual_dataset_builds_features_and_targets(self) -> None:
        scenarios = build_validation_scenarios()[:2]
        dataset = build_residual_dataset(scenarios, max_points_per_scenario=12)

        self.assertTrue(dataset.features)
        self.assertEqual(len(dataset.features), len(dataset.targets["temperature"]))
        self.assertEqual(len(dataset.feature_names), len(dataset.features[0]))
        self.assertIn("estimated_temperature", dataset.feature_names)
        self.assertIn("ac_main_envelope", dataset.feature_names)

    def test_hybrid_residual_experiment_improves_temperature_field_mae(self) -> None:
        result = run_hybrid_residual_experiment(
            include_window_matrix=False,
            holdout_stride=4,
            max_points_per_scenario=48,
            hidden_dim=8,
            epochs=50,
            learning_rate=0.015,
            l2=1e-5,
            seed=42,
        )

        self.assertLess(
            result["hybrid_test_field_mae"]["temperature"],
            result["baseline_test_field_mae"]["temperature"],
        )
        self.assertLess(
            result["hybrid_test_target_zone_mae"]["temperature"],
            result["baseline_test_target_zone_mae"]["temperature"],
        )

        restored = HybridResidualModel.from_dict(result["checkpoint"])
        self.assertEqual(restored.feature_names, result["feature_names"])

    def test_hybrid_residual_experiment_runs_with_fourier_denoising(self) -> None:
        result = run_hybrid_residual_experiment(
            include_window_matrix=False,
            holdout_stride=4,
            max_points_per_scenario=32,
            hidden_dim=6,
            epochs=30,
            learning_rate=0.015,
            l2=1e-5,
            seed=42,
            use_fourier_denoising=True,
            spectral_timeline_steps=7,
            spectral_keep_frequency_ratio=0.35,
            spectral_min_keep_bins=1,
        )

        self.assertTrue(result["configuration"]["spectral_denoising"]["enabled"])
        self.assertLess(
            result["hybrid_test_field_mae"]["temperature"],
            result["baseline_test_field_mae"]["temperature"],
        )


if __name__ == "__main__":
    unittest.main()
