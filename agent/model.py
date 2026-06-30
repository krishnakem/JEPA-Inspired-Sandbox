"""Small PyTorch market world model used by the standalone package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from agent.data.generate import ACTION_FEATURES, STATE_FEATURES


@dataclass(frozen=True)
class ModelConfig:
    state_dim: int = len(STATE_FEATURES)
    action_dim: int = len(ACTION_FEATURES)
    latent_dim: int = 16
    hidden_dim: int = 32


class MarketWorldModel(nn.Module):
    """Encode a market state, apply an action, and predict the next state."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()

        self.encoder = nn.Sequential(
            nn.Linear(self.config.state_dim, self.config.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.config.hidden_dim, self.config.latent_dim),
            nn.ReLU(),
        )
        self.transition = nn.Sequential(
            nn.Linear(self.config.latent_dim + self.config.action_dim, self.config.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.config.hidden_dim, self.config.latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(self.config.latent_dim, self.config.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.config.hidden_dim, self.config.state_dim),
            nn.Sigmoid(),
        )

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(state)
        conditioned = torch.cat([latent, action], dim=-1)
        next_latent = self.transition(conditioned)
        return self.decoder(next_latent)

    @torch.no_grad()
    def predict_next(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        self.eval()
        return self(state, action)


def save_model(model: MarketWorldModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "config": model.config.__dict__,
            "state_features": STATE_FEATURES,
            "action_features": ACTION_FEATURES,
        },
        path,
    )


def load_model(path: Path, device: str = "cpu") -> MarketWorldModel:
    checkpoint = torch.load(path, map_location=device)
    model = MarketWorldModel(ModelConfig(**checkpoint["config"]))
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device)
    model.eval()
    return model
