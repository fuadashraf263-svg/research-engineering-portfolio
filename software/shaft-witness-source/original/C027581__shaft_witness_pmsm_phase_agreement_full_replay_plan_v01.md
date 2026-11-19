# Full-cohort replay plan: PMSM phase-agreement prototype

**Frozen:** 13 October 2026, before running the 1,200-record replay.  
**Question:** Does reusable prototype v0.1 reproduce every source-hashed row in the completed Paderborn phase-agreement expansion under the same signal-processing recipe?

## Data and population

- Inputs: the 1,200-row expansion CSV and the corresponding local MATLAB recordings under `work/paderborn_kat/extracted`.
- Expected population: exactly 15 currently extracted bearing codes × four documented operating profiles × repeats 1–20. This is the complete extracted subset, not the full public benchmark.
- Each input row must map to one distinct filename, profile, bearing code, and repeat; each current MAT file must match the SHA-256 already recorded in the expansion CSV.
- No record may be omitted because of its result. Source file/hierarchy errors, malformed input, or `NOT_EVALUATED` status fail the replay and are retained for review.

## Comparison

- Run the reusable prototype on each file with the source-documented PMSM four-pole-pair setting, nominal current sample rate 64 kHz, 64:1 decimation, 20–125 Hz band, and 0.20–3.80 s scoring window.
- The current dataset documentation describes synchronous motor-current/speed channels; for this digital replay only, pass the prototype's caller evidence flag as true. This flag is an explicit replay assumption, not an independent calibration of relative clock offset, drift, or uncertainty. Current stored-axis diagnostics remain present in the result.
- Compare prototype phase-1 R², phase-2 R², and their mean against the expansion CSV for all 1,200 records. A maximum absolute difference of `1e-8` is a software-reproduction tolerance only; it is not an operating or diagnostic threshold.
- Require all records to remain `METRIC_ONLY`; preserve the physical-validation status as `UNVALIDATED`.

## QA and deliverables

- Independently re-hash all 1,200 source files, re-check unique keys, row count, finite bounded scores, run status, and per-channel/mean maximum error.
- Run the prototype's six unit tests and the independent replay validator.
- Save a compact receipt with every filename, source hash, three reference scores, three prototype scores, score deltas, and the source/code/CSV/plan hashes.
- No raw signal arrays are uploaded or sent to EngineAI Studio. This comparison validates software reproducibility only; it does not validate clock calibration, sensors, fault detection, machine safety, or service value.
