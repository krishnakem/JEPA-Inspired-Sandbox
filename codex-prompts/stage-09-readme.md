# Codex — Stage 9: Documentation (README)

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Everything runs locally — no
OpenAI/Anthropic/LLM APIs. TypeScript orchestrates; Python owns the model and
simulation.

**Scope contract:** Only modify the files under "Touch". Do not refactor code.
Call no external/LLM API. When done, run the Verify check, then make a single
commit with the given message.

## Goal
A clear, GitHub-quality README explaining both the product vision and the
technical architecture.

## Touch
- `README.md`.

## Do
- Title: **JEPA-Inspired Silicon Sandbox**. Subtitle: "A JEPA-inspired OpenClaw
  plugin exploring latent world models for multi-round strategic market
  forecasting."
- Sections: Vision; What this project is; What this project is not; Why latent
  world models; Why JEPA-inspired; Architecture; Example simulation; Installation;
  Standalone Python usage; OpenClaw usage; Generated artifacts; Future roadmap.
- Framing: market-vision forecasting MVP; **not** financial advice; **not** a full
  reproduction of Meta JEPA; runs locally; no OpenAI/Anthropic APIs; the Python
  model maintains the latent world state; OpenClaw orchestrates the experience.
- Reconcile any stale references (e.g. an older `python/silicon_sandbox/` path)
  to the actual `agent/` package and `agent/artifacts/` layout.
- Document the real CLIs: `python -m agent.data.generate`, `python -m agent.train`,
  `python -m agent.simulation`, `python -m agent.plot`.

## Out of scope
- No code changes outside README.

## Verify
Re-read the README against a clean checkout: the install and usage steps should be
runnable as written.

## Commit
```
docs: comprehensive Silicon Sandbox README
```
