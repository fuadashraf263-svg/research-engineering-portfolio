#!/usr/bin/env python3
"""Content-addressed CRFCE source corpus, scope quarantine and claim ledger.

This module turns already-bounded EngineAI ingestion records into reviewable research
evidence.  It does not decide that an extracted sentence is true, does not convert a plot
pixel into a measurement, and cannot authorize design release or physical validation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable
import unicodedata

import project_ingestion
import project_research


SCHEMA = "engineai.crfce-source-corpus.v1"
MANIFEST_SCHEMA = "engineai.crfce-source-manifest.v1"

_TARGET = (
    "crfce", "cryogenic rf", "rf-quiet", "rf quiet", "rebco",
    "superconduct", "dc-biased reluctance", "cryocooler", "quench",
)
_FOREIGN = (
    "phoenix", "wing", "airframe", "airspeed", "aeroelastic", "flutter",
    "distributed propulsion", "thermo-aeroelastic", "aircraft concept",
)
_ARCHIVE_MEMBER = re.compile(r"^archive member (?P<name>.+?) / ")


def _stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _signals(text: str, terms: Iterable[str]) -> list[str]:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return sorted({term for term in terms if re.search(
        r"(?<![a-z0-9])" + re.escape(term.casefold()) + r"(?![a-z0-9])", folded
    )})


def _record_text(record: dict[str, Any]) -> str:
    fragments = [str(record.get("name") or "")]
    structure = record.get("structure") or {}
    fragments.append(str(structure.get("ocr_excerpt") or ""))
    for member in structure.get("members") or []:
        fragments.append(str(member.get("name") or ""))
        fragments.append(str((member.get("structure") or {}).get("ocr_excerpt") or ""))
    for fact in record.get("facts") or []:
        source = fact.get("source") or {}
        fragments.extend((str(fact.get("name") or ""), str(source.get("locator") or ""),
                          str(source.get("excerpt") or "")))
    return " ".join(fragments)


def scope_hint(path: str | Path, ext: str, record: dict[str, Any]) -> dict[str, Any]:
    """Inspect page/paragraph text only to create a bounded scope index.

    Raw text is not retained.  The result records only matched scope terms and locators,
    allowing mixed merged documents to be partitioned before their numeric facts enter the
    CRFCE claim ledger.
    """
    source = Path(path)
    sections: list[tuple[str, str]] = []
    try:
        if ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(source))
            sections = [(f"page {index + 1}", page.extract_text() or "")
                        for index, page in enumerate(reader.pages)]
        elif ext == "docx":
            sections, _ = project_ingestion._docx_sections(source)
        elif ext in {"txt", "md", "py", "c", "cpp", "js", "rs"}:
            sections = [("text", source.read_text(encoding="utf-8", errors="replace"))]
        elif ext == "zip":
            # The archive parser already verified path, encryption, ratio and member bounds.
            # Member names plus the source-linked fact excerpts are sufficient to quarantine
            # the supplied PHOENIX bundle without extracting it into the workspace.
            sections = [("archive index", _record_text(record))]
        else:
            sections = [("source metadata", _record_text(record))]
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "sections": {}}
    section_rows = {}
    target_all: set[str] = set()
    foreign_all: set[str] = set()
    for locator, text in sections:
        target = _signals(text, _TARGET)
        foreign = _signals(text, _FOREIGN)
        target_all.update(target)
        foreign_all.update(foreign)
        if target or foreign:
            standing = ("MIXED_SCOPE_REQUIRES_REVIEW" if target and foreign else
                        "CRFCE_SCOPE_CANDIDATE" if target else
                        "OUTSIDE_CRFCE_SCOPE_QUARANTINED")
            section_rows[locator] = {
                "standing": standing, "target_signals": target,
                "foreign_signals": foreign,
            }
    return {
        "ok": True,
        "target_signals": sorted(target_all),
        "foreign_signals": sorted(foreign_all),
        "sections": section_rows,
        "section_count": len(sections),
        "classified_sections": len(section_rows),
    }


def _version_key(name: str) -> str:
    stem = Path(name).stem
    folded = unicodedata.normalize("NFKC", stem).casefold()
    folded = re.sub(r"\(\s*(?:copy|final|rev(?:ision)?\s*)?\d+\s*\)", " ", folded)
    folded = re.sub(r"\b(?:copy|duplicate)\b", " ", folded)
    folded = re.sub(r"[_\W]+", " ", folded, flags=re.UNICODE)
    folded = re.sub(r"\s+", " ", folded).strip()
    return folded


def _source_disposition(record: dict[str, Any]) -> dict[str, Any]:
    text = _record_text(record)
    hint = record.get("_scope_hint") or {}
    target = sorted(set(_signals(text, _TARGET)) | set(hint.get("target_signals") or []))
    foreign = sorted(set(_signals(text, _FOREIGN)) | set(hint.get("foreign_signals") or []))
    name = str(record.get("name") or "")
    name_target = _signals(name, _TARGET)
    name_foreign = _signals(name, _FOREIGN)
    if foreign and target:
        standing = "MIXED_SCOPE_REQUIRES_PARTITION"
    elif foreign:
        standing = "OUTSIDE_CRFCE_SCOPE_QUARANTINED"
    elif target or name_target:
        standing = "CRFCE_SCOPE_CANDIDATE"
    else:
        standing = "SCOPE_UNRESOLVED_REQUIRES_REVIEW"
    return {
        "standing": standing,
        "target_signals": target,
        "foreign_signals": foreign,
        "filename_target_signals": name_target,
        "filename_foreign_signals": name_foreign,
        "section_count": hint.get("section_count"),
        "classified_sections": hint.get("classified_sections"),
    }


def _fact_disposition(record: dict[str, Any], fact: dict[str, Any],
                      source_scope: dict[str, Any]) -> str:
    source = fact.get("source") or {}
    text = " ".join((str(fact.get("name") or ""), str(source.get("locator") or ""),
                     str(source.get("excerpt") or "")))
    target = _signals(text, _TARGET)
    foreign = _signals(text, _FOREIGN)
    section = ((record.get("_scope_hint") or {}).get("sections") or {}).get(
        str(source.get("locator") or "")
    )
    if section:
        section_standing = section.get("standing")
        if section_standing == "OUTSIDE_CRFCE_SCOPE_QUARANTINED":
            return section_standing
        if section_standing == "CRFCE_SCOPE_CANDIDATE":
            return section_standing
        if section_standing == "MIXED_SCOPE_REQUIRES_REVIEW":
            return section_standing
    if foreign and not target:
        return "OUTSIDE_CRFCE_SCOPE_QUARANTINED"
    if target and not foreign:
        return "CRFCE_SCOPE_CANDIDATE"
    if foreign and target:
        return "MIXED_SCOPE_REQUIRES_REVIEW"
    standing = source_scope["standing"]
    if standing == "CRFCE_SCOPE_CANDIDATE":
        return standing
    if standing == "OUTSIDE_CRFCE_SCOPE_QUARANTINED":
        return standing
    return "SCOPE_UNRESOLVED_REQUIRES_REVIEW"


def _manifest_entry(record: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    structure = record.get("structure") or {}
    return {
        "file_id": record.get("file_id"),
        "name": record.get("name"),
        "sha256": record.get("sha256"),
        "bytes": record.get("bytes"),
        "parser": record.get("parser"),
        "verdict": record.get("verdict"),
        "facts": len(record.get("facts") or []),
        "pages_or_sections": structure.get("pages_or_sections"),
        "nonempty_sections": structure.get("nonempty_sections"),
        "characters": structure.get("characters"),
        "text_sha256": structure.get("text_sha256"),
        "metadata": structure.get("metadata") or {},
        "archive_member_count": structure.get("member_count"),
        "scope": scope,
        "version_family_key": _version_key(str(record.get("name") or "")),
    }


def _blob_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append({
            "kind": "source", "file_id": record.get("file_id"),
            "name": record.get("name"), "sha256": record.get("sha256"),
            "bytes": record.get("bytes"),
            "text_sha256": (record.get("structure") or {}).get("text_sha256"),
        })
        for member in (record.get("structure") or {}).get("members") or []:
            rows.append({
                "kind": "archive_member", "file_id": record.get("file_id"),
                "archive_sha256": record.get("sha256"), "name": member.get("name"),
                "sha256": member.get("sha256"), "bytes": member.get("bytes"),
                "text_sha256": (member.get("structure") or {}).get("text_sha256"),
            })
    return rows


def _duplicate_groups(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        digest = str(row.get(key) or "")
        if digest:
            grouped[digest].append(row)
    return [
        {key: digest, "copies": copies, "standing": (
            "EXACT_BYTE_DUPLICATE" if key == "sha256" else "NORMALISED_TEXT_DUPLICATE"
        )}
        for digest, copies in sorted(grouped.items()) if len(copies) > 1
    ]


def _version_families(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        key = str(entry.get("version_family_key") or "")
        if key:
            grouped[key].append({
                "file_id": entry.get("file_id"), "name": entry.get("name"),
                "sha256": entry.get("sha256"), "text_sha256": entry.get("text_sha256"),
            })
    return [{"version_family_key": key, "members": members,
             "standing": "POTENTIAL_VERSION_FAMILY_REQUIRES_REVIEW"}
            for key, members in sorted(grouped.items()) if len(members) > 1]


def _partition_records(records: list[dict[str, Any]], scopes: dict[str, dict[str, Any]]) -> tuple[list[dict], dict]:
    filtered: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    quarantined_members: Counter[tuple[str, str]] = Counter()
    for record in records:
        file_id = str(record.get("file_id") or "")
        kept = []
        for fact in record.get("facts") or []:
            standing = _fact_disposition(record, fact, scopes[file_id])
            counts[standing] += 1
            source = fact.get("source") or {}
            locator = str(source.get("locator") or "")
            member_match = _ARCHIVE_MEMBER.match(locator)
            if standing == "CRFCE_SCOPE_CANDIDATE":
                kept.append(fact)
            elif member_match:
                quarantined_members[(file_id, member_match.group("name"))] += 1
        filtered.append({**record, "facts": kept})
    quarantine = [{"file_id": file_id, "archive_member": member, "facts": count,
                   "standing": "EXCLUDED_FROM_CRFCE_CLAIM_ANALYSIS"}
                  for (file_id, member), count in sorted(quarantined_members.items())]
    return filtered, {"fact_dispositions": dict(sorted(counts.items())),
                      "archive_member_quarantine": quarantine}


def build(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one deterministic corpus report from successful ingestion records."""
    good = [record for record in records if record.get("ok")]
    failures = [record for record in records if not record.get("ok")]
    scopes = {str(record.get("file_id") or ""): _source_disposition(record) for record in good}
    entries = [_manifest_entry(record, scopes[str(record.get("file_id") or "")]) for record in good]
    filtered, scope_detail = _partition_records(good, scopes)
    claims = project_research.claim_analysis(filtered)
    blobs = _blob_rows(good)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "sources": entries,
        "source_count": len(entries),
        "source_bytes": sum(int(entry.get("bytes") or 0) for entry in entries),
        "ingestion_failures": failures,
        "exact_duplicate_groups": _duplicate_groups(blobs, "sha256"),
        "normalised_text_duplicate_groups": _duplicate_groups(blobs, "text_sha256"),
        "potential_version_families": _version_families(entries),
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": "CORPUS_INDEXED" if good and not failures else "CORPUS_PARTIAL",
        "manifest": manifest,
        "scope": {
            "source_dispositions": [
                {"file_id": entry["file_id"], "name": entry["name"], **entry["scope"]}
                for entry in entries
            ],
            **scope_detail,
            "note": ("Quarantined or unresolved source evidence remains in the manifest but is "
                     "excluded from CRFCE claim comparisons until a reviewer resolves scope."),
        },
        "claims": claims,
        "evidence_boundary": {
            "extracted_claims": "UNVERIFIED_EXTRACTED",
            "plot_pixels": "NOT_DIGITISED_AS_MEASUREMENTS",
            "physical_validation": "NOT_DEMONSTRATED",
            "design_release_status": "NOT_AUTHORIZED",
            "release_authorized": False,
        },
    }
    report["summary"] = (
        f"Indexed {len(entries)} source file(s), {len(blobs) - len(entries)} archive member(s), "
        f"{len(manifest['exact_duplicate_groups'])} exact duplicate group(s), "
        f"{len(manifest['normalised_text_duplicate_groups'])} normalized-text duplicate group(s), "
        f"{len(claims['claim_ledger'])} recognized source-linked claim(s), and "
        f"{len(claims['candidate_conflicts'])} candidate conflict(s). "
        "Out-of-scope evidence is quarantined; physical validation remains NOT_DEMONSTRATED."
    )
    report["receipt"] = _sha_bytes(_stable(report))
    return report


def _write_json(path: Path, payload: Any) -> dict[str, Any]:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")
    content = path.read_bytes()
    return {"name": path.name, "path": str(path), "sha256": _sha_bytes(content),
            "bytes": len(content)}


def _markdown(report: dict[str, Any]) -> str:
    manifest = report["manifest"]
    claims = report["claims"]
    scope_counts = report["scope"]["fact_dispositions"]
    lines = [
        "# CRFCE source-corpus review",
        "",
        f"Corpus receipt: `{report['receipt']}`",
        "",
        "## Inventory",
        "",
        f"- Top-level sources: {manifest['source_count']}",
        f"- Exact duplicate groups: {len(manifest['exact_duplicate_groups'])}",
        f"- Normalized-text duplicate groups: {len(manifest['normalised_text_duplicate_groups'])}",
        f"- Potential version families: {len(manifest['potential_version_families'])}",
        f"- Recognized claims: {len(claims['claim_ledger'])}",
        f"- Candidate conflicts: {len(claims['candidate_conflicts'])}",
        "",
        "## Scope partition",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(scope_counts.items()))
    lines.extend([
        "", "## Evidence boundary", "",
        "Document statements and OCR are unverified extracted evidence. Images were not "
        "digitized as calibrated measurements. No corpus artifact authorizes design release. "
        "Physical validation is **NOT_DEMONSTRATED**.", "",
    ])
    return "\n".join(lines)


def write_bundle(report: dict[str, Any], output: str | Path) -> list[dict[str, Any]]:
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    artifacts = [
        _write_json(target / "CRFCE_source_corpus_manifest.json", report["manifest"]),
        _write_json(target / "CRFCE_claim_ledger.json", {
            "schema": "engineai.crfce-claim-ledger.v1",
            "standing": "UNVERIFIED_EXTRACTED",
            "claims": report["claims"]["claim_ledger"],
            "receipt": report["receipt"],
        }),
        _write_json(target / "CRFCE_candidate_conflict_ledger.json", {
            "schema": "engineai.crfce-candidate-conflict-ledger.v1",
            "candidate_conflicts": report["claims"]["candidate_conflicts"],
            "value_variants": report["claims"]["value_variants"],
            "note": report["claims"]["note"],
            "receipt": report["receipt"],
        }),
        _write_json(target / "CRFCE_source_corpus_report.json", report),
    ]
    md = target / "CRFCE_source_corpus_review.md"
    md.write_text(_markdown(report), encoding="utf-8")
    artifacts.append({"name": md.name, "path": str(md), "sha256": _sha_bytes(md.read_bytes()),
                      "bytes": md.stat().st_size})
    return artifacts


def ingest_paths(paths: Iterable[str | Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records, sources = [], []
    for index, raw in enumerate(paths, 1):
        path = Path(raw)
        digest = project_ingestion._sha(path) if path.is_file() else ""
        metadata = {"id": f"source-{index:03d}-{digest[:12]}", "name": path.name,
                    "ext": path.suffix.lstrip(".").lower(), "sha256": digest}
        record = project_ingestion.ingest(path, metadata)
        if record.get("ok"):
            record["_scope_hint"] = scope_hint(path, metadata["ext"], record)
        records.append(record)
        sources.append({"name": path.name, "sha256": digest, "bytes": (
            path.stat().st_size if path.is_file() else None
        )})
    return records, sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True,
                        help="Explicit source file; repeat for each input")
    parser.add_argument("--output", required=True, help="Output directory for the evidence bundle")
    args = parser.parse_args(argv)
    records, _ = ingest_paths(args.source)
    report = build(records)
    artifacts = write_bundle(report, args.output)
    print(json.dumps({"verdict": report["verdict"], "receipt": report["receipt"],
                      "summary": report["summary"], "artifacts": artifacts},
                     indent=2, ensure_ascii=False))
    return 0 if report["verdict"] == "CORPUS_INDEXED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
