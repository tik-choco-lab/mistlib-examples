"""Wrapper ABI regression tests; no native engine is loaded."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

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


if __name__ == "__main__":
    unittest.main()
