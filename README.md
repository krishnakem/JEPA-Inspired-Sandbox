# OpenClaw Agent Plugin Template

This repository is a small template for building OpenClaw plugins that run
agentic work in the background, stream progress through events, support
cancellation, and write artifacts to disk.

It intentionally does not include browser automation, scraping, LLM calls, or
domain logic. The reusable part is the plugin lifecycle.

## Tool Surface

The template registers six tools:

| Tool | Purpose |
| --- | --- |
| `start_session` | Create a session and return a `session_id`. |
| `run_agent` | Start the example runner in the background. Returns immediately. |
| `get_session_status` | Poll progress, recent events, final result, or error. |
| `stop_run` | Abort the active run cooperatively via `AbortSignal`. |
| `reset_all` | Dry-run or confirmed deletion of scratch/output directories. |
| `end_session` | Abort active work and forget the session. |

Canonical flow:

```text
start_session -> run_agent -> get_session_status -> end_session
```

## Project Layout

```text
src/
  core/
    AgentSession.ts          # Session id, dirs, run config, events, abort signal
  main/
    AgentRunner.ts           # Generic runner contract and abort helpers
    ExampleAgent.ts          # Replace-me example implementation
  plugin/
    index.ts                 # OpenClaw register(api) and tool definitions
    session-registry.ts      # Event buffer + active-run bookkeeping
  shared/
    config.ts                # Template identity constants

skills/
  agent-template/
    SKILL.md                 # Playbook for an OpenClaw agent using this plugin

scripts/
  create-plugin.mjs          # Scaffold a new plugin from this template
  test-plugin.ts             # Local smoke test for plugin registration/lifecycle
```

## Creating Plugins From This Template

On GitHub, mark this repository as a template repository:

```text
Settings -> General -> Template repository
```

For local scaffolding, use the included script:

```bash
npm run create:plugin -- ../weather-agent \
  --id weather-agent \
  --name "Weather Agent" \
  --tool-prefix weather \
  --init-git
```

That command:

- copies this template into the target directory
- skips generated folders such as `.git`, `node_modules`, and `dist`
- rewrites plugin id, display name, package name, config paths, and skill name
- optionally prefixes tool names so every registered tool gets the same namespace
- optionally initializes fresh git history

Use `--install` if you want the script to run `npm install` in the new plugin.
Run `npm run create:plugin -- --help` for all options.

## How To Turn This Into A Real Plugin

1. Rename the plugin in `package.json`, `openclaw.plugin.json`, and the default
   export in `src/plugin/index.ts`.
2. Replace `ExampleAgentRunner` with your real runner.
3. Change the `run_agent` parameter schema and `parseRunInput()` in
   `src/plugin/index.ts`.
4. Keep the background-run pattern unless your tool is guaranteed to finish
   quickly. Returning immediately keeps `stop_run` and status polling usable.
5. Update `skills/agent-template/SKILL.md` so the host agent knows when to call
   your tools and how to handle statuses.
6. Update `scripts/test-plugin.ts` with your expected tools and a cheap run.

## Development

Install dependencies, then run:

```bash
npm run typecheck
npm run lint
npm run test:plugin
```

The smoke test does not call external services. It imports the plugin, registers
tools against a fake OpenClaw API, starts a session, runs the example agent,
polls for completion, and ends the session.

## OpenClaw Install

Install this repo as a linked plugin from your OpenClaw environment:

```bash
openclaw plugins install /absolute/path/to/this/repo --link
```

Restart the OpenClaw gateway after source edits. Linked plugins are picked up on
gateway boot; they are not hot-reloaded while the gateway is running.
