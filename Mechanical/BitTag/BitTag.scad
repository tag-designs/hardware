$fn = 120; // steps in generating circles

makelid = true;
makebase = true;
// Second lid, for testing a board before its cell is fitted: it sits lower,
// with short end blocks on the board top (TAGCASE-PROCESS.md step 6).
lid_no_battery = false;
makeassembly = false;  // base + lid in place, with the tags as simple solids
makechecks = false;    // interference volumes only; should render empty

// One base and lid for the whole 17 mm coin-cell family, which share a body,
// a pogo array and a cell footprint:
//
//   BitTagv7       0.6 mm, 3.5 mm tongue
//   BitTagNG / v8  0.4 mm, 3.75 mm tongue (identical outlines)
//   PresTag (v3)   0.4 mm, 3.5 mm tongue
//   PresTag-v5     0.4 mm, as v3, plus D401 under the board (the fabricated
//                  PresTag; ~/Research/ultralight-tags/hardware/PresTagv5)
//   PresTag-v6     0.4 mm, as v5, plus C4 (0603) under the board over the pogo
//                  insulator (not fabricated)
//
// Replaces BitTagvb.scad / BitTagvc.scad. Their two defects, and how this
// design rules each out by construction and by `make check`, are in README.md:
//   1. pogo pins too shallow: the seat height is set from the 855 drawing
//      with a compression budget, and nothing under the board can hold it up;
//   2. lid stalls on the inserts/dowels before seating: the lid floats
//      >= lid_post_clearance_min above the post tops even on the thinnest
//      board with no cell, and is drilled clear of the dowel tops.
//
// All dimensions are millimetres. Coordinates are centred on J201 (the pogo
// array), +x toward the tongue/cell end, +y up the screen: case x = kicad_x -
// J201_x, case y = J201_y - kicad_y. z = 0 is the board underside.
eps = 0.1;

// ---------------------------------------------------------------------------
// Pogo pins and the seat height
// ---------------------------------------------------------------------------

// 855-22-0XX-10-001101 (BoardDesigns/libraries/datasheets/855_10_001101_0.svg,
// 855-series datasheet.pdf). Heights above the tag-base PCB top:
pogo_free_height = 4.72 + 1.55;    // plunger tip, uncompressed
pogo_max_stroke = 1.40;            // .055"
pogo_mid_stroke = 0.70;            // .0275", the rated working point
pogo_insulator_top = 0.51 + 3.78;  // insulator floats 0.51 on the pin collars
pogo_insulator_size = [3.0, 6.73]; // .118" x (6 x .025" + .115")

// Design compression. 1.0 for BitTagv7, BitTagNG/v8 and PresTag v3/v5: 0.3
// past mid stroke, 0.4 short of the stop. PresTag-v6 needs the shallower 0.8 base:
// its C4 hangs over the insulator (see presv6_c4 below). The Makefile builds
// both bases from this one parameter.
pogo_compression = 1.0;
seat_height = pogo_free_height - pogo_compression; // board underside above base PCB
presv6_fits = pogo_compression <= 0.8 + 1e-6;

pogo_cutout_len = 3.2;             // proven window, clears the 3.0 x 6.73 insulator
pogo_cutout_width = 7;

// ---------------------------------------------------------------------------
// Boards
// ---------------------------------------------------------------------------

// Shared by all four boards (Edge.Cuts, relative to J201).
board_far_x = -11.135;
board_shoulder_x = 2.365;          // body end; the tongue carries on to +x
board_corner_radius = 1.0;
board_sweep_height = 4.0;          // vertical clearance swept by the PCB
board_edge_clearance = 0.0015 * 25.4; // routing/board-fab tolerance per edge

// [name, thickness, body y0, body y1, tongue y0, tongue y1, tongue end x,
//  tongue corner radius, shoulder fillet radius, J401 x]
BT7 = ["BitTagv7",   0.6, -4.47, 4.53, -1.97, 2.03, 5.865, 0.5,  0.5,  0.17];
BTNG = ["BitTagNG",  0.4, -4.50, 4.50, -2.00, 2.00, 6.115, 0.75, 0.75, 0.38];
PT3 = ["PresTag",    0.4, -4.50, 4.50, -1.97, 2.04, 5.865, 0.5,  0.5,  0.17];
PT5 = ["PresTag-v5", 0.4, -4.50, 4.50, -1.97, 2.04, 5.865, 0.5,  0.5,  0.17];
PT6 = ["PresTag-v6", 0.4, -4.50, 4.50, -1.97, 2.04, 5.865, 0.5,  0.5,  0.17];
boards = [BT7, BTNG, PT3, PT5, PT6];

thinnest_board = 0.4;
thickest_board = 0.6;

function board_body_y(b) = [b[2], b[3]];
function board_tongue_y(b) = [b[4], b[5]];

// Union of the outlines, for the groove.
groove_body_y = [-4.50, 4.53];
groove_tongue_y = [-2.00, 2.04];
groove_tongue_end = 6.115;

// Harness holes J301-J304: x 1.08-1.12 / -9.88 to -9.89, y +-3.23-3.25;
// radius 0.625 on BitTagv7 (1.25 mm holes), 0.55 on the others.
near_hole_x = [1.08, 1.12];
far_hole_x = -9.885;
corner_hole_y = 3.25;
corner_hole_radius = 0.625;        // the largest

// ---------------------------------------------------------------------------
// Parts, from Mechanical/tools/board_geometry.py (courtyards, relative to
// J201). Heights are body heights from the datasheets or KiCad models,
// rounded up; `make assembly` checks the real models.
// ---------------------------------------------------------------------------

// [min, max, height above board top]
function top_parts(b) =
    b == BT7 ? [
        [[-7.73, -3.11], [-1.49, 3.13], 0.90],  // U302 QFN-32 (on top here)
        [[-3.51, 3.16], [-1.65, 4.10], 0.60]    // C502
    ] : b == BTNG ? [
        [[-5.98, 0.10], [-4.59, 1.55], 0.33],   // C1, C3
        [[-8.95, -0.98], [-7.55, -0.28], 0.33], // C2
        [[-4.54, 2.94], [-2.73, 3.86], 0.70],   // C4 0402
        [[-5.99, 1.59], [-4.17, 2.51], 0.70],   // C404 0402
        [[-5.98, 2.55], [-4.59, 3.25], 0.33],   // C5
        [[-2.55, -2.71], [-1.85, -1.31], 0.33], // C501
        [[-4.18, -0.10], [-2.69, 2.90], 0.50],  // C502, C503, Q501
        [[-10.86, -1.18], [-9.41, 1.78], 1.00], // C6 0603
        [[-2.60, -3.68], [-0.74, -2.74], 0.60], // D401
        [[-6.94, -0.96], [-5.54, -0.26], 0.33], // R1
        [[-5.44, -3.40], [-2.63, -0.20], 0.50], // U1 WLCSP
        [[-8.84, 0.30], [-6.04, 3.10], 1.00],   // U2 LGA-12 (model 0.97)
        [[-8.93, -3.31], [-5.54, -1.11], 0.80]  // U501 RV-8803-C7
    ] : [ // PresTag v3, v5 and v6 (identical top sides)
        [[-6.85, -3.60], [-6.15, 0.70], 0.33],  // C1, R1, C503
        [[-4.49, 0.62], [-3.05, 3.45], 0.50],   // C101, C502, Q501
        [[-9.64, 1.00], [-8.94, 2.40], 0.33],   // C2
        [[-3.47, -3.73], [-0.86, -2.79], 0.60], // C3 (v6) / D401 (v3)
        [[-8.85, 0.63], [-7.93, 2.45], 0.70],   // C404
        [[-2.73, -2.73], [-2.03, -1.33], 0.33], // C501
        [[-7.93, 0.73], [-4.73, 3.53], 0.50],   // U1 WLCSP
        [[-6.10, -2.70], [-2.89, 0.50], 1.90],  // U2 LPS27HHW (model 1.85)
        [[-9.10, -2.80], [-6.90, 0.60], 0.80]   // U501 RV-3028-C7
    ];

// [min, max, depth below the board underside]
presv6_c4 = [[-2.79, 2.67], [0.17, 4.13], 1.05]; // 06036D476MAT2A, 1.0 max + solder
function bottom_parts(b) =
    b == BT7 ? [
        [[-5.30, 0.90], [-3.26, 2.76], 0.60],   // C402, C404
        [[-2.70, -1.25], [-1.76, 0.61], 0.60],  // C403
        [[-6.40, 0.50], [-5.46, 2.76], 0.60],   // C501, R1
        [[-7.90, -1.70], [-6.46, 2.36], 0.60],  // C503, R1
        [[-2.70, -3.70], [-1.76, -1.84], 0.45], // D401 SOD-923
        [[-2.98, 1.08], [-1.98, 2.48], 0.50],   // Q501
        [[-6.78, -2.49], [-3.28, 0.36], 1.14],  // U405 ADXL362 (model 1.14)
        [[-10.63, -1.57], [-8.43, 1.83], 0.80]  // U501 RV-3028-C7
    ] : b == PT5 ? [
        [[-9.05, -3.09], [-2.81, 3.15], 0.90],  // U302
        [[-2.73, -3.74], [-0.87, -2.80], 0.65]  // D401 CDBQC0130L (model 0.61), over the insulator corner
    ] : b == PT6 ? [
        [[-9.05, -3.09], [-2.81, 3.15], 0.90],  // U302
        [[-2.73, -3.74], [-0.87, -2.80], 0.65], // D401
        presv6_c4
    ] : [
        [[-9.05, -3.09], [-2.76, 3.20], 0.90]   // U302
    ];

// ---------------------------------------------------------------------------
// Coin cell (J401)
// ---------------------------------------------------------------------------

// Centres as soldered (Mechanical/TAGCASE-PROCESS.md step 5): MS621F 5.0
// beyond the J401 pad centre, MS920SE 7.03. Both overhang the tongue and the
// shoulders, so the relief is a hull over every board's cells.
ms621_offset = 5.0;
ms621_radius = 3.68;
ms920_offset = 7.03;
ms920_radius = 5.14;
battery_radius_clearance = 0.4;
battery_cell_bottom_gap = 0.15;    // under-cell tab lifts the cell off the board
ms621_stack_height = 2.7;
ms920_stack_height = 2.85;         // to the top of the positive contact
cell_tab_thickness = 0.15;         // tab foot on the J401 pads, under the pogo block

// Outside the board outline the base stays at least this high under the
// cells, so the board edge always has a stop: below the thinnest board top,
// and below every cell bottom.
battery_stop_height = thinnest_board - 0.05;
battery_tab_notch_halfwidth = 1.5;
battery_tab_notch_height = thinnest_board - 0.15;

// ---------------------------------------------------------------------------
// Posts, inserts and alignment pins (6pin_tagpoints_new_offset)
// ---------------------------------------------------------------------------

post_center = [-5.0, 0];
post_spacing = 20.0;
post_radius = 3.0;
insert_hole_radius = 1.65;         // press fit for 2-56 insert (proven)
screw_hole_radius = 1.3;           // clearance for 2-56 screw (proven)

alignment_pin_offset = [-5.0, 6.5];
alignment_pin_radius = 0.75;       // press fit for 1/16" dowel (proven)
dowel_length = 9.525;              // 3/8"; Components/dowel_pin.step
base_pcb_thickness = 1.6;
dowel_top_z = dowel_length - base_pcb_thickness - seat_height;

// ---------------------------------------------------------------------------
// Base
// ---------------------------------------------------------------------------

base_x = [-15.2, 6.6];             // 4 beyond the far end, 0.45 past the tongue
base_half_width = 8.05;
base_extra_height = 1.0;           // base top and post tops above the board underside
base_top_z = base_extra_height;
base_height = seat_height + base_extra_height;

// Under-board pocket: every board's bottom parts plus 0.2, as two boxes so no
// thin islands are left to print. Two edges sit on a courtyard with no extra
// clearance, because the ledges there would otherwise be under 0.4 wide: the
// far end (BitTagv7 U501, x -10.63) and the +y side next to the pogo window
// (PresTag-v6 C4, y 4.13). A courtyard already lies >= 0.25 beyond the body.
bottom_parts_clearance = 0.2;
under_board_cut_depth = 1.5;       // tallest bottom part 1.14 (ADXL362 model)

// Harness slots run the full base width and cover every board's corner holes.
// The near slot is narrowed to 1.8 so it stops short of the body shoulder
// (x 2.40), which is the battery-end stop on every board.
far_slot_x = [far_hole_x - corner_hole_radius - 0.1, far_hole_x - corner_hole_radius - 0.1 + 2.5];
near_slot_x = [near_hole_x[1] - corner_hole_radius - 0.1, 2.2];
near_slot_center = (near_slot_x[0] + near_slot_x[1]) / 2;

under_pocket_boxes = [
    [[-10.63, -3.74 - bottom_parts_clearance], [near_slot_center, 3.20 + bottom_parts_clearance]],
    [[-2.79 - bottom_parts_clearance, 3.20], [near_slot_center, 4.13]]
];

// ---------------------------------------------------------------------------
// Lid (lid coordinates: z = 0 is the lid underside)
// ---------------------------------------------------------------------------

lid_preview_z = 10;
lid_body_height = 3;
lid_end_height = 4;

// Both lids float on their screws and seat on the pogo-end block, which
// presses the board directly over J201. On these boards the cell lies beside
// the pogo pins, not over them (unlike UIUCTag), so even the battery lid's
// block bears on the board -- on the cell's tab foot over the J401 pads -- and
// the cell never takes the force the pins need.
//
// No-battery lid. Its drop sets the lowest the lid ever sits: on the thinnest
// board, underside at 0.4 + 2.4 = 2.8, which clears
//   the post and insert tops (z 1.0) by 1.8 -- inserts may stand up to
//     insert_proud_allowance proud and still leave lid_post_clearance_min;
//   the tallest top part, PresTag U2 (LPS27HHW, top z 2.25), by 0.55;
//   the dowels, through dowel_relief holes, whatever their length.
lid_nb_pogo_block_drop = 2.4;
// Battery lid. The body runs on over the cell, so the drop is the MS920 stack
// plus a 0.2 gap, counted from the bare board top: if the block lands beside
// the tab foot instead of on it, the cell still clears. With the tab under it
// the gap is 0.35 (MS920) / 0.5 (MS621), so the cell is retained, not loaded.
lid_cell_gap = 0.2;
lid_pogo_block_drop = ms920_stack_height + lid_cell_gap;
lid_pogo_block_x = [-0.9, 0.9];    // over the pins (x +-0.635), short of the cell tabs' rise
lid_pogo_block_halfwidth = corner_hole_y - corner_hole_radius - 0.25; // 0.25 clear of J301/J302
insert_proud_allowance = 1.0;
lid_post_clearance_min = 0.5;

// Far block: a 0.2 gap so the pogo end always seats first. The only free
// board top near the far end on every board is this patch: 0.25 in from the
// far edge, 0.25 clear of BitTagNG C6 (y -1.18..1.78), PresTag U501 (x -9.10)
// and the J303 harness hole.
lid_far_block_gap = 0.2;
lid_far_block_min = [board_far_x + 0.25, -2.3];
lid_far_block_max = [-9.35, -1.43];

// The battery lid covers the cell out to the base end; the no-battery lid
// stops at the pogo block.
function lid_body_x(nb) = [lid_far_block_min[0], nb ? lid_pogo_block_x[1] : base_x[1]];
lid_body_y = [-4.5, 4.5];
dowel_relief_radius = 1.1;

function pogo_drop(nb) = nb ? lid_nb_pogo_block_drop : lid_pogo_block_drop;
// Lid underside height when its pogo block rests on board b, on the cell's
// tab foot or on the bare board top.
function lid_z(b, nb, on_tab) = b[1] + (on_tab ? cell_tab_thickness : 0) + pogo_drop(nb);

// ---------------------------------------------------------------------------
// Engraving
// ---------------------------------------------------------------------------

// Bold, at the sizes and depth that print (TAGCASE-PROCESS.md step 7).
text_font = "Liberation Sans:style=Bold";
text_grow = 0.05;
text_size_base = 3;
text_size_lid = 2.6;
text_depth_base = 0.8;
text_depth_lid = 0.8;

lid_text = "BTAG";
base_text = presv6_fits ? "PTV6" : "BTAG";
base_text_pos = [-10.5, 0, -seat_height]; // clear of the dowel holes at x -5

marker_size_base = 3.5;            // glyph 1.99 x 1.92
marker_size_lid = 5;               // glyph 2.81 x 2.70
// Base marker in the strip between the cell relief (y 5.54) and the base edge.
base_marker_pos = [4.3, (ms920_radius + battery_radius_clearance + base_half_width) / 2, base_top_z];
lid_marker_pos = [-1.0, 0, lid_body_height];
lid_text_pos = [post_center[0], 0, lid_body_height];
// The no-battery lid adds this on the body between the far end and the
// crossbar (x -10.89..-8.0).
lid_nb_text = "TEST";
// 7.68 x 2.25 at 2.2: the lid body is only 9 wide (9.08 at text_size_lid ran off it).
lid_nb_text_size = 2.2;
lid_nb_text_pos = [(lid_far_block_min[0] + post_center[0] - post_radius) / 2, 0, lid_body_height];

// Extra base support around the post bosses (as UIUCTag).
base_post_secondary_x = -3.5;
base_post_fill_x = -1.75;
base_post_fill_len = 3.5;
base_post_fill_width = 6;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

module xy_centered_cube(size) {
    translate([0, 0, size[2] / 2]) cube(size, center=true);
}

module box_from(minxy, maxxy, z0, z1) {
    translate([minxy[0], minxy[1], z0])
        cube([maxxy[0] - minxy[0], maxxy[1] - minxy[1], z1 - z0]);
}

module mirrored_y(y) {
    for (side = [-1, 1]) translate([0, side * y, 0]) children();
}

module at_post_center() {
    translate([post_center[0], post_center[1], 0]) children();
}

module rounded_box_2d(minxy, maxxy, r) {
    hull()
        for (x = [minxy[0] + r, maxxy[0] - r], y = [minxy[1] + r, maxxy[1] - r])
            translate([x, y]) circle(r=r);
}

module marker(size, depth) {
    linear_extrude(depth + eps)
        translate([0, -0.229 * size])
            text(text="*", size=size, font=text_font, halign="center", valign="center");
}

module engraved_text(s, size, depth) {
    rotate([0, 0, -90])
        linear_extrude(depth + eps)
            offset(delta=text_grow)
                text(text=s, size=size, font=text_font, halign="center", valign="center");
}

// ---------------------------------------------------------------------------
// Board outlines
// ---------------------------------------------------------------------------

// Body (rounded corners) and tongue (rounded far corners), with the concave
// shoulder fillets closed at radius b[8].
module board_2d(b) {
    offset(r=-b[8]) offset(delta=b[8])
        union() {
            rounded_box_2d([board_far_x, b[2]], [board_shoulder_x, b[3]], board_corner_radius);
            rounded_box_2d([board_shoulder_x - 2, b[4]], [b[6], b[5]], b[7]);
        }
}

module groove_2d() {
    offset(delta=board_edge_clearance)
        union() for (b = boards) board_2d(b);
}

// ---------------------------------------------------------------------------
// Shared post geometry
// ---------------------------------------------------------------------------

module post_holes(radius, height) {
    at_post_center() mirrored_y(post_spacing / 2) cylinder(r=radius, h=height);
}

module crossbar_with_holes(height, end_height, hole_radius) {
    difference() {
        at_post_center() {
            xy_centered_cube([2 * post_radius, post_spacing, height]);
            mirrored_y(post_spacing / 2) cylinder(r=post_radius, h=end_height);
        }
        translate([0, 0, -eps]) post_holes(hole_radius, end_height + 2 * eps);
    }
}

module reinforced_base_crossbar(height) {
    at_post_center() mirrored_y(post_spacing / 2) {
        cylinder(r=post_radius, h=height);
        translate([base_post_secondary_x, 0, 0]) cylinder(r=post_radius, h=height);
        translate([base_post_fill_x, 0, 0])
            xy_centered_cube([base_post_fill_len, base_post_fill_width, height]);
    }
}

// ---------------------------------------------------------------------------
// Base
// ---------------------------------------------------------------------------

module base_solid() {
    translate([0, 0, -seat_height]) {
        box_from([base_x[0], -base_half_width], [base_x[1], base_half_width], 0, base_height);
        reinforced_base_crossbar(base_height);
    }
}

module board_groove() {
    linear_extrude(board_sweep_height, convexity=10) groove_2d();
}

module under_board_pocket() {
    for (p = under_pocket_boxes)
        box_from(p[0], p[1], -under_board_cut_depth, board_sweep_height);
}

module harness_slots() {
    for (sx = [far_slot_x, near_slot_x])
        box_from([sx[0], -base_half_width - eps], [sx[1], base_half_width + eps],
                 -under_board_cut_depth, board_sweep_height);
}

module pogo_pin_cutout() {
    translate([0, 0, -seat_height - eps])
        xy_centered_cube([pogo_cutout_len, pogo_cutout_width, seat_height + 4.0]);
}

module alignment_pin_holes() {
    translate([alignment_pin_offset[0], 0, -seat_height - eps])
        mirrored_y(alignment_pin_offset[1])
            cylinder(r=alignment_pin_radius, h=base_height + 2 * eps);
}

module base_insert_holes() {
    translate([0, 0, -seat_height - eps])
        post_holes(insert_hole_radius, base_height + 2 * eps);
}

// Hull over every board's cells, from battery_stop_height up. Inside the
// outline the groove is already open; outside it this leaves a stop at the
// board edge, below the cells. Where the MS920's under-cell tab crosses the
// end of the shorter tongues the stop is notched lower.
module battery_relief() {
    translate([0, 0, battery_stop_height])
        linear_extrude(board_sweep_height)
            hull()
                for (b = boards) {
                    translate([b[9] + ms621_offset, 0]) circle(r=ms621_radius + battery_radius_clearance);
                    translate([b[9] + ms920_offset, 0]) circle(r=ms920_radius + battery_radius_clearance);
                }
    box_from([BT7[6] - eps, -battery_tab_notch_halfwidth],
             [base_x[1] + eps, battery_tab_notch_halfwidth],
             battery_tab_notch_height, board_sweep_height);
}

module base_engraving() {
    translate(base_text_pos - [0, 0, eps])
        mirror([1, 0, 0]) engraved_text(base_text, text_size_base, text_depth_base);
    translate(base_marker_pos - [0, 0, text_depth_base])
        marker(marker_size_base, text_depth_base);
}

module makeBase() {
    difference() {
        base_solid();
        board_groove();
        under_board_pocket();
        harness_slots();
        pogo_pin_cutout();
        alignment_pin_holes();
        base_insert_holes();
        battery_relief();
        base_engraving();
    }
}

// ---------------------------------------------------------------------------
// Lid
// ---------------------------------------------------------------------------

module lid_solid(nb) {
    crossbar_with_holes(lid_body_height, lid_end_height, screw_hole_radius);
    bx = lid_body_x(nb);
    box_from([bx[0], lid_body_y[0]], [bx[1], lid_body_y[1]], 0, lid_body_height);
    box_from([lid_pogo_block_x[0], -lid_pogo_block_halfwidth],
             [lid_pogo_block_x[1], lid_pogo_block_halfwidth],
             -pogo_drop(nb), lid_body_height);
    box_from(lid_far_block_min, lid_far_block_max,
             -(pogo_drop(nb) - lid_far_block_gap), lid_body_height);
}

module makeLid(nb=lid_no_battery) {
    difference() {
        lid_solid(nb);
        translate([alignment_pin_offset[0], 0, -eps])
            mirrored_y(alignment_pin_offset[1])
                cylinder(r=dowel_relief_radius, h=lid_end_height + 2 * eps);
        translate(lid_text_pos - [0, 0, text_depth_lid])
            engraved_text(lid_text, text_size_lid, text_depth_lid);
        if (nb)
            translate(lid_nb_text_pos - [0, 0, text_depth_lid])
                engraved_text(lid_nb_text, lid_nb_text_size, text_depth_lid);
        translate(lid_marker_pos - [0, 0, text_depth_lid])
            marker(marker_size_lid, text_depth_lid);
    }
}

// ---------------------------------------------------------------------------
// Tags, base-side parts and check volumes
// ---------------------------------------------------------------------------

module tag_board(b) {
    translate([0, 0, tag_check_lift]) tag_board_at_rest(b);
}

module tag_board_at_rest(b) {
    linear_extrude(b[1])
        difference() {
            board_2d(b);
            for (hx = [near_hole_x[0], far_hole_x]) mirrored_y(corner_hole_y)
                translate([hx, 0]) circle(r=0.55);
        }
    for (p = top_parts(b)) box_from(p[0], p[1], b[1], b[1] + p[2]);
    for (p = bottom_parts(b)) box_from(p[0], p[1], -p[2], 0);
}

module tag_cell_bodies(b) {
    for (c = [[ms621_offset, ms621_radius, ms621_stack_height],
              [ms920_offset, ms920_radius, ms920_stack_height]])
        translate([b[9] + c[0], 0, b[1] + battery_cell_bottom_gap])
            cylinder(r=c[1], h=c[2] - battery_cell_bottom_gap);
}

module tag_cells(b) {
    tag_cell_bodies(b);
    // Under-cell tab, flat on the board top from J401 out to the cell centre.
    for (off = [ms621_offset, ms920_offset])
        translate([b[9], -1.25, b[1]]) cube([off, 2.5, battery_cell_bottom_gap]);
}

// Pogo connector insulator, 0.1 grown, as it stands under the board.
module pogo_insulator() {
    translate([0, 0, -seat_height + 0.51])
        xy_centered_cube([pogo_insulator_size[0], pogo_insulator_size[1],
                          pogo_insulator_top - 0.51 + 0.1]);
}

module dowel_tops() {
    translate([alignment_pin_offset[0], 0, base_top_z])
        mirrored_y(alignment_pin_offset[1])
            cylinder(r=0.794, h=dowel_top_z - base_top_z);
}

// Inserts standing proud of their posts, plus the minimum clearance.
module insert_allowance() {
    translate([0, 0, base_top_z])
        post_holes(post_radius, insert_proud_allowance + lid_post_clearance_min);
}

// In the checks the tag is lifted 0.5 um off the groove floor and the lid
// 1 um: seated parts touch face to face, which CGAL reports as a zero-volume
// leftover rather than an empty result.
check_lift = makechecks ? 0.001 : 0;
tag_check_lift = makechecks ? 0.0005 : 0;

module lid_in_place(b, nb, on_tab) {
    translate([0, 0, lid_z(b, nb, on_tab) + check_lift]) makeLid(nb);
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

check_boards = presv6_fits ? boards : [BT7, BTNG, PT3, PT5];

if (makechecks) {
    // Each of these must be empty.
    for (b = check_boards) {
        intersection() { makeBase(); tag_board(b); }
        intersection() { makeBase(); tag_cells(b); }
        intersection() { pogo_insulator(); tag_board(b); }
        // No-battery lid on the bare board; battery lid on the tab foot and,
        // the worst case for the cell, on the bare board beside it.
        for (pose = [[true, false], [false, true], [false, false]]) {
            intersection() { lid_in_place(b, pose[0], pose[1]); tag_board(b); }
            intersection() { lid_in_place(b, pose[0], pose[1]); makeBase(); }
            intersection() { lid_in_place(b, pose[0], pose[1]); insert_allowance(); }
            intersection() { lid_in_place(b, pose[0], pose[1]); dowel_tops(); }
        }
        intersection() { lid_in_place(b, false, true); tag_cells(b); }
        // Block on the bare board: the tab is then not where the model puts
        // it, so only the cell bodies count.
        intersection() { lid_in_place(b, false, false); tag_cell_bodies(b); }
    }
    // The design rules, as geometry: anything non-empty here is a violation.
    if (pogo_compression < pogo_mid_stroke || pogo_compression > pogo_max_stroke - 0.3)
        cube(1);
} else if (makeassembly) {
    makeBase();
    lid_in_place(BTNG, lid_no_battery, !lid_no_battery);
    %tag_board(BTNG);
    %tag_cells(BTNG);
} else {
    if (makebase) makeBase();
    if (makelid) translate([0, 0, lid_preview_z]) makeLid();
}
