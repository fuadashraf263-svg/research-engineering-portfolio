# Shaft Witness PMSM phase-agreement source

This is a code-and-protocol sample from the original Shaft Witness phase-agreement work. It preserves the two replay-plan versions, prototype and runner revisions, the v2 prototype test source, and the corresponding validators.

The full-cohort report and score tables are not included here. The source dataset is maintained by Paderborn University's KAt Bearing DataCenter under CC BY-NC 4.0; the raw waveforms and dataset-derived results are not redistributed in this portfolio copy. The archived replay also relies on a parent analysis CSV that is outside this source-only package, so the included full-replay runner is not a self-contained reproduction.

The frozen plan records that the 1,200-row comparison is software parity only, with the physical status marked UNVALIDATED; it does not establish calibrated timing, fault detection, or bearing diagnosis. The included files preserve the original project labels and limitations.

- [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md) — data source and sharing boundary.
- `original/` — 10 original code and planning files, copied byte-for-byte.
- `SHA256SUMS.txt` — hashes for the copied source files.

Source data information: [Paderborn Bearing DataCenter](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter). The data page states CC BY-NC 4.0 and requests citation; commercial data use requires contacting the source author.
