"""Prize și becuri Tuya, controlate local (fără cloud) pentru aplicația mobilă.

Folosește același ``smart_home.json`` ca restul TITAN. Fiecare intrare din
``entities`` este un bec (implicit) sau o priză, dacă are ``"type": "plug"``.
Pentru prize: ``switch_dps`` (implicit "1"), ``power_dps`` (implicit "19", W×10)
și ``power_scale`` (implicit 0.1). Cheile locale rămân în fișierul ignorat de Git.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any, Callable


class HomeError(RuntimeError):
    """Eroare afișabilă utilizatorului."""


def _default_factory(details: dict[str, Any], kind: str) -> Any:
    try:
        import tinytuya
    except ImportError as error:
        raise HomeError("Lipsește modulul tinytuya. Rulează: pip install tinytuya") from error
    cls = tinytuya.BulbDevice if kind == "light" else tinytuya.OutletDevice
    device = cls(
        str(details["device_id"]),
        address=str(details["ip"]),
        local_key=str(details["local_key"]),
        version=float(details.get("version", 3.3)),
        persist=False,
    )
    device.set_socketTimeout(2)
    device.set_socketRetryLimit(1)
    device.set_socketRetryDelay(0)
    return device


class HomeDevices:
    def __init__(
        self,
        config_path: str | Path = "smart_home.json",
        factory: Callable[[dict[str, Any], str], Any] = _default_factory,
    ) -> None:
        self._path = Path(config_path)
        self._factory = factory
        # Un dispozitiv Tuya acceptă o singură conexiune locală odată.
        self._io = RLock()

    # ---- configurare -------------------------------------------------
    def _config(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if data.get("provider") != "tuya_local":
            return {}
        items = {}
        for name, details in (data.get("entities") or {}).items():
            if name == "all" or not isinstance(details, dict):
                continue
            if not all(details.get(key) for key in ("device_id", "ip", "local_key")):
                continue
            kind = "plug" if details.get("type") == "plug" else "light"
            items[str(name)] = {**details, "_kind": kind}
        return items

    def configured(self) -> bool:
        return bool(self._config())

    def meters(self) -> dict[str, str]:
        """Prizele care raportează putere: {id: etichetă}."""
        return {
            name: str(d.get("label", name))
            for name, d in self._config().items()
            if d["_kind"] == "plug" and d.get("power_dps", "19")
        }

    # ---- citire / comandă --------------------------------------------
    @staticmethod
    def _dps(status: Any) -> dict[str, Any]:
        if not isinstance(status, dict) or status.get("Error") or status.get("Err"):
            raise HomeError("Dispozitivul nu a răspuns local.")
        dps = status.get("dps")
        if not isinstance(dps, dict):
            raise HomeError("Răspuns invalid de la dispozitiv.")
        return dps

    @staticmethod
    def _switch_key(details: dict[str, Any]) -> str:
        if details["_kind"] == "plug":
            return str(details.get("switch_dps", "1"))
        return str(details.get("power_dps", "20"))

    @staticmethod
    def _watts(details: dict[str, Any], dps: dict[str, Any]) -> float | None:
        if details["_kind"] != "plug":
            return None
        raw = dps.get(str(details.get("power_dps", "19")))
        if raw is None:
            return None
        try:
            return round(float(raw) * float(details.get("power_scale", 0.1)), 1)
        except (TypeError, ValueError):
            return None

    def _read(self, details: dict[str, Any]) -> dict[str, Any]:
        device = self._factory(details, details["_kind"])
        dps = self._dps(device.status())
        on = dps.get(self._switch_key(details))
        return {"on": bool(on) if on is not None else None, "watts": self._watts(details, dps)}

    def snapshot(self) -> list[dict[str, Any]]:
        result = []
        for name, details in self._config().items():
            entry: dict[str, Any] = {
                "id": name,
                "label": str(details.get("label", name)),
                "kind": details["_kind"],
                "online": False,
                "on": None,
                "watts": None,
            }
            with self._io:
                try:
                    entry.update(self._read(details), online=True)
                except (HomeError, OSError, ValueError, KeyError):
                    pass
            result.append(entry)
        return result

    def read_watts(self) -> dict[str, float]:
        readings = {}
        for name in self.meters():
            details = self._config()[name]
            with self._io:
                try:
                    watts = self._read(details)["watts"]
                except (HomeError, OSError, ValueError, KeyError):
                    continue
            if watts is not None:
                readings[name] = watts
        return readings

    def _details(self, device_id: str) -> dict[str, Any]:
        details = self._config().get(device_id)
        if details is None:
            raise KeyError(device_id)
        return details

    def set_power(self, device_id: str, on: bool) -> dict[str, Any]:
        details = self._details(device_id)
        with self._io:
            try:
                device = self._factory(details, details["_kind"])
                if details["_kind"] == "plug":
                    switch = int(self._switch_key(details))
                    self._dps(device.turn_on(switch=switch) if on else device.turn_off(switch=switch))
                else:
                    self._dps(device.turn_on() if on else device.turn_off())
                state = self._read(details)
            except (OSError, ValueError, KeyError) as error:
                raise HomeError(f"Nu pot comanda «{device_id}». {error}") from error
        if state["on"] is not on:
            raise HomeError(f"«{device_id}» nu a confirmat comanda.")
        return {"id": device_id, **state}

    def set_brightness(self, device_id: str, percent: int) -> None:
        details = self._details(device_id)
        if details["_kind"] != "light":
            raise HomeError("Luminozitatea se poate regla doar la becuri.")
        if not 1 <= percent <= 100:
            raise HomeError("Luminozitatea trebuie să fie între 1 și 100.")
        with self._io:
            try:
                device = self._factory(details, "light")
                self._dps(device.set_brightness_percentage(percent))
            except (OSError, ValueError, KeyError) as error:
                raise HomeError(f"Nu pot regla «{device_id}». {error}") from error
