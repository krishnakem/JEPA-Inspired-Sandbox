"""Generate developer diagnostic plots from saved artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np


def load_pyplot():
    cache_dir = Path(os.environ.get("TMPDIR", "/tmp")) / "jepa_matplotlib_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        if exc.name == "matplotlib":
            raise RuntimeError(
                "Matplotlib is required for plotting. Install local project dependencies "
                "before running agent.plot."
            ) from exc
        raise
    return plt


def default_artifacts_dir() -> Path:
    return Path("agent/artifacts")


def default_plots_dir() -> Path:
    return default_artifacts_dir() / "plots"


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise RuntimeError(
            f"Missing {description}: {path}. "
            "Run `python -m agent.train --epochs 5` before generating diagnostics."
        )


def project_2d(embeddings: np.ndarray) -> np.ndarray:
    centered = embeddings - embeddings.mean(axis=0, keepdims=True)
    _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
    return centered @ vh[:2].T


def normalized_singular_values(embeddings: np.ndarray) -> np.ndarray:
    centered = embeddings - embeddings.mean(axis=0, keepdims=True)
    singular_values = np.linalg.svd(centered, full_matrices=False, compute_uv=False)
    total = singular_values.sum()
    if total <= 0:
        return np.zeros_like(singular_values)
    return singular_values / total


def effective_rank_from_embeddings(embeddings: np.ndarray) -> float:
    values = normalized_singular_values(embeddings)
    values = values[values > 0]
    if len(values) == 0:
        return 1.0
    entropy = -float(np.sum(values * np.log(values)))
    return float(np.exp(entropy))


def load_artifacts(artifacts_dir: Path) -> tuple[np.ndarray, dict[str, Any]]:
    embeddings_path = artifacts_dir / "embeddings.npy"
    metrics_path = artifacts_dir / "metrics.json"
    require_file(embeddings_path, "embeddings artifact")
    require_file(metrics_path, "metrics artifact")

    embeddings = np.load(embeddings_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if embeddings.ndim != 2 or embeddings.shape[0] < 2:
        raise RuntimeError(f"Embeddings must be a 2D array with at least two rows: {embeddings_path}")
    if not metrics.get("effective_rank"):
        raise RuntimeError(f"Metrics must contain an effective_rank series: {metrics_path}")
    return embeddings, metrics


def plot_latent_trajectory(embeddings: np.ndarray, output: Path) -> Path:
    plt = load_pyplot()
    coords = project_2d(embeddings)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7.5, 5.5))
    order = np.arange(coords.shape[0])
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=order, s=24, cmap="viridis", alpha=0.82)
    plt.plot(coords[:, 0], coords[:, 1], color="#4b5563", linewidth=0.8, alpha=0.35)
    plt.colorbar(scatter, label="sample order")
    plt.xlabel("latent projection 1")
    plt.ylabel("latent projection 2")
    plt.title("Latent Trajectory Diagnostic")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_effective_rank(metrics: dict[str, Any], output: Path) -> Path:
    plt = load_pyplot()
    steps = metrics.get("step") or list(range(1, len(metrics["effective_rank"]) + 1))
    ranks = metrics["effective_rank"]
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 4.5))
    plt.plot(steps, ranks, color="#2563eb", linewidth=2)
    plt.axhline(1.0, color="#dc2626", linestyle="--", linewidth=1, label="collapse floor")
    plt.xlabel("training step")
    plt.ylabel("effective rank")
    plt.title("Effective Rank During JEPA Training")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def plot_collapse_comparison(embeddings: np.ndarray, output: Path) -> Path:
    plt = load_pyplot()
    healthy_values = normalized_singular_values(embeddings)
    collapsed = np.repeat(embeddings.mean(axis=0, keepdims=True), embeddings.shape[0], axis=0)
    collapsed[:, 0] += np.linspace(-1e-4, 1e-4, embeddings.shape[0])
    collapsed_values = normalized_singular_values(collapsed)
    healthy_rank = effective_rank_from_embeddings(embeddings)
    collapsed_rank = effective_rank_from_embeddings(collapsed)
    limit = min(12, len(healthy_values), len(collapsed_values))
    x = np.arange(limit)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 4.8))
    plt.bar(x - 0.18, healthy_values[:limit], width=0.36, label=f"healthy rank {healthy_rank:.2f}")
    plt.bar(x + 0.18, collapsed_values[:limit], width=0.36, label=f"collapsed rank {collapsed_rank:.2f}")
    plt.xlabel("singular value index")
    plt.ylabel("normalized weight")
    plt.title("Healthy vs. Collapsed Latent Spectrum")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    return output


def generate_diagnostics(artifacts_dir: Path, plots_dir: Path) -> list[Path]:
    embeddings, metrics = load_artifacts(artifacts_dir)
    return [
        plot_latent_trajectory(embeddings, plots_dir / "latent_trajectory.png"),
        plot_effective_rank(metrics, plots_dir / "effective_rank.png"),
        plot_collapse_comparison(embeddings, plots_dir / "collapse_comparison.png"),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Silicon Sandbox diagnostics.")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=default_artifacts_dir(),
        help="Directory containing metrics.json and embeddings.npy.",
    )
    parser.add_argument(
        "--plots-dir",
        type=Path,
        default=default_plots_dir(),
        help="Directory for diagnostic PNG outputs.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        outputs = generate_diagnostics(args.artifacts_dir, args.plots_dir)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    for output in outputs:
        print(f"Wrote plot to {output}")


if __name__ == "__main__":
    main()
