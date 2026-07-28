using System;
using System.Runtime.InteropServices;

namespace MistLib
{
    public static class MistFFI
    {
        private const string DllName = "mistlib";

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate void EventCallback(uint eventType, IntPtr from, UIntPtr fromLen, IntPtr data, UIntPtr dataLen);

        // v2: same shape as EventCallback, with a room_id (ptr, len) pair inserted
        // right after eventType (mirrors the Rust EventCallbackV2 ABI, SPEC-12).
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate void EventCallbackV2(uint eventType, IntPtr room, UIntPtr roomLen, IntPtr from, UIntPtr fromLen, IntPtr data, UIntPtr dataLen);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate void LogCallback(uint level, IntPtr data, UIntPtr len);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void register_event_callback(EventCallback cb);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void register_event_callback_v2(EventCallbackV2 cb);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void register_log_callback(LogCallback cb);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void init(IntPtr idPtr, UIntPtr idLen, IntPtr urlPtr, UIntPtr urlLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        [return: MarshalAs(UnmanagedType.I1)]
        public static extern bool init_with_config(IntPtr idPtr, UIntPtr idLen, IntPtr configPtr, UIntPtr configLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void join_room(IntPtr roomPtr, UIntPtr roomLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void leave_room();

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void leave_room_id(IntPtr roomPtr, UIntPtr roomLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void update_position(float x, float y, float z);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void update_position_in_room(IntPtr roomPtr, UIntPtr roomLen, float x, float y, float z);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void on_connected(IntPtr nodePtr, UIntPtr nodeLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void on_disconnected(IntPtr nodePtr, UIntPtr nodeLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void set_config(IntPtr data, UIntPtr len);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void send_message(IntPtr targetPtr, UIntPtr targetLen, IntPtr dataPtr, UIntPtr dataLen, uint method);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void send_message_in_room(IntPtr roomPtr, UIntPtr roomLen, IntPtr targetPtr, UIntPtr targetLen, IntPtr dataPtr, UIntPtr dataLen, uint method);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint get_stats(IntPtr buffer, UIntPtr bufferLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint storage_add(IntPtr namePtr, UIntPtr nameLen, IntPtr dataPtr, UIntPtr dataLen, IntPtr cidBuffer, UIntPtr cidBufferLen);

        // Explicit-position variant of storage_add (SPEC-16): tags the block with a
        // world position instead of relying on the caller's last update_position.
        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint storage_add_at(IntPtr namePtr, UIntPtr nameLen, IntPtr dataPtr, UIntPtr dataLen, float x, float y, float z, IntPtr cidBuffer, UIntPtr cidBufferLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint storage_get(IntPtr cidPtr, UIntPtr cidLen, IntPtr buffer, UIntPtr bufferLen);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint get_config(IntPtr buffer, UIntPtr bufferLen);
    }
}
