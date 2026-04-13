import unittest

from digital_twin.core.scenarios import build_validation_scenarios
from digital_twin.neural.hybrid_residual import (
    HybridResidualModel,
    build_residual_dataset,
    run_hybrid_residual_experiment,
)


class HybridResidualTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
