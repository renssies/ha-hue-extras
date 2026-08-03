# Hue Extras

Companion integration that adds extra **actions** and **entities** on top of the core Home Assistant Philips Hue integration.

## Actions

### `hue_extras.change_light`

Changes a Hue light's **brightness, color, or color temperature without changing
its power state** — the piece `light.turn_on` can't do, since setting any
property there always powers the light on.

- **Drop-in replacement for `light.turn_on`.** The fields have the same names,
  selectors, and capability filters, so you can swap `light.turn_on` for
  `hue_extras.change_light` and keep the same `data:` block. Fields that don't
  apply to the selected light are hidden (a brightness-only light shows no color
  fields, etc.).
- Works on lights from the **core Philips Hue integration** — both modern **v2**
  (CLIP) bridges and legacy **v1** bridges.
- Same **target picker as `light.turn_on`** (single light, device, area, label,
  or light group); non-Hue targets and light-group members are handled
  automatically. Restricted to nothing extra — the handler keeps only Hue lights.
- If a light is **off it stays off**; the bridge stores the new values and
  applies them the next time it turns on. If it's on, the change is applied live.

**Fields** (all named as in `light.turn_on`): `brightness` (0-255) or
`brightness_pct` (0-100); `color_temp_kelvin` or `color_temp` (mireds);
`rgb_color`, `hs_color`, `xy_color`, `color_name` (normalized to the bridge's
native xy color); and `transition` (seconds).

How it works: v2 lights are driven via the CLIP `set_state` call with the `on`
field omitted; v1 lights via a state command without `on`. Hue has no
white/RGBW channel, so those `light.turn_on` fields are intentionally absent.

### `hue_extras.start_signaling` / `hue_extras.stop_signaling`

Drives the **Hue v2 signaling API** (the modern replacement for the old
alert/breathe flash) on single lights, Hue **grouped lights** (rooms/zones), and
the **All lights** bridge entity.

**`start_signaling`** fields:

- `signal`: **On off** (blink in the current color), **On off color** (blink in
  `color`), or **Alternating** (alternate between `color` and `color2`).
- `duration`: seconds.
- `color` / `color2`: RGB (required by On off color / Alternating).

**`stop_signaling`** takes only a target and stops any active signal.

Both target single lights and Hue **grouped lights** directly (a targeted
room/zone or the *All lights* entity is signalled as a group, not expanded); HA
light groups are expanded to their members. Lights that don't advertise support
for the signal are skipped.

Example — alternate red/blue on a room for 30 seconds, then stop:

```yaml
action: hue_extras.start_signaling
target:
  entity: light.living_room     # a Hue room/zone grouped light
data:
  signal: alternating
  duration: 30
  color: [255, 0, 0]
  color2: [0, 0, 255]
```

```yaml
action: hue_extras.stop_signaling
target:
  entity: light.living_room
```

How it works: sends a `SignalingFeaturePut` via the Hue v2 CLIP API using each
resource's own controller (`LightPut` for lights, `GroupedLightPut` for grouped
lights). Hue v2 only.

## Entities

### "All lights" (per Hue **v2** bridge)

A light entity — named **`<Bridge name> All lights`** and shown under the Hue
bridge device — that turns **every light connected to that bridge** on or off.

It drives the bridge's `bridge_home` grouped_light resource via the Hue v2 API,
which the core Hue integration intentionally does not expose. It is a
**full grouped light** — it reuses the core Hue `GroupedHueLight`, so besides
on/off it supports **brightness, color and color temperature** (aggregated from
the member lights' capabilities), plus transition and flash. Like the core Hue
grouped lights it exposes `is_hue_group`, `lights`, and `entity_id` attributes
and can be targeted by **`start_signaling`** / **`stop_signaling`**. One entity
is created per loaded v2 bridge; legacy v1 bridges are not supported for this
entity.

## Installation (HACS custom repository)

1. In HACS → *Integrations* → ⋮ → **Custom repositories**, add this repo's URL
   with category **Integration**.
2. Install **Hue Extras**, then restart Home Assistant.
3. Add it via **Settings → Devices & Services → Add Integration → Hue Extras**.

## Local development & debugging

This repo is developed alongside the sibling integrations in this workspace.
See the shared `../dev/` Docker environment for running Home Assistant with all
integrations mounted and `debugpy` remote debugging enabled. See
[../dev/README.md](../dev/README.md).

## License

[MIT](LICENSE)
