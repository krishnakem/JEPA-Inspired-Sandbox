# Codex — Stage 3: JEPA-inspired model (CORRECTNESS GATE)

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Core loop: Current Market → latent
representation → strategic action → predicted future representation → repeat →
Final Market Vision. Everything runs locally — no OpenAI/Anthropic/LLM APIs.
Allowed deps: PyTorch, NumPy, Matplotlib, and the Python standard library.

**Locked decisions:**
- Numeric engine is canonical: state = 8-dim vector, action = 5-dim vector.
- The model must be genuinely JEPA-inspired: online encoder, target encoder +
  stop-gradient, action-conditioned predictor operating in **latent space**,
  variance regularization, effective-rank metric. A decoder exists **only** as a
  display readout, never as the training objective.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Call no external/LLM
API. When done, run the Verify command, then make a single commit with the given
message. If a needed change is out of scope, stop and report it instead.

## Current state (important)
`agent/model.py` is currently a state-space **autoencoder** (encoder →
transition → decoder, trained with MSE on the raw next state). This is **not**
JEPA-inspired and must be replaced. The feature dims come from
`agent/data/generate.py` (`STATE_FEATURES` = 8, `ACTION_FEATURES` = 5).

## Goal
Replace `model.py` with a small but genuinely JEPA-inspired latent world model.

## Touch
- `agent/model.py` only.

## Do
Implement, keeping tensors small and shapes clearly commented:
- `encoder` — online encoder mapping state vector → latent embedding.
- `target_encoder` — a stop-gradient/EMA copy of the encoder used to produce
  prediction targets. Targets must not receive gradients.
- `predictor` — maps (latent, action) → **predicted next latent**.
- `readout` (decoder) — maps latent → state vector, used **only** for display.
- Helper functions: `encode_state`, `encode_target` (no grad), `predict_latent`,
  `decode_state`, `training_loss`, `effective_rank`.
- `training_loss` = latent prediction loss (predicted next latent vs.
  stop-gradient target latent) + variance regularization (optionally a covariance
  term). The readout may add a small, clearly-separated auxiliary reconstruction
  term so display stays meaningful — but the primary objective is latent
  prediction, not state-space MSE.
- `effective_rank` computes the effective rank of a batch of embeddings (e.g. via
  the entropy of normalized singular values) as a collapse diagnostic.
- Keep `save_model` / `load_model` working (update them to the new module).

## Out of scope
- Do not modify `train.py` beyond what an import signature requires; do not run
  training in this stage.
- Do not touch data, simulation, or plotting.

## Verify
Add a tiny inline sanity check (script or `if __name__ == "__main__"`): build the
model, run a random batch, confirm `training_loss` is finite and decreases on a
few manual steps, and confirm `effective_rank` returns a value clearly > 1.

## Commit
```
feat(model): JEPA-inspired latent predictor with collapse guards
```

## GATE
This is the project's correctness gate. Do not proceed to Stage 4 unless the
latent space shows no obvious collapse (effective rank stays well above 1). If it
collapses, fix this stage first.
