"""Built-in simulation presets."""

from __future__ import annotations

from agent.config import SimulationConfig, merge_config


PRESETS: dict[str, dict[str, object]] = {
    "ai_startup": {
        "industry": "AI",
        "market_dimensions": [
            "developer_adoption",
            "enterprise_trust",
            "switching_cost",
            "open_source_momentum",
            "platform_dependency",
            "regulatory_risk",
            "margin_health",
            "adoption_rate",
        ],
        "action_dimensions": [
            "open_source_release",
            "enterprise_push",
            "price_cut",
            "developer_marketing",
            "partnership",
        ],
        "actors": ["startup", "incumbent", "developers", "enterprise_buyers", "investors"],
        "objective": "developer_adoption",
        "simulation_style": "aggressive",
        "shock_events": ["incumbent_price_war", "open_source_breakthrough"],
    },
    "saas_enterprise": {
        "industry": "SaaS",
        "market_dimensions": [
            "enterprise_trust",
            "sales_cycle_pressure",
            "switching_cost",
            "competition_intensity",
            "platform_power",
            "margin_health",
            "adoption_rate",
        ],
        "action_dimensions": [
            "enterprise_push",
            "price_cut",
            "partnership",
            "security_investment",
            "repositioning",
        ],
        "actors": ["company", "incumbent", "enterprise_buyers", "investors", "regulators"],
        "objective": "enterprise_trust",
        "simulation_style": "base_case",
        "shock_events": ["enterprise_standardization"],
    },
    "consumer_tech": {
        "industry": "Consumer Technology",
        "market_dimensions": [
            "consumer_demand",
            "brand_trust",
            "competition_intensity",
            "platform_dependency",
            "price_pressure",
            "adoption_rate",
        ],
        "action_dimensions": [
            "product_launch",
            "price_cut",
            "creator_marketing",
            "partnership",
            "repositioning",
        ],
        "actors": ["company", "customers", "platform_owner", "investors"],
        "objective": "adoption_rate",
        "simulation_style": "chaotic",
        "shock_events": ["platform_policy_change"],
    },
    "retail": {
        "industry": "Retail",
        "market_dimensions": [
            "consumer_demand",
            "price_pressure",
            "supplier_power",
            "competition_intensity",
            "margin_health",
            "brand_trust",
        ],
        "action_dimensions": [
            "price_cut",
            "partnership",
            "supply_chain_improvement",
            "repositioning",
        ],
        "actors": ["company", "customers", "suppliers", "incumbent", "investors"],
        "objective": "margin_health",
        "simulation_style": "capital_constrained",
        "shock_events": ["supply_chain_disruption"],
    },
    "manufacturing": {
        "industry": "Manufacturing",
        "market_dimensions": [
            "demand_growth",
            "supplier_power",
            "production_capacity",
            "regulatory_pressure",
            "margin_health",
            "customer_trust",
        ],
        "action_dimensions": [
            "capacity_expansion",
            "partnership",
            "acquisition",
            "price_cut",
            "supply_chain_improvement",
        ],
        "actors": ["company", "suppliers", "customers", "regulators", "investors"],
        "objective": "margin_health",
        "simulation_style": "conservative",
        "shock_events": ["supply_chain_disruption", "new_regulation"],
    },
    "fintech": {
        "industry": "Fintech",
        "market_dimensions": [
            "customer_trust",
            "regulatory_pressure",
            "adoption_rate",
            "competition_intensity",
            "platform_power",
            "margin_health",
        ],
        "action_dimensions": [
            "product_launch",
            "partnership",
            "security_investment",
            "acquisition",
            "repositioning",
        ],
        "actors": ["company", "customers", "regulators", "incumbent", "investors"],
        "objective": "customer_trust",
        "simulation_style": "regulated",
        "shock_events": ["new_regulation", "security_incident"],
    },
}


def preset_config(name: str, base: SimulationConfig | None = None) -> SimulationConfig:
    try:
        values = PRESETS[name]
    except KeyError as exc:
        choices = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset {name!r}. Available presets: {choices}") from exc
    return merge_config(base or SimulationConfig(), values, source=f"preset {name}")
