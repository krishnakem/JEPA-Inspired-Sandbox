"""Run a local multi-round market simulation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from agent.data.generate import ACTION_FEATURES, STATE_FEATURES, evolve_market
from agent.report import write_report


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

ROUND_ACTORS = [
    "company",
    "competitors",
    "customers",
    "investors/regulators",
]


def clamp(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def default_model_path() -> Path:
    return Path("agent/artifacts/model.pt")


def default_output_dir() -> Path:
    return Path("agent/artifacts/simulations")


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


def actor_for_round(round_index: int) -> str:
    return ROUND_ACTORS[(round_index - 1) % len(ROUND_ACTORS)]


def action_for_actor(base_action: np.ndarray, actor: str, round_index: int) -> np.ndarray:
    action = np.zeros_like(base_action)
    base = base_action.reshape(-1)

    if actor == "company":
        action = base_action.copy()
    elif actor == "competitors":
        if base[ACTION_FEATURES.index("price_cut")] > 0:
            action[0, ACTION_FEATURES.index("product_launch")] = 0.65
        else:
            action[0, ACTION_FEATURES.index("price_cut")] = 0.62
        action[0, ACTION_FEATURES.index("repositioning")] = 0.25
    elif actor == "customers":
        action[0, ACTION_FEATURES.index("partnership")] = 0.35
        action[0, ACTION_FEATURES.index("repositioning")] = 0.45
    else:
        action[0, ACTION_FEATURES.index("partnership")] = 0.42
        action[0, ACTION_FEATURES.index("acquisition")] = 0.25

    return np.clip(action * (1.0 - 0.04 * (round_index - 1)), 0.0, 1.0).astype(np.float32)


def describe_action(actor: str, strategic_action: str, action: np.ndarray) -> str:
    if actor == "company":
        return strategic_action

    values = action.reshape(-1)
    strongest = ACTION_FEATURES[int(np.argmax(values))].replace("_", " ")
    if actor == "competitors":
        return f"competitors answer with {strongest} pressure"
    if actor == "customers":
        return f"customers shift adoption toward vendors with clearer {strongest}"
    return f"investors and regulators reassess the market through {strongest}"


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


def describe_shift(previous_state: np.ndarray, next_state: np.ndarray) -> str:
    delta = next_state.reshape(-1) - previous_state.reshape(-1)
    strongest = int(np.argmax(np.abs(delta)))
    direction = "rises" if delta[strongest] >= 0 else "softens"
    feature = STATE_FEATURES[strongest].replace("_", " ")
    return f"{feature} {direction} by {abs(float(delta[strongest])):.2f}"


def confidence_score(previous_state: np.ndarray, next_state: np.ndarray, action: np.ndarray, model_used: bool) -> float:
    shift = float(np.linalg.norm(next_state.reshape(-1) - previous_state.reshape(-1)))
    action_strength = float(np.clip(action.mean(), 0.0, 1.0))
    base = 0.62 + (0.08 if model_used else 0.0) + 0.18 * action_strength - 0.18 * shift
    return round(clamp(base), 3)


def print_json_progress(payload: dict[str, object]) -> None:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True), flush=True)


def simulate(
    current_market: str,
    company_type: str = "",
    strategic_action: str = "",
    simulation_rounds: int = 6,
    model_path: Path | None = None,
    company_profile: str | None = None,
    initial_action: str | None = None,
    json_progress: bool = False,
) -> dict[str, object]:
    company_type = company_type or company_profile or "startup"
    strategic_action = strategic_action or initial_action or "reposition the company"
    state = encode_initial_state(current_market, company_type)
    base_action = encode_action(strategic_action)
    model = None
    latent = None
    if model_path and model_path.exists():
        try:
            import torch

            from agent.model import load_model

            model = load_model(model_path)
            with torch.no_grad():
                latent = model.encode_state(torch.from_numpy(state.astype(np.float32)))
        except Exception as exc:
            print(
                f"Warning: could not load trained model at {model_path}; "
                f"falling back to rule-based local dynamics. ({exc})",
                file=sys.stderr,
            )
            model = None
            latent = None

    rounds = [
        {
            "round": 0,
            "actor": "market",
            "action_or_reaction": "starting market conditions",
            "predicted_market_shift": "baseline market state encoded from the prompt",
            "updated_market_state": state_to_dict(state),
            "confidence": 1.0,
            "summary": "Initial market representation.",
        }
    ]

    for round_index in range(1, simulation_rounds + 1):
        actor = actor_for_round(round_index)
        action = action_for_actor(base_action, actor, round_index)
        previous_state = state.copy()

        if model is None:
            state = evolve_market(state, action, rng=None, noise_scale=0.0)
        else:
            with torch.no_grad():
                action_tensor = torch.from_numpy(action.astype(np.float32))
                predicted_latent = model.predictor(
                    torch.cat(
                        [latent, action_tensor],
                        dim=-1,
                    )
                )
                prediction = model.decode_state(predicted_latent)
                latent = model.encode_state(prediction)
            state = prediction.numpy().astype(np.float32)

        round_record = {
            "round": round_index,
            "actor": actor,
            "action_or_reaction": describe_action(actor, strategic_action, action),
            "predicted_market_shift": describe_shift(previous_state, state),
            "updated_market_state": state_to_dict(state),
            "confidence": confidence_score(previous_state, state, action, model is not None),
            "summary": summarize_round(state),
        }
        rounds.append(round_record)
        if json_progress:
            print_json_progress(
                {
                    "type": "round",
                    "round": round_record["round"],
                    "actor": round_record["actor"],
                    "confidence": round_record["confidence"],
                    "summary": round_record["summary"],
                }
            )

    final_state = state.reshape(-1)
    opportunity = STATE_FEATURES[int(np.argmax(final_state))]
    constraint = STATE_FEATURES[int(np.argmin(final_state))]

    result = {
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
            feature: round(float(base_action.reshape(-1)[index]), 4)
            for index, feature in enumerate(ACTION_FEATURES)
        },
        "rounds": rounds,
        "final_market_vision": (
            f"After {simulation_rounds} rounds, the simulated market is most shaped by "
            f"{opportunity}. The main strategic constraint is {constraint}."
        ),
    }
    if json_progress:
        print_json_progress(
            {
                "type": "final",
                "mode": result["mode"],
                "final_market_vision": result["final_market_vision"],
            }
        )
    return result


def write_outputs(result: dict[str, object], output_dir: Path, report_format: str) -> Path:
    return write_report(result, output_dir=output_dir, report_format=report_format)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local Silicon Sandbox market simulation.")
    parser.add_argument("--current-market", required=True, help="Current market description.")
    parser.add_argument("--company-type", default="", help="Company type taking the action.")
    parser.add_argument("--company-profile", help="Alias for company type/profile.")
    parser.add_argument("--strategic-action", default="", help="Strategic action to simulate.")
    parser.add_argument("--initial-action", help="Alias for the initial strategic action.")
    parser.add_argument("--simulation-rounds", type=int, default=6, help="Number of rounds to run.")
    parser.add_argument("--model", type=Path, help="Optional trained model checkpoint.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Report output format.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir(),
        help="Directory for JSON and Markdown outputs.",
    )
    parser.add_argument(
        "--json-progress",
        action="store_true",
        help="Stream one compact JSON progress object per simulation round.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.simulation_rounds < 1:
        raise SystemExit("--simulation-rounds must be at least 1")
    if args.model and not args.model.exists():
        raise SystemExit(f"Model file not found: {args.model}")

    model_path = args.model
    if model_path is None and default_model_path().exists():
        model_path = default_model_path()

    result = simulate(
        current_market=args.current_market,
        company_type=args.company_type,
        strategic_action=args.strategic_action,
        simulation_rounds=args.simulation_rounds,
        model_path=model_path,
        company_profile=args.company_profile,
        initial_action=args.initial_action,
        json_progress=args.json_progress,
    )
    report_path = write_outputs(result, args.output_dir, args.format)
    print(result["final_market_vision"])
    print(f"Wrote {args.format} Market Vision report to {report_path}")


if __name__ == "__main__":
    main()
