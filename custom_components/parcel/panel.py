"""The Packages sidebar panel and the live data it receives."""

from __future__ import annotations

import asyncio
from collections import Counter
import hashlib
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .accounts import loaded_coordinators
from .const import (
    DATA_PANEL,
    DATA_PANEL_LOCK,
    DATA_STATIC,
    DATA_SUBSCRIBERS,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    STATIC_URL,
)
from .models import ICON_CHOICES, ICON_RULES

FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_JS = "parcel-panel.js"

# Suggested first in the carrier picker for people in the US.
US_CARRIERS = ("usps", "ups", "fedex", "amzlus", "dhl", "ont")


def _file_version(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return "missing"


def panel_config() -> dict[str, Any]:
    """What the panel is given once, when it loads: things that never change while running."""
    return {
        "static_url": STATIC_URL,
        "icon_rules": [{"pattern": pattern, "icon": icon} for pattern, icon in ICON_RULES],
        "icon_choices": list(ICON_CHOICES),
    }


async def async_register_panel(hass: HomeAssistant) -> None:
    """Add the Packages panel to the sidebar (once, for all accounts).

    Accounts set up at the same time, so the lock makes sure only one of them
    registers the panel; the others find it already there.
    """
    lock: asyncio.Lock = hass.data.setdefault(DATA_PANEL_LOCK, asyncio.Lock())
    async with lock:
        if hass.data.get(DATA_PANEL):
            return
        if not hass.data.get(DATA_STATIC):
            await hass.http.async_register_static_paths(
                [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=True)]
            )
            hass.data[DATA_STATIC] = True
        version = await hass.async_add_executor_job(_file_version, FRONTEND_DIR / PANEL_JS)
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            module_url=f"{STATIC_URL}/{PANEL_JS}?v={version}",
            require_admin=False,
            config=panel_config(),
        )
        hass.data[DATA_PANEL] = True


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the panel when no account is loaded."""
    if hass.data.pop(DATA_PANEL, False):
        frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)


def panel_payload(hass: HomeAssistant, exclude: str | None = None) -> dict[str, Any]:
    """Everything the panel shows, across all loaded accounts."""
    return {
        "entries": [
            coordinator.panel_state()
            for coordinator in loaded_coordinators(hass)
            if coordinator.config_entry.entry_id != exclude
        ]
    }


def suggested_carriers(hass: HomeAssistant) -> list[str]:
    """Carriers this household uses most, then common ones for the country."""
    used: Counter[str] = Counter()
    for coordinator in loaded_coordinators(hass):
        if coordinator.data is not None:
            used.update(d.carrier_code for d in coordinator.data.deliveries.values())
    suggestions = [code for code, _count in used.most_common(6)]
    if hass.config.country == "US":
        suggestions += [code for code in US_CARRIERS if code not in suggestions]
    return suggestions


@callback
def async_notify_panel(hass: HomeAssistant, exclude: str | None = None) -> None:
    """Send fresh data to every open panel."""
    subscribers = hass.data.get(DATA_SUBSCRIBERS)
    if not subscribers:
        return
    payload = panel_payload(hass, exclude)
    for send in list(subscribers):
        send(payload)
