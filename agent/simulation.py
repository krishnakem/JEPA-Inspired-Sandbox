"""Run a local multi-round market simulation."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from agent.actors import get_actor_profile, validate_actors
from agent.config import (
    DEFAULT_ACTION_DIMENSIONS,
    DEFAULT_MARKET_DIMENSIONS,
    LEVEL_TO_STYLE,
    SimulationConfig,
    load_config_file,
    merge_config,
    validate_config,
)
from agent.report import write_report


COMPANY_TYPE_PRIORS = {
    "startup": [0.55, 0.35, 0.45, 0.52, 0.25, 0.28, 0.42, 0.5],
    "incumbent": [0.42, 0.45, 0.65, 0.62, 0.68, 0.48, 0.67, 0.48],
    "platform": [0.5, 0.4, 0.72, 0.58, 0.82, 0.52, 0.64, 0.56],
    "niche vendor": [0.38, 0.32, 0.42, 0.7, 0.3, 0.34, 0.58, 0.42],
}

ACTION_KEYWORDS = {
    "product_launch": ["launch", "release", "product", "feature"],
    "price_cut": ["price", "discount", "cheap", "freemium", "free"],
    "partnership": ["partner", "alliance", "ecosystem", "channel"],
    "acquisition": ["acquire", "acquisition", "buy", "merge"],
    "repositioning": ["reposition", "brand", "segment", "focus"],
    "open_source_release": ["open", "source", "oss", "community", "release"],
    "enterprise_push": ["enterprise", "sales", "procurement", "security"],
    "developer_marketing": ["developer", "community", "docs", "hackathon"],
    "security_investment": ["security", "compliance", "trust", "audit"],
    "supply_chain_improvement": ["supply", "logistics", "inventory", "resilience"],
    "capacity_expansion": ["capacity", "factory", "manufacturing", "scale"],
    "creator_marketing": ["creator", "influencer", "social", "brand"],
}

STYLE_MULTIPLIERS = {
    "conservative": 0.6,
    "base_case": 1.0,
    "aggressive": 1.35,
    "chaotic": 1.7,
    "winner_take_all": 1.5,
    "regulated": 0.8,
    "capital_constrained": 0.7,
}

ACTOR_ACTION_PRIORITIES = {
    "incumbent": ["price_cut", "product_launch", "acquisition", "repositioning"],
    "competitors": ["price_cut", "product_launch", "acquisition", "repositioning"],
    "customers": ["repositioning", "partnership", "price_cut"],
    "enterprise_buyers": ["enterprise_push", "security_investment", "partnership"],
    "investors": ["acquisition", "partnership", "repositioning"],
    "regulators": ["security_investment", "repositioning", "partnership"],
    "developers": ["open_source_release", "developer_marketing", "product_launch"],
    "open_source_community": ["open_source_release", "developer_marketing"],
    "platform_owner": ["partnership", "price_cut", "repositioning"],
    "suppliers": ["supply_chain_improvement", "partnership", "price_cut"],
}


def clamp(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def default_model_path() -> Path:
    return Path("agent/artifacts/model.pt")


def default_output_dir() -> Path:
    return Path("agent/artifacts/simulations")


def is_default_vector_shape(config: SimulationConfig) -> bool:
    return (
        config.market_dimensions == DEFAULT_MARKET_DIMENSIONS
        and config.action_dimensions == DEFAULT_ACTION_DIMENSIONS
    )


def _tokens(name: str) -> list[str]:
    return [part for part in name.lower().replace("-", "_").split("_") if part]


def _dimension_index(dimensions: list[str], name: str) -> int | None:
    try:
        return dimensions.index(name)
    except ValueError:
        return None


def _find_dimension(dimensions: list[str], candidates: list[str]) -> int | None:
    for candidate in candidates:
        index = _dimension_index(dimensions, candidate)
        if index is not None:
            return index
    candidate_tokens = set(candidates)
    for index, dimension in enumerate(dimensions):
        if candidate_tokens.intersection(_tokens(dimension)):
            return index
    return None


def _bump(state: np.ndarray, dimensions: list[str], candidates: list[str], amount: float) -> None:
    for index, dimension in enumerate(dimensions):
        if dimension in candidates or set(candidates).intersection(_tokens(dimension)):
            state[index] += amount


def market_text_adjustments(current_market: str, config: SimulationConfig | None = None) -> np.ndarray:
    config = config or SimulationConfig()
    text = current_market.lower()
    state = np.zeros(len(config.market_dimensions), dtype=np.float32)

    if any(word in text for word in ["growing", "growth", "expanding", "hot"]):
        _bump(state, config.market_dimensions, ["demand", "growth", "adoption"], 0.10)
    if any(word in text for word in ["crowded", "competitive", "saturated"]):
        _bump(state, config.market_dimensions, ["competition", "intensity"], 0.12)
        _bump(state, config.market_dimensions, ["margin"], -0.05)
    if any(word in text for word in ["regulated", "compliance", "legal"]):
        _bump(state, config.market_dimensions, ["regulatory", "risk", "pressure"], 0.12)
    if any(word in text for word in ["trusted", "enterprise", "mission critical"]):
        _bump(state, config.market_dimensions, ["trust", "enterprise"], 0.08)
    if any(word in text for word in ["commoditized", "price pressure", "low margin"]):
        _bump(state, config.market_dimensions, ["price", "pressure"], 0.12)
        _bump(state, config.market_dimensions, ["margin"], -0.08)
    if any(word in text for word in ["open source", "open-source", "developer"]):
        _bump(state, config.market_dimensions, ["open", "source", "developer"], 0.08)

    return state


def encode_initial_state(
    current_market: str,
    company_type: str,
    config: SimulationConfig | None = None,
) -> np.ndarray:
    config = config or SimulationConfig()
    prior = COMPANY_TYPE_PRIORS.get(company_type.lower(), COMPANY_TYPE_PRIORS["startup"])
    prior_by_dimension = dict(zip(DEFAULT_MARKET_DIMENSIONS, prior))
    values = []

    for dimension in config.market_dimensions:
        base = prior_by_dimension.get(dimension, 0.5)
        tokens = _tokens(dimension)
        if "regulatory" in tokens or "risk" in tokens:
            base = min(base, 0.42 if company_type.lower() == "startup" else 0.55)
        if "platform" in tokens and company_type.lower() == "platform":
            base = max(base, 0.72)
        if "enterprise" in tokens and company_type.lower() == "incumbent":
            base = max(base, 0.62)
        values.append(base)

    state = np.array(values, dtype=np.float32)
    state += market_text_adjustments(current_market, config)
    return np.clip(state, 0.0, 1.0).reshape(1, -1)


def encode_action(strategic_action: str, config: SimulationConfig | None = None) -> np.ndarray:
    config = config or SimulationConfig()
    text = strategic_action.lower()
    action = np.zeros(len(config.action_dimensions), dtype=np.float32)

    for index, feature in enumerate(config.action_dimensions):
        keywords = ACTION_KEYWORDS.get(feature, _tokens(feature))
        if any(keyword in text for keyword in keywords):
            action[index] = 0.85

    if not np.any(action):
        fallback = _find_dimension(config.action_dimensions, ["repositioning", "product", "launch"])
        action[fallback if fallback is not None else 0] = 0.55

    return action.reshape(1, -1)


def actor_for_round(round_index: int, config: SimulationConfig | None = None) -> str:
    config = config or SimulationConfig()
    return config.actors[(round_index - 1) % len(config.actors)]


def _set_action(action: np.ndarray, dimensions: list[str], candidates: list[str], value: float) -> bool:
    index = _find_dimension(dimensions, candidates)
    if index is None:
        return False
    action[0, index] = max(float(action[0, index]), value)
    return True


def action_for_actor(
    base_action: np.ndarray,
    actor: str,
    round_index: int,
    config: SimulationConfig | None = None,
) -> np.ndarray:
    config = config or SimulationConfig()
    if actor in {"company", "startup"}:
        action = base_action.copy()
    else:
        action = np.zeros_like(base_action)
        priorities = ACTOR_ACTION_PRIORITIES.get(actor, ["partnership", "repositioning"])
        for offset, action_name in enumerate(priorities[:2]):
            _set_action(action, config.action_dimensions, [action_name, *_tokens(action_name)], 0.62 - 0.12 * offset)
        if not np.any(action):
            action[0, 0] = 0.45

    profile = get_actor_profile(actor)
    decay = 1.0 - 0.04 * (round_index - 1)
    return np.clip(action * profile.influence_weight * decay, 0.0, 1.0).astype(np.float32)


def describe_action(
    actor: str,
    strategic_action: str,
    action: np.ndarray,
    config: SimulationConfig | None = None,
) -> str:
    config = config or SimulationConfig()
    if actor in {"company", "startup"}:
        return strategic_action

    values = action.reshape(-1)
    strongest = config.action_dimensions[int(np.argmax(values))].replace("_", " ")
    profile = get_actor_profile(actor)
    return f"{actor} {profile.reaction_templates[0]} through {strongest}"


def _apply_action_rule(delta: np.ndarray, dimensions: list[str], candidates: list[str], value: float, coefficient: float) -> None:
    for index, dimension in enumerate(dimensions):
        tokens = set(_tokens(dimension))
        if dimension in candidates or tokens.intersection(candidates):
            delta[index] += coefficient * value


def _market_delta_from_actions(
    state: np.ndarray,
    action: np.ndarray,
    actor: str,
    round_index: int,
    config: SimulationConfig,
) -> np.ndarray:
    values = action.reshape(-1)
    delta = np.zeros(len(config.market_dimensions), dtype=np.float32)

    for index, action_dimension in enumerate(config.action_dimensions):
        value = float(values[index])
        if value <= 0:
            continue
        action_tokens = set(_tokens(action_dimension))
        if action_dimension == "product_launch" or action_tokens.intersection({"product", "launch", "release"}):
            _apply_action_rule(delta, config.market_dimensions, ["demand", "growth", "adoption"], value, 0.08)
            _apply_action_rule(delta, config.market_dimensions, ["competition", "intensity"], value, 0.06)
        if action_dimension == "price_cut" or action_tokens.intersection({"price", "cut", "discount", "free"}):
            _apply_action_rule(delta, config.market_dimensions, ["price", "pressure"], value, 0.12)
            _apply_action_rule(delta, config.market_dimensions, ["margin", "health"], value, -0.08)
            _apply_action_rule(delta, config.market_dimensions, ["adoption"], value, 0.06)
        if action_dimension == "partnership" or action_tokens.intersection({"partner", "partnership", "alliance"}):
            _apply_action_rule(delta, config.market_dimensions, ["trust", "enterprise"], value, 0.07)
            _apply_action_rule(delta, config.market_dimensions, ["platform", "dependency", "power"], value, 0.06)
            _apply_action_rule(delta, config.market_dimensions, ["margin", "health"], value, 0.03)
        if action_dimension == "acquisition" or action_tokens.intersection({"acquisition", "acquire", "buy"}):
            _apply_action_rule(delta, config.market_dimensions, ["competition", "intensity"], value, 0.06)
            _apply_action_rule(delta, config.market_dimensions, ["platform", "power"], value, 0.07)
            _apply_action_rule(delta, config.market_dimensions, ["regulatory", "risk", "pressure"], value, 0.04)
            _apply_action_rule(delta, config.market_dimensions, ["margin", "health"], value, 0.04)
        if action_dimension == "repositioning" or action_tokens.intersection({"reposition", "brand", "focus"}):
            _apply_action_rule(delta, config.market_dimensions, ["trust", "brand"], value, 0.05)
            _apply_action_rule(delta, config.market_dimensions, ["adoption", "demand"], value, 0.04)
        if action_tokens.intersection({"open", "source", "developer"}):
            _apply_action_rule(delta, config.market_dimensions, ["open", "source", "developer", "adoption"], value, 0.08)
            _apply_action_rule(delta, config.market_dimensions, ["platform", "dependency"], value, -0.04)
        if action_tokens.intersection({"enterprise", "security", "compliance"}):
            _apply_action_rule(delta, config.market_dimensions, ["enterprise", "trust", "customer"], value, 0.08)
            _apply_action_rule(delta, config.market_dimensions, ["regulatory", "risk", "pressure"], value, -0.03)
        if action_tokens.intersection({"supply", "capacity"}):
            _apply_action_rule(delta, config.market_dimensions, ["supplier", "capacity"], value, 0.08)
            _apply_action_rule(delta, config.market_dimensions, ["margin", "health"], value, 0.05)

    current = state.reshape(-1)
    demand = _find_dimension(config.market_dimensions, ["demand", "growth"])
    trust = _find_dimension(config.market_dimensions, ["trust", "enterprise"])
    price = _find_dimension(config.market_dimensions, ["price", "pressure"])
    competition = _find_dimension(config.market_dimensions, ["competition", "intensity"])
    margin = _find_dimension(config.market_dimensions, ["margin", "health"])
    adoption = _find_dimension(config.market_dimensions, ["adoption"])

    if demand is not None and adoption is not None:
        delta[adoption] += 0.025 * current[demand]
    if trust is not None and demand is not None:
        delta[demand] += 0.025 * current[trust]
    if price is not None and demand is not None:
        delta[demand] -= 0.035 * current[price]
    if competition is not None and margin is not None:
        delta[margin] -= 0.035 * current[competition]

    profile = get_actor_profile(actor)
    for affected in profile.affected_dimensions:
        index = _find_dimension(config.market_dimensions, [affected, *_tokens(affected)])
        if index is not None:
            delta[index] += 0.015 * profile.influence_weight

    multiplier = STYLE_MULTIPLIERS[config.simulation_style]
    if config.simulation_style == "winner_take_all":
        _scale_dimensions(delta, config.market_dimensions, ["platform", "competition"], 1.25)
    elif config.simulation_style == "regulated":
        _scale_dimensions(delta, config.market_dimensions, ["regulatory", "risk", "pressure"], 1.35)
    elif config.simulation_style == "capital_constrained":
        _scale_dimensions(delta, config.market_dimensions, ["margin", "investor"], 1.35)
    elif config.simulation_style == "chaotic":
        wobble = 0.015 * math.sin(round_index * 1.7 + float(values.sum()) * 3.0)
        delta += wobble

    return delta * multiplier


def _scale_dimensions(delta: np.ndarray, dimensions: list[str], tokens: list[str], scale: float) -> None:
    for index, dimension in enumerate(dimensions):
        if set(tokens).intersection(_tokens(dimension)):
            delta[index] *= scale


def evolve_configured_market(
    state: np.ndarray,
    action: np.ndarray,
    actor: str,
    round_index: int,
    config: SimulationConfig,
) -> np.ndarray:
    delta = _market_delta_from_actions(state, action, actor, round_index, config)
    return np.clip(state + delta.reshape(1, -1), 0.0, 1.0).astype(np.float32)


def state_to_dict(state: np.ndarray, config: SimulationConfig | None = None) -> dict[str, float]:
    config = config or SimulationConfig()
    values = state.reshape(-1)
    return {
        feature: round(float(values[index]), 4)
        for index, feature in enumerate(config.market_dimensions)
    }


def summarize_round(state: np.ndarray, config: SimulationConfig | None = None) -> str:
    config = config or SimulationConfig()
    values = state.reshape(-1)
    strongest = int(np.argmax(values))
    weakest = int(np.argmin(values))
    return (
        f"{config.market_dimensions[strongest]} is the strongest signal "
        f"while {config.market_dimensions[weakest]} is the main constraint."
    )


def describe_shift(
    previous_state: np.ndarray,
    next_state: np.ndarray,
    config: SimulationConfig | None = None,
) -> str:
    config = config or SimulationConfig()
    delta = next_state.reshape(-1) - previous_state.reshape(-1)
    strongest = int(np.argmax(np.abs(delta)))
    direction = "rises" if delta[strongest] >= 0 else "softens"
    feature = config.market_dimensions[strongest].replace("_", " ")
    return f"{feature} {direction} by {abs(float(delta[strongest])):.2f}"


def confidence_score(
    previous_state: np.ndarray,
    next_state: np.ndarray,
    action: np.ndarray,
    model_used: bool,
) -> float:
    shift = float(np.linalg.norm(next_state.reshape(-1) - previous_state.reshape(-1)))
    action_strength = float(np.clip(action.mean(), 0.0, 1.0))
    base = 0.62 + (0.08 if model_used else 0.0) + 0.18 * action_strength - 0.18 * shift
    return round(clamp(base), 3)


def print_json_progress(payload: dict[str, object]) -> None:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True), flush=True)


def resolve_config(args: argparse.Namespace) -> SimulationConfig:
    config = SimulationConfig()
    if args.config:
        config = load_config_file(args.config, base=config)

    cli_overrides: dict[str, Any] = {
        "rounds": args.rounds or args.simulation_rounds,
        "simulation_style": LEVEL_TO_STYLE[args.level] if args.level else None,
        "objective": args.objective,
        "industry": args.industry,
    }
    config = merge_config(config, cli_overrides, source="CLI flags")
    validate_runtime_config(config)
    return config


def validate_runtime_config(config: SimulationConfig) -> None:
    validate_config(config)
    validate_actors(config.actors)


def simulate(
    current_market: str,
    company_type: str = "",
    strategic_action: str = "",
    simulation_rounds: int | None = None,
    model_path: Path | None = None,
    company_profile: str | None = None,
    initial_action: str | None = None,
    json_progress: bool = False,
    config: SimulationConfig | None = None,
) -> dict[str, object]:
    config = config or SimulationConfig(rounds=simulation_rounds or SimulationConfig().rounds)
    if simulation_rounds is not None:
        config = merge_config(config, {"rounds": simulation_rounds}, source="simulation_rounds")
    validate_runtime_config(config)

    company_type = company_type or company_profile or "startup"
    strategic_action = strategic_action or initial_action or "reposition the company"
    state = encode_initial_state(current_market, company_type, config)
    base_action = encode_action(strategic_action, config)
    model = None
    latent = None

    if model_path and model_path.exists() and is_default_vector_shape(config):
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
    elif model_path and model_path.exists():
        print(
            "Warning: trained model dimensions do not match the selected simulation config; "
            "falling back to rule-based local dynamics.",
            file=sys.stderr,
        )

    rounds = [
        {
            "round": 0,
            "actor": "market",
            "action_or_reaction": "starting market conditions",
            "predicted_market_shift": "baseline market state encoded from the prompt",
            "updated_market_state": state_to_dict(state, config),
            "confidence": 1.0,
            "summary": "Initial market representation.",
        }
    ]

    for round_index in range(1, config.rounds + 1):
        actor = actor_for_round(round_index, config)
        action = action_for_actor(base_action, actor, round_index, config)
        previous_state = state.copy()

        if model is None:
            state = evolve_configured_market(state, action, actor, round_index, config)
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
            "actor_role": get_actor_profile(actor).role,
            "action_or_reaction": describe_action(actor, strategic_action, action, config),
            "predicted_market_shift": describe_shift(previous_state, state, config),
            "updated_market_state": state_to_dict(state, config),
            "confidence": confidence_score(previous_state, state, action, model is not None),
            "summary": summarize_round(state, config),
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
    opportunity = config.market_dimensions[int(np.argmax(final_state))]
    constraint = config.market_dimensions[int(np.argmin(final_state))]

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "current_market": current_market,
            "company_type": company_type,
            "strategic_action": strategic_action,
            "simulation_rounds": config.rounds,
            "model_path": str(model_path) if model_path else None,
        },
        "config": config.to_dict(),
        "mode": "trained_model" if model is not None else "rule_based_local_dynamics",
        "artifact_metadata": {
            "market_dimensions": config.market_dimensions,
            "action_dimensions": config.action_dimensions,
            "actors": config.actors,
        },
        "action_vector": {
            feature: round(float(base_action.reshape(-1)[index]), 4)
            for index, feature in enumerate(config.action_dimensions)
        },
        "rounds": rounds,
        "final_market_vision": (
            f"After {config.rounds} rounds in {config.industry}, the simulated market is most shaped by "
            f"{opportunity}. The main strategic constraint for {config.objective} is {constraint}."
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


def write_outputs(result: dict[str, object], output_dir: Path, output_format: str) -> Path:
    return write_report(result, output_dir=output_dir, report_format=output_format)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local Silicon Sandbox market simulation.")
    parser.add_argument("--current-market", required=True, help="Current market description.")
    parser.add_argument(
        "--company-type",
        choices=sorted(COMPANY_TYPE_PRIORS),
        default="",
        help="Company type taking the action.",
    )
    parser.add_argument("--strategic-action", default="", help="Strategic action to simulate.")
    parser.add_argument("--simulation-rounds", type=int, help="Number of rounds to run.")
    parser.add_argument("--rounds", type=int, help="Alias for --simulation-rounds.")
    parser.add_argument("--config", type=Path, help="Path to a simulation config JSON file.")
    parser.add_argument("--level", choices=sorted(LEVEL_TO_STYLE), help="Friendly simulation intensity.")
    parser.add_argument("--objective", help="Company objective to optimize the scenario around.")
    parser.add_argument("--industry", help="Industry context for the scenario.")
    parser.add_argument("--model", type=Path, help="Optional trained model checkpoint.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Report file format.",
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
    try:
        config = resolve_config(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.model and not args.model.exists():
        raise SystemExit(f"Model file not found: {args.model}")

    model_path = args.model
    if model_path is None and default_model_path().exists():
        model_path = default_model_path()

    result = simulate(
        current_market=args.current_market,
        company_type=args.company_type,
        strategic_action=args.strategic_action,
        model_path=model_path,
        json_progress=args.json_progress,
        config=config,
    )
    report_path = write_outputs(result, args.output_dir, args.format)
    print(result["final_market_vision"])
    print(f"Wrote {args.format} Market Vision report to {report_path}")


if __name__ == "__main__":
    main()
