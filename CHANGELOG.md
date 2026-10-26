# Changelog

## 2026-10-26 — engine 0.7.1 (Web wrapper 0.3.0, Unity package 0.2.0)

- Target engine 0.7.1 exactly across wrappers, demo import maps, scripts and API
  manifests. Engine 0.7.1 is published on GitHub Releases and npm; fetch local
  native and WASM artifacts with `just fetch 0.7.1`.
- Web wrapper 0.3.0 (breaking): adopt the unified event codes 0–12, including
  node position updates (7), connection loss (9), and room lifecycle (10–12).
  TypeScript constants now have literal values. Media codes stay 100/101.
- Unity package 0.2.0 (breaking): replace misleading `MistLibMessageType` members
  with canonical callback names and values, including native room events. The
  sync manager handles `Raw` (0); room readiness/failure/leave and connection loss
  are logged when callbacks reach the main thread.
- Python (source package, no independent version): rename `EVENT_JOIN` and
  `EVENT_LEAVE` to `EVENT_PEER_CONNECTED` and `EVENT_PEER_DISCONNECTED`, without
  aliases. Export all 13 application events and log native room lifecycle events.
- Document native-compatible Web peer/AOI payloads: UTF-8 `joined`, `entered`,
  and `left`, rather than the old WASM payloads.
- Add offline event/export/pin validation and callback contract tests. Restrict
  engine update automation to the supported manifest version.
