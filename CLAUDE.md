# hassio-integration-fox-ess

HA custom integration `fox_ess` for FoxESS inverters over Modbus, built per the
HA 2026.9 "Modernizing Modbus" guidelines
(https://developers.home-assistant.io/docs/modbus/introduction). Started
2026-09-24 from scratch. Library: `../foxess-modbus-py` (PyPI name
`foxess-modbus`, not published yet). The old fork
`../hassio-integration-foxess-modbus` (domain `foxess_modbus`, runs on prod) is
reference material only.

Chat in Polish, code/commits/docs in English.

## Decisions (2026-09-24, user)

- Domain `fox_ess` (not `foxess`: collides with foxess-ha cloud on prod; not
  `foxess_modbus`: the fork, and against the "name after the device" rule).
- Two repos, library + integration (like sofar-modbus + sofar).
- H3 only for v1.
- Strictly the shared connection (`async_get_unit` / `async_get_temporary_unit`);
  the fw 2.23 framing bug is fixed upstream in tmodbus, never with our own socket.

## Layout rules (from the guide's checklist)

- No Modbus I/O here; everything through `FoxEssH3Inverter`.
- Coordinator data = the library's `UpdateReport`; entity `available` = its
  `report` name in `data.updated`. TOTAL_INCREASING sensors stay available and
  restore (`FoxEssTotalSensor`).
- Two coordinators: readings (10 s, recycles a wedged link after 3 timeouts),
  settings (60 s).
- No unique_id on the entry (H3 has no serial over Modbus):
  `_async_abort_entries_match` on host/port/unit_id; entity unique ids and the
  device identifier use `entry_id`.

## Versions

HA 2026.9.x pins modbus-connection 4.10.0 (no `Device`); HA dev/2026.10 pins
4.12.1. The library needs 4.12.1, so `hacs.json` says 2026.10.0. The test venv
runs HA 2026.9.3 with 4.12.1 on top (works: HA's modbus connection.py only uses
the params and `for_unit`).

## Dev

`.venv` (uv, Python 3.14): `pytest`, `ruff check .`, `ruff format --check .`,
`mypy` (strict). uv lives in the session scratchpad venv, not on the system.

## Test hardware

H3-10.0-E, AUX RS485, slave 247, behind an RS485-to-TCP gateway; test HA = the
test VM (addresses in the fork's CLAUDE.md, not in this public repo). **The
gateway is shared with prod** (the fork polls it) - a second client disturbs the
first. Never test on prod HA.

## Open

1. fw 2.23 unit-id bug: `docs/tmodbus-missing-unit-id.md` (patch ready, not
   submitted - needs the user).
2. Publish `foxess-modbus` to PyPI (user decision) - until then manifest
   requirement cannot be installed by HA.
3. Test-VM run once HA 2026.10 beta is out and the tmodbus fix is available.
4. Remote control 44000+ (untested on fw 1.95, FC06 only).
