"""Configurable simulation actor profiles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorProfile:
    name: str
    role: str
    influence_weight: float
    affected_dimensions: list[str]
    reaction_templates: list[str]


ACTOR_PROFILES: dict[str, ActorProfile] = {
    "company": ActorProfile(
        name="company",
        role="the focal company executes the selected strategic action",
        influence_weight=1.0,
        affected_dimensions=["demand_growth", "customer_trust", "adoption_rate"],
        reaction_templates=["executes the strategic action"],
    ),
    "startup": ActorProfile(
        name="startup",
        role="a fast-moving entrant tries to turn speed into adoption",
        influence_weight=1.0,
        affected_dimensions=["developer_adoption", "adoption_rate", "open_source_momentum"],
        reaction_templates=["pushes a focused entrant move"],
    ),
    "incumbent": ActorProfile(
        name="incumbent",
        role="established competitors defend distribution, pricing, and trust",
        influence_weight=0.9,
        affected_dimensions=["competition_intensity", "price_pressure", "platform_power"],
        reaction_templates=["responds with pricing, bundling, or distribution pressure"],
    ),
    "competitors": ActorProfile(
        name="competitors",
        role="rivals respond to visible market momentum",
        influence_weight=0.85,
        affected_dimensions=["competition_intensity", "price_pressure", "margin_health"],
        reaction_templates=["answer with pricing and positioning pressure"],
    ),
    "customers": ActorProfile(
        name="customers",
        role="buyers reveal adoption, trust, and switching-cost constraints",
        influence_weight=0.75,
        affected_dimensions=["customer_trust", "adoption_rate", "switching_cost"],
        reaction_templates=["shift adoption toward clearer value and lower risk"],
    ),
    "investors": ActorProfile(
        name="investors",
        role="capital providers reprice growth, margin, and risk expectations",
        influence_weight=0.65,
        affected_dimensions=["margin_health", "demand_growth", "competition_intensity"],
        reaction_templates=["reassess funding appetite and growth durability"],
    ),
    "regulators": ActorProfile(
        name="regulators",
        role="public authorities increase or reduce operating constraints",
        influence_weight=0.7,
        affected_dimensions=["regulatory_pressure", "regulatory_risk", "customer_trust"],
        reaction_templates=["reassess compliance, safety, and market power concerns"],
    ),
    "developers": ActorProfile(
        name="developers",
        role="technical adopters amplify or reject ecosystem momentum",
        influence_weight=0.75,
        affected_dimensions=["developer_adoption", "open_source_momentum", "platform_dependency"],
        reaction_templates=["shift attention toward tools with stronger ecosystem pull"],
    ),
    "suppliers": ActorProfile(
        name="suppliers",
        role="upstream partners shape cost, supply, and delivery reliability",
        influence_weight=0.6,
        affected_dimensions=["supplier_power", "margin_health", "production_capacity"],
        reaction_templates=["tighten or loosen operating leverage through supply terms"],
    ),
    "platform_owner": ActorProfile(
        name="platform_owner",
        role="distribution platforms change access, policy, or economics",
        influence_weight=0.8,
        affected_dimensions=["platform_power", "platform_dependency", "margin_health"],
        reaction_templates=["adjusts access terms and channel leverage"],
    ),
    "open_source_community": ActorProfile(
        name="open_source_community",
        role="community contributors change adoption and trust through openness",
        influence_weight=0.7,
        affected_dimensions=["open_source_momentum", "developer_adoption", "customer_trust"],
        reaction_templates=["amplifies or fragments ecosystem momentum"],
    ),
    "enterprise_buyers": ActorProfile(
        name="enterprise_buyers",
        role="large buyers test trust, security, integration, and procurement fit",
        influence_weight=0.8,
        affected_dimensions=["enterprise_trust", "switching_cost", "adoption_rate"],
        reaction_templates=["reward credible enterprise readiness and integration depth"],
    ),
}


def get_actor_profile(name: str) -> ActorProfile:
    return ACTOR_PROFILES[name]


def validate_actors(names: list[str]) -> None:
    unknown = [name for name in names if name not in ACTOR_PROFILES]
    if unknown:
        choices = ", ".join(sorted(ACTOR_PROFILES))
        raise ValueError(
            f"Unsupported actor(s): {', '.join(unknown)}. Supported actors: {choices}"
        )
