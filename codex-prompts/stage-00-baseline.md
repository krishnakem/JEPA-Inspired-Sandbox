# Codex — Stage 0: Baseline + dependencies

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
- The model will be genuinely JEPA-inspired (later stage): online encoder, target
  encoder + stop-gradient, latent-space predictor, variance regularization,
  effective-rank metric; a decoder exists only as a display readout.
- All artifacts live under `agent/artifacts/`.
- Numeric-first dataset plus a readable JSONL sidecar.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Call no external/LLM
API. When done, run the Verify command, then make a single commit with the given
message. If a needed change is out of scope, stop and report it instead.

## Goal
Freeze the existing Stage-1 skeleton and pin dependencies so later stages have a
clean, reproducible base.

## Touch
- `requirements.txt` (new)
- `pyproject.toml` (optional, only if trivial)
- repo (commit the currently-untracked `agent/` package as-is)

## Do
- Create `requirements.txt` pinning `torch`, `numpy`, `matplotlib`.
- Do not change any code in `agent/`.

## Out of scope
- No changes to model, data, training, simulation, plotting, or TypeScript.

## Verify
```
python -c "import agent, agent.data.generate, agent.simulation, agent.model, agent.train, agent.plot"
```

## Commit
```
chore: freeze stage-1 skeleton and pin python deps
```
