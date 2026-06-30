"""Train the standalone local market world model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from agent.data.generate import ACTION_FEATURES, STATE_FEATURES, default_output_path, write_dataset


def default_model_path() -> Path:
    return Path("agent/artifacts/model.pt")


def load_or_create_data(path: Path, samples: int, seed: int) -> dict[str, np.ndarray]:
    if not path.exists():
        write_dataset(output=path, samples=samples, seed=seed)
    with np.load(path) as data:
        return {
            "states": data["states"].astype(np.float32),
            "actions": data["actions"].astype(np.float32),
            "next_states": data["next_states"].astype(np.float32),
        }


def train_model(
    data_path: Path,
    model_path: Path,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
    samples: int,
    json_progress: bool = False,
) -> dict[str, list[float | int]]:
    try:
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        from agent.model import MarketWorldModel, save_model
    except ModuleNotFoundError as exc:
        if exc.name == "torch":
            raise RuntimeError(
                "PyTorch is required for training. Install local project dependencies "
                "before running agent.train."
            ) from exc
        raise

    torch.manual_seed(seed)
    try:
        dataset = load_or_create_data(data_path, samples=samples, seed=seed)
    except OSError as exc:
        raise RuntimeError(
            f"Could not load or generate dataset at {data_path}. "
            "Run `python -m agent.data.generate` and try again."
        ) from exc

    tensors = TensorDataset(
        torch.from_numpy(dataset["states"]),
        torch.from_numpy(dataset["actions"]),
        torch.from_numpy(dataset["next_states"]),
    )
    train_loader = DataLoader(
        tensors,
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = MarketWorldModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    metrics: dict[str, list[float | int]] = {
        "step": [],
        "epoch": [],
        "loss": [],
        "latent_loss": [],
        "variance_loss": [],
        "covariance_loss": [],
        "readout_loss": [],
        "effective_rank": [],
    }
    step = 0

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_losses = []
        epoch_ranks = []
        for state, action, next_state in train_loader:
            parts = model.training_loss(state, action, next_state)
            loss = parts["loss"]

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            model.update_target_encoder()

            step += 1
            loss_value = float(loss.detach())
            rank_value = float(parts["effective_rank"])
            epoch_losses.append(loss_value)
            epoch_ranks.append(rank_value)

            metrics["step"].append(step)
            metrics["epoch"].append(epoch)
            metrics["loss"].append(loss_value)
            metrics["latent_loss"].append(float(parts["latent_loss"]))
            metrics["variance_loss"].append(float(parts["variance_loss"]))
            metrics["covariance_loss"].append(float(parts["covariance_loss"]))
            metrics["readout_loss"].append(float(parts["readout_loss"]))
            metrics["effective_rank"].append(rank_value)

            if json_progress:
                print(
                    json.dumps(
                        {
                            "type": "metric",
                            "step": step,
                            "epoch": epoch,
                            "loss": loss_value,
                            "effective_rank": rank_value,
                        },
                        sort_keys=True,
                    )
                )

        mean_loss = float(np.mean(epoch_losses))
        mean_rank = float(np.mean(epoch_ranks))
        if not json_progress:
            print(f"epoch={epoch:03d} loss={mean_loss:.6f} effective_rank={mean_rank:.2f}")

    save_model(model, model_path)

    artifacts_dir = model_path.parent
    metrics_path = artifacts_dir / "metrics.json"
    embeddings_path = artifacts_dir / "embeddings.npy"
    feature_spec_path = artifacts_dir / "feature_spec.json"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    model.eval()
    with torch.no_grad():
        embeddings = model.encode_state(torch.from_numpy(dataset["states"])).cpu().numpy()
    np.save(embeddings_path, embeddings.astype(np.float32))

    feature_spec = {
        "state_features": STATE_FEATURES,
        "action_features": ACTION_FEATURES,
        "normalization": {
            "type": "none",
            "value_range": [0.0, 1.0],
            "notes": "Synthetic numeric vectors are generated and clipped to [0, 1].",
        },
        "dataset": str(data_path),
        "samples": int(dataset["states"].shape[0]),
        "seed": seed,
    }
    feature_spec_path.write_text(json.dumps(feature_spec, indent=2), encoding="utf-8")

    if json_progress:
        print(json.dumps({"type": "artifact", "path": str(model_path)}, sort_keys=True))
        print(json.dumps({"type": "artifact", "path": str(metrics_path)}, sort_keys=True))
        print(json.dumps({"type": "artifact", "path": str(embeddings_path)}, sort_keys=True))
        print(json.dumps({"type": "artifact", "path": str(feature_spec_path)}, sort_keys=True))
    else:
        print(f"Saved model to {model_path}")
        print(f"Saved metrics to {metrics_path}")
        print(f"Saved embeddings to {embeddings_path}")
        print(f"Saved feature spec to {feature_spec_path}")
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the local Silicon Sandbox world model.")
    parser.add_argument("--data", type=Path, default=default_output_path(), help="Training dataset path.")
    parser.add_argument("--model", type=Path, default=default_model_path(), help="Output model path.")
    parser.add_argument("--samples", type=int, default=2_000, help="Samples to generate if data is missing.")
    parser.add_argument("--epochs", type=int, default=25, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=64, help="Training batch size.")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="Adam learning rate.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    parser.add_argument(
        "--json-progress",
        action="store_true",
        help="Stream training metrics as JSON objects.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.epochs < 1:
        raise SystemExit("--epochs must be at least 1")
    if args.samples < 1:
        raise SystemExit("--samples must be at least 1")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")

    try:
        train_model(
            data_path=args.data,
            model_path=args.model,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            seed=args.seed,
            samples=args.samples,
            json_progress=args.json_progress,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
