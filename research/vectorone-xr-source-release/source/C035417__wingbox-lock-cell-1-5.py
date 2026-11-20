"""Parametric 1:5 wing-box / load-spreading joint test article.

This is a printable structural-mechanism study, not a flight component.
Dimensions are derived from or assumed against the supplied VECTORONE boards;
see wingbox-lock-cell-design-note.md for status and limits.
"""
from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq


OUT = Path(__file__).resolve().parent
SCALE = 5.0
FULL_WING_AREA_M2 = 14.0          # latest-board target; unverified
FULL_WINGSPAN_M = 13.0            # latest-board target; unverified
FULL_ROOT_MOMENT_NM = 40_600.0    # board screening value; unverified
FULL_CAP_FORCE_N = 178_000.0      # board screening value; unverified
FULL_BAY_MM = 200.0               # membrane/support bay target from boards
FULL_STIFFENER_PITCH_MM = 40.0    # candidate value from boards

CHORD_MM = FULL_WING_AREA_M2 / FULL_WINGSPAN_M * 1000.0 / SCALE
DEPTH_MM = FULL_ROOT_MOMENT_NM / FULL_CAP_FORCE_N * 1000.0 / SCALE
BAY_MM = FULL_BAY_MM / SCALE
RIB_PITCH_MM = FULL_STIFFENER_PITCH_MM / SCALE
SEGMENT_MM = BAY_MM
WALL_MM = 1.2                     # local print choice; not a full-scale shell value
RIB_MM = 1.2
WEB_MM = 1.2
PIN_D_MM = 3.0
PIN_BORE_MM = 3.6                 # provisional clearance; use existing fit coupon
STRAP_T_MM = 1.6
STRAP_W_MM = 18.0
STRAP_LEN_MM = 40.0
BOSS_R_MM = 4.0
BOSS_H_MM = 6.0
PIN_X_FROM_JOINT_MM = 10.0
PIN_Y_POSITIONS_MM = (-CHORD_MM / 4.0, CHORD_MM / 4.0)


def box(lx: float, ly: float, lz: float, x: float, y: float, z: float) -> cq.Solid:
    return cq.Solid.makeBox(lx, ly, lz, cq.Vector(x, y, z))


def cylinder(radius: float, length: float, base, direction) -> cq.Solid:
    return cq.Solid.makeCylinder(radius, length, cq.Vector(*base), cq.Vector(*direction))


def rib_at(x_start: float) -> cq.Solid:
    rib = box(RIB_MM, CHORD_MM - 2 * WALL_MM, DEPTH_MM - 2 * WALL_MM,
              x_start, -CHORD_MM / 2 + WALL_MM, -DEPTH_MM / 2 + WALL_MM)
    # Two apertures keep the transverse support from becoming a solid bulkhead.
    for y in PIN_Y_POSITIONS_MM:
        cutter = cylinder(10.0, RIB_MM + 0.4,
                          (x_start - 0.2, y, -5.0), (1, 0, 0))
        rib = rib.cut(cutter)
    return rib


def box_segment(x0: float, pin_x: float, label: str) -> cq.Shape:
    # Closed perimeter section with open spanwise ends. The separated section
    # ends are tied by four cap bridges; the box skin is not the only load path.
    outer = box(SEGMENT_MM, CHORD_MM, DEPTH_MM,
                x0, -CHORD_MM / 2, -DEPTH_MM / 2)
    inner = box(SEGMENT_MM + 0.2, CHORD_MM - 2 * WALL_MM,
                DEPTH_MM - 2 * WALL_MM, x0 - 0.1,
                -CHORD_MM / 2 + WALL_MM, -DEPTH_MM / 2 + WALL_MM)
    body = outer.cut(inner)

    # Three spanwise shear webs divide the chord into four closed cells.
    for y_center in PIN_Y_POSITIONS_MM + (0.0,):
        web = box(SEGMENT_MM, WEB_MM, DEPTH_MM - 2 * WALL_MM,
                  x0, y_center - WEB_MM / 2, -DEPTH_MM / 2 + WALL_MM)
        body = body.fuse(web)

    # Full-depth ribs at the supplied 40 mm full-scale pitch (8 mm in this 1:5
    # coupon) distribute skin pressure into the webs. Add a local rib at the
    # pin station so the joint load enters the box rather than only the skin.
    rib_starts = {round(x0 + n * RIB_PITCH_MM, 4) for n in range(1, 5)}
    rib_starts.add(round(pin_x - RIB_MM / 2, 4))
    for xr in sorted(rib_starts):
        if xr < x0 + WALL_MM or xr + RIB_MM > x0 + SEGMENT_MM - WALL_MM:
            continue
        body = body.fuse(rib_at(xr))

    # Local lugs reinforce the cap around each provisional test-pin location.
    z_inner_top = DEPTH_MM / 2 - WALL_MM
    z_inner_bottom = -DEPTH_MM / 2 + WALL_MM
    for y in PIN_Y_POSITIONS_MM:
        top_pad = cylinder(BOSS_R_MM, BOSS_H_MM,
                           (pin_x, y, z_inner_top - BOSS_H_MM), (0, 0, 1))
        bottom_pad = cylinder(BOSS_R_MM, BOSS_H_MM,
                              (pin_x, y, z_inner_bottom), (0, 0, 1))
        body = body.fuse(top_pad).fuse(bottom_pad)

    # Separate top and bottom pin bores; do not perforate the opposite cap.
    bore_r = PIN_BORE_MM / 2
    z_outer_top = DEPTH_MM / 2
    z_outer_bottom = -DEPTH_MM / 2
    bore_len = BOSS_H_MM + WALL_MM + 0.4
    for y in PIN_Y_POSITIONS_MM:
        top_bore = cylinder(bore_r, bore_len,
                            (pin_x, y, z_outer_top - WALL_MM - BOSS_H_MM - 0.2),
                            (0, 0, 1))
        bottom_bore = cylinder(bore_r, bore_len,
                               (pin_x, y, z_outer_bottom - 0.2), (0, 0, 1))
        body = body.cut(top_bore).cut(bottom_bore)
    return body.clean()


def cap_strap(y_center: float, z0: float, label: str) -> cq.Shape:
    plate = box(STRAP_LEN_MM, STRAP_W_MM, STRAP_T_MM,
                -STRAP_LEN_MM / 2, y_center - STRAP_W_MM / 2, z0)
    # One pin per adjoining segment; both pins bridge to a reinforced cap lug.
    for x in (-PIN_X_FROM_JOINT_MM, PIN_X_FROM_JOINT_MM):
        bore = cylinder(PIN_BORE_MM / 2, STRAP_T_MM + 0.4,
                        (x, y_center, z0 - 0.2), (0, 0, 1))
        plate = plate.cut(bore)
    return plate.clean()


def lock_pin(x: float, y: float, top: bool, label: str) -> cq.Shape:
    head_h = 1.6
    shaft_len = BOSS_H_MM + WALL_MM + STRAP_T_MM - 0.2
    if top:
        strap_top = DEPTH_MM / 2 + STRAP_T_MM
        shaft = cylinder(PIN_D_MM / 2, shaft_len,
                         (x, y, strap_top - shaft_len), (0, 0, 1))
        head = cylinder(5.0 / 2, head_h,
                        (x, y, strap_top), (0, 0, 1))
    else:
        strap_bottom = -DEPTH_MM / 2 - STRAP_T_MM
        shaft = cylinder(PIN_D_MM / 2, shaft_len,
                         (x, y, strap_bottom), (0, 0, 1))
        head = cylinder(5.0 / 2, head_h,
                        (x, y, strap_bottom - head_h), (0, 0, 1))
    return shaft.fuse(head).clean()


def save_stl(shape: cq.Shape, path: Path) -> None:
    cq.exporters.export(shape, str(path), exportType="STL",
                        tolerance=0.05, angularTolerance=0.05)


def build() -> dict:
    left = box_segment(-SEGMENT_MM, -PIN_X_FROM_JOINT_MM, "left")
    right = box_segment(0.0, PIN_X_FROM_JOINT_MM, "right")
    parts: dict[str, cq.Shape] = {
        "wingbox-cell-left": left,
        "wingbox-cell-right": right,
    }

    top_z = DEPTH_MM / 2
    bottom_z = -DEPTH_MM / 2 - STRAP_T_MM
    for side, y in (("front", PIN_Y_POSITIONS_MM[0]),
                    ("rear", PIN_Y_POSITIONS_MM[1])):
        parts[f"cap-bridge-top-{side}"] = cap_strap(y, top_z, side)
        parts[f"cap-bridge-bottom-{side}"] = cap_strap(y, bottom_z, side)
        for x, station in ((-PIN_X_FROM_JOINT_MM, "left"),
                           (PIN_X_FROM_JOINT_MM, "right")):
            parts[f"lock-pin-top-{side}-{station}"] = lock_pin(x, y, True, station)
            parts[f"lock-pin-bottom-{side}-{station}"] = lock_pin(x, y, False, station)

    # Compound keeps every printable piece separate in STEP and STL.
    assembly = cq.Compound.makeCompound(list(parts.values()))
    cq.exporters.export(assembly, str(OUT / "wingbox-lock-cell-1-5-assembly.step"))
    save_stl(assembly, OUT / "wingbox-lock-cell-1-5-assembly.stl")
    for name, shape in parts.items():
        save_stl(shape, OUT / f"{name}.stl")

    bb = assembly.BoundingBox()
    metrics = {
        "model": "VECTORONE XR wing-box / load-spreading joint coupon",
        "status": "printable geometry candidate; untested; not a flight component",
        "scale": "1:5 structural cell study",
        "source_inputs": {
            "wing_area_m2": FULL_WING_AREA_M2,
            "wingspan_m": FULL_WINGSPAN_M,
            "root_moment_Nm": FULL_ROOT_MOMENT_NM,
            "cap_force_N": FULL_CAP_FORCE_N,
            "bay_mm": FULL_BAY_MM,
            "stiffener_pitch_mm": FULL_STIFFENER_PITCH_MM,
        },
        "derived_coupon_dimensions_mm": {
            "mean_chord": round(CHORD_MM, 3),
            "implied_cap_separation": round(DEPTH_MM, 3),
            "bay_length": round(BAY_MM, 3),
            "stiffener_pitch": round(RIB_PITCH_MM, 3),
        },
        "print_assumptions_mm": {
            "wall": WALL_MM,
            "rib": RIB_MM,
            "shear_web": WEB_MM,
            "test_pin_diameter": PIN_D_MM,
            "test_pin_bore": PIN_BORE_MM,
            "cap_bridge_thickness": STRAP_T_MM,
        },
        "assembly_envelope_mm": {
            "x": round(bb.xlen, 3), "y": round(bb.ylen, 3), "z": round(bb.zlen, 3),
        },
        "full_scale_implied_cap_separation_m": round(FULL_ROOT_MOMENT_NM / FULL_CAP_FORCE_N, 6),
        "similarity_load_reference_only": {
            "root_moment_at_1_to_5_Nm": round(FULL_ROOT_MOMENT_NM / SCALE**3, 3),
            "cap_force_at_1_to_5_N": round(FULL_CAP_FORCE_N / SCALE**2, 1),
            "note": "Not a prescribed bench load; polymer/material and print anisotropy are not correlated to the full-scale claim.",
        },
        "scope_limits": [
            "No material strength is claimed.",
            "No pin fit is validated; use the existing fit coupon before a full print.",
            "The coupon tests joint geometry and load transfer only; it does not prove aircraft-scale strength.",
            "The full-scale moment and cap force are unverified board values.",
        ],
        "print_parts": sorted(parts),
    }
    (OUT / "wingbox-lock-cell-1-5-metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
