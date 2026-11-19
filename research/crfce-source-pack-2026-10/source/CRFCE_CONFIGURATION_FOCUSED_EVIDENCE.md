# CRFCE source-to-configuration focused evidence

**Standing:** `FOCUSED_VERIFIED_CANDIDATE_NOT_GOVERNED`

The implementation was exercised at commit
`02e7408eb641b01fff3bcd490c99306988e20ff4`, tree
`09d81aca493c59fe3f1fb5cd08c2486b68f21893`.  This evidence does not make the
branch governed or integrated; exact-source governance remains a prerequisite.

## What the path does

- Routes explicit CRFCE source-configuration requests from Studio chat and the
  `/api/research/crfce/configuration` contract into the fixed scheduler registry.
- Executes in the reviewed external worker, rebuilds the selected project's real source
  corpus, and stores content-addressed review artifacts back into that project.
- Maps only `rotor_radius`, `rotor_stack_length`, and `operating_temperature` through
  explicit unit contracts into the shared coupled-V&V configuration.
- Treats repeated text as repeated unverified evidence, not independent validation.
- Keeps distinct source values as separate design-version candidates.  Explicit review is
  required even when an upstream conflict ledger fails to identify the conflict.
- Preserves all remaining model inputs as named reference assumptions and preserves claimed
  outputs as review-required requirements rather than converting them into inputs.

## Focused tests

The following passed against the same implementation content:

- `governance_status.py --check`: 513 solver call sites; 0 bypass/unclassified sites.
- `crfce_configuration_resolution_conformance.py`: unit conversion, source identity,
  repetition, omitted-conflict, wrong-selection, missing-review, unsupported-field,
  deterministic hashing, V&V handoff, artifact, and evidence-boundary checks.
- `crfce_studio_conformance.py`: chat routing, dedicated API path, invalid decision refusal,
  explicit-project refusal, scheduler admission, a real uploaded TXT source through a real
  external worker process, project persistence, and hashed artifact storage.
- `compute_scheduler_conformance.py`, `crfce_corpus_conformance.py`,
  `surface_partition.py`, `master_goal_registry_conformance.py`,
  `public_claims_conformance.py`, and `assistant_core.py --selftest`.
- Python compilation and `git diff --check`.

One broad Studio selftest initially exposed the new CRFCE magnetic refinement call as an
unclassified call site.  It was corrected in both the call-site census and the function
adjudication ledger as an independent finite-volume verification oracle.  A subsequent
static authority scan returned zero bypass/unclassified sites.  The full measured census
will run again in the branch's exact-source governance gate.

## Actual ten-file CRFCE corpus result

Input evidence:

- `CRFCE_claim_ledger.json`: SHA-256
  `2cc010dda32a43c54125c3318e421320f6b12c05fda71607ac3e2a09ede6e8da`
- `CRFCE_candidate_conflict_ledger.json`: SHA-256
  `92246f8a34c7e3118d80a68cfd9d4a1b3e21c729d08358a389a489a117148cd1`
- Claim count: 72
- Analysis hash:
  `1d28cf60f5528abf54f8c9b36e503eb00011ef11ea8d4114cb574b7cb107ed53`

The analysis retained:

- `30 K` as one repeated candidate across 11 claim occurrences.
- `50 mm` stack length as one repeated candidate across 8 occurrences.
- Two incompatible rotor-radius variants: `60 mm` and `215 mm`, each converted separately
  to `0.060 m` and `0.215 m`; averaging and automatic selection are forbidden.
- Review-required target/requirement candidates for 20 kW, 20 N m, 400 V, 10 W HTS AC
  loss, 0.2 mm lamination, 40 K trip temperature, 4 mm tape width, and 8 kg mass.

The resulting verdict was `CONFIGURATION_WITHHELD_REVIEW_INCOMPLETE`.  No shared executable
configuration was emitted because no external review selected a design version, claim IDs,
or review reference.

Generated evidence:

- `CRFCE_configuration_resolution.json`: SHA-256
  `59d1b5e229ffdc1ef8217c04327dc2b15289ec9ea66abac015b44af268f48ec5`
- `CRFCE_requirement_candidates.csv`: SHA-256
  `594fbd58056cb8d2e3b75ec4fb815bb3c5b81964c533d531477a6e89de44b2fd`
- `CRFCE_CONFIGURATION_REVIEW.md`: SHA-256
  `751887fbebf6c04e1768af1224574e44c73276396a40aac7ae8e68c7eb9515c6`

## Boundary

Source extraction and review selection do not validate a document, establish independent
measurement, certify a material, authorize a design, or demonstrate physical performance.
Physical validation is `NOT_DEMONSTRATED`; design release is `NOT_AUTHORIZED`.
