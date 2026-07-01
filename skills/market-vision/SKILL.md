---
name: market-vision
description: Run JEPA-Inspired Silicon Sandbox market-vision simulations through OpenClaw's sandbox Python. Trigger for sandboxed market simulations, strategic scenario reports, or when the user wants the canonical OpenClaw run path.
---

# Market Vision Sandbox Run

Use this skill as the canonical OpenClaw run path for JEPA-Inspired Silicon
Sandbox. It runs the Python engine through OpenClaw's sandboxed `exec` tool,
which resolves to the Stage 10 sandbox image and uses the shipped `python3`.
No host Python is required.

Required inputs:

- current market
- strategic action
- company type
- objective
- industry
- number of rounds
- level

## Preconditions

Confirm the active OpenClaw session is sandboxed and this repo is mounted at
`/workspace`, as configured by `deploy/openclaw.sandbox.json5`.

The sandbox image must be `openclaw-sandbox-jepa:bookworm-slim`, with
dependencies baked in and `network: "none"` still set.

## Prepare Model If Needed

If `/workspace/agent/artifacts/model.pt` is absent, run the Stage 10 prep once
through the sandboxed `exec` tool:

```bash
cd /workspace && python3 -m agent.data.generate --samples 200 && python3 -m agent.train --epochs 5
```

This works offline because the image already includes the dependencies from
`requirements.txt`.

## Run Simulation

Run the engine through the sandboxed `exec` tool:

```bash
cd /workspace && python3 -m agent.simulation \
  --current-market "<CURRENT_MARKET>" \
  --strategic-action "<STRATEGIC_ACTION>" \
  --company-type "<COMPANY_TYPE>" \
  --objective "<OBJECTIVE>" \
  --industry "<INDUSTRY>" \
  --simulation-rounds <N> \
  --level "<LEVEL>" \
  --format markdown
```

## Present Report

Read back the newest Markdown report from:

```text
/workspace/agent/artifacts/simulations/*.md
```

Present the report summary and the report path to the user. If no report was
written, show the sandbox command output and the failing condition.
