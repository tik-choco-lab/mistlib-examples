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
