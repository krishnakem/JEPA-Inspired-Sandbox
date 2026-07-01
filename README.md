# JEPA Silicon Sandbox

**Let a small business war-game a strategic move before making it — and watch a learned world model roll the market forward round by round.**

```bash
python3 -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --objective developer_adoption \
  --industry AI --level medium --format markdown
```

That single command trains-or-loads a JEPA-inspired latent world model, rolls the market through four rounds of **company action → competitor response → customer reaction → investor/regulator pressure**, and writes a structured Market Vision report to disk. No hosted LLM, no API keys, fully local.

---

## Why this exists

Small and mid-sized business owners make irreversible competitive moves — cut a price, launch a product, enter a segment — with no way to rehearse how the market will react. Big companies pay strategy consultants to build these scenarios by hand. Everyone else guesses.

Silicon Sandbox is my bet that a **learned world model** can do that rehearsal cheaply and repeatably. This repo is the JEPA branch of that bet: instead of asking an LLM to narrate a prediction, it keeps market state in numeric latent form and *predicts the next state* the way JEPA predicts future representations. Text is only the adapter — keyword encoding on the way in, deterministic templates on the way out.

> This is a research MVP and portfolio artifact, not financial advice and not a claim that synthetic dynamics equal real markets. It is a working demonstration that the world-model approach produces coherent, multi-round strategic scenarios.

---

## The ML, honestly

The model in [`agent/model.py`](agent/model.py) is a genuine (small, local) JEPA, not an LLM wrapper:

| Component | Implementation |
| --- | --- |
| **Online + target encoder** | Two MLP encoders; the target is an EMA copy (`ema_decay=0.98`) updated with no gradient |
| **Stop-gradient targets** | `encode_target()` runs under `torch.no_grad()` and `.detach()` — predictions chase a slow-moving target, not themselves |
| **Action-conditioned predictor** | Predicts the *next latent* from `[latent_state, action]`, so strategy is a first-class input |
| **Collapse guards** | VICReg-style variance floor + covariance penalty stop the encoder from mapping every market to the same point |
| **Effective-rank diagnostic** | Entropy of the latent singular-value spectrum; a live readout that flags representational collapse before it ruins a run |
| **Readout decoder** | Auxiliary only — used to *display* a latent as a human-readable state vector, never as the primary objective |

The whole thing has a built-in sanity check: `python3 -m agent.model` trains 12 steps and hard-fails if loss doesn't drop or effective rank collapses below 2.0. That guardrail is the point — representational collapse is the failure mode this project was built to demonstrate *and* defeat.

---

## Architecture

```text
OpenClaw (TypeScript harness)
  src/plugin/index.ts ............ registers marketsim_* tools
  src/main/JepaSiliconSandboxRunner.ts .. spawns local python3, streams round events

Python engine (owns all ML + simulation)
  agent/data/generate.py ......... synthetic market-transition dataset (+ readable JSONL)
  agent/model.py ................. JEPA-inspired latent world model
  agent/train.py ................. training loop, standardized artifacts
  agent/simulation.py ............ 4-round market rollout
  agent/report.py ................ deterministic Market Vision reports
  agent/plot.py .................. latent-trajectory & collapse diagnostics

agent/artifacts/ ................. model.pt, metrics.json, embeddings, reports, plots
```

TypeScript only orchestrates. Every prediction, every regularizer, every diagnostic lives in Python.

## How a run works

1. **Encode** the described market into a latent state vector.
2. **Roll forward** four rounds. Each round conditions the predictor on the round's action and advances the *latent* world state, so round N+1 starts from the changed world, not the original prompt.
3. **Read out** each round's latent for display and score the trajectory.
4. **Report** a structured Market Vision memo (summary, strategic changes, competitive landscape, winners, risks, opportunities, round-by-round evolution, final state).

## Quickstart

```bash
# Python 3.10+  (torch, numpy, matplotlib — see requirements.txt)
python3 -m pip install -r requirements.txt

# Generate data + train (one-time; writes agent/artifacts/model.pt)
python3 -m agent.data.generate --samples 200
python3 -m agent.train --epochs 5

# Run a simulation
python3 -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --objective developer_adoption \
  --industry AI --level medium --format markdown

# Diagnostics (latent trajectory, effective rank, collapse comparison)
python3 -m agent.plot
```

**Levels:** `light` / `medium` / `hard` (map to conservative / base-case / aggressive intensity). Every run is exactly four rounds.
**Company types:** `startup`, `incumbent`, `platform`, `niche vendor`.

## Running it as an OpenClaw tool

Silicon Sandbox runs inside [OpenClaw](https://openclaw.ai) as a host-only plugin so an agent can call it in natural language. Install linked:

```bash
openclaw plugins install /absolute/path/to/jepa-silicon-sandbox --link
```

Five tools are exposed; the common flow is `marketsim_run_market_simulation → marketsim_get_session_status → marketsim_end_session`. The run tool takes the same fields as the CLI:

```json
{
  "current_market": "AI coding assistants are rapidly growing and competitive",
  "strategic_action": "launch a free coding agent",
  "company_type": "startup",
  "objective": "developer_adoption",
  "industry": "AI",
  "level": "medium"
}
```

The host needs the Python deps and a trained `agent/artifacts/model.pt` in place before the plugin can run.

## Where this sits in the bigger project

Silicon Sandbox has two experimental branches exploring the same thesis:

- **This repo (JEPA branch)** — a learned latent world model. Strong on *representation* and multi-round state; deliberately not an LLM.
- **[SME_MVP](https://github.com/krishnakem/SME_MVP) (LLM branch)** — LLM agents with explicit cognitive profiles. Strong on *interpretable competitor reasoning*; weaker on learned dynamics.

The open research question is which representation better predicts real incumbent retaliation — a question I'm pursuing as a research assistant at the Ross School of Business.

## Roadmap

- Richer deterministic text adapters for market descriptions
- Industry-specific transition regimes in the synthetic generator
- Validation sets and stronger collapse/robustness gates
- Multi-action report comparisons (A/B a strategy)
- A packaged demo dataset + screenshots for portfolio review

## License

See repository. Research/portfolio use.