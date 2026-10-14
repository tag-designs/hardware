$fn = 120; // steps in generating circles

makelid = true;
makebase = true;
// Second lid, for testing a board before its coin cell is fitted: the
// pogo-end block reaches down to the board top instead of the cell. A standard
// part of every case (Mechanical/TAGCASE-PROCESS.md, step 6).
lid_no_battery = false;
makeassembly = false;  // base + lid in place, with the tag as simple solids
makechecks = false;    // interference volumes only; should render empty

// Imprinted in base and lid. Bold text at a printable size leaves room for six
// characters between the lid screw bosses, so this names the type only.
version_string = "UIUC";

// Fits BoardDesigns/Tags/UIUCTag (19 x 10 mm). Started from
// Mechanical/BitPresTagBMP585; the changes and derivations are in README.md.
// Relative to J201 the board is the parent's, except 1 mm longer at the far
// end, with the ADXL362 (U2) and its neighbours re-placed.
//
// All dimensions are millimeters. XY coordinates are board-centered with +x
// toward the pogo/battery end and +y up the screen; KiCad's y runs down, so
// case y = 108 - kicad_y and case x = kicad_x - 148.5. Z=0 is the board
// underside.
eps = 0.1;

// ---------------------------------------------------------------------------
// Board and manufacturing tolerances
// ---------------------------------------------------------------------------

board_nominal_len = 19;
board_nominal_width = 10;
board_thickness = 0.4;             // (general (thickness 0.4)) in the .kicad_pcb
board_corner_radius = 1.0;
board_sweep_height = 4.0;          // vertical clearance swept by the PCB

board_edge_clearance = 0.0015 * 25.4; // routing/board-fab tolerance per edge
board_len = board_nominal_len + board_edge_clearance * 2;
board_width = board_nominal_width + board_edge_clearance * 2;
board_top_z = board_thickness;

// Envelope of the B.Cu courtyards (U2, U302, C1-C4, R2), from
// Mechanical/tools/board_geometry.py. The
// under-board pocket is this plus a clearance, so the ledges are as wide as
// the bottom-side parts allow rather than a fixed inset from the board edge.
bottom_parts_min = [-8.22, -3.95];
bottom_parts_max = [3.79, 3.92];
bottom_parts_height = 1.06;        // ADXL362 CC-16-4 (U2) is the tallest
bottom_parts_clearance = 0.2;
under_board_cut_depth = 1.5;


// J301-J304: 1.1 mm harness holes in the board corners.
corner_hole_x = [-8.07, 5.78];   // J303/J304 avg -8.07, J301/J302 5.78
corner_hole_y = 3.75;
corner_hole_radius = 0.55;

// ---------------------------------------------------------------------------
// Coin cell (J401)
// ---------------------------------------------------------------------------

// Cell centres as each cell sits when its tabs are soldered to the J401 pads.
// The feet end 5.9 mm (MS621F) and 8.05 mm (MS920SE-FL27E) from the cell
// centre, so the MS920 sits 2 mm further out. Both overhang the pogo-end
// board edge. Radii are the models' outer rims. Checked in FreeCAD with the
// real models by `make assembly`.
ms621_center = [9.3, 0];          // J401 at x 4.30, + 5.0
ms621_radius = 3.68;
ms920_center = [11.33, 0];        // J401 + 7.03
ms920_radius = 5.14;
battery_radius_clearance = 0.4;
battery_cell_bottom_gap = 0.15;    // under-cell tab lifts the cell off the board
battery_stack_height = 2.7;        // board top to top of the MS621 positive tab

// Beyond the board end the base keeps a shelf up to battery_stop_height, so
// the board edge has a positive stop across its full width. The under-cell tab
// leaves the board edge flat at board-top height, so the shelf is notched
// lower where the tabs cross it.
battery_stop_height = board_top_z - 0.05;
battery_tab_notch_halfwidth = 1.5; // tabs span y -0.75..1.25 (MS920), +-1 (MS621)
battery_tab_notch_height = board_top_z - 0.15;
battery_top_z = board_top_z + battery_stack_height;

// ---------------------------------------------------------------------------
// Pogo pins, posts, and alignment features
// ---------------------------------------------------------------------------

// 855 series: 6.27 free height, compressed by its 0.0275" (0.70) mid stroke.
pogo_pin_height_at_board = 6.27 - 0.7;
pogo_cutout_len = 3.2;
pogo_cutout_width = 7;
pogo_center = [6.9, 0.0];          // J201

post_center = [pogo_center[0] - 5.0, pogo_center[1]];
post_spacing = 20.0;
post_radius = 3.0;
insert_hole_radius = 1.65;         // press fit for 2-56 insert
screw_hole_radius = 1.3;           // clearance for 2-56 screw

// The (-5, +-6.5) pair is in both 6pin_tagpoints_new_offset and
// 6pin_tagpoints_double_screws, so it fits every base. The (-8.5, +-10) pair
// exists only on the double-screw (lipo) base.
alignment_pin_offset = [-5.0, 6.5];
lipo_alignment_pin_offset = [-8.5, 10];
enable_lipo_alignment_pins = false;
alignment_pin_radius = 0.75;       // press fit for 1/16" dowel

// ---------------------------------------------------------------------------
// Case dimensions
// ---------------------------------------------------------------------------

case_margin_len = 8.0;
case_margin_width = 7.0;
base_len = board_len + case_margin_len;
base_width = board_width + case_margin_width;
base_extra_height = 1;             // base top above the board underside
base_height = pogo_pin_height_at_board + base_extra_height;

// Each slot covers its corner holes, set so its -x edge sits just past the
// holes' -x edge: at the far end that keeps the end ledge wide, at the pogo
// end it keeps a support bar between the pocket and the slot.
harness_slot_width = 2.5;
harness_slot_margin = 0.1;
function harness_slot_x(hole_x) =
    hole_x - corner_hole_radius - harness_slot_margin + harness_slot_width / 2;

// The pocket runs on into the pogo-end harness slot. Stopping it at the B.Cu
// envelope (x 3.99) left a 1.14 x 1.5 mm free-standing bar between the pocket
// and the slot/pogo window that does not print well; nothing under the board
// needs it.
under_pocket_min = bottom_parts_min - [1, 1] * bottom_parts_clearance;
under_pocket_max = [harness_slot_x(corner_hole_x[1]),
                    bottom_parts_max[1] + bottom_parts_clearance];

// ---------------------------------------------------------------------------
// Lid dimensions
// ---------------------------------------------------------------------------

lid_preview_z = 10;
lid_body_height = 3;
lid_end_height = 4;

// The lid floats on its screws: the pogo-end block bears on the cell above
// the pogo pins and sets the lid height; the far block bears on the board.
// The pogo drop is the previous BitPresTag lid's, so the screws still reach.
lid_pogo_block_drop = 2.1;
lid_pogo_block_len = 2;
lid_pogo_block_width = board_width - 1;


// Stops short of the board by lid_far_block_gap so the pogo end always seats
// first; screw tension closes the gap. Kept inside the corner holes in y, 0.25
// in from the board end, and 0.25 clear of C7 (x -7.57) in x.
lid_far_block_gap = 0.2;
lid_far_block_drop = lid_pogo_block_drop + battery_stack_height - lid_far_block_gap;
lid_far_block_x = [-9.25, -7.82];
lid_far_block_width = 5.2;

// No-battery lid: with no cell to clear it sits lower, so both end blocks are
// short. The pogo-end block lands on the board top directly above J201; the
// far block is shorter by lid_far_block_gap so the pogo end still seats
// first. The drop is 2.6, not the standard lid's 2.1: at 2.1 the lid underside
// cleared U3 (BMP585, 1.96 tall) by 0.055 and the dowel tops by 0.095; 2.6
// gives ~0.55 to both (make assembly). The screws run 2.3 further into the
// (through) inserts. The pogo-end block is narrowed to stay
// 0.25 clear of the J301/J302 harness holes, which it would otherwise cover.
lid_nb_pogo_block_drop = 2.6;
lid_nb_far_block_drop = lid_nb_pogo_block_drop - lid_far_block_gap;
lid_nb_assembled_z = board_top_z + lid_nb_pogo_block_drop;
lid_nb_pogo_block_width = 2 * (corner_hole_y - corner_hole_radius - 0.25);

lid_body_x = [lid_far_block_x[0], pogo_center[0] + lid_pogo_block_len / 2];
lid_assembled_z = battery_top_z + lid_pogo_block_drop;

// ---------------------------------------------------------------------------
// Engraving
// ---------------------------------------------------------------------------

// Bold, larger and deeper than the earlier cases, whose text printed too thin.
text_font = "Liberation Sans:style=Bold";
text_grow = 0.05;                  // per-side stroke growth
text_size_base = 3;
text_size_lid = 2.6;
text_depth_base = 0.8;
text_depth_lid = 0.8;

base_text_pos = [-4.5, 0, -pogo_pin_height_at_board];
// The "*" pogo-end markers. The asterisk sits high in its em box (at size s
// it spans y -0.04s..+0.50s with valign="center"), so marker() recentres it on
// its real extent. Beyond the board end the battery relief reaches y 5.54, so
// the base marker is centred in the strip between that arc and the base edge
// (y 8.54), 0.54 clear of each and 1.1 from the end; the earlier size-3 marker
// ran to within 0.02 of the edge. The lid marker sits 0.9 in from the lid's
// pogo end and ~1 clear of the lid text. Positions are formulas so the
// rule carries to other boards.
marker_size_base = 3.5;            // glyph 1.99 x 1.92
marker_size_lid = 5;               // glyph 2.81 x 2.70
base_marker_pos = [base_len / 2 - 2.04,
                   (ms920_radius + battery_radius_clearance + base_width / 2) / 2,
                   base_extra_height];
lid_marker_pos = [pogo_center[0] + lid_pogo_block_len / 2 - 2.3, 0, lid_body_height];
lid_text_pos = [post_center[0], 0, lid_body_height];

// The no-battery lid keeps the version text and adds this label on the lid
// body, centred between the far block and the crossbar. A suffix on the
// version text does not fit: six bold characters already fill the crossbar.
lid_nb_text = "TEST";              // 9.08 x 2.66 at text_size_lid; lid body is 10.08 wide
lid_nb_text_pos = [(lid_far_block_x[0] + post_center[0] - post_radius) / 2, 0, lid_body_height];

// Extra base support added around the post bosses.
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
    for (side = [-1, 1]) {
        translate([0, side * y, 0]) children();
    }
}

module at_post_center() {
    translate([post_center[0], post_center[1], 0]) children();
}

module rounded_rect_2d(size, radius) {
    hull() {
        for (x = [-1, 1], y = [-1, 1]) {
            translate([
                x * (size[0] / 2 - radius),
                y * (size[1] / 2 - radius)
            ])
                circle(r=radius);
        }
    }
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
                text(text=s, size=size, font=text_font,
                     halign="center", valign="center");
}

// ---------------------------------------------------------------------------
// Board volume
// ---------------------------------------------------------------------------

module board_clearance_volume() {
    linear_extrude(height=board_sweep_height, convexity=10)
        square([board_len, board_width], center=true);
}

// ---------------------------------------------------------------------------
// Shared post geometry
// ---------------------------------------------------------------------------

module crossbar_solid(height, end_height) {
    at_post_center() {
        xy_centered_cube([2 * post_radius, post_spacing, height]);
        mirrored_y(post_spacing / 2)
            cylinder(r=post_radius, h=end_height);
    }
}

module crossbar_with_holes(height, end_height, hole_radius) {
    difference() {
        crossbar_solid(height, end_height);
        post_holes(hole_radius, end_height);
    }
}

module reinforced_base_crossbar(height) {
    at_post_center() {
        mirrored_y(post_spacing / 2) {
            cylinder(r=post_radius, h=height);
            translate([base_post_secondary_x, 0, 0])
                cylinder(r=post_radius, h=height);
            translate([base_post_fill_x, 0, 0])
                xy_centered_cube([base_post_fill_len, base_post_fill_width, height]);
        }
    }
}

module post_holes(radius, height) {
    at_post_center()
        mirrored_y(post_spacing / 2)
            cylinder(r=radius, h=height);
}

// ---------------------------------------------------------------------------
// Base
// ---------------------------------------------------------------------------

module base_solid() {
    translate([0, 0, -pogo_pin_height_at_board]) {
        xy_centered_cube([base_len, base_width, base_height]);
        reinforced_base_crossbar(base_height);
    }
}

module under_board_pocket() {
    box_from(under_pocket_min, under_pocket_max,
             -under_board_cut_depth, board_sweep_height);
}

module harness_slots() {
    for (hx = corner_hole_x)
        translate([harness_slot_x(hx), 0, -under_board_cut_depth])
            xy_centered_cube([harness_slot_width, base_width + eps,
                              board_sweep_height + under_board_cut_depth]);
}

module pogo_pin_cutout() {
    translate([pogo_center[0], pogo_center[1], -pogo_pin_height_at_board - eps])
        xy_centered_cube([pogo_cutout_len, pogo_cutout_width, pogo_pin_height_at_board + 4.0]);
}

module alignment_pin_pair(offset) {
    translate([
        pogo_center[0] + offset[0],
        pogo_center[1],
        -pogo_pin_height_at_board - eps
    ])
        mirrored_y(offset[1])
            cylinder(r=alignment_pin_radius, h=base_height + 2 * eps);
}

module alignment_pin_holes() {
    alignment_pin_pair(alignment_pin_offset);
    if (enable_lipo_alignment_pins)
        alignment_pin_pair(lipo_alignment_pin_offset);
}

module base_insert_holes() {
    translate([0, 0, -pogo_pin_height_at_board - eps])
        post_holes(insert_hole_radius, base_height + 2 * eps);
}

// Hull over both cells, beyond the board end only: over the board the
// clearance volume already opens the space, and both cells are narrower than
// the board there.
module battery_relief() {
    intersection() {
        translate([0, 0, battery_stop_height])
            linear_extrude(board_sweep_height)
                hull() {
                    translate(ms621_center) circle(r=ms621_radius + battery_radius_clearance);
                    translate(ms920_center) circle(r=ms920_radius + battery_radius_clearance);
                }
        translate([board_len / 2, -base_width, -board_sweep_height])
            cube([base_len, 2 * base_width, 3 * board_sweep_height]);
    }
    translate([board_len / 2 - eps, -battery_tab_notch_halfwidth, battery_tab_notch_height])
        cube([base_len, 2 * battery_tab_notch_halfwidth, board_sweep_height]);
}

module base_engraving() {
    // Underside, mirrored so it reads from below.
    translate(base_text_pos - [0, 0, eps])
        mirror([1, 0, 0])
            engraved_text(version_string, text_size_base, text_depth_base);

    // Top face at the pogo/battery end.
    translate(base_marker_pos - [0, 0, text_depth_base])
        marker(marker_size_base, text_depth_base);
}

module base_cutouts() {
    under_board_pocket();
    harness_slots();
    pogo_pin_cutout();
    alignment_pin_holes();
    base_insert_holes();
    battery_relief();
    base_engraving();
    board_clearance_volume();
}

module makeBase() {
    difference() {
        base_solid();
        base_cutouts();
    }
}

// ---------------------------------------------------------------------------
// Lid (lid coordinates: z=0 is the lid underside)
// ---------------------------------------------------------------------------

module lid_solid(nb) {
    crossbar_with_holes(lid_body_height, lid_end_height, screw_hole_radius);

    // Bears on the board at the end away from the battery.
    box_from([lid_far_block_x[0], -lid_far_block_width / 2],
             [lid_far_block_x[1],  lid_far_block_width / 2],
             -(nb ? lid_nb_far_block_drop : lid_far_block_drop), lid_body_height);

    // Bears on the cell above the pogo pins -- or, on the no-battery lid, on
    // the board itself.
    drop = nb ? lid_nb_pogo_block_drop : lid_pogo_block_drop;
    width = nb ? lid_nb_pogo_block_width : lid_pogo_block_width;
    translate([pogo_center[0], pogo_center[1], -drop])
        xy_centered_cube([lid_pogo_block_len, width, drop + lid_body_height]);

    box_from([lid_body_x[0], -board_width / 2],
             [lid_body_x[1],  board_width / 2],
             0, lid_body_height);
}

module lid_engraving(nb) {
    translate(lid_text_pos - [0, 0, text_depth_lid])
        engraved_text(version_string, text_size_lid, text_depth_lid);

    if (nb)
        translate(lid_nb_text_pos - [0, 0, text_depth_lid])
            engraved_text(lid_nb_text, text_size_lid, text_depth_lid);

    translate(lid_marker_pos - [0, 0, text_depth_lid])
        marker(marker_size_lid, text_depth_lid);
}

module makeLid(nb=lid_no_battery) {
    difference() {
        lid_solid(nb);
        lid_engraving(nb);
    }
}

// ---------------------------------------------------------------------------
// Tag, for assembly preview and interference checks
// ---------------------------------------------------------------------------

// F.Cu courtyards (case coordinates) and body heights above the board top.
top_parts = [
    // [min, max, height]
    [[-1.22, -0.67], [2.48, 3.13], 1.96],  // U3 BMP585
    [[-0.03, -3.96], [2.77, -0.76], 0.44], // U1 flash
    [[-2.79, -3.94], [-0.29, -1.74], 0.60], // U501 RV-3028
    [[-5.66, -1.26], [-4.20, 1.70], 0.80], // C6 0603
    [[-6.74, -1.23], [-5.81, 0.58], 0.50], // C404 0402
    [[2.86, -3.97], [3.80, -2.11], 0.50],  // D401
    [[-7.57, -1.26], [-6.88, 0.14], 0.30], // C7
    [[-3.53, 1.92], [-2.53, 3.33], 0.50],  // Q501 SOT-883 (moved to F.Cu)
    [[-3.57, -3.71], [-0.24, 2.10], 0.30]  // R1, C5, C501, C502, C503, C504
];

module tag_board() {
    linear_extrude(board_thickness)
        difference() {
            rounded_rect_2d([board_nominal_len, board_nominal_width], board_corner_radius);
            for (hx = corner_hole_x) mirrored_y(corner_hole_y)
                translate([hx, 0]) circle(r=corner_hole_radius);
        }
    box_from(bottom_parts_min, bottom_parts_max, -bottom_parts_height, 0);
    for (p = top_parts)
        box_from(p[0], p[1], board_top_z, board_top_z + p[2]);
}

module tag_battery(center, radius) {
    translate([center[0], center[1], board_top_z + battery_cell_bottom_gap])
        cylinder(r=radius, h=battery_stack_height - battery_cell_bottom_gap);
    // Under-cell tab, flat at board-top height, out past the board edge.
    translate([0, -1.25, board_top_z])
        cube([center[0], 2.5, battery_cell_bottom_gap]);
}

module tag() {
    tag_board();
    tag_battery(ms621_center, ms621_radius);
    tag_battery(ms920_center, ms920_radius);
}

// The standard lid sits on the cell; the no-battery one, a cell stack lower,
// with its pogo-end block on the board top.
module lid_in_place(nb=lid_no_battery) {
    translate([0, 0, nb ? lid_nb_assembled_z : lid_assembled_z]) makeLid(nb);
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

if (makechecks) {
    // Each of these must be empty.
    intersection() { makeBase(); tag(); }
    intersection() { lid_in_place(false); tag_board(); }
    intersection() { lid_in_place(false); makeBase(); }
    intersection() { lid_in_place(true); tag_board(); }
    intersection() { lid_in_place(true); makeBase(); }
} else if (makeassembly) {
    makeBase();
    lid_in_place();
    %tag();
} else {
    if (makebase) makeBase();
    if (makelid) translate([0, 0, lid_preview_z]) makeLid();
}
