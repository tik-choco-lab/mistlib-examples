# Unity wrapper

The `MistLib` package calls the native mistlib engine through P/Invoke.
Place the platform library in `MistLib/Runtime/Plugins/` (see the repository setup).
Requires mistlib native **0.7.0 or later**. Run `just fetch 0.7.0` at the repository
root to install the Linux x86_64, Windows x86_64 and macOS aarch64 plugins.

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

Code 3 is available in mistlib 0.7.0. When the peer lacks the capability,
the engine falls back to the reliable ordered channel.

```csharp
MistEngine.I.SendMessage("peer-id", data, MistEngine.DeliveryMethod.ReliableUnordered);
```

JSON configuration passes through to the engine, including `storageTransfer`.
MistLib 0.7.0 supplies CP50 defaults when it is omitted.

## Leaving rooms

```csharp
MistEngine.I.LeaveRoom("my-room"); // Leave only this room
MistEngine.I.LeaveAllRooms();     // Leave every room
```

`LeaveAllRooms()` requires mistlib native 0.7.0 or later and is also used during
engine destruction. `LeaveRoom(id)` binds native `leave_room_id`; `LeaveAllRooms()`
binds `leave_all_rooms`. The wrapper never calls the native `leave_room` symbol,
whose signature will change in 0.8. The old no-argument `LeaveRoom()` is an
`[Obsolete]` alias forwarding to `LeaveAllRooms()`.

## Changelog

- **0.2.0**: Require engine 0.7.0; expose `GetVersion()` and `GetBuildInfo()`.
