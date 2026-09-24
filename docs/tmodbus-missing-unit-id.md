# fw 2.23 frames without a unit id: fix in tmodbus

## The problem

Since FoxESS pushed Master 2.23 / Slave 1.03 / Manager 1.95 to the H3
(2026-09-10), about 90 % of RS485 replies arrive without the RTU slave address.
The Modbus TCP gateway forwards what it got, so the frame reads:

```
request   0001 0000 0006 f7 03 7540 0003
reply     0001 0000 0008 03 06 00df 0067 0195        <- unit id missing
expected  0001 0000 0009 f7 03 06 00df 0067 0195
```

The register data is correct. Evidence: the fork's
`docs/ANALYSIS-2026-09-10-fw223.md`.

HA's `modbus` integration owns the shared connection (tmodbus backend). tmodbus
rejects the frame in `ModbusTcpProtocol.send_and_receive` with
`HeaderMismatchError: Unit ID mismatch`. The `fox_ess` integration receives a
`ModbusUnit` and cannot change the framing. Per the guidelines it must not open
its own connection either. So the fix belongs in the client library.

## The fix (tmodbus, opt-in)

`tmodbus-repair-missing-unit-id.patch` (against tmodbus 0.6.2):

- `AsyncTcpTransport(..., repair_missing_unit_id=False)` passes the flag to
  `ModbusTcpProtocol`.
- With the flag set, a reply whose unit id differs from the request **and**
  equals the request's function code (or its exception form, `fc | 0x80`) is
  read as a frame that lost its unit id. The byte is put back in front of the
  PDU and the length grows by one.
- A correct frame never matches: its unit id byte is the one requested. A reply
  from another unit (a real mismatch) still raises.
- Tests: 6 new ones in `tests/transport/test_async_tcp.py` on the frames
  captured from our H3. The full suite passes (1451, TLS tests skipped for the
  missing `cryptography` extra).

## What else has to move

1. **tmodbus**: the patch above.
2. **modbus-connection**: a way for the device library to ask for it through
   its unit, like `require_timeout()`. Proposal:
   `unit.require_unit_id_repair()`. The connection runs with the flag if any
   unit asks for it. It passes the flag to `AsyncTcpTransport`. The pymodbus
   backend ignores it or raises `NotImplementedError`.
3. **foxess-modbus**: `FoxEssH3Inverter.__init__` calls
   `unit.require_unit_id_repair()`.
4. **Home Assistant**: nothing. The flag travels through the unit.

## Status

- 2026-09-24: branch `fix/repair-missing-unit-id` on the fork `jrx-code/tmodbus`,
  commit `eb01157`, rebased on upstream `main` (`41bd1ae`). Upstream suite 1496
  passed, ruff / ruff format / mypy clean. Not submitted.
- tmodbus `AI_POLICY.md` forbids issues and PRs created by autonomous agents.
  The user opens both, reviews the diff and answers maintainers personally.
- CONTRIBUTING asks to discuss first: issue, then PR.

### 1. Issue (https://github.com/wlcrs/tmodbus/issues/new) - draft, rewrite in own words

**TCP response without unit id from serial devices behind a gateway**

My FoxESS H3 inverter (after a firmware update to Master 2.23 / Manager 1.95)
drops the RTU slave address from most replies. The RS485-to-TCP gateway forwards
the reply as is, so the function code ends up in the unit id position:

```
request  0001 0000 0006 f7 03 7540 0003
reply    0001 0000 0008 03 06 00df 0067 0195   (unit id missing)
expected 0001 0000 0009 f7 03 06 00df 0067 0195
```

The data is correct, but tmodbus raises "Unit ID mismatch". Would you accept an
opt-in flag on `AsyncTcpTransport` that puts the unit id back when the received
"unit id" equals the request's function code? I have a branch with tests.

### 2. PR (after the maintainer answers) - draft, follows their template

https://github.com/wlcrs/tmodbus/compare/main...jrx-code:tmodbus:fix/repair-missing-unit-id?expand=1

**Proposed Changes**

Adds `repair_missing_unit_id` (default `False`) to `AsyncTcpTransport` /
`ModbusTcpProtocol`. When set, a response whose unit id differs from the request
but equals the request's function code (or `fc | 0x80`) is treated as a frame
that lost its unit id: the byte is prepended to the PDU. A correct frame never
matches; a response from another unit still raises. Tests use frames captured
from the inverter.

**Related Issues**

#<issue number>

### 3. Afterwards

Same route for modbus-connection (`unit.require_unit_id_repair()` passing the
flag to the tmodbus transport), then `foxess-modbus` calls it in
`FoxEssH3Inverter.__init__`. modbus-connection has the same AI policy.
