#!/usr/bin/env python3
"""Adversarial real-file conformance for the CRFCE source-corpus contract."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import zipfile

from docx import Document
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

import crfce_corpus
import crfce_configuration_resolution as crfce_resolution


def check(condition, message):
    print("  " + ("ok  " if condition else "FAIL") + " " + message)
    if not condition:
        raise AssertionError(message)


def pdf(path: Path, lines: list[str]) -> None:
    page = canvas.Canvas(str(path))
    y = 750
    for line in lines:
        page.drawString(72, y, line)
        y -= 20
    page.save()


with tempfile.TemporaryDirectory(prefix="engineai_crfce_corpus_") as directory:
    root = Path(directory)
    manual = root / "CRFCE Comprehensive Design and Lab Manual.pdf"
    pdf(manual, ["CRFCE cryogenic RF-quiet motor", "Total mass around 8 kg",
                 "Operating temperature 30 K"])

    revision = root / "CRFCE Comprehensive Design and Lab Manual (1).docx"
    doc = Document()
    doc.add_paragraph("CRFCE cryogenic RF-quiet motor")
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Total mass around 11 kg"
    doc.add_paragraph("Operating temperature 30 K")
    doc.save(revision)

    note = root / "CRFCE operating note.txt"
    note.write_text("CRFCE operating temperature 30 K", encoding="utf-8")
    note_copy = root / "CRFCE operating note (1).md"
    note_copy.write_text("CRFCE operating temperature 30 K", encoding="utf-8")

    image = root / "PHOENIX_thermal_gradient.png"
    raster = Image.new("RGB", (640, 240), "white")
    ImageDraw.Draw(raster).text((40, 90), "PHOENIX wing thermal map", fill="black")
    raster.save(image)

    archive = root / "attachments.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(image, "thermal_gradient.png")
        zf.writestr("PHOENIX_report.txt", "PHOENIX wing airspeed 100 m/s")

    records, _ = crfce_corpus.ingest_paths(
        [manual, revision, note, note_copy, archive, image]
    )
    check(all(record.get("ok") for record in records),
          "PDF, DOCX, text, archive and raster sources pass the bounded real-file parsers")
    docx_record = next(record for record in records if record.get("name") == revision.name)
    check(docx_record["parser"] == "docx-openxml" and
          any("word/document.xml paragraph" in str(fact["source"]["locator"])
              for fact in docx_record["facts"]),
          "DOCX table and paragraph evidence receives stable OpenXML locators")

    report = crfce_corpus.build(records)
    check(report["verdict"] == "CORPUS_INDEXED", "a complete bounded corpus is indexed")
    exact = report["manifest"]["exact_duplicate_groups"]
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest()
    check(any(group["sha256"] == image_sha and len(group["copies"]) == 2 for group in exact),
          "an outer file duplicated inside an archive is detected by exact content hash")
    check(report["manifest"]["normalised_text_duplicate_groups"],
          "format-different sources with the same normalized text are deduplicated separately")
    check(report["manifest"]["potential_version_families"],
          "filename revisions are grouped as reviewable version families, not silently collapsed")

    claims = report["claims"]
    check(len(claims["claim_ledger"]) >= 4 and all(
        row["claim_id"] and row["standing"] == "UNVERIFIED_EXTRACTED"
        for row in claims["claim_ledger"]),
        "every recognized claim has stable identity and remains unverified extracted evidence")
    resolved_corpus = crfce_resolution.resolve(
        {"claims": claims["claim_ledger"]},
        {"candidate_conflicts": claims["candidate_conflicts"]}, None,
        source_corpus_report=report)
    check(resolved_corpus.get("source_corpus_receipt") == report["receipt"] and
          resolved_corpus.get("source_corpus_integrity") ==
          "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY" and
          resolved_corpus.get("configuration_ready_for_virtual_analysis") is False,
          "the resolver accepts the real corpus-builder report only after rehashing and remains decision-gated")
    check(any(row["claim"] == "total_mass" for row in claims["candidate_conflicts"]),
          "the 8 kg versus 11 kg source disagreement is retained as a candidate conflict")
    check(report["scope"]["archive_member_quarantine"] and
          report["scope"]["fact_dispositions"].get("OUTSIDE_CRFCE_SCOPE_QUARANTINED", 0) > 0,
          "PHOENIX archive evidence is preserved but excluded from CRFCE claim analysis")
    check(report["evidence_boundary"]["physical_validation"] == "NOT_DEMONSTRATED" and
          report["evidence_boundary"]["release_authorized"] is False,
          "corpus indexing cannot authorize release or physical validation")

    artifacts = crfce_corpus.write_bundle(report, root / "bundle")
    check(len(artifacts) == 5 and all(Path(row["path"]).is_file() and row["sha256"]
                                      for row in artifacts),
          "manifest, claim ledger, conflict ledger, full report and reviewer summary are real hashed files")

print("crfce_corpus_conformance: PASS")
