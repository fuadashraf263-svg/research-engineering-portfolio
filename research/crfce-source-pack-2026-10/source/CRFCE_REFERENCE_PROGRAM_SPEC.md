# CRFCE Reference Research Program

## Intended use

This candidate uses the Cryogenic RF-Quiet Cellular Engine (CRFCE) as an end-to-end
EngineAI reference project. It exercises receipt-backed analytical screening,
adversarial cases, deterministic geometry generation, dimensional back-measurement,
preliminary DFM/BOM output, technical-paper generation, and an explicit list of further
simulation and laboratory work.

It is not a production design, certification basis, safety approval, or physical
validation. The default numerical case is a transparent reference fixture. User
overrides are labelled `USER_SUPPLIED_UNVERIFIED`; defaults are labelled
`REFERENCE_ASSUMPTION`.

## Evidence vocabulary

- `released: true` appears only where the established Studio/capability-runner contract
  admits an output across its internal authority boundary.
- Every such result adds `released_scope: ENGINEAI_CAPABILITY_OUTPUT_ONLY`.
- `release_authorized` is always `false` in this reference program.
- `design_release_status` is always `NOT_AUTHORIZED`.
- `physical_validation` is `NOT_DEMONSTRATED` until calibrated measurements and an
  approved uncertainty/correlation assessment exist.

## Current executable scope

1. Electromagnetic screening based on tangential air-gap shear; radial Maxwell force is
   kept separate and zero electric loading must produce zero torque.
2. Rotor stress concentration, hoop stress, critical speed, fatigue, crack-intensity,
   bearing-life, cryogenic heat-leak, HTS margin, and continuous-rating screening through
   registered EngineAI capabilities.
3. Adversarial rejection of unphysical inputs and disclosure of withheld/out-of-envelope
   models.
4. Parametric stator/rotor proxy, coil-former, and shaft artifacts with dimensional
   back-verification; the reluctance/IPM proxy limitation remains visible.
5. Preliminary requirements, BOM, DFM, readiness gaps, figures, Markdown, HTML, and PDF.

## Required future evidence

- Hash, deduplicate, parse, and reconcile every supplied CRFCE source document and image.
- Replace reference assumptions with an approved requirements and parameter baseline.
- Build the real reluctance/flux-barrier geometry and HTS winding definition.
- Run nonlinear electromagnetic, RF/EMI, thermal, structural, rotordynamic, controls,
  quench, and co-simulation studies with mesh/time-step/convergence evidence.
- Apply the governed robust-design, RAMS, metrology, safety-case, MEQS, physical-validation,
  and DesignPassport authorities to exact-source evidence manifests.
- Produce a V&V matrix, uncertainty budget, lab protocols, calibrated raw measurements,
  correlation assessment, independent technical review, and signed release decision.

## Acceptance for this candidate

The focused candidate is acceptable only when both CRFCE conformances pass in normal and
isolated cold environments; generated STEP/STL/PDF/HTML/figure artifacts are real and
non-empty; receipt/input provenance and negative cases pass; adjacent authority and
surface-partition conformances pass; and no text or machine field claims design release
or physical validation. Exact-source governance and later cold qualification remain
separate prerequisites for integration.
