"""End-to-end pipeline smoke tests for the local Silicon Sandbox."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.data.generate import write_dataset
from agent.report import SECTION_TITLES, write_report
from agent.simulation import simulate


class PipelineTest(unittest.TestCase):
    def assert_report_sections(self, report_path: Path) -> None:
        text = report_path.read_text(encoding="utf-8")
        for title in SECTION_TITLES:
            self.assertIn(f"## {title}", text)

    def test_rule_based_and_trained_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            rule_result = simulate(
                current_market="AI coding assistants are growing and competitive",
                company_type="startup",
                strategic_action="launch a free coding agent",
                simulation_rounds=2,
                model_path=None,
            )
            rule_report = write_report(rule_result, root / "rule-reports", "markdown")
            self.assertTrue(rule_report.exists())
            self.assert_report_sections(rule_report)

            try:
                import torch  # noqa: F401
            except ModuleNotFoundError:
                self.skipTest("PyTorch unavailable; rule-based report path passed.")

            from agent.train import train_model

            data_path = root / "data" / "market_transitions.npz"
            model_path = root / "artifacts" / "model.pt"
            write_dataset(output=data_path, samples=32, seed=11)
            train_model(
                data_path=data_path,
                model_path=model_path,
                epochs=2,
                batch_size=16,
                learning_rate=1e-3,
                seed=11,
                samples=32,
            )

            trained_result = simulate(
                current_market="AI coding assistants are growing and competitive",
                company_type="startup",
                strategic_action="launch a free coding agent",
                simulation_rounds=2,
                model_path=model_path,
            )
            trained_report = write_report(trained_result, root / "trained-reports", "markdown")

            self.assertTrue(model_path.exists())
            self.assertTrue((model_path.parent / "metrics.json").exists())
            self.assertTrue(trained_report.exists())
            self.assert_report_sections(trained_report)


if __name__ == "__main__":
    unittest.main()
