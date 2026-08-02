"""Constants for the Hue Extras integration."""

from __future__ import annotations

from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

DOMAIN = "hue_extras"

# The core Philips Hue integration domain we hook into.
HUE_DOMAIN = "hue"

PLATFORMS: list[Platform] = [Platform.LIGHT]

# Service names exposed by this integration (see services.yaml).
SERVICE_CHANGE_LIGHT = "change_light"

# Service field names — identical to light.turn_on so this action is a drop-in
# replacement (same data keys work).
ATTR_TRANSITION = "transition"
ATTR_BRIGHTNESS = "brightness"
ATTR_BRIGHTNESS_PCT = "brightness_pct"
ATTR_COLOR_TEMP_KELVIN = "color_temp_kelvin"
ATTR_COLOR_TEMP = "color_temp"  # mireds
ATTR_RGB_COLOR = "rgb_color"
ATTR_HS_COLOR = "hs_color"
ATTR_XY_COLOR = "xy_color"
ATTR_COLOR_NAME = "color_name"
