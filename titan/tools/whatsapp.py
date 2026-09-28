"""Contacte WhatsApp locale pentru TITAN.

Fișierul real contacts.json nu se trimite în Git și rămâne exclusiv pe laptop.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus
import unicodedata


def _normalise_alias(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").strip()


class WhatsAppContacts:
    CONFIG_PATH = Path("contacts.json")

    def phone_for(self, alias: str) -> str | None:
        if not self.CONFIG_PATH.is_file():
            return None
        try:
            contacts = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        phone = contacts.get(_normalise_alias(alias))
        if not isinstance(phone, str):
            return None
        # Linkurile WhatsApp acceptă doar format internațional, doar cifre.
        digits = "".join(character for character in phone if character.isdigit())
        return digits or None

    def draft_url(self, alias: str, message: str) -> str | None:
        phone = self.phone_for(alias)
        if not phone:
            return None
        return f"https://web.whatsapp.com/send?phone={phone}&text={quote_plus(message)}"
