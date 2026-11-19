#!/usr/bin/env python3
"""crfce_readiness.py -- honest production-readiness gate for the CRFCE design.

The design pipeline can size a machine and generate back-verified geometry, but that is
NOT a production-ready design. This module scores a DesignPassport against the ten
industry release gates (ASME VVUQ in spirit; ISO 26262 for an automotive drive) and a
strict capability ladder, and it computes the HONEST maturity level from what is actually
demonstrated -- not from optimism. It exists so EngineAI stops over-labelling: a governed
analytical sizing is L1-L2, never a release candidate.

A capability/solver may NEVER label its own output FINAL. Only met gates raise the level;
unmet gates cap it. Physical-test correlation is required before L4+, and can never be
granted by simulation.
"""
from __future__ import annotations

from typing import Any

# Maturity ladder (matches the agreed definition).
LEVELS = ["L0_CONCEPT", "L1_CALCULATED", "L2_SIMULATED", "L3_VERIFIED",
          "L4_VALIDATED", "L5_RELEASE_CANDIDATE", "L6_REAL_WORLD_QUALIFIED"]

# Capability ladder for a single claim.
LADDER = ["IMPLEMENTED", "WIRED", "TESTED", "LIVE_VERIFIED", "REFERENCE_VALIDATED"]


def _gate(idx: int, name: str, status: str, reason: str) -> dict:
    return {"id": f"G{idx:02d}", "gate": name, "status": status, "reason": reason}


def _g05(passport: dict) -> tuple[str, str]:
    """G05 status from the independent EM-FE flux cross-check, if one ran."""
    xc = ((passport.get("as_designed_checks") or {}).get("em_flux_crosscheck") or {})
    if xc.get("ok") and xc.get("receipt"):
        base = (f"an independently cross-verified magnetostatic FE (emag.gapped_core_fea, receipt "
                f"{xc['receipt']}) now cross-checks the torque's critical input, the air-gap "
                f"flux: assumed {xc.get('B_g_assumed_T')} T vs FE {xc.get('B_g_fea_T')} T "
                f"(agreement {xc.get('agreement_fea_over_assumed')}). ")
        if xc.get("flux_confirmed"):
            tail = ("FLUX CONFIRMED below saturation. Remaining for MET: nonlinear-B-H + "
                    "anisotropic Jc(B,T,theta)/E-J/AC-loss HTS EM and Arkkio motor torque via "
                    "GetDP+Gmsh; independent multiphysics via Elmer.")
        else:
            tail = ("but the operating point is near iron saturation, which a LINEAR FE cannot "
                    "confirm -- a nonlinear B-H solve (GetDP) is required. Full HTS EM + Arkkio "
                    "torque via GetDP+Gmsh remain.")
        return "PARTIAL", base + tail
    return ("NOT_MET",
            "torque has no independent EM-FEA cross-check. NEXT STEP: solve the magnetic "
            "circuit with the in-repo cross-verified magnetostatics.py, then GetDP+Gmsh for HTS EM "
            "and Arkkio motor torque.")


def release_gates(passport: dict, dossier: dict) -> list[dict]:
    """The ten gates. status in {MET, PARTIAL, NOT_MET}."""
    geo_ok = bool((passport.get("geometry") or {}).get("geometry_ok"))
    adv = (dossier.get("adversarial_battery") or {})
    dfm = passport.get("manufacturability") or {}
    withheld = (dossier.get("withheld_governed_models") or [])
    gates = [
        _gate(1, "Analytical / reference benchmark passed",
              "PARTIAL",
              "the 2-D magnetostatic FE solver (magnetostatics.py) is benchmarked against "
              "Ampere's law/reluctance/skin-depth, but the motor TORQUE itself is an "
              "analytical air-gap-shear sizing, not a benchmarked motor solve"),
        _gate(2, "Mesh / time-step independence",
              "NOT_MET",
              "no motor EM/thermal/structural mesh exists; the CAD is back-verified but no "
              "field solve was meshed or refined"),
        _gate(3, "Solver convergence",
              "NOT_MET",
              "torque/flux/thermal are closed-form or reduced-order; no iterative solver was "
              "run to convergence on this machine"),
        _gate(4, "Material data valid at every predicted condition",
              "PARTIAL",
              "densities and room-temperature yield are handbook values; the cryogenic-"
              f"temperature yield lookup REFUSED (out of envelope) -- {len(withheld)} governed "
              "models withheld and named, not fabricated"),
        _gate(5, "Independent solver comparison for critical claims",
              *_g05(passport)),
        _gate(6, "Coupled EM / thermal / structural / control multiphysics",
              "NOT_MET",
              "each analysis is standalone; no co-simulation or dependency propagation "
              "between the electromagnetic, thermal and structural models"),
        _gate(7, "Worst-case tolerance and uncertainty analysis",
              "NOT_MET",
              "no tolerance stack-up or propagated uncertainty band on torque/stress/thermal "
              "(OpenTURNS is available but not yet wired into this design)"),
        _gate(8, "Manufacturability and inspection plan",
              "PARTIAL" if dfm.get("meets_min_wall") else "NOT_MET",
              f"min feature {dfm.get('min_feature_mm')} mm vs the wire-EDM limit is checked, "
              "but there is no GD&T, tolerance grade, inspection plan or process routing"),
        _gate(9, "Prototype measurements correlated with predictions",
              "NOT_MET",
              "no physical hardware has been built, cooled, spun or measured -- physical "
              "validation is NOT_DEMONSTRATED and cannot be granted by simulation"),
        _gate(10, "Engineer review and formal release approval",
              "NOT_MET",
              "no qualified human engineering review or formal release sign-off has occurred; "
              "an AI system may not self-approve a production release"),
    ]
    # G8 depends on geometry actually existing
    if not geo_ok:
        for g in gates:
            if g["id"] == "G08":
                g["status"], g["reason"] = "NOT_MET", "geometry did not back-verify"
    return gates


def honest_maturity(gates: list[dict]) -> dict:
    """Compute the defensible maturity level from the gates. Unmet gates cap the level."""
    met = {g["id"]: g["status"] for g in gates}
    # Caps: no independent verification (G05) or convergence/mesh (G02,G03) -> at most L2.
    #       no coupled physics (G06) -> at most L3. no validation data (G09) -> at most L3.
    #       no tolerance/UQ (G07) -> at most L4. release needs ALL. L6 needs physical (G09).
    verified = all(met.get(g) == "MET" for g in ("G02", "G03", "G05"))
    validated = met.get("G09") == "MET"
    coupled = met.get("G06") == "MET"
    tolerance = met.get("G07") == "MET"
    all_met = all(g["status"] == "MET" for g in gates)
    if all_met:
        level = "L5_RELEASE_CANDIDATE"
    elif validated and verified and coupled:
        level = "L4_VALIDATED"
    elif verified and coupled:
        level = "L3_VERIFIED"
    elif verified:
        level = "L2_SIMULATED"
    else:
        # reduced-order/analytical sizing with back-verified geometry
        level = "L2_SIMULATED" if any(g["status"] in ("MET", "PARTIAL") for g in gates) else "L1_CALCULATED"
    n_met = sum(1 for g in gates if g["status"] == "MET")
    n_partial = sum(1 for g in gates if g["status"] == "PARTIAL")
    statement = (f"{level}: analytical/reduced-order governed sizing with back-verified "
                 f"geometry. {n_met}/{len(gates)} release gates fully met, {n_partial} "
                 f"partial. Independent technical review and signed release authority "
                 f"remain separate decisions; simulation cannot grant real-world qualification.")
    if not all_met:
        statement += (" This configuration is NOT a release candidate; independent-solver "
                      "verification, coupled multiphysics, tolerance/UQ, physical-test "
                      "correlation, or human approval remain incomplete.")
    return {
        "level": level,
        "is_release_candidate": level in ("L5_RELEASE_CANDIDATE", "L6_REAL_WORLD_QUALIFIED"),
        "release_authorized": False,
        "gates_met": n_met, "gates_partial": n_partial, "gates_total": len(gates),
        "physical_validation": "NOT_DEMONSTRATED" if not validated else "CORRELATED",
        "statement": statement,
    }


def torque_ladder(dossier: dict) -> dict:
    """Where the torque claim sits on the capability ladder (strict)."""
    em = dossier.get("electromagnetic") or {}
    has_shear = em.get("airgap_shear_kPa") is not None
    return {
        "claim": "motor torque",
        "method": ("preliminary smooth-air-gap fundamental screening "
                   "(em.machine_torque_from_shear on em.airgap_shear_stress_fundamental)"),
        "ladder_position": "TESTED" if has_shear else "WIRED",
        "not_yet": ["LIVE_VERIFIED (independent EM-FEA on this geometry)",
                    "REFERENCE_VALIDATED (measured dynamometer torque)"],
        "note": "governed and unit-checked and sanity-tested (zero current -> zero torque), "
                "but NOT verified by an independent electromagnetic solver or physical test.",
    }


def assess(passport: dict, dossier: dict) -> dict:
    gates = release_gates(passport, dossier)
    maturity = honest_maturity(gates)
    return {
        "schema": "engineai.crfce_readiness.v1",
        "release_gates": gates,
        "maturity": maturity,
        "torque_claim": torque_ladder(dossier),
        "capability_ladder": LADDER,
        "standards_context": [
            "ASME V&V 10 / V&V 20 are methodological references; project applicability and edition require authority selection",
            "ASME Y14.5 is a candidate GD&T reference -- drawings and applicability are not yet established",
            "No sector safety standard, certification basis, edition, or jurisdiction has been approved for this reference study",
        ],
        "release_authorized": False,
        "physical_validation": maturity["physical_validation"],
        "verdict": ("NOT_RELEASE_READY -- this is a governed analytical design study, not a "
                    "production-ready engine. It orchestrates the physics tools EngineAI has; "
                    "it does not replace high-fidelity solvers or physical validation."),
    }


if __name__ == "__main__":
    import contextlib, io, json
    with contextlib.redirect_stdout(io.StringIO()):
        import crfce_engine_design as D
    p = D.design_engine()
    r = assess(p, p["research_dossier"])
    print(json.dumps({"maturity": r["maturity"], "verdict": r["verdict"],
                      "gates": [(g["id"], g["status"]) for g in r["release_gates"]]}, indent=1))
