# Codex — Stage 4: Train the JEPA model + standardized artifacts

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Everything runs locally — no
OpenAI/Anthropic/LLM APIs. Allowed deps: PyTorch, NumPy, Matplotlib, and the
Python standard library.

**Locked decisions:**
- Numeric engine is canonical: state = 8-dim vector, action = 5-dim vector.
- The model is JEPA-inspired (Stage 3): stop-gradient targets + variance
  regularization + effective-rank metric already live in `agent/model.py`.
- All artifacts live under `agent/artifacts/`.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Call no external/LLM
API. When done, run the Verify command, then make a single commit with the given
message. If a needed change is out of scope, stop and report it instead.

## Current state
`agent/train.py` currently trains the old autoencoder with MSE and saves
`market_world_model.pt` + a history JSON. It must be updated to train the new
JEPA model from `agent/model.py` and to emit the canonical artifact set.

## Goal
`python -m agent.train` trains the JEPA model and writes standardized artifacts.

## Touch
- `agent/train.py` only.

## Do
- Load the numeric dataset (generate it if missing, via the existing helper).
- Train using `agent/model.py`'s JEPA `training_loss` (stop-gradient targets +
  variance regularization). Update the target encoder appropriately (EMA or copy).
- Track per-step `loss` and `effective_rank`.
- Save under `agent/artifacts/`:
  - `model.pt` — trained weights + config
  - `metrics.json` — per-step loss and effective_rank
  - `embeddings.npy` — encoded embeddings for the dataset (for diagnostics)
  - `feature_spec.json` — state/action feature names + any normalization (this is
    the numeric-path "vectorizer")
- Support optional `--json-progress` streaming logs, one JSON object per line,
  e.g. `{"type":"metric","step":10,"loss":0.42,"effective_rank":7.3}`.
- Use a reproducible seed and reasonable defaults. Clear console output.
- Fail gracefully with a helpful message if the dataset is missing.

## Out of scope
- Do not modify `model.py`, `simulation.py`, or `plot.py`.

## Verify
```
python -m agent.train --epochs 5
ls agent/artifacts/model.pt agent/artifacts/metrics.json agent/artifacts/embeddings.npy agent/artifacts/feature_spec.json
```

## Commit
```
feat(train): JEPA training with metrics, embeddings, feature spec
```
