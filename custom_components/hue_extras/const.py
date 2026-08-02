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
SERVICE_START_SIGNALING = "start_signaling"
SERVICE_STOP_SIGNALING = "stop_signaling"

# signaling action field names.
ATTR_SIGNAL = "signal"
ATTR_DURATION = "duration"
ATTR_COLOR = "color"
ATTR_COLOR2 = "color2"

# Hue v2 signal types.
SIGNAL_NO_SIGNAL = "no_signal"
SIGNAL_ON_OFF = "on_off"
SIGNAL_ON_OFF_COLOR = "on_off_color"
SIGNAL_ALTERNATING = "alternating"
# Signals offered by start_signaling (no_signal is handled by stop_signaling).
START_SIGNALS = [SIGNAL_ON_OFF, SIGNAL_ON_OFF_COLOR, SIGNAL_ALTERNATING]

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
