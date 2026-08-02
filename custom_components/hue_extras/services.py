"""Service (action) registration for Hue Extras.

The ``hue_extras.change_light`` action changes light properties (brightness,
color, color temperature) on lights provided by the core Philips Hue integration
*without changing their power state*.

Home Assistant's own ``light.turn_on`` always powers a light on when you set a
property. The Hue bridge, however, accepts property changes independently of the
on/off state: the CLIP v2 API applies ``dimming``/``color``/``color_temperature``
without an ``on`` field, and the legacy v1 API accepts a state command without
``on``. This action reuses the core Hue integration's own bridge connection and
error handling to do exactly that.

The service fields deliberately mirror ``light.turn_on`` (same names, same
selectors, same capability filters) so this action is a drop-in replacement.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from aiohue.v2.models.feature import (
    ColorFeaturePut,
    ColorPoint,
    Signal,
    SignalingFeaturePut,
)
from aiohue.v2.models.grouped_light import GroupedLightPut
from aiohue.v2.models.light import LightPut
from homeassistant.components.hue.v1.light import HueLight as HueLightV1
from homeassistant.components.hue.v2.group import GroupedHueLight
from homeassistant.components.hue.v2.helpers import (
    normalize_hue_brightness,
    normalize_hue_colortemp,
    normalize_hue_transition,
)
from homeassistant.components.hue.v2.light import HueLight as HueLightV2
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
    brightness_supported,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import DATA_INSTANCES
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.util import color as color_util

from .const import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR,
    ATTR_COLOR2,
    ATTR_COLOR_NAME,
    ATTR_COLOR_TEMP,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_DURATION,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_SIGNAL,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    DOMAIN,
    LOGGER,
    SERVICE_CHANGE_LIGHT,
    SERVICE_START_SIGNALING,
    SERVICE_STOP_SIGNALING,
    SIGNAL_ALTERNATING,
    SIGNAL_NO_SIGNAL,
    SIGNAL_ON_OFF_COLOR,
    START_SIGNALS,
)
from .light import HueAllLightsLight

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.entity_component import EntityComponent

_MIN_KELVIN = 1000
_MAX_KELVIN = 12000
_MAX_TRANSITION_SEC = 300
_HUE_MAX_BRIGHTNESS = 254

_RGB = vol.ExactSequence((cv.byte, cv.byte, cv.byte))
_HS = vol.ExactSequence(
    (
        vol.All(vol.Coerce(float), vol.Range(min=0, max=360)),
        vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    )
)
_XY = vol.ExactSequence(
    (
        vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
        vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
    )
)

CHANGE_LIGHT_SCHEMA = vol.Schema(
    {
        **cv.ENTITY_SERVICE_FIELDS,
        vol.Optional(ATTR_TRANSITION): vol.All(
            vol.Coerce(float), vol.Range(0, _MAX_TRANSITION_SEC)
        ),
        vol.Optional(ATTR_BRIGHTNESS): vol.All(vol.Coerce(int), vol.Range(0, 255)),
        vol.Optional(ATTR_BRIGHTNESS_PCT): vol.All(
            vol.Coerce(float), vol.Range(0, 100)
        ),
        vol.Optional(ATTR_COLOR_TEMP_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=_MIN_KELVIN, max=_MAX_KELVIN)
        ),
        vol.Optional(ATTR_COLOR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(ATTR_RGB_COLOR): _RGB,
        vol.Optional(ATTR_HS_COLOR): _HS,
        vol.Optional(ATTR_XY_COLOR): _XY,
        vol.Optional(ATTR_COLOR_NAME): cv.string,
    }
)


@dataclass
class LightProperties:
    """Parsed, device-agnostic light properties to apply.

    All of ``light.turn_on``'s color inputs are normalized here into what the Hue
    bridge understands: brightness (0..255), an xy color, and a Kelvin color
    temperature.
    """

    brightness: int | None = None  # 0..255
    color_temp_kelvin: int | None = None
    xy_color: tuple[float, float] | None = None
    transition: float | None = None

    @classmethod
    def from_call(cls, call: ServiceCall) -> LightProperties:
        """Build canonical properties from a light.turn_on-style service call."""
        data = call.data

        brightness = data.get(ATTR_BRIGHTNESS)
        if brightness is None and ATTR_BRIGHTNESS_PCT in data:
            brightness = round(255 * data[ATTR_BRIGHTNESS_PCT] / 100)

        color_temp_kelvin = data.get(ATTR_COLOR_TEMP_KELVIN)
        if color_temp_kelvin is None and ATTR_COLOR_TEMP in data:
            color_temp_kelvin = color_util.color_temperature_mired_to_kelvin(
                data[ATTR_COLOR_TEMP]
            )

        xy_color: tuple[float, float] | None = None
        if ATTR_XY_COLOR in data:
            xy_color = tuple(data[ATTR_XY_COLOR])
        elif ATTR_RGB_COLOR in data:
            xy_color = color_util.color_RGB_to_xy(*data[ATTR_RGB_COLOR])
        elif ATTR_HS_COLOR in data:
            xy_color = color_util.color_RGB_to_xy(
                *color_util.color_hs_to_RGB(*data[ATTR_HS_COLOR])
            )
        elif ATTR_COLOR_NAME in data:
            try:
                rgb = color_util.color_name_to_rgb(data[ATTR_COLOR_NAME])
            except ValueError as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_color_name",
                    translation_placeholders={"name": data[ATTR_COLOR_NAME]},
                ) from err
            xy_color = color_util.color_RGB_to_xy(*rgb)

        return cls(
            brightness=brightness,
            color_temp_kelvin=color_temp_kelvin,
            xy_color=xy_color,
            transition=data.get(ATTR_TRANSITION),
        )

    @property
    def has_any(self) -> bool:
        """Return True if at least one settable property was requested."""
        return any(
            value is not None
            for value in (self.brightness, self.color_temp_kelvin, self.xy_color)
        )


def _expand_group_members(hass: HomeAssistant, entity_ids: set[str]) -> set[str]:
    """Recursively expand group entities into their member entity ids.

    Group entities (e.g. light groups created via the Group helper) advertise
    their members through the ``entity_id`` state attribute, which is what we
    follow here. Leaf entities (no ``entity_id`` attribute) are returned as-is.
    """
    resolved: set[str] = set()
    seen: set[str] = set()
    stack = list(entity_ids)
    while stack:
        entity_id = stack.pop()
        if entity_id in seen:
            continue
        seen.add(entity_id)
        state = hass.states.get(entity_id)
        members = state.attributes.get(ATTR_ENTITY_ID) if state else None
        if members:
            stack.extend(members)
        else:
            resolved.add(entity_id)
    return resolved


def _resolve_hue_light(
    hass: HomeAssistant, entity_id: str
) -> HueLightV2 | HueLightV1 | None:
    """Return the live core-Hue light entity for an entity id, or None."""
    component: EntityComponent | None = hass.data.get(DATA_INSTANCES, {}).get(
        LIGHT_DOMAIN
    )
    if component is None:
        return None
    entity = component.get_entity(entity_id)
    if isinstance(entity, (HueLightV2, HueLightV1)):
        return entity
    return None


async def _apply_v2(entity: HueLightV2, props: LightProperties) -> list[str]:
    """Apply properties to a Hue v2 (CLIP) light without touching power."""
    modes: set[ColorMode] = entity.supported_color_modes or set()
    kwargs: dict[str, Any] = {}
    applied: list[str] = []

    if props.brightness is not None and brightness_supported(modes):
        kwargs["brightness"] = normalize_hue_brightness(props.brightness)
        applied.append("brightness")
    if props.xy_color is not None and ColorMode.XY in modes:
        kwargs["color_xy"] = props.xy_color
        applied.append("color")
    if props.color_temp_kelvin is not None and ColorMode.COLOR_TEMP in modes:
        kwargs["color_temp"] = normalize_hue_colortemp(
            props.color_temp_kelvin,
            entity.min_color_temp_mireds,
            entity.max_color_temp_mireds,
        )
        applied.append("color_temp")
    if props.transition is not None:
        kwargs["transition_time"] = normalize_hue_transition(props.transition)

    if not applied:
        return []

    # No `on` key -> the bridge leaves the on/off state untouched.
    await entity.bridge.async_request_call(
        entity.controller.set_state, id=entity.resource.id, **kwargs
    )
    return applied


async def _apply_v1(entity: HueLightV1, props: LightProperties) -> list[str]:
    """Apply properties to a legacy Hue v1 light without touching power."""
    modes: set[ColorMode] = entity.supported_color_modes or set()
    command: dict[str, Any] = {}
    applied: list[str] = []

    if props.transition is not None:
        command["transitiontime"] = int(props.transition * 10)
    if props.xy_color is not None and ColorMode.XY in modes:
        command["xy"] = list(props.xy_color)
        applied.append("color")
    elif props.color_temp_kelvin is not None and ColorMode.COLOR_TEMP in modes:
        temp_k = max(
            entity.min_color_temp_kelvin,
            min(entity.max_color_temp_kelvin, props.color_temp_kelvin),
        )
        command["ct"] = color_util.color_temperature_kelvin_to_mired(temp_k)
        applied.append("color_temp")
    if props.brightness is not None and brightness_supported(modes):
        command["bri"] = max(1, round((props.brightness / 255) * _HUE_MAX_BRIGHTNESS))
        applied.append("brightness")

    if not applied:
        return []

    # No `on` key -> power state is untouched.
    if entity.is_group:
        await entity.bridge.async_request_call(entity.light.set_action, **command)
    else:
        await entity.bridge.async_request_call(entity.light.set_state, **command)
    await entity.coordinator.async_request_refresh()
    return applied


async def _async_apply(
    entity: HueLightV2 | HueLightV1, props: LightProperties
) -> list[str]:
    """Dispatch to the v2 or v1 implementation."""
    if isinstance(entity, HueLightV2):
        return await _apply_v2(entity, props)
    return await _apply_v1(entity, props)


async def _async_change_light(call: ServiceCall) -> None:
    """Handle the ``hue_extras.change_light`` service call."""
    hass = call.hass
    props = LightProperties.from_call(call)
    if not props.has_any:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_properties"
        )

    selected = async_extract_referenced_entity_ids(hass, TargetSelection(call.data))
    entity_ids = _expand_group_members(
        hass, selected.referenced | selected.indirectly_referenced
    )

    lights = [
        (entity_id, entity)
        for entity_id in entity_ids
        if (entity := _resolve_hue_light(hass, entity_id)) is not None
    ]
    if not lights:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_hue_lights"
        )

    results = await asyncio.gather(
        *(_async_apply(entity, props) for _, entity in lights),
        return_exceptions=True,
    )

    errors: list[str] = []
    for (entity_id, _), result in zip(lights, results, strict=True):
        if isinstance(result, Exception):
            LOGGER.error("Failed to change %s: %s", entity_id, result)
            errors.append(entity_id)
        elif not result:
            LOGGER.warning(
                "%s does not support any of the requested properties; skipped",
                entity_id,
            )
        else:
            LOGGER.debug("Changed %s on %s", ", ".join(result), entity_id)

    if errors:
        raise HomeAssistantError(
            f"Failed to change light(s): {', '.join(sorted(errors))}"
        )


_MAX_SIGNAL_DURATION_SEC = 65534
_MAX_SIGNAL_DURATION_MS = 65534000
_DEFAULT_SIGNAL_DURATION_SEC = 10

START_SIGNALING_SCHEMA = vol.Schema(
    {
        **cv.ENTITY_SERVICE_FIELDS,
        vol.Required(ATTR_SIGNAL): vol.In(START_SIGNALS),
        vol.Optional(ATTR_DURATION, default=_DEFAULT_SIGNAL_DURATION_SEC): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=_MAX_SIGNAL_DURATION_SEC)
        ),
        vol.Optional(ATTR_COLOR): _RGB,
        vol.Optional(ATTR_COLOR2): _RGB,
    }
)

STOP_SIGNALING_SCHEMA = cv.make_entity_service_schema({})


def _resolve_hue_signalable(
    hass: HomeAssistant, entity_id: str
) -> HueLightV2 | GroupedHueLight | HueAllLightsLight | None:
    """Return the live Hue v2 light or grouped light for an entity id, or None."""
    component: EntityComponent | None = hass.data.get(DATA_INSTANCES, {}).get(
        LIGHT_DOMAIN
    )
    if component is None:
        return None
    entity = component.get_entity(entity_id)
    if isinstance(entity, (HueLightV2, GroupedHueLight, HueAllLightsLight)):
        return entity
    return None


def _collect_signalables(
    hass: HomeAssistant, entity_ids: set[str]
) -> dict[str, HueLightV2 | GroupedHueLight | HueAllLightsLight]:
    """Resolve targets to signalable Hue resources.

    A Hue grouped light (room/zone) is signalled directly as a group. Anything
    that is not a Hue light but exposes members (an HA light group) is expanded
    to its members, which are then resolved individually.
    """
    result: dict[str, HueLightV2 | GroupedHueLight | HueAllLightsLight] = {}
    seen: set[str] = set()
    stack = list(entity_ids)
    while stack:
        entity_id = stack.pop()
        if entity_id in seen:
            continue
        seen.add(entity_id)
        if (entity := _resolve_hue_signalable(hass, entity_id)) is not None:
            result[entity_id] = entity
            continue
        state = hass.states.get(entity_id)
        members = state.attributes.get(ATTR_ENTITY_ID) if state else None
        if members:
            stack.extend(members)
    return result


def _signal_colors(signal: str, data: dict[str, Any]) -> list[ColorFeaturePut] | None:
    """Build the signal colors from the rgb inputs, validating requirements."""

    def _to_color(rgb: tuple[int, int, int]) -> ColorFeaturePut:
        return ColorFeaturePut(xy=ColorPoint(*color_util.color_RGB_to_xy(*rgb)))

    color = data.get(ATTR_COLOR)
    color2 = data.get(ATTR_COLOR2)
    if signal == SIGNAL_ON_OFF_COLOR:
        if color is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="signal_needs_color"
            )
        return [_to_color(color)]
    if signal == SIGNAL_ALTERNATING:
        if color is None or color2 is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="signal_needs_two_colors"
            )
        return [_to_color(color), _to_color(color2)]
    return None


async def _apply_signal(
    entity: HueLightV2 | GroupedHueLight | HueAllLightsLight,
    signal: Signal,
    duration_ms: int | None,
    colors: list[ColorFeaturePut] | None,
) -> bool:
    """Send a signal to a Hue light/grouped light. Returns False if unsupported."""
    signaling = getattr(entity.resource, "signaling", None)
    if signaling is None:
        # The light has no signaling feature at all.
        return False
    # no_signal (stop) is always allowed when signaling is supported. For the
    # active signals, honour the advertised signal_values when the light lists
    # them; an empty list is treated as "unknown" and attempted.
    if (
        signal is not Signal.NO_SIGNAL
        and signaling.signal_values
        and signal not in signaling.signal_values
    ):
        return False

    put_cls = LightPut if isinstance(entity, HueLightV2) else GroupedLightPut
    update_obj = put_cls(
        signaling=SignalingFeaturePut(
            signal=signal, duration=duration_ms, colors=colors
        )
    )
    await entity.bridge.async_request_call(
        entity.controller.update, entity.resource.id, update_obj
    )
    return True


async def _run_signal(
    call: ServiceCall,
    signal: Signal,
    duration_ms: int | None,
    colors: list[ColorFeaturePut] | None,
) -> None:
    """Resolve the target and apply a signal to every Hue light in it."""
    hass = call.hass
    selected = async_extract_referenced_entity_ids(hass, TargetSelection(call.data))
    lights = _collect_signalables(
        hass, selected.referenced | selected.indirectly_referenced
    )
    if not lights:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_hue_lights"
        )

    results = await asyncio.gather(
        *(
            _apply_signal(entity, signal, duration_ms, colors)
            for entity in lights.values()
        ),
        return_exceptions=True,
    )

    errors: list[str] = []
    for (entity_id, _entity), result in zip(lights.items(), results, strict=True):
        if isinstance(result, Exception):
            LOGGER.error("Signaling failed on %s: %s", entity_id, result)
            errors.append(entity_id)
        elif result is False:
            LOGGER.warning(
                "%s does not support the '%s' signal; skipped",
                entity_id,
                signal.value,
            )
        else:
            LOGGER.debug("Signal '%s' applied to %s", signal.value, entity_id)

    if errors:
        raise HomeAssistantError(f"Signaling failed on: {', '.join(sorted(errors))}")


async def _async_start_signaling(call: ServiceCall) -> None:
    """Handle ``hue_extras.start_signaling``."""
    signal_str: str = call.data[ATTR_SIGNAL]
    duration_ms = min(int(call.data[ATTR_DURATION] * 1000), _MAX_SIGNAL_DURATION_MS)
    colors = _signal_colors(signal_str, call.data)
    await _run_signal(call, Signal(signal_str), duration_ms, colors)


async def _async_stop_signaling(call: ServiceCall) -> None:
    """Handle ``hue_extras.stop_signaling`` (stops any active signal)."""
    await _run_signal(call, Signal(SIGNAL_NO_SIGNAL), None, None)


def async_register_services(hass: HomeAssistant) -> None:
    """Register all Hue Extras services."""
    if hass.services.has_service(DOMAIN, SERVICE_CHANGE_LIGHT):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHANGE_LIGHT,
        _async_change_light,
        schema=CHANGE_LIGHT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_SIGNALING,
        _async_start_signaling,
        schema=START_SIGNALING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_SIGNALING,
        _async_stop_signaling,
        schema=STOP_SIGNALING_SCHEMA,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove all Hue Extras services."""
    hass.services.async_remove(DOMAIN, SERVICE_CHANGE_LIGHT)
    hass.services.async_remove(DOMAIN, SERVICE_START_SIGNALING)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_SIGNALING)
