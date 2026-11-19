#!/usr/bin/env python3
"""crfce_engine_design.py -- EngineAI computes an unvalidated CRFCE reference-design candidate.

This is the top of the CRFCE reference-design stack. It takes the resolved study inputs
and governed operating-point screen, sizes a parameterized reference candidate, and
attempts geometry generation through CAD adapters when those dependencies are available.
Geometry verification checks generated solids against their own parametric specification;
it does not authenticate a released drawing or as-built machine. Governed analytical
screens consume the retained study-input snapshot and candidate dimensions where available.
The DesignPassport records the BOM, preliminary DfM screens, geometry status, evidence
limits, and explicit maturity level.

HONESTY CEILING. This produces a virtual reference study with candidate geometry and
receipt-backed analytical screens. It does not establish field-solved machine performance,
manufacturing qualification, production readiness, or release authorization. Physical
bench, spin, quench, thermal-cycle, measurement-correlation, independent review, and signed
release remain required. Every passport states physical validation is NOT_DEMONSTRATED.
Sizing choices are labelled ASSUMED/DERIVED/DEFAULT; governed numbers carry receipts;
models that refuse are named, not fabricated.

Topology note: CRFCE is a reluctance-HTS machine. motor_geometry may generate a slotted
stator and an IPM-style rotor lamination; the rotor pockets are a GEOMETRIC PROXY for a
reluctance rotor's flux barriers. These are parametric candidate solids only. Their
generation and dimensional back-check do not show that a released design, as-built part,
or buildable CRFCE assembly has been established.
"""
from __future__ import annotations

import contextlib
import io
import math
from pathlib import Path
from typing import Any

with contextlib.redirect_stdout(io.StringIO()):
    import capability_catalogue as cc
    cc.load_passports()
    import capability_passport as cp
    import capability_runner as cr
    import crfce_research as R

MU0 = 4e-7 * math.pi
STEEL_RHO = 7650.0          # electrical-steel lamination density kg/m^3
BOUNDARY = R.BOUNDARY
MATURITY = ("UNASSESSED_NOT_RELEASEABLE -- reference analytical design study; "
            "physical validation and human release are NOT_DEMONSTRATED.")
RESEARCH_SCHEMA = "engineai.crfce_research.v2"


def candidate_evidence_scope() -> dict[str, Any]:
    """Return the non-promotable evidence boundary for the virtual reference candidate."""
    return {
        "study": "GOVERNED_VIRTUAL_REFERENCE_CANDIDATE",
        "geometry": "PARAMETRIC_CANDIDATE_NOT_RELEASED_OR_AS_BUILT",
        "torque": "ANALYTICAL_SHEAR_ESTIMATE_NOT_FIELD_SOLVE",
        "rotor": "IPM_STYLE_GEOMETRIC_PROXY_NOT_RELUCTANCE_ROTOR",
        "manufacturing": "PRELIMINARY_SCREEN_NOT_QUALIFICATION",
        "physical_validation": "NOT_DEMONSTRATED",
        "release_authorized": False,
    }


def _g(cap_id: str, values: dict, key: str | None = None) -> dict:
    """One governed evaluation (mirrors crfce_research._g)."""
    return R._g(cap_id, values, key)


def _resolved_research_values(container: dict) -> dict[str, float]:
    """Validate the exact research configuration required by downstream design checks."""
    if type(container) is not dict or container.get("schema") != RESEARCH_SCHEMA:
        raise ValueError("CRFCE design requires a v2 research dossier with exact resolved inputs")
    records = container.get("resolved_inputs")
    if type(records) is not dict or set(records) != set(R.REFERENCE):
        raise ValueError("CRFCE research dossier does not retain the exact input set")
    values: dict[str, float] = {}
    for name, reference_value in R.REFERENCE.items():
        record = records.get(name)
        if type(record) is not dict or set(record) != {"value", "provenance"}:
            raise ValueError(f"CRFCE resolved input record is malformed: {name}")
        value, provenance = record["value"], record["provenance"]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(float(value))):
            raise ValueError(f"CRFCE resolved input is not finite numeric data: {name}")
        if provenance == "REFERENCE_ASSUMPTION":
            if value != reference_value:
                raise ValueError(f"CRFCE reference assumption differs from the pinned source: {name}")
        elif provenance == "USER_SUPPLIED_UNVERIFIED":
            validated = R.validate_design_overrides({name: value})
            if validated.get(name) != float(value):
                raise ValueError(f"CRFCE user input failed source contract validation: {name}")
        else:
            raise ValueError(f"CRFCE resolved input provenance is unrecognized: {name}")
        values[name] = float(value)
    user_values = {
        name: values[name]
        for name, record in records.items()
        if record["provenance"] == "USER_SUPPLIED_UNVERIFIED"
    }
    # Re-run the whole request contract, not just per-field checks: geometry and
    # support inputs also have cross-field invariants that a serialized dossier
    # could otherwise evade after it was created.
    validated = R.validate_design_overrides(user_values)
    if any(validated.get(name) != value for name, value in user_values.items()):
        raise ValueError("CRFCE resolved user inputs differ from the validated request")
    return values


# --------------------------------------------------------------------------------------
# 1) Size a machine from the governed operating point
# --------------------------------------------------------------------------------------
def size_from_operating_point(dossier: dict, *, aspect: float | None = None,
                              back_iron_ratio: float = 1.55,
                              air_gap_mm: float = 1.0,
                              slot_count: int = 24, pole_count: int | None = None,
                              slot_fillet_mm: float = 0.5) -> dict:
    """Turn the defended operating point into a motor_geometry spec + auxiliary parts.

    Every value carries an origin: DERIVED (from a governed result), ASSUMED (a stated
    design choice), or DEFAULT.  Rotor pole count must be derived from the exact
    pole-pair value retained by the research dossier; an independent 4-pole geometry
    default previously disagreed with the 3-pole-pair CRFCE reference dossier.
    """
    inputs = _resolved_research_values(dossier)
    pole_pairs = inputs["pole_pairs"]
    pole_pair_input = dossier["resolved_inputs"]["pole_pairs"]
    pole_provenance = pole_pair_input["provenance"]
    if int(pole_pairs) != pole_pairs:
        raise ValueError("resolved pole_pairs input must be an integer")
    derived_pole_count = 2 * int(pole_pairs)
    if pole_count is None:
        pole_count = derived_pole_count
        pole_count_origin = (f"DERIVED as 2 x {int(pole_pairs)} pole pairs from research dossier "
                             f"({pole_provenance})")
    elif type(pole_count) is not int or pole_count != derived_pole_count:
        raise ValueError("explicit pole_count must match the research dossier's 2 x pole_pairs")
    else:
        pole_count_origin = (f"EXPLICIT and cross-checked against 2 x {int(pole_pairs)} "
                             f"research-dossier pole pairs ({pole_provenance})")
    feas = dossier["headline"]["governed_feasible_point"] or {}
    rotor_r_m = inputs["rotor_r_m"]
    rotor_od = round(2 * rotor_r_m * 1000.0, 1)                 # DERIVED
    stator_od = round(rotor_od * back_iron_ratio, 1)           # ASSUMED ratio
    if aspect is None:
        stack_length = round(inputs["L_stack_m"] * 1000.0, 1)
        stack_origin = ("DERIVED from research dossier L_stack_m "
                        f"({dossier['resolved_inputs']['L_stack_m']['provenance']})")
    else:
        if (isinstance(aspect, bool) or not isinstance(aspect, (int, float))
                or not math.isfinite(float(aspect)) or aspect <= 0):
            raise ValueError("explicit aspect must be finite and positive")
        stack_length = round(rotor_od * float(aspect), 1)
        stack_origin = f"ASSUMED explicit aspect L/OD={float(aspect)}"
    shaft_d = round(max(12.0, 0.30 * rotor_od), 1)            # ASSUMED proportion
    spec_params = {
        "rotor_outer_diameter": rotor_od,
        "stator_outer_diameter": stator_od,
        "shaft_diameter": shaft_d,
        "stack_length": stack_length,
        "air_gap": air_gap_mm,
        "slot_count": slot_count,
        "pole_count": pole_count,
    }
    origins = {
        "rotor_outer_diameter": "DERIVED from governed rotor radius (2*r)",
        "stator_outer_diameter": f"ASSUMED back-iron ratio {back_iron_ratio}",
        "stack_length": stack_origin,
        "shaft_diameter": "ASSUMED 0.30*rotor_OD",
        "air_gap": "DESIGN input",
        "slot_count": "DESIGN input (stator field-coil slots)",
        "pole_count": pole_count_origin,
        "operating_B_T": "DERIVED from governed feasible point",
        "operating_rpm": "DERIVED from governed feasible point",
        "operating_T_K": "DERIVED from governed feasible point",
    }
    return {
        "spec_params": spec_params,
        "topology_binding": {
            "pole_pairs": int(pole_pairs),
            "pole_pairs_provenance": pole_provenance,
            "pole_count": pole_count,
            "convention": "pole_count = 2 x pole_pairs",
        },
        "research_inputs": {
            "schema": RESEARCH_SCHEMA,
            "resolved_inputs": {name: dict(record)
                                 for name, record in dossier["resolved_inputs"].items()},
        },
        "operating_point": {"B_T": feas.get("B_T"), "rpm": feas.get("rpm"),
                            "T_K": feas.get("T_K"), "target_torque_Nm": feas.get("torque_Nm"),
                            "target_power_kW": feas.get("power_kW")},
        "coil_former": {"outer": 40.0, "inner": 24.0, "h": 8.0},   # HTS field-coil bobbin
        "shaft": {"d1": shaft_d, "l1": stack_length, "d2": max(10.0, shaft_d - 6),
                  "l2": round(0.4 * stack_length, 1)},
        "slot_fillet_mm": slot_fillet_mm,
        "origins": origins,
    }


# --------------------------------------------------------------------------------------
# 2) Build + dimensionally back-verify parametric candidate solids
# --------------------------------------------------------------------------------------
def build_and_verify(sizing: dict, outdir: str | Path) -> dict:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"files": {}, "verification": {}, "withheld": []}
    # Candidate stator + rotor laminations, back-measured against the generator spec.
    try:
        import motor_geometry as mg
        spec = mg.motor_spec(sizing["spec_params"])
        manifest = mg.export(spec, out / "lamination")
        verify = mg.verify(spec, manifest["files"])
        result["spec"] = spec
        result["files"].update(manifest["files"])
        result["spec_hash"] = manifest["spec_hash"]
        result["verification"]["lamination"] = verify
    except Exception as exc:
        result["withheld"].append(f"lamination geometry withheld: {type(exc).__name__}: {exc}"[:200])
    # Candidate HTS coil former + shaft solids. cad_parts.build returns
    # (workplane, params); export/_volume are the blessed STEP+STL + volume path, and we
    # back-check the modelled volume against the part's closed form.
    try:
        import cad_parts
        for part, kw in (("coil_former", sizing["coil_former"]), ("shaft", sizing["shaft"])):
            wp, _params = cad_parts.build(part, **kw)
            step, stl = cad_parts.export(wp, str(out / part))
            v_model = float(cad_parts._volume(wp))
            v_form = cad_parts.PARTS[part][1](**kw)             # closed-form cross-check
            rel = abs(v_model - v_form) / v_form if v_form else 1.0
            result["files"][f"{part}_step"] = step
            result["files"][f"{part}_stl"] = stl
            result["verification"][part] = {
                "ok": rel < 1e-3, "volume_mm3": round(v_model, 1),
                "analytic_mm3": round(v_form, 1), "rel_err": rel}
    except Exception as exc:
        result["withheld"].append(f"coil/shaft geometry withheld: {type(exc).__name__}: {exc}"[:200])
    lam = result["verification"].get("lamination", {})
    result["geometry_ok"] = bool(lam.get("ok")) and all(
        v.get("ok") for k, v in result["verification"].items() if k != "lamination")
    return result


# --------------------------------------------------------------------------------------
# 3) Reference-case analytical screens using declared inputs and candidate dimensions.
#    These are not a field solve or verification against as-built hardware.
# --------------------------------------------------------------------------------------
def as_designed_checks(sizing: dict, built: dict) -> dict:
    sp = built.get("spec") or {}
    op = sizing["operating_point"]
    inputs = _resolved_research_values(sizing.get("research_inputs"))
    rpm = op.get("rpm") or inputs["rpm"]
    B = op.get("B_T") or inputs["B_T"]
    r_m = (sp.get("rotor_outer_diameter", 0) / 2000.0) or inputs["rotor_r_m"]
    omega = rpm * R.TWO_PI / 60.0
    checks: dict[str, Any] = {}
    receipts = []

    # Rotor centrifugal stress concentrates at the ROTOR's own feature -- the iron bridge
    # at the magnet-pocket / flux-barrier root -- NOT at the stationary stator slot. Use
    # the candidate spec pocket depth as a model input; no as-built geometry is supplied.
    pocket_depth_m = (sp.get("magnet_depth", 0.0) or 0.0) / 1000.0
    rho_m = sizing["slot_fillet_mm"] / 1000.0
    hoop = _g("equation.mech.rotating_ring_hoop",
              {"rho": inputs["rotor_rho_kg_m3"], "r": r_m, "omega": omega})
    mean = hoop["value"] if hoop["ok"] else None
    notch = _g("mechanics.stress_concentration.notch",
               {"sigma_nominal_MPa": mean or 0.0, "a": pocket_depth_m or 0.003, "rho": rho_m})
    Kt = notch["result"]["Kt"] if notch["ok"] else None
    peak = notch["result"]["sigma_peak_MPa"] if notch["ok"] else None
    sf = (inputs["rotor_yield_MPa"] / peak) if peak else None
    for x in (hoop, notch):
        if x.get("receipt"):
            receipts.append(x["receipt"])
    checks["rotor_hoop_mean_MPa"] = round(mean, 1) if mean else None
    checks["rotor_bridge_Kt_candidate"] = round(Kt, 2) if Kt else None
    checks["rotor_peak_MPa"] = round(peak, 1) if peak else None
    checks["rotor_safety_factor"] = round(sf, 2) if sf else None
    checks["rotor_SF_min"] = inputs["rotor_SF_min"]
    checks["rotor_meets_required_SF"] = (sf is not None and sf >= inputs["rotor_SF_min"])

    # Reference-case torque estimate from governed tangential air-gap shear and candidate
    # dimensions (rotor diameter D, active stack length L); not field-solved torque.
    D_m = (sp.get("rotor_outer_diameter", 0.0) or 2000.0 * r_m) / 1000.0
    L_m = (sp.get("stack_length", 0.0) or 0.0) / 1000.0
    K_peak = inputs["electric_loading_peak_A_per_m"]
    cos_delta = inputs["spatial_phase_factor"]
    shear = _g("equation.em.airgap_shear_stress_fundamental",
               {"B_peak": B, "K_peak": K_peak, "cos_delta": cos_delta})
    checks["airgap_shear_kPa"] = round(shear["value"], 2) if shear["ok"] else None
    checks["electric_loading_peak_A_per_m"] = K_peak
    checks["spatial_phase_factor"] = cos_delta
    if shear["ok"]:
        receipts.append(shear["receipt"])
        mt = _g("equation.em.machine_torque_from_shear",
                {"D": D_m, "L": L_m, "tau_avg_kPa": shear["value"]})
        if mt["ok"]:
            checks["asdesigned_torque_Nm"] = round(mt["value"], 1)
            checks["asdesigned_power_kW"] = round(mt["value"] * omega / 1000.0, 1)
            receipts.append(mt["receipt"])
    # Independent EM-FE cross-check of the air-gap flux (governed, receipt-backed) -- G05.
    try:
        import motor_em_crosscheck as mx
        xc = mx.airgap_flux_crosscheck(B)
        checks["em_flux_crosscheck"] = xc
        if xc.get("receipt"):
            receipts.append(xc["receipt"])
    except Exception as exc:  # pragma: no cover
        checks["em_flux_crosscheck"] = {"ok": False, "withheld": f"{type(exc).__name__}: {exc}"[:120]}
    # the normal pole attraction is radial (no torque); reported only, for reference
    force = _g("equation.em.maxwell_stress_force", {"B": B, "A": inputs["pole_area_m2"]})
    if force.get("receipt"):
        receipts.append(force["receipt"])
    checks["normal_pole_attraction_N"] = round(force["value"], 1) if force["ok"] else None

    # cryogenic budget on the sized design (reuse the governed battery)
    cryo = R.cryo_thermal({**inputs, "rpm": rpm, "B_T": B,
                           "T_K": op.get("T_K") or inputs["T_K"]})
    checks["cold_end_load_W"] = cryo.get("total_cold_load_W")
    checks["cryocooler_input_W"] = cryo.get("cryocooler_input_power_W")
    receipts += [x for x in cryo.get("receipts", []) if x]

    checks["receipts"] = sorted(set(receipts))
    return checks


# --------------------------------------------------------------------------------------
# 4) Manufacturability (DfM) on the governed geometry
# --------------------------------------------------------------------------------------
def dfm_checks(built: dict, *, process: str = "lamination_wire_EDM",
               min_wall_mm: float = 0.3) -> dict:
    """Manufacturability of the governed geometry.

    Primary route is how laminations are actually made in a lab -- wire-EDM / laser / stamp
    of thin electrical-steel sheet (min feature ~0.3 mm). A monolithic metal-AM route
    (min wall ~1.0 mm) is reported as an alternative, since a thin slot bridge that a lab
    can wire-EDM would have to be thickened to print.
    """
    sp = built.get("spec") or {}
    if not sp:
        return {"ok": False, "withheld": "no geometry to assess"}
    bore = sp.get("stator_bore_diameter", 0.0)
    tooth = math.pi * bore / sp.get("slot_count", 1) - sp.get("slot_width", 0.0)
    yoke = (sp.get("stator_outer_diameter", 0.0) / 2
            - (bore / 2 + sp.get("slot_opening_bridge", 0.0) + sp.get("slot_depth", 0.0)))
    features = {
        "tooth_width_mm": round(tooth, 2),
        "stator_yoke_mm": round(yoke, 2),
        "slot_bridge_mm": round(sp.get("slot_opening_bridge", 0.0), 2),
        "magnet_bridge_mm": round(sp.get("magnet_bridge", 0.0), 2),
    }
    min_feature = min(features.values())
    aspect = sp.get("stack_length", 0.0) / max(sp.get("stator_outer_diameter", 1.0), 1e-6)
    AM_MIN = 1.0
    return {
        "process": process, "min_wall_required_mm": min_wall_mm,
        "features_mm": features, "min_feature_mm": round(min_feature, 2),
        "meets_min_wall": min_feature >= min_wall_mm,
        "alt_metal_AM": {"min_wall_mm": AM_MIN, "meets": min_feature >= AM_MIN,
                         "note": "monolithic print would need the thin slot bridge thickened to >= 1 mm"},
        "stack_aspect_L_over_OD": round(aspect, 2),
        "closed_slots_self_supporting": True,
        "ok": min_feature >= min_wall_mm,
        "not_assessed": ["residual stress / distortion", "surface finish / tolerance grade",
                         "lamination stacking factor and insulation", "burr / edge quality"],
    }


# --------------------------------------------------------------------------------------
# 5) Bill of materials (governed volumes -> masses)
# --------------------------------------------------------------------------------------
def bom(built: dict) -> dict:
    rows = []
    v = built.get("verification", {})
    lam = built.get("spec") or {}
    if v.get("lamination", {}).get("ok"):
        import motor_geometry as mg
        vs = mg.stator_material_volume(lam) / 1e9   # mm^3 -> m^3
        vr = mg.rotor_material_volume(lam) / 1e9
        rows.append({"part": "stator lamination", "material": "electrical steel M270-35A",
                     "qty": 1, "volume_cm3": round(vs * 1e6, 1), "mass_kg": round(vs * STEEL_RHO, 3)})
        rows.append({"part": "rotor lamination (reluctance/IPM-proxy)", "material": "electrical steel",
                     "qty": 1, "volume_cm3": round(vr * 1e6, 1), "mass_kg": round(vr * STEEL_RHO, 3)})
    for part, mat, rho in (("coil_former", "G10/copper bobbin (HTS field coil)", 1900.0),
                           ("shaft", "AISI 4340 steel", 7850.0)):
        pv = v.get(part)
        if pv and pv.get("ok"):
            vol_m3 = pv["volume_mm3"] / 1e9
            rows.append({"part": part, "material": mat, "qty": 1,
                         "volume_cm3": round(vol_m3 * 1e6, 1), "mass_kg": round(vol_m3 * rho, 3)})
    total = round(sum(r["mass_kg"] for r in rows), 3)
    return {"rows": rows, "total_mass_kg": total,
            "note": "masses are governed geometry volumes x material density; HTS tape, "
                    "cryostat, bearings and fasteners are catalogue items not sized here."}


# --------------------------------------------------------------------------------------
# Orchestrator -> the DesignPassport
# --------------------------------------------------------------------------------------
def design_engine(design: dict | None = None, *, outdir: str | Path | None = None,
                  dossier: dict | None = None) -> dict:
    dossier = dossier or R.deep_research(design)
    outdir = Path(outdir or (Path.cwd() / "out" / "crfce_engine"))
    sizing = size_from_operating_point(dossier)
    built = build_and_verify(sizing, outdir)
    checks = as_designed_checks(sizing, built)
    dfm = dfm_checks(built)
    parts = bom(built)

    all_receipts = sorted(set(dossier["governed_receipts"] + checks.get("receipts", [])))
    requirements = [
        {"id": "EM-1", "requirement": "reference-case analytical torque estimate (governed air-gap shear)",
         "target": ">= 60 Nm screening target", "result": checks.get("asdesigned_torque_Nm"),
         "status": (checks.get("asdesigned_torque_Nm") or 0) >= 60.0,
         "evidence": "receipt-backed shear and cylindrical torque equations on declared candidate dimensions and study inputs; not an as-built or field-solved result"},
        {"id": "STR-1", "requirement": "rotor safety factor at speed",
         "target": f">= {checks.get('rotor_SF_min')}",
         "result": checks.get("rotor_safety_factor"), "status": checks.get("rotor_meets_required_SF")},
        {"id": "THM-1", "requirement": "cold-end load within a lab cryocooler", "target": "reported",
         "result": checks.get("cold_end_load_W"), "evidence": "governed cryo budget"},
        {"id": "MFG-1", "requirement": "min printable wall", "target": f">= {dfm.get('min_wall_required_mm')} mm",
         "result": dfm.get("min_feature_mm"), "status": dfm.get("meets_min_wall")},
        {"id": "GEO-1", "requirement": "candidate solid dimensions match parametric specification", "target": "generator output back-measured against its own specification",
         "result": built.get("geometry_ok"), "status": built.get("geometry_ok")},
    ]
    passport = {
        "schema": "engineai.crfce_design_passport.v1",
        "class": "reluctance-HTS machine (CRFCE)",
        "maturity_level": MATURITY,
        "evidence_level": "IMPLEMENTED_VIRTUAL_REFERENCE_STUDY",
        "release_authorized": False,
        "design_release_status": "NOT_AUTHORIZED",
        "physical_validation": "NOT_DEMONSTRATED",
        "reference_candidate_scope": candidate_evidence_scope(),
        "operating_point": sizing["operating_point"],
        "sizing": sizing,
        "geometry": {"files": built.get("files", {}), "spec_hash": built.get("spec_hash"),
                     "verification": built.get("verification", {}),
                     "geometry_ok": built.get("geometry_ok"), "withheld": built.get("withheld", [])},
        "as_designed_checks": checks,
        "manufacturability": dfm,
        "bom": parts,
        "requirements_matrix": requirements,
        "research_dossier": dossier,
        "governed_receipts": all_receipts,
        "governed_receipt_count": len(all_receipts),
        "topology_proxy_note": ("rotor pockets are a geometric proxy for the reluctance rotor's "
                                "flux barriers. All generated solids are parametric candidates, not "
                                "evidence of released or as-built hardware or assembly buildability. "
                                "A true salient/flux-barrier rotor and a 3-D EM/torque FEA are the "
                                "next design step."),
        "not_demonstrated": [
            "electromagnetic back-EMF / cogging / torque by 3-D FEA on this exact geometry",
            "winding fill, HTS tape routing and quench protection",
            "thermal-structural coupling and rotor burst spin test",
            "bearing/rotordynamic hardware selection and balancing",
            "physical build, cryogenic cool-down and bench performance",
        ],
        "boundary": BOUNDARY,
    }
    # HONEST maturity: computed from the release gates, NOT asserted. This demotes an
    # analytical sizing study out of "release candidate" until validated solvers, coupled
    # multiphysics, tolerance/UQ and physical correlation are actually demonstrated.
    try:
        import crfce_readiness
        readiness = crfce_readiness.assess(passport, dossier)
        passport["production_readiness"] = readiness
        passport["maturity_level"] = readiness["maturity"]["statement"]
        passport["physical_validation"] = readiness["maturity"]["physical_validation"]
    except Exception as exc:  # pragma: no cover
        passport["production_readiness"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    return passport


def wants_engine_design(message: str) -> bool:
    m = (message or "").lower()
    if "design" in m and "crfce" in m:
        return True
    return any(p in m for p in ("design the engine", "design the real", "produce it in a lab",
                                "lab-producible", "manufacturable design", "build the engine"))


def chat_answer(design: dict | None = None, *, outdir: str | Path | None = None,
                with_paper: bool = True) -> dict:
    """Run the design-study pipeline (and paper) for the chatbox.

    ``released`` below is only the Studio capability-output contract. It never means
    that this design or any hardware configuration is released.
    """
    outdir = Path(outdir or (Path.cwd() / "out" / "crfce_engine"))
    passport = design_engine(design, outdir=outdir)
    paper_files: dict[str, str] = {}
    if with_paper:
        try:
            import crfce_paper
            paper = crfce_paper.write_paper(passport, passport["research_dossier"],
                                            outdir=Path(outdir) / "paper")
            paper_files = paper["files"]
        except Exception as exc:  # pragma: no cover
            passport.setdefault("geometry", {}).setdefault("withheld", []).append(
                f"paper withheld: {type(exc).__name__}: {exc}"[:160])
    op = passport["operating_point"]; c = passport["as_designed_checks"]
    bom = passport["bom"]; geo = passport["geometry"]
    lines = [
        "**CRFCE virtual reference candidate study — governed screens + optional paper**",
        "Not evidence of released or as-built hardware, manufacturing qualification, field-solved torque, or physical validation.",
        "",
        f"- Candidate sizing from the governed reference-study screen: **{op.get('target_power_kW')} kW**, "
        f"{op.get('target_torque_Nm')} N·m, B={op.get('B_T')} T, {op.get('rpm')} rpm, {op.get('T_K')} K",
        f"- Geometry: **{len([k for k in geo['files'] if k.endswith('_step')])} candidate STEP parts** "
        f"(stator, rotor, HTS coil former, shaft), back-checked against their own parametric spec: "
        f"**{'PASS' if geo['geometry_ok'] else 'INCOMPLETE'}**; released/as-built correspondence not established",
        f"- Candidate rotor stress screen: hoop {c.get('rotor_hoop_mean_MPa')} MPa, bridge Kt "
        f"{c.get('rotor_bridge_Kt_candidate')}, **screened safety factor {c.get('rotor_safety_factor')}** "
        f"(meets {c.get('rotor_SF_min')}: {c.get('rotor_meets_required_SF')})",
        f"- Cryo budget: cold-end load {c.get('cold_end_load_W')} W → cryocooler input "
        f"{c.get('cryocooler_input_W')} W",
        f"- Preliminary DfM screen (not manufacturing qualification): {passport['manufacturability'].get('process')}, min feature "
        f"{passport['manufacturability'].get('min_feature_mm')} mm → "
        f"{'OK' if passport['manufacturability'].get('meets_min_wall') else 'REVISE'}; "
        f"BOM {bom['total_mass_kg']} kg core mass",
        f"- Governed receipts: **{passport['governed_receipt_count']}**; maturity "
        f"**{passport['maturity_level'].split('--')[0].strip()}**",
    ]
    if paper_files:
        lines.append(f"- Paper generated: `{Path(paper_files.get('pdf','')).name}` (PDF), "
                     f"`{Path(paper_files.get('html','')).name}` (HTML), plus figures")
    lines += ["", f"_{passport['boundary']}_"]
    return {
        "ok": True, "basis": "CRFCE_ENGINE_DESIGN", "released": True,
        "released_scope": R.EXECUTOR_RELEASE_SCOPE,
        "release_authorized": False, "design_release_status": "NOT_AUTHORIZED",
        "physical_validation": "NOT_DEMONSTRATED",
        "engineering_claim": True, "verified": False,
        "capability": "crfce_engine_design.design_engine", "id": "crfce_engine_design.design_engine",
        "answer": "\n".join(lines),
        "value": op.get("target_power_kW"), "unit": "kW",
        "receipt_digest": (passport["governed_receipts"] or [""])[0],
        "governed": passport, "paper_files": paper_files,
        "note": passport["boundary"], "actions": [],
    }


def _print(p: dict) -> None:
    print("=" * 90)
    print(f"ENGINEAI CRFCE ENGINE DESIGN  --  {p['class']}")
    print("=" * 90)
    op = p["operating_point"]
    print(f"  operating point : {op.get('target_power_kW')} kW, {op.get('target_torque_Nm')} Nm, "
          f"B={op.get('B_T')} T, {op.get('rpm')} rpm, {op.get('T_K')} K")
    g = p["geometry"]
    print(f"  geometry        : ok={g['geometry_ok']}  files={list(g['files'].keys())}")
    if g["withheld"]:
        print(f"    withheld      : {g['withheld']}")
    c = p["as_designed_checks"]
    print(f"  candidate screen: Kt={c.get('rotor_bridge_Kt_candidate')}, SF={c.get('rotor_safety_factor')} "
          f"(meets {c.get('rotor_SF_min')}: {c.get('rotor_meets_required_SF')}), "
          f"cold load {c.get('cold_end_load_W')} W")
    d = p["manufacturability"]
    print(f"  DfM             : min feature {d.get('min_feature_mm')} mm >= {d.get('min_wall_required_mm')} mm "
          f"-> {d.get('meets_min_wall')}")
    print(f"  BOM             : {len(p['bom']['rows'])} parts, {p['bom']['total_mass_kg']} kg core mass")
    print(f"  maturity        : {p['maturity_level'].split('--')[0].strip()}")
    print(f"  receipts        : {p['governed_receipt_count']}   physical validation: {p['physical_validation']}")
    print("=" * 90)


if __name__ == "__main__":
    _print(design_engine())
