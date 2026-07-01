"""Simulation configuration loading and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any


ROUNDS = 4
HORIZON = ROUNDS

DEFAULT_MARKET_DIMENSIONS = [
    "demand_growth",
    "price_pressure",
    "competition_intensity",
    "customer_trust",
    "platform_power",
    "regulatory_pressure",
    "margin_health",
    "adoption_rate",
]

DEFAULT_ACTION_DIMENSIONS = [
    "product_launch",
    "price_cut",
    "partnership",
    "acquisition",
    "repositioning",
]

DEFAULT_ACTORS = [
    "company",
    "competitors",
    "customers",
    "investors",
]

SIMULATION_STYLES = {
    "conservative",
    "base_case",
    "aggressive",
    "chaotic",
    "winner_take_all",
    "regulated",
    "capital_constrained",
}

LEVEL_TO_STYLE = {
    "light": "conservative",
    "medium": "base_case",
    "hard": "aggressive",
}

REPORT_FORMATS = {
    "strategy_memo",
    "founder_memo",
    "investor_memo",
    "board_update",
    "risk_report",
    "product_brief",
}

CONFIG_FIELDS = {
    "market_dimensions",
    "action_dimensions",
    "actors",
    "industry",
    "simulation_style",
    "objective",
    "report_format",
}

_DIMENSION_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class SimulationConfig:
    market_dimensions: list[str] = field(default_factory=lambda: list(DEFAULT_MARKET_DIMENSIONS))
    action_dimensions: list[str] = field(default_factory=lambda: list(DEFAULT_ACTION_DIMENSIONS))
    actors: list[str] = field(default_factory=lambda: list(DEFAULT_ACTORS))
    industry: str = "AI"
    rounds: int = ROUNDS
    simulation_style: str = "base_case"
    objective: str = "market_share"
    report_format: str = "strategy_memo"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_csv_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items


def merge_config(base: SimulationConfig, overrides: dict[str, Any], source: str) -> SimulationConfig:
    unknown = sorted(set(overrides) - CONFIG_FIELDS)
    if unknown:
        raise ValueError(f"{source} contains unsupported config fields: {', '.join(unknown)}")

    data = base.to_dict()
    for key, value in overrides.items():
        if value is not None:
            data[key] = value
    config = SimulationConfig(**data)
    validate_config(config)
    return config


def load_config_file(path: Path, base: SimulationConfig | None = None) -> SimulationConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config file {path} is not valid JSON: {exc.msg}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Config file {path} must contain a JSON object")
    return merge_config(base or SimulationConfig(), raw, source=f"config file {path}")


def validate_config(config: SimulationConfig) -> None:
    _validate_string_list(config.market_dimensions, "market_dimensions", require_dimensions=True)
    _validate_string_list(config.action_dimensions, "action_dimensions", require_dimensions=True)
    _validate_string_list(config.actors, "actors")
    if config.rounds != ROUNDS:
        raise ValueError(f"rounds is fixed at {ROUNDS}")
    if not config.industry.strip():
        raise ValueError("industry must not be empty")
    if config.simulation_style not in SIMULATION_STYLES:
        choices = ", ".join(sorted(SIMULATION_STYLES))
        raise ValueError(f"simulation_style must be one of: {choices}")
    if config.report_format not in REPORT_FORMATS:
        choices = ", ".join(sorted(REPORT_FORMATS))
        raise ValueError(f"report_format must be one of: {choices}")
    if not config.objective.strip():
        raise ValueError("objective must not be empty")


def _validate_string_list(
    values: list[str],
    field_name: str,
    require_dimensions: bool = False,
    allow_empty: bool = False,
) -> None:
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    if not values and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")

    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings")
        if value in seen:
            raise ValueError(f"{field_name} contains duplicate entry: {value}")
        seen.add(value)
        if require_dimensions and not _DIMENSION_RE.match(value):
            raise ValueError(
                f"{field_name} entry {value!r} must use lower_snake_case names"
            )
