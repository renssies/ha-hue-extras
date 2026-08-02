"""The Hue Extras integration.

Companion integration that adds extra *actions* (services) and *entities* on top
of the core Home Assistant Philips Hue integration.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER, PLATFORMS
from .services import async_register_services, async_unregister_services

type HueExtrasConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: HueExtrasConfigEntry) -> bool:
    """Set up Hue Extras from a config entry."""
    LOGGER.debug("Setting up Hue Extras")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HueExtrasConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and len(hass.config_entries.async_entries(DOMAIN)) <= 1:
        async_unregister_services(hass)
    return unload_ok
