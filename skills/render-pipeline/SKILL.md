---
name: render-pipeline
description: Configure, run, resume, monitor, transfer, verify, assemble, and compress Blender animation renders across local, Windows, and rented GPU machines. Use for frame-based render delivery workflows rather than scene geometry editing.
---

# Render Pipeline

Use the plugin scripts as the execution layer and keep project choices in `render-pipeline.json`. Never hardcode a project name, host, credential, frame range, output path, or codec into copied scripts.

1. Locate Blender, FFmpeg/FFprobe, the `.blend` file, storage, and remote hosts authorized by the user.
2. Run `scripts/pipeline.py init --root <project>` when no config exists. Adapt the generated config and run `validate` before a paid or long render.
3. Benchmark and inspect representative frames when the scene has not been render-tested. Record the engine, device, samples, resolution, FPS, range, format, and denoiser in config.
4. Start `scripts/monitor.py` on every host whose stages should be visible. Stable routes are `/api/metrics`, `/api/status`, `/manifest.json`, `/frames/<six-digit>.png`, and `/preview.png`.
5. Run Blender with `scripts/blender_render.py -- <config-path>`. It validates PNG chunks and resumes at the first missing or corrupt frame. Preserve completed earlier revisions separately.
6. Run `scripts/deliver.py <config-path>` on the delivery machine. It waits, downloads directly, verifies the manifest, creates the uncompressed master, compares decoded pixels when enabled, and only then creates and validates compressed variants.
7. Report exact paths, metadata, validation results, and limitations. A running process is not a completed delivery.

Use existing authentication. Never put passwords, private keys, or tunnel tokens in config, logs, or repositories. Require an explicit user request before starting paid infrastructure or deleting remote frames.

Read [configuration.md](references/configuration.md) when changing config. Read [operations.md](references/operations.md) for multi-machine deployment, Windows background tasks, and recovery. Read [http-api.md](references/http-api.md) when integrating a custom dashboard, tunnel, orchestrator, or Codex-facing status tool.
