"""Setări pentru funcțiile opționale, inclusiv API-ul plătit.

În versiunea actuală, API-ul rămâne complet dezactivat. Când îl activăm, aceste
limite vor fi verificate înainte ca TITAN să trimită audio sau text în cloud.
"""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ApiSettings:
    enabled: bool
    fallback_on_unknown_command: bool
    monthly_request_limit: int
    monthly_budget_eur: float


def load_api_settings() -> ApiSettings:
    return ApiSettings(
        enabled=os.getenv("TITAN_API_ENABLED", "false").lower() == "true",
        fallback_on_unknown_command=(
            os.getenv("TITAN_API_FALLBACK_ON_UNKNOWN_COMMAND", "false").lower() == "true"
        ),
        monthly_request_limit=int(os.getenv("TITAN_MONTHLY_REQUEST_LIMIT", "100")),
        monthly_budget_eur=float(os.getenv("TITAN_MONTHLY_BUDGET_EUR", "3.00")),
    )
