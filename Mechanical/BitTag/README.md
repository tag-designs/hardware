# BitTag-family tag case

## What to print

**Print `BitTag-base.stl` and both lids.** That covers every board that has
been fabricated: BitTagv7, BitTagNG / v8 and PresTag v5 (most PresTags in
use), plus PresTag v3.

| part | engraved | fits | pogo compression |
|---|---|---|---|
| `BitTag-base.stl` | `BTAG` (underside) | BitTagv7, BitTagNG / v8, PresTag v3 and **v5**. **Not PresTag-v6** | 1.0 mm |
| `BitTag-lid.stl` | `BTAG` | either base, board with its cell fitted | — |
| `BitTag-lid-nobattery.stl` | `BTAG` `TEST` | either base, board without a cell | — |
| `BitTag-base-prestagv6.stl` | `PTV6` (underside) | every board, PresTag-v6 included | 0.8 mm |

- **`BitTag-base-prestagv6.stl` is only needed if PresTag-v6 is ever built.**
  v6 (not fabricated) adds C4, an 0603 on the underside, which would come down
  on the pogo connector's insulator in the main base before the board reached
  its seat. The v6 base fits every board, at the cost of margin: at 0.8 mm a
  board seated 0.1 mm high falls to the pins' rated 0.7 mm mid stroke, where
  the main base tolerates 0.3 mm.
- **Lids:** each fits either base.

## Boards

One case for the 17 mm coin-cell tags that share a body, a pogo array and a
cell footprint, on the single-pin-pair tag base (`6pin_tagpoints_new_offset`):

| board | thickness | tongue end (from J201) | bases |
|---|---|---|---|
| `BitTagv7` | 0.6 | 5.865 | either |
| `BitTagNG` / `BitTagv8` (identical outlines) | 0.4 | 6.115 | either |
| `PresTag` (v3) | 0.4 | 5.865 | either |
| `PresTag-v5` (fabricated; `~/Research/ultralight-tags/hardware/PresTagv5`) | 0.4 | 5.865 | either |
| `PresTag-v6` (not fabricated) | 0.4 | 5.865 | `BitTag-base-prestagv6.stl` only |

PresTag v3, v5 and v6 share an outline and a top side. Underneath, v3 has only
U302; v5 adds D401 (CDBQC0130L, 0402, 0.61 deep), which overlaps a corner of
the pogo insulator but clears it by 0.37 on the main base; v6 adds C4.

```
make            # both bases and both lids
make check      # OpenSCAD interference check against box models of all five boards
make assembly   # FreeCAD fit check against the real boards, cells and base parts
```

Replaces `BitTagvb.scad` and `BitTagvc.scad` (and the older `BitTagCase.scad`),
kept for reference in `legacy/` with their STLs, the FreeCAD model and the
BitTagv7 STEP/DXF they were drawn from. Coordinates are centred on **J201**, because the case
locates on the pogo array and the boards differ everywhere else: case x =
KiCad x − J201 x, case y = J201 y − KiCad y, z = 0 at the board underside.

## The two defects, and what rules each out

Both old cases were measured from their printed STLs, not their `.scad`
(`BitTagvc.scad` no longer renders: `pogo_pin_height` is commented out).

| | `vb` | `vc` |
|---|---|---|
| board seat above the base PCB | 5.57 | 5.37 |
| pogo compression (tip 6.27) | 0.70 | 0.90 |
| post / insert tops | z 2.0 | z 2.0 |
| lid end-block drop (both blocks) | 2.0 | 2.0 |
| lid underside, no cell | z 2.6 (0.6 board) | z 2.4 |
| lid clearance to post tops | 0.6 | 0.4 |
| 3/8″ dowel tops | z 2.36 | z 2.56 — **above the lid** |
| PresTag v5 D401 to pogo insulator | 0.67 | 0.47 |
| PresTag-v6 C4 to pogo insulator (v6 not fabricated) | 0.39 | 0.19, **0 for a 1.0 mm-thick cap** |

**1. The board could not reach its seat, so the pins were not compressed.**
The nominal seat heights were within the pins' travel, and on the fabricated
boards nothing under the board reaches the 855 connector's insulator (its top
stands 4.29 above the base PCB; PresTag v5's D401 clears it by 0.47 on `vc`).
What stopped the board was the lid: the no-battery lid stalled on the dowels
and inserts before its blocks pressed the board down (defect 2), so the board
rode up on the springs and the pins were barely compressed.

A part *would* block the board on PresTag-v6 (not fabricated): its C4
(06036D476MAT2A, 0.8–1.0 thick, on the underside at x −2.1 to −0.5, y 3.0 to
3.8) hangs directly over the insulator, and on `vc` could rest on it. That is
why v6 has its own base.

This case sets the seat from the 855 drawing with an explicit budget, and the
checks prove nothing stands between the board and its seat:

- **Seat height** = 6.27 − compression. Tip 6.27 = 4.72 + 1.55
  (`855_10_001101_0.svg`), stroke 1.40 max, 0.70 mid (datasheet).
- **1.0 mm compression** on the main base: 0.3 past mid stroke, so a board
  0.3 high still meets the rated working point, and 0.4 short of the stop.
- **0.8 mm on the PresTag-v6 base**, the most C4 allows: its insulator top
  sits at z −1.18, 0.13 below a 1.0 mm cap with 0.05 of solder (0.33 below
  the 0.8 nominal). On the main base it would be at −0.98, so a PresTag-v6
  board must not go in it; `make check` proves that (negative control below).
- Nothing else stands under any board: every bottom-side part of all five
  boards clears the pocket, and the insulator clears every bottom part by
  ≥ 0.1 (`make check`, `make assembly`).
- `make check` also fails if the compression leaves the 0.7…1.1 band.

**2. The lid stalled on the inserts.** Fixed by height, not by trimming:

- **Post and insert tops at z 1.0**, not 2.0 (base top 1.0 above the board
  underside, as on UIUCTag).
- **The no-battery lid's lowest pose**, on a 0.4 board, puts its underside at
  z 2.8: **1.8 above the post tops**. `make check` models each insert standing
  **1.0 proud** and requires 0.5 more on top of that.
- **Dowel relief holes** (r 1.1) through the lid crossbar over both dowels, so
  the dowel length no longer matters. Dowel tops are at z 2.66 (main base) and
  2.46 (PresTag-v6 base).
- The battery lid sits higher still (z ≥ 3.45).

## The lids

Both float on their screws and seat on a **pogo-end block over J201**
(x −0.9…0.9, |y| ≤ 2.375, 0.25 clear of the J301/J302 harness holes). On
these boards the cell sits beside the pogo pins, not over them as on UIUCTag,
so the block always bears on the board, never on the cell. With a cell fitted
it lands on the cell's tab foot, which runs out over the J401 pads to x −0.74.

| | no-battery lid | battery lid |
|---|---|---|
| pogo-end block drop | 2.4 | 3.05 = MS920 stack 2.85 + 0.2 |
| underside, 0.4 board | z 2.8 | z 3.45 (bare board), 3.6 on the tab foot |
| body | stops at the pogo block (x 0.9) | runs on over the cell to x 6.6 |
| cell clearance | — | ≥ 0.2 to an MS920 even if the block misses the tab foot; 0.35 on it (MS621 0.5) |
| far block | drop − 0.2 | drop − 0.2 |
| text | `BTAG`, `TEST` | `BTAG` |

The battery lid covers and retains the cell (it cannot lift more than the
gap) without ever loading it, so the pogo force always goes through the board.

**Far block.** The only board top near the far end that is free on every
board is a 1.5 × 0.9 patch at x −10.89…−9.35, y −2.3…−1.43: 0.25 in from the
far edge, and 0.25 clear of BitTagNG C6 (an 0603 across the middle of the far
end), PresTag U501 and the J303 hole. One small block there, 0.2 short of the
board, so the pogo end always seats first. The old lids' far block was
8 mm wide and landed on BitTagNG's C6.

## Derived geometry

- **Groove**: the union of all the outlines + 0.038 per edge. The far end
  (x −11.135) and the **body shoulders** (x 2.365) are identical on every board
  and are the stops; the tongue groove runs to BitTagNG's 6.115, so v7 and
  PresTag tongues have 0.25 of end play, by design.
- **Shoulder stop**: full base height (z 1.0) for |y| > ~3.0, and z 0.35 (below
  the thinnest board top) under the cell relief between the tongue and |y| 3.0.
- **Under-board pocket**: every board's bottom parts + 0.2, as two boxes (no
  islands to print), 1.5 deep (tallest: v7's ADXL362, model 1.03 below the
  board). Two edges sit on a courtyard with no extra clearance, to keep the
  ledges ≥ 0.4: the far end (BitTagv7 U501, x −10.63) and the +y side by the
  pogo window (PresTag-v6 C4, y 4.13).
- **Harness slots** cover every board's holes (r 0.625 on v7, 0.55 otherwise).
  The near slot is narrowed to x 0.395…2.2 so it stops short of the shoulder
  stop; at 2.5 wide it would have removed it.
- **Cell relief**: hull of the MS621 and MS920 as soldered on every board
  (J401 + 5.0 / + 7.03), + 0.4, from z 0.35; notched to z 0.25 where the
  MS920's under-cell tab crosses the end of the shorter tongues.
- **Screw stack**: lid top to post top is 5.8 on the no-battery lid and up to
  6.8 on the battery lid (v7, on the tab foot), against 8.2 on the UIUCTag standard lid. The same
  2-56 screws reach.

## Checks

`make check` runs the box-model check for each base against the boards it
serves (main base: v7, NG, PresTag v3 and v5; PresTag-v6 base: all five) and both
lids in every pose: no-battery lid on the bare board; battery lid on the tab
foot and on the bare board. It covers base, cells, pogo insulator, inserts
1.0 proud plus 0.5, dowel tops, and the compression band. **Passes, both bases,
no warnings.**

Negative controls, each of which must produce geometry:

| override | result |
|---|---|
| `pogo_compression=1.0`, `check_boards=[PT6]` (PresTag-v6 in the main base) | C4 meets the insulator |
| `base_extra_height=2.0`, `lid_nb_pogo_block_drop=2.0` (the `vc` geometry) | lid meets the inserts |
| `lid_far_block_max=[-9.35,0.5]` (far block across C6) | collides with BitTagNG C6 |
| `pogo_compression=0.6` | fails the compression rule |

`make assembly` checks the real boards (KiCad STEP exports), both cells, the
base PCB, the 855 connector model and the dowels in `BitTag-assembly.FCStd`:
each board on each base it fits, with every lid pose. **ALL CLEAR, nine
board/base pairs, no overlaps.**

| board | base | insulator to bottom parts | no-battery lid over 1.0-proud inserts | lid to dowel | shoulder stop |
|---|---|---|---|---|---|
| BitTagv7 | main / v6 | 0.66 / 0.81 | 0.99 | 0.59 / 0.74 | 0.038 |
| BitTagNG | main / v6 | 1.89 / 1.92 | 0.79 | 0.45 / 0.59 | 0.038 |
| PresTag v3 | main / v6 | 1.95 / 1.98 | 0.79 | 0.45 / 0.59 | 0.043 |
| **PresTag v5** | main / v6 | **0.38** / 0.58 (D401) | 0.79 | 0.45 / 0.59 | 0.043 |
| PresTag-v6 | v6 only | 0.335 (C4) | 0.79 | 0.59 | 0.043 |

On every board:
- **No-battery lid:** underside 1.79 above the post tops (1.99 on v7). The
  far block is 0.200 above the board when the pogo block has seated.
- **Battery lid:** clears the cell by 0.35 for an MS920 and 0.50 for an
  MS621, with the tab foot excluded. It is 1.635 over 1.0-proud inserts, and
  the far block is 0.395 above the board.
- **Dowel tops:** z 2.655 on the main base, 2.455 on the v6 base.
- **Insulator top:** z −0.98 on the main base, −1.18 on the v6 base.

## Not covered / limits

- **The PresTag v3 and v5 STEPs lack eight and nine models** (U302 and the
  0201/0402 passives). They are named through `${KISYS3DMOD}` /
  `${KICAD6_3DMODEL_DIR}`, which `kicad-cli` does not resolve. The same U302
  is checked on PresTag-v6 and BitTagNG, v5's D401 and cell models are
  present, and the box model covers both boards in `make check`.
- **BitTagv8** is checked as BitTagNG: identical outline, J201, J401 and U302.
  Its KiCad 6 file has fewer top-side parts than NG.
- **Insert and dowel stand-up are allowances, not measurements.** The case
  tolerates inserts up to 1.0 proud with 0.5 left over, and any dowel length.
- **Print accuracy.** 1.0 compression tolerates a seat printed up to 0.3 high
  before falling below mid stroke, or 0.4 low before the pins bottom out.
