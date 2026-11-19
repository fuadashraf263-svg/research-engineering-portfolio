#!/usr/bin/env python3
"""Conformance for durable CRFCE Studio routing and worker execution."""
from __future__ import annotations

import contextlib
import io
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

with contextlib.redirect_stdout(io.StringIO()):
    import compute_scheduler as scheduler
    import compute_worker
    import studio_pro


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_crfce_corpus_receipt_flow() -> None:
    """Prove Studio passes a structured, recomputable report into resolution."""
    report = {
        "schema": "engineai.crfce-source-corpus.v1",
        "verdict": "CORPUS_INDEXED",
        "manifest": {
            "schema": "engineai.crfce-source-manifest.v1",
            "sources": [{"file_id": "synthetic-corpus-source",
                         "name": "synthetic.txt",
                         "sha256": hashlib.sha256(b"synthetic source").hexdigest(),
                         "bytes": len(b"synthetic source")}],
            "source_count": 1, "source_bytes": len(b"synthetic source"),
            "ingestion_failures": [], "exact_duplicate_groups": [],
            "normalised_text_duplicate_groups": [],
            "potential_version_families": [],
        },
        "scope": {"note": "synthetic test fixture; not source authentication"},
        "claims": {"claim_ledger": [], "candidate_conflicts": [],
                   "repeated_claims": [], "value_variants": [],
                   "note": "Candidate conflicts come from deterministic text extraction; context review is required before declaring a contradiction."},
        "evidence_boundary": {
            "extracted_claims": "UNVERIFIED_EXTRACTED",
            "plot_pixels": "NOT_DIGITISED_AS_MEASUREMENTS",
            "physical_validation": "NOT_DEMONSTRATED",
            "design_release_status": "NOT_AUTHORIZED", "release_authorized": False,
        },
        "summary": "synthetic source-corpus report",
    }
    report["receipt"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()
    corpus_receipt = report["receipt"]
    saved: list[tuple[str, dict]] = []
    stored: list[tuple[str, bytes]] = []
    originals = {
        "build_crfce_source_corpus": studio_pro.build_crfce_source_corpus,
        "list_files": studio_pro.list_files,
        "store_file": studio_pro.store_file,
        "save_to_project": studio_pro.save_to_project,
        "record_activity": studio_pro._record_activity,
    }
    try:
        studio_pro.build_crfce_source_corpus = lambda project: {"ok": True, "report": report}
        studio_pro.list_files = lambda project: {"files": []}

        def store_file(project: str, name: str, content: bytes, *, origin: str = "upload") -> dict:
            stored.append((name, content))
            return {"name": name, "id": hashlib.sha256(name.encode()).hexdigest()[:16],
                    "sha256": hashlib.sha256(content).hexdigest(), "size": len(content),
                    "kind": "document", "ext": "json"}

        studio_pro.store_file = store_file
        studio_pro.save_to_project = lambda project, event: saved.append((project, event))
        studio_pro._record_activity = lambda *args, **kwargs: None
        with tempfile.TemporaryDirectory(prefix="engineai_crfce_receipt_flow_") as directory:
            result = studio_pro.resolve_crfce_project_configuration(
                "synthetic project", decision=None, outdir=directory)
        governed = result.get("governed") or {}
        check(result.get("source_corpus_receipt") == corpus_receipt and
              governed.get("source_corpus_receipt") == corpus_receipt and
              result.get("source_corpus_integrity") ==
              "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY" and
              governed.get("source_corpus_integrity") ==
              "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY",
              "Studio passes and retains the recomputed report receipt with its limited integrity standing")
        check(result.get("receipt_digest") == governed.get("resolution_hash"),
              "the Studio receipt digest equals the corpus-bound governed resolution hash")
        resolution_bytes = next(content for name, content in stored
                                if name == "CRFCE_configuration_resolution.json")
        stored_resolution = json.loads(resolution_bytes.decode("utf-8"))
        check(stored_resolution.get("source_corpus_receipt") == corpus_receipt and
              stored_resolution.get("resolution_hash") == result.get("receipt_digest") and
              stored_resolution.get("source_corpus_integrity") ==
              "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY",
              "the durable project artifact contains the rehashed report-bound resolution identity")
        review_text = next(content for name, content in stored
                           if name == "CRFCE_CONFIGURATION_REVIEW.md").decode("utf-8")
        check(corpus_receipt in review_text and
              "REPORT_RECEIPT_RECOMPUTED_CONTENT_INTEGRITY_NOT_AUTHENTICITY" in review_text,
              "the durable human-readable review exposes the recomputed receipt and its non-authenticating standing")
        check(saved and saved[0][1].get("receipt") == result.get("receipt_digest") and
              saved[0][1].get("release_authorized") is False and
              saved[0][1].get("physical_validation") == "NOT_DEMONSTRATED",
              "the project event records the receipt without promoting research or release")
    finally:
        studio_pro.build_crfce_source_corpus = originals["build_crfce_source_corpus"]
        studio_pro.list_files = originals["list_files"]
        studio_pro.store_file = originals["store_file"]
        studio_pro.save_to_project = originals["save_to_project"]
        studio_pro._record_activity = originals["record_activity"]


def main() -> int:
    check({"CRFCE_RESEARCH", "CRFCE_DESIGN", "CRFCE_COUPLED_VV",
           "CRFCE_CONFIGURATION"}.issubset(scheduler.JOB_TYPES),
          "the scheduler does not admit the fixed CRFCE job types")
    paths = {getattr(route, "path", "") for route in studio_pro._make_app().routes}
    check("/api/research/crfce" in paths and "/api/design/crfce" in paths and
          "/api/research/crfce/vv" in paths and
          "/api/research/crfce/configuration" in paths,
          "the dedicated CRFCE submission contracts are missing")
    verify_crfce_corpus_receipt_flow()

    # Chat routing must create a durable job, never run a long research campaign inside
    # the request or label the queued work validated/released.
    captured: list[dict] = []
    saved: list[tuple[str, dict]] = []
    original_schedule = studio_pro.schedule_compute_job
    original_save = studio_pro.save_to_project
    try:
        def fake_schedule(body: dict) -> dict:
            captured.append(body)
            return {"ok": True, "job": {"id": "job-crfce-test",
                                         "job_type": body["job_type"],
                                         "state": "QUEUED", "project": body["project"]}}

        studio_pro.schedule_compute_job = fake_schedule
        studio_pro.save_to_project = lambda project, event: saved.append((project, event))
        reply = studio_pro.assistant_reply({
            "message": "Run all CRFCE research and decide the further tests",
            "project": "CRFCE reference",
        })
        if sys.platform == "win32":
            # Native Windows intentionally refuses the Linux process-group
            # scheduler; never fake a queued research job just to satisfy the
            # chat contract. The Linux qualification path below remains the
            # stronger queue/worker assertion.
            check(reply["basis"] == "CRFCE_JOB_REFUSED" and
                  "Linux resource/process-group backend" in reply["answer"],
                  "Windows did not preserve the explicit CRFCE scheduler boundary")
            check(not captured and not saved,
                  "a platform-refused CRFCE job reached the scheduler or project store")
        else:
            check(reply["basis"] == "CRFCE_JOB_QUEUED" and
                  captured[0]["job_type"] == "CRFCE_RESEARCH",
                  "the chatbox did not queue the research job")
        if sys.platform == "win32":
            check(reply["released"] is False and reply.get("release_authorized", False) is False and
                  reply.get("physical_validation", "NOT_DEMONSTRATED") == "NOT_DEMONSTRATED",
                  "the platform-refused response overstated its evidence")
            print("crfce_studio_conformance: PASS (Windows scheduler boundary verified)")
            return 0
        check(reply["released"] is False and reply["release_authorized"] is False and
              reply.get("physical_validation", "NOT_DEMONSTRATED") == "NOT_DEMONSTRATED",
              "the queued response overstated its evidence")
        check(any(action.get("payload", {}).get("mode") == "jobs"
                  for action in reply["actions"]),
              "the queued response does not open the live Jobs sandbox")
        check(saved and saved[0][1].get("job_id") == "job-crfce-test",
              "the queued conversation/job identity was not persisted")
        vv_reply = studio_pro.assistant_reply({
            "message": "Run CRFCE coupled multiphysics V&V with sensitivity",
            "project": "CRFCE reference",
            "run_real_solvers": False,
        })
        check(vv_reply["basis"] == "CRFCE_JOB_QUEUED" and
              captured[-1]["job_type"] == "CRFCE_COUPLED_VV",
              "the chatbox did not queue the coupled V&V job")
        configuration_reply = studio_pro.assistant_reply({
            "message": "Resolve CRFCE source configuration conflicts",
            "project": "CRFCE reference",
        })
        check(configuration_reply["basis"] == "CRFCE_JOB_QUEUED" and
              captured[-1]["job_type"] == "CRFCE_CONFIGURATION",
              "the chatbox did not queue the source-to-configuration review")
        missing_project = studio_pro.assistant_reply({
            "message": "Design the CRFCE engine and prepare its paper"})
        check(missing_project["basis"] == "CRFCE_PROJECT_REQUIRED" and
              missing_project["released"] is False,
              "projectless CRFCE execution did not fail closed")
        direct_missing = studio_pro.schedule_crfce_job({}, "CRFCE_RESEARCH")
        check(direct_missing.get("ok") is False and "project" in direct_missing.get("error", ""),
              "the dedicated submission contract accepted an implicit Untitled project")
        unknown = studio_pro.schedule_crfce_job(
            {"project": "CRFCE reference", "design": {"invented_parameter": 1.0}},
            "CRFCE_RESEARCH")
        check(unknown.get("ok") is False and "unknown" in unknown.get("error", ""),
              "an unknown CRFCE design input was silently accepted")
        nonfinite = studio_pro.schedule_crfce_job(
            {"project": "CRFCE reference", "design": {"rpm": float("nan")}},
            "CRFCE_RESEARCH")
        check(nonfinite.get("ok") is False and "finite" in nonfinite.get("error", ""),
              "a non-finite CRFCE design input was accepted")
        bad_uq = studio_pro.schedule_crfce_job({
            "project": "CRFCE reference",
            "uncertainty_model": {"basis_ref": "", "inputs": {}},
        }, "CRFCE_COUPLED_VV")
        check(bad_uq.get("ok") is False and "basis_ref" in bad_uq.get("error", ""),
              "a source-free uncertainty model reached the scheduler")
        bad_decision = studio_pro.schedule_crfce_job({
            "project": "CRFCE reference", "decision": "auto-select",
        }, "CRFCE_CONFIGURATION")
        check(bad_decision.get("ok") is False and "object" in bad_decision.get("error", ""),
              "a malformed source-review decision reached the scheduler")
        check(len(captured) == 3, "a refused CRFCE request reached the scheduler")
    finally:
        studio_pro.schedule_compute_job = original_schedule
        studio_pro.save_to_project = original_save

    if sys.platform == "win32":
        print("crfce_studio_conformance: PASS (Windows scheduler boundary verified)")
        return 0

    # Prove the fixed registry executes in a real external worker process and that the
    # scheduler records the terminal result. No general shell command is involved.
    with tempfile.TemporaryDirectory(prefix="engineai-crfce-job-") as tmp:
        root = Path(tmp)
        submitted = scheduler.submit(
            root, project="CRFCE reference", job_type="CRFCE_RESEARCH", payload={"design": {}},
            owner="conformance", resources={"cpu": {"requested": 1, "maximum": 1},
                                             "ram": {"requested_gb": 0.25,
                                                     "maximum_gb": 2.0},
                                             "disk": {"scratch_requested_gb": 0.01,
                                                      "scratch_maximum_gb": 0.25},
                                             "timeout_seconds": 180})
        check(submitted.get("ok"), f"scheduler refused CRFCE research: {submitted}")
        future = scheduler.dispatch_external(root, submitted["job"]["id"])
        check(future is not None, "the external CRFCE worker was not dispatched")
        future.result(timeout=210)
        terminal = scheduler.get(root, submitted["job"]["id"])
        check(terminal and terminal["state"] == "COMPLETED",
              f"the external CRFCE worker did not succeed: {terminal}")
        result = terminal.get("result") or {}
        check(result.get("basis") == "CRFCE_DEEP_RESEARCH" and
              result.get("release_authorized") is False,
              "the external worker returned the wrong or over-promoted result")
        scheduler.shutdown(root)

    # A real uploaded file must cross the scheduler/process boundary, build a source
    # corpus, and return review artifacts without auto-selecting a design version.
    with tempfile.TemporaryDirectory(prefix="engineai-crfce-config-job-") as tmp:
        root = Path(tmp)
        previous_environment = os.environ.get("ENGINEAI_STUDIO_DATA")
        previous_paths = (studio_pro._DATA, studio_pro._PROJ,
                          studio_pro._FILES_DIR, studio_pro._FILES_IDX)
        try:
            os.environ["ENGINEAI_STUDIO_DATA"] = str(root)
            studio_pro._DATA = root
            studio_pro._PROJ = root / "projects.json"
            studio_pro._FILES_DIR = root / "files"
            studio_pro._FILES_IDX = root / "files.json"
            project = "CRFCE configuration source"
            studio_pro.save_to_project(project, {"kind": "project_created"})
            uploaded = studio_pro.store_file(
                project, "CRFCE_reference.txt",
                (b"CRFCE reference design. Rotor radius: 60 mm. "
                 b"Rotor stack length: 50 mm. Operating temperature: 30 K."))
            check(uploaded.get("ok") and Path(root / "files").is_dir(),
                  "the real CRFCE source file was not stored")
            submitted = scheduler.submit(
                root, project=project, job_type="CRFCE_CONFIGURATION",
                payload={"project": project, "decision": None}, owner="conformance",
                resources={"cpu": {"requested": 1, "maximum": 1},
                           "ram": {"requested_gb": 0.25, "maximum_gb": 2.0},
                           "disk": {"scratch_requested_gb": 0.01,
                                    "scratch_maximum_gb": 0.25},
                           "timeout_seconds": 180})
            check(submitted.get("ok"),
                  f"scheduler refused CRFCE configuration review: {submitted}")
            future = scheduler.dispatch_external(root, submitted["job"]["id"])
            check(future is not None, "the configuration worker was not dispatched")
            future.result(timeout=210)
            terminal = scheduler.get(root, submitted["job"]["id"])
            check(terminal and terminal["state"] == "COMPLETED",
                  f"the configuration worker did not succeed: {terminal}")
            result = terminal.get("result") or {}
            governed = result.get("governed") or {}
            check(result.get("basis") == "CRFCE_CONFIGURATION_RESOLUTION" and
                  governed.get("verdict") == "CONFIGURATION_WITHHELD_REVIEW_INCOMPLETE",
                  "the real-file review did not fail closed pending semantic decisions")
            check(governed.get("missing_source_version_binding") is True and
                  "source-version binding" in result.get("answer", ""),
                  "the Studio result did not identify the missing source-version binding")
            check(result.get("source_corpus_receipt") and
                  result.get("project_artifacts") and
                  all(row.get("sha256") for row in result["project_artifacts"]),
                  "the real-file review did not preserve hashed corpus/configuration evidence")
            check(result.get("physical_validation") == "NOT_DEMONSTRATED" and
                  result.get("release_authorized") is False,
                  "the real-file configuration review overstated its evidence")
            scheduler.shutdown(root)
        finally:
            if previous_environment is None:
                os.environ.pop("ENGINEAI_STUDIO_DATA", None)
            else:
                os.environ["ENGINEAI_STUDIO_DATA"] = previous_environment
            (studio_pro._DATA, studio_pro._PROJ,
             studio_pro._FILES_DIR, studio_pro._FILES_IDX) = previous_paths

    # Worker payload types fail closed before physics execution.
    bad = compute_worker.execute({"job_type": "CRFCE_RESEARCH", "project": "x",
                                  "payload": {"design": "not-an-object"}})
    check(bad.get("ok") is False and "object" in bad.get("error", ""),
          "a malformed CRFCE worker payload was accepted")
    bypass = compute_worker.execute({"job_type": "CRFCE_RESEARCH", "project": "x",
                                     "payload": {"design": {"spatial_phase_factor": 2.0}}})
    check(bypass.get("ok") is False and "spatial_phase_factor" in bypass.get("error", ""),
          "worker-side validation did not stop an API-bypassed invalid override")
    no_project = compute_worker.execute({"job_type": "CRFCE_RESEARCH",
                                         "payload": {"design": {}}})
    check(no_project.get("ok") is False and "project" in no_project.get("error", ""),
          "worker-side validation accepted a projectless CRFCE job")
    bad_vv = compute_worker.execute({"job_type": "CRFCE_COUPLED_VV", "project": "x",
                                     "payload": {"design": {"rpm": float("nan")},
                                                 "run_real_solvers": False}})
    check(bad_vv.get("ok") is False and "finite" in bad_vv.get("error", ""),
          "worker-side V&V validation accepted a non-finite design")
    bad_configuration = compute_worker.execute({
        "job_type": "CRFCE_CONFIGURATION", "project": "x",
        "payload": {"decision": "auto-select"},
    })
    check(bad_configuration.get("ok") is False and
          "object" in bad_configuration.get("error", ""),
          "worker-side configuration validation accepted a malformed decision")
    no_configuration_project = compute_worker.execute({
        "job_type": "CRFCE_CONFIGURATION", "payload": {"decision": None},
    })
    check(no_configuration_project.get("ok") is False and
          "project" in no_configuration_project.get("error", ""),
          "worker-side configuration resolution accepted an implicit project")

    print("crfce_studio_conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
