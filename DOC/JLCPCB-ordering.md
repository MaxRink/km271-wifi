# Ordering KM271-WiFi v1.1.0 at JLCPCB

Production files (Fabrication Toolkit) live in `KM217-WiFi/production/` and
`EXTENSIONS/ETH_W5500/production/`: gerber/drill zip, `bom.csv`, `positions.csv` (CPL),
iBOM, schematic/PCB PDFs, STEP and renders. Regenerate with
`scripts/jlc/make_outputs.sh KM217-WiFi/KM217-WiFi` (or `EXTENSIONS/ETH_W5500/ETH_W5500`).

This revision keeps the original double-sided layout. Changes: fields, labels, fiducials,
part numbers, DRC rules, and one local exception: USB Mini-B J2 was replaced by USB-C
(local re-route around J2 only).

## Order options

| Option | Main board (`Buderus-KM217-WIFI_v1.1.0.zip`) | ETH add-on (`KM271-WiFi-ETHext_v1.1.0.zip`) |
|---|---|---|
| Layers | 2 | 2 |
| Size | 100.82 × 40.0 mm | 59.76 × 34.58 mm |
| Thickness | 1.6 mm (KM271 slot) | 1.6 mm |
| Surface finish | **ENIG** (gold fingers need ENIG; HASL tins them) | HASL lead-free (or ENIG) |
| Gold fingers | **Yes** | No |
| Beveling | **No** (see below) | No |
| Via covering | Tented | Tented |
| Min via | 0.3 mm/(0.4/0.45 mm), no surcharge (board uses 0.4/0.8) | same (board uses 0.3/0.6) |
| Mark on PCB | Specify position: `JLCJLCJLCJLC` under J7 | Specify position: under TR1 |
| PCBA | Standard, **both sides** | Standard, **both sides** |
| PCBA BOM / CPL | `production/bom.csv`, `production/positions.csv` | same |

**No bevel.** The fingers sit on a tongue that ends 5.75 mm short of the two board legs,
so a chamfer cutter cannot reach that edge. JLC also refuses beveling below 50 × 50 mm
(quote form: "Beveled fingers cannot be produced for PCBs smaller than 50mm x 50mm").
The original module is used unbevelled. The fingers stop 0.2 mm before the edge, with
mask open and no vias/pads within 1 mm (rule area `GOLD_FINGERS`). See the fab note on
`Cmts.User`.

**Outline.** 100.82 mm wide is kept: JLC quotes 100 × 40 and 100.82 × 40 at the same
price ($4.00 / 5 pcs, 2-layer HASL, Oct 2026), and shrinking needs a re-route of MOSI/IO22.

## Part swaps (datasheets checked)

| Ref | Original | New (LCSC) | Pinout / footprint | Electrical | Result |
|---|---|---|---|---|---|
| U1 | ESP32-WROOM-32D-N8 | ESP32-WROOM-32E-N8 (C701342) | Same 38+EPAD land pattern; 32E pins 17–22 are NC (32D: internal flash), board leaves them unconnected; pin 32 NC on both | ESP32-D0WD-V3, 8 MB flash, no PSRAM (IO16 = SCL, IO17 = LED stay usable; **not** N8R2). Strapping unchanged: IO12 only drives PCA9306 EN (no pull-up → low at boot), IO0/IO2/IO5/IO15 same nets as before | Clean. Note: EN has 10 k pull-up but **no RC capacitor** (Espressif recommends 10 k/1 µF); same as before, flagged |
| U4, U5 | SN74LV1T34DBVRG4 | SN74LV1T34DBVR (C100024) | Identical SOT-23-5 | G4 = RoHS/green suffix only | Clean |
| C13 | 22 µF 1812 (TDK C4532X5R1A226M) | TDK C4532X7R1E226MT000N (C76690) | Same 1812 | 25 V X7R ≥ 10 V X5R | Clean |
| J3 | Amphenol 54202-G08-03 (no stock) | hanxia HX PZ2.54-2x3P TP (C32713283) | 2×3, 2.54 mm SMD, same KiCad footprint | 3 A, gold | Clean (DNP-compatible jumper header) |
| ETH U2 | AP1117-33 | AZ1117IH-3.3TRG1 (C108495) | Same SOT-223 (1 GND, 2/tab OUT, 3 IN) | AZ1117I is stable with low-ESR ceramics (ESR < 20 Ω, ≥ 10 µF); board has 22 µF 0805 MLCC in/out | Clean. **AMS1117 rejected**: its datasheet requires 22 µF tantalum for stability |
| ETH Y1 | 25 MHz HC49-SD (no MPN) | Abracon ABLS2-25.000MHZ-D4YF-T (C596824) | HC-49SMD, same footprint | CL 18 pF, ±30 ppm, ESR 40 Ω = W5500 spec (25 MHz, ±30 ppm, CL 18 pF); C7/C8 18 pF kept as in WIZnet reference | Clean |
| ETH J1 | WE 2×5 SMD socket (no MPN) | BOOMELE 2×5 SMD female (C843271) | 2.54 mm, 8.5 mm, mates with main J7 (54202-G0805LF) | — | Clean |
| ETH TR1 | Würth 749013011A | **kept** (C7193798) | — | Pulse H1601CE: pin names not published in JLC data, pinout unverified | Kept Würth |
| ETH J2 | Würth 634008137521 | **kept** (C6095310, 57 in stock) | no stocked footprint-identical alternative found | — | Kept; enough for 5 boards |
| J2 | Würth 65100516121 USB Mini-B | HRO TYPE-C-31-M-12 (C165948, 324k stock) | KiCad `USB_C_Receptacle_HRO_TYPE-C-31-M-12` = HRO recommended layout (16 SMD tails, 4 plated shell slots, 2 NPTH pegs); pin table A1/A12/B1/B12 GND, A4/A9/B4/B9 VBUS, A5 CC1, B5 CC2 checked against HRO drawing | 5 A / 20 V. J2 was power-only (D+/D-/ID unconnected), so D+/D-/SBU stay unconnected; CC1 and CC2 each get their own 5.1 kΩ to GND (R69/R70, basic C23186) so USB-C sources supply 5 V; shield via R60 (22 Ω) to GND as before | Clean. Mouth at the same top edge (0.3 mm overhang like Mini-B), centre unchanged in x, origin 2.75 mm closer to the edge; height 3.2 mm vs 4 mm. Shell legs are plated slots: JLC solders them with paste-in-hole (standard for this part); no GND vias or GND pour under the metal shell (rule area `USB_SHELL_NO_POUR`) |
| passives/LEDs | generic | JLC basic parts | same 0603/0805 footprints | 100 n C14663 50 V X7R, 2u2 C23630 16 V X5R (rails ≤ 5 V) | Clean |

## JLC compliance checklist

Rules from jlcpcb.com/capabilities/pcb-capabilities (fetched 2026-10-25), enforced by
`*.kicad_dru` (copy: `scripts/jlc/jlcpcb.kicad_dru`) and board setup. DRC: 0 errors.

| Rule | JLC value | Main | ETH |
|---|---|---|---|
| Track width (1 oz, 2-layer) | ≥ 0.10 mm | 0.25 ✔ | 0.20 ✔ |
| Clearance | ≥ 0.10 mm (SMD pad–pad 0.15) | DRC ✔ | DRC ✔ |
| Via hole / diameter (no surcharge) | ≥ 0.2 / 0.45 mm | 0.4 / 0.8 ✔ | 0.3 / 0.6 ✔ |
| PTH annular ring (2-layer) | ≥ 0.18 mm | 0.34 ✔ | 0.375 ✔ |
| NPTH | ≥ 0.5 mm | 0.9 ✔ | 1.2 ✔ |
| Hole-to-hole (pad / via) | 0.45 / 0.2 mm | DRC ✔ | DRC ✔ |
| Copper to routed edge | ≥ 0.2 mm | DRC ✔ (fingers trimmed) | DRC ✔ |
| Silkscreen text | ≥ 1.0 mm high, ≥ 0.15 mm line | new texts 1.0/0.15 ✔ | ✔ |
| Pad to silkscreen | ≥ 0.15 mm | DRC ✔ | DRC ✔ |
| Min SMD pad | 0.25 × 0.25 mm | 0.30 ✔ | 0.30 ✔ |
| Gold fingers | ENIG, mask open, no copper/vias near, bevel only ≥ 50 × 50 | ✔, no bevel | n/a |
| Fiducials | 1 mm Cu, 2 mm mask, 3 per side, ≥ 3.35 mm from edge | 3 top + 3 bottom ✔ | 3 bottom; **0 top** (no free spot without moving parts): order with JLC edge rails + fiducials, fixed in PR 2 |
| Edge rails | JLC: required for standard PCBA | none in design: let JLC add | same |
| HandSolder pads | — | longer pads, fine for reflow | ✔ |
| BOM/CPL format | Designator, Footprint, Quantity, Value, LCSC Part # / Designator, Mid X, Mid Y, Rotation, Layer | ✔ | ✔ |

## CPL rotation check

`scripts/jlc/check_cpl_rotation.py` downloads JLC's own (EasyEDA) footprint per LCSC part
and computes the rotation/offset that maps the KiCad pads onto it.

| Part | Fabrication Toolkit default | Needed | Fix (`FT Rotation Offset` / `FT Position Offset`) |
|---|---|---|---|
| U1 ESP32-WROOM-32E | 0° | 270°, origin 0.745 mm along the pin rows | 270, `0,-0.745` |
| J3, J7 (SMD headers), ETH J1 | 0° | 270° | 270 |
| SW3, SW4 B3SL | 0° (DB +90°) | 270° (Omron: pins 4–3 and 2–1 bridged, rows must match) | 270 |
| C7, C8 elcos | 180° (DB) | 0° (JLC "+" pad = KiCad pad 1) | 180 |
| ETH TR1 | 90° | 0° | 270 |
| J2 USB-C (HRO) | 180° | 180°, JLC origin 1.575 mm towards the mouth | `0,1.575` |
| SOT-23-5, SOT-223, VSSOP-8, LQFP-48, 0603/0805, LEDs | DB | matches | — |

Not verifiable (no EasyEDA footprint data): ETH J2 RJ45, ETH J3, ETH Y1 (2-pin, either
180° works). **Check these in JLC's placement preview when ordering.**

Fabrication Toolkit's database would have placed SW3/SW4 90° off their pads and C7/C8 reversed;
the overrides above fix that. LEDs: C2286 (red) numbers pad 1 = anode, C72043/C72038 pad 1 =
cathode; all four LEDs are oriented by function, not pad number.

Fabrication Toolkit dropped U6 (PCA9306) and others because the original board had empty
`dnp` fields on them; removed.

## Cost estimate (5 assembled boards each, Oct 2026)

| | Main | ETH |
|---|---|---|
| PCB (JLC quote) | $21.10 (2-layer ENIG + gold fingers) | $4.00 (2-layer HASL) |
| Extended parts (×$3) | 11 → $33 | 10 → $30 |
| Basic parts | 20 | 21 |
| Parts (LCSC unit prices × 5) | ≈ $48 | ≈ $72 |
| Standard PCBA, 2 sides (setup + stencils, est.) | ≈ $55 | ≈ $55 |
| **Subtotal** | **≈ $156** | **≈ $160** |

Total ≈ $316 + shipping (≈ €310 incl. shipping). Making both boards single-sided
removes the second assembly side (≈ $25–30 per board); see branch `single-sided`.
Exact PCBA cost needs the gerber upload on jlcpcb.com.

## Verification (both boards, vs upstream `0f4f064`)

`scripts/jlc/verify.py <project> 0f4f064` and DRC/ERC:

| Check | Main | ETH |
|---|---|---|
| Netlist, pin by pin | only J2 (Mini-B → USB-C), R69/R70 added, R60.1 renamed `/USB_SHIELD` (same connection). Extra edit: J8 (DNP mating screw terminal, no footprint) set "not on board", which drops its two unconnected pins from the netlist | no change |
| Placement | only J2 (USB-C), R69/R70, fiducials; J1 fingers, J7, H1 unchanged | only fiducials; J1 (mates J7) unchanged |
| Tracks / vias | 872 → 893 / 240 → 241 (J2 area) | unchanged |
| DRC with schematic parity | 0 errors, 0 unconnected | 0 errors, 0 unconnected |
| ERC | 0 errors | 0 errors |
| BOM / CPL / fitted PCB refdes | 93 / 93 / 93 | 64 / 64 / 64 |
| Hidden refdes | none | none |
| Courtyard overlaps | 0 (DRC) | 0 (DRC) |
| Fiducial mask openings free of copper | ✔ | ✔ |

Label check against nets: J7 EXT, ETH J1 (mirrored, bottom), ETH J3, J4 DEBUG, J3 PWRSEL,
buttons and ETH LEDs match. **Fixed:** the main-board LED labels were in reverse order
(D1 = IO21 … D4 = IO25 per R23–R26); now matching.

Remaining DRC/ERC warnings (justified):
- `lib_footprint_issues` / `footprint_link_issues`: the build machine has no global KiCad 10
  library table and `the78mole` is the author's external library; footprints are embedded.
- `silk_over_copper` (8 per board): stock footprint outlines (test-point circles, U6, J2/J3
  bodies) touching pad openings; JLC clips silkscreen from openings.
- ERC `endpoint_off_grid` (upstream schematic style), ETH `isolated_pin_label` SCL_X
  (I2C pass-through on the ETH socket is not used on that board).

## Best-practice checklist (PR 1 scope: no part moves, no broad re-route)

| Item | Status | Note |
|---|---|---|
| Solid GND pour both layers | pass | existing pours, refilled |
| GND stitching grid / RF & ETH via fences | deferred to PR 2 | needs via placement across the board |
| Power trace width (IPC-2221) | pass | VBUS/3V3 0.5–0.6 mm ≥ 1.2 A @ 10 °C, load < 0.6 A |
| Regulator thermal copper | pass | SOT-223 tabs on pours (unchanged) |
| Decoupling at ESP32 3V3 (≥ 10 µF + 100 n) | pass, partly | C1 100 n + C14 2.2 µF within ~4 mm of pin 2; C13 22 µF ~8 mm away on the rail (move closer in PR 2) |
| ESP32 EN RC (10 k / 1 µF) | deferred to PR 2 | schematic addition + placement |
| Antenna keep-out | pass | module antenna overhangs the board edge (unchanged) |
| Ethernet pairs / magnetics / Bob Smith | pass (unchanged) | follows WIZnet reference; re-check on PR 2 re-route |
| No 90° corners, teardrops | deferred to PR 2 | needs re-route |
| ESD/TVS on USB-C, KM271 lines | proposed for PR 2 | schematic additions |
| Copper-to-edge pullback ≥ 0.5 mm | fixed for pours | 4 items (main) / 3 (ETH) at 0.2–0.5 mm, deferred to PR 2 |
| Test points 3V3/5V/GND/TX/RX/EN/IO0 | deferred to PR 2 | needs placement |
| Polarity / pin-1 marks | pass | LEDs, elcos, ICs, headers |
| Fab layer: stackup, finish, fingers, revision | fixed | `FAB NOTES` on Cmts.User |
| Title block / revision on silk | pass | v1.1.0 from `${REVISION}` |

## 3D models and renders

`3dmodels/` holds models referenced via `${KIPRJMOD}`: USB-C and TR1 from EasyEDA (aligned by
pad fit), plus approximate boxes (datasheet outline) for the Würth RJ45, the WR-MM J3 and the
WAGO J6, since no vendor model was available offline. The boxes appear in renders, not in
the STEP export (VRML only). `production/*_full_*.png` show the board with all DNP options
populated.
