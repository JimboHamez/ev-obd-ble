# Converting this integration to Toyota bZ4X / Subaru Solterra

Working notes for the port. Written against commit `6eebefe` (v0.4.0b1), on
branch `feat/bz4x-solterra`. §2 was added later, from telemetry read off a
2026 Subaru Trailseeker.

---

## 1. What this repo actually is

A Home Assistant custom integration — **not** a standalone app. It is a thin
HA shell around a separate PyPI package that does all the OBD work:

```
custom_components/nissan_leaf_obd_ble/     ← this repo (HA glue)
    __init__.py        config entry setup, BLE rediscovery callback
    coordinator.py     polling state machine + value cache
    config_flow.py     device picker, BLE UUID config, options
    sensor.py          28 SensorEntityDescriptions
    binary_sensor.py   5 BinarySensorEntityDescriptions
    button.py          "refresh now" button
    entity.py          base CoordinatorEntity, has_entity_name + device info
    overrides.py       loads user-supplied overrides.yaml / decoders.py

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

## 2. Confirmed vehicle data (2026 Subaru Trailseeker)

Ground truth, read off an actual car — a 2026 Subaru Trailseeker with a
vLinker MC+ BLE dongle, via a working ESPHome `ble_elm327` config and an HA
automation that drives it. Those two files live in `ha_components/`, which is
gitignored (the ESPHome config carries an API encryption key).

This closes the three unknowns the port started blocked on — addressing mode,
ECU headers, and a first command set. It is a Subaru Trailseeker rather than a
Toyota bZ4X, so treat it as strong evidence for the e-TNGA platform generally
and as confirmed only for the Trailseeker; §8 has what is left.

### Bus and addressing

| Property | Value |
|---|---|
| Protocol | ISO 15765-4 CAN, **29-bit**, 500 kbit/s — ELM `ATSP7` |
| Tester address | `F1` |

### ECU headers

| ECU | Request header | Response filter | Carries |
|---|---|---|---|
| `5A` — HV battery / hybrid control | `18DA5AF1` | `18DAF15A` | SoC, HV voltage, HV current, speed, odometer |
| `40` — chassis / body | `18DA40F1` | `18DAF140` | 12 V battery voltage, TPMS |

### Confirmed PIDs

Six PIDs, seven quantities — `F49A` carries voltage and current in one
response. All are UDS mode `22`. Byte letters are `a`, `b`, `c`… over the data
payload following the `62 <pid>` echo.

| PID | ECU | Quantity | Decode | Unit |
|---|---|---|---|---|
| `F45B` | `5A` | HV battery state of charge | `0.4333 * a - 3.9131` | % |
| `F49A` | `5A` | HV battery voltage | `int16(c:d) / 64` | V |
| `F49A` | `5A` | HV battery current | `int16(e:f) / 10`, **negative = charging** | A |
| `F40D` | `5A` | Vehicle speed | `a` | km/h |
| `F4A6` | `5A` | Total odometer | `uint32(a:d) / 10` | km |
| `1103` | `40` | 12 V battery voltage | `a / 10` | V |
| `C00D` | `40` | TPMS, one tyre | `x[7] << 8 \| x[8]` | kPa |

One captured `F49A` frame, for the decoder unit tests in §7 step 5:

```
62 F4 9A 0E 00 67 00 FF AF
         a  b  c  d  e  f
               ^^^^^        c:d — 0x6700 / 64 = 412 V
                     ^^^^^  e:f — int16(0xFFAF) / 10 = -8.1 A (charging)
```

### Caveats on the above

- **The SoC formula is an empirical fit**, not a documented scaling. It peaks
  at ~106.6% for `a = 0xFF`, so it wants clamping. Whether it tracks the
  dash-displayed SoC or true pack SoC is unverified.
- **The odometer `/10` needs confirming against the dash.** Several Toyota
  BEVs return whole km from `F4A6` with no scaling.
- **TPMS is one tyre of four.** The remaining three are presumably adjacent
  PIDs or further into the same `C00D` response; the source config's comment
  ("bytes 3 & 4 → `d` and `e`") contradicts its own formula (`x[7]`, `x[8]`),
  so the byte offset is not yet trustworthy.
- **The PIDs are written as ESPHome sends them**, under `ATCAF1` (the ELM
  frames the request). This library runs `ATCAF0` and frames ISO-TP itself,
  so each command needs the PCI length byte prefixed: `F45B` becomes
  `b"0322F45B"`, matching the `03221304` form already in `leaf_commands`.

## 3. What has to change

### Vehicle-specific — must be rewritten

| Item | Today (Leaf) | bZ4X / Solterra |
|---|---|---|
| ECU headers | `797` (VCM), `743` (combination meter), `79B` (LBC / battery controller) | `18DA5AF1` (HV battery) and `18DA40F1` (chassis/body) — confirmed, §2 |
| PIDs | Nissan mode `22` PIDs, e.g. `03221304` power switch, `022101` LBC | Toyota mode `22` PIDs; six confirmed in §2, the rest still to find |
| Decoders | Leaf-specific bit/byte maths, incl. the 53-byte `lbc` blob | New per-PID decoders — formulas for the confirmed six are in §2 |
| CAN protocol | ISO 15765-4, 11-bit, 500 kbit/s | **29-bit** (`ATSP7`) — confirmed, §2. See the note below; this is a bigger change than it looks |
| Sensor set | e-Pedal, ECO mode, CHAdeMO quick-charge counters, J1772 plug state | Toyota equivalents; several Leaf sensors have no counterpart |

### The protocol switch is not a one-line change

`api.py` takes a `protocol` argument and passes it to `ELM327.create`, but the
value is **inert** — it reaches only two log statements. The init sequence
sends a literal `ATSP6` (`elm327.py:156`), and `elm327.py:41` imports exactly
one parser class, `ISO_15765_4_11bit_500k`, which `elm327.py:89` hard-codes as
`self.__protocol`. `protocols/protocol_can.py` defines no 29-bit stub at all;
the upstream python-OBD protocol table was stripped down to the single class
the Leaf needed.

The parsing survived the strip, though — `CANProtocol` still carries its
`id_bits == 29` branch (`protocol_can.py:117`). So the work is a stub class
(`ELM_ID = "7"`, `id_bits=29`) plus honouring the argument, not a new parser.

Two consequences for the command table:

- The library runs `ATCAF0` and `ATH1`, framing ISO-TP itself and filtering
  responses in software by matching the response header. It never sends
  `ATCRA`, so the source config's `pre_commands` receive filters have no
  counterpart here — the request header alone is what `commands.py` needs.
- `obd.py:__set_header` sends `AT SH <header>` and then `AT FC SH <header>`
  with the same value. Flow-control header behaviour with 8-hex-digit 29-bit
  headers is untested on this dongle.

### Vehicle-independent — keep as-is

- The whole ELM327 / ISO-TP / BLE serial stack.
- `coordinator.py` — the fast/slow/extra-slow polling state machine and the
  value cache. Covered by `tests/test_coordinator.py`.
- `config_flow.py` — device discovery and BLE UUID configuration. The dongle
  is the same class of hardware (ELM327 BLE); only the car differs.
- `overrides.py` — the YAML override mechanism.

## 4. The blocking problem

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

If the gate is kept in some form, `22F45B` on `18DA5AF1` (§2) is the natural
replacement probe: it is the one command confirmed to answer on this car, and
a car that does not answer it has nothing else worth asking for either.

So the library must be changed. That is the decision in §5.

## 5. Options for the OBD library

**A — Vendor the OBD stack into this repo.** Copy the library under
`custom_components/<domain>/obd/`, drop the `requirements` entry from
`manifest.json`, rewrite `commands.py` / `decoders.py` in place.

- Everything lives in one repo; HACS installs it with no PyPI publishing.
- PIDs become editable in the same PR as the sensors that consume them.
- Costs: ~1,700 lines to carry, and it diverges from upstream. The upstream
  code is derived from python-OBD (GPL-2.0-or-later), so vendoring pulls that
  licence into this repo — and this repo currently has **no LICENSE file**
  despite the README badge linking to one (see §6).

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

## 6. Pre-existing problems found while setting up

- ~~**`switch.py` is broken.**~~ **Deleted.** It imported `ICON` and `SWITCH`
  from `const.py` and neither existed, so it raised `ImportError` on import;
  it was not in `const.PLATFORMS`, so HA never loaded it and the bug never
  surfaced. It was also entirely stubbed. Removed while closing the
  `strict-typing` rule, which it made unachievable.
- **No LICENSE file**, though `README.md` badges link to one and the upstream
  library is GPL-derived. Needs resolving before vendoring (§5). Until then
  the HACS validation workflow skips its licence check (`ignore: "license"`
  in `.github/workflows/validate.yaml`); drop that when the file is added.
- **`entity.py` reports bad device info** — `manufacturer` is set to the
  integration name and `model` to the version string. Worth fixing during the
  rename, when the correct values are Toyota/Subaru anyway.
- **`setup.cfg` used the `--strict` pytest flag**, removed in pytest 8. Fixed
  on this branch to `--strict-markers`.

## 7. Suggested order of work

1. **Decide §5**, and settle the domain name and the model scope (bZ4X only,
   or bZ4X + Solterra + Trailseeker under one integration).
2. **Resolve the licence question** before any code is vendored.
3. **Discovery — get real data off the car.** Partly done: §2 has the bus,
   both ECU headers and seven PIDs off a Trailseeker. What remains is the
   sensor set §3 lists as having no confirmed counterpart yet — charge state,
   plug state, cell temperatures, the other three TPMS positions — plus
   re-confirming §2's PIDs on a bZ4X if that body is in scope. The PIDs in every published
   Toyota table still need confirming against the actual vehicle and model
   year. A raw-response logger is the tool for this; a previous one can be
   recovered from git:
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

## 8. What is still unknown

§2 closed the three big ones — addressing mode, ECU headers, and a first set
of PIDs — on a 2026 Subaru Trailseeker. What is left:

- **Whether §2 transfers to the bZ4X and the Solterra.** e-TNGA BEVs differ
  from the hybrid line, and the Toyota and Subaru builds may differ from each
  other. Nothing in §2 should be assumed for a body it was not read from.
- **Whether the car answers on the OBD port with the vehicle off**, which is
  what the coordinator's slow-poll branch assumes. The source automation only
  ever polls on arrival or while charging, so this is untested either way.
- **Response layouts beyond the confirmed seven** — charge state, plug state,
  cell temperatures, and the three TPMS positions §2 does not cover.
- **The two §2 formulas flagged as uncertain**: the empirical SoC fit and the
  odometer's `/10` scaling.
- **Flow-control behaviour with 29-bit headers** on this dongle (§3).
