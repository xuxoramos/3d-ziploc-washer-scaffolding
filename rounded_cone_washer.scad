// ============================================================
// Rounded Cone Washer Scaffold for Ziploc Bags
// ============================================================
// A dishwasher-safe mesh cone scaffold for holding Ziploc bags
// open during a dishwasher cycle – designed for the BOTTOM RACK.
//
// Dishwasher usage (INVERTED orientation):
//   1. Place the scaffold INVERTED (large opening facing DOWN) in
//      the BOTTOM rack.  The rounded large rim rests on the tines
//      and protects the bag seal.
//   2. Push the cone inside a Ziploc bag so the bag opening faces
//      DOWNWARD, stretched over the rounded large rim.
//   3. Run on a normal or eco cycle.  Mesh holes allow free water
//      flow; the narrow top lets water drain back down.
//
// Recommended materials (bottom rack – up to 65–70 °C):
//   - ASA (preferred): Best for bottom rack. Heat-resistant to
//     ~95°C, excellent UV stability, handles repeated cycles.
//   - PETG: Good all-round choice. Heat-resistant to ~80°C,
//     food-safe grades available; comfortable margin above
//     bottom-rack temperatures.
//   - PLA / PLA+: NOT suitable – bottom-rack temperatures
//     exceed PLA's heat-deflection point; parts will warp.
//
// Recommended print settings:
//   - Layer height: 0.2 mm
//   - Infill: 20–30 % (Gyroid or Honeycomb)
//   - Perimeters/walls: 3
//   - Supports: None required
//   - Bed adhesion: Brim (5 mm) recommended
//   - Print orientation: Upright (large opening facing UP for a
//     stable print footprint); flip the part when loading into
//     the dishwasher.
// ============================================================

// ── Parametric dimensions ────────────────────────────────────
top_diameter    = 130;   // mm – large opening (bag-opening end; faces DOWN in use)
bottom_diameter =  50;   // mm – narrow drainage opening (faces UP in use)
cone_height     = 160;   // mm – overall height of the cone
wall_thickness  =   2;   // mm – shell thickness
edge_radius     =   4;   // mm – rounding radius on the top rim

// ── Mesh / hole parameters ───────────────────────────────────
hole_diameter   =   8;   // mm – diameter of each mesh hole
hole_rows       =   6;   // number of rows of holes along the height
hole_cols       =  16;   // number of holes around the circumference

// ── Resolution ───────────────────────────────────────────────
$fn = 128;  // smoothness of circles/cylinders

// ============================================================
// Helper: solid truncated cone shell
// ============================================================
module cone_shell() {
    top_r_outer    = top_diameter    / 2;
    top_r_inner    = top_r_outer    - wall_thickness;
    bottom_r_outer = bottom_diameter / 2;
    bottom_r_inner = bottom_r_outer - wall_thickness;

    difference() {
        // Outer surface
        cylinder(h = cone_height,
                 r1 = bottom_r_outer,
                 r2 = top_r_outer);
        // Inner cavity (hollow shell)
        translate([0, 0, -0.1])
            cylinder(h = cone_height + 0.2,
                     r1 = bottom_r_inner,
                     r2 = top_r_inner);
    }
}

// ============================================================
// Helper: rounded top rim (torus added at top edge)
// ============================================================
module top_rim_rounding() {
    top_r_outer = top_diameter / 2;

    translate([0, 0, cone_height])
    rotate_extrude()
        translate([top_r_outer - edge_radius, 0, 0])
            circle(r = edge_radius);
}

// ============================================================
// Helper: bottom drainage ring (small flat annulus)
// ============================================================
module bottom_ring() {
    bottom_r_outer = bottom_diameter / 2;
    ring_height    = wall_thickness;

    difference() {
        cylinder(h = ring_height, r = bottom_r_outer);
        translate([0, 0, -0.1])
            cylinder(h = ring_height + 0.2,
                     r = bottom_r_outer - wall_thickness);
    }
}

// ============================================================
// Helper: mesh hole at a given position on the cone surface
// Each hole is a cylinder oriented radially outward.
// ============================================================
module mesh_holes() {
    top_r    = top_diameter    / 2;
    bot_r    = bottom_diameter / 2;

    for (row = [0 : hole_rows - 1]) {
        // Fraction along the height (avoid very top and bottom)
        frac = (row + 1) / (hole_rows + 1);
        z    = frac * cone_height;

        // Interpolated outer radius at this height
        r_at_z = bot_r + (top_r - bot_r) * frac;

        // Offset columns by half a step on alternating rows (honeycomb offset)
        col_offset = (row % 2 == 0) ? 0 : (360 / hole_cols / 2);

        for (col = [0 : hole_cols - 1]) {
            angle = col * (360 / hole_cols) + col_offset;

            // Rotate around Z, then move outward to the cone surface
            rotate([0, 0, angle])
            translate([r_at_z, 0, z])
            rotate([0, 90, 0])   // orient cylinder radially
                cylinder(h = wall_thickness * 4,
                         r = hole_diameter / 2,
                         center = true);
        }
    }
}

// ============================================================
// Assembly
// ============================================================
difference() {
    union() {
        cone_shell();
        top_rim_rounding();
        bottom_ring();
    }
    mesh_holes();
}
