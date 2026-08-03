"""Light platform for Hue Extras.

Exposes an "All lights" light entity per Philips Hue **v2** bridge that controls
every light connected to that bridge. It drives the bridge's ``bridge_home``
grouped_light resource (which the core Hue integration does not expose) and
reuses the core ``GroupedHueLight`` so it is a full-featured grouped light:
on/off plus brightness, color and color temperature derived from the member
lights' capabilities.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from aiohue.v2 import HueBridgeV2
from aiohue.v2.models.resource import ResourceTypes
from homeassistant.components.hue.const import DOMAIN as HUE_DOMAIN
from homeassistant.components.hue.v2.group import GroupedHueLight
from homeassistant.components.light import LightEntityDescription
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


class HueAllLightsLight(GroupedHueLight):
    """Full grouped light controlling every light on a Hue bridge."""

    entity_description = LightEntityDescription(
        key="hue_all_lights",
        has_entity_name=True,
        name="All lights",
    )

    def __init__(
        self, bridge: HueBridge, api: HueBridgeV2, resource: GroupedLight
    ) -> None:
        """Initialize from the bridge_home grouped_light resource."""
        # The bridge_home group is not a Room/Zone, so provide a minimal stand-in
        # for the `group` the core GroupedHueLight expects (only its id and type
        # are used).
        group = SimpleNamespace(
            id=resource.owner.rid,
            type=SimpleNamespace(value=ResourceTypes.BRIDGE_HOME.value),
        )
        super().__init__(bridge, resource, group)

        bridge_id = api.config.bridge_id
        # Keep a stable unique id and attach to the Hue bridge device, so the
        # entity shows up as "<Bridge name> All lights" (GroupedHueLight would
        # otherwise create a separate device for the group).
        self._attr_unique_id = f"{bridge_id}_all_lights"
        self._attr_device_info = DeviceInfo(identifiers={(HUE_DOMAIN, bridge_id)})
