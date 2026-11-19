#!/usr/bin/env python3
"""Replay prototype v0.2 against every file in the extracted Paderborn cohort."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.io import loadmat


OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
sys.path.insert(0, str(OUT))
from shaft_witness_paderborn_support_channel_corroboration_v01 import read_channel
from shaft_witness_pmsm_phase_agreement_prototype_v02 import pmsm_phase_agreement

DATA_ROOT = ROOT / "work" / "paderborn_kat" / "extracted"
EXPANSION_CSV = OUT / "shaft_witness_paderborn_phase_coherence_expansion_v01.csv"
PLAN = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_plan_v02.md"
PROTOTYPE = OUT / "shaft_witness_pmsm_phase_agreement_prototype_v02.py"
RUNNER = OUT / "run_shaft_witness_pmsm_phase_agreement_full_replay_v02.py"
CSV_OUT = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_v02.csv"
JSON_OUT = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_v02.json"
REPORT_OUT = OUT / "shaft_witness_pmsm_phase_agreement_full_replay_v02.md"
TOLERANCE = 1e-8  # numeric reproducibility tolerance only; not a feature threshold
EXPECTED_N = 1200


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if any(p.exists() for p in (CSV_OUT, JSON_OUT, REPORT_OUT)):
        raise FileExistsError("Refusing to overwrite existing full replay artifacts")
    for required in (EXPANSION_CSV, PLAN, PROTOTYPE):
        if not required.is_file():
            raise FileNotFoundError(required)
    with EXPANSION_CSV.open(newline="", encoding="utf-8") as stream:
        reference_rows = list(csv.DictReader(stream))
    if len(reference_rows) != EXPECTED_N:
        raise RuntimeError(f"Expected {EXPECTED_N} parent reference rows, found {len(reference_rows)}")
    keys = [(row["profile"], row["bearing_code"], int(row["repeat"])) for row in reference_rows]
    if len(set(keys)) != EXPECTED_N:
        raise RuntimeError("Parent CSV has duplicate profile/bearing/repeat keys")

    results: list[dict[str, object]] = []
    max_abs_channel_1 = 0.0
    max_abs_channel_2 = 0.0
    max_abs_mean = 0.0
    nonzero_delta_count = 0
    failed_statuses: list[str] = []
    for ix, expected in enumerate(reference_rows, start=1):
        profile = expected["profile"]
        bearing = expected["bearing_code"]
        repeat = int(expected["repeat"])
        filename = expected["filename"]
        path = DATA_ROOT / bearing / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_hash = sha256(path)
        if actual_hash != expected["source_sha256"]:
            raise RuntimeError(f"Source hash mismatch: {filename}")
        mat = loadmat(path, variable_names=[path.stem], squeeze_me=False, struct_as_record=True)
        if path.stem not in mat:
            raise ValueError(f"Expected MAT variable {path.stem!r} is missing in {filename}")
        record = mat[path.stem][0, 0]
        current_1 = read_channel(record, "phase_current_1")
        current_2 = read_channel(record, "phase_current_2")
        speed = read_channel(record, "speed")
        outcome = pmsm_phase_agreement(
            current_1["times"], current_1["values"], current_2["times"], current_2["values"],
            speed["times"], speed["values"], motor_topology="PMSM", pole_pairs=4,
            motor_configuration_verified=True,
            # The public dataset describes synchronous/support channels; no independent clock calibration is supplied.
            common_clock_verified=True,
            current_unit=current_1["unit"], current_sample_rate_hz=64_000.0, decimation=64,
        )
        if outcome["status"] != "METRIC_ONLY":
            failed_statuses.append(filename)
        r1 = outcome.get("phase_fit_r2_by_channel", {})
        score_1 = r1.get("phase_1") if isinstance(r1, dict) else None
        score_2 = r1.get("phase_2") if isinstance(r1, dict) else None
        mean = outcome.get("two_channel_mean_r2")
        expected_1 = float(expected["current_1_phase_fit_r2"])
        expected_2 = float(expected["current_2_phase_fit_r2"])
        expected_mean = float(expected["two_phase_mean_r2"])
        delta_1 = None if score_1 is None else float(score_1) - expected_1
        delta_2 = None if score_2 is None else float(score_2) - expected_2
        delta_mean = None if mean is None else float(mean) - expected_mean
        if delta_1 is not None and delta_2 is not None and delta_mean is not None:
            max_abs_channel_1 = max(max_abs_channel_1, abs(delta_1))
            max_abs_channel_2 = max(max_abs_channel_2, abs(delta_2))
            max_abs_mean = max(max_abs_mean, abs(delta_mean))
            nonzero_delta_count += sum(d != 0.0 for d in (delta_1, delta_2, delta_mean))
        timing = outcome.get("current_timebase_audit") or {}
        results.append({
            "profile": profile,
            "bearing_code": bearing,
            "repeat": repeat,
            "filename": filename,
            "source_sha256": actual_hash,
            "status": outcome["status"],
            "reference_phase_1_r2": expected_1,
            "prototype_phase_1_r2": score_1,
            "phase_1_delta": delta_1,
            "reference_phase_2_r2": expected_2,
            "prototype_phase_2_r2": score_2,
            "phase_2_delta": delta_2,
            "reference_mean_r2": expected_mean,
            "prototype_mean_r2": mean,
            "mean_delta": delta_mean,
            "current_timestamp_interval_cv_percent": timing.get("interval_cv_percent"),
            "current_max_departure_from_linear_fit_ms": timing.get("max_departure_from_linear_fit_ms"),
            "current_grid_edge_hold_samples_before_stored_axis": outcome.get("current_grid_edge_hold_samples_before_stored_axis"),
            "current_grid_edge_hold_samples_after_stored_axis": outcome.get("current_grid_edge_hold_samples_after_stored_axis"),
            "physical_validation": outcome.get("physical_validation"),
        })
        if ix % 100 == 0:
            print(f"processed {ix}/{EXPECTED_N}", flush=True)

    checks = {
        "exact_1200_parent_rows": len(reference_rows) == EXPECTED_N,
        "exact_1200_unique_source_records": len(results) == EXPECTED_N and len({r["filename"] for r in results}) == EXPECTED_N,
        "all_source_hashes_match_parent_csv": all(r["source_sha256"] == e["source_sha256"] for r, e in zip(results, reference_rows)),
        "all_1200_prototype_statuses_metric_only": not failed_statuses,
        "all_scores_present_finite_and_bounded": all(
            all(isinstance(r[field], (float, int)) and np.isfinite(float(r[field])) and 0.0 <= float(r[field]) <= 1.0
                for field in ("prototype_phase_1_r2", "prototype_phase_2_r2", "prototype_mean_r2")) for r in results
        ),
        "max_abs_phase_1_delta_within_tolerance": max_abs_channel_1 <= TOLERANCE,
        "max_abs_phase_2_delta_within_tolerance": max_abs_channel_2 <= TOLERANCE,
        "max_abs_mean_delta_within_tolerance": max_abs_mean <= TOLERANCE,
        "all_physical_statuses_unvalidated": all(r["physical_validation"] == "UNVALIDATED" for r in results),
    }
    with CSV_OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    summary = {
        "title": "Full-cohort reproducibility replay of the PMSM phase-agreement prototype",
        "study": "shaft_witness_pmsm_phase_agreement_full_replay_v02",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"record_count": len(results), "bearing_count": len({r["bearing_code"] for r in results}),
                  "profiles": sorted({r["profile"] for r in results}), "repeats_per_bearing_profile": 20,
                  "source_subset": "all currently extracted Paderborn files represented in the parent 1,200-row cohort"},
        "frozen_plan": {"file": PLAN.name, "sha256": sha256(PLAN)},
        "prototype_code": {"file": PROTOTYPE.name, "sha256": sha256(PROTOTYPE)},
        "runner_code": {"file": RUNNER.name, "sha256": sha256(RUNNER)},
        "parent_analysis_csv": {"file": EXPANSION_CSV.name, "sha256": sha256(EXPANSION_CSV)},
        "comparison_tolerance": TOLERANCE,
        "maximum_absolute_score_delta": {"phase_1": max_abs_channel_1, "phase_2": max_abs_channel_2, "two_phase_mean": max_abs_mean},
        "nonzero_delta_count_among_3600_score_fields": nonzero_delta_count,
        "failed_status_count": len(failed_statuses),
        "result_status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "results_csv": {"file": CSV_OUT.name, "row_count": len(results), "sha256": sha256(CSV_OUT)},
        "timing_assumption": "Passes common_clock_verified=true from the dataset's synchronous/support-channel documentation for software replay; no independent clock calibration or uncertainty is asserted.",
        "raw_waveforms_sent_to_engineai_studio": False,
        "physical_validation": "UNVALIDATED",
    }
    report = [
        "# Full-cohort PMSM phase-agreement prototype replay",
        "",
        f"**Records:** {len(results):,} across {summary['scope']['bearing_count']} extracted bearing codes and four settings  ",
        "**Software comparison:** prototype v0.2 versus frozen expansion CSV  ",
        "**Physical validation:** UNVALIDATED",
        f"**Replay status:** {summary['result_status']}",
        "",
        "## Result",
        "",
        f"All {len(results):,} records were replayed. The maximum absolute score difference was {max_abs_channel_1:.3g} for phase 1, {max_abs_channel_2:.3g} for phase 2, and {max_abs_mean:.3g} for their mean. {nonzero_delta_count} of 3,600 score deltas were nonzero. The predeclared numeric reproduction tolerance was {TOLERANCE:g}; it is not a physical or diagnostic threshold.",
        "",
        "The replay hashes every MAT source against the parent CSV and reproduces the same interpolation/filter/phase-fit recipe. The current call supplies `common_clock_verified=True` because the dataset documents synchronous/support channels; this does not independently calibrate the relative speed/current clock or its uncertainty. This is software parity evidence only.",
        "",
        f"## Validation checks\n\n" + "\n".join(f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in checks.items()),
        "",
        f"Per-record comparisons are in [{CSV_OUT.name}]({CSV_OUT.name}); the [frozen plan]({PLAN.name}) defines the cohort and tolerance.",
        "",
        "Sources: [Paderborn KAt dataset page](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download) and [Lessmeier et al. primary paper](https://mb.uni-paderborn.de/fileadmin-mb/kat/PDF/Veroeffentlichungen/20160703_PHME16_CM_bearing.pdf).",
        "",
    ]
    REPORT_OUT.write_text("\n".join(report), encoding="utf-8")
    summary["report"] = {"file": REPORT_OUT.name, "sha256": sha256(REPORT_OUT)}
    summary["results_csv"]["sha256"] = sha256(CSV_OUT)
    JSON_OUT.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"study": summary["study"], "records": len(results),
                      "maximum_absolute_score_delta": summary["maximum_absolute_score_delta"],
                      "nonzero_delta_count": nonzero_delta_count, "checks": checks,
                      "physical_validation": summary["physical_validation"]}, indent=2))
    if summary["result_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
