# Codex — Stage 7: Developer diagnostics (plots)

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Everything runs locally — no
OpenAI/Anthropic/LLM APIs. Allowed deps: PyTorch, NumPy, Matplotlib, and the
Python standard library.

**Locked decisions:**
- Numeric engine is canonical.
- All artifacts live under `agent/artifacts/`. Plots go in
  `agent/artifacts/plots/`.
- These plots are developer diagnostics, not the product surface.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Matplotlib only — no
seaborn. Call no external/LLM API. When done, run the Verify command, then make a
single commit with the given message. If a needed change is out of scope, stop
and report it instead.

## Current state
`agent/plot.py` currently plots training loss and a simulation trace. It should
instead (or additionally) produce the three named diagnostic figures below from
the saved artifacts.

## Goal
Generate the three diagnostic PNGs from saved embeddings/metrics.

## Touch
- `agent/plot.py` only.

## Do
- Read from `agent/artifacts/`: `embeddings.npy`, `metrics.json`, and a simulation
  trace JSON if available.
- Produce:
  - `agent/artifacts/plots/latent_trajectory.png` — latent-space trajectory
    (e.g. 2D projection of embeddings / rollout).
  - `agent/artifacts/plots/effective_rank.png` — effective rank over training steps.
  - `agent/artifacts/plots/collapse_comparison.png` — healthy vs. collapsed
    comparison.
- Matplotlib only, no seaborn. Handle missing artifacts with a helpful error
  message rather than a stack trace.
- Keep `python -m agent.plot` working as the entry point.

## Out of scope
- Do not modify `model.py`, `train.py`, `simulation.py`, or `report.py`.

## Verify
```
python -m agent.plot
ls agent/artifacts/plots/latent_trajectory.png agent/artifacts/plots/effective_rank.png agent/artifacts/plots/collapse_comparison.png
```

## Commit
```
feat(plot): latent trajectory, effective-rank, collapse diagnostics
```
