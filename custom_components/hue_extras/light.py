"""Light platform for Hue Extras.

Exposes an "All lights" light entity per Philips Hue **v2** bridge that turns
every light connected to that bridge on or off. It drives the bridge's
``bridge_home`` grouped_light resource, which the core Hue integration
deliberately does not expose as an entity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohue.v2 import HueBridgeV2
from aiohue.v2.controllers.events import EventType
from aiohue.v2.models.resource import ResourceTypes
from homeassistant.components.hue.const import DOMAIN as HUE_DOMAIN
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.start import async_at_started

from .const import LOGGER

if TYPE_CHECKING:
    from aiohue.v2.models.grouped_light import GroupedLight
    from homeassistant.components.hue.bridge import HueBridge


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up an "All lights" entity for each loaded Hue v2 bridge."""

    @callback
    def _add_entities(_hass: HomeAssistant) -> None:
        entities: list[HueAllLightsLight] = []
        for hue_entry in hass.config_entries.async_entries(HUE_DOMAIN):
            if hue_entry.state is not ConfigEntryState.LOADED:
                continue
            bridge = getattr(hue_entry, "runtime_data", None)
            api = getattr(bridge, "api", None)
            if not isinstance(api, HueBridgeV2):
                # Only Hue v2 (CLIP) bridges expose a bridge_home grouped_light.
                continue
            group = next(
                (
                    item
                    for item in api.groups.grouped_light.items
                    if item.owner.rtype == ResourceTypes.BRIDGE_HOME
                ),
                None,
            )
            if group is None:
                LOGGER.debug(
                    "No bridge-home group found for Hue bridge %s", api.config.name
                )
                continue
            entities.append(HueAllLightsLight(bridge, api, group))

        if entities:
            async_add_entities(entities)

    # Run once Home Assistant (and therefore the Hue bridges) has started, so the
    # bridges are loaded and their grouped_light resources are available. Fires
    # immediately if HA is already running (e.g. integration added at runtime).
    entry.async_on_unload(async_at_started(hass, _add_entities))


class HueAllLightsLight(LightEntity):
    """A light that switches every light on a Hue bridge on/off."""

    _attr_has_entity_name = True
    _attr_name = "All lights"
    _attr_should_poll = False
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(
        self, bridge: HueBridge, api: HueBridgeV2, resource: GroupedLight
    ) -> None:
        """Initialize the all-lights entity."""
        self._bridge = bridge
        self._api = api
        self._resource = resource
        self._id = resource.id
        bridge_id = api.config.bridge_id
        self._attr_unique_id = f"{bridge_id}_all_lights"
        # Attach to the existing Hue bridge device so the entity is named after
        # the bridge, e.g. "<Bridge name> All lights".
        self._attr_device_info = DeviceInfo(identifiers={(HUE_DOMAIN, bridge_id)})

    @property
    def is_on(self) -> bool:
        """Return true if any light on the bridge is on."""
        return self._resource.on.on

    async def async_added_to_hass(self) -> None:
        """Subscribe to bridge_home group updates."""
        self.async_on_remove(
            self._api.groups.grouped_light.subscribe(self._handle_event, self._id)
        )

    @callback
    def _handle_event(self, event_type: EventType, resource: GroupedLight) -> None:
        """Handle a state update from the bridge."""
        if resource is not None:
            self._resource = resource
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn all lights on the bridge on."""
        await self._bridge.async_request_call(
            self._api.groups.grouped_light.set_state, id=self._id, on=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn all lights on the bridge off."""
        await self._bridge.async_request_call(
            self._api.groups.grouped_light.set_state, id=self._id, on=False
        )
