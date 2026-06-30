"""Run a local multi-round market simulation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from agent.data.generate import ACTION_FEATURES, STATE_FEATURES, evolve_market


COMPANY_TYPE_PRIORS = {
    "startup": [0.55, 0.35, 0.45, 0.52, 0.25, 0.28, 0.42, 0.5],
    "incumbent": [0.42, 0.45, 0.65, 0.62, 0.68, 0.48, 0.67, 0.48],
    "platform": [0.5, 0.4, 0.72, 0.58, 0.82, 0.52, 0.64, 0.56],
    "niche vendor": [0.38, 0.32, 0.42, 0.7, 0.3, 0.34, 0.58, 0.42],
}

ACTION_KEYWORDS = {
    "product_launch": ["launch", "release", "product", "feature"],
    "price_cut": ["price", "discount", "cheap", "freemium"],
    "partnership": ["partner", "alliance", "ecosystem", "channel"],
    "acquisition": ["acquire", "acquisition", "buy", "merge"],
    "repositioning": ["reposition", "brand", "segment", "focus"],
}


def clamp(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def market_text_adjustments(current_market: str) -> np.ndarray:
    text = current_market.lower()
    state = np.zeros(len(STATE_FEATURES), dtype=np.float32)

    if any(word in text for word in ["growing", "growth", "expanding", "hot"]):
        state[0] += 0.12
        state[7] += 0.08
    if any(word in text for word in ["crowded", "competitive", "saturated"]):
        state[2] += 0.14
        state[6] -= 0.06
    if any(word in text for word in ["regulated", "compliance", "legal"]):
        state[5] += 0.12
    if any(word in text for word in ["trusted", "enterprise", "mission critical"]):
        state[3] += 0.08
    if any(word in text for word in ["commoditized", "price pressure", "low margin"]):
        state[1] += 0.12
        state[6] -= 0.08

    return state


def encode_initial_state(current_market: str, company_type: str) -> np.ndarray:
    base = COMPANY_TYPE_PRIORS.get(company_type.lower(), COMPANY_TYPE_PRIORS["startup"])
    state = np.array(base, dtype=np.float32)
    state += market_text_adjustments(current_market)
    return np.clip(state, 0.0, 1.0).reshape(1, -1)


def encode_action(strategic_action: str) -> np.ndarray:
    text = strategic_action.lower()
    action = np.zeros(len(ACTION_FEATURES), dtype=np.float32)

    for index, feature in enumerate(ACTION_FEATURES):
        keywords = ACTION_KEYWORDS[feature]
        if any(keyword in text for keyword in keywords):
            action[index] = 0.85

    if not np.any(action):
        action[ACTION_FEATURES.index("repositioning")] = 0.55

    return action.reshape(1, -1)


def state_to_dict(state: np.ndarray) -> dict[str, float]:
    values = state.reshape(-1)
    return {feature: round(float(values[index]), 4) for index, feature in enumerate(STATE_FEATURES)}


def summarize_round(state: np.ndarray) -> str:
    values = state.reshape(-1)
    strongest = int(np.argmax(values))
    weakest = int(np.argmin(values))
    return (
        f"{STATE_FEATURES[strongest]} is the strongest signal "
        f"while {STATE_FEATURES[weakest]} is the main constraint."
    )


def simulate(
    current_market: str,
    company_type: str,
    strategic_action: str,
    simulation_rounds: int,
    model_path: Path | None = None,
) -> dict[str, object]:
    state = encode_initial_state(current_market, company_type)
    action = encode_action(strategic_action)
    model = None
    if model_path:
        import torch

        from agent.model import load_model

        model = load_model(model_path)

    rounds = [
        {
            "round": 0,
            "state": state_to_dict(state),
            "summary": "Initial encoded market representation.",
        }
    ]

    for round_index in range(1, simulation_rounds + 1):
        if model is None:
            state = evolve_market(state, action, rng=None, noise_scale=0.0)
        else:
            with torch.no_grad():
                prediction = model.predict_next(
                    torch.from_numpy(state.astype(np.float32)),
                    torch.from_numpy(action.astype(np.float32)),
                )
            state = prediction.numpy().astype(np.float32)

        rounds.append(
            {
                "round": round_index,
                "state": state_to_dict(state),
                "summary": summarize_round(state),
            }
        )

    final_state = state.reshape(-1)
    opportunity = STATE_FEATURES[int(np.argmax(final_state))]
    constraint = STATE_FEATURES[int(np.argmin(final_state))]

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "current_market": current_market,
            "company_type": company_type,
            "strategic_action": strategic_action,
            "simulation_rounds": simulation_rounds,
            "model_path": str(model_path) if model_path else None,
        },
        "mode": "trained_model" if model is not None else "rule_based_local_dynamics",
        "action_vector": {
            feature: round(float(action.reshape(-1)[index]), 4)
            for index, feature in enumerate(ACTION_FEATURES)
        },
        "rounds": rounds,
        "final_market_vision": (
            f"After {simulation_rounds} rounds, the simulated market is most shaped by "
            f"{opportunity}. The main strategic constraint is {constraint}."
        ),
    }


def write_outputs(result: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"simulation-{stamp}.json"
    md_path = output_dir / f"simulation-{stamp}.md"

    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    inputs = result["inputs"]
    rounds = result["rounds"]
    lines = [
        "# Silicon Sandbox Market Vision",
        "",
        f"- company type: {inputs['company_type']}",
        f"- strategic action: {inputs['strategic_action']}",
        f"- rounds: {inputs['simulation_rounds']}",
        f"- mode: {result['mode']}",
        "",
        "## Final Market Vision",
        "",
        str(result["final_market_vision"]),
        "",
        "## Round Trace",
        "",
    ]
    for item in rounds:
        lines.append(f"### Round {item['round']}")
        lines.append("")
        lines.append(str(item["summary"]))
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local Silicon Sandbox market simulation.")
    parser.add_argument("--current-market", required=True, help="Current market description.")
    parser.add_argument("--company-type", required=True, help="Company type taking the action.")
    parser.add_argument("--strategic-action", required=True, help="Strategic action to simulate.")
    parser.add_argument("--simulation-rounds", type=int, default=6, help="Number of rounds to run.")
    parser.add_argument("--model", type=Path, help="Optional trained model checkpoint.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/simulations"),
        help="Directory for JSON and Markdown outputs.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.simulation_rounds < 1:
        raise SystemExit("--simulation-rounds must be at least 1")
    if args.model and not args.model.exists():
        raise SystemExit(f"Model file not found: {args.model}")

    result = simulate(
        current_market=args.current_market,
        company_type=args.company_type,
        strategic_action=args.strategic_action,
        simulation_rounds=args.simulation_rounds,
        model_path=args.model,
    )
    json_path, md_path = write_outputs(result, args.output_dir)
    print(result["final_market_vision"])
    print(f"Wrote JSON trace to {json_path}")
    print(f"Wrote Markdown summary to {md_path}")


if __name__ == "__main__":
    main()
