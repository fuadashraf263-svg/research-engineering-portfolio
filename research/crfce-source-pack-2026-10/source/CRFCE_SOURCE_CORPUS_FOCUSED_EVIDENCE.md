# CRFCE source-corpus focused evidence

This record covers the content-addressed source-corpus capability introduced at exact
implementation commit `1bfe6bd893ff9dc851c35ee643ff984535463b11` (tree
`883f3caf5270766454aa6ce80ba02e22c083cb27`). It is focused evidence, not a full
governance verdict, product release, or physical-validation claim.

## Supplied source identities

| Source | Bytes | SHA-256 |
|---|---:|---|
| `Research paper_merged.pdf` | 23,204,295 | `96bf7809fc8d6ae0a6b86ad9b06fe126be19248d12d3fd60f4e08dde9b01f111` |
| `Cryogenic RF‑Quiet Cellular Engine (CRFCE) Comprehensive Design and Lab Manual (1) (1).pdf` | 3,945,533 | `2faf284ee38d0ce81646611cb0bf8687847afaa45f393a912837b46e092c0a97` |
| `Cryogenic RF‑Quiet Cellular Engine (CRFCE) Comprehensive Design and Lab Manual.pdf` | 3,937,078 | `29fe437957e76af42d1b61665b5f4d995c863a9f323dcc5d94f51d204c1eb873` |
| `CRFCE__1.pdf` | 998,179 | `13e01b251454e2e5fdb930d3feb8146b1d0dfb95894753c8c62ee263e08ca8fa` |
| `Cryogenic RF‑Quiet Cellular Engine (CRFCE) Comprehensive Design and Lab Manual (1).docx` | 6,122,456 | `fac2f67fee7e67ff118b13c91f2584d1e8519d16e02d32268e399f63897f2afa` |
| `Cryogenic RF‑Quiet Cellular Engine (CRFCE) Prototype Design and Lab Manual.pdf` | 219,294 | `4313220532442386cf470b58074a76eaa017f6f4fdb91cd6752bb9e2e2f8cfd8` |
| `Cryogenic RF‑Quiet Cellular Engine (CRFCE) Comprehensive Design and Lab Manual (1).pdf` | 843,942 | `aa8b3a7a6f505f34bedc5818590a750efa23af3742c3835c5ba61844bf5a04c3` |
| `CRFCE_Final_Validation_Framework_and_Master_Test_Matrix.pdf` | 212,003 | `31426072e310ecdb591fd7fda2aa0b0477596e038f3ae888ba37b4f070c720d0` |
| `attachments (1).zip` | 8,981,979 | `f90558617f7f8680214e8350161a97fb7c95e846f4fab0f438cd4111397c9faa` |
| `thermal_gradient.png` | 23,470 | `c389ad8fc7e3d8743d01c279219770afcbce26678cbbc26f8eb72d2b5f759616` |

## Exact-clean execution

Three fresh qualification contexts ran with one thread, private HOME/cache/Studio roots,
and no network authority:

- `crfce_corpus_conformance.py`: return code 0; elapsed 0.419 s; stdout SHA-256
  `fdde81829a627ffe21843ddfecc37d7e162166ef632f29fb492f5d5bf0c1d59f`;
  empty stderr.
- `project_ingestion_conformance.py`: return code 0; elapsed 29.418 s; stdout SHA-256
  `98ede39f2e88b2054cec8ff41be39d374403ebfa898a6a260dd48430877e7ced`;
  empty stderr.
- All ten real source files: return code 0; elapsed 21.026 s; stdout SHA-256
  `b0543d888e394cbbbd836628b08294e83a1e6405010c83e636d292c471da421e`;
  empty stderr.

The combined focused record verdict was `FOCUSED_PASS`. Its durable scratch record was
written as `/tmp/crfce-corpus-focused.json` during the run.

## Observed corpus result

- Corpus verdict: `CORPUS_INDEXED`
- Corpus receipt: `bc3424cba7cc28e98d3a30da11565b958b48e66d01e5dc479b8ff5896f44f713`
- Top-level source files: 10; archive members: 7; parser failures: 0.
- Source-linked recognized claims admitted to the CRFCE candidate ledger: 72.
- Exact duplicate groups: 1. The standalone `thermal_gradient.png` is byte-identical to
  the member with that name inside `attachments (1).zip`.
- Potential filename version families: 1; these are review candidates, not auto-collapsed.
- Candidate quantitative conflicts: 1. Multiple source pages state incompatible rotor
  radii (60 mm versus 215 mm); the ledger marks this for semantic/design-version review.
- Fact-level scope partition: 716 CRFCE candidates, 818 quarantined outside-scope facts,
  and 346 unresolved facts retained for reviewer disposition.
- `Research paper_merged.pdf` and `CRFCE__1.pdf` are mixed-scope and therefore partitioned
  by page. `attachments (1).zip` and the supplied thermal-gradient image are PHOENIX/wing
  evidence and are quarantined from CRFCE claim comparison.

## Generated evidence artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `CRFCE_source_corpus_manifest.json` | 14,389 | `476381f514b62fbb73c30a930b872b8a38dd66ed0c926dc8538d616c64e84a3f` |
| `CRFCE_claim_ledger.json` | 47,439 | `2cc010dda32a43c54125c3318e421320f6b12c05fda71607ac3e2a09ede6e8da` |
| `CRFCE_candidate_conflict_ledger.json` | 2,305 | `92246f8a34c7e3118d80a68cfd9d4a1b3e21c729d08358a389a489a117148cd1` |
| `CRFCE_source_corpus_report.json` | 107,117 | `bcaa3771919ef1bc72b3a05ff7c49f6f89fbf21cb6d3dbe9e7d756db8f7bef5e` |
| `CRFCE_source_corpus_review.md` | 659 | `96f0a0a9ff0ab99dbf357c16fec4356fbe538cba09667632e1a8e16881c91da8` |

## Evidence boundary and remaining work

Extracted document statements remain `UNVERIFIED_EXTRACTED`. OCR is explicitly
`UNVERIFIED_OCR_NOT_PLOT_DIGITISATION`; color-map pixels were not promoted to calibrated
temperatures. Physical validation remains `NOT_DEMONSTRATED`, design release is
`NOT_AUTHORIZED`, and `release_authorized` is false.

The 346 unresolved facts and the rotor-radius candidate conflict require project-owner or
independent reviewer disposition. Full exact-source governance, dependency integration,
coupled model V&V, independent review, calibrated measurements, and final cold qualification
remain separate gates.
