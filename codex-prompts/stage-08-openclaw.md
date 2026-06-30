# Codex — Stage 8: OpenClaw integration

## Context (read first)
You are working on an OpenClaw plugin, **JEPA-Inspired Silicon Sandbox**. The
product is a **local market-vision forecasting MVP**; the JEPA-inspired latent
model is the engine, not the product. Everything runs locally — no
OpenAI/Anthropic/LLM APIs. **TypeScript orchestrates; Python owns the model and
simulation.** Do not port any ML logic into TypeScript.

**Scope contract:** Only modify the files under "Touch". Do not refactor, rename,
or rewrite unrelated modules. Preserve the existing OpenClaw plugin lifecycle and
the public behavior of lifecycle tools. Call no external/LLM API. When done, run
the Verify command, then make a single commit with the given message. If a needed
change is out of scope, stop and report it instead.

## Current state
The plugin still uses the template runner. `src/plugin/index.ts` registers
`start_session`, `run_agent`, `get_session_status`, `stop_run`, `reset_all`,
`end_session`, and `run_agent` calls `ExampleAgentRunner` in `src/main/`.

## Goal
Replace the template runner with a runner that launches the local Python
simulator and streams progress back, preserving the lifecycle.

## Touch
- `src/main/` — add `JepaInspiredSiliconSandboxRunner.ts`; retire
  `ExampleAgent.ts`.
- `src/plugin/index.ts` — rename `run_agent` → `run_market_simulation` with
  params `current_market`, `company_type`, `strategic_action`,
  `simulation_rounds`; wire it to the new runner.
- `openclaw.plugin.json` and `package.json` — update plugin identity from
  `agent-template` to the Silicon Sandbox.
- `scripts/test-plugin.ts` — update the smoke test for the new tool.

## Do
- `JepaInspiredSiliconSandboxRunner` spawns the Python simulator as a child
  process, passes the user inputs, and streams its `--json-progress` lines into
  the existing event buffer as progress events.
- Return the final Market Vision report and expose generated figures as artifacts
  when available.
- Keep `start_session`, `get_session_status`, `stop_run`, `reset_all`,
  `end_session` working with the same semantics (including cooperative
  cancellation via AbortSignal).
- Do not implement any model/simulation logic in TypeScript — only orchestration.

## Out of scope
- No changes to the Python package's modeling/simulation logic.

## Verify
```
npm run typecheck && npm run lint && npm run test:plugin
```

## Commit
```
feat(plugin): JepaInspiredSiliconSandboxRunner over local Python engine
```
