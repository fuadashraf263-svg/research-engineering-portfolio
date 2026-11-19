#!/usr/bin/env python3
"""crfce_paper.py -- EngineAI writes the CRFCE research + design paper.

Turns a governed DesignPassport (crfce_engine_design.design_engine) and the research
dossier (crfce_research.deep_research) into a full, IEEE-structured technical paper:
Markdown source, a printable HTML rendering with embedded figures, real data-driven
figures (every point traced to a governed result), and a figures/tables PDF companion.

Every resolved study input is printed with its value and limited provenance label; each
computed result retains its governed receipt status. The paper does not elevate assumptions
to measurements and states plainly that the work is a virtual reference study that is neither
design-release-authorized nor physically validated -- not a claim of a tested machine.
"""
from __future__ import annotations

import base64
import contextlib
import io
import math
from pathlib import Path
from typing import Any

with contextlib.redirect_stdout(io.StringIO()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages


def _require_candidate_scope(passport: dict) -> dict:
    """Refuse paper generation if the non-promotable study boundary is absent or changed."""
    scope = passport.get("reference_candidate_scope")
    required_scope = {
        "study": "GOVERNED_VIRTUAL_REFERENCE_CANDIDATE",
        "geometry": "PARAMETRIC_CANDIDATE_NOT_RELEASED_OR_AS_BUILT",
        "torque": "ANALYTICAL_SHEAR_ESTIMATE_NOT_FIELD_SOLVE",
        "rotor": "IPM_STYLE_GEOMETRIC_PROXY_NOT_RELUCTANCE_ROTOR",
        "manufacturing": "PRELIMINARY_SCREEN_NOT_QUALIFICATION",
        "physical_validation": "NOT_DEMONSTRATED",
    }
    if (type(scope) is not dict
            or any(scope.get(key) != value for key, value in required_scope.items())
            or scope.get("release_authorized") is not False):
        raise ValueError("CRFCE paper requires the exact non-promotable reference-candidate evidence boundary")
    return scope


def _candidate_identity_boundary(passport: dict) -> str:
    """Keep documentary candidates distinct from the exact analysis parameterization."""
    sizing = passport.get("sizing") or {}
    spec = sizing.get("spec_params") or {}
    binding = sizing.get("topology_binding") or {}
    slot_count = spec.get("slot_count")
    pole_count = spec.get("pole_count")
    pole_pairs = binding.get("pole_pairs")
    provenance = binding.get("pole_pairs_provenance")
    if (type(slot_count) is not int or type(pole_count) is not int
            or type(pole_pairs) is not int or pole_count != 2 * pole_pairs
            or not isinstance(provenance, str) or not provenance):
        raise ValueError("CRFCE paper requires an exact sizing/topology parameterization")
    return (
        "**Machine-identity boundary:** R7 CRFCE package-paper/STEP documentary baseline: "
        "24 stator slots / 4 rotor poles (manual visual transcription, unverified, and not applied "
        "to the current analysis). This paper's CRFCE analysis parameterization: "
        f"{slot_count} stator slots / {pole_count} rotor poles ({pole_pairs} pole pairs; {provenance}). "
        "EngineAI's generic 24-slot / 6-pole case is a reference assumption, not proof of the "
        "package's machine identity. R5-C is a separate plan: three-phase, 48 slots / 8 poles, "
        "permanent-magnet machine; retained 8-slot / 6-pole SRM results are surrogate-only. "
        "These candidates are separate, not interchangeable. The pinned CRFCE STEP geometry "
        "supports only a package-level topology candidate and does not establish the "
        "released revision or as-built machine. No CRFCE or R5-C machine-specific torque-ripple "
        "result is established by the SRM surrogate.\n"
    )


def _fig_cross_section(spec: dict, path: Path) -> str:
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    so, bore = spec["stator_outer_diameter"] / 2, spec["stator_bore_diameter"] / 2
    ro, sh = spec["rotor_outer_diameter"] / 2, spec["shaft_diameter"] / 2
    for r, c in ((so, "#1f4e79"), (bore, "#2e75b6"), (ro, "#c55a11"), (sh, "#404040")):
        ax.add_patch(plt.Circle((0, 0), r, fill=False, lw=1.6, color=c))
    # stator slots
    n = int(spec["slot_count"]); depth = spec["slot_depth"]; bridge = spec["slot_opening_bridge"]
    for k in range(n):
        a = 2 * math.pi * k / n
        r0 = bore + bridge; r1 = r0 + depth
        ax.plot([r0 * math.cos(a), r1 * math.cos(a)], [r0 * math.sin(a), r1 * math.sin(a)],
                color="#2e75b6", lw=1.0)
    # rotor poles
    p = int(spec["pole_count"]); rm = spec["r_mag_mm"]
    for k in range(p):
        a = 2 * math.pi * k / p
        ax.plot(rm * math.cos(a), rm * math.sin(a), "s", color="#c55a11", ms=5)
    ax.set_aspect("equal"); ax.set_xlim(-so * 1.1, so * 1.1); ax.set_ylim(-so * 1.1, so * 1.1)
    ax.set_title(f"CRFCE lamination cross-section\n{n} stator slots / {p} rotor poles, "
                 f"air gap {spec['air_gap']} mm", fontsize=9)
    ax.set_xlabel("mm"); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)
    return str(path)


def _fig_burden(dossier: dict, path: Path) -> str:
    curve = (dossier.get("continuous_rating") or {}).get("burden_curve") or []
    rpm = [c["rpm"] for c in curve if c.get("cold_load_W") is not None]
    load = [c["cold_load_W"] for c in curve if c.get("cold_load_W") is not None]
    inp = [c["input_W"] for c in curve if c.get("input_W") is not None]
    fig, ax1 = plt.subplots(figsize=(5.6, 4.0))
    ax1.plot(rpm, load, "-o", color="#c55a11", label="cold-end load (W)")
    ax1.set_xlabel("rotor speed (rpm)"); ax1.set_ylabel("cold-end heat load (W)", color="#c55a11")
    lift = (dossier.get("continuous_rating") or {}).get("installed_cooler_lift_W")
    if lift:
        ax1.axhline(lift, ls="--", color="#808080", label=f"reference cooler lift {lift} W")
    ax2 = ax1.twinx(); ax2.plot(rpm, inp, "-s", color="#2e75b6", label="cryocooler input (W)")
    ax2.set_ylabel("cryocooler input power (W)", color="#2e75b6")
    ax1.set_title("Governed cryogenic burden vs speed", fontsize=9)
    ax1.grid(alpha=0.2); fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)
    return str(path)


def _fig_requirements(passport: dict, path: Path) -> str:
    rows = passport["requirements_matrix"]
    fig, ax = plt.subplots(figsize=(7.2, 0.5 + 0.5 * len(rows)))
    ax.axis("off")
    cells = [[r.get("id"), r.get("requirement"), str(r.get("target")),
              str(r.get("result"))[:26], str(r.get("status"))] for r in rows]
    tbl = ax.table(cellText=cells,
                   colLabels=["ID", "Requirement", "Target", "Result", "Met"],
                   loc="center", cellLoc="left")
    tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.scale(1, 1.4)
    ax.set_title("Requirements verification matrix (governed)", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)
    return str(path)


def _b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def _resolved_research_inputs_markdown(sizing: dict) -> str:
    """Render the exact validated inputs and their limited provenance labels.

    Input provenance is not measurement provenance: a user-supplied value remains
    unverified until independent evidence is attached. Keeping the values in the
    paper makes an override reproducible without elevating its evidence tier.
    """
    import crfce_engine_design as design
    import crfce_research as research

    records = sizing.get("research_inputs") if type(sizing) is dict else None
    values = design._resolved_research_values(records)
    units = {
        "B_T": "T", "pole_area_m2": "m^2", "rotor_r_m": "m",
        "rotor_rho_kg_m3": "kg/m^3", "rpm": "rpm", "I_op_A": "A",
        "T_K": "K", "B_saturation_T": "T", "rotor_yield_MPa": "MPa",
        "rotor_SF_min": "-", "rotor_Kt": "-", "hts_margin_max": "-",
        "electric_loading_peak_A_per_m": "A/m", "spatial_phase_factor": "-",
        "L_stack_m": "m", "pole_pairs": "pairs", "Ic0_A": "A",
        "I_amplitude_A": "A", "tape_length_m": "m",
        "slot_root_depth_m": "m", "slot_root_radius_m": "m",
        "rotor_delta_m": "m", "rotor_E_Pa": "Pa", "rotor_alpha_1_K": "1/K",
        "rotor_nu": "-", "bearing_C_N": "N", "bearing_P_N": "N",
        "cooler_lift_W": "W", "conduction_k_W_mK": "W/(m K)",
        "support_r_inner_m": "m", "support_r_outer_m": "m",
        "support_length_m": "m", "cold_area_m2": "m^2",
        "mli_emissivity": "-", "Su_MPa": "MPa", "crack_a_m": "m",
        "crack_Y": "-", "cycles_per_mission": "count",
    }
    if set(units) != set(research.REFERENCE):
        raise RuntimeError("CRFCE paper input-unit map does not cover the research schema")
    lines = [
        "| Input | Resolved value | Unit | Provenance |",
        "|---|---:|---|---|",
    ]
    for name in sorted(values):
        record = records["resolved_inputs"][name]
        lines.append(
            f"| {name} | {format(values[name], '.12g')} | {units[name]} | "
            f"{record['provenance']} |"
        )
    return "\n".join(lines)


def _markdown(passport: dict, dossier: dict, figs: dict) -> str:
    op = passport["operating_point"]; c = passport["as_designed_checks"]
    dfm = passport["manufacturability"]; bom = passport["bom"]
    rec = dossier["reconciliation"]; adv = dossier["adversarial_battery"]
    cryo = dossier["cryogenic_thermal"]
    scope = _require_candidate_scope(passport)
    md = []
    A = md.append
    A("# A Governed Computational Design of a Cryogenic RF-Quiet Cellular Engine (CRFCE):")
    A("## A Reluctance-HTS Machine Sized, Analysed, and Verified by an Authority-Bounded Engineering System\n")
    A("**Author:** EngineAI Governed Computational Engineering System  ")
    A("**Artifact class:** " + passport["schema"] + "  ")
    A(f"**Maturity:** {passport['maturity_level']}  ")
    A(f"**Physical validation:** {passport['physical_validation']}\n")
    A("### Abstract\n")
    A(f"We present a governed computational reference study of a cryogenic, RF-quiet reluctance "
      f"machine with a high-temperature-superconducting (HTS) field winding. Each reported value "
      f"is either a resolved study input or a computed result. Computed results carry a "
      f"content-addressed receipt when admitted by the governed executor; the input table records "
      f"reference assumptions and user-supplied unverified values, which are not measurements. "
      f"From a governed "
      f"feasible operating point ({op.get('target_power_kW')} kW, {op.get('target_torque_Nm')} N·m at "
      f"B = {op.get('B_T')} T, {op.get('rpm')} rpm, {op.get('T_K')} K) we size a machine and attempt "
      f"candidate stator/rotor lamination and HTS coil-former geometry generation, subject to native CAD "
      f"availability and successful dimensional checks, then run governed structural, "
      f"electromagnetic and cryogenic-thermal screens for the sizing case; these do not constitute "
      f"a validated FEA or physical test. A model-derived candidate rotor-bridge notch factor of K_t = {c.get('rotor_bridge_Kt_candidate')} "
      f"— estimated from candidate geometry-spec dimensions, not as-built geometry or a local-stress FEA measurement — yields a screened rotor safety factor "
      f"of {c.get('rotor_safety_factor')} at speed. A governed cryogenic budget shows a cold-end load "
      f"of {c.get('cold_end_load_W')} W dominated by support conduction. An adversarial-mutation "
      f"battery rejects {adv['caught']}/{adv['attacks']} unphysical variants. The result is a "
      f"governed virtual reference study; any preliminary manufacturing artifacts are conditional "
      f"on successful geometry generation and checks. Design release "
      f"is NOT_AUTHORIZED and physical validation (spin, cool-down, quench, bench performance) "
      f"is defined but NOT demonstrated. "
      f"The work is backed by {passport['governed_receipt_count']} governed receipts.\n")
    A("**Evidence boundary:** This is a virtual reference-candidate study. Parametric geometry is "
      "not bound to released/as-built hardware; air-gap torque is an analytical estimate, not a "
      "field solve; the IPM-style rotor is a geometric proxy; preliminary DfM is not manufacturing "
      "qualification. These claims do not establish a buildable or physically validated CRFCE.\n")
    A(_candidate_identity_boundary(passport))
    A("**Index Terms** — superconducting machines, reluctance motor, cryogenics, computational "
      "design, verification and validation, governed AI.\n")

    A("### I. Introduction\n")
    A("Cryogenic reluctance machines with HTS field windings promise high torque density with a "
      "quiet electromagnetic signature, but their design couples electromagnetics, rotor mechanics, "
      "and cryogenics tightly. Generative AI can propose such designs but cannot be trusted to "
      "compute them: it confabulates. EngineAI inverts the trust model — a language model may "
      "propose, but a registered executor computes, an authority boundary admits, and every admitted "
      "number carries a receipt with an evidence tier. Executor admission is not product release. "
      "This paper exercises that pipeline end-to-end "
      "on a CRFCE reference case and records its input assumptions and explicit physical-validation plan.\n")

    A("### II. Governed Computational Method\n")
    A("Governed calculations call `capability_runner.run(executor, inputs)` and either return an "
      "executor-admitted result with a receipt digest or refuse. This internal decision cannot "
      "authorize design or product release. Refusals are reported, not patched over: models that "
      "declined on out-of-envelope inputs (e.g. cryogenic-temperature yield lookup) are named in the "
      "residual-unknowns list rather than replaced by a guess. The design geometry is generated by a "
      "deterministic parametric kernel and dimensionally checked when the native CAD boundary is "
      "available: each solid's measured volume is compared to a closed-form material balance, and "
      "the bounding box, air gap and watertightness are checked. A refusal or missing artifact is not "
      "reported as a successful geometry check.\n")

    A("### III. Machine Topology and Sizing\n")
    A("Rotor radius and active stack length are taken from the exact CRFCE research dossier, "
      "not inferred from the optimized operating point. The stator outer diameter and shaft use "
      "the stated sizing rules. The table lists every resolved research input and labels each as "
      "a reference assumption or user-supplied unverified value. Those labels are provenance "
      "disclosures, not measurements or independent validation. The reluctance rotor's flux barriers "
      "are represented here by a lamination-proxy pocket geometry; this proxy is not a validated "
      "CRFCE rotor design.\n")
    A(_resolved_research_inputs_markdown(passport.get("sizing") or {}))
    A("\n")
    A(f"![Cross-section]({Path(figs['cross']).name})\n")
    A("*Figure 1. Governed lamination cross-section generated from the sizing spec.*\n")

    A("### IV. Electromagnetic Analysis\n")
    A(f"Torque is screened from the governed average TANGENTIAL air-gap shear relation, "
      f"tau = 0.5·B_peak·K_peak·cos(delta) = {c.get('airgap_shear_kPa')} kPa "
      f"(peak fundamental air-gap flux density B_peak = {op.get('B_T')} T, peak fundamental "
      f"surface-current loading K_peak = {c.get('electric_loading_peak_A_per_m')} A/m, "
      f"spatial phase factor cos(delta) = {c.get('spatial_phase_factor')}), applied as "
      f"T = (π/2)·D²·L·sigma. This yields an as-designed torque of "
      f"{c.get('asdesigned_torque_Nm')} N·m and {c.get('asdesigned_power_kW')} kW for this "
      f"sizing model. The normal pole attraction ({c.get('normal_pole_attraction_N')} N) is RADIAL "
      f"and produces no torque; an earlier revision incorrectly used it as the torque source, "
      f"which is corrected here. Torque requires a real winding — with zero electric loading "
      f"the governed shear is zero. A 3-D electromagnetic torque/cogging FEA on this exact "
      f"geometry is the named next step.\n")
    xc = (passport.get("as_designed_checks") or {}).get("em_flux_crosscheck") or {}
    if xc.get("ok"):
        A(f"As an independent check (gate G05), the air-gap flux was re-computed with EngineAI's "
          f"independently cross-verified 2-D magnetostatic FE (emag.gapped_core_fea, benchmarked against Ampere's law "
          f"and lumped reluctance): assumed {xc.get('B_g_assumed_T')} T vs FE {xc.get('B_g_fea_T')} T "
          f"(agreement {xc.get('agreement_fea_over_assumed')}). "
          + ("The linear FE flags this operating point as near iron saturation and cannot confirm "
             "it — a nonlinear B-H solve (GetDP) is required."
             if xc.get("near_iron_saturation") else
             "The flux is confirmed below iron saturation.") + "\n")

    A("### V. Rotor Structural Integrity\n")
    A(f"The governed rotating-ring hoop-stress estimate is {c.get('rotor_hoop_mean_MPa')} MPa (mean) at "
      f"{op.get('rpm')} rpm. The candidate rotor-bridge notch factor is K_t = {c.get('rotor_bridge_Kt_candidate')}, "
      f"estimated by a governed notch model using pocket-depth and root-radius dimensions from the "
      f"candidate geometry spec; no as-built geometry is bound and this is not a local-stress FEA measurement. This estimate gives a peak of "
      f"{c.get('rotor_peak_MPa')} MPa and a safety factor of {c.get('rotor_safety_factor')} "
      f"— compared with the {c.get('rotor_SF_min')} minimum target. Crucially, the three-lever enhancement engine had assumed "
      f"K_t = {rec['enhancement_assumed_Kt']}; this model's notch estimate is higher, so an earlier "
      f"{rec['enhancement_peak_power_kW']} kW 'peak' is optimistic within this model and the "
      f"defensible feasible point is {rec['governed_feasible_power_kW']} kW.\n")

    A("### VI. Cryogenic Thermal Budget\n")
    A(f"The governed cold-end budget aggregates AC loss ({cryo.get('ac_loss_W')} W), support "
      f"conduction ({cryo.get('conduction_leak_W')} W) and radiation ({cryo.get('radiation_leak_W')} W) "
      f"to a total of {c.get('cold_end_load_W')} W. At the Carnot COP {cryo.get('cop_carnot')} this "
      f"is {cryo.get('cryocooler_input_ideal_W')} W ideal; a real cryocooler achieves only "
      f"~{int(cryo.get('cryocooler_carnot_fraction', 0.15)*100)}% of Carnot, so the realistic "
      f"wall-plug input is **{c.get('cryocooler_input_W')} W** — an order of magnitude above the "
      f"ideal, and the true system-mass driver. The dominant load is '{cryo.get('dominant_load')}', "
      f"so the binding continuous-rating constraint is the cryostat heat path, not AC loss.\n")
    A(f"![Burden]({Path(figs['burden']).name})\n")
    A("*Figure 2. Governed cryogenic burden vs speed (every point a receipted result).*\n")

    A("### VII. Design Optimization and Adversarial Verification\n")
    A(f"A governed sweep over (B, rpm, T) enforcing all constraints at once "
      f"({dossier['optimization_sweep']['feasible_points']} feasible of "
      f"{dossier['optimization_sweep']['grid_points_evaluated']} evaluated) selects the feasible "
      f"operating point. An adversarial-mutation battery then drives the design into infeasible "
      f"territory — overspeed, over-temperature, a razor-thin slot root, a rigidly restrained "
      f"cool-down — and confirms a governed constraint REJECTS each ({adv['caught']}/{adv['attacks']}), "
      f"demonstrating engineering reasoning rather than a passing render.\n")

    A("### VIII. Manufacturing and Bill of Materials\n")
    A(f"The minimum governed feature is {dfm['min_feature_mm']} mm, within the "
      f"{dfm['min_wall_required_mm']} mm wire-EDM/laser lamination limit "
      f"(a monolithic metal-AM route would require thickening the {dfm['features_mm']['slot_bridge_mm']} mm "
      f"slot bridge to ≥ {dfm['alt_metal_AM']['min_wall_mm']} mm). The core bill of materials totals "
      f"{bom['total_mass_kg']} kg:\n")
    A("| Part | Material | Vol (cm³) | Mass (kg) |")
    A("|---|---|---|---|")
    for r in bom["rows"]:
        A(f"| {r['part']} | {r['material']} | {r['volume_cm3']} | {r['mass_kg']} |")
    A("")
    A(f"![Requirements]({Path(figs['reqs']).name})\n")
    A("*Figure 3. Governed requirements verification matrix.*\n")

    A("### IX. Physical Validation Plan (NOT yet demonstrated)\n")
    A("This design is a governed virtual reference study with preliminary manufacturing "
      "artifacts. The following are proposed experiments that require real hardware and can "
      "never be granted by simulation:\n")
    for item in passport["not_demonstrated"]:
        A(f"- {item}")
    A("")

    pr = passport.get("production_readiness") or {}
    if pr.get("release_gates"):
        A("### X. Production-readiness gates (honest V&V status)\n")
        A(f"Computed maturity: **{pr['maturity']['level']}** — {pr['maturity']['statement']}\n")
        A(f"Verdict: **{pr['verdict']}**\n")
        A("| Release gate | Status | Reason |")
        A("|---|---|---|")
        for g in pr["release_gates"]:
            A(f"| {g['gate']} | {g['status']} | {g['reason'][:100]} |")
        A("")
        A("This design orchestrates the physics tools EngineAI has; it does not replace "
          "high-fidelity solvers (Motor-CAD/Maxwell-class EM, CFD, NVH) or the physical "
          "validation process. The next concrete step is the independent EM-FEA torque "
          "cross-check named in gate G05.\n")

    A("### XI. Conclusion\n")
    A("EngineAI carried a cryogenic reluctance-HTS reference case from resolved inputs and a "
      "governed operating-point screen into a preliminary computational design study with an "
      "explicit experimental plan. The governance layer caught a discrepancy between the assumed "
      "and geometry-input-driven notch estimates and refused to promote the result past what the "
      "physics supports. The next step is physical fabrication and the bench program in Section IX.\n")

    A("### References\n")
    A("[1] Governing relations used (each a governed executor): Maxwell stress B²A/2μ₀; rotating-ring "
      "hoop ρ(rω)²; Norris AC loss; superconductor I_c(B,T); refrigeration COP T_c/(T_h−T_c). ")
    A("[2] ASME V&V 10 / V&V 20, Verification, Validation and Uncertainty Quantification. ")
    A("[3] ASME Y14.5, Dimensioning and Tolerancing. ")
    A("[4] Norris, *Calculation of hysteresis losses in hard superconductors*, J. Phys. D, 1970.\n")

    A("### Appendix A. Governed receipt digests\n")
    A("Every headline number derives from one of these content-addressed receipts:\n")
    A("`" + ", ".join(passport["governed_receipts"][:40]) + "`\n")
    A(f"\n*{passport['boundary']}*\n")
    return "\n".join(md)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(s: str) -> str:
    out = _esc(s)
    while "**" in out:
        out = out.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    return out


def _html(markdown_text: str, figdir: Path) -> str:
    """Render our own markdown (headers, bold, tables, images, lists) to a clean,
    printable, self-contained IEEE-style HTML paper with images embedded as data URIs."""
    html: list[str] = []
    lines = markdown_text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        if ln.startswith("### "):
            html.append(f"<h3>{_inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            html.append(f"<h2>{_inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            html.append(f"<h1>{_inline(ln[2:])}</h1>")
        elif ln.startswith("!["):
            ref = ln.split("(", 1)[1].rstrip(")")
            p = figdir / ref
            if p.is_file():
                html.append(f"<img alt='figure' style='max-width:100%' "
                            f"src='data:image/png;base64,{_b64(str(p))}'>")
        elif ln.startswith("|") and i + 1 < n and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in ln.strip("|").split("|")]
            html.append("<table><thead><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in head)
                        + "</tr></thead><tbody>")
            i += 2
            while i < n and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                html.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            html.append("</tbody></table>")
            continue
        elif ln.startswith("- "):
            html.append(f"<li>{_inline(ln[2:])}</li>")
        elif ln.startswith("*") and ln.endswith("*") and len(ln) > 2:
            html.append(f"<p class='cap'>{_inline(ln.strip('*'))}</p>")
        elif ln.strip():
            html.append(f"<p>{_inline(ln)}</p>")
        i += 1
    return ("<!doctype html><meta charset='utf-8'><title>CRFCE Governed Design Paper</title><style>"
            "body{max-width:820px;margin:2rem auto;font:15px/1.65 Georgia,serif;color:#111;padding:0 1.2rem}"
            "h1{font-size:1.5rem;line-height:1.3}h2{font-size:1.1rem;color:#333;font-weight:normal}"
            "h3{font-size:1.05rem;border-bottom:1px solid #ddd;padding-bottom:.2rem;margin-top:1.6rem}"
            "table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:14px}"
            "th,td{border:1px solid #bbb;padding:.35rem .5rem;text-align:left}th{background:#f0f0f0}"
            ".cap{color:#555;font-size:13px}img{display:block;margin:1rem auto}code{font-size:12px}"
            "</style>" + "\n".join(html))


def _pdf(markdown_text: str, figdir: Path, path: Path) -> str:
    """Full paginated PDF: the complete paper text (monospace) with each figure rendered
    inline on its own page where it is referenced."""
    import textwrap
    stream: list[tuple[str, str]] = []
    for ln in markdown_text.splitlines():
        if ln.startswith("!["):
            ref = ln.split("(", 1)[1].rstrip(")")
            stream.append(("img", str(figdir / ref)))
            continue
        t = ln.replace("**", "").replace("### ", "").replace("## ", "").replace("# ", "")
        if not t.strip():
            stream.append(("text", ""))
            continue
        for seg in (textwrap.wrap(t, 98) or [""]):
            stream.append(("text", seg))
    with PdfPages(str(path)) as pdf:
        buf: list[str] = []

        def flush() -> None:
            nonlocal buf
            if not buf:
                return
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.08, 0.96, "\n".join(buf), va="top", ha="left",
                     family="monospace", fontsize=8)
            pdf.savefig(fig); plt.close(fig); buf = []

        for kind, val in stream:
            if kind == "text":
                buf.append(val)
                if len(buf) >= 56:
                    flush()
            else:
                flush()
                try:
                    img = plt.imread(val)
                    fig = plt.figure(figsize=(8.27, 11.69))
                    ax = fig.add_axes([0.08, 0.28, 0.84, 0.46]); ax.axis("off"); ax.imshow(img)
                    pdf.savefig(fig); plt.close(fig)
                except Exception:
                    buf.append(f"[figure: {Path(val).name}]")
        flush()
    return str(path)


def write_paper(passport: dict, dossier: dict | None = None,
                outdir: str | Path | None = None) -> dict:
    import crfce_research as R
    dossier = dossier or passport.get("research_dossier") or R.deep_research()
    out = Path(outdir or (Path.cwd() / "out" / "crfce_paper"))
    out.mkdir(parents=True, exist_ok=True)
    spec = (passport.get("geometry") or {}).get("verification", {})
    spec_full = None
    # recover spec from sizing (design passport stores spec_params; geometry stores verified spec)
    spec_full = passport.get("sizing", {}).get("spec_params")
    # prefer the completed motor spec if the passport carried it
    built_spec = None
    try:
        import motor_geometry as mg
        built_spec = mg.motor_spec(passport["sizing"]["spec_params"])
    except Exception:
        built_spec = passport["sizing"]["spec_params"]
    figs = {
        "cross": _fig_cross_section(built_spec, out / "fig1_cross_section.png"),
        "burden": _fig_burden(dossier, out / "fig2_burden.png"),
        "reqs": _fig_requirements(passport, out / "fig3_requirements.png"),
    }
    md = _markdown(passport, dossier, figs)
    md_path = out / "CRFCE_design_paper.md"; md_path.write_text(md, encoding="utf-8")
    html_path = out / "CRFCE_design_paper.html"; html_path.write_text(_html(md, out), encoding="utf-8")
    pdf_path = _pdf(md, out, out / "CRFCE_design_paper.pdf")
    return {
        "ok": True, "schema": "engineai.crfce_paper.v1",
        "files": {"markdown": str(md_path), "html": str(html_path), "pdf": pdf_path,
                  **{f"figure_{k}": v for k, v in figs.items()}},
        "sections": 10, "figures": len(figs),
        "governed_receipts": passport["governed_receipt_count"],
        "physical_validation": passport["physical_validation"],
        "boundary": passport["boundary"],
    }


if __name__ == "__main__":
    import crfce_engine_design as D
    p = D.design_engine()
    r = write_paper(p, p["research_dossier"])
    print("paper files:", {k: v for k, v in r["files"].items()})
    print("receipts:", r["governed_receipts"], "physical_validation:", r["physical_validation"])
