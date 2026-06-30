# JEPA-Inspired Silicon Sandbox

JEPA-Inspired Silicon Sandbox is an OpenClaw plugin for local market vision
forecasting. The user describes a market, a company type, a strategic action,
and a number of simulation rounds. The plugin then simulates how that market
could evolve round by round after the action, ending with a structured final
market vision.

This is not primarily a machine learning demo. The product goal is a portfolio
quality forecasting MVP for exploring strategic market futures. The
JEPA-inspired architecture is the implementation technique used to keep the
simulation modular, inspectable, and repeatable.

## Product Goal

The MVP should answer questions like:

```text
If a mid-market B2B SaaS company enters the AI sales-assistant market by
launching an open ecosystem strategy, what might the market look like after
six competitive response cycles?
```

The intended user input is:

| Input | Meaning |
| --- | --- |
| `current_market` | The market as it exists now, including players, demand, constraints, and trends. |
| `company_type` | The kind of company making the move, such as startup, incumbent, platform, or niche vendor. |
| `strategic_action` | The action to simulate, such as price cut, partnership, product launch, acquisition, or repositioning. |
| `simulation_rounds` | How many market evolution rounds to run. |

The intended output is:

- a round-by-round market evolution trace
- an internal representation of the market state at each round
- predicted changes in competitors, customers, pricing, positioning, and risk
- a final market vision summary
- local artifacts that can be inspected after the run

## Core Loop

```text
Current Market State
-> Internal Market Representation
-> Strategic Action
-> Predicted Future Market Representation
-> Repeat
-> Final Market Vision
```

OpenClaw owns the user-facing orchestration:

- session lifecycle
- tool registration
- progress events
- cancellation
- status polling
- artifact paths

Python will own the market model:

- parsing market inputs into a latent representation
- applying strategic actions
- evolving the representation over multiple rounds
- producing structured forecasts
- writing simulation artifacts

TypeScript should remain the OpenClaw boundary. Python should contain the
forecasting logic so the market model can stay easy to test and iterate on.

## Local-Only Constraint

Everything must run locally.

The project should not call OpenAI, Anthropic, hosted LLMs, or external model
APIs. Any intelligence in the MVP should come from deterministic simulation
logic, local algorithms, lightweight local models, or explicit rules that live
in this repository.

That constraint is part of the product: a user should be able to install the
plugin, run a simulation, inspect the generated artifacts, and understand how
the forecast was produced.

## Planned Tool Surface

The current repository still contains the reusable OpenClaw agent scaffold. As
the project becomes the Silicon Sandbox, the primary run tool should move from
template parameters to market forecasting parameters.

Planned canonical flow:

```text
start_session
-> run_market_simulation
-> get_session_status
-> end_session
```

Planned `run_market_simulation` input:

```json
{
  "session_id": "session returned by start_session",
  "current_market": "Description of the current market",
  "company_type": "Type of company taking action",
  "strategic_action": "Strategic move to simulate",
  "simulation_rounds": 6
}
```

The existing lifecycle tools should remain useful:

| Tool | Purpose |
| --- | --- |
| `start_session` | Create a local simulation session and return a `session_id`. |
| `run_market_simulation` | Start the market forecast in the background. |
| `get_session_status` | Poll progress, recent events, result, errors, and artifact paths. |
| `stop_run` | Cancel an in-flight simulation cooperatively. |
| `reset_all` | Clear local scratch and output data after confirmation. |
| `end_session` | Abort active work and forget the session. |

## Intended Architecture

```text
src/plugin/
  index.ts
    OpenClaw register(api), tool schemas, session orchestration

src/core/
  AgentSession.ts
    Session id, scratch/output directories, event stream, abort signal

src/main/
  MarketSimulationRunner.ts
    TypeScript runner that launches local Python simulation code

python/
  silicon_sandbox/
    market_state.py
      Market representation and validation
    actions.py
      Strategic action modeling
    simulator.py
      Multi-round market evolution loop
    artifacts.py
      Markdown and JSON artifact writing
```

The JEPA-inspired shape should stay understandable:

- encode the current market into an internal representation
- condition on the strategic action
- predict a future representation
- compare and carry forward the representation
- repeat for the requested number of rounds
- decode the final representation into a market vision

## Current Repository State

This repo currently starts from an OpenClaw long-running agent plugin template.
It already has useful infrastructure:

- TypeScript plugin registration
- background run lifecycle
- event buffering
- status polling
- cooperative cancellation
- local output artifacts
- local smoke test

The next implementation step is to replace the template runner with the market
simulation runner and add the Python model package.

## Development

Install dependencies:

```bash
npm install
```

Run local checks:

```bash
npm run typecheck
npm run lint
npm run test:plugin
```

The current smoke test imports the plugin, registers tools against a fake
OpenClaw API, starts a session, runs the template agent, polls for completion,
and ends the session. It should be updated as soon as the market simulation
tool replaces the template runner.

## OpenClaw Install

Install this repo as a linked plugin from your OpenClaw environment:

```bash
openclaw plugins install /absolute/path/to/this/repo --link
```

Restart the OpenClaw gateway after source edits. Linked plugins are picked up on
gateway boot; they are not hot-reloaded while the gateway is running.
