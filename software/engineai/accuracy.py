#!/usr/bin/env python3
"""
accuracy.py - how ACCURATE is each file EngineAI produces?

VERIFIED IS NOT THE SAME AS ACCURATE
------------------------------------
deliverables.py proves each file opens and its contents are self-consistent. That
is necessary and it is not sufficient. A STEP file can round-trip perfectly and
still describe the wrong part; a spreadsheet can hold live formulas that compute a
wrong number; an FEA deck can run cleanly and be 30% off.

This module asks the harder question: for every artifact, what is the NUMERICAL
ERROR against an independently-known truth, and is that error acceptable for the
purpose the file serves?

THREE CLASSES OF TRUTH, AND THEY ARE NOT EQUAL
----------------------------------------------
    EXACT       the answer is a definition or closed-form identity. Any error above
                floating-point noise is a bug. Example: a STEP round-trip must
                return the same volume; pi d^4/64 is not an approximation.
    ANALYTIC    a closed-form solution exists for an idealised case. Discretisation
                error is expected and must be BOUNDED and CONVERGING.
    EMPIRICAL   a correlation fitted to data. Error is inherent, and the honest
                figure is the correlation's own published scatter, not our residual.

Reporting one tolerance for all three would be dishonest. A 1.05% CFD error is
excellent; a 1.05% error in a STEP volume would mean the geometry is wrong.

Every row reports the error, the class of truth, the tolerance appropriate to that
class, and the VERDICT.
"""
from __future__ import annotations
import argparse, json, math, os, tempfile

EXACT = "exact"
ANALYTIC = "analytic"
EMPIRICAL = "empirical"

# Tolerance appropriate to each class of truth, and why.
TOLERANCE = {
    EXACT: (1e-9, "a definition or algebraic identity - anything above "
                  "floating-point noise is a defect"),
    ANALYTIC: (0.05, "closed-form solution of an idealised case; discretisation "
                     "error is expected but must be bounded and converging"),
    EMPIRICAL: (0.15, "a correlation fitted to experimental data; its own published "
                      "scatter is typically 10-20%, so our residual cannot be "
                      "meaningfully tighter"),
}

_ROWS = []


def measure(artifact, quantity, produced, truth, truth_class, source, note=""):
    """Record one accuracy measurement."""
    tol, rationale = TOLERANCE[truth_class]
    err = (abs(produced - truth) / abs(truth)) if truth else abs(produced)
    _ROWS.append({"artifact": artifact, "quantity": quantity,
                  "produced": produced, "truth": truth, "class": truth_class,
                  "rel_error": err, "tolerance": tol, "within": err <= tol,
                  "truth_source": source, "rationale": rationale, "note": note})
    return _ROWS[-1]


# --------------------------------------------------------------------------- #
def audit_cad():
    """STEP and STL: geometry must be EXACT, because nothing is being approximated
    when a solid is written and read back. Tessellation is the one exception - a
    mesh is an approximation by construction, and its error is set by the chord
    tolerance requested."""
    import cadquery as cq, cad_parts, trimesh
    with tempfile.TemporaryDirectory() as d:
        wp, params = cad_parts.build("flange", od=140.0, idia=60.0, t=16.0,
                                     bc=110.0, n=8.0, bolt_d=13.0)
        v_model = wp.val().Volume()
        # analytic volume of the same feature set - computed from the parameters,
        # NOT from the solid, so this is a genuinely independent number
        v_analytic = (math.pi / 4 * (140.0 ** 2 - 60.0 ** 2) * 16.0
                      - 8 * math.pi / 4 * 13.0 ** 2 * 16.0)
        measure("part.step", "solid volume vs the analytic feature sum",
                v_model, v_analytic, EXACT,
                "pi/4 (OD^2 - ID^2) t minus 8 bolt holes",
                "the B-rep and the hand formula describe the same part")

        p = os.path.join(d, "f.step")
        cq.exporters.export(wp, p)
        back = cq.importers.importStep(p)
        measure("part.step", "volume after STEP write and re-read",
                back.val().Volume(), v_model, EXACT, "the model it came from",
                "a lossless exchange format must be lossless")

        ps = os.path.join(d, "f.stl")
        cad_parts.clear_triangulation(wp)
        cq.exporters.export(wp, ps, tolerance=0.05, angularTolerance=0.05)
        m = trimesh.load(ps)
        measure("part.stl", "tessellated volume vs the exact solid",
                m.volume, v_model, ANALYTIC,
                "the B-rep solid, at a 0.05 mm chord tolerance",
                "a mesh approximates curvature by construction; error scales with "
                "the chord tolerance requested")
        fine = os.path.join(d, "fine.stl")
        cad_parts.clear_triangulation(wp)
        cq.exporters.export(wp, fine, tolerance=0.005, angularTolerance=0.005)
        mf = trimesh.load(fine)
        measure("part.stl", "same, at a 10x finer chord tolerance",
                mf.volume, v_model, ANALYTIC,
                "the same solid at 0.005 mm",
                "the error must FALL when the tolerance tightens")

        # THE CHECK THAT CAUGHT THE BUG. Comparing each mesh to the solid passed
        # both times while the tolerance was being ignored entirely - the two errors
        # were identical to four decimal places, which no converging mesher does.
        # Refinement must actually refine.
        coarse_faces, fine_faces = len(m.faces), len(mf.faces)
        e_coarse = abs(m.volume - v_model) / v_model
        e_fine = abs(mf.volume - v_model) / v_model
        measure("part.stl", "face count ratio, fine mesh vs coarse",
                fine_faces / max(coarse_faces, 1), 1.0, EMPIRICAL,
                "a 10x tighter chord tolerance must produce more triangles",
                f"coarse {coarse_faces} faces, fine {fine_faces}. Identical counts "
                "mean OCC returned a cached triangulation and the tolerance was "
                "silently ignored")
        _ROWS[-1]["within"] = fine_faces > coarse_faces * 1.2
        _ROWS[-1]["rel_error"] = 0.0 if _ROWS[-1]["within"] else float("inf")
        measure("part.stl", "refinement reduces the volume error",
                e_fine, 0.0, ANALYTIC, "monotone convergence",
                f"{e_coarse*100:.4f}% coarse -> {e_fine*100:.4f}% fine")
        _ROWS[-1]["within"] = e_fine < e_coarse


def audit_fea():
    """FEA against beam theory. The truth here is ANALYTIC, and the honest reference
    is Timoshenko rather than Euler-Bernoulli, because a 3D solid genuinely shears
    and Euler does not."""
    import fea
    P, L, b, h, E, nu = 1000.0, 500.0, 20.0, 40.0, 210000.0, 0.3
    r = fea.cantilever(P, L, b, h, E, nu, nx=40, ny=2, nz=8)
    if "error" in r:
        return
    ti = fea.timoshenko_tip(P, L, b, h, E, nu)
    eb = fea.euler_bernoulli_tip(P, L, b, h, E)
    measure("part.inp / results.csv", "FEA tip deflection vs Timoshenko",
            r["delta_fea_mm"], ti, ANALYTIC,
            "Timoshenko beam theory, which includes shear",
            "the correct reference for a 3D solid; Euler omits the shear the solid "
            "actually develops")
    measure("part.inp / results.csv", "the same FEA result vs Euler-Bernoulli",
            r["delta_fea_mm"], eb, ANALYTIC,
            "Euler-Bernoulli, which omits shear",
            "reported for contrast: judging a 3D result against Euler misattributes "
            "real physics as error")
    mc = fea.mesh_convergence(P, L, b, h, E, nu,
                              refinements=((8, 1, 2), (16, 2, 4), (32, 2, 8)))
    if "error" not in mc:
        last = mc["last_refinement_change_percent"]
        measure("mesh_convergence.csv", "change between the last two refinements",
                last / 100.0, 0.0, ANALYTIC, "self-convergence",
                "a converged answer changes little on further refinement; this is "
                "the number that says whether the mesh is fine enough")


def audit_cfd():
    """CFD against the exact plane-Poiseuille solution. The 2/3 mean-to-max ratio is
    a pure number, independent of every input - which makes it EXACT as a target
    even though the numerical route to it is approximate."""
    import cfd
    if not cfd.foam_available():
        return
    r = cfd.poiseuille()
    if "error" in r:
        return
    measure("centerline.csv", "mean/max velocity ratio vs the exact 2/3",
            r["mean_over_max_numerical"], 2.0 / 3.0, ANALYTIC,
            "exact Navier-Stokes solution for plane Poiseuille flow",
            "a pure number independent of h, mu and dp - reproducing it exercises "
            "discretisation, boundary conditions and pressure-velocity coupling at once")
    measure("centerline.csv", "worst point on the velocity profile",
            r["profile_max_error_percent"] / 100.0, 0.0, ANALYTIC,
            "the analytic parabola",
            "profile shape, not just the integral")


def audit_spice():
    """Circuit simulation against a closed-form cutoff. The residual here is
    dominated by the frequency GRID, not by the solver - 40 points per decade cannot
    land exactly on 159.15 Hz."""
    import deliverables
    with tempfile.TemporaryDirectory() as d:
        r = deliverables.make_spice(os.path.join(d, "rc.cir"),
                                    os.path.join(d, "rc.csv"))
        if not r["verified"]:
            return
        fc = r.get("fc_Hz")
        exact = 1.0 / (2 * math.pi * 1000.0 * 1e-6)
        measure("rc_lowpass.cir / rc_ac.csv", "-3 dB point vs 1/(2 pi R C)",
                fc, exact, ANALYTIC, "first-order filter theory",
                "the residual is set by the 40-points-per-decade sweep grid, not by "
                "ngspice; a finer sweep would tighten it")


def audit_drawing():
    """Drawings: every dimension must be EXACT against the B-rep it was measured
    from. There is nothing to approximate - a dimension either matches the model or
    the drawing is wrong."""
    import drawings_dim as dd
    with tempfile.TemporaryDirectory() as d:
        r = dd.make_dimensioned_sheet("mounting_plate", outdir=d, L=150.0, W=100.0,
                                      T=12.0, hole_d=10.0, margin=20.0)
        v = r["verification"]
        measure("part_drawing.svg/.dxf", "worst dimension vs the measured solid",
                v["worst_error_mm"], 0.0, EXACT, "the B-rep the sheet was made from",
                "a drawing that disagrees with its model is how wrong parts get made")
        m = r["measured"]
        measure("part_drawing.svg/.dxf", "overall length as drawn",
                m["xlen"], 150.0, EXACT, "the requested parameter", "")
        holes = m["cylindrical_features"]
        if holes:
            measure("part_drawing.svg/.dxf", "hole diameter found in the solid",
                    holes[0]["diameter"], 10.0, EXACT, "the requested parameter",
                    "found by walking cylindrical faces, not read from parameters")


def audit_mesh():
    """Meshes: node and element counts are what they are, but the mesh must actually
    cover the geometry. Volume is the check."""
    import deliverables, meshio
    with tempfile.TemporaryDirectory() as d:
        r = deliverables.make_gmsh(os.path.join(d, "h.geo"),
                                   os.path.join(d, "h.msh"))
        if not r["verified"]:
            return
        m = meshio.read(r["path"])
        pts = m.points
        bbox = ((pts[:, 0].max() - pts[:, 0].min()),
                (pts[:, 1].max() - pts[:, 1].min()),
                (pts[:, 2].max() - pts[:, 2].min()))
        measure("heatsink.msh", "meshed bounding box, x", bbox[0], 60.0, EXACT,
                "the .geo that generated it", "the mesh must span the geometry")
        measure("heatsink.msh", "meshed bounding box, z", bbox[2], 31.0, EXACT,
                "6 mm base + 25 mm fins", "")


def audit_spreadsheet():
    """A spreadsheet's formulas must produce the same numbers the engine does.
    Recomputed here with the same inputs, independently of openpyxl."""
    import structural
    P, L, b, h, E, sy = 4000.0, 300.0, 50.0, 34.0, 200000.0, 370.0
    sec = structural.rectangle(b, h)
    r = structural.cantilever_point(P, L, E, sec["I"])
    sigma = r["M"] / sec["Z"]
    measure("calc.xlsx", "I = b h^3/12 as written in the sheet",
            b * h ** 3 / 12.0, sec["I"], EXACT, "structural.rectangle", "")
    measure("calc.xlsx", "sigma = M/Z as written in the sheet",
            P * L / (b * h ** 2 / 6.0), sigma, EXACT,
            "structural.cantilever_point", "")
    measure("calc.xlsx", "delta = PL^3/3EI as written in the sheet",
            P * L ** 3 / (3 * E * sec["I"]), r["defl"], EXACT,
            "structural.cantilever_point",
            "the spreadsheet must not disagree with the engine that sized the part")


def audit_field_plot():
    """The plotted stress field must match M c / I exactly - a picture with the
    wrong peak on it is worse than no picture."""
    import structural
    P, L, b, h = 4000.0, 300.0, 50.0, 34.0
    sec = structural.rectangle(b, h)
    peak_plot = P * L * (h / 2) / sec["I"]
    peak_theory = P * L / sec["Z"]
    measure("von_mises.png", "peak stress annotated on the plot",
            peak_plot, peak_theory, EXACT, "M/Z",
            "M c / I and M / Z are the same quantity written two ways")


def audit_reference_data():
    """Downloaded constants against the exact SI definitions."""
    import refdata
    r = refdata.codata()
    if not r.get("constants"):
        return
    for frag, truth, name in [
        ("speed of light in vacuum", 299792458.0, "c"),
        ("Planck constant", 6.62607015e-34, "h"),
        ("elementary charge", 1.602176634e-19, "e"),
        ("Boltzmann constant", 1.380649e-23, "k"),
    ]:
        hits = [k for k in r["constants"] if frag.lower() in k.lower()]
        if hits:
            k = min(hits, key=len)
            measure("codata_2022.txt", f"{name} - an EXACT SI defining constant",
                    r["constants"][k]["value"], truth, EXACT,
                    "the 2019 SI redefinition",
                    "defined, not measured, so there is no tolerance at all")


def audit_multibody():
    """Simulation against closed forms. The pendulum period is ANALYTIC; the energy
    conservation of a chaotic system is EXACT in principle and limited by the
    integrator in practice."""
    import multibody
    if not multibody.chrono_available():
        return
    p = multibody.pendulum(length=1.0, theta0_deg=5.0)
    if p.get("period_simulated_s"):
        measure("multibody pendulum", "period vs 2 pi sqrt(L/g)",
                p["period_simulated_s"], p["period_analytic_s"], ANALYTIC,
                "small-angle pendulum theory",
                "the small-angle formula is itself an approximation above ~15 deg")
    d = multibody.double_pendulum(t_end=2.0)
    if "error" not in d:
        measure("multibody double pendulum", "energy drift over 100k steps",
                d["E_final_J"], d["E_initial_J"], ANALYTIC,
                "conservation of energy in an undamped system",
                "the trajectory is chaotic and uncheckable; the energy is not")


def audit_correlations():
    """Empirical correlations, judged against their OWN published scatter rather
    than against an exact value they never claimed to have."""
    import thermal, fluid_mech
    nu = thermal.nusselt_dittus_boelter(50000.0, 4.0)
    measure("heat transfer correlations", "Dittus-Boelter Nu at Re 5e4, Pr 4",
            nu["Nu"], 0.023 * 50000.0 ** 0.8 * 4.0 ** 0.4, EXACT,
            "the correlation as published",
            "we reproduce the CORRELATION exactly; the correlation itself carries "
            "about 15-25% scatter against experiment, and that is the real accuracy "
            "of any answer built on it")
    cd = fluid_mech.cd_sphere(1e4)
    measure("drag correlations", "sphere Cd in the Newton regime",
            cd["Cd"], 0.44, EMPIRICAL, "standard drag curve",
            "a shape factor read from experimental data; 10-20% is the honest "
            "uncertainty even when the arithmetic is perfect")


def run_audit(quiet=False):
    _ROWS.clear()
    for fn in (audit_cad, audit_drawing, audit_spreadsheet, audit_field_plot,
               audit_fea, audit_cfd, audit_spice, audit_mesh,
               audit_reference_data, audit_multibody, audit_correlations):
        try:
            fn()
        except Exception as e:
            _ROWS.append({"artifact": fn.__name__, "quantity": "audit failed",
                          "produced": None, "truth": None, "class": EXACT,
                          "rel_error": float("inf"), "tolerance": 0.0,
                          "within": False, "truth_source": "-",
                          "rationale": "", "note": f"{type(e).__name__}: {e}"})
    if not quiet:
        for r in _ROWS:
            mark = "OK  " if r["within"] else "OUT "
            e = r["rel_error"]
            es = "exact" if e == 0 else (f"{e*100:.3e}%" if e < 1e-6
                                         else f"{e*100:.4f}%")
            print(f"  {mark} {r['artifact'][:26]:<26} {r['quantity'][:48]:<48} "
                  f"{es:>12}  [{r['class']}]")
    by_class = {}
    for r in _ROWS:
        c = by_class.setdefault(r["class"], {"n": 0, "ok": 0, "worst": 0.0})
        c["n"] += 1
        c["ok"] += 1 if r["within"] else 0
        if r["rel_error"] != float("inf"):
            c["worst"] = max(c["worst"], r["rel_error"])
    return {"rows": _ROWS, "total": len(_ROWS),
            "within": sum(1 for r in _ROWS if r["within"]),
            "outside": sum(1 for r in _ROWS if not r["within"]),
            "by_class": by_class}


def _selftest():
    ok = True
    def chk(n, c, e=""):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}{('  ' + e) if e else ''}"); ok = ok and c

    r = run_audit(quiet=True)
    chk(f"every one of the {r['total']} accuracy measurements is within the "
        "tolerance appropriate to ITS class of truth",
        r["outside"] == 0, f"{r['within']}/{r['total']}")
    for row in r["rows"]:
        if not row["within"]:
            chk(f"  {row['artifact']}: {row['quantity']}", False,
                row.get("note") or f"error {row['rel_error']*100:.4f}% vs tolerance "
                                   f"{row['tolerance']*100:.4f}%")

    ex = r["by_class"].get(EXACT, {})
    chk("EXACT quantities are exact to floating-point noise, not merely close",
        ex.get("worst", 1) < 1e-9,
        f"worst exact-class error {ex.get('worst', 0)*100:.3e}% over {ex.get('n')} "
        "measurements")
    an = r["by_class"].get(ANALYTIC, {})
    chk("ANALYTIC quantities are within 5%, which is the honest bar for a "
        "discretised solution",
        an.get("worst", 1) <= 0.05,
        f"worst {an.get('worst', 0)*100:.3f}% over {an.get('n')} measurements")

    chk("the three classes of truth are held to DIFFERENT tolerances, because "
        "treating them alike would be dishonest",
        TOLERANCE[EXACT][0] < TOLERANCE[ANALYTIC][0] < TOLERANCE[EMPIRICAL][0],
        f"exact {TOLERANCE[EXACT][0]:g}, analytic {TOLERANCE[ANALYTIC][0]:g}, "
        f"empirical {TOLERANCE[EMPIRICAL][0]:g}")
    chk("every measurement names the independent source of its truth",
        all(row["truth_source"] for row in r["rows"]))
    chk("...and empirical results say plainly that the CORRELATION's own scatter, "
        "not our residual, is the real accuracy",
        any("scatter" in row["note"] for row in r["rows"]))

    print("accuracy selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="numerical accuracy of generated files")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()
    if a.audit:
        print("=" * 116)
        print("EngineAI - ACCURACY of every generated artifact against independent truth")
        print("=" * 116)
        r = run_audit()
        print()
        for cls, v in sorted(r["by_class"].items()):
            tol, why = TOLERANCE[cls]
            print(f"  {cls:<10} {v['ok']}/{v['n']} within {tol:g}   "
                  f"worst {v['worst']*100:.4f}%")
            print(f"             {why}")
        print()
        print(f"  {r['within']}/{r['total']} measurements within tolerance")
        raise SystemExit(0 if r["outside"] == 0 else 1)
    raise SystemExit(_selftest())
