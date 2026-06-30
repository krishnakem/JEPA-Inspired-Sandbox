"""Deterministic Market Vision report rendering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECTION_TITLES = [
    "Summary",
    "Major Strategic Changes",
    "Competitive Landscape",
    "Likely Winners",
    "Likely Risks",
    "Emerging Opportunities",
    "Round-by-Round Evolution",
    "Final Market State",
]


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
    return [item.rstrip(".") + "." for item in items]


def build_report(result: dict[str, Any]) -> dict[str, Any]:
    inputs = result["inputs"]
    final_state = _final_state(result)
    strongest = _ranked_features(final_state)[0]
    weakest = _ranked_features(final_state, reverse=False)[0]
    changes = _largest_changes(result)[:3]
    positive = [item for item in changes if item[1] >= 0]
    negative = [item for item in changes if item[1] < 0]
    rounds = result["rounds"][1:]

    sections = {
        "Summary": _sentence_list(
            [
                (
                    f"{inputs['company_type']} tests '{inputs['strategic_action']}' "
                    f"against a market where {_label(strongest[0])} becomes the strongest signal"
                ),
                f"The main constraint by the final round is {_label(weakest[0])}",
                f"The simulation used {result['mode']} across {inputs['simulation_rounds']} rounds",
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
                    "Competitors are likely to respond through pricing and positioning pressure "
                    "when the company action creates visible adoption momentum"
                ),
                (
                    f"Competition intensity finishes at {final_state['competition_intensity']:.2f}, "
                    f"while platform power finishes at {final_state['platform_power']:.2f}"
                ),
            ]
        ),
        "Likely Winners": _sentence_list(
            [
                f"Teams with strength in {_label(strongest[0])} are positioned to compound the shift",
                "Vendors that pair clear product motion with trust-building distribution should benefit",
            ]
        ),
        "Likely Risks": _sentence_list(
            [
                f"Weakness in {_label(weakest[0])} could slow conversion or expansion",
                (
                    "A competitor response can compress margins if price pressure and competition "
                    "rise together"
                ),
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
        "title": "Silicon Sandbox Market Vision",
        "inputs": inputs,
        "mode": result["mode"],
        "sections": sections,
        "final_market_vision": result["final_market_vision"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    inputs = report["inputs"]
    lines = [
        f"# {report['title']}",
        "",
        f"- company type: {inputs['company_type']}",
        f"- strategic action: {inputs['strategic_action']}",
        f"- rounds: {inputs['simulation_rounds']}",
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
