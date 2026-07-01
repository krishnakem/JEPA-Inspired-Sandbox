# JEPA-Inspired Silicon Sandbox

A JEPA-inspired OpenClaw plugin exploring latent world models for multi-round
strategic market forecasting.

## Vision

JEPA-Inspired Silicon Sandbox is a local market-vision forecasting MVP. A user
describes a current market, a company profile, a strategic action, and a number
of rounds. The system rolls the market forward through company action,
competitor response, customer reaction, and investor/regulator pressure, then
returns a structured Market Vision report.

The goal is not to predict public-market returns. This is not financial advice.
It is a portfolio project for exploring how latent world models can support
repeatable strategic scenario planning.

## What this project is

- A local OpenClaw plugin for market scenario simulation.
- A configurable numeric vector engine with default 8-dimension market state and
  5-dimension action vectors.
- A Python-owned JEPA-inspired latent world model.
- A deterministic report generator using templates, not hosted LLM prose.
- An artifact-producing sandbox for reports, metrics, embeddings, and plots.
- A local-only system with no OpenAI, Anthropic, or hosted model API calls.

## What this project is not

- Not financial advice or an investment recommendation engine.
- Not a full reproduction of Meta JEPA.
- Not an LLM wrapper.
- Not a hosted API product.
- Not a claim that synthetic market dynamics are real market truth.

## Why latent world models

Multi-round strategy is naturally stateful. A market move changes demand,
competition, trust, pricing pressure, regulation, margins, and adoption. The
next round should start from that changed world, not from the original prompt.

This project keeps that world state in numeric latent form. Text is only the
input/output adapter: keyword encoding on the way in, deterministic templates on
the way out.

## Why JEPA-inspired

The model predicts future latent representations rather than reconstructing raw
market vectors as its main objective. The implementation includes:

- online encoder for current market state
- target encoder with stop-gradient targets
- action-conditioned latent predictor
- variance and covariance collapse guards
- effective-rank diagnostics
- readout decoder used only to display state vectors

That is JEPA-inspired, but intentionally small and local.

## Architecture

```text
OpenClaw / TypeScript
  src/plugin/index.ts
    start_session, run_market_simulation, status, cancellation, reset
  src/main/JepaInspiredSiliconSandboxRunner.ts
    spawns the local Python simulator and streams progress events

Python engine
  agent/data/generate.py
    numeric dataset and readable JSONL sidecar
  agent/model.py
    JEPA-inspired latent predictor
  agent/train.py
    training loop and standardized artifacts
  agent/simulation.py
    multi-round market rollout
  agent/report.py
    deterministic JSON/Markdown Market Vision reports
  agent/plot.py
    developer diagnostics

Artifacts
  agent/artifacts/
```

Python owns the model and simulation. TypeScript only orchestrates the local
process for OpenClaw.

## Example simulation

```bash
python -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --simulation-rounds 4 \
  --format markdown
```

If your system does not provide a `python` alias, use `python3` for the same
commands.

## Installation

Install JavaScript dependencies:

```bash
npm install
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run checks:

```bash
npm run typecheck
npm run lint
npm run test:plugin
```

## Standalone Python usage

Generate the numeric dataset and readable JSONL sidecar:

```bash
python -m agent.data.generate --samples 200
```

Train the JEPA-inspired model:

```bash
python -m agent.train --epochs 5
```

Run a market simulation and write a report:

```bash
python -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --simulation-rounds 4 \
  --format markdown
```

Run with a built-in preset and configurable simulation fields:

```bash
python -m agent.simulation \
  --preset ai_startup \
  --current-market "AI coding assistants are growing quickly..." \
  --company-profile "open-source startup" \
  --strategic-action "launch a free coding agent" \
  --rounds 5 \
  --simulation-style aggressive \
  --actors startup,incumbent,developers,enterprise_buyers,investors \
  --shock-events incumbent_price_war,open_source_breakthrough \
  --objective developer_adoption \
  --report-format founder_memo
```

Load a JSON config file:

```bash
python -m agent.simulation \
  --config examples/configs/ai_startup.json \
  --current-market "AI coding assistants are growing quickly..." \
  --company-profile "open-source startup" \
  --strategic-action "launch a free coding agent"
```

Built-in presets are `ai_startup`, `saas_enterprise`, `consumer_tech`, `retail`,
`manufacturing`, and `fintech`. Config priority is base defaults, then preset,
then config file, then CLI flags.

Generate diagnostics:

```bash
python -m agent.plot
```

## OpenClaw usage

Install this repo as a linked OpenClaw plugin:

```bash
openclaw plugins install /absolute/path/to/JEPA-Inspired-Sandbox --link
```

Canonical tool flow:

```text
start_session
run_market_simulation
get_session_status
end_session
```

`run_market_simulation` expects:

```json
{
  "session_id": "session returned by start_session",
  "current_market": "AI coding assistants are rapidly growing and competitive",
  "company_type": "startup",
  "strategic_action": "launch a free coding agent",
  "simulation_rounds": 4
}
```

Optional fields include `company_profile`, `preset`, `rounds`,
`simulation_style`, `actors`, `market_dimensions`, `action_dimensions`,
`shock_events`, `objective`, and `report_format`. The runner writes a temporary
config JSON, launches `python -m agent.simulation` locally, and returns the final
Market Vision report path. It also includes diagnostic plot paths when they are
available.

### Run on OpenClaw's shipped Python

For sandbox deployments, build a custom OpenClaw sandbox image that starts from
OpenClaw's shipped `python3` base and bakes in this repo's `requirements.txt`.
Then merge the sandbox config snippet from [deploy/](deploy/) into the
operator's `openclaw.json`.

The sandbox path keeps `network: "none"` and trains `agent/artifacts/model.pt`
with `setupCommand` when the container is first created. The existing
`run_market_simulation` TypeScript runner still uses the host-spawn path in this
stage.

## Generated artifacts

All Python artifacts live under `agent/artifacts/`.

```text
agent/artifacts/data/market_transitions.npz
agent/artifacts/data/market_transitions.json
agent/artifacts/data/market_transitions.jsonl
agent/artifacts/model.pt
agent/artifacts/metrics.json
agent/artifacts/embeddings.npy
agent/artifacts/feature_spec.json
agent/artifacts/simulations/market-vision-*.md
agent/artifacts/simulations/market-vision-*.json
agent/artifacts/plots/latent_trajectory.png
agent/artifacts/plots/effective_rank.png
agent/artifacts/plots/collapse_comparison.png
```

## Future roadmap

- Add richer deterministic text adapters for market descriptions.
- Expand the synthetic transition generator with more industry-specific regimes.
- Add validation sets and stronger collapse/robustness gates.
- Improve OpenClaw progress events if the Python simulator gains JSON progress.
- Add richer report comparisons across multiple strategic actions.
- Package a small demo dataset and screenshots for portfolio presentation.
