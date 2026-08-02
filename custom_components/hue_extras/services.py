"""Service (action) registration for Hue Extras."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, LOGGER, SERVICE_EXAMPLE_ACTION

EXAMPLE_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("target"): cv.string,
        vol.Optional("value"): cv.string,
    }
)


async def _async_example_action(call: ServiceCall) -> None:
    """Handle the ``hue_extras.example_action`` service call.

    TODO: Implement a real Hue action (e.g. via the core Hue bridge/entities).
    This stub only logs its input so the integration is loadable and debuggable.
    """
    LOGGER.debug("example_action called with data: %s", dict(call.data))


def async_register_services(hass: HomeAssistant) -> None:
    """Register all Hue Extras services."""
    if hass.services.has_service(DOMAIN, SERVICE_EXAMPLE_ACTION):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXAMPLE_ACTION,
        _async_example_action,
        schema=EXAMPLE_ACTION_SCHEMA,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove all Hue Extras services."""
    hass.services.async_remove(DOMAIN, SERVICE_EXAMPLE_ACTION)
