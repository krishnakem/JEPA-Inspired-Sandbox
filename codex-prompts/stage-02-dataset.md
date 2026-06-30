# Codex — Stage 2: Dataset (numeric core + readable JSONL sidecar)

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Core loop: Current Market → latent
representation → strategic action → predicted future representation → repeat →
Final Market Vision. Everything runs locally — no OpenAI/Anthropic/LLM APIs.
TypeScript orchestrates (OpenClaw); Python owns the model and simulation.
Allowed deps: PyTorch, NumPy, Matplotlib, and the Python standard library.

**Locked decisions:**
- Numeric engine is canonical: state = 8-dim vector, action = 5-dim vector. Text
  is only a thin input/output adapter.
- All artifacts live under `agent/artifacts/`.
- Numeric-first dataset plus a readable JSONL sidecar (this stage).

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Call no external/LLM
API. When done, run the Verify command, then make a single commit with the given
message. If a needed change is out of scope, stop and report it instead.

## Current state
`agent/data/generate.py` already produces a compressed numeric dataset
(`states`, `actions`, `next_states`) as `.npz` plus a `.json` metadata file using
a fixed seed. The feature schemas `STATE_FEATURES` (8) and `ACTION_FEATURES` (5)
already exist there. It does **not** yet emit human-readable JSONL, industries, or
transition types.

## Goal
Keep the numeric dataset as the training source, and additionally emit a
human-readable JSONL view of the same data so the dataset is inspectable and
portfolio-ready.

## Touch
- `agent/data/generate.py` only.

## Do
- Keep the existing numeric `.npz` output unchanged as the training source.
- Additionally write `agent/artifacts/data/market_transitions.jsonl`, one JSON
  object per line, each containing:
  - `current_market_state` — readable string rendered from the state vector
  - `company_action` — readable string rendered from the action vector
  - `future_market_state` — readable string rendered from the next-state vector
  - `industry` — one of: AI, SaaS, Consumer Technology, Retail, Manufacturing
  - `transition_type` — one of: product launch, price cut, open-source release,
    enterprise expansion, regulatory pressure, competitor response, customer
    adoption shift, supply chain improvement
  - `metadata` — at least `{ seed, state_vector, action_vector, next_state_vector }`
- Keep generation deterministic with a fixed seed.
- Set the default sample count to `--samples 200` (allow override).
- Render readable strings deterministically from the numeric vectors (e.g.
  describe the strongest/weakest features); do not invent free text via any API.

## Out of scope
- Do not change `model.py`, `train.py`, `simulation.py`, or `plot.py`.

## Verify
```
python -m agent.data.generate --samples 200
head -n 5 agent/artifacts/data/market_transitions.jsonl
```
Confirm 5 readable, well-formed JSONL lines with all required fields.

## Commit
```
feat(data): numeric dataset + readable JSONL sidecar
```
