# EngiDraw Verified

EngiDraw Verified is a working MVP for deterministic engineering-document and computational-geometry generation.

It does not use a text-to-image model to draw authoritative geometry. Structured specifications feed deterministic geometry functions, validators, renderers, and evidence manifests.

## Current capabilities

- Dimensioned mechanical SVG drawings for plates, flanges, and three-step shafts
- ASME Y14.5 and ISO 128 profile selection recorded in every artifact
- Constrained natural-language interpretation for the supported templates
- Validation gates for physical dimensions, profile containment, spacing, metadata, and template boundaries
- SHA-256 input and artifact fingerprints
- SVG, JSON evidence manifest, print/PDF workflow, and canonical-spec download/copy
- Implicit signed-distance gyroid thermal-core generation
- Marching-tetrahedra surface extraction, rotatable 3D preview, STL export, CEM recipe, and mesh telemetry
- Explicit separation between machine-validated drawings and research geometry that still requires physics/manufacturing validation

## Run locally

Requirements: Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Open the local URL shown by the development server.

## Verify

```bash
npm test
npm run build
npm run lint
```

## Project structure

- `app/page.tsx` — interactive engineering workbench
- `lib/engidraw.ts` — typed mechanical specifications, validators, SVG renderer, interpreter, artifact manifests
- `lib/computational.ts` — implicit gyroid SDF, meshing, STL generation, mesh rendering, computational evidence
- `tests/engine.test.ts` — deterministic and rejection-path tests
- `examples/` — supported example specifications
- `docs/computational-engineering-architecture.md` — path from MVP to LEAP 71-class computational engineering

## Accuracy boundary

“Validated” means the checks in the downloaded manifest passed. It does not certify fitness, safety, code compliance, manufacturability, or physical performance. Production release requires domain-specific simulation, process validation, physical testing, and qualified engineer approval.

## License note

This repository does not bundle ASME, ISO, IEC, or other licensed standards content. A production implementation must license the applicable documents and obtain legal review before making conformance claims.
