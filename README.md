# Codex Render Pipeline

A Codex plugin for Blender animation delivery: resumable PNG rendering, live metrics, direct remote transfer, SHA-256 verification, an uncompressed RGB master, decoded-pixel verification, and compressed delivery variants.

Copy `render-pipeline.example.json` into a Blender project as `render-pipeline.json`, then let `$render-pipeline` adapt it to the available machines and desired outputs. The scripts use Python's standard library; Blender and FFmpeg are external runtime dependencies.

The HTTP monitor exposes stable machine-readable routes so Codex can inspect or customize every stage. Credentials remain outside project configuration and use the host's existing authentication.
