"""Contorizarea consumului: măsurători salvate local, în SQLite.

Prizele raportează puterea instantanee (W). TITAN o citește la fiecare minut
și o salvează pe Raspberry Pi; energia (kWh) se calculează apoi prin integrare.
Nimic nu pleacă în cloud.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from threading import Event, Lock, Thread
import time
from typing import Callable, Iterable

# Dacă între două măsurători trece mai mult, nu știm ce s-a întâmplat
# (Pi oprit, priză offline) și intervalul nu se numără.
MAX_GAP_SECONDS = 300
RETENTION_DAYS = 400


class EnergyStore:
    def __init__(self, path: str | Path = "data/energy.db") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._db = sqlite3.connect(self._path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS samples (ts INTEGER NOT NULL, device TEXT NOT NULL, watts REAL NOT NULL)"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS samples_device_ts ON samples (device, ts)")
        self._db.commit()

    def record(self, device: str, watts: float, ts: float | None = None) -> None:
        if not (0 <= watts < 100_000):  # respinge valori absurde de la senzor
            return
        with self._lock:
            self._db.execute(
                "INSERT INTO samples (ts, device, watts) VALUES (?, ?, ?)",
                (int(ts if ts is not None else time.time()), device, float(watts)),
            )
            self._db.commit()

    def prune(self, now: float | None = None) -> None:
        cutoff = int((now if now is not None else time.time()) - RETENTION_DAYS * 86400)
        with self._lock:
            self._db.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
            self._db.commit()

    def latest_watts(self, device: str, now: float | None = None, max_age: int = 180) -> float | None:
        now = now if now is not None else time.time()
        with self._lock:
            row = self._db.execute(
                "SELECT ts, watts FROM samples WHERE device = ? ORDER BY ts DESC LIMIT 1", (device,)
            ).fetchone()
        if not row or now - row[0] > max_age:
            return None
        return float(row[1])

    def kwh_between(self, device: str, start: float, end: float) -> float:
        """kWh pentru intervalele care încep în [start, end), prin trapez."""
        with self._lock:
            rows = self._db.execute(
                "SELECT ts, watts FROM samples WHERE device = ? AND ts >= ? AND ts < ? ORDER BY ts",
                (device, int(start), int(end) + MAX_GAP_SECONDS),
            ).fetchall()
        wh = 0.0
        for (t1, w1), (t2, w2) in zip(rows, rows[1:]):
            if t1 >= end:
                break
            dt = t2 - t1
            if 0 < dt <= MAX_GAP_SECONDS:
                wh += (w1 + w2) / 2 * dt / 3600
        return wh / 1000

    def total_kwh(self, devices: Iterable[str], start: float, end: float) -> float:
        return sum(self.kwh_between(d, start, end) for d in devices)


def _local_midnight(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def period_edges(kind: str, now: datetime) -> list[datetime]:
    """Marginile intervalelor (ora locală): zi → ore, săptămână/lună → zile."""
    midnight = _local_midnight(now)
    if kind == "day":
        start, step, count = midnight, timedelta(hours=1), 24
    elif kind == "week":
        start, step, count = midnight - timedelta(days=6), timedelta(days=1), 7
    elif kind == "month":
        start = midnight.replace(day=1)
        step, count = timedelta(days=1), (midnight - start).days + 1
    else:
        raise ValueError("Perioadă necunoscută.")
    edges = []
    for i in range(count + 1):
        if kind == "day":
            edges.append(start + i * step)
        else:  # zile calendaristice, corecte și la schimbarea orei
            edges.append(_local_midnight(start + timedelta(days=i, hours=12)))
    return edges


def summarize(store: EnergyStore, devices: dict[str, str], kind: str, now: datetime | None = None) -> dict:
    """Rezumat pentru UI. ``devices`` = {id: etichetă}."""
    now = now or datetime.now().astimezone()
    edges = period_edges(kind, now)
    series = []
    for a, b in zip(edges, edges[1:]):
        series.append({"t": a.isoformat(), "kwh": round(store.total_kwh(devices, a.timestamp(), b.timestamp()), 4)})
    per_device = []
    for device_id, label in devices.items():
        per_device.append(
            {
                "id": device_id,
                "label": label,
                "kwh": round(store.kwh_between(device_id, edges[0].timestamp(), edges[-1].timestamp()), 4),
                "watts": store.latest_watts(device_id, now.timestamp()),
            }
        )
    live = [d["watts"] for d in per_device if d["watts"] is not None]
    return {
        "range": kind,
        "watts_now": round(sum(live), 1) if live else None,
        "total_kwh": round(sum(item["kwh"] for item in series), 3),
        "series": series,
        "per_device": sorted(per_device, key=lambda item: item["kwh"], reverse=True),
    }


class EnergySampler:
    """Citește periodic puterea prizelor și o salvează."""

    def __init__(self, read: Callable[[], dict[str, float]], store: EnergyStore, interval: float = 60) -> None:
        self._read, self._store, self._interval = read, store, interval
        self._stop = Event()
        self._thread: Thread | None = None

    def tick(self) -> None:
        try:
            readings = self._read()
        except Exception:  # un ciclu eșuat nu trebuie să oprească contorizarea
            return
        for device, watts in readings.items():
            self._store.record(device, watts)

    def start(self) -> None:
        if self._thread:
            return
        self._thread = Thread(target=self._run, name="titan-energy", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        cycles = 0
        while not self._stop.is_set():
            self.tick()
            cycles += 1
            if cycles % 1440 == 0:
                self._store.prune()
            self._stop.wait(self._interval)
