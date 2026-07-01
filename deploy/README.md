# OpenClaw Sandbox Deployment

This deployment runs the existing Python engine on the `python3` shipped in
OpenClaw's sandbox image, with this repo's Python dependencies baked into a
custom image. Build the image from the repo root so `requirements.txt` is
available to the Dockerfile:

```bash
docker build -t openclaw-sandbox-jepa:bookworm-slim -f deploy/Dockerfile.sandbox .
```

Merge `deploy/openclaw.sandbox.json5` into the operator's `openclaw.json`. The
repo must be mounted as the sandbox workspace at `/workspace`.

On first container create, `setupCommand` generates training data and trains
`agent/artifacts/model.pt` inside `/workspace`:

```bash
cd /workspace && python3 -m agent.data.generate --samples 200 && python3 -m agent.train --epochs 5
```

Run a simulation from the sandbox with:

```bash
cd /workspace && python3 -m agent.simulation \
  --current-market "AI coding assistants are rapidly growing and competitive" \
  --company-type startup --strategic-action "launch a free coding agent" \
  --simulation-rounds 4 --format markdown
```

Keep `network: "none"` set. Dependencies are baked into the image, so no runtime
downloads are required.

Two deployment constraints matter:

- `model.pt` persists only because `/workspace` is a mounted repo workspace.
- Build `openclaw-sandbox-jepa:bookworm-slim` on the same CPU architecture as
  the sandbox host.
