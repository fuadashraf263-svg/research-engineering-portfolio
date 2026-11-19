# SERT / URTM-R2 bounded verification sample

This folder preserves a small original Python/NumPy reference exercise archived on 12 November 2026. It covers two deliberately simple baselines: mesh localization over a fixed physical interval and progressive removal of three parallel unit-stiffness members.

The report states its limits: the quantities are nondimensional, no fracture PDE or physical experiment was run, and the toy example does not show that SERT outperforms standard mechanics. It is useful as a transparent code-and-reasoning sample, not as empirical validation.

- `original/REPORT.md`: original report.
- `original/test.py`: original reference script.
- `original/mesh_localization.csv`, `original/truss_baselines.csv`, and `original/results.json`: original outputs.
- `SHA256SUMS.txt`: integrity hashes for these five original files.
- Related proposal: [`../../research/sert-urtm-proposal.pdf`](../../research/sert-urtm-proposal.pdf).

The original files were extracted from `C089374__SERT_validation_20261112.zip` and are preserved byte-for-byte. No license is specified; ask the author before reuse.
