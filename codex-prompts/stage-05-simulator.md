# Codex — Stage 5: Multi-round market simulator (MVP centerpiece)

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Core loop: Current Market → latent
representation → strategic action → predicted future representation → repeat →
Final Market Vision. Everything runs locally — no OpenAI/Anthropic/LLM APIs.
Allowed deps: PyTorch, NumPy, Matplotlib, and the Python standard library.

**Locked decisions:**
- Numeric engine is canonical: state = 8-dim vector, action = 5-dim vector. Text
  is only a thin input/output adapter (keyword-encode in, templated language out).
- The trained JEPA model drives the rounds; rule-based dynamics are the fallback.
- All artifacts live under `agent/artifacts/`.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Call no external/LLM
API. When done, run the Verify command, then make a single commit with the given
message. If a needed change is out of scope, stop and report it instead.

## Current state
`agent/simulation.py` already runs a multi-round loop (rule-based, with an
optional model path) and writes JSON + Markdown. It is missing the full per-round
schema (actor / reaction / confidence) and should use the JEPA model's
latent rollout when a trained model is available.

## Goal
Drive the round loop with the trained latent model and complete the per-round
output schema, keeping the rule-based fallback.

## Touch
- `agent/simulation.py` only.

## Do
- Inputs: `current_market`, `company_type`/`company_profile`, `strategic_action`/
  `initial_action`, `rounds`.
- When `agent/artifacts/model.pt` exists: encode the initial market to a latent,
  then roll forward in **latent space** via the model's `predict_latent`, and use
  `decode_state` to produce a readable state each round.
- When no model exists: keep the existing deterministic rule-based evolution.
- Each round must include: `round`, `actor`, `action_or_reaction`,
  `predicted_market_shift`, `updated_market_state`, `confidence` (a diagnostic
  score). Round roles cycle: company acts → competitors respond → customers react
  → investors/regulators respond.
- Output structured JSON. Keep user-facing language about markets, not ML
  internals.
- Keep the CLI working:
  `python -m agent.simulation --current-market "..." --company-type "..." --strategic-action "..." --simulation-rounds 4`

## Out of scope
- Report formatting (Stage 6) and diagnostic plots (Stage 7). Do not modify
  `model.py`, `train.py`, or `plot.py`.

## Verify
```
python -m agent.simulation --current-market "AI coding assistants are rapidly growing and competitive" --company-type startup --strategic-action "launch a free coding agent" --simulation-rounds 4
```
Confirm each round shows actor, action_or_reaction, predicted_market_shift,
updated_market_state, and confidence.

## Commit
```
feat(sim): latent-model rounds with full per-round schema
```
