# Full-cohort replay plan: PMSM phase-agreement prototype v0.2

**Frozen:** 13 October 2026, before the v0.2 replay.  
**Question:** Does the reusable prototype reproduce every source-hashed row in the completed Paderborn phase-agreement expansion when it uses the same fixed four-second current grid?

## Data and population

- Inputs: the 1,200-row expansion CSV and corresponding local MATLAB recordings under work/paderborn_kat/extracted.
- Population: exactly 15 extracted bearing codes × four documented operating profiles × 20 repeats. This is the complete extracted subset represented by the parent CSV, not the entire public benchmark.
- Every MAT file must match the SHA-256 in the parent CSV. Every profile/bearing/repeat key must be unique and present.
- The v0.1 full replay exceeded its declared numerical tolerance and did not save per-record comparisons. This v0.2 run writes its receipt and comparison CSV before returning a failed status, so failures remain reviewable.

## Frozen signal recipe and comparison

- Use the source-documented PMSM four-pole-pair setting, nominal current sample rate 64 kHz, 64:1 decimation, 20–125 Hz band, and 0.20–3.80 s scoring window.
- Interpolate current channels onto exactly 256,000 nominal samples over [0, 4 s). Match the parent analysis's NumPy endpoint-hold behavior when the stored current axis does not cover the first or last nominal grid point; record the number of held points at each edge. Do not include any extra stored samples beyond that interval in zero-phase filter edge handling.
- The public dataset describes synchronous motor-current/speed support channels. Pass common_clock_verified=true for this software replay only; this is not an independent measurement of relative offset, drift, or timing uncertainty.
- Compare phase-1 R², phase-2 R², and their mean against the frozen parent expansion values for all 1,200 records. Maximum absolute difference tolerance is 1e-8 and applies only to software reproducibility.
- All outputs must remain METRIC_ONLY with physical validation UNVALIDATED.

## Checks, tests, and artifacts

- Eight prototype unit tests cover valid synthetic behavior, evidence gates, malformed axes, insufficient windows, invariance to extra stored samples beyond the declared four-second filter window, and short-tail endpoint holding.
- The run checks exact population and key coverage, source hashes, all scores finite and bounded, all statuses, per-channel and mean numerical deltas, and the physical-validation label.
- The independent validator re-reads the CSV and JSON, re-hashes all sources and code, checks every score and all three reported maximum errors, and verifies the report and run hashes.
- Raw signal arrays are not sent to EngineAI Studio. The separate Studio task uses only scalar speed, power, and torque inputs for a conditional bench sensitivity.
- This replay checks code and arithmetic only. It does not verify physical clock calibration, sensors, fault detection, bearing diagnosis, machine safety, or service value.

## Sources

- Paderborn KAt dataset page: https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download
- Lessmeier et al. primary paper: https://mb.uni-paderborn.de/fileadmin-mb/kat/PDF/Veroeffentlichungen/20160703_PHME16_CM_bearing.pdf
