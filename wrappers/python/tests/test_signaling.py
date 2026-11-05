"""Signaling configuration checks without loading the native engine."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mist.core import MistNode, default_config


class SignalingTests(unittest.TestCase):
    def test_default_requires_an_invite(self):
        self.assertEqual(default_config()["signaling"]["mode"], "nostr_auto")
        with patch("mist.core._active_instance", None), patch("mist.core._load_library", return_value=Mock()):
            with self.assertRaisesRegex(ValueError, "inviteSalt and inviteCode"):
                MistNode("node")

    def test_nostr_modes_require_both_invite_values(self):
        for mode in ("nostr_auto", "nostrAuto", "nostr", None):
            for nostr in ({}, {"inviteSalt": "app"}, {"inviteCode": "secret"}):
                with self.subTest(mode=mode, nostr=nostr), \
                     patch("mist.core._active_instance", None), \
                     patch("mist.core._load_library", return_value=Mock()):
                    signaling = {"nostr": nostr}
                    if mode is not None:
                        signaling["mode"] = mode
                    with self.assertRaisesRegex(ValueError, "must be set"):
                        MistNode("node", config={"signaling": signaling})

    def test_nostr_modes_accept_invites_and_keep_supplied_config(self):
        for mode in ("nostr_auto", "nostrAuto", "nostr", None):
            with self.subTest(mode=mode), patch("mist.core._active_instance", None), \
                 patch("mist.core._load_library", return_value=Mock()):
                signaling = {"nostr": {"inviteSalt": "app", "inviteCode": "secret"}}
                if mode is not None:
                    signaling["mode"] = mode
                config = {"signaling": signaling}
                node = MistNode("node", config=config)
                self.assertEqual(node.config, config)

    def test_websocket_does_not_require_an_invite(self):
        with patch("mist.core._active_instance", None), patch("mist.core._load_library", return_value=Mock()):
            node = MistNode("node", config={"signaling": {"mode": "websocket"}})
            self.assertEqual(node.config["signaling"]["mode"], "websocket")
