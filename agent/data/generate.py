"""Generate small local transition datasets for market-world experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

STATE_FEATURES = [
    "demand_growth",
    "price_pressure",
    "competition_intensity",
    "customer_trust",
    "platform_power",
    "regulatory_pressure",
    "margin_health",
    "adoption_rate",
]

ACTION_FEATURES = [
    "product_launch",
    "price_cut",
    "partnership",
    "acquisition",
    "repositioning",
]

INDUSTRIES = [
    "AI",
    "SaaS",
    "Consumer Technology",
    "Retail",
    "Manufacturing",
]

TRANSITION_TYPES = [
    "product launch",
    "price cut",
    "open-source release",
    "enterprise expansion",
    "regulatory pressure",
    "competitor response",
    "customer adoption shift",
    "supply chain improvement",
]


def default_output_path() -> Path:
    return Path("agent/artifacts/data/market_transitions.npz")


def default_jsonl_path() -> Path:
    return Path("agent/artifacts/data/market_transitions.jsonl")


def sample_states(rng: np.random.Generator, count: int) -> np.ndarray:
    """Return bounded market state vectors in the range [0, 1]."""
    return rng.uniform(0.15, 0.85, size=(count, len(STATE_FEATURES))).astype(np.float32)


def sample_actions(rng: np.random.Generator, count: int) -> np.ndarray:
    """Return sparse strategic action vectors in the range [0, 1]."""
    actions = np.zeros((count, len(ACTION_FEATURES)), dtype=np.float32)
    primary = rng.integers(0, len(ACTION_FEATURES), size=count)
    actions[np.arange(count), primary] = rng.uniform(0.45, 1.0, size=count)

    secondary_mask = rng.random(count) < 0.25
    secondary = rng.integers(0, len(ACTION_FEATURES), size=count)
    actions[secondary_mask, secondary[secondary_mask]] = rng.uniform(
        0.1, 0.45, size=secondary_mask.sum()
    )
    return actions


def evolve_market(
    states: np.ndarray,
    actions: np.ndarray,
    rng: np.random.Generator | None = None,
    noise_scale: float = 0.015,
) -> np.ndarray:
    """Apply transparent local market dynamics for one simulation step."""
    next_states = states.copy()

    product_launch = actions[:, 0]
    price_cut = actions[:, 1]
    partnership = actions[:, 2]
    acquisition = actions[:, 3]
    repositioning = actions[:, 4]

    next_states[:, 0] += 0.09 * product_launch + 0.04 * repositioning + 0.03 * partnership
    next_states[:, 1] += 0.12 * price_cut + 0.03 * acquisition
    next_states[:, 2] += 0.08 * product_launch + 0.05 * price_cut + 0.06 * acquisition
    next_states[:, 3] += 0.07 * partnership + 0.05 * repositioning - 0.04 * price_cut
    next_states[:, 4] += 0.08 * partnership + 0.07 * acquisition
    next_states[:, 5] += 0.04 * acquisition + 0.02 * product_launch
    next_states[:, 6] += 0.05 * acquisition + 0.03 * partnership - 0.08 * price_cut
    next_states[:, 7] += 0.08 * product_launch + 0.06 * price_cut + 0.04 * repositioning

    demand_growth = states[:, 0]
    price_pressure = states[:, 1]
    competition = states[:, 2]
    trust = states[:, 3]
    margin = states[:, 6]

    next_states[:, 0] += 0.03 * trust - 0.04 * price_pressure
    next_states[:, 2] += 0.04 * demand_growth
    next_states[:, 6] += 0.03 * demand_growth - 0.04 * competition
    next_states[:, 7] += 0.03 * demand_growth + 0.02 * trust

    if rng is not None and noise_scale > 0:
        next_states += rng.normal(0.0, noise_scale, size=next_states.shape).astype(np.float32)

    return np.clip(next_states, 0.0, 1.0).astype(np.float32)


def generate_dataset(samples: int, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    states = sample_states(rng, samples)
    actions = sample_actions(rng, samples)
    next_states = evolve_market(states, actions, rng=rng)
    return {
        "states": states,
        "actions": actions,
        "next_states": next_states,
    }


def _feature_phrase(features: list[str], values: np.ndarray, high_label: str, low_label: str) -> str:
    high_index = int(np.argmax(values))
    low_index = int(np.argmin(values))
    high_name = features[high_index].replace("_", " ")
    low_name = features[low_index].replace("_", " ")
    return (
        f"{high_label} {high_name} at {values[high_index]:.2f}; "
        f"{low_label} {low_name} at {values[low_index]:.2f}"
    )


def render_market_state(state: np.ndarray) -> str:
    return _feature_phrase(STATE_FEATURES, state, "strongest", "softest")


def render_company_action(action: np.ndarray) -> str:
    primary_index = int(np.argmax(action))
    primary_name = ACTION_FEATURES[primary_index].replace("_", " ")
    active = [
        f"{name.replace('_', ' ')} {value:.2f}"
        for name, value in zip(ACTION_FEATURES, action)
        if value >= 0.1
    ]
    if not active:
        return "no material action"
    return f"primary {primary_name}; mix: {', '.join(active)}"


def choose_industry(state: np.ndarray, action: np.ndarray, index: int, seed: int) -> str:
    signal = int(round(float((state.sum() + action.sum()) * 100)))
    return INDUSTRIES[(signal + index + seed) % len(INDUSTRIES)]


def choose_transition_type(state: np.ndarray, action: np.ndarray, next_state: np.ndarray) -> str:
    primary_action = int(np.argmax(action))
    delta = next_state - state
    if state[5] > 0.68 or delta[5] > 0.04:
        return "regulatory pressure"
    if delta[2] > 0.07:
        return "competitor response"
    if delta[7] > 0.07:
        return "customer adoption shift"
    if delta[6] > 0.05:
        return "supply chain improvement"
    return TRANSITION_TYPES[primary_action]


def write_jsonl_sidecar(
    path: Path,
    dataset: dict[str, np.ndarray],
    seed: int,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index, (state, action, next_state) in enumerate(
            zip(dataset["states"], dataset["actions"], dataset["next_states"])
        ):
            record = {
                "current_market_state": render_market_state(state),
                "company_action": render_company_action(action),
                "future_market_state": render_market_state(next_state),
                "industry": choose_industry(state, action, index=index, seed=seed),
                "transition_type": choose_transition_type(state, action, next_state),
                "metadata": {
                    "seed": seed,
                    "state_vector": state.tolist(),
                    "action_vector": action.tolist(),
                    "next_state_vector": next_state.tolist(),
                },
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def write_dataset(output: Path, samples: int, seed: int) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset = generate_dataset(samples=samples, seed=seed)
    np.savez_compressed(output, **dataset)

    metadata = {
        "samples": samples,
        "seed": seed,
        "state_features": STATE_FEATURES,
        "action_features": ACTION_FEATURES,
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_jsonl_sidecar(path=default_jsonl_path(), dataset=dataset, seed=seed)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate local Silicon Sandbox transition data.")
    parser.add_argument("--samples", type=int, default=200, help="Number of transitions to create.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducible data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_path(),
        help="Path for the compressed NumPy dataset.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be at least 1")

    output = write_dataset(output=args.output, samples=args.samples, seed=args.seed)
    print(f"Wrote {args.samples} transitions to {output}")
    print(f"Wrote metadata to {output.with_suffix('.json')}")
    print(f"Wrote readable JSONL to {default_jsonl_path()}")


if __name__ == "__main__":
    main()
