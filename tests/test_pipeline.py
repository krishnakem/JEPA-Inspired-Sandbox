"""End-to-end pipeline smoke tests for the local Silicon Sandbox."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.config import ROUNDS, SimulationConfig, load_config_file, merge_config
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
                model_path=None,
            )
            self.assertEqual(rule_result["inputs"]["simulation_rounds"], ROUNDS)
            self.assertEqual(len(rule_result["rounds"]), ROUNDS + 1)
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
                model_path=model_path,
            )
            self.assertEqual(trained_result["inputs"]["simulation_rounds"], ROUNDS)
            self.assertEqual(len(trained_result["rounds"]), ROUNDS + 1)
            trained_report = write_report(trained_result, root / "trained-reports", "markdown")

            self.assertTrue(model_path.exists())
            self.assertTrue((model_path.parent / "metrics.json").exists())
            self.assertTrue(trained_report.exists())
            self.assert_report_sections(trained_report)

    def test_default_config_loads(self) -> None:
        config = SimulationConfig()
        self.assertEqual(config.market_dimensions[0], "demand_growth")
        self.assertEqual(config.action_dimensions[-1], "repositioning")
        self.assertEqual(config.report_format, "strategy_memo")

    def test_custom_config_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                """
                {
                  "market_dimensions": ["developer_adoption", "enterprise_trust"],
                  "action_dimensions": ["open_source_release", "enterprise_push"],
                  "actors": ["startup", "developers"],
                  "simulation_style": "aggressive",
                  "objective": "developer_adoption",
                  "report_format": "founder_memo"
                }
                """,
                encoding="utf-8",
            )
            config = load_config_file(path)
        self.assertEqual(config.market_dimensions, ["developer_adoption", "enterprise_trust"])
        self.assertEqual(config.rounds, ROUNDS)

    def test_merge_config_override_priority(self) -> None:
        config = SimulationConfig(
            industry="AI",
            market_dimensions=[
                "developer_adoption",
                "enterprise_trust",
                "switching_cost",
                "open_source_momentum",
            ],
            action_dimensions=[
                "open_source_release",
                "enterprise_push",
                "price_cut",
            ],
            actors=["startup", "developers"],
            objective="developer_adoption",
            simulation_style="aggressive",
        )
        config = merge_config(
            config,
            {"simulation_style": "regulated", "report_format": "risk_report"},
            source="test overrides",
        )
        self.assertEqual(config.industry, "AI")
        self.assertEqual(config.rounds, ROUNDS)
        self.assertEqual(config.simulation_style, "regulated")
        self.assertEqual(config.report_format, "risk_report")

    def test_custom_dimensions_actors_and_report_format(self) -> None:
        config = SimulationConfig(
            market_dimensions=[
                "developer_adoption",
                "enterprise_trust",
                "open_source_momentum",
                "margin_health",
            ],
            action_dimensions=[
                "open_source_release",
                "enterprise_push",
                "price_cut",
            ],
            actors=["startup", "incumbent", "developers"],
            industry="AI",
            simulation_style="aggressive",
            objective="developer_adoption",
            report_format="founder_memo",
        )
        result = simulate(
            current_market="AI coding assistants are growing with open source developer interest",
            company_type="startup",
            strategic_action="launch an open source release with developer marketing",
            model_path=None,
            config=config,
        )

        self.assertEqual(result["config"]["report_format"], "founder_memo")
        self.assertEqual(list(result["rounds"][-1]["updated_market_state"]), config.market_dimensions)
        self.assertEqual(list(result["action_vector"]), config.action_dimensions)
        expected_actors = [config.actors[index % len(config.actors)] for index in range(ROUNDS)]
        self.assertEqual([round_["actor"] for round_ in result["rounds"][1:]], expected_actors)

        with tempfile.TemporaryDirectory() as tmp:
            report_path = write_report(result, Path(tmp), "markdown")
            text = report_path.read_text(encoding="utf-8")
        self.assertIn("# Silicon Sandbox Founder Memo", text)
        self.assertIn("## Simulation Configuration", text)
        self.assertIn("developer adoption", text)


if __name__ == "__main__":
    unittest.main()
