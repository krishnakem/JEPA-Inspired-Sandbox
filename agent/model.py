"""Small JEPA-inspired latent market world model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import nn

from agent.data.generate import ACTION_FEATURES, STATE_FEATURES


@dataclass(frozen=True)
class ModelConfig:
    state_dim: int = len(STATE_FEATURES)
    action_dim: int = len(ACTION_FEATURES)
    latent_dim: int = 16
    hidden_dim: int = 64
    ema_decay: float = 0.98
    variance_floor: float = 0.35
    variance_weight: float = 0.08
    covariance_weight: float = 0.01
    readout_weight: float = 0.05


def _mlp(input_dim: int, hidden_dim: int, output_dim: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(input_dim, hidden_dim),
        nn.SiLU(),
        nn.Linear(hidden_dim, hidden_dim),
        nn.SiLU(),
        nn.Linear(hidden_dim, output_dim),
    )


class MarketWorldModel(nn.Module):
    """Predict future market representations in latent space."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()

        # state: [batch, state_dim] -> latent: [batch, latent_dim]
        self.encoder = nn.Sequential(
            _mlp(self.config.state_dim, self.config.hidden_dim, self.config.latent_dim),
            nn.LayerNorm(self.config.latent_dim),
        )
        self.target_encoder = nn.Sequential(
            _mlp(self.config.state_dim, self.config.hidden_dim, self.config.latent_dim),
            nn.LayerNorm(self.config.latent_dim),
        )
        self.predictor = _mlp(
            self.config.latent_dim + self.config.action_dim,
            self.config.hidden_dim,
            self.config.latent_dim,
        )
        self.readout = nn.Sequential(
            _mlp(self.config.latent_dim, self.config.hidden_dim, self.config.state_dim),
            nn.Sigmoid(),
        )

        self._copy_online_to_target()
        for parameter in self.target_encoder.parameters():
            parameter.requires_grad_(False)

    def _copy_online_to_target(self) -> None:
        self.target_encoder.load_state_dict(self.encoder.state_dict())

    @torch.no_grad()
    def update_target_encoder(self, decay: float | None = None) -> None:
        ema_decay = self.config.ema_decay if decay is None else decay
        for online, target in zip(self.encoder.parameters(), self.target_encoder.parameters()):
            target.data.mul_(ema_decay).add_(online.data, alpha=1.0 - ema_decay)

    def encode_state(self, state: torch.Tensor) -> torch.Tensor:
        return self.encoder(state)

    @torch.no_grad()
    def encode_target(self, next_state: torch.Tensor) -> torch.Tensor:
        return self.target_encoder(next_state).detach()

    def predict_latent(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        latent = self.encode_state(state)
        # concatenate latent state and action: [batch, latent_dim + action_dim]
        conditioned = torch.cat([latent, action], dim=-1)
        return self.predictor(conditioned)

    def decode_state(self, latent: torch.Tensor) -> torch.Tensor:
        return self.readout(latent)

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        predicted_latent = self.predict_latent(state, action)
        return self.decode_state(predicted_latent)

    @torch.no_grad()
    def predict_next(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        self.eval()
        return self(state, action)

    def training_loss(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
        next_state: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        predicted_latent = self.predict_latent(state, action)
        target_latent = self.encode_target(next_state)

        latent_loss = F.smooth_l1_loss(predicted_latent, target_latent)
        variance_loss = _variance_loss(predicted_latent, self.config.variance_floor)
        covariance_loss = _covariance_loss(predicted_latent)

        # Auxiliary display readout only; the latent prediction remains primary.
        decoded_next_state = self.decode_state(predicted_latent)
        readout_loss = F.mse_loss(decoded_next_state, next_state)

        total = (
            latent_loss
            + self.config.variance_weight * variance_loss
            + self.config.covariance_weight * covariance_loss
            + self.config.readout_weight * readout_loss
        )
        return {
            "loss": total,
            "latent_loss": latent_loss.detach(),
            "variance_loss": variance_loss.detach(),
            "covariance_loss": covariance_loss.detach(),
            "readout_loss": readout_loss.detach(),
            "effective_rank": effective_rank(predicted_latent).detach(),
        }


def _variance_loss(embeddings: torch.Tensor, floor: float) -> torch.Tensor:
    if embeddings.shape[0] < 2:
        return embeddings.new_tensor(0.0)
    std = torch.sqrt(embeddings.var(dim=0, unbiased=False) + 1e-4)
    return F.relu(floor - std).mean()


def _covariance_loss(embeddings: torch.Tensor) -> torch.Tensor:
    if embeddings.shape[0] < 2:
        return embeddings.new_tensor(0.0)
    centered = embeddings - embeddings.mean(dim=0, keepdim=True)
    covariance = centered.T @ centered / (embeddings.shape[0] - 1)
    off_diagonal = covariance - torch.diag(torch.diag(covariance))
    return off_diagonal.pow(2).sum() / embeddings.shape[1]


def effective_rank(embeddings: torch.Tensor) -> torch.Tensor:
    """Return entropy-based rank of a latent batch; low values flag collapse."""
    if embeddings.ndim != 2 or min(embeddings.shape) < 2:
        return embeddings.new_tensor(1.0)
    centered = embeddings - embeddings.mean(dim=0, keepdim=True)
    singular_values = torch.linalg.svdvals(centered)
    probabilities = singular_values / singular_values.sum().clamp_min(1e-12)
    entropy = -(probabilities * probabilities.clamp_min(1e-12).log()).sum()
    return entropy.exp()


def save_model(model: MarketWorldModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "config": asdict(model.config),
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


def _sanity_check() -> None:
    torch.manual_seed(7)
    model = MarketWorldModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-3)

    state = torch.rand(64, model.config.state_dim)
    action = torch.zeros(64, model.config.action_dim)
    action[torch.arange(64), torch.randint(0, model.config.action_dim, (64,))] = 1.0
    next_state = torch.clamp(
        state
        + 0.08 * torch.randn_like(state)
        + 0.05 * action[:, :1].expand(-1, model.config.state_dim),
        0.0,
        1.0,
    )

    losses: list[float] = []
    ranks: list[float] = []
    for _ in range(12):
        parts = model.training_loss(state, action, next_state)
        optimizer.zero_grad()
        parts["loss"].backward()
        optimizer.step()
        model.update_target_encoder()
        losses.append(float(parts["loss"].detach()))
        ranks.append(float(parts["effective_rank"]))

    final_rank = ranks[-1]
    if not torch.isfinite(torch.tensor(losses)).all():
        raise SystemExit("sanity check failed: non-finite loss")
    if losses[-1] >= losses[0]:
        raise SystemExit(f"sanity check failed: loss did not decrease {losses[0]:.4f}->{losses[-1]:.4f}")
    if final_rank <= 2.0:
        raise SystemExit(f"sanity check failed: effective rank collapsed to {final_rank:.2f}")
    print(
        "sanity ok "
        f"loss={losses[0]:.4f}->{losses[-1]:.4f} "
        f"effective_rank={final_rank:.2f}"
    )


if __name__ == "__main__":
    _sanity_check()
