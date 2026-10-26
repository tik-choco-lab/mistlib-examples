# @tik-choco/mistlib-web

Thin browser wrapper around the [mistlib engine](https://github.com/tik-choco-lab/mistlib).

```sh
npm i @tik-choco/mistlib @tik-choco/mistlib-web
```

Use in a browser application:

```js
import { MistNode, getVersion, getBuildInfo } from '@tik-choco/mistlib-web';

console.log(await getVersion()); // Loaded engine version
console.log(JSON.parse(await getBuildInfo())); // Loaded engine build details
const node = new MistNode(crypto.randomUUID(), {
    signaling: {
        mode: 'nostr',
        nostr: {
            inviteSalt: 'my-app',
            inviteCode: 'replace-with-your-shared-secret',
        },
    },
});
await node.init();
await node.joinRoomAsync('my-room');
```

Choose invite values unique to your application and share them with its peers.
The wrapper imports the engine by package name (`@tik-choco/mistlib`), so your
bundler or browser import map must resolve it. The engine requires version 0.7.0
or later. Wrapper versions are independent from engine versions.

Both metadata functions initialize WASM without starting a node and return strings;
`getBuildInfo()` returns JSON. If the loaded engine lacks these exports, update to
`@tik-choco/mistlib >= 0.7.0`. For a local import map, rerun `just fetch 0.7.0` or
`just sync` at the repository root, then reload the page.

## Delivery methods

`node.sendMessage(toId, payload, delivery, roomId)` accepts these constants:

| Export | Code | Guarantee |
| --- | --- | --- |
| `DELIVERY_RELIABLE` | 0 | Fully reliable, ordered |
| `DELIVERY_UNRELIABLE_ORDERED` | 1 | May drop messages, ordered |
| `DELIVERY_UNRELIABLE` | 2 | May drop or reorder messages (default) |
| `DELIVERY_RELIABLE_UNORDERED` | 3 | Fully reliable, unordered |

The `DeliveryMethod` TypeScript type covers codes 0–3. Code 3 falls back to the
reliable ordered channel when the peer lacks support.

```js
import { DELIVERY_RELIABLE_UNORDERED } from '@tik-choco/mistlib-web';
node.sendMessage('peer-id', 'hello', DELIVERY_RELIABLE_UNORDERED);
```

Options pass through to the engine, including `storageTransfer`. MistLib 0.7.0
supplies CP50 defaults when it is omitted.

Run `node --test wrappers/web/tests/*.test.mjs` from the repository root to test
with a mock engine; no WASM binary is needed.

## Leaving rooms

```js
node.leaveRoom('my-room'); // Leave only this room
node.leaveAllRooms();     // Leave every room and release the engine
```

`leaveAllRooms()` calls the WASM `leave_all_rooms()` export and requires mistlib
0.7.0 or later. `leaveRoom(id)` calls WASM `leave_room(id)`.
The no-argument `leaveRoom()` and `leaveRoomId(id)` aliases are deprecated and
warn; use `leaveAllRooms()` and `leaveRoom(id)` respectively.

`await node.leaveRoomAsync(id)` waits for signaling and transport cleanup.

## Media audience and storage

`node.setLocalTrackAudience(trackId, nodeIds)` limits a registered track to the
listed peers. Pass `null`/`undefined` for all peers or `[]` for nobody.
`await setLogLevel('debug')` configures engine logging before the first node init.

Storage exports follow the engine's async API: `storage_add`, `storage_get`,
`storage_add_at`, `storage_pin`, `storage_unpin`, `storage_is_pinned`,
`storage_add_pinned`, `storage_kv_set`, `storage_kv_get`, and `storage_kv_delete`.
Pinning keeps roots out of eviction; KV data is local to the browser origin.

## Changelog

- **0.3.0**: Require engine 0.7.0, add `getBuildInfo()`, stale-engine diagnostics,
  track audience control, async room leave and log level configuration.
