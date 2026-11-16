"""The bundled blueprints load in Home Assistant, and their messages read naturally."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.util.yaml.loader import load_yaml_dict

from .test_init import setup

FOLDER = Path(__file__).parent.parent / "blueprints" / "automation" / "parcel"
BLUEPRINTS = sorted(FOLDER.glob("*.yaml"))


def test_the_blueprints_are_all_here() -> None:
    assert [path.name for path in BLUEPRINTS] == [
        "morning_briefing.yaml",
        "needs_attention.yaml",
        "notify_delivered.yaml",
    ]


@pytest.mark.parametrize("path", BLUEPRINTS, ids=lambda path: path.stem)
def test_blueprint_is_one_home_assistant_accepts(path: Path) -> None:
    blueprint = Blueprint(
        load_yaml_dict(str(path)),
        path=str(path),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    assert blueprint.name.startswith("Parcel - ")
    # The link people paste to import it points at this very file.
    assert blueprint.metadata["source_url"].endswith(f"/blueprints/automation/parcel/{path.name}")
    assert blueprint.inputs


async def test_the_morning_briefing_reads_naturally(
    hass: HomeAssistant,
    mock_parcel: SimpleNamespace,
    config_entry: MockConfigEntry,
    deliveries: list,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Several packages are listed by name; a single one isn't named twice."""
    freezer.move_to("2026-11-16 15:00:00+00:00")
    await hass.config.async_set_time_zone("America/New_York")
    await setup(hass, config_entry)
    message = load_yaml_dict(str(FOLDER / "morning_briefing.yaml"))["actions"][0]["message"]
    variables = {"arriving": "sensor.parcel_arriving_today"}

    assert hass.states.get("sensor.parcel_arriving_today").state == "2"
    assert Template(message, hass).async_render(variables) == (
        "2 packages arrive today: Dog food and Coffee grinder"
    )

    deliveries[-1]["date_expected"] = "2026-11-17 00:00:00"  # dog food comes tomorrow
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.parcel_arriving_today").state == "1"
    assert Template(message, hass).async_render(variables) == "Coffee grinder arrives today"
