# Codex stage prompts — JEPA-Inspired Silicon Sandbox

Hand these to Codex **one at a time, in order**. Each file is self-contained
(it repeats the project context and the scope contract), so you can paste a single
file into a fresh Codex session. Commit after each stage before starting the next.

| Order | File | What it does |
| --- | --- | --- |
| 0 | `stage-00-baseline.md` | Pin deps, commit the existing skeleton as the baseline. |
| 1 | `stage-01-skeleton-DONE.md` | Already done — reference only, do not run. |
| 2 | `stage-02-dataset.md` | Numeric dataset + readable JSONL sidecar. |
| 3 | `stage-03-jepa-model.md` | Replace the autoencoder with a real JEPA model. **Correctness gate.** |
| 4 | `stage-04-train.md` | Train the JEPA model; emit standardized artifacts. |
| 5 | `stage-05-simulator.md` | Latent-model rounds + full per-round schema (MVP core). |
| 6 | `stage-06-report.md` | Market Vision report (JSON + Markdown). |
| 7 | `stage-07-diagnostics.md` | Three diagnostic plots. |
| 8 | `stage-08-openclaw.md` | TypeScript runner over the local Python engine. |
| 9 | `stage-09-readme.md` | GitHub-quality README. |

## Rules that apply to every stage
- Only modify the files each prompt lists under **Touch**; leave everything else
  alone. This is what keeps Codex from overshooting again.
- Commit after each stage (every prompt ends with its commit message).
- **Do not pass Stage 3** until the latent space does not collapse (effective rank
  stays well above 1). It is the foundation the rest of the product sits on.
- Locked design: numeric vector engine, genuinely JEPA-inspired model, all
  artifacts under `agent/artifacts/`, local-only, no LLM APIs.
