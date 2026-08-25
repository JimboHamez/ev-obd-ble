# Converting this integration to Toyota bZ4X / Subaru Solterra

Working notes for the port. Written against commit `6eebefe` (v0.4.0b1), on
branch `feat/bz4x-solterra`.

---

## 1. What this repo actually is

A Home Assistant custom integration — **not** a standalone app. It is a thin
HA shell around a separate PyPI package that does all the OBD work:

```
custom_components/nissan_leaf_obd_ble/     ← this repo (HA glue)
    __init__.py        config entry setup, BLE rediscovery callback
    coordinator.py     polling state machine + value cache
    config_flow.py     device picker, BLE UUID config, options
    sensor.py          25 SensorEntityDescriptions
    binary_sensor.py   5 BinarySensorEntityDescriptions
    button.py          "refresh now" button
    entity.py          base CoordinatorEntity
    overrides.py       loads user-supplied overrides.yaml / decoders.py
    switch.py          dead code, see §5

py-nissan-leaf-obd-ble (PyPI, 0.1.2)       ← the OBD stack
    commands.py        ← Leaf PIDs + ECU headers          ** vehicle-specific **
    decoders.py        ← Leaf byte-level decoding          ** vehicle-specific **
    api.py             ← command loop                      ** partly specific **
    obd.py, elm327.py, bleserial.py, protocols/, codes.py, utils.py, OBD*.py
                       ← generic ELM327 / ISO-TP stack, derived from python-OBD
```

Roughly 1,300 of the library's 1,700 lines are vehicle-independent. The
vehicle-specific part is concentrated in `commands.py` (~35 lines of table)
and `decoders.py` (~315 lines).

## 2. What has to change

### Vehicle-specific — must be rewritten

| Item | Today (Leaf) | bZ4X / Solterra |
|---|---|---|
| ECU headers | `797` (VCM), `743` (combination meter), `79B` (LBC / battery controller) | Toyota addressing — **must be confirmed against a car** |
| PIDs | Nissan mode `22` PIDs, e.g. `03221304` power switch, `022101` LBC | Toyota mode `22` PIDs — **must be confirmed** |
| Decoders | Leaf-specific bit/byte maths, incl. the 53-byte `lbc` blob | New per-PID decoders |
| CAN protocol | `protocol="6"` hard-coded in `api.py` (ISO 15765-4, 11-bit, 500 kbit/s) | May need `"7"` (29-bit) — **must be confirmed** |
| Sensor set | e-Pedal, ECO mode, CHAdeMO quick-charge counters, J1772 plug state | Toyota equivalents; several Leaf sensors have no counterpart |

### Vehicle-independent — keep as-is

- The whole ELM327 / ISO-TP / BLE serial stack.
- `coordinator.py` — the fast/slow/extra-slow polling state machine and the
  value cache. Covered by `tests/test_coordinator.py`.
- `config_flow.py` — device discovery and BLE UUID configuration. The dongle
  is the same class of hardware (ELM327 BLE); only the car differs.
- `overrides.py` — the YAML override mechanism.

## 3. The blocking problem

**The overrides system cannot carry this port on its own.** In
`py_nissan_leaf_obd_ble/api.py`:

```python
for command in commands.values():
    response = await api.query(command, force=True)
    # the first command is the Mystery command. If this doesn't have a
    # response, then none of the other will
    if command.name == "unknown" and len(response.messages) == 0:
        break
```

`unknown` is `0210C0` on header `797` — a Nissan address. A bZ4X will not
answer it, so the loop breaks on the first command and **every** override
is skipped before it runs. Overrides also inherit their defaults from
`leaf_commands`, and `overrides.py` imports that dict directly.

So the library must be changed. That is the decision in §4.

## 4. Options for the OBD library

**A — Vendor the OBD stack into this repo.** Copy the library under
`custom_components/<domain>/obd/`, drop the `requirements` entry from
`manifest.json`, rewrite `commands.py` / `decoders.py` in place.

- Everything lives in one repo; HACS installs it with no PyPI publishing.
- PIDs become editable in the same PR as the sensors that consume them.
- Costs: ~1,700 lines to carry, and it diverges from upstream. The upstream
  code is derived from python-OBD (GPL-2.0-or-later), so vendoring pulls that
  licence into this repo — and this repo currently has **no LICENSE file**
  despite the README badge linking to one (see §5).

**B — Fork the library as `py-toyota-bz4x-obd-ble`.** Separate repo,
published to PyPI, referenced from `manifest.json`.

- Matches how HA integrations are normally structured; keeps this repo thin.
- Costs: a second repo, a PyPI account and a release step for every PID
  change. Slow feedback loop during the discovery phase, which is exactly
  when iteration needs to be fast.

**C — Generalise into a multi-vehicle stack.** One library, a vehicle profile
selected in the config flow, `leaf_commands` / `bz4x_commands` side by side.

- Fits the repo's existing name (`ev-obd-ble`) and keeps the Leaf working.
- Most work, and the profile abstraction is easier to get right once there is
  a second known-good command set to generalise *from*.

**Recommendation: A now, C later.** Vendor it, get the bZ4X reading real data,
and only introduce the vehicle-profile abstraction once the Toyota command
table is known-good. C is a refactor of A, not a competing design.

## 5. Pre-existing problems found while setting up

- **`switch.py` is broken.** It imports `ICON` and `SWITCH` from `const.py`,
  and neither exists — `ImportError` on import. It is not listed in
  `const.PLATFORMS`, so HA never loads it and the bug never surfaces. It is
  also entirely stubbed (`is_on` returns `False`, the turn on/off bodies are
  commented out). It should be deleted as part of the port.
- **No LICENSE file**, though `README.md` badges link to one and the upstream
  library is GPL-derived. Needs resolving before vendoring (§4).
- **`entity.py` reports bad device info** — `manufacturer` is set to the
  integration name and `model` to the version string. Worth fixing during the
  rename, when the correct values are Toyota/Subaru anyway.
- **`setup.cfg` used the `--strict` pytest flag**, removed in pytest 8. Fixed
  on this branch to `--strict-markers`.

## 6. Suggested order of work

1. **Decide §4**, and settle the domain name and the model scope (bZ4X only,
   or bZ4X + Solterra + Trailseeker under one integration).
2. **Resolve the licence question** before any code is vendored.
3. **Discovery — get real data off the car.** Nothing below can be written
   without it. The PIDs in every published Toyota table need confirming
   against the actual vehicle and model year. A raw-response logger is the
   tool for this; a previous one can be recovered from git:
   ```
   git show 6a4edf3^:custom_components/nissan_leaf_obd_ble/_debug_agent.py
   ```
4. **Vendor + strip.** Bring the stack in, delete `leaf_commands` and the Leaf
   decoders, remove the `unknown` gate from the command loop or replace it
   with a Toyota liveness probe.
5. **Build the command table** from step 3, one PID at a time, each with a
   decoder unit test over a captured response frame.
6. **Rewrite the entity descriptions** in `sensor.py` / `binary_sensor.py` to
   match, deleting the Leaf-only ones.
7. **Rename the domain** — directory, `manifest.json`, `hacs.json`, `const.py`,
   `overrides.py` paths, README. `tests/test_manifest.py` enforces that these
   stay consistent, and the suite discovers the domain rather than hard-coding
   it, so it keeps running across the rename.
8. **Update discovery metadata** — `manifest.json` `bluetooth` service UUIDs
   and the `LOCAL_NAMES = {"OBDBLE"}` filter in `config_flow.py`, if the
   target dongle differs.

## 7. What is genuinely unknown

These need a real bZ4X or Solterra and a dongle. They should not be guessed
from other Toyota models — e-TNGA BEVs differ from the hybrid line, and
Toyota and Subaru builds may differ from each other:

- The CAN addressing mode (11-bit vs 29-bit) and therefore the ELM protocol.
- The ECU header for the HV battery controller, and for the meter cluster.
- Every PID and its response layout.
- Whether the car answers on the OBD port with the vehicle off, which is what
  the coordinator's slow-poll branch assumes.
