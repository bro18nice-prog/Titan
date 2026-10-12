"""Serverul local pentru aplicația de telefon TITAN.

Acest modul este intenționat să ruleze pe Raspberry Pi. În dezvoltare rulează
doar pe ``127.0.0.1``; pentru acces extern îl vom publica exclusiv prin
Tailscale Serve, nu prin port-forwarding.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import secrets
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from titan.core.assistant import TitanAssistant
from titan.tools.energy import EnergySampler, EnergyStore, summarize
from titan.tools.home_devices import HomeDevices, HomeError


STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).parents[2]
# .env este ignorat de Git. Îl citim o singură dată, la pornirea serverului,
# pentru codul de asociere al telefonului; valoarea nu este logată niciodată.
load_dotenv(PROJECT_ROOT / ".env")


class CommandRequest(BaseModel):
    """O singură comandă text venită din aplicație."""

    text: str = Field(min_length=1, max_length=500)
    session_id: str | None = Field(default=None, max_length=80)


class PowerRequest(BaseModel):
    on: bool


class BrightnessRequest(BaseModel):
    percent: int = Field(ge=1, le=100)


class CommandResponse(BaseModel):
    response: str
    session_id: str


@dataclass
class _Session:
    assistant: TitanAssistant


class AssistantSessions:
    """Păstrează confirmările separat pentru fiecare telefon/sesiune.

    De exemplu, o confirmare WhatsApp pe telefon nu trebuie să poată confirma
    accidental o comandă pornită de la microfonul local.
    """

    def __init__(self, factory: Callable[[], TitanAssistant]) -> None:
        self._factory = factory
        self._sessions: dict[str, _Session] = {}
        self._lock = Lock()

    def assistant_for(self, session_id: str | None) -> tuple[str, TitanAssistant]:
        safe_id = (
            session_id
            if session_id and re.fullmatch(r"[A-Za-z0-9_-]{12,80}", session_id)
            else ""
        )
        if not safe_id:
            safe_id = secrets.token_urlsafe(24)

        with self._lock:
            session = self._sessions.get(safe_id)
            if session is None:
                # Limităm memoria în mod defensiv. Sesiunile nu conțin parole
                # sau mesaje salvate, ci doar o confirmare temporară.
                if len(self._sessions) >= 64:
                    self._sessions.pop(next(iter(self._sessions)))
                session = _Session(self._factory())
                self._sessions[safe_id] = session
        return safe_id, session.assistant


def _require_token(expected_token: str):
    """Cere token doar când aplicația este pregătită pentru Pi.

    În preview local tokenul poate lipsi. Nu permitem totuși pornirea pe o
    interfață de rețea fără acesta; verificarea este făcută în ``main``.
    """

    def verify(authorization: str | None = Header(default=None)) -> None:
        if not expected_token:
            return
        prefix = "Bearer "
        if not authorization or not authorization.startswith(prefix):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autentificare necesară.")
        supplied_token = authorization.removeprefix(prefix)
        if not secrets.compare_digest(supplied_token, expected_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid.")

    return verify


def create_app(
    *,
    assistant_factory: Callable[[], TitanAssistant] = TitanAssistant,
    access_token: str | None = None,
    home: HomeDevices | None = None,
    energy: EnergyStore | None = None,
    run_sampler: bool = False,
) -> FastAPI:
    """Creează aplicația fără a o publica în rețea.

    ``assistant_factory`` face serverul testabil și ne va permite ca, pe Pi,
    să folosim un executor pentru Home Assistant şi Laptop Agent.
    """

    token = access_token if access_token is not None else os.getenv("TITAN_MOBILE_ACCESS_TOKEN", "")
    sessions = AssistantSessions(assistant_factory)
    home = home or HomeDevices(PROJECT_ROOT / "smart_home.json")
    store = energy or EnergyStore(PROJECT_ROOT / "data" / "energy.db")
    sampler = EnergySampler(home.read_watts, store) if run_sampler else None

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if sampler and home.meters():
            sampler.start()
        yield
        if sampler:
            sampler.stop()

    app = FastAPI(title="TITAN Mobile", docs_url=None, redoc_url=None, lifespan=lifespan)
    authenticate = _require_token(token)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> FileResponse:
        return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/api/status", dependencies=[Depends(authenticate)])
    def get_status() -> dict[str, str | bool]:
        return {
            "name": "TITAN Hub",
            "mode": "protected" if token else "local_preview",
            "remote_ready": bool(token),
        }

    @app.post("/api/commands", response_model=CommandResponse, dependencies=[Depends(authenticate)])
    def run_command(command: CommandRequest) -> CommandResponse:
        session_id, assistant = sessions.assistant_for(command.session_id)
        response = assistant.handle(command.text.strip())
        return CommandResponse(response=response, session_id=session_id)

    @app.get("/api/home/devices", dependencies=[Depends(authenticate)])
    def home_devices() -> dict:
        return {"configured": home.configured(), "devices": home.snapshot()}

    @app.post("/api/home/devices/{device_id}/power", dependencies=[Depends(authenticate)])
    def home_power(device_id: str, request: PowerRequest) -> dict:
        try:
            return home.set_power(device_id, request.on)
        except KeyError:
            raise HTTPException(status_code=404, detail="Dispozitiv necunoscut.") from None
        except HomeError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @app.post("/api/home/devices/{device_id}/brightness", dependencies=[Depends(authenticate)])
    def home_brightness(device_id: str, request: BrightnessRequest) -> dict[str, bool]:
        try:
            home.set_brightness(device_id, request.percent)
        except KeyError:
            raise HTTPException(status_code=404, detail="Dispozitiv necunoscut.") from None
        except HomeError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        return {"ok": True}

    @app.get("/api/home/energy", dependencies=[Depends(authenticate)])
    def home_energy(range: str = Query("day", pattern="^(day|week|month)$")) -> dict:
        data = summarize(store, home.meters(), range)
        price = os.getenv("TITAN_KWH_PRICE", "").replace(",", ".")
        try:
            data["price_per_kwh"] = float(price) if price else None
        except ValueError:
            data["price_per_kwh"] = None
        data["currency"] = os.getenv("TITAN_CURRENCY", "lei")
        data["metered_devices"] = len(home.meters())
        return data

    # Imaginile aplicației sunt reutilizate din identitatea deja aleasă pentru
    # TITAN, fără duplicări inutile în proiect.
    app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app(run_sampler=True)


def main() -> None:
    """Pornește preview-ul local; pe Pi va fi pornit de systemd."""

    import uvicorn

    host = os.getenv("TITAN_MOBILE_HOST", "127.0.0.1")
    token = os.getenv("TITAN_MOBILE_ACCESS_TOKEN", "")
    if host not in {"127.0.0.1", "localhost", "::1"} and not token:
        raise RuntimeError(
            "Refuz pornirea pe rețea fără TITAN_MOBILE_ACCESS_TOKEN. "
            "Pe Raspberry Pi vom folosi Tailscale Serve peste 127.0.0.1."
        )
    uvicorn.run(app, host=host, port=int(os.getenv("TITAN_MOBILE_PORT", "8787")))


if __name__ == "__main__":
    main()
