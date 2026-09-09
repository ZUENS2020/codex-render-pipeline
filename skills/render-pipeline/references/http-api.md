# HTTP API

- `GET /api/metrics`: current phase plus render/transfer progress, ETA, GPU utilization/VRAM/temperature/power/clock, CPU/RAM/processes, disk capacity, output metadata, trend history, and recent logs.
- `GET /api/status`: stable machine-readable state for automation. Delivery uses `stage == "frames_complete"` as the transfer gate.
- `GET /manifest.json`: source frame byte sizes and SHA-256 hashes. Available after render completion.
- `GET /frames/000001.png`: exact source frame. Only six-digit PNG names are accepted.
- `GET /preview.png`: most recent committed source frame.
- `GET /`: responsive human dashboard.

Render stages: `starting`, `rendering`, `frames_complete`, `failed`.

Delivery stages: `waiting_render`, `downloading`, `verifying`, `assembling_master`, `verifying_master`, `compressing`, `validating_variant`, `complete`, `failed`.

Every JSON response has `schema_version`. Consumers must tolerate new fields. Place authentication or an access proxy in front of the monitor when exposing it beyond a trusted network.
