# Ordering KM271-WiFi v1.1.0 at JLCPCB

Production files (Fabrication Toolkit) live in `KM217-WiFi/production/` and
`EXTENSIONS/ETH_W5500/production/`: gerber/drill zip, `bom.csv`, `positions.csv` (CPL),
iBOM, schematic/PCB PDFs, STEP and renders. Regenerate with
`scripts/jlc/make_outputs.sh KM217-WiFi/KM217-WiFi` (or `EXTENSIONS/ETH_W5500/ETH_W5500`).

This revision keeps the original double-sided layout; only fields, labels, fiducials,
part numbers and DRC rules changed.

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
| Fiducials | 1 mm Cu, 2 mm mask, 3 per side, ≥ 3.35 mm from edge | 3 top + 3 bottom ✔ | 3 bottom; **0 top** (no free spot without moving parts) |
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
| SOT-23-5, SOT-223, VSSOP-8, LQFP-48, 0603/0805, LEDs | DB | matches | — |

Not verifiable (no EasyEDA footprint data): main J2 USB mini-B, ETH J2 RJ45, ETH J3,
ETH Y1. **Check these four in JLC's placement preview when ordering.**

Fabrication Toolkit dropped U6 (PCA9306) and others because the original board had empty
`dnp` fields on them; removed.

## Cost estimate (5 assembled boards each, Oct 2026)

| | Main | ETH |
|---|---|---|
| PCB (JLC quote) | $21.10 (2-layer ENIG + gold fingers) | $4.00 (2-layer HASL) |
| Extended parts (×$3) | 11 → $33 | 10 → $30 |
| Basic parts | 19 | 21 |
| Parts (LCSC unit prices × 5) | ≈ $57 | ≈ $72 |
| Standard PCBA, 2 sides (setup + stencils, est.) | ≈ $55 | ≈ $55 |
| **Subtotal** | **≈ $165** | **≈ $160** |

Total ≈ $325 + shipping (≈ €320 incl. shipping). Making both boards single-sided
removes the second assembly side (≈ $25–30 per board); see branch `single-sided`.
Exact PCBA cost needs the gerber upload on jlcpcb.com.
