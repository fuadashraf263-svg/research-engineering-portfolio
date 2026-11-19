#!/usr/bin/env python3
"""Shared-configuration CRFCE coupled virtual V&V.

This module closes a specific honesty gap in the CRFCE research stack: the existing
domain analyses are useful, but a reviewer also needs proof that they consumed the
same design revision, that cross-domain dependencies were propagated, that numerical
methods were checked independently, and that uncertainty was supplied rather than
invented.

The result remains a *virtual* verification record.  The real finite-volume and Elmer
checks below qualify methods and a representative magnetic circuit; they are not a
nonlinear 3-D solve of the exact motor.  RF quietness, control stability, quench
protection, hardware correlation and release authority remain withheld until their
required models or measurements exist.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
from typing import Any

import numpy as np

import crfce_research as R


SCHEMA = "engineai.crfce-coupled-vv.v1"
CONFIG_SCHEMA = "engineai.crfce-shared-configuration.v1"
BOUNDARY = (
    "Virtual verification only. Solver convergence and uncertainty propagation do "
    "not demonstrate physical performance, RF quietness, safety, certification, or "
    "release readiness. Calibrated hardware measurements and independent human "
    "approval remain required."
)
SUPPORTED_UQ_INPUTS = {
    "B_T", "rpm", "T_K", "electric_loading_peak_A_per_m",
    "spatial_phase_factor", "slot_root_radius_m", "rotor_yield_MPa",
    "conduction_k_W_mK", "mli_emissivity", "cooler_lift_W",
}
SENSITIVITY_INPUTS = tuple(sorted(SUPPORTED_UQ_INPUTS))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False,
                      default=_json_default).encode("utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seal_configuration(design: dict[str, Any] | None = None,
                       input_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create one immutable configuration record for every downstream domain.

    ``input_evidence`` does not make a value true.  It only links the value to a
    reviewable source.  The caller may link reference defaults as well as overrides;
    every unlinked default remains a REFERENCE_ASSUMPTION and every unlinked override
    remains USER_SUPPLIED_UNVERIFIED.
    """
    overrides = R.validate_design_overrides(design)
    values = {**R.REFERENCE, **overrides}
    evidence = input_evidence or {}
    if not isinstance(evidence, dict):
        raise TypeError("input_evidence must be an object keyed by CRFCE input name")
    unknown = sorted(set(evidence) - set(values))
    if unknown:
        raise ValueError("unknown CRFCE input evidence key(s): " + ", ".join(unknown))

    provenance: dict[str, dict[str, Any]] = {}
    for name in sorted(values):
        linked = evidence.get(name)
        if linked is not None:
            if isinstance(linked, str):
                source_ref = linked.strip()
                note = ""
            elif isinstance(linked, dict):
                source_ref = str(linked.get("source_ref") or "").strip()
                note = str(linked.get("note") or "").strip()[:500]
            else:
                raise TypeError(f"input_evidence[{name!r}] must be a string or object")
            if not source_ref:
                raise ValueError(f"input_evidence[{name!r}] needs a non-empty source_ref")
            provenance[name] = {
                "standing": "SOURCE_LINKED_NOT_INDEPENDENTLY_VERIFIED",
                "source_ref": source_ref,
                "note": note,
            }
        elif name in overrides:
            provenance[name] = {"standing": "USER_SUPPLIED_UNVERIFIED"}
        else:
            provenance[name] = {"standing": "REFERENCE_ASSUMPTION"}

    payload = {"schema": CONFIG_SCHEMA, "values": values,
               "input_provenance": provenance}
    payload["configuration_hash"] = _hash(payload)
    payload["traceability"] = {
        "source_linked_inputs": sum(
            row["standing"] == "SOURCE_LINKED_NOT_INDEPENDENTLY_VERIFIED"
            for row in provenance.values()),
        "total_inputs": len(provenance),
        "complete": all(
            row["standing"] == "SOURCE_LINKED_NOT_INDEPENDENTLY_VERIFIED"
            for row in provenance.values()),
        "note": "A source link is traceability, not validation or calibration.",
    }
    return payload


def _evaluate(values: dict[str, float], configuration_hash: str) -> dict[str, Any]:
    """Run the coupled reduced-order chain on one already-validated configuration."""
    em = R.electromagnetic(values)
    structural = R.rotor_structural(values)
    rotor = R.rotordynamics(values)
    cryo = R.cryo_thermal(values)
    continuous = R.continuous_rating(values)
    ic = cryo.get("Ic_at_operating_A")
    margin = values["I_op_A"] / ic if ic else None
    cooler_margin = (values["cooler_lift_W"] - cryo["total_cold_load_W"]
                     if cryo.get("total_cold_load_W") is not None else None)
    outputs = {
        "torque_Nm": em.get("torque_Nm"),
        "power_kW": em.get("power_kW"),
        "rotor_safety_factor": structural.get("safety_factor_on_peak"),
        "cold_load_W": cryo.get("total_cold_load_W"),
        "cryocooler_input_W": cryo.get("cryocooler_input_power_W"),
        "hts_current_fraction": margin,
        "cooler_margin_W": cooler_margin,
        "critical_speed_rpm": rotor.get("critical_speed_rpm"),
        "continuous_rpm_ceiling": continuous.get("max_continuous_rpm_at_this_lift"),
    }
    receipts: list[str] = []
    for block in (em, structural, rotor, cryo):
        receipts.extend(x for x in block.get("receipts", []) if x)

    # These edges are actual value propagation through the implemented chain.  They do
    # not pretend that the present one-way reduced-order chain is a converged co-solve.
    edges = [
        {"from": "configuration.rpm", "to": "electromagnetic.angular_speed",
         "value": values["rpm"], "unit": "rpm"},
        {"from": "configuration.rpm", "to": "cryogenic.electrical_frequency",
         "value": cryo.get("electrical_frequency_Hz"), "unit": "Hz"},
        {"from": "configuration.B_T", "to": "electromagnetic.airgap_flux",
         "value": values["B_T"], "unit": "T"},
        {"from": "configuration.B_T,T_K", "to": "cryogenic.critical_current",
         "value": ic, "unit": "A"},
        {"from": "cryogenic.ac+conduction+radiation", "to": "cooler.cold_load",
         "value": cryo.get("total_cold_load_W"), "unit": "W"},
        {"from": "configuration.rpm,T_K", "to": "structural.hoop+cooldown",
         "value": structural.get("safety_factor_on_peak"), "unit": "1"},
        {"from": "electromagnetic.torque,rpm", "to": "shaft.power",
         "value": em.get("power_kW"), "unit": "kW"},
    ]
    for row in edges:
        row["configuration_hash"] = configuration_hash
    return {
        "configuration_hash": configuration_hash,
        "method": "one-way dependency propagation across governed reduced-order models",
        "outputs": outputs,
        "domains": {
            "electromagnetic": {"configuration_hash": configuration_hash, **em},
            "structural": {"configuration_hash": configuration_hash, **structural},
            "rotordynamics": {"configuration_hash": configuration_hash, **rotor},
            "cryogenic_thermal": {"configuration_hash": configuration_hash, **cryo},
            "continuous_rating": {"configuration_hash": configuration_hash, **continuous},
        },
        "coupling_edges": edges,
        "governed_receipts": sorted(set(receipts)),
        "coupling_standing": "PARTIAL_ONE_WAY_REDUCED_ORDER",
        "not_a_cosimulation": True,
    }


def local_sensitivity(configuration: dict[str, Any], parameters: list[str] | None = None,
                      *, relative_step: float = 0.01) -> dict[str, Any]:
    """Central finite-difference sensitivities on the sealed configuration.

    ``relative_step`` is a differentiation step, not an uncertainty or tolerance.
    """
    if not math.isfinite(relative_step) or not 1e-4 <= relative_step <= 0.10:
        raise ValueError("relative_step must lie in [1e-4, 0.10]")
    params = list(parameters or SENSITIVITY_INPUTS)
    unknown = sorted(set(params) - set(SENSITIVITY_INPUTS))
    if unknown:
        raise ValueError("unsupported sensitivity input(s): " + ", ".join(unknown))
    values = dict(configuration["values"])
    cfg_hash = configuration["configuration_hash"]
    baseline = _evaluate(values, cfg_hash)["outputs"]
    rows: list[dict[str, Any]] = []
    for name in params:
        base = float(values[name])
        delta = max(abs(base) * relative_step, 1e-12)
        lo, hi = base - delta, base + delta
        # Respect known bounded variables while retaining a central difference whenever
        # possible. R's input contract is the final authority.
        if name == "spatial_phase_factor":
            lo, hi = max(-1.0, lo), min(1.0, hi)
        elif name == "mli_emissivity":
            lo, hi = max(1e-9, lo), min(1.0, hi)
        elif name == "T_K":
            lo = max(1e-6, lo)
        R.validate_design_overrides({name: lo})
        R.validate_design_overrides({name: hi})
        low = _evaluate({**values, name: lo}, cfg_hash)["outputs"]
        high = _evaluate({**values, name: hi}, cfg_hash)["outputs"]
        for output, base_out in baseline.items():
            low_out, high_out = low.get(output), high.get(output)
            if not all(isinstance(v, (int, float)) and math.isfinite(float(v))
                       for v in (base_out, low_out, high_out)):
                continue
            derivative = (float(high_out) - float(low_out)) / (hi - lo)
            elasticity = (derivative * base / float(base_out)) if base_out else None
            rows.append({
                "input": name, "output": output, "base_input": base,
                "low_input": lo, "high_input": hi, "base_output": base_out,
                "low_output": low_out, "high_output": high_out,
                "derivative": derivative, "elasticity": elasticity,
            })
    ranked = sorted(
        (row for row in rows if row["elasticity"] is not None),
        key=lambda row: (-abs(row["elasticity"]), row["input"], row["output"]),
    )
    return {
        "configuration_hash": cfg_hash,
        "method": "central finite difference on the same sealed configuration",
        "relative_step": relative_step,
        "step_is_not_uncertainty": True,
        "rows": rows,
        "ranked_by_absolute_elasticity": ranked,
    }


def _validate_uq_model(model: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    if not isinstance(model, dict):
        raise ValueError("uncertainty_model must be an object")
    basis = str(model.get("basis_ref") or "").strip()
    if not basis:
        raise ValueError("uncertainty_model.basis_ref is required; EngineAI will not invent spread")
    raw = model.get("inputs")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("uncertainty_model.inputs must be a non-empty object")
    clean: dict[str, dict[str, Any]] = {}
    for name, spec in raw.items():
        if name not in SUPPORTED_UQ_INPUTS:
            raise ValueError(f"uncertainty input {name!r} is unsupported")
        if not isinstance(spec, dict):
            raise ValueError(f"uncertainty input {name!r} must be an object")
        source = str(spec.get("source_ref") or "").strip()
        if not source:
            raise ValueError(f"uncertainty input {name!r} needs source_ref")
        dist = str(spec.get("dist") or "uniform").lower()
        if dist == "uniform":
            half = float(spec.get("rel_halfwidth", 0.0))
            if not math.isfinite(half) or not 0.0 < half < 1.0:
                raise ValueError(f"uncertainty input {name!r} uniform needs 0 < rel_halfwidth < 1")
            clean[name] = {"dist": dist, "rel_halfwidth": half, "source_ref": source}
        elif dist == "normal":
            sigma = float(spec.get("rel_sigma", 0.0))
            if not math.isfinite(sigma) or not 0.0 < sigma <= 0.5:
                raise ValueError(f"uncertainty input {name!r} normal needs 0 < rel_sigma <= 0.5")
            clean[name] = {"dist": dist, "rel_sigma": sigma, "source_ref": source,
                           "sampling": "rejection-truncated to the CRFCE input contract"}
        else:
            raise ValueError(f"uncertainty input {name!r} dist must be uniform or normal")
    return basis, clean


def _draw(rng: np.random.Generator, base: float, spec: dict[str, Any]) -> float:
    if spec["dist"] == "uniform":
        half = spec["rel_halfwidth"]
        return float(base * rng.uniform(1.0 - half, 1.0 + half))
    return float(base * rng.normal(1.0, spec["rel_sigma"]))


def _stats(values: list[float]) -> dict[str, Any]:
    a = np.asarray(values, dtype=float)
    if not len(a):
        return {"n": 0}
    p05, p50, p95 = (float(x) for x in np.percentile(a, [5, 50, 95]))
    return {"n": int(len(a)), "mean": float(np.mean(a)),
            "std": float(np.std(a, ddof=1)) if len(a) > 1 else 0.0,
            "p05": p05, "p50": p50, "p95": p95,
            "min": float(np.min(a)), "max": float(np.max(a))}


def propagate_uncertainty(configuration: dict[str, Any], model: dict[str, Any],
                          *, samples: int = 128, seed: int = 0) -> dict[str, Any]:
    """Propagate only caller-declared, source-linked uncertainty."""
    samples = int(samples)
    if not 32 <= samples <= 5000:
        raise ValueError("samples must be between 32 and 5000")
    basis, inputs = _validate_uq_model(model)
    base = dict(configuration["values"])
    cfg_hash = configuration["configuration_hash"]
    rng = np.random.default_rng(int(seed))
    arrays: dict[str, list[float]] = {}
    feasible: list[bool] = []
    rejected = 0
    attempts = 0
    while len(feasible) < samples and attempts < samples * 100:
        attempts += 1
        trial = dict(base)
        for name, spec in inputs.items():
            trial[name] = _draw(rng, float(base[name]), spec)
        try:
            R.validate_design_overrides({name: trial[name] for name in inputs})
        except (TypeError, ValueError):
            rejected += 1
            continue
        out = _evaluate(trial, cfg_hash)["outputs"]
        numeric = {name: float(value) for name, value in out.items()
                   if isinstance(value, (int, float)) and math.isfinite(float(value))}
        for name, value in numeric.items():
            arrays.setdefault(name, []).append(value)
        sf_ok = numeric.get("rotor_safety_factor", -math.inf) >= base["rotor_SF_min"]
        cold_ok = numeric.get("cold_load_W", math.inf) <= base["cooler_lift_W"]
        hts_ok = numeric.get("hts_current_fraction", math.inf) <= base["hts_margin_max"]
        feasible.append(bool(sf_ok and cold_ok and hts_ok))
    if len(feasible) != samples:
        raise ValueError("uncertainty model produced too many values outside the CRFCE input contract")

    spec = {"schema": "engineai.crfce-uncertainty.v1", "basis_ref": basis,
            "inputs": inputs, "samples": samples, "seed": int(seed),
            "configuration_hash": cfg_hash}
    result = {
        "configuration_hash": cfg_hash,
        "numeric_band_available": True,
        "specification": spec,
        "spec_hash": _hash(spec),
        "distributions": {name: _stats(values) for name, values in sorted(arrays.items())},
        "reliability": {
            "P_declared_requirements_met": float(np.mean(feasible)),
            "requirements": {
                "rotor_safety_factor_min": base["rotor_SF_min"],
                "cold_load_max_W": base["cooler_lift_W"],
                "hts_current_fraction_max": base["hts_margin_max"],
            },
        },
        "accepted_samples": samples, "rejected_draws": rejected,
        "source_refs": sorted({basis} | {row["source_ref"] for row in inputs.values()}),
        "not_propagated": [
            "nonlinear iron B-H and hysteresis model-form uncertainty",
            "anisotropic HTS Jc(B,T,theta), E-J, quench and harmonic AC-loss uncertainty",
            "exact winding, RF enclosure, control-loop, bearing and manufacturing tolerances",
            "solver discretisation/model-form discrepancy on the exact CRFCE geometry",
        ],
        "standing": "PARTIAL_SOURCE_BEARING_UQ_NOT_A_VALIDATION",
    }
    return result


def withheld_uncertainty(configuration_hash: str) -> dict[str, Any]:
    return {
        "configuration_hash": configuration_hash,
        "numeric_band_available": False,
        "standing": "WITHHELD_MISSING_SOURCE_BEARING_UNCERTAINTY_MODEL",
        "reason": "EngineAI will not invent probability distributions, tolerances, or uncertainty widths.",
    }


def solver_qualification(configuration: dict[str, Any], *, run_real_solvers: bool,
                         outdir: str | Path | None = None) -> dict[str, Any]:
    """Run real independent numerical checks without overstating their geometry scope."""
    cfg_hash = configuration["configuration_hash"]
    if not run_real_solvers:
        return {
            "configuration_hash": cfg_hash, "ran": False,
            "standing": "NOT_RUN_REQUESTED",
            "method_qualification_is_not_design_convergence": True,
        }
    target = Path(outdir) if outdir else None
    if target:
        target.mkdir(parents=True, exist_ok=True)
    checks: dict[str, Any] = {}

    # Representative, mesh-resolvable magnetic circuit driven by the shared B target.
    # It is deliberately not labelled as the exact slotted rotor/stator solution.
    try:
        import execution_guard
        import magnetostatics
        gap = 0.005
        ni = float(configuration["values"]["B_T"]) * gap / magnetostatics.MU0
        runs = []
        for n in (320, 400):
            with execution_guard.verification_context(
                    "CRFCE representative magnetic-circuit refinement"):
                result = magnetostatics.c_core(NI=ni, gap=gap, n=n)
            runs.append({"n": n, "cells": result["cells"],
                         "gap_cells": result["gap_cells"],
                         "B_gap_T": result["B_gap_fea_T"],
                         "physical_sign_correct": result["physical_sign_correct"],
                         "result_sha256": _hash(result)})
        change = abs(runs[-1]["B_gap_T"] - runs[-2]["B_gap_T"]) / abs(runs[-1]["B_gap_T"]) * 100.0
        checks["electromagnetic"] = {
            "ok": change < 3.0 and all(row["physical_sign_correct"] for row in runs),
            "solver": "EngineAI 2-D finite-volume magnetostatics",
            "runs": runs, "last_refinement_change_percent": change,
            "scope": "representative linear gapped circuit using shared B target; not exact motor geometry",
            "standing": "METHOD_QUALIFIED_DESIGN_CONVERGENCE_PARTIAL",
        }
    except Exception as exc:
        checks["electromagnetic"] = {"ok": False,
            "standing": "WITHHELD_SOLVER_FAILURE",
            "error": f"{type(exc).__name__}: {exc}"[:500]}

    # Elmer is checked on a problem with an exact Fourier reference.  This establishes
    # the thermal solver path and refinement behavior, not the CRFCE cryostat geometry.
    try:
        import elmer
        if not elmer.elmer_available():
            checks["thermal"] = {"ok": False, "standing": "WITHHELD_ELMER_UNAVAILABLE"}
        else:
            rows = []
            for n in (8, 16):
                result = elmer.plate_conduction(n=n, include_vtu_bytes=target is not None)
                if not result.get("ok"):
                    raise RuntimeError(result["error"])
                artifact = None
                if target:
                    artifact_path = target / f"elmer-plate-n{n}.vtu"
                    artifact_path.write_bytes(result["vtu_bytes"])
                    artifact = {"path": str(artifact_path),
                                "bytes": artifact_path.stat().st_size,
                                "sha256": _file_hash(artifact_path)}
                rows.append({"n": n, "nodes": result["nodes"],
                             "T_centre": result["T_centre_numerical"],
                             "T_exact": result["T_centre_exact"],
                             "error_percent": result["error_percent"],
                             "bounded": result["bounded"], "artifact": artifact})
            change = abs(rows[-1]["T_centre"] - rows[-2]["T_centre"])
            checks["thermal"] = {
                "ok": all(row["bounded"] and row["error_percent"] < 5.0 for row in rows),
                "solver": f"Elmer {elmer.elmer_version()} HeatSolve",
                "runs": rows, "last_refinement_change_K": change,
                "scope": "exact-reference plate benchmark; not the CRFCE cryostat geometry",
                "standing": "METHOD_QUALIFIED_DESIGN_CONVERGENCE_NOT_DEMONSTRATED",
            }
    except Exception as exc:
        checks["thermal"] = {"ok": False, "standing": "WITHHELD_SOLVER_FAILURE",
                             "error": f"{type(exc).__name__}: {exc}"[:500]}

    checks["structural"] = {
        "ok": False, "standing": "EXACT_CRFCE_MESH_CONVERGENCE_NOT_DEMONSTRATED",
        "reason": "CalculiX is qualified elsewhere, but no exact rotor/shaft load-case mesh is run here.",
    }
    checks["rf_emi"] = {"ok": False, "standing": "NOT_DEMONSTRATED",
                         "reason": "No governed full-wave RF/EMI solve on the enclosure and harness."}
    checks["controls"] = {"ok": False, "standing": "NOT_DEMONSTRATED",
                           "reason": "No plant identification, controller, margins, saturation or fault simulation."}
    return {
        "configuration_hash": cfg_hash, "ran": True, "checks": checks,
        "method_qualification_is_not_design_convergence": True,
        "real_solver_checks_passed": sum(bool(row.get("ok")) for row in checks.values()),
        "exact_design_solver_checks_passed": 0,
    }


def _domain_matrix(solvers: dict[str, Any], uncertainty: dict[str, Any]) -> list[dict[str, str]]:
    checks = solvers.get("checks") or {}
    em = checks.get("electromagnetic") or {}
    thermal = checks.get("thermal") or {}
    return [
        {"domain": "electromagnetic torque/flux", "status": "PARTIAL" if em.get("ok") else "SCREENING_ONLY",
         "evidence": "governed air-gap shear + representative linear FV refinement; exact nonlinear motor solve missing"},
        {"domain": "cryogenic thermal", "status": "PARTIAL" if thermal.get("ok") else "SCREENING_ONLY",
         "evidence": "governed reduced-order cold-load chain + Elmer exact-reference benchmark; exact cryostat solve missing"},
        {"domain": "structural/rotordynamics", "status": "SCREENING_ONLY",
         "evidence": "governed hoop/notch/cooldown/fatigue/critical-speed models; exact rotor mesh and burst case missing"},
        {"domain": "coupling", "status": "PARTIAL",
         "evidence": "sealed one-way dependency graph; no iterative co-simulation or coupled convergence"},
        {"domain": "uncertainty", "status": "PARTIAL" if uncertainty.get("numeric_band_available") else "WITHHELD",
         "evidence": uncertainty.get("standing", "unknown")},
        {"domain": "controls", "status": "NOT_DEMONSTRATED",
         "evidence": "plant/controller/margins/fault response absent"},
        {"domain": "RF/EMI quietness", "status": "NOT_DEMONSTRATED",
         "evidence": "full-wave enclosure/harness model and chamber measurements absent"},
        {"domain": "physical validation", "status": "NOT_DEMONSTRATED",
         "evidence": "no calibrated CRFCE hardware measurements supplied"},
    ]


def run(design: dict[str, Any] | None = None, *,
        input_evidence: dict[str, Any] | None = None,
        uncertainty_model: dict[str, Any] | None = None,
        samples: int = 128, seed: int = 0,
        run_real_solvers: bool = True,
        outdir: str | Path | None = None) -> dict[str, Any]:
    configuration = seal_configuration(design, input_evidence)
    cfg_hash = configuration["configuration_hash"]
    coupled = _evaluate(configuration["values"], cfg_hash)
    sensitivity = local_sensitivity(
        configuration,
        parameters=["B_T", "rpm", "T_K", "electric_loading_peak_A_per_m",
                    "slot_root_radius_m", "conduction_k_W_mK"],
    )
    uncertainty = (propagate_uncertainty(configuration, uncertainty_model,
                                         samples=samples, seed=seed)
                   if uncertainty_model is not None else withheld_uncertainty(cfg_hash))
    solver_dir = Path(outdir) / "solver-evidence" if outdir else None
    solvers = solver_qualification(configuration, run_real_solvers=run_real_solvers,
                                   outdir=solver_dir)
    matrix = _domain_matrix(solvers, uncertainty)
    result = {
        "schema": SCHEMA,
        "verdict": "VIRTUAL_VV_EXECUTED_NOT_RELEASEABLE",
        "configuration": configuration,
        "coupled_model": coupled,
        "sensitivity": sensitivity,
        "uncertainty": uncertainty,
        "solver_qualification": solvers,
        "domain_matrix": matrix,
        "release_gates_advanced": {
            "G02_mesh_independence": "PARTIAL_REPRESENTATIVE_EM_ONLY",
            "G03_solver_convergence": "PARTIAL_METHOD_QUALIFICATION_ONLY",
            "G06_coupled_multiphysics": "PARTIAL_ONE_WAY_REDUCED_ORDER",
            "G07_uncertainty": ("PARTIAL_SOURCE_BEARING_SUBSET" if uncertainty.get("numeric_band_available")
                                else "NOT_MET_MISSING_UNCERTAINTY_MODEL"),
        },
        "release_authorized": False,
        "design_release_status": "NOT_AUTHORIZED",
        "physical_validation": "NOT_DEMONSTRATED",
        "boundary": BOUNDARY,
    }
    result["record_hash"] = _hash(result)
    if outdir:
        result["artifacts"] = write_bundle(result, outdir)
    return result


def write_bundle(result: dict[str, Any], outdir: str | Path) -> list[dict[str, Any]]:
    root = Path(outdir)
    root.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in result.items() if key != "artifacts"}
    files: list[Path] = []

    record = root / "crfce-coupled-vv.json"
    record.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False,
                                 allow_nan=False, default=_json_default) + "\n", encoding="utf-8")
    files.append(record)

    config = root / "crfce-shared-configuration.json"
    config.write_text(json.dumps(result["configuration"], indent=2, sort_keys=True,
                                 ensure_ascii=False, allow_nan=False,
                                 default=_json_default) + "\n", encoding="utf-8")
    files.append(config)

    sensitivity = root / "crfce-sensitivity.csv"
    fields = ("input", "output", "base_input", "low_input", "high_input",
              "base_output", "low_output", "high_output", "derivative", "elasticity")
    with sensitivity.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({name: row.get(name) for name in fields}
                         for row in result["sensitivity"]["rows"])
    files.append(sensitivity)

    matrix = root / "crfce-domain-matrix.csv"
    with matrix.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("domain", "status", "evidence"))
        writer.writeheader()
        writer.writerows(result["domain_matrix"])
    files.append(matrix)

    report = root / "CRFCE_COUPLED_VV_REPORT.md"
    lines = [
        "# CRFCE coupled virtual V&V report", "",
        f"- Record: `{result['record_hash']}`",
        f"- Shared configuration: `{result['configuration']['configuration_hash']}`",
        f"- Verdict: **{result['verdict']}**",
        f"- Physical validation: **{result['physical_validation']}**", "",
        "## Domain standing", "",
        "| Domain | Standing | Evidence boundary |", "|---|---|---|",
    ]
    lines.extend(f"| {row['domain']} | {row['status']} | {row['evidence']} |"
                 for row in result["domain_matrix"])
    lines += ["", "## Release boundary", "", result["boundary"], ""]
    report.write_text("\n".join(lines), encoding="utf-8")
    files.append(report)

    return [{"path": str(path), "bytes": path.stat().st_size,
             "sha256": _file_hash(path)} for path in files]


def wants_coupled_vv(message: str) -> bool:
    text = (message or "").casefold()
    if "crfce" not in text:
        return False
    return any(term in text for term in (
        "coupled", "multiphysics", "v&v", "verification and validation",
        "uncertainty", "sensitivity", "convergence", "validate all physics",
    ))


def chat_answer(design: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    result = run(design, **kwargs)
    output = result["coupled_model"]["outputs"]
    matrix = ", ".join(f"{row['domain']}: {row['status']}" for row in result["domain_matrix"])
    return {
        "ok": True, "released": True,
        "released_scope": R.EXECUTOR_RELEASE_SCOPE,
        "basis": "CRFCE_COUPLED_VIRTUAL_VV",
        "release_authorized": False,
        "design_release_status": "NOT_AUTHORIZED",
        "physical_validation": "NOT_DEMONSTRATED",
        "engineering_claim": True, "verified": False,
        "capability": "crfce_coupled_vv.run", "id": "crfce_coupled_vv.run",
        "value": output.get("power_kW"), "unit": "kW",
        "receipt_digest": (result["coupled_model"]["governed_receipts"] or [result["record_hash"]])[0],
        "answer": (
            "**CRFCE coupled virtual V&V completed**\n\n"
            f"- Shared configuration: `{result['configuration']['configuration_hash'][:16]}`\n"
            f"- Power: {output.get('power_kW')} kW; rotor SF: {output.get('rotor_safety_factor')}; "
            f"cold load: {output.get('cold_load_W')} W\n"
            f"- Domain standing: {matrix}\n\n"
            f"_{result['boundary']}_"
        ),
        "governed": result,
        "actions": result.get("artifacts", []),
        "note": result["boundary"],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="out/crfce-coupled-vv")
    parser.add_argument("--no-real-solvers", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(outdir=args.outdir,
                         run_real_solvers=not args.no_real_solvers),
                     indent=2, sort_keys=True))
