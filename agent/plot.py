"""Plot training history or simulation traces with Matplotlib."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent.data.generate import STATE_FEATURES


def load_pyplot():
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        if exc.name == "matplotlib":
            raise RuntimeError(
                "Matplotlib is required for plotting. Install local project dependencies "
                "before running agent.plot."
            ) from exc
        raise
    return plt


def plot_training_history(history_path: Path, output: Path) -> Path:
    plt = load_pyplot()
    history = json.loads(history_path.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 4.5))
    plt.plot(history["train_loss"], label="train")
    plt.plot(history["val_loss"], label="validation")
    plt.xlabel("Epoch")
    plt.ylabel("MSE loss")
    plt.title("Market World Model Training")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    return output


def plot_simulation_trace(trace_path: Path, output: Path) -> Path:
    plt = load_pyplot()
    payload: dict[str, Any] = json.loads(trace_path.read_text(encoding="utf-8"))
    rounds = payload["rounds"]
    output.parent.mkdir(parents=True, exist_ok=True)

    x = [item["round"] for item in rounds]
    plt.figure(figsize=(10, 5.5))
    for feature in STATE_FEATURES:
        y = [item["state"][feature] for item in rounds]
        plt.plot(x, y, label=feature)

    plt.xlabel("Round")
    plt.ylabel("Feature value")
    plt.ylim(0, 1)
    plt.title("Market Simulation Trace")
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Silicon Sandbox local artifacts.")
    parser.add_argument(
        "--history",
        type=Path,
        help="Training history JSON produced by agent.train.",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        help="Simulation trace JSON produced by agent.simulation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/plots/output.png"),
        help="Output PNG path.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if bool(args.history) == bool(args.trace):
        raise SystemExit("Provide exactly one of --history or --trace")

    try:
        if args.history:
            output = plot_training_history(args.history, args.output)
        else:
            output = plot_simulation_trace(args.trace, args.output)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Wrote plot to {output}")


if __name__ == "__main__":
    main()
