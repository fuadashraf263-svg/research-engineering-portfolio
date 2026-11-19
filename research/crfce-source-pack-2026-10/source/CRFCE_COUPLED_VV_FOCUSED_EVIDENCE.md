# CRFCE coupled virtual V&V — focused evidence

This record is focused branch evidence, not full governance acceptance and not physical
validation.

## Tested implementation

- Commit: `a18df7dcea0f136781324157e7582d227e0b2281`
- Tree: `db345e3bb202edfe83f8ba9082e0520316806f24`
- Branch: `codex/crfce-coupled-vv-next`
- Focused conformance: `crfce_coupled_vv_conformance.py` — PASS on the exact clean commit
- Studio/scheduler conformance: `crfce_studio_conformance.py` and
  `compute_scheduler_conformance.py` — PASS
- Existing CRFCE research, design and real-file corpus conformances — PASS
- Surface partition, assistant, public-claim, registry and compile checks — PASS

## Exact reference execution

- Verdict: `VIRTUAL_VV_EXECUTED_NOT_RELEASEABLE`
- Record hash: `4eba3b07796324a7ba9bc4a0f59984383007338ae0e98066ac861227815812b3`
- Shared configuration hash:
  `5a4344b1e3ef8ed78a274b51cc1f31eff8101a1cf6a100cce0b3c039eb0765f6`
- Governed reduced-order outputs on the explicit reference assumptions: 61.1 N·m,
  64.0 kW, rotor safety factor 1.93, cold load 239.76 W, and cooler margin -89.76 W.
  These are model outputs, not measured performance.
- Uncertainty standing: `WITHHELD_MISSING_SOURCE_BEARING_UNCERTAINTY_MODEL`.
  Conformance separately proves deterministic propagation when a caller supplies cited
  distributions; the reference run does not invent them.

### Real solver checks

- 2-D finite-volume representative gapped circuit:
  - 320×320 cells: 10 cells across the gap, 1.469024356 T,
    result hash `36f7a2687280d3b2169ef938da32b6ebb9ed7a1c5c7a1f49827b2db32877212b`
  - 400×400 cells: 12 cells across the gap, 1.501655939 T,
    result hash `e810bb5238c133a7cb99088bab02a3b4dc7decfcd713479b2782e47d4c4825df`
  - Last-refinement change: 2.17304%; physical-sign checks passed.
  - Standing: `METHOD_QUALIFIED_DESIGN_CONVERGENCE_PARTIAL` because this is a
    representative linear circuit, not the exact nonlinear slotted machine.
- Elmer 26.2 HeatSolve exact-reference plate:
  - 8×8: 81 nodes, 25.000000000000018 versus exact 25 K; VTU SHA-256
    `cce44d73f39de4c840c0d1c1f04f81104c855b951063d89492a3aadc8aa597b2`
  - 16×16: 289 nodes, 25.00000000000001 versus exact 25 K; VTU SHA-256
    `360f0597352e06a2426717ee43b0f04fc3edfd7a827355344158942cae70eb80`
  - Maximum-principle bounds passed. This qualifies the solver path, not the CRFCE cryostat.

### Hashed handoff files

- `crfce-coupled-vv.json` —
  `5ff78b3079dbdd73b97cce2662db7670ed68fe044df95506594a12ce36c2e8e4`
- `crfce-shared-configuration.json` —
  `c7a87db18c78e9b176c3fb8f9f5d11f180e1b633d60b31b61b33c21cd8aefdd1`
- `crfce-sensitivity.csv` —
  `36a2f1f67344c2c0117ae806351c61b8fc92106456928bb560a17a03d471e5b6`
- `crfce-domain-matrix.csv` —
  `57c9fec558f384845ac1f942b15b2509bcf504253e8718e5c1b8a7b245908ebb`
- `CRFCE_COUPLED_VV_REPORT.md` —
  `28d1a6228caaa88c681f9d88d958d3118886ef2748a292738c8fe6d2d5280391`

## Honest remaining boundary

Exact nonlinear motor EM/torque, exact cryostat thermal, exact rotor/shaft FEA,
iterative coupled convergence, winding/quench, control-loop/fault simulation, full-wave
RF/EMI, source-bearing complete UQ, calibrated measurements and independent release
approval are not demonstrated. Physical validation remains `NOT_DEMONSTRATED`, and
release remains `NOT_AUTHORIZED`.
