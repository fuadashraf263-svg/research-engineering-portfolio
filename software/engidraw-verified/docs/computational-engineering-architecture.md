# Computational Engineering Architecture

## Goal

Evolve EngiDraw from verified 2D drawing automation into a computational engineering platform capable of generating classes of complex physical machines—not merely individual CAD models.

LEAP 71 describes this approach as encoding engineering logic, physics, and manufacturing constraints into computational models that output manufacturable geometry. Its public stack uses the C#-based PicoGK geometry kernel, ShapeKernel, lattices, implicits, and application-specific computational models. References: [LEAP 71 technology](https://leap71.com/tech/), [PicoGK documentation](https://picogk.org/doc/), and [official LEAP 71 GitHub](https://github.com/leap71).

EngiDraw should learn from that architecture without claiming to reproduce proprietary Noyron capabilities.

## Target pipeline

```text
Mission requirements + materials + process + operating envelope
                              |
                              v
          Typed Computational Engineering Recipe (versioned)
                              |
            +-----------------+------------------+
            |                 |                  |
            v                 v                  v
     Engineering logic   Physics models   Manufacturing rules
            |                 |                  |
            +-----------------+------------------+
                              |
                   Multidisciplinary optimizer
                              |
                              v
         Parametric + implicit + voxel geometry compiler
                              |
            +-----------------+------------------+
            |                 |                  |
            v                 v                  v
       CAD/B-rep          SDF/voxels       Lattices/fields
            |                 |                  |
            +-----------------+------------------+
                              |
             Mesh, STEP, slices, drawings, reports
                              |
                              v
       Independent verification + physical-test feedback
```

## Current implementation

| Layer | Implemented now | Status |
|---|---|---|
| Requirement capture | Typed specs plus constrained prompt interpreter | Working MVP |
| Conventional geometry | Deterministic plate, flange, and stepped-shaft templates | Working MVP |
| Drawing generation | Orthographic/detail SVG with dimensions, notes, title block | Working MVP |
| Evidence | SHA-256 fingerprints and per-rule manifest | Working MVP |
| Implicit geometry | Gyroid signed-distance field clipped to a design envelope | Working MVP |
| Surface extraction | Marching tetrahedra with STL export | Working MVP/research resolution |
| 3D visualization | Rotatable projected triangle preview | Working MVP |
| Multiphysics | Adapter boundary only | Not implemented |
| Optimization | Design-variable and objective schema to add | Not implemented |
| Production geometry | PicoGK/OpenVDB/robust B-rep worker | Not implemented |
| Physical feedback | Test-ledger schema and model calibration to add | Not implemented |

The gyroid demonstrator proves that the product architecture is no longer restricted to conventional drawings. It generates volumetric, periodic, implicit geometry from an engineering recipe and exports a real triangle mesh. It is not yet a qualified heat exchanger.

## Production services

### 1. Computational model service

Each domain package contains:

- Input variables, units, validity ranges, and dependencies
- Analytical equations and material/property sources
- Geometry-construction algorithm
- Objectives and constraints
- Required simulations and acceptance limits
- Process-specific manufacturing rules
- Calibration parameters and physical-test lineage

Initial domain packages should be heat exchangers, turbomachinery flow paths, lightweight structural lattices, and electric-machine cooling—not rocket propulsion. Rocket engines require a dedicated propulsion organization, facilities, and regulatory/safety program.

### 2. Geometry worker fleet

Use separate kernel adapters behind a common job contract:

- Exact B-rep/CAD worker for prismatic parts, interfaces, datums, and STEP AP242
- Implicit/voxel worker for highly complex internal passages, lattices, and Boolean-heavy shapes
- Mesh/slicing worker for STL/3MF/CLI production output
- Drawing worker that derives sections, critical interfaces, and inspection sheets from the semantic model

PicoGK is a relevant production adapter: the official NuGet package is Apache-2.0 licensed and the current package identified during this build is 2.3.0 for .NET 9. The web MVP does not bundle it because PicoGK is a native/desktop-oriented C# kernel and the hosted app runs in a browser/edge environment. Reference: [PicoGK NuGet](https://www.nuget.org/packages/PicoGK).

### 3. Physics orchestration

Simulation must be a required gate, not decorative imagery:

- Conjugate heat transfer and pressure drop
- Linear/nonlinear structural analysis
- Modal, fatigue, creep, and thermal-cycle evaluation
- Electromagnetic analysis for motors
- Combustion/propulsion models only in a separately governed domain
- Mesh-convergence studies and uncertainty tracking

Every solver run stores its input deck, solver/container version, mesh statistics, residuals, convergence state, output checksum, and pass/fail criteria.

### 4. Optimization

Use a staged optimizer:

1. Analytical screening eliminates impossible designs cheaply.
2. Surrogate models explore the feasible region.
3. High-fidelity solvers validate finalists.
4. Robust optimization accounts for material, boundary-condition, and manufacturing variation.
5. Human review chooses the releasable design.

The optimizer never changes an undeclared parameter and never promotes a non-converged simulation.

### 5. Manufacturing compiler

Rules are specific to machine, material, orientation, and post-processing route:

- Minimum wall/channel/beam sizes
- Unsupported overhangs and trapped powder
- Drainage and depowdering access
- Surface allowance and machining datum stock
- Build-volume and recoater constraints
- Thermal-distortion compensation
- Inspection access and CT-resolution limits

## Worker contract

```json
{
  "job_id": "cem_01J...",
  "recipe_version": "heat-exchanger.v1.3.0",
  "kernel": "picogk-2.3.0",
  "resolution_mm": 0.25,
  "inputs": {},
  "objectives": [],
  "constraints": [],
  "manufacturing_profile": "lpbf-alsi10mg-machine-a",
  "required_outputs": ["vdb", "stl", "step-interfaces", "inspection-drawing"],
  "validation_profile": "thermal-core-release-v2"
}
```

The worker returns artifacts, hashes, resource use, diagnostics, and an explicit supported/unsupported list. It cannot return “certified” without the independent validation service.

## Development stages

### Stage A — present MVP

- Verified mechanical templates
- Implicit gyroid model and STL export
- Evidence manifests and refusal behavior

### Stage B — production geometry kernel

- Deploy C# PicoGK 2.3 worker on GPU-capable Windows/Linux compute
- Add robust mesh repair, watertightness, self-intersection, volume, and minimum-feature checks
- Add exact interface geometry and STEP boundary representation
- Persist recipes and immutable artifacts

### Stage C — first real CEM

- Select one thermal-core family and encode the full construction algorithm
- Couple a CFD/thermal solver and manufacturing constraints
- Run design-of-experiments and calibration coupons
- Compare generated results with instrumented physical tests

### Stage D — model platform

- Versioned domain SDK
- Solver and kernel plug-ins
- Distributed optimization
- Material/process database with provenance
- Test feedback and model calibration ledger

### Stage E — advanced machines

- Multi-component assemblies and interfaces
- Turbomachinery, motors, complex fluid systems
- Safety case, regulatory controls, and qualified release organization per domain

## What “beyond LEAP 71” would require

That claim cannot be established by visual complexity. It requires measurable superiority in at least one dimension:

- More validated engineering domains
- Higher physical prediction accuracy against test data
- Better multidisciplinary optimization
- Stronger manufacturing qualification
- Faster generation at equal fidelity
- More complete traceability and independent verification

The benchmark must be public and reproducible where intellectual-property and safety constraints permit. Until those results exist, EngiDraw should describe itself as a computational-engineering platform in development—not as superior to another organization.
