#!/usr/bin/env python3
"""Resolve CRFCE document claims into a versioned virtual-analysis configuration.

Extraction is not authority.  Repetition is not independence, and two dimensions from
different design versions must never be averaged into one fictional machine.  This
module therefore proposes version candidates, retains all source locators, and requires
an explicit review decision before compatible claims become inputs to
``crfce_coupled_vv``.

The result authorizes virtual analysis only.  It cannot validate a source, calibrate an
instrument, authorize a design release, or demonstrate physical performance.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import secrets
from typing import Any

import crfce_coupled_vv as V


SCHEMA = "engineai.crfce-configuration-resolution.v4"
ANALYSIS_SCHEMA = "engineai.crfce-configuration-candidates.v1"
SOURCE_VERSION_BINDING_SCHEMA = "engineai.crfce-source-version-binding.v1"
SOURCE_CORPUS_REPORT_SCHEMA = "engineai.crfce-source-corpus.v1"
SOURCE_CORPUS_MANIFEST_SCHEMA = "engineai.crfce-source-manifest.v1"
SOURCE_CORPUS_INTEGRITY_STANDING = (
    "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY"
)
ARTIFACT_MANIFEST_SCHEMA = "engineai.crfce-configuration-artifact-manifest.v1"
REQUIRED_EXECUTABLE_FIELDS = ("rotor_r_m", "L_stack_m", "T_K")

# deterministic, unit-explicit mappings; unmapped claims stay research requirements
# rather than silently becoming a similarly named model input.
CLAIM_TO_INPUT = {
    "rotor_radius": {"field": "rotor_r_m", "unit": "mm", "factor": 1e-3,
                     "output_unit": "m"},
    "rotor_stack_length": {"field": "L_stack_m", "unit": "mm", "factor": 1e-3,
                          "output_unit": "m"},
    "operating_temperature": {"field": "T_K", "unit": "K", "factor": 1.0,
                              "output_unit": "K"},
}

TARGET_CLAIMS = {
    "continuous_mechanical_power": "virtual/bench output target, not an input",
    "continuous_torque": "virtual/bench output target, not an input",
    "total_mass": "mass-budget target; full BOM model missing",
    "hts_ac_loss": "loss-budget target; model applicability must be reviewed",
    "dc_bus_voltage": "electrical architecture requirement; inverter model missing",
    "rebco_tape_width": "winding/manufacturing requirement; winding model missing",
    "lamination_thickness": "manufacturing/loss requirement; lamination model missing",
    "quench_trip_temperature": "protection requirement; quench/control model missing",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_corpus_receipt(value: Any) -> str:
    if (type(value) is not str or len(value) != 64 or value != value.lower() or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("source_corpus_receipt must be a lowercase SHA-256 digest")
    return value


def _validated_source_corpus_report(value: Any, claim_ledger: Any,
                                    conflict_ledger: Any) -> str | None:
    """Recompute a corpus report receipt and bind the resolver inputs to its rows.

    This verifies report self-consistency only. It cannot establish that the report's
    source bytes, extracted claims, researcher decisions, or external source origins are
    authentic; those remain separate review evidence.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("source_corpus_report must be a structured corpus report")
    if value.get("schema") != SOURCE_CORPUS_REPORT_SCHEMA:
        raise ValueError("source_corpus_report has an unsupported schema")
    receipt = _validate_corpus_receipt(value.get("receipt"))
    body = {key: item for key, item in value.items() if key != "receipt"}
    if _hash(body) != receipt:
        raise ValueError("source_corpus_report receipt does not match its report contents")
    if value.get("verdict") != "CORPUS_INDEXED":
        raise ValueError("source_corpus_report must be a complete CORPUS_INDEXED report")

    manifest = value.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("schema") != SOURCE_CORPUS_MANIFEST_SCHEMA:
        raise ValueError("source_corpus_report has no supported source manifest")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source_corpus_report manifest must contain source files")
    if (type(manifest.get("source_count")) is not int or
            manifest["source_count"] != len(sources)):
        raise ValueError("source_corpus_report manifest source_count does not match sources")
    if manifest.get("ingestion_failures") != []:
        raise ValueError("source_corpus_report with ingestion failures cannot bind a configuration")

    source_pairs: set[tuple[str, str]] = set()
    source_ids: set[str] = set()
    source_bytes = 0
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source_corpus_report manifest source must be an object")
        file_id = source.get("file_id")
        if type(file_id) is not str or not file_id.strip() or file_id in source_ids:
            raise ValueError("source_corpus_report needs unique stable source file_id values")
        digest = _validate_corpus_receipt(source.get("sha256"))
        size = source.get("bytes")
        if type(size) is not int or size < 0:
            raise ValueError("source_corpus_report source bytes must be a nonnegative integer")
        source_ids.add(file_id)
        source_pairs.add((file_id, digest))
        source_bytes += size
    if type(manifest.get("source_bytes")) is not int or manifest["source_bytes"] != source_bytes:
        raise ValueError("source_corpus_report manifest source_bytes does not match sources")

    evidence_boundary = value.get("evidence_boundary")
    if (not isinstance(evidence_boundary, dict) or
            evidence_boundary.get("release_authorized") is not False or
            evidence_boundary.get("physical_validation") != "NOT_DEMONSTRATED"):
        raise ValueError("source_corpus_report cannot promote release or physical-validation standing")
    report_claims = value.get("claims")
    if not isinstance(report_claims, dict):
        raise ValueError("source_corpus_report has no claims record")
    report_claim_rows = _rows(report_claims, "claim_ledger")
    report_conflict_rows = _rows(report_claims, "candidate_conflicts")
    import project_research
    for claim in report_claim_rows:
        if claim.get("claim_id") != project_research.claim_id_for(claim):
            raise ValueError("source_corpus_report claim_id does not match claim contents")
    recomputed_claim_analysis = project_research.claim_analysis_from_ledger(report_claim_rows)
    for key in ("candidate_conflicts", "repeated_claims", "value_variants", "note"):
        if _hash(report_claims.get(key)) != _hash(recomputed_claim_analysis[key]):
            raise ValueError(f"source_corpus_report {key} is inconsistent with its claim ledger")
    supplied_claim_rows = _rows(claim_ledger, "claims")
    supplied_conflict_rows = _rows(conflict_ledger, "candidate_conflicts")
    if _hash(report_claim_rows) != _hash(supplied_claim_rows):
        raise ValueError("claim ledger does not match source_corpus_report")
    if _hash(report_conflict_rows) != _hash(supplied_conflict_rows):
        raise ValueError("candidate conflict ledger does not match source_corpus_report")
    for claim in report_claim_rows:
        source = claim.get("source")
        file_id = source.get("file_id") if isinstance(source, dict) else None
        digest = source.get("sha256") if isinstance(source, dict) else None
        if type(file_id) is not str or not file_id.strip() or type(digest) is not str:
            raise ValueError("every corpus claim needs a stable file_id and source hash")
        _validate_corpus_receipt(digest)
        if (file_id, digest) not in source_pairs:
            raise ValueError("corpus claim source hash is absent from the source manifest")
        member_digest = source.get("member_sha256")
        if member_digest is not None:
            try:
                _validate_corpus_receipt(member_digest)
            except ValueError as exc:
                raise ValueError(
                    "corpus claim member_sha256 must be a lowercase SHA-256 digest"
                ) from exc
    return receipt


def _rows(value: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get(key)
    if not isinstance(value, list):
        raise ValueError(f"expected a {key} array")
    if any(not isinstance(row, dict) for row in value):
        raise ValueError(f"every {key} row must be an object")
    return value


def _validate_claims(value: Any) -> list[dict[str, Any]]:
    rows = _rows(value, "claims")
    seen: set[str] = set()
    clean = []
    for row in rows:
        cid = str(row.get("claim_id") or "")
        if len(cid) != 64 or any(ch not in "0123456789abcdef" for ch in cid):
            raise ValueError("every claim needs a 64-character lowercase content ID")
        if cid in seen:
            raise ValueError(f"duplicate claim_id {cid}")
        seen.add(cid)
        name = str(row.get("claim") or "")
        unit = str(row.get("normalized_unit") or "")
        value = row.get("normalized_value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"claim {cid} needs a finite normalized value")
        source = row.get("source")
        if not isinstance(source, dict) or not source.get("sha256") or not source.get("locator"):
            raise ValueError(f"claim {cid} has no stable source hash/locator")
        clean.append({**row, "claim_id": cid, "claim": name,
                      "normalized_unit": unit, "normalized_value": float(value)})
    return clean


def _validate_conflicts(value: Any, claim_ids: set[str]) -> list[dict[str, Any]]:
    rows = _rows(value, "candidate_conflicts")
    for row in rows:
        ids = row.get("claim_ids")
        if not isinstance(ids, list) or len(ids) < 2 or not set(ids).issubset(claim_ids):
            raise ValueError("candidate conflict references missing claim IDs")
        if row.get("standing") != "CANDIDATE_CONFLICT_REQUIRES_SEMANTIC_REVIEW":
            raise ValueError("candidate conflict lost its review-required standing")
    return rows


def _group(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[float, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["normalized_value"], row["normalized_unit"])
        groups.setdefault(key, []).append(row)
    out = []
    for (value, unit), members in sorted(groups.items()):
        out.append({
            "normalized_value": value, "normalized_unit": unit,
            "claim_ids": sorted(row["claim_id"] for row in members),
            "sources": [{"sha256": row["source"]["sha256"],
                         "file_id": row["source"].get("file_id"),
                         "locator": row["source"]["locator"]} for row in members],
            "repetition_count": len(members),
            "standing": "UNVERIFIED_REPEATED_VALUE_NOT_INDEPENDENT_VALIDATION",
        })
    return out


def analyse(claim_ledger: Any, conflict_ledger: Any) -> dict[str, Any]:
    claims = _validate_claims(claim_ledger)
    claim_ids = {row["claim_id"] for row in claims}
    conflicts = _validate_conflicts(conflict_ledger, claim_ids)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in claims:
        by_name.setdefault(row["claim"], []).append(row)

    executable = []
    for claim, mapping in sorted(CLAIM_TO_INPUT.items()):
        rows = by_name.get(claim, [])
        candidates = _group(rows)
        unit_ok = all(row["normalized_unit"] == mapping["unit"] for row in rows)
        executable.append({
            "claim": claim, "input_field": mapping["field"],
            "required_unit": mapping["unit"], "output_unit": mapping["output_unit"],
            "conversion_factor": mapping["factor"], "unit_contract_ok": unit_ok,
            "candidates": candidates,
            "standing": ("SEMANTIC_REVIEW_REQUIRED" if len(candidates) > 1 else
                         "SELECTION_REQUIRED" if candidates else "SOURCE_VALUE_MISSING"),
        })

    conflict_variants = []
    for conflict in conflicts:
        relevant = [row for row in claims if row["claim_id"] in set(conflict["claim_ids"])]
        mapped = CLAIM_TO_INPUT.get(str(conflict.get("claim") or ""))
        variants = []
        for group in _group(relevant):
            variant = {**group}
            if mapped:
                variant["input_field"] = mapped["field"]
                variant["converted_value"] = group["normalized_value"] * mapped["factor"]
                variant["converted_unit"] = mapped["output_unit"]
            variants.append(variant)
        conflict_variants.append({
            "claim": conflict.get("claim"), "standing": conflict.get("standing"),
            "variants": variants,
            "rule": "choose one reviewed design version; averaging/merging is forbidden",
        })

    requirements = []
    for claim, use in sorted(TARGET_CLAIMS.items()):
        for group in _group(by_name.get(claim, [])):
            requirements.append({
                "claim": claim, "value": group["normalized_value"],
                "unit": group["normalized_unit"], "claim_ids": group["claim_ids"],
                "intended_use": use,
                "standing": "UNVERIFIED_REQUIREMENT_CANDIDATE_REVIEW_REQUIRED",
            })

    result = {
        "schema": ANALYSIS_SCHEMA,
        "verdict": "SEMANTIC_REVIEW_REQUIRED",
        "claim_count": len(claims),
        "executable_input_candidates": executable,
        "conflict_variants": conflict_variants,
        "research_requirement_candidates": requirements,
        "unmapped_claims": sorted(set(by_name) - set(CLAIM_TO_INPUT) - set(TARGET_CLAIMS)),
        "automatic_selection_permitted": False,
        "configuration_ready_for_virtual_analysis": False,
        "release_authorized": False,
        "physical_validation": "NOT_DEMONSTRATED",
        "boundary": ("Extracted claims are unverified evidence. Equivalent repeated text is not "
                     "independent validation, and conflicting design versions are never merged."),
    }
    result["analysis_hash"] = _hash(result)
    return result


def _selection_source(row: dict[str, Any]) -> str:
    source = row["source"]
    return (f"claim:{row['claim_id']} file-id:{str(source.get('file_id') or '')} "
            f"source-sha256:{source['sha256']} "
            f"locator:{source['locator']}")


def _source_version_binding(binding: Any, *, variant: str, review_ref: str,
                            selections: dict[str, Any], selected_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate and retain the reviewer's explicit claim-to-source-version join.

    This is an external review assertion, not machine-verifiable proof that the
    selected documents describe one physical design. Exact claim IDs and source
    hashes make the assertion auditable and keep the join inside the resolution hash.
    """
    if not isinstance(binding, dict):
        raise ValueError("source_version_binding must be an object")
    required = {"schema", "configuration_variant", "review_ref", "rationale",
                "selected_claim_ids", "sources"}
    if set(binding) != required:
        raise ValueError("source_version_binding must contain exactly the version-join fields")
    if binding.get("schema") != SOURCE_VERSION_BINDING_SCHEMA:
        raise ValueError("source_version_binding schema is unsupported")
    if binding.get("configuration_variant") != variant:
        raise ValueError("source_version_binding variant does not match the decision")
    if binding.get("review_ref") != review_ref:
        raise ValueError("source_version_binding review_ref does not match the decision")
    rationale = binding.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("source_version_binding needs a nonempty join rationale")

    selected_claim_ids = {field: str(selections[field]) for field in REQUIRED_EXECUTABLE_FIELDS}
    if binding.get("selected_claim_ids") != selected_claim_ids:
        raise ValueError("source_version_binding claim IDs do not match the selected inputs")

    expected_sources: set[tuple[str, str]] = set()
    for row in selected_rows:
        source = row["source"]
        file_id = str(source.get("file_id") or "").strip()
        digest = str(source.get("sha256") or "")
        if not file_id:
            raise ValueError("selected source claim needs a stable file_id for version binding")
        if (len(digest) != 64 or digest != digest.lower() or
                any(character not in "0123456789abcdef" for character in digest)):
            raise ValueError("selected source claim needs a lowercase SHA-256 source digest")
        expected_sources.add((file_id, digest))

    sources = binding.get("sources")
    if not isinstance(sources, list):
        raise ValueError("source_version_binding.sources must be an array")
    provided_sources: list[tuple[str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"file_id", "sha256"}:
            raise ValueError("each bound source must contain exactly file_id and sha256")
        file_id = str(source.get("file_id") or "").strip()
        digest = str(source.get("sha256") or "")
        if not file_id or len(digest) != 64 or digest != digest.lower() or any(
                character not in "0123456789abcdef" for character in digest):
            raise ValueError("each bound source needs a file_id and lowercase SHA-256 digest")
        provided_sources.append((file_id, digest))
    if len(set(provided_sources)) != len(provided_sources):
        raise ValueError("source_version_binding contains duplicate source documents")
    if set(provided_sources) != expected_sources:
        raise ValueError("source_version_binding source set does not exactly match selected claims")

    return {
        "schema": SOURCE_VERSION_BINDING_SCHEMA,
        "configuration_variant": variant,
        "review_ref": review_ref,
        "rationale": rationale.strip(),
        "selected_claim_ids": selected_claim_ids,
        "sources": [{"file_id": file_id, "sha256": digest}
                    for file_id, digest in sorted(expected_sources)],
        "standing": "EXTERNAL_REVIEW_ASSERTION_NOT_INDEPENDENTLY_VERIFIED",
    }


def resolve(claim_ledger: Any, conflict_ledger: Any,
            decision: dict[str, Any] | None, *,
            source_corpus_report: dict[str, Any] | None = None,
            source_corpus_receipt: str | None = None) -> dict[str, Any]:
    if source_corpus_receipt is not None:
        raise ValueError(
            "bare source_corpus_receipt is no longer accepted; provide source_corpus_report"
        )
    corpus_receipt = _validated_source_corpus_report(
        source_corpus_report, claim_ledger, conflict_ledger)
    analysis = analyse(claim_ledger, conflict_ledger)
    claims = _validate_claims(claim_ledger)
    conflicts = _validate_conflicts(conflict_ledger, {row["claim_id"] for row in claims})
    by_id = {row["claim_id"]: row for row in claims}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in claims:
        by_name.setdefault(row["claim"], []).append(row)
    intrinsic_conflicts = {
        claim for claim, mapping in CLAIM_TO_INPUT.items()
        if len(_group([row for row in by_name.get(claim, [])
                       if row["normalized_unit"] == mapping["unit"]])) > 1
    }
    decision = decision or {}
    if not isinstance(decision, dict):
        raise TypeError("decision must be an object")
    selections = decision.get("selections") or {}
    if not isinstance(selections, dict):
        raise TypeError("decision.selections must be an object keyed by CRFCE input field")
    review_ref = str(decision.get("review_ref") or "").strip()
    variant = str(decision.get("configuration_variant") or "").strip()
    source_binding = decision.get("source_version_binding")
    missing_source_binding = not isinstance(source_binding, dict) or not source_binding
    missing_source_corpus_report = corpus_receipt is None
    missing = [field for field in REQUIRED_EXECUTABLE_FIELDS if field not in selections]
    if missing or not review_ref or not variant or missing_source_binding or missing_source_corpus_report:
        result = {
            "schema": SCHEMA, "verdict": "CONFIGURATION_WITHHELD_REVIEW_INCOMPLETE",
            "analysis": analysis, "missing_required_selections": missing,
            "missing_review_ref": not bool(review_ref),
            "missing_configuration_variant": not bool(variant),
            "missing_source_version_binding": missing_source_binding,
            "missing_source_corpus_report": missing_source_corpus_report,
            "configuration_ready_for_virtual_analysis": False,
            "release_authorized": False, "physical_validation": "NOT_DEMONSTRATED",
            "boundary": ("An exact source-version binding for every selected claim and a "
                         "complete structured source-corpus report are required before this "
                         "can become a virtual-analysis input set. The report receipt is "
                         "recomputed and its claim/conflict arrays are bound to the resolver "
                         "inputs; this checks content integrity, not source authenticity, "
                         "researcher judgment, release authorization, or physical validation."),
        }
        if corpus_receipt is not None:
            result["source_corpus_receipt"] = corpus_receipt
            result["source_corpus_integrity"] = SOURCE_CORPUS_INTEGRITY_STANDING
        result["resolution_hash"] = _hash(result)
        return result

    unknown_fields = sorted(set(selections) - set(REQUIRED_EXECUTABLE_FIELDS))
    if unknown_fields:
        raise ValueError("unsupported configuration selection field(s): " + ", ".join(unknown_fields))
    conflict_resolutions = decision.get("conflict_resolutions") or {}
    if not isinstance(conflict_resolutions, dict):
        raise TypeError("decision.conflict_resolutions must be an object")

    design: dict[str, float] = {}
    evidence: dict[str, dict[str, str]] = {}
    selected_rows = []
    for field in REQUIRED_EXECUTABLE_FIELDS:
        cid = str(selections[field])
        if cid not in by_id:
            raise ValueError(f"selected claim {cid!r} does not exist")
        row = by_id[cid]
        mapping = CLAIM_TO_INPUT.get(row["claim"])
        if not mapping or mapping["field"] != field:
            raise ValueError(f"claim {cid} cannot populate {field}")
        if row["normalized_unit"] != mapping["unit"]:
            raise ValueError(f"claim {cid} unit {row['normalized_unit']} cannot populate {field}")
        if row["claim"] in intrinsic_conflicts:
            resolution = conflict_resolutions.get(row["claim"])
            if not isinstance(resolution, dict):
                raise ValueError(f"conflicting claim {row['claim']} needs an explicit resolution")
            if str(resolution.get("selected_claim_id") or "") != cid:
                raise ValueError(f"conflict resolution for {row['claim']} selects a different claim")
            if not str(resolution.get("review_ref") or "").strip() or not str(resolution.get("rationale") or "").strip():
                raise ValueError(f"conflict resolution for {row['claim']} needs review_ref and rationale")
        converted = row["normalized_value"] * mapping["factor"]
        design[field] = converted
        evidence[field] = {
            "source_ref": _selection_source(row),
            "note": f"selected for variant {variant} under review decision {review_ref}",
        }
        selected_rows.append({
            "input_field": field, "value": converted, "unit": mapping["output_unit"],
            "claim": row["claim"], "claim_id": cid, "source": row["source"],
            "standing": "REVIEW_SELECTED_UNVERIFIED_SOURCE_INPUT",
        })

    source_binding_record = _source_version_binding(
        source_binding, variant=variant, review_ref=review_ref,
        selections=selections, selected_rows=selected_rows)

    shared = V.seal_configuration(design, evidence)
    result = {
        "schema": SCHEMA,
        "verdict": "VERSIONED_CONFIGURATION_READY_FOR_VIRTUAL_ANALYSIS",
        "configuration_variant": variant,
        "review_ref": review_ref,
        "review_decision": decision,
        "review_decision_hash": _hash(decision),
        "decision_authority": "EXTERNAL_REVIEW_REFERENCE_ONLY_NOT_ENGINEAI_RELEASE",
        "analysis": analysis,
        "selected_claims": selected_rows,
        "source_version_binding": source_binding_record,
        "source_corpus_receipt": corpus_receipt,
        "source_corpus_integrity": SOURCE_CORPUS_INTEGRITY_STANDING,
        "conflict_resolutions": conflict_resolutions,
        "shared_configuration": shared,
        "configuration_ready_for_virtual_analysis": True,
        "input_traceability_complete": shared["traceability"]["complete"],
        "remaining_reference_assumptions": [
            name for name, row in shared["input_provenance"].items()
            if row["standing"] == "REFERENCE_ASSUMPTION"
        ],
        "requirement_candidates": analysis["research_requirement_candidates"],
        "release_authorized": False,
        "design_release_status": "NOT_AUTHORIZED",
        "physical_validation": "NOT_DEMONSTRATED",
        "boundary": ("Ready means only that the selected source claims can be run as a "
                     "versioned virtual-analysis input set. The claims remain unverified; "
                     "the source-corpus report receipt is recomputed and its claim/conflict "
                     "arrays are matched to the resolver inputs, but source authenticity and "
                     "researcher judgment remain unverified; most model inputs remain explicit "
                     "reference assumptions."),
    }
    result["resolution_hash"] = _hash(result)
    return result


def write_bundle(result: dict[str, Any], outdir: str | Path) -> list[dict[str, Any]]:
    resolution_hash = result.get("resolution_hash")
    if (type(resolution_hash) is not str or len(resolution_hash) != 64 or
            resolution_hash != resolution_hash.lower() or
            any(character not in "0123456789abcdef" for character in resolution_hash)):
        raise ValueError("resolution_hash must be a lowercase SHA-256 digest")
    if _hash({key: value for key, value in result.items()
              if key != "resolution_hash"}) != resolution_hash:
        raise ValueError("resolution_hash does not match the output record")

    root = Path(outdir)
    root.mkdir(parents=True, exist_ok=True)
    resolution_root = root / resolution_hash
    resolution_root.mkdir(exist_ok=True)
    run_id = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") +
              "-" + secrets.token_hex(8))
    run_dir = resolution_root / run_id
    # Never reuse an output directory, even for a repeated identical resolution.
    run_dir.mkdir(exist_ok=False)
    files: list[Path] = []
    record = run_dir / "CRFCE_configuration_resolution.json"
    with record.open("x", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False) + "\n")
    files.append(record)

    analysis = result.get("analysis") or {}
    if result.get("shared_configuration"):
        shared = run_dir / "CRFCE_shared_configuration.json"
        with shared.open("x", encoding="utf-8", newline="") as stream:
            stream.write(json.dumps(result["shared_configuration"], indent=2, sort_keys=True,
                                    ensure_ascii=False, allow_nan=False) + "\n")
        files.append(shared)
    requirements = run_dir / "CRFCE_requirement_candidates.csv"
    with requirements.open("x", newline="", encoding="utf-8") as stream:
        fields = ("claim", "value", "unit", "intended_use", "standing", "claim_ids")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        rows = result.get("requirement_candidates") or analysis.get("research_requirement_candidates") or []
        for row in rows:
            writer.writerow({**{field: row.get(field) for field in fields},
                             "claim_ids": ";".join(row.get("claim_ids") or [])})
    files.append(requirements)

    report = run_dir / "CRFCE_CONFIGURATION_REVIEW.md"
    lines = ["# CRFCE source-to-configuration review", "",
             f"- Verdict: **{result['verdict']}**",
             f"- Physical validation: **{result['physical_validation']}**", ""]
    if result.get("source_corpus_receipt"):
        lines += ["## Source corpus binding", "",
                  f"- Corpus receipt: `{result['source_corpus_receipt']}`",
                  f"- Integrity standing: `{result.get('source_corpus_integrity')}`",
                  "- The resolver recomputes the receipt over the structured report and requires its claim/conflict arrays to match the resolved inputs. This verifies report content integrity only; it does not authenticate source bytes, source origin, extracted claims, or reviewer judgment.", ""]
    if result.get("missing_source_version_binding"):
        lines += ["## Source-version binding required", "",
                  "No exact external review assertion binds the selected claim IDs and source hashes to one configuration variant; virtual-analysis configuration is withheld.", ""]
    if result.get("missing_source_corpus_report"):
        lines += ["## Source-corpus report required", "",
                  "No complete structured source-corpus report was provided for receipt recomputation and claim/conflict binding; virtual-analysis configuration is withheld.", ""]
    if result.get("shared_configuration"):
        lines += [f"- Variant: `{result['configuration_variant']}`",
                  f"- Shared configuration: `{result['shared_configuration']['configuration_hash']}`",
                  f"- Remaining reference assumptions: {len(result['remaining_reference_assumptions'])}", ""]
        binding = result.get("source_version_binding") or {}
        lines += ["## Source-version binding", "",
                  f"- Review reference: `{binding.get('review_ref', 'missing')}`",
                  f"- Bound source documents: {len(binding.get('sources') or [])}",
                  f"- Standing: `{binding.get('standing', 'NOT_BOUND')}`",
                  "- This is an external reviewer assertion; EngineAI does not independently verify that the sources describe one physical machine.", ""]
    variants = (analysis.get("conflict_variants") or
                (result.get("analysis") or {}).get("conflict_variants") or [])
    lines += ["## Conflict variants", ""]
    for item in variants:
        lines.append(f"- {item['claim']}: {len(item['variants'])} version candidate(s); automatic merging forbidden")
    lines += ["", "## Boundary", "", str(result.get("boundary") or analysis.get("boundary") or ""), ""]
    with report.open("x", encoding="utf-8", newline="") as stream:
        stream.write("\n".join(lines))
    files.append(report)

    manifest = {
        "schema": ARTIFACT_MANIFEST_SCHEMA,
        "standing": "OUTPUT_BYTES_HASHED_NOT_SOURCE_AUTHENTICITY_OR_SCIENTIFIC_VALIDATION",
        "resolution_hash": resolution_hash,
        "source_corpus_receipt": result.get("source_corpus_receipt"),
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_excludes_itself": True,
        "artifacts": [{"path": path.name, "bytes": path.stat().st_size,
                       "sha256": _file_hash(path)} for path in files],
    }
    manifest_path = run_dir / "CRFCE_artifact_manifest.json"
    with manifest_path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False) + "\n")
    files.append(manifest_path)
    return [{"path": str(path), "bytes": path.stat().st_size,
             "sha256": _file_hash(path)} for path in files]


def chat_answer(claim_ledger: Any, conflict_ledger: Any,
                decision: dict[str, Any] | None = None, *,
                outdir: str | Path = "out/crfce-configuration",
                source_corpus_report: dict[str, Any] | None = None,
                source_corpus_receipt: str | None = None) -> dict[str, Any]:
    """Return one Studio/worker-shaped result without promoting source claims.

    A completed job may still withhold an executable configuration.  That distinction is
    intentional: successful corpus analysis is not the same as a reviewed design-version
    decision, and neither condition authorizes a released design.
    """
    result = resolve(claim_ledger, conflict_ledger, decision,
                     source_corpus_report=source_corpus_report,
                     source_corpus_receipt=source_corpus_receipt)
    artifacts = write_bundle(result, outdir)
    ready = bool(result.get("configuration_ready_for_virtual_analysis"))
    if ready:
        config_hash = result["shared_configuration"]["configuration_hash"]
        answer = (
            "**CRFCE source configuration resolved for virtual analysis**\n\n"
            f"- Variant: `{result['configuration_variant']}`\n"
            f"- Configuration: `{config_hash[:16]}`\n"
            f"- Remaining reference assumptions: "
            f"{len(result['remaining_reference_assumptions'])}\n\n"
            "The selected claim IDs and exact source hashes are bound by an explicit external review assertion; EngineAI does not independently verify that those sources describe one physical machine.\n\n"
            f"The content-addressed source-corpus report receipt is recomputed by the resolver "
            f"({result.get('source_corpus_integrity')}); this is not source authenticity or "
            "researcher acceptance. The selected claims remain source-linked but unverified. Physical validation "
            "is NOT_DEMONSTRATED and design release is NOT_AUTHORIZED."
        )
    else:
        analysis = result.get("analysis") or {}
        conflicts = analysis.get("conflict_variants") or []
        missing_items = list(result.get("missing_required_selections") or [])
        if result.get("missing_source_version_binding"):
            missing_items.append("source-version binding")
        if result.get("missing_source_corpus_report"):
            missing_items.append("source-corpus report")
        if result.get("missing_review_ref") or result.get("missing_configuration_variant"):
            missing_items.append("review metadata")
        answer = (
            "**CRFCE source-to-configuration review completed; execution withheld**\n\n"
            f"- Extracted claims reviewed: {analysis.get('claim_count', 0)}\n"
            f"- Design-version conflicts: {len(conflicts)}\n"
            f"- Missing required selections: "
            f"{', '.join(missing_items) or 'unspecified decision fields'}\n\n"
            "A structured source-version binding is also required before claims form one virtual-analysis input set. EngineAI did not average conflicting versions or invent missing authority. "
            "Provide an explicit reviewed decision to create a versioned virtual-analysis "
            "configuration. Physical validation remains NOT_DEMONSTRATED."
        )
    if result.get("source_corpus_receipt") is not None:
        answer += (f"\n\n- Source corpus receipt: `{result['source_corpus_receipt']}` "
                   f"(report content rehashed; standing: {result.get('source_corpus_integrity')})")
    receipt = (result.get("resolution_hash") or
               (result.get("analysis") or {}).get("analysis_hash"))
    return {
        "ok": True, "released": False, "verified": False,
        "basis": "CRFCE_CONFIGURATION_RESOLUTION",
        "release_authorized": False, "design_release_status": "NOT_AUTHORIZED",
        "physical_validation": "NOT_DEMONSTRATED",
        "configuration_ready_for_virtual_analysis": ready,
        "source_corpus_receipt": result.get("source_corpus_receipt"),
        "source_corpus_integrity": result.get("source_corpus_integrity"),
        "receipt_digest": receipt,
        "answer": answer, "governed": result, "actions": artifacts,
        "note": result.get("boundary") or (result.get("analysis") or {}).get("boundary"),
    }


def wants_configuration_resolution(message: str) -> bool:
    text = (message or "").casefold()
    return "crfce" in text and any(term in text for term in (
        "resolve configuration", "source configuration", "claims to inputs",
        "design version", "resolve contradiction", "resolve conflict",
    ))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("claim_ledger")
    parser.add_argument("conflict_ledger")
    parser.add_argument("--decision")
    parser.add_argument("--source-corpus-report",
                        help="JSON report emitted by the CRFCE source-corpus builder")
    parser.add_argument("--source-corpus-receipt",
                        help="deprecated bare receipt (refused; supply --source-corpus-report)")
    parser.add_argument("--outdir", default="out/crfce-configuration")
    args = parser.parse_args()
    claims = json.loads(Path(args.claim_ledger).read_text(encoding="utf-8"))
    conflicts = json.loads(Path(args.conflict_ledger).read_text(encoding="utf-8"))
    decision = (json.loads(Path(args.decision).read_text(encoding="utf-8"))
                if args.decision else None)
    source_report = (json.loads(Path(args.source_corpus_report).read_text(encoding="utf-8"))
                     if args.source_corpus_report else None)
    result = resolve(claims, conflicts, decision,
                     source_corpus_report=source_report,
                     source_corpus_receipt=args.source_corpus_receipt)
    result["artifacts"] = write_bundle(result, args.outdir)
    print(json.dumps(result, indent=2, sort_keys=True))
