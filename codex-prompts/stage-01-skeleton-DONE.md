# Codex — Stage 1: Package skeleton

## Status: DONE — do not run this as a prompt.

The standalone `agent/` package already exists and its CLIs import and run
(`agent.data.generate`, `agent.train`, `agent.simulation`, `agent.plot`). No
action is required for Stage 1. Treat the Stage 0 commit as the Stage 1 baseline
and proceed to Stage 2.

If you are re-creating the repo from scratch, the skeleton requirement was:
`agent/` with `__init__.py`, `model.py`, `train.py`, `plot.py`, `simulation.py`,
and `data/{__init__.py, generate.py}`; runnable via `python -m agent.<module>`;
local deps only (PyTorch, NumPy, Matplotlib, stdlib); no OpenClaw dependency yet.
