# Hue Extras

Companion integration that adds extra **actions** and **entities** on top of the core Home Assistant Philips Hue integration.

> ⚠️ **Scaffold / work in progress.** This repository currently contains a
> loadable skeleton so the integration can be installed and debugged inside a
> Home Assistant test environment. Functional behaviour is stubbed with TODOs.

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
