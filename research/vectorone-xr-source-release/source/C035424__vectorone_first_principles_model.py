"""Build a scale folding-mechanism prototype from explicit geometry inputs.

This model is a printable, unpowered demonstrator.  It is not a flight design.
Only the dimensions in the adjacent design-basis document are used here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "vectorone-xr-cs02-prototype"
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 20
ROAD_LENGTH_MM = 5200 / SCALE
WINGSPAN_MM = 13000 / SCALE
BODY_WIDTH_MM = 52.0
BODY_HEIGHT_MM = 34.0
CANOPY_HEIGHT_MM = 24.0
WHEEL_RADIUS_MM = 15.0
WHEEL_WIDTH_MM = 9.0
PIN_DIAMETER_MM = 3.0
PIN_HOLE_DIAMETER_MM = 3.6
AXLE_DIAMETER_MM = 4.6
AXLE_KEEPER_BORE_MM = 4.8
WHEEL_HUB_HOLE_MM = 5.4
HINGE_AXIS_ROOT_Z_MM = 41.0
WING_Z_MM = 36.0
HULL_Z_OFFSET_MM = 2.5
HALFSPAN_MM = WINGSPAN_MM / 2
ROOT_Y_MM = BODY_WIDTH_MM / 2 + 6.0
MID_Y_MM = 180.0
TIP_Y_MM = HALFSPAN_MM
BAR_RADIUS_MM = 2.0
RAIL_POSITIONS = (-0.5, 0.0, 0.5)


def vec(p):
    return cq.Vector(float(p[0]), float(p[1]), float(p[2]))


def rod(a, b, radius=BAR_RADIUS_MM):
    va, vb = vec(a), vec(b)
    d = vb - va
    return cq.Solid.makeCylinder(radius, d.Length, va, d.normalized())


def ring(center, axis, length, outer_r, bore_r=PIN_HOLE_DIAMETER_MM / 2):
    c = vec(center)
    d = vec(axis).normalized()
    base = c - d * (length / 2)
    outer = cq.Solid.makeCylinder(outer_r, length, base, d)
    inner = cq.Solid.makeCylinder(bore_r, length + 0.2, base - d * 0.1, d)
    return outer.cut(inner)


def chord_at(y_abs: float) -> float:
    # Taper from a 54 mm root chord to a 34 mm tip chord.
    t = max(0.0, min(1.0, (y_abs - ROOT_Y_MM) / (TIP_Y_MM - ROOT_Y_MM)))
    return 54.0 + (34.0 - 54.0) * t


def wing_panel(side: int, start_abs: float, end_abs: float, is_root: bool):
    """Two-cell open frame panel with a split pin hinge at the mid-fold."""
    y0, y1 = side * start_abs, side * end_abs
    samples = [start_abs, end_abs]
    samples.extend(
        v for v in range(math.ceil(start_abs / 36) * 36, int(end_abs), 36)
        if start_abs < v < end_abs
    )
    samples = sorted(set(samples))
    shapes = []

    def x_for(y_abs, fraction):
        return chord_at(y_abs) * fraction

    for fraction in RAIL_POSITIONS:
        shapes.append(rod((x_for(start_abs, fraction), y0, WING_Z_MM),
                          (x_for(end_abs, fraction), y1, WING_Z_MM)))
    for y_abs in samples:
        y = side * y_abs
        half = chord_at(y_abs) / 2
        x0, xm, x1 = -half, 0.0, half
        if is_root and y_abs == start_abs:
            # Leave the vertical pivot bore open; the ribs terminate at its rim.
            shapes.append(rod((x0, y, WING_Z_MM), (-6.0, y, WING_Z_MM)))
            shapes.append(rod((6.0, y, WING_Z_MM), (x1, y, WING_Z_MM)))
        else:
            shapes.append(rod((x0, y, WING_Z_MM), (xm, y, WING_Z_MM)))
            shapes.append(rod((xm, y, WING_Z_MM), (x1, y, WING_Z_MM)))

    # A root lug hangs between two body-side bearing ears on a vertical pin.
    if is_root:
        hinge_center = (0.0, side * ROOT_Y_MM, HINGE_AXIS_ROOT_Z_MM)
        shapes.append(ring(hinge_center, (0, 0, 1), 9.0, 6.0))
    # Split barrels occupy opposite halves of one chordwise axis. The center gap
    # leaves clearance for the 3 mm pin and avoids overlapping printable parts.
    hinge_y = side * (end_abs if is_root else start_abs)
    barrel_x = -10.0 if is_root else 10.0
    hinge_z = WING_Z_MM + 8.0
    shapes.append(ring((barrel_x, hinge_y, hinge_z), (1, 0, 0), 12.0, 5.3))
    if is_root:
        shapes.append(rod((barrel_x, hinge_y, WING_Z_MM),
                          (barrel_x, hinge_y, WING_Z_MM + 3.0), 2.8))
    if not is_root:
        shapes.append(rod((barrel_x, hinge_y, WING_Z_MM),
                          (barrel_x, hinge_y, WING_Z_MM + 3.0), 2.8))

    return cq.Compound.makeCompound(shapes)


def root_ears(side: int):
    """Fixed two-ear clevis on the spine; leaves a 0.5 mm lug gap."""
    x, y = 0.0, side * ROOT_Y_MM
    parts = [
        ring((x, y, 34.5), (0, 0, 1), 4.0, 6.5),
        ring((x, y, 47.5), (0, 0, 1), 4.0, 6.5),
    ]
    # Paired diagonal yoke struts transfer each root hinge into the spine shell.
    parts.extend([
        rod((-12, side * 18, 24), (-6, side * ROOT_Y_MM, 34.5), 3.6),
        rod((12, side * 18, 24), (6, side * ROOT_Y_MM, 34.5), 3.6),
    ])
    return cq.Compound.makeCompound(parts)


def body_shell():
    # Elliptic cross-sections taper the nose and tail from explicit dimensions.
    sections = [
        (-130, 3, 1.5, 3), (-126, 5, 6, 6), (-116, 10, 13, 11),
        (-98, 15, 20, 15), (-80, 17, 23, 17), (65, 17, 26, 17),
        (92, 16, 23, 16), (112, 13, 17, 13), (124, 8, 9, 8),
        (130, 3, 1.5, 3),
    ]
    wires = []
    for x, zc, half_width, half_height in sections:
        section = cq.Workplane("YZ").ellipse(half_width, half_height).val()
        wires.append(section.translate((x, 0, zc)))
    shell = cq.Solid.makeLoft(wires, ruled=False).translate(cq.Vector(0, 0, HULL_Z_OFFSET_MM))
    # Simplified printed cabin fairing, lofted from a wide sill to a smaller crown.
    canopy = (cq.Workplane("XY").workplane(offset=BODY_HEIGHT_MM)
              .ellipse(60, 23).workplane(offset=CANOPY_HEIGHT_MM)
              .ellipse(47, 17).loft(combine=True).val()
              .translate((18, 0, 0)))
    # Four fixed axle stubs are part of the spine. Each wheel slides onto one
    # stub; a separate split keeper snaps over the end shoulder.
    axle_parts = [shell]
    for x in (-82.0, 82.0):
        for side in (-1, 1):
            direction = cq.Vector(0, side, 0)
            axle_parts.append(cq.Solid.makeCylinder(AXLE_DIAMETER_MM / 2, 24.5,
                               cq.Vector(x, side * 18.0, WHEEL_RADIUS_MM), direction))
            axle_parts.append(cq.Solid.makeCylinder(5.5 / 2, 1.5,
                               cq.Vector(x, side * 41.0, WHEEL_RADIUS_MM), direction))
    return cq.Compound.makeCompound(axle_parts), canopy


def wheel_module(x, side):
    center_y = side * 35.5
    center_z = WHEEL_RADIUS_MM
    tire = cq.Solid.makeCylinder(WHEEL_RADIUS_MM, WHEEL_WIDTH_MM,
                                 cq.Vector(x, center_y - side * WHEEL_WIDTH_MM / 2, center_z),
                                 cq.Vector(0, side, 0))
    hub = cq.Solid.makeCylinder(7.5, WHEEL_WIDTH_MM + 1.0,
                                cq.Vector(x, center_y - side * (WHEEL_WIDTH_MM + 1.0) / 2, center_z),
                                cq.Vector(0, side, 0))
    tire = tire.cut(cq.Solid.makeCylinder(WHEEL_HUB_HOLE_MM / 2, WHEEL_WIDTH_MM + 0.2,
                                         cq.Vector(x, center_y - side * (WHEEL_WIDTH_MM + 0.2) / 2, center_z),
                                         cq.Vector(0, side, 0)))
    hub = hub.cut(cq.Solid.makeCylinder(WHEEL_HUB_HOLE_MM / 2, WHEEL_WIDTH_MM + 1.2,
                                        cq.Vector(x, center_y - side * (WHEEL_WIDTH_MM + 1.2) / 2, center_z),
                                        cq.Vector(0, side, 0)))
    return cq.Compound.makeCompound([tire, hub])


def wheel_keeper(x, side):
    """Split C keeper snaps over the 5.5 mm axle shoulder."""
    length, outer_r = 2.6, 6.4
    center_y, center_z = side * 41.8, WHEEL_RADIUS_MM
    axis = cq.Vector(0, side, 0)
    origin = cq.Vector(x, center_y - side * length / 2, center_z)
    outer = cq.Solid.makeCylinder(outer_r, length, origin, axis)
    inner = cq.Solid.makeCylinder(AXLE_KEEPER_BORE_MM / 2, length + 0.2,
                                  origin - axis * 0.1, axis)
    clip = outer.cut(inner)
    # Radial throat through the lower side makes the printed clip flex open.
    slot = cq.Solid.makeBox(2.1, length + 0.3, outer_r + 0.5,
                            cq.Vector(x - 1.05, center_y - side * (length + 0.3) / 2,
                                      center_z - outer_r - 0.25))
    return clip.cut(slot)


def fit_coupon():
    # First row tests 3 mm hinge pins; second row tests the 4.6 mm axle interface.
    plate = cq.Workplane("XY").box(48, 24, 4).val().translate((0, 0, 2))
    result = plate
    for y, sizes in ((-6, (3.2, 3.4, 3.6, 3.8)), (6, (4.4, 4.6, 4.8, 5.0))):
        for x, hole_d in zip((-18, -6, 6, 18), sizes):
            bore = cq.Solid.makeCylinder(hole_d / 2, 4.2,
                                         cq.Vector(x, y, -0.1), cq.Vector(0, 0, 1))
            result = result.cut(bore)
    return result


def pin(axis: str, length: float, center):
    d = {"x": cq.Vector(1, 0, 0), "y": cq.Vector(0, 1, 0), "z": cq.Vector(0, 0, 1)}[axis]
    c = vec(center)
    return cq.Solid.makeCylinder(PIN_DIAMETER_MM / 2, length, c - d * (length / 2), d)


def save_stl(shape, path):
    cq.exporters.export(shape, str(path), exportType="STL", tolerance=0.08, angularTolerance=0.08)


def build():
    parts: dict[str, cq.Shape] = {}
    shell, canopy = body_shell()
    parts["spine-shell"] = shell
    parts["cabin-fairing"] = canopy

    for side, label in ((1, "right"), (-1, "left")):
        parts[f"root-clevis-{label}"] = root_ears(side)
        parts[f"inner-wing-loop-{label}"] = wing_panel(side, ROOT_Y_MM, MID_Y_MM, True)
        parts[f"outer-wing-loop-{label}"] = wing_panel(side, MID_Y_MM, TIP_Y_MM, False)
        for x, axle in ((82.0, "front"), (-82.0, "rear")):
            parts[f"wheel-{axle}-{label}"] = wheel_module(x, side)
            parts[f"wheel-keeper-{axle}-{label}"] = wheel_keeper(x, side)

    parts["root-pin-right"] = pin("z", 22, (0, ROOT_Y_MM, 41))
    parts["root-pin-left"] = pin("z", 22, (0, -ROOT_Y_MM, 41))
    # Mid pins are horizontal along the shared chordwise hinge axis.
    parts["mid-pin-right"] = pin("x", 38, (0, MID_Y_MM, WING_Z_MM + 8.0))
    parts["mid-pin-left"] = pin("x", 38, (0, -MID_Y_MM, WING_Z_MM + 8.0))
    parts["hinge-fit-coupon"] = fit_coupon()

    for name, shape in parts.items():
        save_stl(shape, OUT / f"{name}.stl")

    assembly = cq.Compound.makeCompound([parts[k] for k in parts if k != "hinge-fit-coupon"])
    cq.exporters.export(assembly, str(OUT / "vectorone-cs02-2-deployed-assembly.step"))
    save_stl(assembly, OUT / "vectorone-cs02-2-deployed-assembly.stl")

    metrics = {
        "model": "VECTORONE XR CS-02.2 folding mechanism demonstrator",
        "scale": "1:20",
        "inherited_concept_length_mm_full_scale": 5200,
        "inherited_concept_span_mm_full_scale": 13000,
        "derived_model_length_mm": ROAD_LENGTH_MM,
        "derived_model_span_mm": WINGSPAN_MM,
        "root_panel_length_mm": MID_Y_MM - ROOT_Y_MM,
        "outer_panel_length_mm": TIP_Y_MM - MID_Y_MM,
        "pin_diameter_mm": PIN_DIAMETER_MM,
        "provisional_hole_diameter_mm": PIN_HOLE_DIAMETER_MM,
        "diametral_clearance_mm": PIN_HOLE_DIAMETER_MM - PIN_DIAMETER_MM,
        "wheel_axle_diameter_mm": AXLE_DIAMETER_MM,
        "wheel_hub_hole_diameter_mm": WHEEL_HUB_HOLE_MM,
        "keeper_bore_diameter_mm": AXLE_KEEPER_BORE_MM,
        "folded_width_envelope_mm": 2 * (ROOT_Y_MM + 54.0 / 2),
        "folded_length_envelope_mm": ROAD_LENGTH_MM / 2 + (MID_Y_MM - ROOT_Y_MM) + 8.0,
        "folded_height_envelope_mm": WING_Z_MM + 8.0 + (TIP_Y_MM - MID_Y_MM) + BAR_RADIUS_MM,
        "spine_shell_vertical_offset_mm": HULL_Z_OFFSET_MM,
        "scope": "Unpowered geometry demonstrator; no flight/hover/structural qualification",
        "print_parts": sorted(parts),
    }
    (OUT / "geometry-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "parts": len(parts), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    build()
