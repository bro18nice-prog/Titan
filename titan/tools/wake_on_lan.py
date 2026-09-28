"""Pornirea responsabilă a laptopului prin Wake-on-LAN.

Raspberry Pi trimite numai un pachet standard Wake-on-LAN în rețeaua locală.
Nu deschidem porturi spre internet: telefonul va vorbi doar cu TITAN Hub, iar
Hub-ul trimite pachetul din interiorul casei.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import socket
from typing import Any


class WakeOnLanActions:
    CONFIG_PATH = Path("laptop.json")
    MAC_PATTERN = re.compile(r"^[0-9A-Fa-f]{2}([:-]?[0-9A-Fa-f]{2}){5}$")

    def wake(self) -> str:
        config = self._load_config()
        if not config:
            return (
                "Pornirea laptopului nu este configurată încă. Când montăm TITAN pe Raspberry Pi, "
                "completăm laptop.json cu adresa MAC a laptopului și activăm Wake-on-LAN."
            )

        try:
            packet = self.magic_packet(str(config["mac_address"]))
            broadcast_address = str(config.get("broadcast_address", "255.255.255.255"))
            port = int(config.get("port", 9))
            if not 1 <= port <= 65535:
                raise ValueError("port invalid")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as connection:
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                connection.sendto(packet, (broadcast_address, port))
        except (OSError, ValueError, KeyError):
            return "Nu am putut trimite Wake-on-LAN. Verificăm configurația locală a laptopului."
        return "Am trimis semnalul de pornire către laptop. Așteaptă aproximativ un minut."

    @classmethod
    def _load_config(cls) -> dict[str, Any] | None:
        if not cls.CONFIG_PATH.is_file():
            return None
        try:
            config = json.loads(cls.CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        mac_address = config.get("mac_address")
        if not isinstance(mac_address, str) or not cls.MAC_PATTERN.fullmatch(mac_address):
            return None
        return config

    @classmethod
    def magic_packet(cls, mac_address: str) -> bytes:
        """Construiește pachetul standard: 6 octeți FF + MAC repetat de 16 ori."""
        if not cls.MAC_PATTERN.fullmatch(mac_address):
            raise ValueError("Adresa MAC nu este validă.")
        mac = bytes.fromhex(re.sub(r"[:-]", "", mac_address))
        return b"\xff" * 6 + mac * 16
