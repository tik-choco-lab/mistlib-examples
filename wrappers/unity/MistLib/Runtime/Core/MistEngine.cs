using System;
using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;

namespace MistLib
{
    public class MistEngine : MonoBehaviour
    {
        public enum DeliveryMethod : uint
        {
            ReliableOrdered = 0,
            UnreliableOrdered = 1,
            Unreliable = 2
        }

        public static MistEngine I { get; private set; }
        public string SelfId { get; private set; }
        private const string DefaultNostrRelayUrl = "ws://127.0.0.1:7777";
        // inviteSalt and inviteCode are deliberately absent. Together they derive
        // the secret that scopes discovery, so every deployment sharing them shares
        // one namespace and one admission secret -- shipping defaults here meant
        // every project built from this wrapper inherited the same pair. Set
        // InviteSalt and InviteCode below to values unique to your application.
        private const string InviteSalt = "";
        private const string InviteCode = "";
        private static string DefaultConfigJson =>
            "{\"signaling\":{\"mode\":\"nostr\",\"nostr\":{\"relays\":[\"" + DefaultNostrRelayUrl +
            "\"],\"discoveryKind\":25049,\"messageKind\":25050,\"ttlSeconds\":60," +
            "\"maxClockSkewSeconds\":300,\"inviteSalt\":\"" + InviteSalt +
            "\",\"inviteCode\":\"" + InviteCode + "\"}}}";
        // CIDs are multibase-prefixed base32(varint version + varint codec + varint multihash + sha256 digest),
        // ~59 bytes in practice; this leaves ample margin without over-allocating.
        private const int CidBufferSize = 256;
        // get_config gives no required-length hint on overflow (unlike storage_get), so a
        // single generously-sized buffer is used instead of a two-phase query.
        private const int ConfigBufferSize = 65536;

        private static MistFFI.EventCallbackV2 _staticEventCallback;
        private static MistFFI.LogCallback _staticLogCallback;
        private static readonly ConcurrentQueue<(uint type, string from, byte[] data, string roomId)> _eventQueue = new();

        [SerializeField] private string _roomId = "lobby";
        [SerializeField] private string _customNodeId = "";
        [SerializeField] private bool _useDefaultNostrConfig = true;
        [SerializeField] private string _signalingUrl = DefaultNostrRelayUrl;
        [SerializeField] private string _configJson = "";

        public event Action<uint, string, byte[]> OnEvent;
        public event Action<uint, string, byte[], string> OnRoomEvent;

        private void Awake()
        {
            if (I != null)
            {
                Destroy(gameObject);
                return;
            }
            I = this;
            DontDestroyOnLoad(gameObject);

            _staticEventCallback = OnEventFromRust;
            _staticLogCallback = OnLogFromRust;
            
            SelfId = string.IsNullOrEmpty(_customNodeId) ? Guid.NewGuid().ToString() : _customNodeId;
            if (_useDefaultNostrConfig || !string.IsNullOrWhiteSpace(_configJson))
            {
                var useBuiltIn = string.IsNullOrWhiteSpace(_configJson);
                if (useBuiltIn && (InviteSalt.Length == 0 || InviteCode.Length == 0))
                {
                    // The engine would reject an empty invite and init_with_config
                    // would just return false, leaving no clue why nothing connects.
                    Debug.LogError(
                        "MistLib: set InviteSalt and InviteCode in MistEngine.cs before using " +
                        "the built-in Nostr config. Together they derive the secret that decides " +
                        "who can reach your rooms, so peers sharing them share a namespace -- " +
                        "which is why no default ships. Alternatively supply your own config JSON.");
                    return;
                }
                if (!InitWithConfig(SelfId, useBuiltIn ? DefaultConfigJson : _configJson))
                {
                    Debug.LogError("MistLib: the engine rejected the signaling configuration.");
                    return;
                }
            }
            else
            {
                Init(SelfId, _signalingUrl);
            }
            
            MistFFI.register_event_callback_v2(_staticEventCallback);
            MistFFI.register_log_callback(_staticLogCallback);
        }

        private void Start()
        {
            JoinRoom(_roomId);
            MistLogger.Log($"Engine initialized and joined room: {_roomId}");
        }

        private void OnDestroy()
        {
            if (I == this)
            {
                MistFFI.leave_room();
                I = null;
            }
        }

        private void Update()
        {
            while (_eventQueue.TryDequeue(out var ev))
            {
                OnHandleEvent(ev.type, ev.from, ev.data, ev.roomId);
            }
        }

        protected virtual void OnHandleEvent(uint type, string from, byte[] data, string roomId)
        {
            OnEvent?.Invoke(type, from, data);
            OnRoomEvent?.Invoke(type, from, data, roomId);
        }

        public void Init(string nodeId, string signalingUrl)
        {
            var idBytes = Encoding.UTF8.GetBytes(nodeId);
            var urlBytes = Encoding.UTF8.GetBytes(signalingUrl);
            
            PinAndCall(idBytes, (idPtr, idLen) => {
                PinAndCall(urlBytes, (urlPtr, urlLen) => {
                    MistFFI.init(idPtr, idLen, urlPtr, urlLen);
                });
            });
        }

        public bool InitWithConfig(string nodeId, string configJson)
        {
            var idBytes = Encoding.UTF8.GetBytes(nodeId);
            var configBytes = Encoding.UTF8.GetBytes(configJson);
            var accepted = false;

            PinAndCall(idBytes, (idPtr, idLen) => {
                PinAndCall(configBytes, (configPtr, configLen) => {
                    accepted = MistFFI.init_with_config(idPtr, idLen, configPtr, configLen);
                });
            });
            return accepted;
        }

        public void JoinRoom(string roomId)
        {
            // Callable multiple times with different room ids; re-joining the
            // same room is an idempotent re-announce.
            var bytes = Encoding.UTF8.GetBytes(roomId);
            PinAndCall(bytes, (ptr, len) => MistFFI.join_room(ptr, len));
        }

        public void LeaveRoom() => MistFFI.leave_room();

        public void LeaveRoom(string roomId)
        {
            var bytes = Encoding.UTF8.GetBytes(roomId);
            PinAndCall(bytes, (ptr, len) => MistFFI.leave_room_id(ptr, len));
        }

        public void UpdatePosition(Vector3 pos, string room = null)
        {
            if (!string.IsNullOrEmpty(room))
            {
                var roomBytes = Encoding.UTF8.GetBytes(room);
                PinAndCall(roomBytes, (roomPtr, roomLen) => {
                    MistFFI.update_position_in_room(roomPtr, roomLen, pos.x, pos.y, pos.z);
                });
                return;
            }
            MistFFI.update_position(pos.x, pos.y, pos.z);
        }

        public void SendMessage(string targetNodeId, byte[] data, DeliveryMethod method = DeliveryMethod.Unreliable, string room = null)
        {
            var idBytes = string.IsNullOrEmpty(targetNodeId) ? Array.Empty<byte>() : Encoding.UTF8.GetBytes(targetNodeId);
            if (!string.IsNullOrEmpty(room))
            {
                var roomBytes = Encoding.UTF8.GetBytes(room);
                PinAndCall(roomBytes, (roomPtr, roomLen) => {
                    PinAndCall(idBytes, (idPtr, idLen) => {
                        PinAndCall(data, (dataPtr, dataLen) => {
                            MistFFI.send_message_in_room(roomPtr, roomLen, idPtr, idLen, dataPtr, dataLen, (uint)method);
                        });
                    });
                });
                return;
            }
            PinAndCall(idBytes, (idPtr, idLen) => {
                PinAndCall(data, (dataPtr, dataLen) => {
                    MistFFI.send_message(idPtr, idLen, dataPtr, dataLen, (uint)method);
                });
            });
        }

        public string GetStats()
        {
            var buffer = new byte[4096];
            uint written = 0;
            var handle = GCHandle.Alloc(buffer, GCHandleType.Pinned);
            try
            {
                written = MistFFI.get_stats(handle.AddrOfPinnedObject(), (UIntPtr)buffer.Length);
            }
            finally
            {
                handle.Free();
            }

            if (written > 0 && written <= buffer.Length)
            {
                return Encoding.UTF8.GetString(buffer, 0, (int)written);
            }
            return "{}";
        }

        public string StorageAdd(string name, byte[] data) => StorageAddCore(name, data, null);

        // Explicit-position variant of StorageAdd (SPEC-16): tags the block with a world
        // position, prioritizing it for retention over untagged blocks during spatial eviction.
        public string StorageAddAt(string name, byte[] data, Vector3 position) => StorageAddCore(name, data, position);

        public byte[] StorageGet(string cid)
        {
            if (string.IsNullOrEmpty(cid))
            {
                return null;
            }
            var cidBytes = Encoding.UTF8.GetBytes(cid);

            // Phase 1: probe with a zero-length buffer. storage_get reports the required
            // length instead of copying when the buffer is too small, so this never copies.
            var probe = new byte[1];
            uint required = 0;
            PinAndCall(cidBytes, (cidPtr, cidLen) => {
                required = PinBufferAndCall(probe, UIntPtr.Zero, (bufPtr, bufLen) =>
                    MistFFI.storage_get(cidPtr, cidLen, bufPtr, bufLen));
            });

            if (required == 0)
            {
                return null;
            }

            // Phase 2: fetch into a buffer sized exactly for the length reported above.
            var buffer = new byte[required];
            uint written = 0;
            PinAndCall(cidBytes, (cidPtr, cidLen) => {
                written = PinBufferAndCall(buffer, (UIntPtr)buffer.Length, (bufPtr, bufLen) =>
                    MistFFI.storage_get(cidPtr, cidLen, bufPtr, bufLen));
            });

            if (written == 0 || written > buffer.Length)
            {
                return null;
            }
            if (written == buffer.Length)
            {
                return buffer;
            }
            // Underlying data shrank between the probe and the fetch; trim to what was written.
            var result = new byte[written];
            Array.Copy(buffer, result, (int)written);
            return result;
        }

        public string GetConfigJson()
        {
            var buffer = new byte[ConfigBufferSize];
            uint written = PinBufferAndCall(buffer, (UIntPtr)buffer.Length, MistFFI.get_config);

            if (written == 0 || written > buffer.Length)
            {
                return null;
            }
            return Encoding.UTF8.GetString(buffer, 0, (int)written);
        }

        private string StorageAddCore(string name, byte[] data, Vector3? position)
        {
            var nameBytes = Encoding.UTF8.GetBytes(name ?? string.Empty);
            var cidBuffer = new byte[CidBufferSize];
            uint written = 0;

            PinAndCall(nameBytes, (namePtr, nameLen) => {
                PinAndCall(data, (dataPtr, dataLen) => {
                    written = PinBufferAndCall(cidBuffer, (UIntPtr)cidBuffer.Length, (cidPtr, cidLen) =>
                        position.HasValue
                            ? MistFFI.storage_add_at(namePtr, nameLen, dataPtr, dataLen, position.Value.x, position.Value.y, position.Value.z, cidPtr, cidLen)
                            : MistFFI.storage_add(namePtr, nameLen, dataPtr, dataLen, cidPtr, cidLen));
                });
            });

            if (written == 0 || written > cidBuffer.Length)
            {
                return null;
            }
            return Encoding.UTF8.GetString(cidBuffer, 0, (int)written);
        }

        private void PinAndCall(byte[] data, Action<IntPtr, UIntPtr> action)
        {
            if (data == null || data.Length == 0)
            {
                action(IntPtr.Zero, UIntPtr.Zero);
                return;
            }
            var handle = GCHandle.Alloc(data, GCHandleType.Pinned);
            try
            {
                action(handle.AddrOfPinnedObject(), (UIntPtr)data.Length);
            }
            finally
            {
                handle.Free();
            }
        }

        // Pins an output buffer for the duration of an FFI call that writes into it
        // (get_stats-style: pointer + length in, byte count written out).
        private static uint PinBufferAndCall(byte[] buffer, UIntPtr len, Func<IntPtr, UIntPtr, uint> call)
        {
            var handle = GCHandle.Alloc(buffer, GCHandleType.Pinned);
            try
            {
                return call(handle.AddrOfPinnedObject(), len);
            }
            finally
            {
                handle.Free();
            }
        }

        [AOT.MonoPInvokeCallback(typeof(MistFFI.EventCallbackV2))]
        private static void OnEventFromRust(uint eventType, IntPtr room, UIntPtr roomLen, IntPtr from, UIntPtr fromLen, IntPtr data, UIntPtr dataLen)
        {
            try
            {
                var roomBuffer = new byte[(int)roomLen];
                Marshal.Copy(room, roomBuffer, 0, (int)roomLen);
                var roomId = Encoding.UTF8.GetString(roomBuffer);

                var fromBuffer = new byte[(int)fromLen];
                Marshal.Copy(from, fromBuffer, 0, (int)fromLen);
                var fromId = Encoding.UTF8.GetString(fromBuffer);

                var dataBuffer = new byte[(int)dataLen];
                Marshal.Copy(data, dataBuffer, 0, (int)dataLen);

                _eventQueue.Enqueue((eventType, fromId, dataBuffer, roomId));
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
            }
        }

        [AOT.MonoPInvokeCallback(typeof(MistFFI.LogCallback))]
        private static void OnLogFromRust(uint level, IntPtr data, UIntPtr len)
        {
            try
            {
                var buffer = new byte[(int)len];
                Marshal.Copy(data, buffer, 0, (int)len);
                var message = Encoding.UTF8.GetString(buffer);
                MistLogger.Log(message, (MistLogger.LogLevel)level);
            }
            catch (Exception ex)
            {
                System.Console.WriteLine($"[MistLib Log Callback Error] {ex.Message}");
            }
        }
    }
}
