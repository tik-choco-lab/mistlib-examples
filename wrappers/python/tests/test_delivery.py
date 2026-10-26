"""Wrapper ABI regression tests; no native engine is loaded."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import ctypes

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mist


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.node = mist.MistNode.__new__(mist.MistNode)
        self.node.lib = Mock()

    def test_public_codes(self):
        self.assertEqual(
            (mist.DELIVERY_RELIABLE, mist.DELIVERY_UNRELIABLE_ORDERED,
             mist.DELIVERY_UNRELIABLE, mist.DELIVERY_RELIABLE_UNORDERED),
            (0, 1, 2, 3),
        )

    def test_all_codes_reach_both_ffi_entry_points(self):
        for code in (0, 1, 2, 3):
            for room in (None, "room-1"):
                with self.subTest(code=code, room=room):
                    self.node.lib.reset_mock()
                    self.node.send_message("peer", b"\x00\xff", delivery=code, room=room)
                    args = (b"peer", 4, b"\x00\xff", 2, code)
                    if room is None:
                        self.node.lib.send_message.assert_called_once_with(*args)
                        self.node.lib.send_message_in_room.assert_not_called()
                    else:
                        self.node.lib.send_message_in_room.assert_called_once_with(
                            b"room-1", 6, *args)
                        self.node.lib.send_message.assert_not_called()

    def test_default_remains_unreliable(self):
        self.node.send_message(None, b"hello")
        self.node.lib.send_message.assert_called_once_with(b"", 0, b"hello", 5, 2)


class RoomLeaveTests(unittest.TestCase):
    def setUp(self):
        self.active = patch("mist.core._active_instance", None)
        self.active.start()
        self.addCleanup(self.active.stop)

    def make_node(self):
        lib = Mock()
        with patch("mist.core.os.path.exists", return_value=True), \
             patch("mist.core.ctypes.CDLL", return_value=lib):
            node = mist.MistNode("sender", "ws://localhost")
        return node, lib

    def test_new_bindings_and_single_room_preserve_active_instance(self):
        node, lib = self.make_node()
        self.assertEqual(lib.leave_all_rooms.argtypes, [])
        self.assertIsNone(lib.leave_all_rooms.restype)
        self.assertEqual(lib.leave_room_id.argtypes, [ctypes.c_char_p, ctypes.c_size_t])
        node.leave_room(room="部屋")
        lib.leave_room_id.assert_called_once_with("部屋".encode(), 6)
        lib.leave_all_rooms.assert_not_called()
        lib.leave_room.assert_not_called()
        self.assertIs(mist.core._active_instance, node)
        node.leave_all_rooms()
        lib.leave_all_rooms.assert_called_once_with()
        self.assertIsNone(mist.core._active_instance)

    def test_deprecated_aliases(self):
        node, lib = self.make_node()
        with self.assertWarnsRegex(DeprecationWarning, "leave_room_id"):
            node.leave_room_id("room-1")
        lib.leave_room_id.assert_called_once_with(b"room-1", 6)
        with self.assertWarnsRegex(DeprecationWarning, "leave_all_rooms"):
            node.leave_room()
        lib.leave_all_rooms.assert_called_once_with()
        lib.leave_room.assert_not_called()
        self.assertIsNone(mist.core._active_instance)

    def test_older_library_is_rejected(self):
        lib = Mock()
        del lib.leave_all_rooms
        with patch("mist.core.os.path.exists", return_value=True), \
             patch("mist.core.ctypes.CDLL", return_value=lib):
            with self.assertRaises(AttributeError):
                mist.MistNode("sender", "ws://localhost")
        self.assertIsNone(mist.core._active_instance)
        lib.leave_room.assert_not_called()


if __name__ == "__main__":
    unittest.main()
