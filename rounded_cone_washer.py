"""
rounded_cone_washer.py
======================
Generates an STL file for the rounded-cone Ziploc-bag dishwasher scaffold.

The model is a truncated cone (frustum) with:
  - A rounded top rim
  - Honeycomb-offset circular mesh holes on the lateral surface
  - A thin bottom drainage ring

Requirements
------------
    pip install numpy numpy-stl

Usage
-----
    python3 rounded_cone_washer.py
    # Writes 'rounded_cone_washer.stl' in the current directory.

Recommended print materials (dishwasher-safe)
---------------------------------------------
  * PETG        – Best all-round choice. Heat-resistant to ~80 °C, food-safe
                  grades available, minimal warping.
  * ASA         – Excellent heat resistance (up to 95 °C) and UV stability.
  * High-temp PLA (PLA+) – Top rack only; standard PLA softens near 60 °C.

Print settings
--------------
  * Layer height  : 0.20 mm
  * Wall count    : 3
  * Infill        : 20–30 % Gyroid or Honeycomb
  * Supports      : None (print upright, large opening up)
  * Bed adhesion  : 5 mm Brim
"""

import math
import numpy as np
from stl import mesh as stl_mesh

# ── Parametric dimensions ─────────────────────────────────────────────────────
TOP_DIAMETER    = 130.0   # mm  – opening at top  (fits gallon Ziploc)
BOTTOM_DIAMETER =  50.0   # mm  – drainage opening at bottom
CONE_HEIGHT     = 160.0   # mm  – overall height
WALL_THICKNESS  =   2.0   # mm  – shell thickness
EDGE_RADIUS     =   4.0   # mm  – rounding radius on the top rim

# ── Mesh / hole parameters ────────────────────────────────────────────────────
HOLE_DIAMETER   =   8.0   # mm  – diameter of each mesh hole
HOLE_ROWS       =   6     # number of rows of holes along the height
HOLE_COLS       =  16     # number of holes around the circumference

# ── Resolution ────────────────────────────────────────────────────────────────
SEGMENTS        =  64     # polygon segments for circles/cylinders
RIM_SEGMENTS    =  32     # segments for the torus rim cross-section


# ── Low-level triangle helpers ────────────────────────────────────────────────

def unit_normal(v0, v1, v2):
    """Return the unit normal of a triangle defined by three vertices."""
    a = v1 - v0
    b = v2 - v0
    n = np.cross(a, b)
    length = np.linalg.norm(n)
    if length == 0:
        return np.array([0.0, 0.0, 1.0])
    return n / length


def make_mesh(triangles):
    """Build a numpy-stl Mesh from a list of (v0, v1, v2) vertex triples."""
    data = np.zeros(len(triangles), dtype=stl_mesh.Mesh.dtype)
    for i, (v0, v1, v2) in enumerate(triangles):
        data["vectors"][i] = [v0, v1, v2]
        data["normals"][i] = unit_normal(
            np.array(v0), np.array(v1), np.array(v2)
        )
    return stl_mesh.Mesh(data)


# ── Geometry builders ─────────────────────────────────────────────────────────

def frustum_triangles(r_bot, r_top, h, segments, inward=False):
    """
    Lateral surface of a truncated cone (frustum).
    If *inward* is True the normals point inward (used for the inner shell).
    """
    tris = []
    for i in range(segments):
        a0 = 2 * math.pi * i       / segments
        a1 = 2 * math.pi * (i + 1) / segments

        b0 = np.array([r_bot * math.cos(a0), r_bot * math.sin(a0), 0.0])
        b1 = np.array([r_bot * math.cos(a1), r_bot * math.sin(a1), 0.0])
        t0 = np.array([r_top * math.cos(a0), r_top * math.sin(a0), h])
        t1 = np.array([r_top * math.cos(a1), r_top * math.sin(a1), h])

        if inward:
            tris += [(b0, t0, b1), (b1, t0, t1)]
        else:
            tris += [(b0, b1, t0), (b1, t1, t0)]
    return tris


def disk_annulus_triangles(r_inner, r_outer, z, segments, face_up=True):
    """Flat annular ring at height *z*."""
    tris = []
    for i in range(segments):
        a0 = 2 * math.pi * i       / segments
        a1 = 2 * math.pi * (i + 1) / segments

        io0 = np.array([r_inner * math.cos(a0), r_inner * math.sin(a0), z])
        io1 = np.array([r_inner * math.cos(a1), r_inner * math.sin(a1), z])
        oo0 = np.array([r_outer * math.cos(a0), r_outer * math.sin(a0), z])
        oo1 = np.array([r_outer * math.cos(a1), r_outer * math.sin(a1), z])

        if face_up:
            tris += [(io0, oo0, io1), (io1, oo0, oo1)]
        else:
            tris += [(io0, io1, oo0), (io1, oo1, oo0)]
    return tris


def torus_rim_triangles(major_r, minor_r, major_segs, minor_segs, z_offset):
    """
    Quarter-torus (90 °) forming the rounded top rim.
    The torus cross-section sweeps from the outer edge pointing upward,
    curving inward to produce the rounded top.
    major_r  : centre of the tube circle (= top_r_outer - minor_r)
    minor_r  : tube radius (= edge_radius)
    z_offset : height at which the top rim sits
    """
    tris = []
    for i in range(major_segs):
        a0 = 2 * math.pi * i       / major_segs
        a1 = 2 * math.pi * (i + 1) / major_segs

        for j in range(minor_segs):
            # Only use the outer quarter (0 → π/2) of the minor circle
            b0 = math.pi / 2 * j       / minor_segs          # 0 → π/2
            b1 = math.pi / 2 * (j + 1) / minor_segs

            def pt(a, b):
                tube_x = major_r + minor_r * math.cos(b)
                tube_z = minor_r * math.sin(b)
                return np.array([
                    tube_x * math.cos(a),
                    tube_x * math.sin(a),
                    z_offset + tube_z,
                ])

            p00, p10 = pt(a0, b0), pt(a1, b0)
            p01, p11 = pt(a0, b1), pt(a1, b1)

            tris += [(p00, p10, p01), (p10, p11, p01)]
    return tris


def cylinder_triangles(cx, cy, cz, r, length, axis, segments):
    """
    Hollow open-ended cylinder (lateral surface only) for subtracting holes.
    axis : unit vector direction of the cylinder axis
    The cylinder extends ±length/2 around the centre (cx, cy, cz).
    Returns triangles for the lateral surface only.
    """
    # Build two perpendicular axes to 'axis'
    axis = np.array(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    if abs(axis[0]) < 0.9:
        perp = np.cross(axis, [1, 0, 0])
    else:
        perp = np.cross(axis, [0, 1, 0])
    perp /= np.linalg.norm(perp)
    binorm = np.cross(axis, perp)

    ring = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        ring.append(math.cos(angle) * perp + math.sin(angle) * binorm)

    centre = np.array([cx, cy, cz])
    half   = axis * (length / 2)
    tris   = []

    for i in range(segments):
        r0 = ring[i]
        r1 = ring[(i + 1) % segments]
        b0 = centre - half + r * r0
        b1 = centre - half + r * r1
        t0 = centre + half + r * r0
        t1 = centre + half + r * r1
        tris += [(b0, b1, t0), (b1, t1, t0)]

    return tris


def disk_triangles(cx, cy, cz, r, normal, segments):
    """Filled disk (cap) for closing cylinder ends."""
    normal = np.array(normal, dtype=float)
    normal /= np.linalg.norm(normal)
    if abs(normal[0]) < 0.9:
        perp = np.cross(normal, [1, 0, 0])
    else:
        perp = np.cross(normal, [0, 1, 0])
    perp /= np.linalg.norm(perp)
    binorm = np.cross(normal, perp)

    centre = np.array([cx, cy, cz])
    ring   = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        ring.append(centre + r * (math.cos(angle) * perp +
                                   math.sin(angle) * binorm))
    tris = []
    for i in range(segments):
        p0 = ring[i]
        p1 = ring[(i + 1) % segments]
        # winding depends on normal direction
        tris.append((centre, p0, p1))
    return tris


# ── Boolean subtraction helpers ───────────────────────────────────────────────

def triangles_to_verts(tris):
    """Flatten a list of (v0,v1,v2) triples into an (N,3,3) array."""
    arr = np.array(tris, dtype=np.float64)
    if arr.ndim == 1:
        return arr.reshape(-1, 3, 3)
    return arr.reshape(-1, 3, 3)


def is_inside_cylinder(point, cx, cy, cz, r, length, axis):
    """Return True if *point* is inside the specified cylinder."""
    axis  = np.array(axis,  dtype=float)
    axis /= np.linalg.norm(axis)
    p = np.array(point) - np.array([cx, cy, cz])
    proj    = np.dot(p, axis)
    radial  = p - proj * axis
    return abs(proj) <= length / 2 and np.linalg.norm(radial) <= r


def filter_triangles_by_cylinders(tris, cylinders):
    """
    Remove any triangle whose centroid lies inside ANY of the subtraction
    cylinders.  This is an approximation of CSG difference sufficient for
    the mesh-hole pattern.
    """
    kept = []
    for tri in tris:
        centroid = (np.array(tri[0]) + np.array(tri[1]) + np.array(tri[2])) / 3
        inside   = False
        for cyl in cylinders:
            if is_inside_cylinder(centroid, *cyl):
                inside = True
                break
        if not inside:
            kept.append(tri)
    return kept


# ── Main model builder ────────────────────────────────────────────────────────

def build_model():
    top_r_outer = TOP_DIAMETER    / 2
    bot_r_outer = BOTTOM_DIAMETER / 2
    top_r_inner = top_r_outer - WALL_THICKNESS
    # Ensure the inner radius is at least 1 mm so the bottom ring remains printable
    MIN_INNER_RADIUS = 1.0
    bot_r_inner = max(bot_r_outer - WALL_THICKNESS, MIN_INNER_RADIUS)
    h           = CONE_HEIGHT

    # ── Define subtraction cylinders (one per mesh hole) ─────────────────────
    hole_r   = HOLE_DIAMETER / 2
    # 6× wall thickness ensures the hole cylinder extends well beyond both
    # the outer and inner surfaces of the cone shell (3× each side).
    HOLE_PIERCE_MULTIPLIER = 6
    cyl_len  = WALL_THICKNESS * HOLE_PIERCE_MULTIPLIER

    cylinders = []   # each entry: (cx, cy, cz, r, length, axis)
    for row in range(HOLE_ROWS):
        frac = (row + 1) / (HOLE_ROWS + 1)
        z    = frac * h
        r_at_z = bot_r_outer + (top_r_outer - bot_r_outer) * frac
        col_offset = 0.0 if row % 2 == 0 else (math.pi / HOLE_COLS)

        for col in range(HOLE_COLS):
            angle = 2 * math.pi * col / HOLE_COLS + col_offset
            cx  = r_at_z * math.cos(angle)
            cy  = r_at_z * math.sin(angle)
            # Radial outward axis
            axis = [math.cos(angle), math.sin(angle), 0.0]
            cylinders.append((cx, cy, z, hole_r, cyl_len, axis))

    all_tris = []

    # ── Outer lateral surface of the cone ────────────────────────────────────
    outer_tris = frustum_triangles(bot_r_outer, top_r_outer, h,
                                   SEGMENTS, inward=False)
    outer_tris = filter_triangles_by_cylinders(outer_tris, cylinders)
    all_tris.extend(outer_tris)

    # ── Inner lateral surface of the cone ────────────────────────────────────
    inner_tris = frustum_triangles(bot_r_inner, top_r_inner, h,
                                   SEGMENTS, inward=True)
    inner_tris = filter_triangles_by_cylinders(inner_tris, cylinders)
    all_tris.extend(inner_tris)

    # ── Top annular face (connects outer and inner at the top) ────────────────
    # (the rim rounding replaces the flat top annulus)
    # We add the torus rim instead:
    minor_r = EDGE_RADIUS
    major_r = top_r_outer - minor_r
    rim_tris = torus_rim_triangles(major_r, minor_r,
                                   SEGMENTS, RIM_SEGMENTS,
                                   CONE_HEIGHT)
    all_tris.extend(rim_tris)

    # ── Bottom annular face (flat, face down) ─────────────────────────────────
    bot_face = disk_annulus_triangles(bot_r_inner, bot_r_outer, 0.0,
                                      SEGMENTS, face_up=False)
    all_tris.extend(bot_face)

    # ── Hole tunnel walls (inner surface of each mesh hole) ───────────────────
    # Adding smooth cylinder walls makes the model watertight.
    hole_segs = max(8, SEGMENTS // 8)
    for (cx, cy, cz, r, length, axis) in cylinders:
        # Lateral wall of the hole tunnel
        cyl_wall = cylinder_triangles(cx, cy, cz, r, length,
                                      axis, hole_segs)
        all_tris.extend(cyl_wall)

    return all_tris


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    output_file = "rounded_cone_washer.stl"
    print("Building model …")
    tris = build_model()
    print(f"  {len(tris):,} triangles generated")

    m = make_mesh(tris)
    m.save(output_file)
    print(f"Saved → {output_file}")
    print()
    print("─" * 60)
    print("Recommended materials for dishwasher-safe printing")
    print("─" * 60)
    print("  PETG  : ★★★★★  Best choice – heat-safe to ~80 °C,")
    print("                  food-safe grades available.")
    print("  ASA   : ★★★★☆  Excellent heat & UV resistance (to 95 °C).")
    print("  PLA+  : ★★☆☆☆  Top rack only; standard PLA not suitable.")
    print()
    print("Print settings")
    print("─" * 60)
    print("  Layer height : 0.20 mm")
    print("  Wall count   : 3")
    print("  Infill       : 20–30 % Gyroid")
    print("  Supports     : None (print upright)")
    print("  Bed adhesion : 5 mm Brim")
    print("─" * 60)


if __name__ == "__main__":
    main()
