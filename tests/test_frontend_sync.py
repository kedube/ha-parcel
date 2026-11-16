"""The panel must be able to draw every icon the integration can choose."""

from __future__ import annotations

from pathlib import Path
import re

from custom_components.parcel.models import DEFAULT_ICON, ICON_CHOICES, ICON_RULES

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
