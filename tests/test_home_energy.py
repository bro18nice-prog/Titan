"""Teste pentru prize, consum și endpoint-urile Casa (cu dispozitive simulate)."""

from datetime import datetime, timedelta, timezone
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from titan.mobile.server import create_app
from titan.tools.energy import EnergySampler, EnergyStore, period_edges, summarize
from titan.tools.home_devices import HomeDevices


class FakeDevice:
    registry: dict[str, dict] = {}

    def __init__(self, details, kind) -> None:
        self.state = self.registry.setdefault(
            details["device_id"], {"1": False, "20": False, "19": 0, "online": True}
        )
        self.kind = kind

    def _check(self):
        if not self.state["online"]:
            return {"Error": "Timeout", "Err": "914"}
        return None

    def status(self):
        return self._check() or {"dps": {k: v for k, v in self.state.items() if k != "online"}}

    def turn_on(self, switch=None):
        self.state["20" if self.kind == "light" else str(switch or 1)] = True
        return self.status()

    def turn_off(self, switch=None):
        self.state["20" if self.kind == "light" else str(switch or 1)] = False
        return self.status()

    def set_brightness_percentage(self, percent):
        self.state["bright"] = percent
        return self.status()


def make_home(tmp: Path) -> HomeDevices:
    FakeDevice.registry = {}
    config = {
        "provider": "tuya_local",
        "entities": {
            "all": "ignorat",
            "hol": {"device_id": "b1", "ip": "1.1.1.1", "local_key": "k", "power_dps": "20", "label": "Hol"},
            "tv": {"type": "plug", "label": "TV", "device_id": "p1", "ip": "1.1.1.2", "local_key": "k"},
            "incomplet": {"type": "plug", "device_id": "p2"},
        },
    }
    path = tmp / "smart_home.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return HomeDevices(path, factory=FakeDevice)


class EnergyTests(unittest.TestCase):
    def test_integrates_constant_power(self) -> None:
        store = EnergyStore(":memory:")
        for minute in range(0, 61):  # 1 oră la 100 W = 0,1 kWh
            store.record("tv", 100, ts=1_000_000 + minute * 60)
        self.assertAlmostEqual(store.kwh_between("tv", 1_000_000, 1_000_000 + 3601), 0.1, places=4)

    def test_gaps_are_not_counted(self) -> None:
        store = EnergyStore(":memory:")
        store.record("tv", 1000, ts=1_000_000)
        store.record("tv", 1000, ts=1_000_000 + 3600)  # Pi oprit o oră
        self.assertEqual(store.kwh_between("tv", 1_000_000, 1_010_000), 0)

    def test_rejects_absurd_readings(self) -> None:
        store = EnergyStore(":memory:")
        store.record("tv", -5, ts=1)
        store.record("tv", 1e9, ts=2)
        self.assertIsNone(store.latest_watts("tv", now=3))

    def test_period_edges(self) -> None:
        now = datetime(2026, 10, 12, 17, 30, tzinfo=timezone(timedelta(hours=3)))
        self.assertEqual(len(period_edges("day", now)), 25)
        self.assertEqual(len(period_edges("week", now)), 8)
        self.assertEqual(len(period_edges("month", now)), 13)  # 1-12 oct
        with self.assertRaises(ValueError):
            period_edges("an", now)

    def test_summary_per_device_and_total(self) -> None:
        store = EnergyStore(":memory:")
        now = datetime(2026, 10, 12, 17, 30, tzinfo=timezone(timedelta(hours=3)))
        base = datetime(2026, 10, 12, 10, 0, tzinfo=now.tzinfo).timestamp()
        for i in range(0, 61):
            store.record("tv", 200, ts=base + i * 60)
        result = summarize(store, {"tv": "TV"}, "day", now)
        self.assertAlmostEqual(result["total_kwh"], 0.2, places=2)
        self.assertEqual(result["per_device"][0]["label"], "TV")
        self.assertEqual(len(result["series"]), 24)

    def test_sampler_survives_read_errors(self) -> None:
        store = EnergyStore(":memory:")
        calls = []

        def read():
            calls.append(1)
            if len(calls) == 1:
                raise OSError("rețea")
            return {"tv": 50.0}

        sampler = EnergySampler(read, store)
        sampler.tick()
        sampler.tick()
        self.assertEqual(store.latest_watts("tv"), 50.0)


class HomeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.home = make_home(Path(self._dir.name))
        self.store = EnergyStore(":memory:")
        self.client = TestClient(
            create_app(access_token="tok", home=self.home, energy=self.store)
        )
        self.auth = {"Authorization": "Bearer tok"}

    def test_requires_token(self) -> None:
        for method, path in [("get", "/api/home/devices"), ("get", "/api/home/energy"),
                             ("post", "/api/home/devices/tv/power")]:
            self.assertEqual(getattr(self.client, method)(path).status_code, 401)

    def test_lists_only_valid_devices(self) -> None:
        data = self.client.get("/api/home/devices", headers=self.auth).json()
        self.assertTrue(data["configured"])
        self.assertEqual([d["id"] for d in data["devices"]], ["hol", "tv"])

    def test_toggle_plug_and_verify(self) -> None:
        r = self.client.post("/api/home/devices/tv/power", json={"on": True}, headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["on"])
        listed = {d["id"]: d for d in self.client.get("/api/home/devices", headers=self.auth).json()["devices"]}
        self.assertTrue(listed["tv"]["on"])

    def test_unknown_device_is_404(self) -> None:
        r = self.client.post("/api/home/devices/necunoscut/power", json={"on": True}, headers=self.auth)
        self.assertEqual(r.status_code, 404)

    def test_offline_device_gives_honest_error(self) -> None:
        self.client.get("/api/home/devices", headers=self.auth)  # creează starea
        FakeDevice.registry["p1"]["online"] = False
        r = self.client.post("/api/home/devices/tv/power", json={"on": True}, headers=self.auth)
        self.assertEqual(r.status_code, 502)
        listed = {d["id"]: d for d in self.client.get("/api/home/devices", headers=self.auth).json()["devices"]}
        self.assertFalse(listed["tv"]["online"])

    def test_brightness_validation(self) -> None:
        ok = self.client.post("/api/home/devices/hol/brightness", json={"percent": 40}, headers=self.auth)
        self.assertEqual(ok.status_code, 200)
        bad = self.client.post("/api/home/devices/hol/brightness", json={"percent": 500}, headers=self.auth)
        self.assertEqual(bad.status_code, 422)
        plug = self.client.post("/api/home/devices/tv/brightness", json={"percent": 40}, headers=self.auth)
        self.assertEqual(plug.status_code, 502)

    def test_watts_are_scaled_and_sampled(self) -> None:
        self.client.get("/api/home/devices", headers=self.auth)
        FakeDevice.registry["p1"]["19"] = 853  # 85,3 W
        self.assertEqual(self.home.read_watts(), {"tv": 85.3})
        EnergySampler(self.home.read_watts, self.store).tick()
        data = self.client.get("/api/home/energy?range=day", headers=self.auth).json()
        self.assertEqual(data["watts_now"], 85.3)
        self.assertEqual(data["metered_devices"], 1)

    def test_energy_range_validated(self) -> None:
        r = self.client.get("/api/home/energy?range=an", headers=self.auth)
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
