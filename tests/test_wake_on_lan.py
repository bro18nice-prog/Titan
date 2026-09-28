import unittest
from unittest.mock import MagicMock, patch

from titan.tools.wake_on_lan import WakeOnLanActions


class WakeOnLanTests(unittest.TestCase):
    def test_builds_standard_magic_packet(self) -> None:
        packet = WakeOnLanActions.magic_packet("AA:BB:CC:DD:EE:FF")
        self.assertEqual(len(packet), 102)
        self.assertEqual(packet[:6], b"\xff" * 6)
        self.assertEqual(packet[6:12], bytes.fromhex("AABBCCDDEEFF"))

    def test_rejects_invalid_mac_address(self) -> None:
        with self.assertRaises(ValueError):
            WakeOnLanActions.magic_packet("not-a-mac")

    @patch.object(WakeOnLanActions, "_load_config")
    @patch("titan.tools.wake_on_lan.socket.socket")
    def test_sends_packet_to_local_broadcast(self, socket_factory: MagicMock, load_config: MagicMock) -> None:
        load_config.return_value = {
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "broadcast_address": "192.168.50.255",
            "port": 9,
        }
        connection = socket_factory.return_value.__enter__.return_value

        response = WakeOnLanActions().wake()

        self.assertIn("Am trimis", response)
        connection.sendto.assert_called_once_with(
            WakeOnLanActions.magic_packet("AA:BB:CC:DD:EE:FF"),
            ("192.168.50.255", 9),
        )
