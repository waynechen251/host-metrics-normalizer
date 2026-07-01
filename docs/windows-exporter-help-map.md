# windows_exporter HELP knowledge index

This directory is organized by `windows_exporter` version.

Each version file is a live capture from a specific exporter version. Keep one version per file, and do not merge different exporter versions into the same document.

## Current versions

- [windows_exporter-0.31.6.md](windows-exporter-help-map/windows_exporter-0.31.6.md) - live scrape from `http://127.0.0.1:9182/metrics`

## Capture rule

1. Start the target `windows_exporter` version.
2. Enable the collector set you want to document.
3. Scrape `http://127.0.0.1:9182/metrics`.
4. Split metrics by `# HELP` family name.
5. Save the result as `windows_exporter-<version>.md`.

If a later scrape of the same version changes collector coverage, create a new versioned document only when the exporter version changes. Keep the file tied to one version and one capture context.
