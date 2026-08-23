$fn = 120; // steps in generating circles

makelid = true;
makebase = true;

version_string = "IMUTagv1"; // imprinted in base and lid

// All dimensions are millimeters. XY coordinates are board-centered unless
// otherwise noted; Z=0 is the nominal board underside.
eps = 0.1;

// ---------------------------------------------------------------------------
// Board and manufacturing tolerances
// ---------------------------------------------------------------------------

board_nominal_len = 21.550;
board_nominal_width = 11.5;
board_sweep_height = 4.0;          // vertical clearance swept by the PCB
board_min_thickness = 0.4;         // fiberglass thickness, kept for reference

board_edge_clearance = 0.001 * 25.4; // routing/board-fab tolerance per edge
board_len = board_nominal_len + board_edge_clearance * 2;
board_width = board_nominal_width + board_edge_clearance * 2;

use_dxf_sized_board_outline = true;
board_outline_dxf = "IMUTag-Edge_Cuts.dxf";
board_dxf_center = [150.828553, -107.250];
board_outline_offset = [-board_dxf_center[0], -board_dxf_center[1]];
board_dxf_size = [21.542893, 11.500000];

// KiCad exports Edge.Cuts as stroked linework, not a filled region. Use the
// measured centerline extents from the DXF to build a filled boolean cutter.
board_corner_radius = 1.0;

// The under-board pocket is intentionally smaller than the board outline so
// the board remains supported by a ledge.
under_board_ledges = 1.5;
under_board_cut_depth = 1.5;

// ---------------------------------------------------------------------------
// Pogo pins, posts, and alignment features
// ---------------------------------------------------------------------------

pogo_pin_height_at_board = 6.27 - 0.9;
pogo_cutout_len = 3.2;
pogo_cutout_width = 7;
pogo_center = [8.175, 0.0];

post_center = [pogo_center[0] - 5.0, pogo_center[1]];
post_spacing = 20.0;
post_radius = 3.0;
insert_hole_radius = 1.65;         // clearance for 2-56 insert
screw_hole_radius = 1.3;           // clearance for 2-56 screw

alignment_pin_offset = [-8.5, 10];
alignment_pin_radius = 0.75;

// ---------------------------------------------------------------------------
// Case dimensions
// ---------------------------------------------------------------------------

case_margin_len = 8.0;
case_margin_width = 7.0;
base_len = board_len + case_margin_len;
base_width = board_width + case_margin_width;
base_height = pogo_pin_height_at_board + 1;

harness_slot_width = 2.5;
harness_slot_radius = harness_slot_width / 2;
harness_slot_x = board_len / 2 - under_board_ledges / 2 - harness_slot_radius;

base_text_pos = [-4, 0, -pogo_pin_height_at_board + 0.4];
base_marker_pos = [8, 4.5, board_sweep_height / 2 - 0.4];
lid_text_pos = [3, 0, 2.5];
lid_marker_pos = [7, 1, 2.5];
text_depth_base = 0.5;
text_depth_lid = 0.6;

// ---------------------------------------------------------------------------
// Lid dimensions
// ---------------------------------------------------------------------------

lid_preview_z = 10;
lid_body_height = 3;
lid_end_height = 4;
lid_end_len = 2;
lid_end_width = board_width - 1;
lid_left_end_x = -board_len / 2 + 2;
lid_body_x = -board_len / 2 + 0.1;
lid_body_len = board_len / 2 - 0.7 + pogo_cutout_len / 2 + pogo_center[0];

// Extra base support added around the post bosses.
base_post_bridge_x = -2.5;
base_post_bridge_extra_len = 5;
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

module mirrored_y(y) {
    for (side = [-1, 1]) {
        translate([0, side * y, 0]) children();
    }
}

module at_post_center() {
    translate([post_center[0], post_center[1], 0]) children();
}

// ---------------------------------------------------------------------------
// Board volume
// ---------------------------------------------------------------------------

module raw_board_outline_2d() {
    if (use_dxf_sized_board_outline) {
        rounded_rect_2d([
            board_dxf_size[0] + board_edge_clearance * 2,
            board_dxf_size[1] + board_edge_clearance * 2
        ], board_corner_radius + board_edge_clearance);
    } else {
        square([board_len, board_width], center=true);
    }
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

module dxf_stroke_outline_2d() {
    translate(board_outline_offset)
        import(file=board_outline_dxf);
}

module board_support_pocket_2d() {
    offset(delta=-under_board_ledges / 2) raw_board_outline_2d();
}

module board_clearance_volume() {
    linear_extrude(height=board_sweep_height, convexity=10)
        raw_board_outline_2d();
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

module reinforced_base_crossbar(height, end_height) {
    at_post_center() {
        translate([base_post_bridge_x, 0, 0])
            xy_centered_cube([2 * post_radius + base_post_bridge_extra_len, post_spacing, height]);

        mirrored_y(post_spacing / 2) {
            cylinder(r=post_radius, h=end_height);
            translate([base_post_secondary_x, 0, 0])
                cylinder(r=post_radius, h=end_height);
            translate([base_post_fill_x, 0, 0])
                xy_centered_cube([base_post_fill_len, base_post_fill_width, end_height]);
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
        reinforced_base_crossbar(base_height, base_height);
    }
}

module under_board_pocket() {
    cut_height = board_sweep_height + under_board_cut_depth;

    translate([0, 0, -under_board_cut_depth]) {
        if (use_dxf_sized_board_outline) {
            linear_extrude(height=cut_height, convexity=10)
                board_support_pocket_2d();
        } else {
            xy_centered_cube([board_len - under_board_ledges, board_width - under_board_ledges, cut_height]);
        }

        translate([-harness_slot_x, 0, 0])
            xy_centered_cube([harness_slot_width, base_width, cut_height]);
        translate([harness_slot_x, 0, 0])
            xy_centered_cube([harness_slot_width, base_width, cut_height]);

        translate([harness_slot_x, base_width / 2, 0])
            cylinder(r=harness_slot_radius, h=cut_height);
        translate([harness_slot_x, -base_width / 2, 0])
            cylinder(r=harness_slot_radius, h=cut_height);
    }
}

module pogo_pin_cutout() {
    translate([pogo_center[0], pogo_center[1], -pogo_pin_height_at_board - eps])
        xy_centered_cube([pogo_cutout_len, pogo_cutout_width, pogo_pin_height_at_board + 4.0]);
}

module alignment_pin_holes() {
    translate([
        pogo_center[0] + alignment_pin_offset[0],
        pogo_center[1],
        -pogo_pin_height_at_board - eps
    ])
        mirrored_y(alignment_pin_offset[1])
            cylinder(r=alignment_pin_radius, h=board_sweep_height + pogo_pin_height_at_board);
}

module base_insert_holes() {
    translate([0, 0, -6])
        post_holes(insert_hole_radius, base_height + 2);
}

module base_engraving() {
    translate(base_text_pos)
        rotate(a=[0, 180, -90])
            linear_extrude(text_depth_base)
                text(text=version_string, size=2, halign="center");

    translate(base_marker_pos)
        linear_extrude(text_depth_base)
            text(text="*", size=3, halign="center");
}

module base_cutouts() {
    under_board_pocket();
    pogo_pin_cutout();
    alignment_pin_holes();
    base_insert_holes();
    base_engraving();
}

module makeBase() {
    difference() {
        base_solid();
        base_cutouts();
    }
}

// ---------------------------------------------------------------------------
// Lid
// ---------------------------------------------------------------------------

module lid_solid() {
    crossbar_with_holes(lid_body_height, lid_end_height, screw_hole_radius);

    // End piece inset from board edge.
    translate([lid_left_end_x, 0, -lid_end_height / 2 - eps])
        xy_centered_cube([lid_end_len, lid_end_width - 1, lid_end_height + eps]);

    // Centered over the pogo pins.
    translate([pogo_center[0], pogo_center[1], -lid_end_height / 2 - 1.8])
        xy_centered_cube([lid_end_len, lid_end_width, lid_end_height + 1.8]);

    translate([lid_body_x, -board_width / 2, 0])
        cube([lid_body_len, board_width, lid_body_height]);
}

module lid_engraving() {
    translate(lid_text_pos)
        rotate(a=[0, 0, -90])
            linear_extrude(text_depth_lid)
                text(text=version_string, size=2, halign="center", valign="center");

    translate(lid_marker_pos)
        linear_extrude(text_depth_lid)
            text(text="*", size=3, halign="center");
}

module makeLid() {
    translate([0, 0, lid_preview_z])
        difference() {
            lid_solid();
            lid_engraving();
        }
}

if (makebase) {
    difference() {
        makeBase();
        board_clearance_volume();
    }
}

if (makelid) makeLid();
