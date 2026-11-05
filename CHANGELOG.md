# Changelog

## 2026-11-05 — engine 0.7.3-beta.5

- Pin wrappers, demos, scripts and documentation to engine 0.7.3-beta.5;
  exported APIs and event codes remain unchanged.
- Engine fix: `nostr_auto` now also prefers a loopback relay found in the
  fetched relay list (the default list includes `ws://localhost:7447`); when it
  opens, the listed remote relays are not contacted.

## 2026-11-05 — engine 0.7.3-beta.4 (Web wrapper 0.3.1-beta.3)

- Pin wrappers, demos, scripts and documentation to engine 0.7.3-beta.4;
  exported APIs and event codes remain unchanged.
- Default to `nostr_auto`, which prefers configured local relays before falling
  back to remote relays. Web and Python invite guards cover `nostr_auto` and
  `nostrAuto`; the Web defaults merge covers both as well as `nostr`.
- Switch the Web demos to `nostr_auto`; Python demos use the updated default.

## 2026-11-05 — Web wrapper 0.3.1-beta.2

- feat(web): expose storage_add_owned / storage_add_pinned_owned (zero-copy, mistlib 0.7.3-beta.3)

## 2026-11-04 — engine 0.7.3-beta.3 (Web wrapper 0.3.1-beta.1)

- Target engine 0.7.3-beta.3 (npm `beta` dist-tag, GitHub prerelease) exactly
  across wrappers, demo import maps, scripts and API manifests; fetch local
  native and WASM artifacts with `just fetch 0.7.3-beta.3`. The exported API and
  the event codes 0–12 / 100–101 are unchanged from 0.7.1; the engine changes
  since then are internal (signaling load bounds, WebRTC recovery, storage
  transfer robustness, wasm storage work off the main thread).
- Version checks in `sync-mistlib.sh`, `check-engine-api.mjs` and the
  update-engine workflow now accept semver prerelease versions.
- Add `just publish status|beta|stable [--unity] [--push] [--dry-run]` for Web
  wrapper releases. Prereleases are staged under the npm `beta` dist-tag; a
  stable wrapper is refused while the engine pin is a prerelease.

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
