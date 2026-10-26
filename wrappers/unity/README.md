# Unity wrapper

The `MistLib` package calls the native mistlib engine through P/Invoke.
Place the platform library in `MistLib/Runtime/Plugins/` (see the repository setup).
Requires mistlib native **0.7.1**. Run `just fetch 0.7.1` at the repository
root to install the Linux x86_64, Windows x86_64 and macOS aarch64 plugins.

Engine 0.7.1 is available on [GitHub Releases](https://github.com/tik-choco-lab/mistlib/releases/tag/v0.7.1)
and [npm](https://www.npmjs.com/package/@tik-choco/mistlib/v/0.7.1). See the
[root README](../../README.md) for setup and the unified event table. This wrapper targets engine 0.7.1 exactly.

```csharp
Debug.Log(MistEngine.I.GetVersion());   // Loaded engine version
Debug.Log(MistEngine.I.GetBuildInfo()); // Build details as a JSON string
```

Both metadata methods query the required buffer size before reading UTF-8 data.

`MistEngine.SendMessage(targetNodeId, data, method, room)` uses
`MistEngine.DeliveryMethod`:

| Enum member | Code | Guarantee |
| --- | --- | --- |
| `ReliableOrdered` | 0 | Fully reliable, ordered |
| `UnreliableOrdered` | 1 | May drop messages, ordered |
| `Unreliable` | 2 | May drop or reorder messages (default) |
| `ReliableUnordered` | 3 | Fully reliable, unordered |

Code 3 is available in mistlib 0.7.1. When the peer lacks the capability,
the engine falls back to the reliable ordered channel.

```csharp
MistEngine.I.SendMessage("peer-id", data, MistEngine.DeliveryMethod.ReliableUnordered);
```

JSON configuration passes through to the engine, including `storageTransfer`.
MistLib 0.7.1 supplies CP50 defaults when it is omitted.

## Leaving rooms

```csharp
MistEngine.I.LeaveRoom("my-room"); // Leave only this room
MistEngine.I.LeaveAllRooms();     // Leave every room
```

`LeaveAllRooms()` requires mistlib native 0.7.1 and is also used during
engine destruction. `LeaveRoom(id)` binds native `leave_room_id`; `LeaveAllRooms()`
binds `leave_all_rooms`. The wrapper never calls the native `leave_room` symbol,
whose signature will change in 0.8. The old no-argument `LeaveRoom()` is an
`[Obsolete]` alias forwarding to `LeaveAllRooms()`.

## Events

Cast the `type` argument of `OnEvent` / `OnRoomEvent` to `MistLibMessageType`.
The enum now covers all application events 0–12 with canonical names, including
`PeerConnected`, `PeerDisconnected`, `RoomJoined`, `RoomJoinFailed`, and `RoomLeft`.
Use `OnRoomEvent` for room ids; room lifecycle events have empty senders.
`MistSyncManager` deserializes transforms only on `Raw` (0).

## Changelog

- **0.2.0** (breaking): Target engine 0.7.1 exactly; replace the misleading
  callback enum members with the canonical table, correct `Neighbors` to 4, and
  handle room lifecycle/connection-loss notifications on the main thread. Expose
  `GetVersion()` and `GetBuildInfo()`.
