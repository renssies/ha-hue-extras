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

## Entities

### "All lights" (per Hue **v2** bridge)

A light entity — named **`<Bridge name> All lights`** and shown under the Hue
bridge device — that turns **every light connected to that bridge** on or off.

It drives the bridge's `bridge_home` grouped_light resource via the Hue v2 API,
which the core Hue integration intentionally does not expose. It's an on/off
light (no brightness/color). One entity is created per loaded v2 bridge; legacy
v1 bridges are not supported for this entity.

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
