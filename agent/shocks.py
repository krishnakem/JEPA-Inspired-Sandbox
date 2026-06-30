"""External shock events for configurable simulations."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ShockEvent:
    name: str
    round: int
    effects: dict[str, float]
    explanation: str


SHOCK_DEFINITIONS: dict[str, tuple[dict[str, float], str]] = {
    "incumbent_price_war": (
        {
            "price_pressure": 0.25,
            "margin_health": -0.15,
            "competition_intensity": 0.20,
            "enterprise_trust": -0.04,
            "developer_adoption": -0.03,
        },
        "An incumbent starts a price war, raising competitive pressure and compressing margins.",
    ),
    "new_regulation": (
        {
            "regulatory_pressure": 0.25,
            "regulatory_risk": 0.25,
            "customer_trust": 0.05,
            "enterprise_trust": 0.05,
            "adoption_rate": -0.04,
        },
        "New regulation increases compliance pressure while modestly improving trust.",
    ),
    "security_incident": (
        {
            "customer_trust": -0.22,
            "enterprise_trust": -0.24,
            "regulatory_pressure": 0.12,
            "regulatory_risk": 0.14,
            "adoption_rate": -0.08,
        },
        "A security incident damages trust and invites regulatory scrutiny.",
    ),
    "funding_boom": (
        {
            "demand_growth": 0.08,
            "developer_adoption": 0.08,
            "competition_intensity": 0.12,
            "margin_health": -0.05,
        },
        "A funding boom increases experimentation and competitive entry.",
    ),
    "capital_crunch": (
        {
            "demand_growth": -0.08,
            "margin_health": -0.12,
            "competition_intensity": -0.05,
            "developer_adoption": -0.04,
        },
        "Capital tightens, reducing risk appetite and forcing margin discipline.",
    ),
    "platform_policy_change": (
        {
            "platform_power": 0.18,
            "platform_dependency": 0.20,
            "margin_health": -0.08,
            "adoption_rate": -0.04,
        },
        "A platform owner changes policy, increasing dependency and channel pressure.",
    ),
    "supply_chain_disruption": (
        {
            "supplier_power": 0.22,
            "production_capacity": -0.18,
            "margin_health": -0.12,
            "customer_trust": -0.05,
        },
        "A supply disruption reduces operating capacity and weakens margin health.",
    ),
    "open_source_breakthrough": (
        {
            "open_source_momentum": 0.24,
            "developer_adoption": 0.18,
            "platform_dependency": -0.08,
            "price_pressure": 0.05,
        },
        "An open-source breakthrough accelerates developer adoption and weakens dependency.",
    ),
    "lawsuit": (
        {
            "regulatory_pressure": 0.12,
            "regulatory_risk": 0.16,
            "customer_trust": -0.08,
            "enterprise_trust": -0.10,
            "margin_health": -0.05,
        },
        "A lawsuit increases perceived risk and slows trust-building.",
    ),
    "enterprise_standardization": (
        {
            "enterprise_trust": 0.18,
            "switching_cost": 0.12,
            "adoption_rate": 0.08,
            "competition_intensity": -0.04,
        },
        "Enterprise buyers standardize requirements, rewarding credible vendors.",
    ),
}

_SHOCK_WITH_ROUND_RE = re.compile(r"^(?P<name>[a-z][a-z0-9_]*)(?:@|:)(?P<round>[1-9][0-9]*)$")


def validate_shock_names(names: list[str]) -> None:
    unknown = []
    for item in names:
        name, _round = split_shock_name(item)
        if name not in SHOCK_DEFINITIONS:
            unknown.append(item)
    if unknown:
        choices = ", ".join(sorted(SHOCK_DEFINITIONS))
        raise ValueError(
            f"Unsupported shock event(s): {', '.join(unknown)}. Supported shocks: {choices}"
        )


def split_shock_name(item: str) -> tuple[str, int | None]:
    match = _SHOCK_WITH_ROUND_RE.match(item)
    if match:
        return match.group("name"), int(match.group("round"))
    return item, None


def schedule_shocks(names: list[str], rounds: int) -> list[ShockEvent]:
    if not names:
        return []

    validate_shock_names(names)
    scheduled: list[ShockEvent] = []
    middle_start = max(1, rounds // 2)
    span = max(1, rounds - middle_start + 1)

    for index, item in enumerate(names):
        name, explicit_round = split_shock_name(item)
        shock_round = explicit_round or min(rounds, middle_start + (index % span))
        effects, explanation = SHOCK_DEFINITIONS[name]
        scheduled.append(
            ShockEvent(
                name=name,
                round=max(1, min(rounds, shock_round)),
                effects=dict(effects),
                explanation=explanation,
            )
        )
    return scheduled
