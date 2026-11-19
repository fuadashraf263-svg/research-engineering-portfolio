#!/usr/bin/env python3
"""Adversarial conformance for shared-config CRFCE coupled virtual V&V."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import crfce_coupled_vv as V


def check(condition: bool, message: str) -> None:
    print("  " + ("ok  " if condition else "FAIL") + " " + message)
    if not condition:
        raise AssertionError(message)


def refuses(call, message: str) -> None:
    try:
        call()
    except (TypeError, ValueError):
        check(True, message)
    else:
        check(False, message)


cfg = V.seal_configuration(
    {"rpm": 10000.0},
    {"rpm": {"source_ref": "claim:CRFCE-RPM-001", "note": "document claim under review"}},
)
check(len(cfg["configuration_hash"]) == 64,
      "the shared configuration is content-addressed")
check(cfg == V.seal_configuration(
    {"rpm": 10000.0},
    {"rpm": {"source_ref": "claim:CRFCE-RPM-001", "note": "document claim under review"}},
), "the configuration seal is deterministic")
check(cfg["input_provenance"]["rpm"]["standing"] ==
      "SOURCE_LINKED_NOT_INDEPENDENTLY_VERIFIED",
      "a document link adds traceability without becoming validation")
check(cfg["traceability"]["complete"] is False,
      "unlinked reference assumptions keep traceability incomplete")
refuses(lambda: V.seal_configuration({"not_a_parameter": 1.0}),
        "unknown design inputs are refused")
refuses(lambda: V.seal_configuration({}, {"rpm": {"source_ref": ""}}),
        "empty source references are refused")
refuses(lambda: V.seal_configuration({}, {"not_a_parameter": "x"}),
        "unknown evidence keys are refused")

coupled = V._evaluate(cfg["values"], cfg["configuration_hash"])
check(all(block["configuration_hash"] == cfg["configuration_hash"]
          for block in coupled["domains"].values()),
      "every domain consumes the exact same sealed configuration")
check(all(edge["configuration_hash"] == cfg["configuration_hash"]
          for edge in coupled["coupling_edges"]),
      "every dependency edge is bound to the same configuration")
check(coupled["governed_receipts"], "coupled results retain governed receipts")
check(coupled["not_a_cosimulation"] is True and
      coupled["coupling_standing"] == "PARTIAL_ONE_WAY_REDUCED_ORDER",
      "one-way propagation is not mislabeled as a converged co-simulation")

sense = V.local_sensitivity(cfg, ["rpm", "B_T", "slot_root_radius_m"])
power_rpm = next(row for row in sense["rows"]
                 if row["input"] == "rpm" and row["output"] == "power_kW")
check(power_rpm["elasticity"] is not None and 0.8 < power_rpm["elasticity"] < 1.2,
      "power sensitivity responds physically to speed")
check(sense["step_is_not_uncertainty"] is True,
      "the numerical differentiation step is not presented as an uncertainty")

refuses(lambda: V.propagate_uncertainty(cfg, {}, samples=64),
        "UQ refuses a missing basis and input model")
refuses(lambda: V.propagate_uncertainty(
    cfg, {"basis_ref": "review", "inputs": {"rpm": {"rel_halfwidth": 0.05}}},
    samples=64), "UQ refuses an input with no source_ref")
refuses(lambda: V.propagate_uncertainty(
    cfg, {"basis_ref": "review", "inputs": {
        "tape_length_m": {"rel_halfwidth": 0.05, "source_ref": "x"}}}, samples=64),
    "UQ refuses a parameter that is not supported in this version")

model = {"basis_ref": "TEST: declared tolerance study",
         "inputs": {
             "rpm": {"dist": "uniform", "rel_halfwidth": 0.04,
                     "source_ref": "TEST: speed-control envelope"},
             "B_T": {"dist": "uniform", "rel_halfwidth": 0.03,
                     "source_ref": "TEST: field-model spread"},
         }}
u1 = V.propagate_uncertainty(cfg, model, samples=64, seed=17)
u2 = V.propagate_uncertainty(cfg, model, samples=64, seed=17)
check(u1["spec_hash"] == u2["spec_hash"] and
      u1["distributions"] == u2["distributions"] and
      u1["reliability"] == u2["reliability"],
      "source-bearing UQ is deterministic under a fixed seed")
check(u1["distributions"]["power_kW"]["std"] > 0 and
      0.0 <= u1["reliability"]["P_declared_requirements_met"] <= 1.0,
      "UQ returns a real numeric band and a bounded reliability")
check(u1["standing"] == "PARTIAL_SOURCE_BEARING_UQ_NOT_A_VALIDATION" and
      len(u1["not_propagated"]) >= 4,
      "partial UQ names the model-form contributors it does not cover")

with tempfile.TemporaryDirectory(prefix="engineai_crfce_vv_") as directory:
    result = V.run({"rpm": 10000.0}, input_evidence={"rpm": "claim:CRFCE-RPM-001"},
                   uncertainty_model=model, samples=64, seed=17,
                   run_real_solvers=True, outdir=directory)
    checks = result["solver_qualification"].get("checks") or {}
    check(checks["electromagnetic"]["ok"] is True and
          len(checks["electromagnetic"]["runs"]) == 2,
          "real finite-volume magnetostatics runs at two refinements")
    check(checks["electromagnetic"]["standing"] ==
          "METHOD_QUALIFIED_DESIGN_CONVERGENCE_PARTIAL",
          "representative magnetic refinement is not promoted to exact-design convergence")
    if checks["thermal"]["standing"] != "WITHHELD_ELMER_UNAVAILABLE":
        check(checks["thermal"]["ok"] is True and
              all(row["artifact"] and Path(row["artifact"]["path"]).is_file()
                  for row in checks["thermal"]["runs"]),
              "real Elmer refinements produce hashed VTU evidence")
    check(checks["structural"]["standing"] ==
          "EXACT_CRFCE_MESH_CONVERGENCE_NOT_DEMONSTRATED" and
          checks["rf_emi"]["standing"] == "NOT_DEMONSTRATED" and
          checks["controls"]["standing"] == "NOT_DEMONSTRATED",
          "missing exact structural, RF and controls evidence remains withheld")
    check(result["release_authorized"] is False and
          result["physical_validation"] == "NOT_DEMONSTRATED",
          "virtual V&V cannot authorize release or physical validation")
    artifacts = result["artifacts"]
    check(len(artifacts) == 5 and all(Path(row["path"]).is_file() and row["sha256"]
                                      for row in artifacts),
          "the V&V record, configuration, matrices and report are real hashed files")
    loaded = json.loads(Path(artifacts[0]["path"]).read_text(encoding="utf-8"))
    check(loaded["configuration"]["configuration_hash"] ==
          result["configuration"]["configuration_hash"],
          "the written bundle preserves the sealed shared configuration")

check(V.wants_coupled_vv("Run CRFCE coupled multiphysics V&V with uncertainty"),
      "explicit CRFCE coupled-V&V intent is recognized")
check(not V.wants_coupled_vv("explain uncertainty in general"),
      "ordinary chat is not hijacked")

reply = V.chat_answer(run_real_solvers=False)
check(reply["basis"] == "CRFCE_COUPLED_VIRTUAL_VV" and reply["released"] is True,
      "the chat result carries a narrow capability-output basis")
check(reply["verified"] is False and reply["physical_validation"] == "NOT_DEMONSTRATED" and
      reply["release_authorized"] is False,
      "the chat surface retains the physical/release boundary")

print("crfce_coupled_vv_conformance: PASS")
