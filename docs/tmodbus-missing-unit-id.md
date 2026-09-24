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

Not submitted. modbus-connection's AI policy (Open Home Foundation) forbids
autonomous PRs: a human reviews, understands and submits. Suggested order:
open an issue on wlcrs/tmodbus with the captured frames, then the PR; then the
modbus-connection issue for step 2.
