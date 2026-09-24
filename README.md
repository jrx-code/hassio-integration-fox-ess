# FoxESS (Modbus) for Home Assistant

A custom integration for FoxESS hybrid inverters over Modbus TCP. It is built
the way Home Assistant 2026.9 introduced for Modbus devices
([Modernizing Modbus](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus)):

- The register map lives in a separate library,
  [foxess-modbus](https://github.com/jrx-code/foxess-modbus), built on
  [modbus-connection](https://home-assistant-libs.github.io/modbus-connection/).
- The integration asks Home Assistant's `modbus` integration for a unit with
  `async_get_unit`. It never opens its own socket. Other integrations on the
  same gateway share the connection.
- You set it up in the UI. There is no YAML register map.

Domain: `fox_ess`.

## Requirements

- Home Assistant 2026.10 or later (needs modbus-connection 4.12).
- A FoxESS **H3** (`H3-x.x-E`) on its RS485 port through a Modbus TCP gateway
  (for example a USR or Waveshare RS485-to-Ethernet box in "Modbus TCP to RTU"
  mode).

Other FoxESS families are recognised but not read yet.

## Installation

1. HACS, then custom repositories, then add this repository as an integration.
2. Install "FoxESS (Modbus)" and restart Home Assistant.
3. Settings, then Devices & services, then Add integration, then FoxESS.
4. Enter the gateway host, the port (502) and the inverter's Modbus address
   (247 out of the box).

The flow reads the model and firmware before it creates the entry.

## Entities

| Kind | Entities |
|---|---|
| Sensors | PV power per string and total, grid power (positive = export), feed-in and import power, load power, inverter power, battery SoC, power, voltage, current, temperature; BMS state of health and remaining energy; lifetime and daily energy counters |
| Binary sensor | Fault (the diagnostics download names the active faults) |
| Select | Work mode (Self use, Feed-in first, Back-up, Peak shaving) |
| Numbers | Max charge and discharge current, min SoC off grid, max SoC, min SoC on grid |

Per-phase values and a few diagnostic sensors are disabled by default.

Energy counters stay available while the inverter is unreachable, and they
restore after a restart. This keeps the energy dashboard free of gaps.

## Polling

Measurements and energy every 10 s (three block reads). Settings every
minute (two block reads). A write reads the settings back at once.

## Known limitations

- **H3 firmware Master 2.23 / Manager 1.95** sends most replies without the
  unit id byte. Home Assistant's Modbus client rejects them, so the inverter
  looks unreachable. A fix for the client library is prepared in
  [`docs/tmodbus-missing-unit-id.md`](docs/tmodbus-missing-unit-id.md).
- On manager firmware 1.93 and later the daily battery charge and discharge
  counters are not valid on the inverter. The integration does not create
  those two sensors there.
- The H3 does not report its serial number over Modbus. A config entry is
  identified by host, port and unit id.
- Remote control (registers 44000+) and charge periods are not supported.

## Troubleshooting

Download the diagnostics from the device page. It contains the raw register
map, which is enough to reproduce most problems in a test.

## Development

```bash
uv venv --python 3.14 && uv pip install pytest-homeassistant-custom-component "pymodbus[serial]==3.13.1" -e ../foxess-modbus-py ruff mypy
.venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/mypy
```
