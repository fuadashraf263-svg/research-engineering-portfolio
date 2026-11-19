#!/usr/bin/env python3
"""Conformance for version-safe CRFCE source-to-configuration resolution."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import crfce_configuration_resolution as C
import crfce_coupled_vv as V
import project_research


def check(condition: bool, message: str) -> None:
    print("  " + ("ok  " if condition else "FAIL") + " " + message)
    if not condition:
        raise AssertionError(message)


def rejected_decision(claim_ledger: dict, conflict_ledger: dict,
                      decision: dict, expected: str, message: str) -> None:
    try:
        C.resolve(claim_ledger, conflict_ledger, decision,
                  source_corpus_report=source_corpus_report(claim_ledger, conflict_ledger))
    except ValueError as exc:
        check(expected in str(exc), message)
    else:
        check(False, message)


_claim_ids: dict[str, str] = {}


def cid(label: str) -> str:
    return _claim_ids.get(label, hashlib.sha256(label.encode()).hexdigest())


def claim(label: str, name: str, value: float, unit: str, page: int) -> dict:
    row = {"claim": name, "normalized_value": value,
           "normalized_unit": unit, "original_value": value, "original_unit": unit,
           "source": {"sha256": hashlib.sha256(("source-" + label).encode()).hexdigest(),
                      "file_id": "file-" + label, "member_sha256": None,
                      "locator": f"page {page}", "excerpt": label},
           "standing": "UNVERIFIED_EXTRACTED"}
    row["claim_id"] = project_research.claim_id_for(row)
    _claim_ids[label] = row["claim_id"]
    return row


def source_corpus_report(claim_ledger: dict, conflict_ledger: dict,
                         *, name_suffix: str = "") -> dict:
    claim_rows = sorted(claim_ledger.get("claims", []), key=lambda row: (
        str(row["claim"]), str(row["source"].get("sha256")),
        str(row["source"].get("locator")), row["normalized_value"],
    ))
    derived_claim_analysis = project_research.claim_analysis_from_ledger(claim_rows)
    source_map = {}
    for row in claim_rows:
        source = row.get("source") or {}
        file_id, digest = source.get("file_id"), source.get("sha256")
        if file_id and digest:
            source_map[(str(file_id), str(digest))] = {
                "file_id": str(file_id), "name": str(file_id) + name_suffix,
                "sha256": str(digest), "bytes": 1,
            }
    body = {
        "schema": "engineai.crfce-source-corpus.v1",
        "verdict": "CORPUS_INDEXED",
        "manifest": {
            "schema": "engineai.crfce-source-manifest.v1",
            "sources": [source_map[key] for key in sorted(source_map)],
            "source_count": len(source_map), "source_bytes": len(source_map),
            "ingestion_failures": [], "exact_duplicate_groups": [],
            "normalised_text_duplicate_groups": [], "potential_version_families": [],
        },
        "scope": {"note": "synthetic test fixture; not source authentication"},
        "claims": {
            "claim_ledger": claim_rows,
            "candidate_conflicts": conflict_ledger.get("candidate_conflicts", []),
            "repeated_claims": derived_claim_analysis["repeated_claims"],
            "value_variants": derived_claim_analysis["value_variants"],
            "note": derived_claim_analysis["note"],
        },
        "evidence_boundary": {
            "extracted_claims": "UNVERIFIED_EXTRACTED",
            "plot_pixels": "NOT_DIGITISED_AS_MEASUREMENTS",
            "physical_validation": "NOT_DEMONSTRATED",
            "design_release_status": "NOT_AUTHORIZED", "release_authorized": False,
        },
        "summary": "synthetic source-corpus report",
    }
    report = dict(body)
    report["receipt"] = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()
    return report


def reseal_source_corpus_report(report: dict) -> dict:
    body = {key: value for key, value in report.items() if key != "receipt"}
    resealed = dict(body)
    resealed["receipt"] = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()
    return resealed


rows = sorted([
    claim("radius-small", "rotor_radius", 60.0, "mm", 3),
    claim("radius-large", "rotor_radius", 215.0, "mm", 93),
    claim("stack", "rotor_stack_length", 50.0, "mm", 4),
    claim("temp-a", "operating_temperature", 30.0, "K", 5),
    claim("temp-b", "operating_temperature", 30.0, "K", 8),
    claim("power", "continuous_mechanical_power", 20000.0, "W", 6),
], key=lambda row: (str(row["claim"]), str(row["source"].get("sha256")),
                    str(row["source"].get("locator")), row["normalized_value"]))
claims = {"claims": rows}
conflicts = {"candidate_conflicts":
             project_research.claim_analysis_from_ledger(rows)["candidate_conflicts"]}

by_claim_id = {row["claim_id"]: row for row in rows}


def binding_for(decision: dict) -> dict:
    selected_sources = sorted({
        (by_claim_id[str(claim_id)]["source"]["file_id"],
         by_claim_id[str(claim_id)]["source"]["sha256"])
        for claim_id in decision["selections"].values()
    })
    return {
        "schema": C.SOURCE_VERSION_BINDING_SCHEMA,
        "configuration_variant": decision["configuration_variant"],
        "review_ref": decision["review_ref"],
        "rationale": "Selected source locators are asserted to belong to this reviewed input set; this assertion remains unverified.",
        "selected_claim_ids": decision["selections"],
        "sources": [{"file_id": file_id, "sha256": digest}
                    for file_id, digest in selected_sources],
    }

a = C.analyse(claims, conflicts)
check(a["verdict"] == "SEMANTIC_REVIEW_REQUIRED" and
      a["automatic_selection_permitted"] is False,
      "extracted claims cannot auto-select an executable configuration")
radius = next(row for row in a["executable_input_candidates"]
              if row["input_field"] == "rotor_r_m")
check(len(radius["candidates"]) == 2 and radius["standing"] == "SEMANTIC_REVIEW_REQUIRED",
      "60 mm and 215 mm remain separate design-version candidates")
variants = a["conflict_variants"][0]["variants"]
check({row["converted_value"] for row in variants} == {0.06, 0.215} and
      "averaging/merging is forbidden" in a["conflict_variants"][0]["rule"],
      "candidate conversion is unit-correct and never averaged")
temperature = next(row for row in a["executable_input_candidates"]
                   if row["input_field"] == "T_K")
check(len(temperature["candidates"]) == 1 and
      temperature["candidates"][0]["repetition_count"] == 2 and
      temperature["candidates"][0]["standing"] ==
      "UNVERIFIED_REPEATED_VALUE_NOT_INDEPENDENT_VALIDATION",
      "repeated identical text does not become independent validation")
check(any(row["claim"] == "continuous_mechanical_power" and
          row["standing"] == "UNVERIFIED_REQUIREMENT_CANDIDATE_REVIEW_REQUIRED"
          for row in a["research_requirement_candidates"]),
      "a claimed output is retained as an unverified target, not smuggled into an input")

withheld = C.resolve(claims, conflicts, None)
check(withheld["verdict"] == "CONFIGURATION_WITHHELD_REVIEW_INCOMPLETE" and
      set(withheld["missing_required_selections"]) == set(C.REQUIRED_EXECUTABLE_FIELDS),
      "missing semantic decisions withhold the configuration")

base = {"configuration_variant": "small-rotor-prototype", "review_ref": "review:R-17",
        "selections": {"rotor_r_m": cid("radius-small"),
                       "L_stack_m": cid("stack"), "T_K": cid("temp-a")}}
source_report_a = source_corpus_report(claims, conflicts)
source_report_b = source_corpus_report(claims, conflicts, name_suffix="-other")
corpus_receipt_a = source_report_a["receipt"]
corpus_receipt_b = source_report_b["receipt"]
checked_report = C.resolve(claims, conflicts, None,
                           source_corpus_report=source_report_a)
check(checked_report.get("source_corpus_receipt") == source_report_a["receipt"] and
      checked_report.get("source_corpus_integrity") ==
      "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY",
      "the resolver recomputes a structured corpus report receipt rather than trusting a bare digest")
base_with_binding = {**base, "source_version_binding": binding_for(base)}
try:
    C.resolve(claims, conflicts, base_with_binding,
              source_corpus_report=source_report_a)
except ValueError as exc:
    check("explicit resolution" in str(exc),
          "a conflicting claim cannot be selected without an explicit resolution")
else:
    check(False, "conflicting claim selection bypassed review")

try:
    C.resolve(claims, {"candidate_conflicts": []}, base_with_binding,
              source_corpus_report=source_report_a)
except ValueError as exc:
    check("candidate conflict ledger does not match" in str(exc),
          "distinct source values require review even if an upstream conflict ledger omits them")
else:
    check(False, "an incomplete conflict ledger enabled automatic source selection")

decision = {**base, "conflict_resolutions": {"rotor_radius": {
    "selected_claim_id": cid("radius-small"), "review_ref": "review:R-17",
    "rationale": "prototype document version; large-radius study is a separate variant",
}}}
unbound = C.resolve(claims, conflicts, decision,
                    source_corpus_report=source_report_a)
check(unbound["verdict"] == "CONFIGURATION_WITHHELD_REVIEW_INCOMPLETE" and
      unbound.get("missing_source_version_binding") is True and
      unbound["configuration_ready_for_virtual_analysis"] is False,
      "cross-source input claims cannot form a variant without an exact source-version binding")
with tempfile.TemporaryDirectory(prefix="engineai_crfce_unbound_") as directory:
    unbound_bundle = C.chat_answer(claims, conflicts, decision, outdir=directory)
    unbound_review_path = next(
        Path(row["path"]) for row in unbound_bundle["actions"]
        if Path(row["path"]).name == "CRFCE_CONFIGURATION_REVIEW.md")
    review_text = unbound_review_path.read_text(encoding="utf-8")
    check("source-version binding" in unbound_bundle["answer"] and
          "Source-version binding required" in review_text and
          "Source-corpus report required" in review_text and
          unbound_bundle["governed"].get("release_authorized") is False,
          "the answer and report name missing source/version inputs without implying release")
source_binding = binding_for(decision)
bound_decision = {**decision, "source_version_binding": source_binding}

invalid_member_rows = []
invalid_member_claim = None
for row in rows:
    if row["claim_id"] == cid("stack"):
        changed = json.loads(json.dumps(row))
        changed["source"]["member_sha256"] = ""
        changed.pop("claim_id")
        changed["claim_id"] = project_research.claim_id_for(changed)
        invalid_member_claim = changed
        invalid_member_rows.append(changed)
    else:
        invalid_member_rows.append(row)
invalid_member_claims = {"claims": invalid_member_rows}
invalid_member_conflicts = {"candidate_conflicts":
                            project_research.claim_analysis_from_ledger(
                                invalid_member_rows)["candidate_conflicts"]}
invalid_member_report = source_corpus_report(invalid_member_claims,
                                            invalid_member_conflicts)
invalid_member_decision = {
    **decision,
    "selections": {**decision["selections"],
                   "L_stack_m": invalid_member_claim["claim_id"]},
}
by_claim_id[invalid_member_claim["claim_id"]] = invalid_member_claim
invalid_member_decision["source_version_binding"] = binding_for(invalid_member_decision)
try:
    C.resolve(invalid_member_claims, invalid_member_conflicts,
              invalid_member_decision,
              source_corpus_report=invalid_member_report)
except ValueError as exc:
    check("member_sha256" in str(exc),
          "an explicitly empty archive-member digest is rejected before virtual configuration")
else:
    check(False,
          "an explicitly empty archive-member digest was accepted into a virtual configuration")

missing_corpus = C.resolve(claims, conflicts, bound_decision)
check(missing_corpus["verdict"] == "CONFIGURATION_WITHHELD_REVIEW_INCOMPLETE" and
      missing_corpus.get("missing_source_corpus_report") is True and
      missing_corpus["configuration_ready_for_virtual_analysis"] is False,
      "a complete reviewer selection without a structured corpus report remains withheld")

try:
    C.resolve(claims, conflicts, bound_decision, source_corpus_receipt="not-a-digest")
except ValueError as exc:
    check("source_corpus_receipt" in str(exc),
          "the direct resolver refuses a bare source-corpus receipt")
else:
    check(False, "the direct resolver accepted a bare source-corpus receipt")

tampered_report = {**source_report_a, "summary": "changed after receipt creation"}
try:
    C.resolve(claims, conflicts, None, source_corpus_report=tampered_report)
except ValueError as exc:
    check("receipt does not match" in str(exc),
          "changing report contents without recomputing its receipt is refused")
else:
    check(False, "a stale receipt was accepted after report contents changed")

changed_claim_body = json.loads(json.dumps(source_report_a))
changed_claim_body["claims"]["claim_ledger"][0]["normalized_value"] += 0.01
try:
    C.resolve(claims, conflicts, None,
              source_corpus_report=reseal_source_corpus_report(changed_claim_body))
except ValueError as exc:
    check("claim_id does not match" in str(exc),
          "a rehashed report cannot change claim contents while keeping a stale content ID")
else:
    check(False, "a stale claim content ID was accepted")

incomplete_conflict_body = json.loads(json.dumps(source_report_a))
incomplete_conflict_body["claims"]["candidate_conflicts"] = []
try:
    C.resolve(claims, conflicts, None,
              source_corpus_report=reseal_source_corpus_report(incomplete_conflict_body))
except ValueError as exc:
    check("candidate_conflicts is inconsistent" in str(exc),
          "a rehashed report cannot omit deterministic conflicts present in its claim ledger")
else:
    check(False, "a self-hashed report with omitted claim conflicts was accepted")

promoted_boundary_body = json.loads(json.dumps(source_report_a))
promoted_boundary_body["evidence_boundary"]["release_authorized"] = True
try:
    C.resolve(claims, conflicts, None,
              source_corpus_report=reseal_source_corpus_report(promoted_boundary_body))
except ValueError as exc:
    check("cannot promote release" in str(exc),
          "a corpus report cannot use its own receipt to promote release or physical-validation status")
else:
    check(False, "a report claiming release authorization was accepted")

try:
    C.resolve({"claims": [rows[0]]}, conflicts, None,
              source_corpus_report=source_report_a)
except ValueError as exc:
    check("claim ledger does not match" in str(exc),
          "a report cannot be paired with a different claim ledger")
else:
    check(False, "a mismatched claim ledger was accepted")

try:
    C.resolve(claims, {"candidate_conflicts": []}, None,
              source_corpus_report=source_report_a)
except ValueError as exc:
    check("candidate conflict ledger does not match" in str(exc),
          "a report cannot be paired with a different conflict ledger")
else:
    check(False, "a mismatched candidate conflict ledger was accepted")

manifest_rows = list(source_report_a["manifest"]["sources"])
unmanifested_body = {key: value for key, value in source_report_a.items()
                     if key != "receipt"}
unmanifested_body["manifest"] = {
    **source_report_a["manifest"],
    "sources": manifest_rows[1:],
    "source_count": len(manifest_rows) - 1,
    "source_bytes": len(manifest_rows) - 1,
}
unmanifested_report = reseal_source_corpus_report(unmanifested_body)
try:
    C.resolve(claims, conflicts, None, source_corpus_report=unmanifested_report)
except ValueError as exc:
    check("absent from the source manifest" in str(exc),
          "a self-consistent report with a claim source missing from its manifest is refused")
else:
    check(False, "a claim source omitted from the manifest was accepted")

partial_body = {key: value for key, value in source_report_a.items() if key != "receipt"}
partial_body["verdict"] = "CORPUS_PARTIAL"
try:
    C.resolve(claims, conflicts, None,
              source_corpus_report=reseal_source_corpus_report(partial_body))
except ValueError as exc:
    check("complete CORPUS_INDEXED" in str(exc),
          "a partial ingestion report cannot bind virtual-analysis inputs")
else:
    check(False, "a partial corpus report was accepted")

wrong_variant = {**bound_decision, "source_version_binding": {
    **source_binding, "configuration_variant": "different-variant"}}
rejected_decision(claims, conflicts, wrong_variant, "variant does not match",
                  "a binding for a different variant is refused")
wrong_claims = {**source_binding, "selected_claim_ids": {
    **decision["selections"], "L_stack_m": cid("radius-large")}}
rejected_decision(claims, conflicts, {**decision, "source_version_binding": wrong_claims},
                  "claim IDs do not match",
                  "a source binding cannot silently swap one selected input claim")
extra_source = {**source_binding, "sources": [
    *source_binding["sources"],
    {"file_id": "unselected-source", "sha256": hashlib.sha256(b"extra").hexdigest()},
]}
rejected_decision(claims, conflicts, {**decision, "source_version_binding": extra_source},
                  "source set does not exactly match",
                  "the bound source set cannot add documents outside the selected claims")
claims_without_source_id_rows = []
for row in rows:
    if row["claim_id"] == cid("stack"):
        changed = {**row, "source": {key: value for key, value in row["source"].items()
                                     if key != "file_id"}}
        changed.pop("claim_id")
        changed["claim_id"] = project_research.claim_id_for(changed)
        claims_without_source_id_rows.append(changed)
    else:
        claims_without_source_id_rows.append(row)
claims_without_source_id = {"claims": claims_without_source_id_rows}
rejected_decision(claims_without_source_id, conflicts, bound_decision,
                  "stable file_id",
                  "a selected claim without a stable source file ID cannot be version-bound")

r = C.resolve(claims, conflicts, bound_decision,
              source_corpus_report=source_report_a)
check(r["verdict"] == "VERSIONED_CONFIGURATION_READY_FOR_VIRTUAL_ANALYSIS" and
      r["configuration_ready_for_virtual_analysis"] is True and
      r["schema"] == "engineai.crfce-configuration-resolution.v4" and
      r["source_corpus_integrity"] ==
      "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY",
      "a complete report-bound source selection becomes a virtual-analysis input set without claiming authenticity")
with tempfile.TemporaryDirectory(prefix="engineai_crfce_corpus_bound_") as directory:
    corpus_bound = C.chat_answer(
        claims, conflicts, bound_decision, outdir=directory,
        source_corpus_report=source_report_a)
    bound_governed = corpus_bound["governed"]
    resolution_artifact = next(
        row for row in corpus_bound["actions"]
        if Path(row["path"]).name == "CRFCE_configuration_resolution.json")
    stored_resolution = json.loads(Path(resolution_artifact["path"]).read_text(encoding="utf-8"))
    check(bound_governed.get("source_corpus_receipt") == corpus_receipt_a and
          corpus_bound.get("source_corpus_receipt") == corpus_receipt_a and
          bound_governed.get("source_corpus_integrity") ==
          "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY",
          "the recomputed report receipt and limited integrity standing are retained in governed and Studio results")
    check(corpus_bound["receipt_digest"] == bound_governed["resolution_hash"] ==
          stored_resolution["resolution_hash"] and
          stored_resolution.get("source_corpus_receipt") == corpus_receipt_a,
          "the corpus receipt is bound before resolution hashing and bundle writing")
    check(C._hash({key: value for key, value in bound_governed.items()
                  if key != "resolution_hash"}) == bound_governed["resolution_hash"],
          "the retained resolution hash recomputes over the corpus-bound record")
    review_artifact = next(
        row for row in corpus_bound["actions"]
        if Path(row["path"]).name == "CRFCE_CONFIGURATION_REVIEW.md")
    review_text = Path(review_artifact["path"]).read_text(encoding="utf-8")
    check(corpus_receipt_a in corpus_bound["answer"] and corpus_receipt_a in review_text,
          "the Studio answer and human-readable report expose the bound corpus receipt")
with tempfile.TemporaryDirectory(prefix="engineai_crfce_corpus_receipt_a_") as first_dir, \
        tempfile.TemporaryDirectory(prefix="engineai_crfce_corpus_receipt_b_") as second_dir:
    first = C.chat_answer(claims, conflicts, bound_decision, outdir=first_dir,
                          source_corpus_report=source_report_a)
    second = C.chat_answer(claims, conflicts, bound_decision, outdir=second_dir,
                           source_corpus_report=source_report_b)
    check(first["receipt_digest"] != second["receipt_digest"] and
          first["governed"]["review_decision_hash"] == second["governed"]["review_decision_hash"],
          "changing corpus identity changes resolution identity without changing reviewer-decision identity")

with tempfile.TemporaryDirectory(prefix="engineai_crfce_report_cli_") as directory:
    root = Path(directory)
    inputs = {
        "claims.json": claims,
        "conflicts.json": conflicts,
        "decision.json": bound_decision,
        "source-corpus.json": source_report_a,
    }
    for name, payload in inputs.items():
        (root / name).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    cli = [sys.executable, "-B", str(Path(C.__file__).resolve()),
           str(root / "claims.json"), str(root / "conflicts.json"),
           "--decision", str(root / "decision.json"),
           "--source-corpus-report", str(root / "source-corpus.json"),
           "--outdir", str(root / "output")]
    cli_result = subprocess.run(cli, capture_output=True, text=True, check=False)
    cli_payload = json.loads(cli_result.stdout) if cli_result.returncode == 0 else {}
    check(cli_result.returncode == 0 and
          cli_payload.get("source_corpus_receipt") == source_report_a["receipt"] and
          cli_payload.get("configuration_ready_for_virtual_analysis") is True,
          "the CLI accepts a structured report, recomputes it, and emits the source-bound configuration receipt")
    bare_receipt_result = subprocess.run(
        [sys.executable, "-B", str(Path(C.__file__).resolve()),
         str(root / "claims.json"), str(root / "conflicts.json"),
         "--decision", str(root / "decision.json"),
         "--source-corpus-receipt", source_report_a["receipt"],
         "--outdir", str(root / "bare-output")],
        capture_output=True, text=True, check=False)
    check(bare_receipt_result.returncode != 0 and
          "bare source_corpus_receipt is no longer accepted" in bare_receipt_result.stderr,
          "the CLI explicitly rejects the deprecated bare-digest contract")

try:
    C.chat_answer(claims, conflicts, bound_decision, outdir=tempfile.gettempdir(),
                  source_corpus_receipt="not-a-digest")
except ValueError as exc:
    check("source_corpus_receipt" in str(exc),
          "a malformed source-corpus receipt is refused before generating a resolution")
else:
    check(False, "a malformed source-corpus receipt was accepted")
check(r["analysis"]["automatic_selection_permitted"] is False and
      len(r["review_decision_hash"]) == 64,
      "the resolved record retains its analysis and content-addressed review decision")
check(r["source_version_binding"]["standing"] ==
      "EXTERNAL_REVIEW_ASSERTION_NOT_INDEPENDENTLY_VERIFIED" and
      len(r["source_version_binding"]["sources"]) == 3 and
      all(f"file-id:{file_id}" in r["shared_configuration"]["input_provenance"][field]["source_ref"]
          for field, file_id in (("rotor_r_m", "file-radius-small"),
                                 ("L_stack_m", "file-stack"),
                                 ("T_K", "file-temp-a"))),
      "the exact cross-source join is visible and explicitly remains an unverified reviewer assertion")
values = r["shared_configuration"]["values"]
check(values["rotor_r_m"] == 0.06 and values["L_stack_m"] == 0.05 and values["T_K"] == 30.0,
      "selected claims are converted to the exact CRFCE SI input fields")
check(all(r["shared_configuration"]["input_provenance"][name]["standing"] ==
          "SOURCE_LINKED_NOT_INDEPENDENTLY_VERIFIED" for name in C.REQUIRED_EXECUTABLE_FIELDS),
      "each selected value retains its claim/source provenance")
check(r["input_traceability_complete"] is False and len(r["remaining_reference_assumptions"]) > 20,
      "three selected claims do not hide the remaining reference assumptions")
check(r["release_authorized"] is False and r["physical_validation"] == "NOT_DEMONSTRATED",
      "semantic review cannot authorize release or physical validation")

vv = V.run({name: values[name] for name in C.REQUIRED_EXECUTABLE_FIELDS},
           input_evidence={name: r["shared_configuration"]["input_provenance"][name]
                           ["source_ref"] for name in C.REQUIRED_EXECUTABLE_FIELDS},
           run_real_solvers=False)
check(vv["configuration"]["values"]["rotor_r_m"] == 0.06 and
      vv["physical_validation"] == "NOT_DEMONSTRATED",
      "the resolved version feeds the shared V&V contract without changing its boundary")

with tempfile.TemporaryDirectory(prefix="engineai_crfce_config_") as directory:
    first_artifacts = C.write_bundle(r, directory)
    first_resolution_path = next(
        Path(row["path"]) for row in first_artifacts
        if Path(row["path"]).name == "CRFCE_configuration_resolution.json")
    first_resolution_bytes = first_resolution_path.read_bytes()
    artifacts = C.write_bundle(r, directory)
    check(len(artifacts) == 5 and all(Path(row["path"]).is_file() and row["sha256"]
                                      for row in artifacts),
          "resolution, shared config, requirement matrix, review report and manifest are hashed files")
    manifest_row = next((row for row in artifacts
                         if Path(row["path"]).name == "CRFCE_artifact_manifest.json"), None)
    check(manifest_row is not None,
          "the CRFCE resolution output bundle emits an artifact manifest")
    if manifest_row is not None:
        manifest = json.loads(Path(manifest_row["path"]).read_text(encoding="utf-8"))
        payload_rows = [row for row in artifacts
                        if Path(row["path"]).name != "CRFCE_artifact_manifest.json"]
        check(manifest.get("resolution_hash") == r["resolution_hash"] and
              len(manifest.get("artifacts", [])) == 4 and
              all((Path(manifest_row["path"]).parent / item["path"]).is_file() and
                  (Path(manifest_row["path"]).parent / item["path"]).stat().st_size == item["bytes"] and
                  C._file_hash(Path(manifest_row["path"]).parent / item["path"]) == item["sha256"]
                  for item in manifest["artifacts"]),
              "the manifest binds the resolution digest and all four payload hashes/sizes")
    first_output_dirs = {Path(row["path"]).parent for row in first_artifacts}
    second_output_dirs = {Path(row["path"]).parent for row in artifacts}
    check(first_output_dirs.isdisjoint(second_output_dirs) and
          first_resolution_path.read_bytes() == first_resolution_bytes,
          "repeated CRFCE reviews use separate directories and preserve prior resolution bytes")
    loaded = json.loads(Path(next(row["path"] for row in artifacts
                                  if Path(row["path"]).name ==
                                  "CRFCE_configuration_resolution.json"))
                        .read_text(encoding="utf-8"))
    check(loaded["resolution_hash"] == r["resolution_hash"],
          "the written resolution preserves its content identity")

check(C.wants_configuration_resolution("Resolve CRFCE source configuration conflicts"),
      "explicit CRFCE configuration resolution intent is recognized")
check(not C.wants_configuration_resolution("What is CRFCE?"),
      "ordinary CRFCE chat is not hijacked")

tampered_resolution = dict(r)
tampered_resolution["review_ref"] = str(r["review_ref"]) + ":tampered"
with tempfile.TemporaryDirectory(prefix="engineai_crfce_tampered_bundle_") as directory:
    try:
        C.write_bundle(tampered_resolution, directory)
    except ValueError as exc:
        check("resolution_hash does not match" in str(exc),
              "a modified resolution cannot reuse a stale content hash")
    else:
        check(False, "a modified resolution with a stale content hash was written")
    check(not list(Path(directory).iterdir()),
          "hash-mismatched output is refused before creating a bundle")

print("crfce_configuration_resolution_conformance: PASS")
