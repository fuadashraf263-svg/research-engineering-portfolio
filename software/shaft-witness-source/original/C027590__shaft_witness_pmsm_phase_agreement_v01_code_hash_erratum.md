# Erratum: v0.1 phase-agreement prototype source hash

**Date:** 13 October 2026  
**Scope:** Provenance of the three-record v0.1 prototype replay.

The three-record replay receipt records prototype SHA-256 0bb2fab138860fb61dc960cbf48e73f07e61d2f4feb031cc6b4657ec538255a7. The file currently at shaft_witness_pmsm_phase_agreement_prototype_v01.py has SHA-256 45bde75de4f04f107845df2d5df11f708281e20450ccb19b3625455d5c3b38a90. The original source bytes for the receipted hash are not present in the workspace.

The v0.1 independent validator therefore reports **9/10**, failing only prototype_code_hash_matches; it still confirms that the three recorded source hashes and three score comparisons are intact. The prior v0.1 full replay also exceeded its numeric comparison tolerance, and its runner stopped before writing per-record diagnostics.

The corrected implementation is versioned as shaft_witness_pmsm_phase_agreement_prototype_v02.py. Its frozen v0.2 plan fixes the filter grid to the parent analysis's four-second interval and records edge-hold counts. The complete 1,200-record v0.2 replay passes its source, arithmetic, and reproducibility checks with zero difference across all 3,600 score fields; its independent validator passes 23/23.

Treat the v0.1 receipt as historical evidence whose original code source is unavailable. The v0.2 source, plan, runner, full result CSV/JSON, and independent validator form the reproducible replacement. The physical-validation status remains **UNVALIDATED**.
