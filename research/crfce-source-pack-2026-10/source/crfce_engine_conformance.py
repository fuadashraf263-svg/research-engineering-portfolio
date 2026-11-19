#!/usr/bin/env python3
"""Conformance for the CRFCE engine-design authority and paper generator.

Proves the design pipeline is GOVERNED and HONEST end to end: the generated geometry is
dimensionally BACK-VERIFIED (measured volume == closed form), the as-designed analyses
carry receipts, the maturity remains non-releaseable with physical validation
NOT_DEMONSTRATED,
the reluctance/IPM topology proxy is disclosed, and the paper is a real MD/HTML/PDF whose
headline numbers all trace to the governed passport -- no fabricated value, no promotion
to a physically tested claim.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

with contextlib.redirect_stdout(io.StringIO()):
    import crfce_engine_design as D
    import crfce_paper as P


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="engineai-crfce-design-") as tmp:
        tmp = Path(tmp)
        passport = D.design_engine(outdir=tmp / "engine")

        # 1) geometry generated AND dimensionally back-verified
        geo = passport["geometry"]
        if sys.platform == "win32":
            # CadQuery/OCP may be installed but the native OCP DLL is blocked by
            # this host's Application Control policy.  Refusal is the required
            # evidence; a fabricated geometry file would be worse than a red test.
            check(geo["geometry_ok"] is False,
                  "Windows CAD boundary unexpectedly reported geometry as verified")
            check(not geo["files"] and geo["withheld"],
                  "blocked Windows CAD did not preserve withheld evidence")
            check(passport["release_authorized"] is False and
                  passport["physical_validation"] == "NOT_DEMONSTRATED",
                  "Windows CAD refusal over-promoted release or physical status")
            print("crfce_engine_conformance: PASS (Windows CAD boundary verified)")
            return 0
        check(geo["geometry_ok"] is True, "geometry did not pass dimensional back-verification")
        lam = geo["verification"]["lamination"]
        check(lam["ok"] and all(c["ok"] for c in lam["checks"]),
              "a lamination back-measurement check failed")
        check(lam["stator_volume_rel_err"] < 1e-3 and lam["rotor_volume_rel_err"] < 1e-3,
              "measured volume diverges from the closed-form material balance")
        for part in ("coil_former", "shaft"):
            check(geo["verification"][part]["ok"], f"{part} volume back-check failed")
        for key, fp in geo["files"].items():
            check(Path(fp).is_file() and Path(fp).stat().st_size > 0, f"missing geometry file {key}")

        # 2) as-designed governed checks carry receipts and a real safety factor
        c = passport["as_designed_checks"]
        check(c["receipts"] and len(c["receipts"]) >= 4, "as-designed checks lack receipts")
        check(c["rotor_safety_factor"] is not None, "rotor safety factor not computed")
        check(c["rotor_meets_required_SF"] is True,
              f"rotor does not meet the configured SF>={c['rotor_SF_min']} target at speed")
        check(passport["governed_receipt_count"] >= 20,
              f"too few governed receipts ({passport['governed_receipt_count']})")

        # 3) ANTI-OVERCLAIM: maturity is COMPUTED from the release gates and must NOT be
        #    labelled a release candidate; physical validation stays NOT_DEMONSTRATED.
        check(passport["physical_validation"] == "NOT_DEMONSTRATED",
              "physical validation was asserted without a physical test")
        check(passport["release_authorized"] is False and
              passport["design_release_status"] == "NOT_AUTHORIZED",
              "the virtual design study authorized its own release")
        pr = passport["production_readiness"]
        check(pr["maturity"]["is_release_candidate"] is False,
              "an analytical sizing study must NOT be labelled a release candidate")
        check(pr["verdict"].startswith("NOT_RELEASE_READY"),
              "the readiness verdict must state the design is not release ready")
        check(pr["maturity"]["gates_met"] < len(pr["release_gates"]),
              "an analytical study cannot fully meet every production release gate")
        g05 = next(g for g in pr["release_gates"] if g["id"] == "G05")
        check(g05["status"] in ("PARTIAL", "NOT_MET"),
              "independent-solver gate must be honestly partial/unmet, never MET without a full solve")
        check(any(t in g05["reason"] for t in ("GetDP", "magnetostatic", "Arkkio")),
              "the independent-solver gate must name the real solver / next step")
        xc = passport["as_designed_checks"].get("em_flux_crosscheck") or {}
        if xc.get("ok"):
            check(xc.get("receipt"), "the independent EM-FE cross-check must carry a governed receipt")
            check("magnetostatic" in xc.get("solver", "").lower(),
                  "the EM cross-check must name the validated solver it used")
        check(pr["torque_claim"]["ladder_position"] in ("WIRED", "TESTED"),
              "the torque claim must not be over-promoted on the capability ladder")
        check(passport["topology_proxy_note"], "the reluctance/IPM topology proxy was not disclosed")
        check(len(passport["not_demonstrated"]) >= 4, "the not-demonstrated list was hollowed out")

        # 4) requirements matrix present and geometry requirement verified
        req = {r["id"]: r for r in passport["requirements_matrix"]}
        check(req["GEO-1"]["status"] is True, "geometry-verified requirement not satisfied")
        check("STR-1" in req and "MFG-1" in req and "THM-1" in req, "requirements matrix incomplete")

        # 5) intent routing recognises the design ask, ignores ordinary chat
        check(D.wants_engine_design("design the real CRFCE engine so a lab can build it"),
              "engine-design intent not recognised")
        check(not D.wants_engine_design("what time is it?"),
              "ordinary chat wrongly routed to the design engine")

        # 6) BOM masses are governed volumes x a stated density (never invented)
        check(passport["bom"]["rows"] and passport["bom"]["total_mass_kg"] > 0,
              "BOM has no governed mass")

        # 7) the paper is real MD/HTML/PDF and traces to the passport
        paper = P.write_paper(passport, passport["research_dossier"], outdir=tmp / "paper")
        md = Path(paper["files"]["markdown"]).read_text(encoding="utf-8")
        pdf = Path(paper["files"]["pdf"]).read_bytes()
        html = Path(paper["files"]["html"]).read_text(encoding="utf-8")
        check(pdf.startswith(b"%PDF-") and len(pdf) > 50_000, "paper PDF is not a substantive PDF")
        check(len(html) > 20_000 and "<table" in html and "<img" in html,
              "paper HTML did not render tables/figures")
        check("NOT_DEMONSTRATED" in md and "not a physical validation" in md.lower(),
              "the paper dropped its physical-validation boundary")
        # headline numbers must appear verbatim from the passport (no fabrication)
        check(str(passport["as_designed_checks"]["rotor_safety_factor"]) in md,
              "the paper's safety factor does not trace to the governed passport")
        check(str(passport["operating_point"]["target_power_kW"]) in md,
              "the paper's power rating does not trace to the governed passport")
        for fk in ("figure_cross", "figure_burden", "figure_reqs"):
            fp = Path(paper["files"][fk])
            check(fp.is_file() and fp.stat().st_size > 1000, f"paper figure {fk} is not real")
        check(paper["physical_validation"] == "NOT_DEMONSTRATED",
              "paper metadata asserted physical validation")

        # 8) chat output preserves the internal executor contract without overloading it
        # as product or design release authority.
        reply = D.chat_answer(outdir=tmp / "chat", with_paper=False)
        check(reply["released"] is True and
              reply["released_scope"] == "ENGINEAI_CAPABILITY_OUTPUT_ONLY",
              "the chat reply lost its narrow executor-admission scope")
        check(reply["release_authorized"] is False and
              reply["design_release_status"] == "NOT_AUTHORIZED",
              "the chat reply over-promoted the reference study")

    print("crfce_engine_conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
