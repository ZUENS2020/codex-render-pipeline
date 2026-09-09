# Operations

```text
python scripts/pipeline.py init --root PROJECT
python scripts/pipeline.py validate PROJECT/render-pipeline.json
python scripts/monitor.py PROJECT/render-pipeline.json
blender --background PROJECT/scene.blend --python scripts/blender_render.py -- PROJECT/render-pipeline.json
python scripts/deliver.py PROJECT/render-pipeline.json
```

Run the monitor before remote rendering. Confirm `/api/status` and `/frames/000001.png` from the delivery host before unattended transfer.

On Windows, call `scripts/install-windows-task.ps1` with the config, Python executable, plugin root, and task name. The task uses `pythonw.exe`, survives the shell, and restarts on failure. Check Task Scheduler plus `delivery.state_file` to prove it is active.

Rerunning render preserves valid contiguous PNGs. Rerunning delivery skips verified destination PNGs. Partial downloads use `.partial`. Encoders write `.partial` output and publish final filenames only after validation.

Do not shut down a rented server until the manifest and every frame have been verified on the delivery machine. Keep the source manifest with delivered outputs.
