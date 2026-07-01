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
- An artifact-producing local workspace for reports, metrics, embeddings, and
  plots.
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
    marketsim_run_market_simulation, status, cancellation, reset
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
python3 -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --objective developer_adoption \
  --industry AI \
  --simulation-rounds 4 \
  --level medium \
  --format markdown
```

## Installation

Install JavaScript dependencies:

```bash
npm install
```

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
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
python3 -m agent.data.generate --samples 200
```

Train the JEPA-inspired model:

```bash
python3 -m agent.train --epochs 5
```

Run a market simulation and write a report:

```bash
python3 -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --objective developer_adoption \
  --industry AI \
  --simulation-rounds 4 \
  --level medium \
  --format markdown
```

Run with a different intensity:

```bash
python3 -m agent.simulation \
  --current-market "AI coding assistants are growing quickly..." \
  --company-type startup \
  --strategic-action "launch a free coding agent" \
  --objective developer_adoption \
  --industry AI \
  --rounds 5 \
  --level hard \
  --format markdown
```

The supported levels are `light`, `medium`, and `hard`. They map to the existing
simulation styles `conservative`, `base_case`, and `aggressive`.

Generate diagnostics:

```bash
python3 -m agent.plot
```

## OpenClaw usage

Install this repo as a linked OpenClaw plugin:

```bash
openclaw plugins install /absolute/path/to/JEPA-Inspired-Sandbox --link
```

This is a host-only plugin. `marketsim_run_market_simulation` launches the
local `python3` runtime from this checkout, so the host running the OpenClaw
gateway needs the Python dependencies and trained model artifact in place:

```bash
python3 -m pip install -r requirements.txt
test -f agent/artifacts/model.pt || {
  python3 -m agent.data.generate --samples 200
  python3 -m agent.train --epochs 5
}
```

The plugin tool flow is:

```text
marketsim_run_market_simulation
marketsim_get_session_status
marketsim_end_session
```

`marketsim_run_market_simulation` expects:

```json
{
  "current_market": "AI coding assistants are rapidly growing and competitive",
  "strategic_action": "launch a free coding agent",
  "company_type": "startup",
  "objective": "developer_adoption",
  "industry": "AI",
  "rounds": 4,
  "level": "medium"
}
```

`company_type` must be `startup`, `incumbent`, `platform`, or `niche vendor`.
`level` must be `light`, `medium`, or `hard`. The run tool creates a session,
returns its `session_id`, writes a temporary config JSON, launches
`python3 -m agent.simulation` locally, and returns immediately. Poll
`marketsim_get_session_status` with that `session_id` until `run_status` is
`completed`; the result includes the final Market Vision report path and
diagnostic plot paths when they are available. Call `marketsim_end_session` when
the user is done.

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
