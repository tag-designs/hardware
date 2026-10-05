#!/usr/bin/env freecadcmd
# -*- coding: utf-8 -*-
"""
tagcase_param.py -- one parametric FreeCAD model for the pogo-pin tag cases.

A single core model (base + lid) covering the BitPresTag and CompassTag
families.  A specific board is described by a JSON variant file listing only
the cells that differ from the defaults below:

    freecadcmd tagcase_param.py -- --params CompassTag/CompassTagv1.json
    freecadcmd tagcase_param.py -- --params BitPresTag/BitPresTag.json --stl

Every value lives in the document's `params` spreadsheet, and every sketch
constraint, pad/pocket length and feature-enable flag is bound to it by
expression, so a board can also be re-specialized by editing cells in the GUI
-- including the optional features, via PartDesign's `Suppressed` property.

Document structure
------------------
    params        Spreadsheet: every dimension, aliased.  Derived values are
                  spreadsheet formulas.
    BaseBody      PartDesign Body -- the base.
    LidBody       PartDesign Body -- the lid.
    Base / Lid    Part::Cut of the body with its engraving.  Cutting the text
                  through Part (rather than a PartDesign Pocket) keeps `name`
                  a live spreadsheet value, since a ShapeString cannot be a
                  PartDesign profile.

Coordinates follow the .scad sources: XY board-centered, Z = 0 at the nominal
board underside, base extending down to -pogo_pin_height_at_board.  The lid is
drawn lifted by `lid_preview_z`; set it to 0 to assemble the parts.

Optional features (spreadsheet flags, 1 = present)
--------------------------------------------------
    enable_base_crossbar        solid bar joining the two post bosses
                                (CompassTag) -- BitPresTag omits it
    enable_post_boss_aux        second pair of bosses (BitPresTag)
    enable_post_web             web filling between boss pairs (BitPresTag)
    enable_battery_pocket       round battery relief
    enable_battery_end_pocket   rectangular battery-end relief (CompassTag)

A variant file may also carry build settings, as keys prefixed with "_":
    {"_out": "CompassTagv1-param.FCStd", "_doc_name": "CompassTagv1_param",
     "_stl_prefix": "CompassTagv1-fc", "_stl": true}
Relative "_out" is resolved against the variant file's own directory.
"""

import json
import os
import re
import sys

import FreeCAD as App
import Part
import Sketcher

V = App.Vector

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:                                   # exec()'d in the GUI console
    SCRIPT_DIR = os.getcwd()

# ---------------------------------------------------------------------------
# Core defaults.  These populate the `params` spreadsheet; a variant file
# overrides individual aliases.
#
# Entries are (alias, content, comment).  Content beginning with '=' is a
# spreadsheet formula and may reference any alias in the sheet.
# ---------------------------------------------------------------------------

SECTIONS = [
    ("Identity", [
        ("name", "BitPrTagv1", "engraved in base and lid"),
        ("marker", "*", "second, larger engraved glyph"),
        ("font_file", "/System/Library/Fonts/Supplemental/Arial.ttf",
         "TrueType file for the engraving (OpenSCAD's default is "
         "Liberation Sans)"),
    ]),
    ("Optional features", [
        ("enable_base_crossbar", "0",
         "1 = solid bar between the post bosses (CompassTag); "
         "0 = bosses only (BitPresTag)"),
        ("enable_post_boss_aux", "1", "1 = second pair of post bosses"),
        ("enable_post_web", "1", "1 = web between the boss pairs"),
        ("enable_battery_pocket", "1", "1 = round battery relief"),
        ("enable_battery_end_pocket", "0",
         "1 = rectangular battery-end relief (CompassTag)"),
    ]),
    ("Tolerance", [
        ("eps", "0.1 mm", "boolean-overlap fudge, from the .scad sources"),
    ]),
    ("Pogo pins", [
        ("pogo_pin_full_height", "6.27 mm", "pin free length"),
        ("pogo_pin_board_inset", "0.7 mm", "pin length taken up by the board"),
        ("pogo_pin_height_at_board", "=pogo_pin_full_height - pogo_pin_board_inset",
         "base depth below the board underside"),
        ("pogo_cutout_len", "3.2 mm", "pogo window, X"),
        ("pogo_cutout_width", "7 mm", "pogo window, Y"),
        ("pogo_center_x", "6.4 mm", "pogo block center, X (board-relative)"),
        ("pogo_center_y", "0 mm", "pogo block center, Y (board-relative)"),
    ]),
    ("Posts and inserts", [
        ("post_offset_from_pogo", "-5.0 mm", "post center X, relative to pogo center"),
        ("post_center_x", "=pogo_center_x + post_offset_from_pogo", ""),
        ("post_center_y", "=pogo_center_y", ""),
        ("post_spacing", "20.0 mm", "post-to-post distance in Y"),
        ("post_radius", "3.0 mm", ""),
        ("base_crossbar_width", "=post_radius * 2",
         "X width of the optional base crossbar"),
        ("insert_hole_radius", "1.65 mm", "clearance for a 2-56 insert (base)"),
        ("screw_hole_radius", "1.3 mm", "clearance for a 2-56 screw (lid)"),
        ("base_post_secondary_dx", "-3.5 mm", "aux boss, relative to post center X"),
        ("base_post_web_dx", "-1.75 mm", "web center, relative to post center X"),
        ("base_post_web_len", "3.5 mm", ""),
        ("base_post_web_width", "6 mm", ""),
    ]),
    ("Alignment pins", [
        ("alignment_pin_dx", "-8.5 mm", "relative to pogo center X"),
        ("alignment_pin_dy", "10 mm", "+/- about pogo center Y"),
        ("alignment_pin_radius", "0.75 mm", ""),
    ]),
    ("Board", [
        ("board_nominal_len", "18 mm", "PCB X"),
        ("board_nominal_width", "10 mm", "PCB Y"),
        ("board_edge_clearance", "=0.0015 * 25.4 mm", "board-fab tolerance per edge"),
        ("board_len", "=board_nominal_len + board_edge_clearance * 2", ""),
        ("board_width", "=board_nominal_width + board_edge_clearance * 2", ""),
        ("board_sweep_height", "4.0 mm", "vertical clearance swept by the PCB"),
        ("board_min_thickness", "0.4 mm", "fiberglass thickness"),
        ("under_board_ledges", "1.5 mm", "total ledge width supporting the board"),
        ("under_board_cut_depth", "1.5 mm", "pocket depth below the board underside"),
    ]),
    ("Battery relief", [
        ("battery_diameter", "10.5 mm", "round relief"),
        ("battery_height", "3 mm", ""),
        ("battery_x", "=battery_diameter / 2 + pogo_center_x - 0.2 mm", ""),
        ("battery_y", "0 mm", ""),
        ("battery_z", "=board_min_thickness", "relief floor"),
        ("battery_end_len", "5 mm", "rectangular relief, X"),
        ("battery_end_width", "7 mm", "rectangular relief, Y"),
        ("battery_end_x", "=board_len / 2 - 1 mm + battery_end_len / 2", ""),
        ("battery_end_y", "0 mm", ""),
        ("battery_end_z", "=board_min_thickness", ""),
        ("battery_end_height", "=board_sweep_height", ""),
    ]),
    ("Case", [
        ("case_margin_len", "8.0 mm", "base overhang beyond the board, X (total)"),
        ("case_margin_width", "7.0 mm", "base overhang beyond the board, Y (total)"),
        ("base_len", "=board_len + case_margin_len", ""),
        ("base_width", "=board_width + case_margin_width", ""),
        ("base_extra_height", "1 mm", "base height above the board underside"),
        ("base_height", "=pogo_pin_height_at_board + base_extra_height", ""),
        ("harness_slot_width", "2.5 mm", ""),
        ("harness_slot_x", "=board_len / 2 - under_board_ledges / 2 - harness_slot_width / 2",
         "+/- about board center"),
    ]),
    ("Lid", [
        ("lid_preview_z", "10 mm", "exploded-view lift; 0 puts the lid in place"),
        ("lid_body_height", "3 mm", ""),
        ("lid_end_height", "4 mm", "nominal height of the two end blocks"),
        ("lid_end_len", "2 mm", "end block length, X"),
        ("lid_end_width", "=board_width - 1 mm", "pogo-end block width, Y"),
        ("lid_left_end_inset", "1.5 mm", "left end block center, in from the board edge"),
        ("lid_left_end_x", "=-board_len / 2 + lid_left_end_inset", ""),
        ("lid_left_end_width", "=lid_end_width - 1 mm", "left end block width, Y"),
        ("lid_left_end_drop", "2.1 mm",
         "how far the left end block hangs below -lid_end_height/2"),
        ("lid_pogo_end_z_shift", "-0.1 mm",
         "pogo end block floor, relative to -lid_end_height/2"),
        ("lid_pogo_end_extra", "0.1 mm",
         "pogo end block height, relative to lid_end_height"),
        ("lid_body_inset", "0.5 mm", "lid body start, in from the board edge"),
        ("lid_body_x", "=-board_len / 2 + lid_body_inset", "lid body minimum X"),
        ("lid_body_len_trim", "1.1 mm", "shortening of the lid body past the pogo window"),
        ("lid_body_len", "=board_len / 2 + pogo_cutout_len / 2 + pogo_center_x - lid_body_len_trim",
         ""),
    ]),
    ("Engraving", [
        ("text_size", "2 mm", "cap height of the version string"),
        ("marker_size", "3 mm", "cap height of the marker glyph"),
        ("text_depth_base", "0.5 mm", ""),
        ("text_depth_lid", "0.6 mm", ""),
        ("base_text_x", "0 mm", ""),
        ("base_text_y", "0 mm", ""),
        ("base_text_z", "=-pogo_pin_height_at_board + 0.4 mm",
         "0.4 mm above the base underside -> 0.4 mm deep engraving"),
        ("base_marker_x", "8 mm", ""),
        ("base_marker_y", "4.5 mm", ""),
        ("base_marker_z", "=board_sweep_height / 2 - 0.4 mm",
         "cuts the base top face only when base_height reaches it: with "
         "base_extra_height = 1 it floats clear and removes nothing, exactly "
         "as in BitPresTag.scad; with 2 (CompassTag) it engraves"),
        ("lid_text_x", "1.5 mm", ""),
        ("lid_text_y", "0 mm", ""),
        ("lid_text_z", "2.5 mm", "0.5 mm below the lid top face"),
        ("lid_marker_x", "5 mm", ""),
        ("lid_marker_y", "1 mm", ""),
        ("lid_marker_z", "2.5 mm", ""),
    ]),
]

TEXT_ALIASES = ("name", "marker", "font_file")

BUILD = {
    "make_base": True,
    "make_lid": True,
    "engrave": True,
    "doc_name": "TagCase_param",
    "out": os.path.join(SCRIPT_DIR, "TagCase-param.FCStd"),
    "stl": False,
    "stl_prefix": "TagCase-fc",
}


# ---------------------------------------------------------------------------
# Spreadsheet
# ---------------------------------------------------------------------------

_NEG = re.compile(r"^-\s*[0-9.]+(\s*[a-zA-Z]+)?$")


def _cell_content(value):
    """FreeCAD's cell parser stores a bare negative quantity ('-5 mm') as text,
    so promote those to a formula."""
    text = str(value)
    return "=" + text if _NEG.match(text) else text


def build_spreadsheet(doc, overrides=None):
    """Create the `params` sheet: col A label, col B value (aliased), col C note."""
    overrides = dict(overrides or {})
    unknown = set(overrides) - {a for _, e in SECTIONS for a, _c, _m in e}
    if unknown:
        raise RuntimeError("variant sets unknown parameters: %s"
                           % ", ".join(sorted(unknown)))

    sheet = doc.addObject("Spreadsheet::Sheet", "params")
    sheet.Label = "params"
    row = 1
    for title, entries in SECTIONS:
        sheet.set("A%d" % row, "[ %s ]" % title)
        row += 1
        for alias, content, comment in entries:
            if alias in overrides:
                content = overrides[alias]
            sheet.set("A%d" % row, alias)
            sheet.set("B%d" % row, _cell_content(content))
            sheet.setAlias("B%d" % row, alias)
            if comment:
                sheet.set("C%d" % row, comment)
            row += 1
        row += 1
    doc.recompute(None, True)

    # Fail loudly and specifically rather than letting a bad cell poison every
    # downstream feature with a null shape.
    problems = []
    for _, entries in SECTIONS:
        for alias, _c, _m in entries:
            try:
                val = sheet.get(sheet.getCellFromAlias(alias))
            except Exception as exc:
                problems.append("%s: %s" % (alias, exc))
                continue
            if isinstance(val, str) and alias not in TEXT_ALIASES:
                problems.append("%s: stored as text (%r), expected a quantity"
                                % (alias, val))
    if problems or "Invalid" in (sheet.State or []):
        raise RuntimeError("params spreadsheet is invalid:\n  "
                           + "\n  ".join(problems or ["(no bad cell identified)"]))
    return sheet


# ---------------------------------------------------------------------------
# Sketch helpers
#
# Every primitive is fully constrained and every driving constraint is named
# and bound to a spreadsheet expression, so the sketches stay solvable and
# editable in the GUI.
# ---------------------------------------------------------------------------

def _origin_plane(body, role):
    for feat in body.Origin.OriginFeatures:
        if getattr(feat, "Role", "") == role:
            return feat
    raise RuntimeError("origin plane %s not found" % role)


def _ev(sheet, expr):
    """Numeric value of an expression string, used to seed sketch geometry."""
    val = sheet.evalExpression(expr)
    try:
        return float(val.Value)          # Quantity
    except AttributeError:
        return float(val)


def _name_last(sk, tag):
    sk.renameConstraint(sk.ConstraintCount - 1, tag)


def _add_rect(sk, sheet, tag, cx, cy, ln, wd):
    """Origin-referenced, centered rectangle. Constraints: <tag>_len/_wid/_cx/_cy."""
    cxn, cyn = _ev(sheet, cx), _ev(sheet, cy)
    lnn, wdn = abs(_ev(sheet, ln)) or 1.0, abs(_ev(sheet, wd)) or 1.0
    x0, x1 = cxn - lnn / 2.0, cxn + lnn / 2.0
    y0, y1 = cyn - wdn / 2.0, cyn + wdn / 2.0
    g = len(sk.Geometry)
    sk.addGeometry(Part.LineSegment(V(x0, y0, 0), V(x1, y0, 0)), False)
    sk.addGeometry(Part.LineSegment(V(x1, y0, 0), V(x1, y1, 0)), False)
    sk.addGeometry(Part.LineSegment(V(x1, y1, 0), V(x0, y1, 0)), False)
    sk.addGeometry(Part.LineSegment(V(x0, y1, 0), V(x0, y0, 0)), False)
    sk.addGeometry(Part.Point(V(cxn, cyn, 0)), True)          # center, construction
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        sk.addConstraint(Sketcher.Constraint("Coincident", g + a, 2, g + b, 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", g + 0))
    sk.addConstraint(Sketcher.Constraint("Horizontal", g + 2))
    sk.addConstraint(Sketcher.Constraint("Vertical", g + 1))
    sk.addConstraint(Sketcher.Constraint("Vertical", g + 3))
    sk.addConstraint(Sketcher.Constraint("Symmetric", g + 0, 1, g + 2, 1, g + 4, 1))
    sk.addConstraint(Sketcher.Constraint("DistanceX", g + 0, 1, g + 0, 2, lnn))
    _name_last(sk, tag + "_len")
    sk.addConstraint(Sketcher.Constraint("DistanceY", g + 1, 1, g + 1, 2, wdn))
    _name_last(sk, tag + "_wid")
    sk.addConstraint(Sketcher.Constraint("DistanceX", g + 4, 1, cxn))
    _name_last(sk, tag + "_cx")
    sk.addConstraint(Sketcher.Constraint("DistanceY", g + 4, 1, cyn))
    _name_last(sk, tag + "_cy")
    sk.setExpression("Constraints.%s_len" % tag, ln)
    sk.setExpression("Constraints.%s_wid" % tag, wd)
    sk.setExpression("Constraints.%s_cx" % tag, cx)
    sk.setExpression("Constraints.%s_cy" % tag, cy)


def _add_circle(sk, sheet, tag, cx, cy, r):
    """Origin-referenced circle. Constraints: <tag>_r/_cx/_cy."""
    cxn, cyn, rn = _ev(sheet, cx), _ev(sheet, cy), abs(_ev(sheet, r)) or 1.0
    g = len(sk.Geometry)
    sk.addGeometry(Part.Circle(V(cxn, cyn, 0), V(0, 0, 1), rn), False)
    sk.addConstraint(Sketcher.Constraint("Radius", g, rn))
    _name_last(sk, tag + "_r")
    sk.addConstraint(Sketcher.Constraint("DistanceX", g, 3, cxn))
    _name_last(sk, tag + "_cx")
    sk.addConstraint(Sketcher.Constraint("DistanceY", g, 3, cyn))
    _name_last(sk, tag + "_cy")
    sk.setExpression("Constraints.%s_r" % tag, r)
    sk.setExpression("Constraints.%s_cx" % tag, cx)
    sk.setExpression("Constraints.%s_cy" % tag, cy)


def sketch(doc, sheet, body, name, z_expr, prims):
    """Create a sketch on the body's XY plane, offset in Z by `z_expr`.

    `prims` is a list of ("rect", tag, cx, cy, len, wid) or
    ("circle", tag, cx, cy, r), all values being expression strings.
    """
    sk = doc.addObject("Sketcher::SketchObject", name)
    body.addObject(sk)
    sk.AttachmentSupport = [(_origin_plane(body, "XY_Plane"), "")]
    sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(V(0, 0, _ev(sheet, z_expr)), App.Rotation())
    sk.setExpression("AttachmentOffset.Base.z", z_expr)
    for prim in prims:
        if prim[0] == "rect":
            _add_rect(sk, sheet, prim[1], prim[2], prim[3], prim[4], prim[5])
        else:
            _add_circle(sk, sheet, prim[1], prim[2], prim[3], prim[4])
    doc.recompute()
    if not sk.FullyConstrained:
        print("  ! sketch %s is not fully constrained (solver=%s)"
              % (name, sk.solve()))
    return sk


# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------

def _finish(doc, feat, label, enable):
    """Bind the optional-feature flag, then validate unless it is switched off.

    PartDesign's Suppressed accepts an expression, so which features exist is
    itself a spreadsheet value rather than a script-time decision.
    """
    if enable:
        feat.setExpression("Suppressed", "%s == 0" % enable)
    doc.recompute(None, True)
    if getattr(feat, "Suppressed", False):
        print("  - %s suppressed by %s" % (label, enable))
        return feat
    bad = []
    if "Invalid" in (feat.State or []):
        bad.append("marked invalid (see the Report view)")
    try:
        if feat.Shape.isNull():
            bad.append("null shape")
        elif not feat.Shape.isValid():
            bad.append("invalid shape")
    except Exception as exc:
        bad.append("no shape: %s" % exc)
    if bad:
        raise RuntimeError("%s (%s): %s" % (label, feat.Name, "; ".join(bad)))
    return feat


def pad(doc, sheet, body, name, sk, length_expr, reversed_=False,
        midplane=False, enable=None):
    f = body.newObject("PartDesign::Pad", name)
    f.Profile = sk
    f.Length = max(_ev(sheet, length_expr), 0.01)
    f.setExpression("Length", length_expr)
    f.Reversed = reversed_
    f.Midplane = midplane
    return _finish(doc, f, "pad " + name, enable)


def pocket(doc, sheet, body, name, sk, length_expr=None,
           reversed_=False, midplane=False, enable=None):
    f = body.newObject("PartDesign::Pocket", name)
    f.Profile = sk
    if length_expr is None:
        f.Type = "ThroughAll"
    else:
        f.Type = "Length"
        f.Length = max(_ev(sheet, length_expr), 0.01)
        f.setExpression("Length", length_expr)
    f.Reversed = reversed_
    f.Midplane = midplane
    return _finish(doc, f, "pocket " + name, enable)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

def build_base(doc, sheet):
    body = doc.addObject("PartDesign::Body", "BaseBody")
    body.Label = "BaseBody"

    bottom = "-params.pogo_pin_height_at_board"

    # --- solid -------------------------------------------------------------
    sk = sketch(doc, sheet, body, "sk_base_block", bottom,
                [("rect", "blk", "0 mm", "0 mm", "params.base_len", "params.base_width")])
    pad(doc, sheet, body, "base_block", sk, "params.base_height")

    # The crossbar between the posts.  CompassTag.scad has the solid bar;
    # BitPresTag.scad has it commented out and adds a second boss pair plus a
    # web instead.  All three are modelled and switched by flag.
    sk = sketch(doc, sheet, body, "sk_base_crossbar", bottom,
                [("rect", "cb", "params.post_center_x", "params.post_center_y",
                  "params.base_crossbar_width", "params.post_spacing")])
    pad(doc, sheet, body, "base_crossbar", sk, "params.base_height",
        enable="params.enable_base_crossbar")

    sk = sketch(doc, sheet, body, "sk_post_boss_main", bottom, [
        ("circle", "n", "params.post_center_x",
         "params.post_center_y + params.post_spacing / 2", "params.post_radius"),
        ("circle", "s", "params.post_center_x",
         "params.post_center_y - params.post_spacing / 2", "params.post_radius"),
    ])
    pad(doc, sheet, body, "post_boss_main", sk, "params.base_height")

    # Separate pads because the boss pairs and the web overlap each other, and
    # PartDesign rejects self-intersecting profiles.
    sk = sketch(doc, sheet, body, "sk_post_boss_aux", bottom, [
        ("circle", "n", "params.post_center_x + params.base_post_secondary_dx",
         "params.post_center_y + params.post_spacing / 2", "params.post_radius"),
        ("circle", "s", "params.post_center_x + params.base_post_secondary_dx",
         "params.post_center_y - params.post_spacing / 2", "params.post_radius"),
    ])
    pad(doc, sheet, body, "post_boss_aux", sk, "params.base_height",
        enable="params.enable_post_boss_aux")

    sk = sketch(doc, sheet, body, "sk_post_web", bottom, [
        ("rect", "n", "params.post_center_x + params.base_post_web_dx",
         "params.post_center_y + params.post_spacing / 2",
         "params.base_post_web_len", "params.base_post_web_width"),
        ("rect", "s", "params.post_center_x + params.base_post_web_dx",
         "params.post_center_y - params.post_spacing / 2",
         "params.base_post_web_len", "params.base_post_web_width"),
    ])
    pad(doc, sheet, body, "post_web", sk, "params.base_height",
        enable="params.enable_post_web")

    # --- cuts --------------------------------------------------------------
    sk = sketch(doc, sheet, body, "sk_under_board", "-params.under_board_cut_depth",
                [("rect", "pk", "0 mm", "0 mm",
                  "params.board_len - params.under_board_ledges",
                  "params.board_width - params.under_board_ledges")])
    pocket(doc, sheet, body, "under_board_pocket", sk, reversed_=True)

    # Harness slots.  Made 2*eps longer than the base in Y so the cut faces are
    # not coplanar with the base side walls (both .scad files used exactly
    # base_width); the end fillet circles in the .scad sources fall entirely
    # outside the base wall and removed nothing, so they are omitted.
    sk = sketch(doc, sheet, body, "sk_harness_slots", "-params.under_board_cut_depth", [
        ("rect", "e", "params.harness_slot_x", "0 mm",
         "params.harness_slot_width", "params.base_width + params.eps * 2"),
        ("rect", "w", "-params.harness_slot_x", "0 mm",
         "params.harness_slot_width", "params.base_width + params.eps * 2"),
    ])
    pocket(doc, sheet, body, "harness_slots", sk, reversed_=True)

    # The swept PCB envelope, removed from z = 0 up.
    sk = sketch(doc, sheet, body, "sk_board_clearance", "0 mm",
                [("rect", "bd", "0 mm", "0 mm", "params.board_len", "params.board_width")])
    pocket(doc, sheet, body, "board_clearance", sk, reversed_=True)

    # Through-cuts.  Both .scad files extruded these a finite amount that
    # always exited both faces; ThroughAll + Midplane is the robust equivalent
    # and stays correct if the base gets taller.
    sk = sketch(doc, sheet, body, "sk_pogo_window", "0 mm",
                [("rect", "pg", "params.pogo_center_x", "params.pogo_center_y",
                  "params.pogo_cutout_len", "params.pogo_cutout_width")])
    pocket(doc, sheet, body, "pogo_window", sk, midplane=True)

    sk = sketch(doc, sheet, body, "sk_alignment_pins", "0 mm", [
        ("circle", "n", "params.pogo_center_x + params.alignment_pin_dx",
         "params.pogo_center_y + params.alignment_pin_dy", "params.alignment_pin_radius"),
        ("circle", "s", "params.pogo_center_x + params.alignment_pin_dx",
         "params.pogo_center_y - params.alignment_pin_dy", "params.alignment_pin_radius"),
    ])
    pocket(doc, sheet, body, "alignment_pin_holes", sk, midplane=True)

    sk = sketch(doc, sheet, body, "sk_insert_holes", "0 mm", [
        ("circle", "n", "params.post_center_x",
         "params.post_center_y + params.post_spacing / 2", "params.insert_hole_radius"),
        ("circle", "s", "params.post_center_x",
         "params.post_center_y - params.post_spacing / 2", "params.insert_hole_radius"),
    ])
    pocket(doc, sheet, body, "insert_holes", sk, midplane=True)

    sk = sketch(doc, sheet, body, "sk_battery", "params.battery_z",
                [("circle", "bt", "params.battery_x", "params.battery_y",
                  "params.battery_diameter / 2")])
    pocket(doc, sheet, body, "battery_pocket", sk, "params.battery_height",
           reversed_=True, enable="params.enable_battery_pocket")

    sk = sketch(doc, sheet, body, "sk_battery_end", "params.battery_end_z",
                [("rect", "be", "params.battery_end_x", "params.battery_end_y",
                  "params.battery_end_len", "params.battery_end_width")])
    pocket(doc, sheet, body, "battery_end_pocket", sk, "params.battery_end_height",
           reversed_=True, enable="params.enable_battery_end_pocket")

    doc.recompute()
    return body


# ---------------------------------------------------------------------------
# Lid
# ---------------------------------------------------------------------------

def build_lid(doc, sheet):
    body = doc.addObject("PartDesign::Body", "LidBody")
    body.Label = "LidBody"

    z0 = "params.lid_preview_z"

    sk = sketch(doc, sheet, body, "sk_lid_body", z0,
                [("rect", "bd", "params.lid_body_x + params.lid_body_len / 2", "0 mm",
                  "params.lid_body_len", "params.board_width")])
    pad(doc, sheet, body, "lid_body", sk, "params.lid_body_height")

    sk = sketch(doc, sheet, body, "sk_lid_crossbar", z0,
                [("rect", "cb", "params.post_center_x", "params.post_center_y",
                  "params.post_radius * 2", "params.post_spacing")])
    pad(doc, sheet, body, "lid_crossbar", sk, "params.lid_body_height")

    sk = sketch(doc, sheet, body, "sk_lid_post_ends", z0, [
        ("circle", "n", "params.post_center_x",
         "params.post_center_y + params.post_spacing / 2", "params.post_radius"),
        ("circle", "s", "params.post_center_x",
         "params.post_center_y - params.post_spacing / 2", "params.post_radius"),
    ])
    pad(doc, sheet, body, "lid_post_ends", sk, "params.lid_end_height")

    sk = sketch(doc, sheet, body, "sk_lid_end_left",
                z0 + " - params.lid_end_height / 2 - params.lid_left_end_drop",
                [("rect", "el", "params.lid_left_end_x", "0 mm",
                  "params.lid_end_len", "params.lid_left_end_width")])
    pad(doc, sheet, body, "lid_end_left", sk,
        "params.lid_end_height + params.lid_left_end_drop")

    sk = sketch(doc, sheet, body, "sk_lid_end_pogo",
                z0 + " - params.lid_end_height / 2 + params.lid_pogo_end_z_shift",
                [("rect", "ep", "params.pogo_center_x", "params.pogo_center_y",
                  "params.lid_end_len", "params.lid_end_width")])
    pad(doc, sheet, body, "lid_end_pogo", sk,
        "params.lid_end_height + params.lid_pogo_end_extra")

    sk = sketch(doc, sheet, body, "sk_lid_screw_holes", z0, [
        ("circle", "n", "params.post_center_x",
         "params.post_center_y + params.post_spacing / 2", "params.screw_hole_radius"),
        ("circle", "s", "params.post_center_x",
         "params.post_center_y - params.post_spacing / 2", "params.screw_hole_radius"),
    ])
    pocket(doc, sheet, body, "lid_screw_holes", sk, midplane=True)

    doc.recompute()
    return body


# ---------------------------------------------------------------------------
# Engraving
#
# Each cutter reproduces the .scad transform exactly:
#     translate(pos) rotate(rot) linear_extrude(depth) text(..., halign, valign)
# ShapeString.Justification covers OpenSCAD's halign/valign directly, so the
# placement needs no reference to the glyph extents and the whole chain stays
# live when `name` changes:
#     halign="center", valign="baseline" -> Bottom-Center / Cap Height
#                                           (baseline at local y = 0)
#     halign="center", valign="center"   -> Middle-Center / Cap Height
# ---------------------------------------------------------------------------

_JUSTIFY = {
    ("center", "baseline"): "Bottom-Center",
    ("center", "center"): "Middle-Center",
    ("left", "baseline"): "Bottom-Left",
}


def _shapestring(doc, sheet, name, string_expr, size_expr, halign, valign):
    import Draft
    ss = Draft.make_shapestring(String=str(sheet.evalExpression(string_expr)),
                                FontFile=sheet.get("font_file"),
                                Size=_ev(sheet, size_expr), Tracking=0)
    ss.Label = name
    ss.Justification = _JUSTIFY[(halign, valign)]
    ss.JustificationReference = "Cap Height"
    ss.setExpression("Size", size_expr)
    try:
        ss.setExpression("String", string_expr)
    except Exception as exc:
        print("  ! could not bind %s.String to %s (%s); value baked in"
              % (name, string_expr, exc))
    doc.recompute()
    return ss


def _text_cutter(doc, sheet, name, string_expr, size_expr, depth_expr,
                 pos_expr, rot, halign="center", valign="baseline"):
    """Extruded, placed text solid.  `rot` is an App.Rotation; `pos_expr` is
    an (x, y, z) tuple of expression strings giving the .scad translate()."""
    ss = _shapestring(doc, sheet, name + "_glyphs", string_expr, size_expr,
                      halign, valign)

    ext = doc.addObject("Part::Extrusion", name)
    ext.Label = name
    ext.Base = ss
    ext.DirMode = "Custom"
    ext.Dir = V(0, 0, 1)
    ext.LengthFwd = _ev(sheet, depth_expr)
    ext.setExpression("LengthFwd", depth_expr)
    ext.Solid = True
    ext.Placement = App.Placement(V(0, 0, 0), rot)
    for axis, expr in zip(("x", "y", "z"), pos_expr):
        ext.setExpression("Placement.Base.%s" % axis, expr)
    doc.recompute(None, True)
    if ext.Shape.isNull() or not ext.Shape.isValid():
        raise RuntimeError("text cutter %s produced no valid solid" % name)
    return ext


def build_engraving(doc, sheet, part, body):
    """Cut `part`'s engraving from `body`; returns the resulting Part::Cut."""
    if part == "base":
        # rotate([0, 180, -90]) == Rz(-90) * Ry(180): the string reads
        # correctly when the base is viewed from underneath.
        rot_text = App.Rotation(V(0, 0, 1), -90).multiply(App.Rotation(V(0, 1, 0), 180))
        cutters = [
            _text_cutter(doc, sheet, "base_text", "params.name", "params.text_size",
                         "params.text_depth_base",
                         ("params.base_text_x", "params.base_text_y", "params.base_text_z"),
                         rot_text, halign="center", valign="baseline"),
            _text_cutter(doc, sheet, "base_marker", "params.marker", "params.marker_size",
                         "params.text_depth_base",
                         ("params.base_marker_x", "params.base_marker_y",
                          "params.base_marker_z"),
                         App.Rotation(), halign="center", valign="baseline"),
        ]
        label = "Base"
    else:
        lz = "params.lid_preview_z + "
        cutters = [
            _text_cutter(doc, sheet, "lid_text", "params.name", "params.text_size",
                         "params.text_depth_lid",
                         ("params.lid_text_x", "params.lid_text_y",
                          lz + "params.lid_text_z"),
                         App.Rotation(V(0, 0, 1), -90), halign="center", valign="center"),
            _text_cutter(doc, sheet, "lid_marker", "params.marker", "params.marker_size",
                         "params.text_depth_lid",
                         ("params.lid_marker_x", "params.lid_marker_y",
                          lz + "params.lid_marker_z"),
                         App.Rotation(), halign="center", valign="baseline"),
        ]
        label = "Lid"

    fuse = doc.addObject("Part::MultiFuse", part + "_engraving")
    fuse.Label = part + "_engraving"
    fuse.Shapes = cutters
    doc.recompute()

    cut = doc.addObject("Part::Cut", label)
    cut.Label = label
    cut.Base = body
    cut.Tool = fuse
    doc.recompute()
    if not cut.Shape.isValid():
        raise RuntimeError("%s engraving cut produced an invalid shape" % label)
    return cut


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _show_only(doc, keep):
    """Part::Cut / Part::MultiFuse built by script do not hide their inputs the
    way the GUI commands do, which would otherwise leave the sketches and the
    engraving cutter solids floating in the 3D view."""
    if not App.GuiUp:
        return
    import FreeCADGui
    for obj in doc.Objects:
        vo = getattr(obj, "ViewObject", None)
        if vo is not None and hasattr(vo, "Visibility"):
            vo.Visibility = obj.Name in keep
    visible = [o.Name for o in doc.Objects
               if getattr(getattr(o, "ViewObject", None), "Visibility", False)]
    print("visible objects:", ", ".join(visible) or "(none)")
    FreeCADGui.SendMsgToActiveView("ViewFit")


def build(overrides=None, build_opts=None):
    opts = dict(BUILD)
    opts.update(build_opts or {})

    if opts["doc_name"] in App.listDocuments():
        App.closeDocument(opts["doc_name"])
    if opts["out"]:
        target = os.path.abspath(opts["out"])
        for name, existing in list(App.listDocuments().items()):
            if os.path.abspath(existing.FileName or "") == target:
                App.closeDocument(name)
    doc = App.newDocument(opts["doc_name"])

    sheet = build_spreadsheet(doc, overrides)
    results = {}

    if opts["make_base"]:
        body = build_base(doc, sheet)
        results["Base"] = (build_engraving(doc, sheet, "base", body)
                           if opts["engrave"] else body)
    if opts["make_lid"]:
        body = build_lid(doc, sheet)
        results["Lid"] = (build_engraving(doc, sheet, "lid", body)
                          if opts["engrave"] else body)

    doc.recompute()

    for label, obj in results.items():
        s = obj.Shape
        print("%-5s solids=%d volume=%.4f bbox=(%.4f %.4f %.4f)-(%.4f %.4f %.4f)"
              % (label, len(s.Solids), s.Volume,
                 s.BoundBox.XMin, s.BoundBox.YMin, s.BoundBox.ZMin,
                 s.BoundBox.XMax, s.BoundBox.YMax, s.BoundBox.ZMax))
        if len(s.Solids) != 1:
            print("  ! %s is not a single solid -- check the enable flags" % label)

    _show_only(doc, set(results))

    if opts["out"]:
        doc.saveAs(opts["out"])
        print("saved", opts["out"])

    if opts["stl"]:
        import Mesh
        outdir = os.path.dirname(opts["out"] or ".") or "."
        for label, obj in results.items():
            path = os.path.join(outdir, "%s-%s.stl"
                                % (opts["stl_prefix"], label.lower()))
            Mesh.export([obj], path)
            print("exported", path)

    return doc, results


def load_variant(path):
    """Split a variant file into spreadsheet overrides and build options."""
    with open(path) as fh:
        data = json.load(fh)
    overrides, opts = {}, {}
    here = os.path.dirname(os.path.abspath(path))
    for key, val in data.items():
        if not key.startswith("_"):
            overrides[key] = val
            continue
        opt = key[1:]
        if opt == "out" and val and not os.path.isabs(val):
            val = os.path.join(here, val)
        opts[opt] = val
    return overrides, opts


def _parse_argv(argv):
    overrides, opts = {}, {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--stl":
            opts["stl"] = True
        elif a == "--no-save":
            opts["out"] = None
        elif a == "--base-only":
            opts["make_lid"] = False
        elif a == "--lid-only":
            opts["make_base"] = False
        elif a == "--no-engrave":
            opts["engrave"] = False
        elif a == "--out":
            i += 1
            opts["out"] = argv[i]
        elif a == "--params":
            i += 1
            vo, vb = load_variant(argv[i])
            overrides.update(vo)
            opts.update(vb)
        elif a == "--set":
            i += 1
            k, _, v = argv[i].partition("=")
            overrides[k] = v
        i += 1
    return overrides, opts


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    elif argv and argv[0].endswith(".py"):
        argv = argv[1:]
    _o, _b = _parse_argv(argv)
    build(_o, _b)
