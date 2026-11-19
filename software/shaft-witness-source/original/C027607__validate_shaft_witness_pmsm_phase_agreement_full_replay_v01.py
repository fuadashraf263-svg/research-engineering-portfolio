#!/usr/bin/env python3
"""Independent full-cohort hash and numerical comparison audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
DATA = ROOT / "work" / "paderborn_kat" / "extracted"
PLAN = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_plan_v01.md"
CODE = OUT / "shaft_witness_pmsm_phase_agreement_prototype_v01.py"
RUNNER = OUT / "run_shaft_witness_pmsm_phase_agreement_full_replay_v01.py"
PARENT_CSV = OUT / "shaft_witness_paderborn_phase_coherence_expansion_v01.csv"
CSV_PATH = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_v01.csv"
REPORT = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_v01.md"
SUMMARY = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_v01.json"
RESULT = OUT / "validate_shaft_witness_pmsm_phase_agreement_full_replay_v01.json"
TOLERANCE = 1e-8


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    with PARENT_CSV.open(newline="", encoding="utf-8") as stream:
        parent = list(csv.DictReader(stream))
    with CSV_PATH.open(newline="", encoding="utf-8") as stream:
        replay = list(csv.DictReader(stream))
    parent_by_key = {(r["profile"], r["bearing_code"], int(r["repeat"])): r for r in parent}
    replay_by_key = {(r["profile"], r["bearing_code"], int(r["repeat"])): r for r in replay}
    expected_keys = set(parent_by_key)
    numeric_pairs = (
        ("reference_phase_1_r2", "prototype_phase_1_r2"),
        ("reference_phase_2_r2", "prototype_phase_2_r2"),
        ("reference_mean_r2", "prototype_mean_r2"),
    )
    max_error = 0.0
    numeric_valid = True
    for key, expected in parent_by_key.items():
        actual = replay_by_key.get(key)
        if actual is None:
            numeric_valid = False
            continue
        for ref_field, value_field in numeric_pairs:
            try:
                error = abs(float(actual[ref_field]) - float(actual[value_field]))
                if not math.isfinite(error):
                    numeric_valid = False
                max_error = max(max_error, error)
            except (TypeError, ValueError):
                numeric_valid = False
    checks = {
        "study_identifier": summary.get("study") == "shaft_witness_pmsm_phase_agreement_full_replay_v01",
        "parent_population_exact_1200": len(parent) == 1200,
        "replay_rows_exact_1200": len(replay) == 1200,
        "replay_keys_match_parent_keys": set(replay_by_key) == expected_keys and len(replay_by_key) == 1200,
        "no_duplicated_filenames": len({r["filename"] for r in replay}) == 1200,
        "all_statuses_metric_only": all(r["status"] == "METRIC_ONLY" for r in replay),
        "all_scores_match_within_1e_8": numeric_valid and max_error <= TOLERANCE,
        "all_source_files_hash_match_replay_csv": all(
            (DATA / r["bearing_code"] / r["filename"]).is_file()
            and sha256(DATA / r["bearing_code"] / r["filename"]) == r["source_sha256"]
            for r in replay
        ),
        "all_source_hashes_match_parent_csv": all(
            replay_by_key[key]["source_sha256"] == parent_by_key[key]["source_sha256"] for key in expected_keys
        ),
        "frozen_plan_hash_matches": summary.get("frozen_plan", {}).get("sha256") == sha256(PLAN),
        "prototype_hash_matches": summary.get("prototype_code", {}).get("sha256") == sha256(CODE),
        "runner_hash_recorded": bool(summary.get("runner_code", {}).get("sha256")) if summary.get("runner_code") else False,
        "parent_csv_hash_matches": summary.get("parent_analysis_csv", {}).get("sha256") == sha256(PARENT_CSV),
        "output_csv_hash_matches": summary.get("results_csv", {}).get("sha256") == sha256(CSV_PATH),
        "report_hash_matches": summary.get("report", {}).get("sha256") == sha256(REPORT),
        "summary_delta_matches_recalculation": abs(float(summary.get("maximum_absolute_score_delta", {}).get("two_phase_mean", -1)) - max_error) <= 1e-15,
        "no_physical_validation_claim": summary.get("physical_validation") == "UNVALIDATED",
        "timing_assumption_documented": "no independent clock calibration" in summary.get("timing_assumption", ""),
        "pipeline_checks_passed": all(summary.get("checks", {}).values()),
    }
    result = {
        "validator": "validate_shaft_witness_pmsm_phase_agreement_full_replay_v01",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "maximum_recalculated_absolute_score_error": max_error,
        "checks": checks,
        "issues": [key for key, value in checks.items() if not value],
        "physical_validation": summary.get("physical_validation"),
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
