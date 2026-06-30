"""Deterministic Market Vision report rendering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECTION_TITLES = [
    "Summary",
    "Simulation Configuration",
    "Major Strategic Changes",
    "Competitive Landscape",
    "Likely Winners",
    "Likely Risks",
    "Emerging Opportunities",
    "Round-by-Round Evolution",
    "Final Market State",
]

REPORT_TITLES = {
    "strategy_memo": "Silicon Sandbox Strategy Memo",
    "founder_memo": "Silicon Sandbox Founder Memo",
    "investor_memo": "Silicon Sandbox Investor Memo",
    "board_update": "Silicon Sandbox Board Update",
    "risk_report": "Silicon Sandbox Risk Report",
    "product_brief": "Silicon Sandbox Product Brief",
}


def _label(feature: str) -> str:
    return feature.replace("_", " ")


def _final_round(result: dict[str, Any]) -> dict[str, Any]:
    return result["rounds"][-1]


def _initial_state(result: dict[str, Any]) -> dict[str, float]:
    return result["rounds"][0]["updated_market_state"]


def _final_state(result: dict[str, Any]) -> dict[str, float]:
    return _final_round(result)["updated_market_state"]


def _ranked_features(state: dict[str, float], reverse: bool = True) -> list[tuple[str, float]]:
    return sorted(state.items(), key=lambda item: item[1], reverse=reverse)


def _largest_changes(result: dict[str, Any]) -> list[tuple[str, float]]:
    initial = _initial_state(result)
    final = _final_state(result)
    changes = [(feature, final[feature] - initial[feature]) for feature in final]
    return sorted(changes, key=lambda item: abs(item[1]), reverse=True)


def _sentence_list(items: list[str]) -> list[str]:
    return [item.rstrip(".") + "." for item in items if item]


def _state_value(state: dict[str, float], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in state:
            return f"{_label(candidate)} finishes at {state[candidate]:.2f}"
    for feature, value in state.items():
        tokens = set(feature.split("_"))
        if tokens.intersection(candidates):
            return f"{_label(feature)} finishes at {value:.2f}"
    return None


def _format_list(values: list[str]) -> str:
    return ", ".join(_label(value) for value in values) if values else "none"


def _format_shocks(config: dict[str, Any], result: dict[str, Any]) -> str:
    scheduled = result.get("artifact_metadata", {}).get("scheduled_shocks", [])
    if scheduled:
        parts = [f"{item['name']} in round {item['round']}" for item in scheduled]
        return ", ".join(parts)
    return _format_list(config.get("shock_events", []))


def build_report(result: dict[str, Any]) -> dict[str, Any]:
    inputs = result["inputs"]
    config = result.get("config", {})
    final_state = _final_state(result)
    strongest = _ranked_features(final_state)[0]
    weakest = _ranked_features(final_state, reverse=False)[0]
    changes = _largest_changes(result)[:3]
    positive = [item for item in changes if item[1] >= 0]
    negative = [item for item in changes if item[1] < 0]
    rounds = result["rounds"][1:]
    report_format = config.get("report_format", "strategy_memo")
    objective = config.get("objective", "market_share")
    industry = config.get("industry", "AI")

    competitive_signals = [
        _state_value(final_state, ["competition_intensity", "competition"]),
        _state_value(final_state, ["platform_power", "platform", "dependency"]),
        _state_value(final_state, ["price_pressure", "price"]),
    ]

    risk_intro = "Watch execution risk"
    if report_format == "risk_report":
        risk_intro = "Primary risk watchpoint"
    elif report_format == "founder_memo":
        risk_intro = "Founder attention should stay on"
    elif report_format == "investor_memo":
        risk_intro = "Investor diligence should test"

    sections = {
        "Summary": _sentence_list(
            [
                (
                    f"{inputs['company_type']} tests '{inputs['strategic_action']}' "
                    f"in {industry}, where {_label(strongest[0])} becomes the strongest signal"
                ),
                f"The objective is {_label(objective)} and the main constraint by the final round is {_label(weakest[0])}",
                (
                    f"The simulation used {config.get('simulation_style', 'base_case')} style "
                    f"across {inputs['simulation_rounds']} rounds in {result['mode']}"
                ),
            ]
        ),
        "Simulation Configuration": _sentence_list(
            [
                f"Industry: {industry}",
                f"Objective: {_label(objective)}",
                f"Report format: {_label(report_format)}",
                f"Active actors: {_format_list(config.get('actors', []))}",
                f"Shock events: {_format_shocks(config, result)}",
                f"Market dimensions: {_format_list(config.get('market_dimensions', []))}",
                f"Action dimensions: {_format_list(config.get('action_dimensions', []))}",
            ]
        ),
        "Major Strategic Changes": _sentence_list(
            [
                f"{_label(feature)} {'increases' if delta >= 0 else 'decreases'} by {abs(delta):.2f}"
                for feature, delta in changes
            ]
        ),
        "Competitive Landscape": _sentence_list(
            [
                (
                    "Configured actors create pressure through the selected action dimensions "
                    "rather than a fixed market sequence"
                ),
                *[item for item in competitive_signals if item],
            ]
        ),
        "Likely Winners": _sentence_list(
            [
                f"Teams with strength in {_label(strongest[0])} are positioned to compound the shift",
                f"Operators that connect the action mix to {_label(objective)} should benefit most",
            ]
        ),
        "Likely Risks": _sentence_list(
            [
                f"{risk_intro} {_label(weakest[0])}",
                "A strong actor response can compress the advantage if pressure rises faster than trust or adoption",
            ]
            + [
                f"Watch {_label(feature)} because it moved down by {abs(delta):.2f}"
                for feature, delta in negative[:1]
            ]
        ),
        "Emerging Opportunities": _sentence_list(
            [
                f"Use {_label(feature)} momentum as a wedge for near-term positioning"
                for feature, _delta in (positive[:2] or changes[:2])
            ]
        ),
        "Round-by-Round Evolution": _sentence_list(
            [
                (
                    f"Round {item['round']}: {item['actor']} - {item['action_or_reaction']}; "
                    f"{item['predicted_market_shift']} with confidence {item['confidence']:.2f}"
                )
                for item in rounds
            ]
        ),
        "Final Market State": _sentence_list(
            [
                f"{_label(feature)} ends at {value:.2f}"
                for feature, value in _ranked_features(final_state)[:5]
            ]
        ),
    }

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": REPORT_TITLES.get(report_format, "Silicon Sandbox Market Vision"),
        "inputs": inputs,
        "config": config,
        "mode": result["mode"],
        "sections": sections,
        "final_market_vision": result["final_market_vision"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    inputs = report["inputs"]
    config = report.get("config", {})
    lines = [
        f"# {report['title']}",
        "",
        f"- company type: {inputs['company_type']}",
        f"- strategic action: {inputs['strategic_action']}",
        f"- rounds: {inputs['simulation_rounds']}",
        f"- industry: {config.get('industry', 'AI')}",
        f"- objective: {_label(config.get('objective', 'market_share'))}",
        f"- simulation style: {config.get('simulation_style', 'base_case')}",
        f"- report format: {_label(config.get('report_format', 'strategy_memo'))}",
        f"- mode: {report['mode']}",
        "",
    ]
    for title in SECTION_TITLES:
        lines.append(f"## {title}")
        lines.append("")
        for item in report["sections"][title]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(result: dict[str, Any], output_dir: Path, report_format: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report = build_report(result)

    if report_format == "json":
        path = output_dir / f"market-vision-{stamp}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return path
    if report_format == "markdown":
        path = output_dir / f"market-vision-{stamp}.md"
        path.write_text(render_markdown(report), encoding="utf-8")
        return path
    raise ValueError(f"Unsupported report format: {report_format}")
