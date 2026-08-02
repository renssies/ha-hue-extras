"""Switch platform for Hue Extras.

Demonstrates that this integration can own its own entities in addition to the
services it registers. Replace the demo switch with real Hue-derived entities.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Hue Extras switch entities from a config entry."""
    async_add_entities([HueExtrasExampleSwitch(entry)])


class HueExtrasExampleSwitch(SwitchEntity):
    """A placeholder switch owned by Hue Extras."""

    _attr_has_entity_name = True
    _attr_name = "Example switch"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._attr_unique_id = f"{entry.entry_id}_example_switch"
        self._attr_is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Hue Extras",
            manufacturer="Hue Extras",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Turn the switch on."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Turn the switch off."""
        self._attr_is_on = False
        self.async_write_ha_state()
