"""Răspuns vocal prin vocile instalate în Windows."""

from __future__ import annotations


class Speaker:
    def __init__(self) -> None:
        self._engine = None

    def say(self, text: str) -> None:
        """Spune textul fără a opri TITAN dacă TTS nu este disponibil."""
        try:
            if self._engine is None:
                import pyttsx3

                self._engine = pyttsx3.init()
                self._choose_romanian_voice_when_available()
                self._engine.setProperty("rate", 180)
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            # Textul este deja afișat în terminal; vocea nu trebuie să blocheze o comandă.
            return

    def _choose_romanian_voice_when_available(self) -> None:
        for voice in self._engine.getProperty("voices"):
            description = f"{voice.id} {voice.name}".lower()
            if "ro-ro" in description or "romanian" in description or "romana" in description:
                self._engine.setProperty("voice", voice.id)
                return
