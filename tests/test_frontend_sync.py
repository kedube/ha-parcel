"""Things written down in two places agree: the panel and Python, the code and its words."""

from __future__ import annotations

import json
from pathlib import Path
import re

from custom_components.parcel.changes import STATUS_EVENTS
from custom_components.parcel.const import (
    CONF_ACCOUNT_TOKEN,
    CONF_PACKAGE_SENSORS,
    CONF_REMOVE_ACCOUNT_TOKEN,
    CONF_SCAN_INTERVAL,
    EVENT_TYPES,
)
from custom_components.parcel.device_trigger import TRIGGERS
from custom_components.parcel.models import (
    DEFAULT_ICON,
    ICON_CHOICES,
    ICON_RULES,
    STATUS_OPTIONS,
    STATUS_SLUGS,
)

ICONS_JS = Path(__file__).parent.parent / "frontend-src" / "src" / "icons.js"


def test_panel_knows_every_icon() -> None:
    """Every icon in the rules and choices has artwork in the panel."""
    source = ICONS_JS.read_text(encoding="utf-8")
    block = source.split("const ITEM_ICONS = {", 1)[1].split("};", 1)[0]
    panel_icons = set(re.findall(r"'(mdi:[a-z0-9-]+)'", block))
    wanted = {DEFAULT_ICON, *ICON_CHOICES, *(icon for _pattern, icon in ICON_RULES)}
    assert wanted <= panel_icons, sorted(wanted - panel_icons)


def test_patterns_work_in_javascript_too() -> None:
    """Rules avoid Python-only regex syntax, since the panel reuses them."""
    for pattern, _icon in ICON_RULES:
        assert (
            "(?P" not in pattern
            and "(?<" not in pattern
            and "\\A" not in pattern
            and "\\Z" not in pattern
        )


# Things that are written down in more than one place must agree -------------

ROOT = Path(__file__).parent.parent
COMPONENT = ROOT / "custom_components" / "parcel"
LOGIC_JS = ROOT / "frontend-src" / "src" / "logic.js"


def _strings() -> dict:
    return json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))


def test_translations_are_a_copy_of_strings() -> None:
    """Home Assistant reads translations/en.json; strings.json is where edits are made."""
    assert (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8") == (
        COMPONENT / "strings.json"
    ).read_text(encoding="utf-8")


def test_the_panel_has_words_for_every_status() -> None:
    """Parcel's statuses are named in Python, shown by the panel, and translated for sensors."""
    slugs = set(STATUS_SLUGS.values())
    source = LOGIC_JS.read_text(encoding="utf-8")
    block = source.split("export const STATUS = {", 1)[1].split("\n};", 1)[0]
    panel = dict(re.findall(r"^  (\w+): \{.*?icon: '(\w+)'", block, flags=re.MULTILINE))
    assert set(panel) == slugs

    icons_block = ICONS_JS.read_text(encoding="utf-8").split("export const ICON = {", 1)[1]
    drawn = set(re.findall(r"^  (\w+): mdi", icons_block.split("\n};", 1)[0], flags=re.MULTILINE))
    assert set(panel.values()) <= drawn, sorted(set(panel.values()) - drawn)

    assert set(_strings()["entity"]["sensor"]["package"]["state"]) == slugs
    assert STATUS_EVENTS.keys() == STATUS_SLUGS.keys()
    assert set(STATUS_OPTIONS) == slugs


def test_every_event_type_is_translated_and_offered() -> None:
    states = _strings()["entity"]["event"]["package_update"]["state_attributes"]["event_type"]
    assert set(states["state"]) == set(EVENT_TYPES)
    assert set(STATUS_EVENTS.values()) <= set(EVENT_TYPES)
    triggers = _strings()["device_automation"]["trigger_type"]
    assert set(triggers) == set(TRIGGERS)
    assert {kind for kind in TRIGGERS.values() if kind} <= set(EVENT_TYPES)


def test_every_message_the_code_asks_for_exists() -> None:
    """A translation key used in Python has a sentence in strings.json."""
    strings = _strings()
    known = (
        set(strings["exceptions"])
        | set(strings["issues"])
        | set(strings["entity"]["sensor"])
        | set(strings["entity"]["event"])
        | set(strings["entity"]["button"])
    )
    used: set[str] = set()
    for path in COMPONENT.glob("*.py"):
        used |= set(re.findall(r'translation_key="(\w+)"', path.read_text(encoding="utf-8")))
    assert used <= known, sorted(used - known)
    # Keys passed along in a variable: the two reasons checks are put off.
    assert {"rate_limited", "hourly_limit"} <= set(strings["exceptions"])
    # And nothing is left over that no code refers to.
    exceptions_used = used | {"rate_limited", "hourly_limit"}
    assert set(strings["exceptions"]) <= exceptions_used, sorted(
        set(strings["exceptions"]) - exceptions_used
    )


def test_every_form_field_and_error_is_labelled() -> None:
    strings = _strings()
    options = strings["options"]["step"]["init"]
    fields = {
        CONF_SCAN_INTERVAL,
        CONF_PACKAGE_SENSORS,
        CONF_ACCOUNT_TOKEN,
        CONF_REMOVE_ACCOUNT_TOKEN,
    }
    assert set(options["data"]) == fields
    assert set(options["data_description"]) == fields
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    errors = set(re.findall(r'return "(\w+)"', source))
    sign_in_only = {"invalid_account_token", "account_token_other_account"}
    assert errors == {"invalid_auth", "rate_limited", "cannot_connect", "unknown", *sign_in_only}
    assert errors - sign_in_only <= set(strings["config"]["error"])
    assert errors - {"invalid_auth"} <= set(strings["options"]["error"])
