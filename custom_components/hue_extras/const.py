"""Constants for the Hue Extras integration."""

from __future__ import annotations

from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

DOMAIN = "hue_extras"

PLATFORMS: list[Platform] = [Platform.SWITCH]

# Service names exposed by this integration (see services.yaml).
SERVICE_EXAMPLE_ACTION = "example_action"
