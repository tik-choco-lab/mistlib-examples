# Unity wrapper

The `MistLib` package calls the native mistlib engine through P/Invoke.
Place the platform library in `MistLib/Runtime/Plugins/` (see the repository setup).

`MistEngine.SendMessage(targetNodeId, data, method, room)` uses
`MistEngine.DeliveryMethod`:

| Enum member | Code | Guarantee |
| --- | --- | --- |
| `ReliableOrdered` | 0 | Fully reliable, ordered |
| `UnreliableOrdered` | 1 | May drop messages, ordered |
| `Unreliable` | 2 | May drop or reorder messages (default) |
| `ReliableUnordered` | 3 | Fully reliable, unordered |

Code 3 requires the upcoming mistlib native release. When the peer lacks the
capability, the engine falls back to the reliable ordered channel. Codes 0–2
are unchanged.

```csharp
MistEngine.I.SendMessage("peer-id", data, MistEngine.DeliveryMethod.ReliableUnordered);
```

JSON configuration passes through to the engine, including `storageTransfer`.
The upcoming engine supplies CP50 defaults when it is omitted.

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
