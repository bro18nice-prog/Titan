"""Integrare locală cu luminile din Home Assistant sau LEDVANCE/Tuya.

TITAN nu caută automat dispozitive în rețea și nu trimite date în cloud. Este
activat numai dacă utilizatorul creează `smart_home.json` local, din exemplu.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class SmartHomeActions:
    CONFIG_PATH = Path("smart_home.json")
    COLOR_MAP = {
        "red": [255, 45, 45],
        "blue": [45, 105, 255],
        "green": [45, 220, 115],
        "purple": [170, 70, 255],
        "yellow": [255, 205, 50],
        "white": [255, 255, 255],
        "warm_white": [255, 170, 95],
        "cool_white": [205, 225, 255],
    }

    def control(self, arguments: dict[str, str | int]) -> str:
        config = self._load_config()
        if not config:
            return (
                "Luminile nu sunt configurate încă. Creează smart_home.json din "
                "un fișier exemplu, apoi conectăm TITAN local."
            )
        provider = config.get("provider")
        if provider == "tuya_local":
            return self._control_tuya_local(config, arguments)
        if provider != "home_assistant":
            return "Providerul de lumini nu este suportat. Alege home_assistant sau tuya_local."

        room = str(arguments.get("room", "all"))
        entity_id = config.get("entities", {}).get(room)
        if not entity_id:
            return f"Nu există o lumină configurată pentru «{room}»."

        operation = str(arguments["operation"])
        try:
            if operation == "off":
                self._call(config, "turn_off", entity_id, {})
                return f"Am stins luminile: {room}."

            payload: dict[str, Any] = {"entity_id": entity_id}
            if operation == "brightness":
                percent = int(arguments["percent"])
                payload["brightness_pct"] = percent
            elif operation == "color":
                payload["rgb_color"] = self.COLOR_MAP[str(arguments["color"])]
            self._call(config, "turn_on", entity_id, payload)
        except RuntimeError as error:
            return str(error)
        if operation == "brightness":
            return f"Am pus luminile {room} la {arguments['percent']}%."
        if operation == "color":
            return f"Am schimbat culoarea luminilor {room}."
        return f"Am aprins luminile: {room}."

    def _load_config(self) -> dict[str, Any] | None:
        if not self.CONFIG_PATH.is_file():
            return None
        try:
            data = json.loads(self.CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        provider = data.get("provider")
        if provider == "home_assistant" and (
            not data.get("url") or not data.get("token") or not data.get("entities")
        ):
            return None
        if provider == "tuya_local" and not data.get("entities"):
            return None
        return data if provider in {"home_assistant", "tuya_local"} else None

    def _control_tuya_local(self, config: dict[str, Any], arguments: dict[str, str | int]) -> str:
        """Controlează LEDVANCE Wi‑Fi direct în rețeaua locală.

        Datele de conectare sunt cheile locale ale becurilor; acestea rămân
        exclusiv în smart_home.json, care este ignorat de Git.
        """
        try:
            import tinytuya
        except ImportError:
            return "Lipsește modulul pentru becurile locale. Rulează: pip install tinytuya"

        room = str(arguments.get("room", "all"))
        entities = config["entities"]
        if room == "all":
            targets = [(name, item) for name, item in entities.items() if name != "all"]
        else:
            item = entities.get(room)
            targets = [(room, item)] if isinstance(item, dict) else []
        if not targets:
            return f"Nu există un bec configurat pentru «{room}»."

        operation = str(arguments["operation"])
        try:
            for _, details in targets:
                device = tinytuya.BulbDevice(
                    str(details["device_id"]),
                    address=str(details["ip"]),
                    local_key=str(details["local_key"]),
                    version=float(details.get("version", 3.3)),
                    # Fiecare comandă mobile este independentă. O conexiune
                    # persistentă lăsată de un request care a eșuat poate
                    # bloca următoarele comenzi şi nu ajută pe un singur bec.
                    persist=False,
                )
                # Răspuns rapid şi sincer: nu aşteptăm zeci de secunde după
                # un IP vechi sau un bec deconectat de la Wi-Fi.
                device.set_socketTimeout(2)
                device.set_socketRetryLimit(1)
                device.set_socketRetryDelay(0)
                if operation == "off":
                    result = device.turn_off()
                elif operation == "brightness":
                    result = device.set_brightness_percentage(int(arguments["percent"]))
                elif operation == "color":
                    result = device.set_colour(*self.COLOR_MAP[str(arguments["color"])])
                else:
                    result = device.turn_on()

                self._assert_tuya_success(result)
                # TinyTuya poate întoarce o eroare în dicționar fără să ridice
                # o excepție. Mai cerem starea reală înainte să spunem că
                # acțiunea s-a terminat, ca aplicația mobilă să nu mintă.
                device_status = self._assert_tuya_success(device.status())
                if operation in {"on", "off"}:
                    self._assert_power_state(
                        device_status,
                        expected_on=operation == "on",
                        power_dps=str(details.get("power_dps", "20")),
                    )
        except (KeyError, OSError, RuntimeError, ValueError) as error:
            return f"Nu pot confirma acțiunea pentru becul {room}. {error}"

        if operation == "off":
            return f"Am stins luminile: {room}."
        if operation == "brightness":
            return f"Am pus luminile {room} la {arguments['percent']}%."
        if operation == "color":
            return f"Am schimbat culoarea luminilor {room}."
        return f"Am aprins luminile: {room}."

    @staticmethod
    def _assert_tuya_success(response: Any) -> dict[str, Any]:
        """Normalizează răspunsurile TinyTuya şi opreşte confirmările false."""
        if not isinstance(response, dict):
            raise RuntimeError("Becul nu a trimis un răspuns valid.")
        if response.get("Error") or response.get("Err"):
            raise RuntimeError("Becul nu a răspuns local; verificăm IP-ul sau cheia lui.")
        return response

    @staticmethod
    def _assert_power_state(response: dict[str, Any], *, expected_on: bool, power_dps: str) -> None:
        dps = response.get("dps")
        if not isinstance(dps, dict) or power_dps not in dps:
            raise RuntimeError("Nu pot verifica starea de pornire a becului.")
        if bool(dps[power_dps]) is not expected_on:
            state = "aprins" if dps[power_dps] else "stins"
            raise RuntimeError(f"Becul raportează că este încă {state}.")

    @staticmethod
    def _call(config: dict[str, Any], service: str, entity_id: str, payload: dict[str, Any]) -> None:
        payload.setdefault("entity_id", entity_id)
        url = str(config["url"]).rstrip("/") + f"/api/services/light/{service}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {config['token']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=4) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"Home Assistant a răspuns cu {response.status}.")
        except URLError as error:
            raise RuntimeError("Nu pot ajunge la Home Assistant local.") from error
