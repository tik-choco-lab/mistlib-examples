# @tik-choco/mistlib-web

Thin browser wrapper around the [mistlib engine](https://github.com/tik-choco-lab/mistlib).

```sh
npm i @tik-choco/mistlib @tik-choco/mistlib-web
```

Use in a browser application:

```js
import { MistNode, getVersion } from '@tik-choco/mistlib-web';

console.log(await getVersion()); // Loaded engine version
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
bundler or browser import map must resolve it. The engine requires version 0.6.2
or later. Wrapper versions are independent from engine versions.

## Delivery methods

`node.sendMessage(toId, payload, delivery, roomId)` accepts these constants:

| Export | Code | Guarantee |
| --- | --- | --- |
| `DELIVERY_RELIABLE` | 0 | Fully reliable, ordered |
| `DELIVERY_UNRELIABLE_ORDERED` | 1 | May drop messages, ordered |
| `DELIVERY_UNRELIABLE` | 2 | May drop or reorder messages (default) |
| `DELIVERY_RELIABLE_UNORDERED` | 3 | Fully reliable, unordered |

The `DeliveryMethod` TypeScript type covers codes 0–3. Code 3 requires the upcoming
mistlib release, beyond the general minimum version above. It falls back to the
reliable ordered channel when the peer lacks support. Codes 0–2 are unchanged.

```js
import { DELIVERY_RELIABLE_UNORDERED } from '@tik-choco/mistlib-web';
node.sendMessage('peer-id', 'hello', DELIVERY_RELIABLE_UNORDERED);
```

Options pass through to the engine, including `storageTransfer`. The upcoming
engine supplies CP50 defaults when it is omitted.

Run `node --test wrappers/web/tests/*.test.mjs` from the repository root to test
with a mock engine; no WASM binary is needed.
