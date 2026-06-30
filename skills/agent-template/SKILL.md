---
name: agent-template
description: Use the Agent Template OpenClaw plugin. Trigger only for template/demo agent runs or while developing a new plugin from this template.
---

# Agent Template Playbook

This skill demonstrates the standard lifecycle for an OpenClaw plugin that runs
agent work in the background.

## Canonical Flow

1. Call `start_session`.
2. Save the returned `session_id`.
3. Call `run_agent` with that `session_id`.
4. Tell the user the run is in progress.
5. When the user asks for progress, call `get_session_status`.
6. When `run_status` is `completed`, show `result.summary` and the artifact path.
7. Call `end_session` when the user is done.

## Tool Calls

Start:

```json
{ "name": "start_session", "arguments": {} }
```

Run:

```json
{
  "name": "run_agent",
  "arguments": {
    "session_id": "...",
    "topic": "demo",
    "steps": 3
  }
}
```

Status:

```json
{ "name": "get_session_status", "arguments": { "session_id": "..." } }
```

Stop:

```json
{ "name": "stop_run", "arguments": { "session_id": "..." } }
```

End:

```json
{ "name": "end_session", "arguments": { "session_id": "..." } }
```

## Status Handling

- `idle`: no run has started.
- `running`: report `last_phase`, recent progress events, and elapsed time.
- `completed`: present `result.summary` and `result.artifactPath`.
- `stopped`: tell the user the run was cancelled.
- `failed`: show `error` and suggest retrying after the cause is addressed.

## Reset

For a dry-run preview:

```json
{ "name": "reset_all", "arguments": {} }
```

After explicit user confirmation:

```json
{ "name": "reset_all", "arguments": { "confirm": true } }
```

Never call confirmed reset without asking first.
