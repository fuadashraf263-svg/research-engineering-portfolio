# N006: bounded CPython `bin()` differential for the checked accumulator model

**Date:** 2026-10-27
**Target:** execute the existing checked accumulator artifacts; SRM remained stopped.

## Results

1. Re-ran `verify_cpython_binary_accumulator_model_20261027.py` with pinned CPython 3.14.7. The model matched an independent repeated-division/remainder oracle on 139,800 exhaustive signed normalized tokens and 5,000 seeded random normalized limb lists (up to 20 limbs / 600 magnitude bits). All lower chunks emitted their fixed widths and returned the accumulator state to zero. Result JSON SHA-256: `FC9E67C18474B3FEC91C0EA6147BCA7B3D3B97F84B51D90C8E59047F02FADB72`.
2. Ran `probe_cpython_bin_accumulator_differential_20261027.py`, comparing the same explicit accumulator transcription with the actual pinned interpreter's builtin `bin(int)`: all 65,536 nonzero integers in `[-32768,32768]` and 5,000 seeded normalized limb values matched exactly. The zero-input wrapper case was checked separately (`bin(0) == "0b0"`) because the accumulator source branch emits the single digit `0` and the builtin adds its format prefix. No mismatch remained.
3. Confirmed the local pinned source snapshot SHA-256 is `7A6D6CB8D6480C6E8B0D388E9898A136F19DED2013155357EB014405EBC55864`; the runtime was `C:\Python314\python.exe`, CPython 3.14.7, 64-bit Windows.
4. Rechecked the already compiled Lean evidence by hashing its source, OLean and compiler log. The bytes still match the prior Lean 4.34.1 compile record: source `38AF27C8BD4B333A64FE7A37AC15A5443514DB746852B57EEC88FA3BA0AB94EC`, OLean `7FDDFA5BFAA1362D961ED4363432706AFCF3B3913BC802B120C17346870A8631`, log `66EEC27B40F286A15E69F3954B9B8FB4F58D4D25C0DC0748626290C7B985E669`; log records `LEAN_EXIT=0` and no `sorryAx` among the audited theorems. Lean was not launched again: free RAM fell to 3.11 GiB, below this workspace's 6 GiB compile gate.

## Exact scope

The independent-oracle run checks the saved Python transcription against repeated division. The new differential run checks that transcription's emitted strings against the observed `bin()` behavior of this one installed CPython executable on a finite corpus. The Lean theorem separately proves that its formal BitVec64 machine agrees with its formal Nat model for all finite normalized 30-bit limb lists. The Python transcription is structurally intended to express the same loop, but this execution did **not** prove that the Python script is generated from or refines the Lean definition. Therefore these results do not close the general Lean-to-C-to-CPython source/runtime refinement.

Still open: formal C integer-promotion/shift semantics; proof that the actual executable uses the modeled PyLong digit configuration and source; all-input relation between the Lean function and Python transcription; builtin wrapper/call-path and Unicode output proof; `json.dumps`/UTF-8/consumer relation; resource bounds; production adoption; and coherent snapshots under concurrent mutation. The known mutable-graph counterexample remains. This is a reproducible bridge experiment, not universal refinement or completion of N006 or the broader mathematical research goal.

## Failure record

The first harness attempt stopped at a copied source-digest typo before running cases. A later run stopped at zero because the loop transcription's digit output is `"0"`, while `bin(0)` is `"0b0"`; this is the distinct zero/wrapper boundary. A PowerShell quoting typo then caused a Python parse error before cases. These are recorded in `probe_cpython_bin_accumulator_differential_FAILED_ATTEMPT_20261027.md`; the corrected script pins the actual source digest, separates the zero branch, and completed successfully.

## Artifacts

- Lean theorem source: `CPythonAccumulatorUInt64Refinement.lean`
- Lean compiled artifact: `CPythonAccumulatorUInt64Refinement.olean`
- Lean compiler log: `CPythonAccumulatorUInt64Refinement.compile.log`
- Independent model checker: `verify_cpython_binary_accumulator_model_20261027.py`
- CPython differential probe: `probe_cpython_bin_accumulator_differential_20261027.py`
- Differential evidence: `cpython_bin_accumulator_differential_evidence_20261027.json`
- Preserved failed harness attempts: `probe_cpython_bin_accumulator_differential_FAILED_ATTEMPT_20261027.md`
