# Codex — Stage 6: Market Vision report

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Everything runs locally — no
OpenAI/Anthropic/LLM APIs. Allowed deps: PyTorch, NumPy, Matplotlib, and the
Python standard library.

**Locked decisions:**
- Numeric engine is canonical; text is only an output adapter (deterministic
  templates, no API-generated prose).
- All artifacts live under `agent/artifacts/`.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite any other module. Preserve public function signatures of modules you
are not assigned. Add no dependencies beyond those listed. Call no external/LLM
API. When done, run the Verify command, then make a single commit with the given
message. If a needed change is out of scope, stop and report it instead.

## Goal
Turn a simulation result into a portfolio-quality Market Vision report, in both
JSON and Markdown, using deterministic templates.

## Touch
- New module `agent/report.py`.
- `agent/simulation.py` — only to call the report module and pass a `--format`
  option through. Do not change its simulation logic.

## Do
- In `agent/report.py`, build a report from a simulation result dict with these
  sections: Summary, Major Strategic Changes, Competitive Landscape, Likely
  Winners, Likely Risks, Emerging Opportunities, Round-by-Round Evolution, Final
  Market State.
- Summarize the final simulated market state and the trajectory — do not just
  dump raw round logs.
- Support both JSON and Markdown output, selected via `--format {json,markdown}`
  on the simulation CLI (default markdown for human runs).
- All language is template-driven and deterministic. No external/LLM APIs.

## Out of scope
- Do not modify `model.py`, `train.py`, or `plot.py`. Do not change simulation
  dynamics.

## Verify
```
python -m agent.simulation --current-market "..." --company-type startup --strategic-action "launch a free coding agent" --simulation-rounds 4 --format markdown
```
Confirm a readable report with all eight sections is written.

## Commit
```
feat(report): structured Market Vision (JSON + Markdown)
```
