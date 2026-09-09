# Configuration interface

Relative paths resolve from `project.root`, which resolves from the config directory. These keys are the portable contract.

- `project`: display `name`, immutable `revision`, project `root`, and Blender `blend_file`.
- `render`: frames, state, manifest, inclusive range, FPS, size, engine/device, samples, denoising, and image format.
- `monitor`: bind host/port and dashboard assets. `plugin:assets/dashboard` selects the bundled UI.
- `remote`: HTTP base URL, polling interval, and request timeout used by delivery.
- `delivery`: destination paths, FFmpeg tools, verification switches, one uncompressed `master`, and compressed `variants`.

The manifest maps each six-digit PNG filename to byte size and SHA-256. State files contain `schema_version`, `stage`, project, revision, timestamps, progress, output paths, and errors. Consumers must tolerate extra fields.

Frame directories must be unique per revision. Never point a new revision at older frames unless the user explicitly intends to reuse identical renders.
