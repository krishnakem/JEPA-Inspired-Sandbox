"""Train the standalone local market world model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from agent.data.generate import default_output_path, write_dataset


def default_model_path() -> Path:
    return Path("artifacts/models/market_world_model.pt")


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
) -> dict[str, list[float]]:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset, random_split

        from agent.model import MarketWorldModel, save_model
    except ModuleNotFoundError as exc:
        if exc.name == "torch":
            raise RuntimeError(
                "PyTorch is required for training. Install local project dependencies "
                "before running agent.train."
            ) from exc
        raise

    torch.manual_seed(seed)
    dataset = load_or_create_data(data_path, samples=samples, seed=seed)

    tensors = TensorDataset(
        torch.from_numpy(dataset["states"]),
        torch.from_numpy(dataset["actions"]),
        torch.from_numpy(dataset["next_states"]),
    )

    train_size = max(1, int(len(tensors) * 0.85))
    val_size = len(tensors) - train_size
    if val_size == 0:
        train_data = tensors
        val_data = tensors
    else:
        train_data, val_data = random_split(
            tensors,
            [train_size, val_size],
            generator=torch.Generator().manual_seed(seed),
        )

    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=batch_size)

    model = MarketWorldModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.MSELoss()
    history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for state, action, target in train_loader:
            prediction = model(state, action)
            loss = loss_fn(prediction, target)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        model.eval()
        val_losses = []
        with torch.no_grad():
            for state, action, target in val_loader:
                prediction = model(state, action)
                val_losses.append(float(loss_fn(prediction, target).item()))

        train_loss = float(np.mean(train_losses))
        val_loss = float(np.mean(val_losses))
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        print(f"epoch={epoch:03d} train_loss={train_loss:.6f} val_loss={val_loss:.6f}")

    save_model(model, model_path)
    history_path = model_path.with_suffix(".history.json")
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"Saved model to {model_path}")
    print(f"Saved training history to {history_path}")
    return history


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the local Silicon Sandbox world model.")
    parser.add_argument("--data", type=Path, default=default_output_path(), help="Training dataset path.")
    parser.add_argument("--model", type=Path, default=default_model_path(), help="Output model path.")
    parser.add_argument("--samples", type=int, default=2_000, help="Samples to generate if data is missing.")
    parser.add_argument("--epochs", type=int, default=25, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=64, help="Training batch size.")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="Adam learning rate.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
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
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
