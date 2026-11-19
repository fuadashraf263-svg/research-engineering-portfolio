#!/usr/bin/env python3
"""Conformance for the CRFCE deep-research battery (crfce_research.py).

Proves the battery is GOVERNED and HONEST: every headline number is backed by a
capability receipt crossing the authority boundary; the adversarial battery actually
rejects unphysical designs (reasoning, not a passing render); the reconciliation
SURFACES the enhancement peak as optimistic rather than rubber-stamping it; withheld
models are named not fabricated; residual unknowns stay named; and nothing is promoted
to physical validation.
"""
from __future__ import annotations

import contextlib
import io
import re

with contextlib.redirect_stdout(io.StringIO()):
    import crfce_research as C


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    d = C.deep_research()

    # 1) crosses the governed boundary: substantial receipts, all content digests
    check(d["governed_receipt_count"] >= 12,
          f"too few governed receipts ({d['governed_receipt_count']})")
    hexpat = re.compile(r"^[0-9a-f]{6,}$")
    check(all(hexpat.match(r) for r in d["governed_receipts"]),
          "a governed receipt is not a content digest")

    # 1b) TORQUE PHYSICS (anti-regression): torque must come from the governed TANGENTIAL
    #     air-gap shear, never the normal pole force. A machine with no winding current
    #     (zero electric loading) must produce ZERO torque -- the normal-force method could
    #     never capture that, so this pins the correct physics permanently.
    em = d["electromagnetic"]
    check(em.get("airgap_shear_kPa") is not None,
          "torque is not derived from the governed air-gap shear stress")
    check("normal_pole_attraction_N" in em,
          "the normal pole force must be reported separately as radial attraction, not torque")
    zero = C.electromagnetic({**C.REFERENCE, "electric_loading_peak_A_per_m": 0.0})
    check(zero.get("torque_Nm") in (None, 0, 0.0),
          "zero electric loading must give zero torque -- torque needs a real winding")

    # 2) each executor-admitted headline number is backed by a domain receipt
    check(d["electromagnetic"]["receipts"], "EM block admitted no receipts")
    check(d["rotor_structural"]["receipts"], "structural block admitted no receipts")
    check(d["cryogenic_thermal"]["receipts"], "cryo block admitted no receipts")
    check(d["headline"]["baseline_power_kW"] is not None, "baseline power not governed")
    check(d["headline"]["total_cold_load_W"] is not None, "cold-end load not governed")

    # 3) adversarial battery actually rejects EVERY unphysical design
    adv = d["adversarial_battery"]
    check(adv["all_caught"] and adv["attacks"] >= 4,
          f"adversarial battery did not reject every attack ({adv['caught']}/{adv['attacks']})")
    for t in adv["tests"]:
        check(t["caught"] is True, f"attack not caught: {t['attack']}")

    # 4) reconciliation corrects the enhancement rather than rubber-stamping it
    rec = d["reconciliation"]
    check(rec["governed_notch_Kt"] is not None and rec["enhancement_assumed_Kt"] is not None,
          "reconciliation missing the Kt comparison")
    check(rec["governed_notch_Kt"] > rec["enhancement_assumed_Kt"],
          "governed notch Kt should exceed the assumed value for the sharp slot root")
    check(rec["enhancement_peak_optimistic"] is True,
          "the optimistic-peak correction was not surfaced")

    # 5) governed optimisation returned a structurally-safe feasible point under ALL constraints
    best = d["optimization_sweep"]["best_feasible_operating_point"]
    check(best is not None and best.get("sf_on_peak") is not None and best["sf_on_peak"] >= 1.5,
          "optimisation did not return a structurally-safe feasible point")
    check(d["optimization_sweep"]["feasible_points"] >= 1, "no feasible sweep point found")

    # 6) HONESTY: no physical-validation claim; boundary intact; withheld models explicit
    check("not a physical validation" in d["boundary"].lower(),
          "the physical-validation boundary was dropped")
    check(isinstance(d["withheld_governed_models"], list),
          "withheld models must be an explicit (possibly empty) list, never hidden")
    check(d["release_authorized"] is False and d["design_release_status"] == "NOT_AUTHORIZED",
          "virtual research was allowed to authorize design release")
    check(d["physical_validation"] == "NOT_DEMONSTRATED",
          "virtual research asserted physical validation")

    # Reference defaults and user overrides remain distinguishable.
    check(all(v == "REFERENCE_ASSUMPTION" for v in d["input_provenance"].values()),
          "the default case was not labelled as reference assumptions")
    overridden = C.deep_research({"rpm": 3000.0})
    check(overridden["input_provenance"]["rpm"] == "USER_SUPPLIED_UNVERIFIED",
          "a user override lost its provenance class")

    # 7) residual unknowns stay NAMED (never dishonestly zeroed)
    check(len(d["residual_unknowns"]) >= 3, "residual unknowns were dishonestly zeroed")

    # 8) intent routing recognises the CRFCE ask and ignores ordinary chat
    check(C.wants_deep_research("do all kinds of research on CRFCE and advance it far more"),
          "CRFCE deep-research intent not recognised")
    check(not C.wants_deep_research("hello, what is your name?"),
          "ordinary chat was wrongly routed to the research battery")

    # 9) a razor-thin slot root must NOT pass the structural check (governed rejection)
    sharp = C.rotor_structural(C._cfg({"slot_root_radius_m": 2e-5}))
    check(sharp["meets_SF_min"] is False,
          "a razor-thin slot root should fail the governed structural check")

    # 10) the chat reply is honest: governed but NOT marked verified
    reply = C.chat_answer()
    check(reply["basis"] == "CRFCE_DEEP_RESEARCH" and reply["released"] is True,
          "chat reply lost its governed basis")
    check(reply["verified"] is False,
          "a governed analysis must not be reported as verified/physically validated")
    check(reply["released_scope"] == C.EXECUTOR_RELEASE_SCOPE and
          reply["release_authorized"] is False,
          "the legacy released field was not narrowed to capability-output scope")
    check(reply["receipt_digest"], "chat reply carries no receipt")

    print("crfce_research_conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
