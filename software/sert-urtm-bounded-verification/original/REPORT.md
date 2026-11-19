# SERT / URTM-R2 bounded verification — 2026-11-12

## Scope and assumptions
Executed Python/NumPy reference tests; no fracture PDE, bone dataset or physical experiment executed. All quantities nondimensional. The localization benchmark is a uniform 1D bar, L=A=E=1, imposed u(x)=x. Thus strain=1 and energy density=0.5. The fixed physical region is x in [0.35,0.65]. Piecewise-constant element density is integrated with exact interval overlap. This is an analytical patch test, not a general proof of mesh-objectivity for fracture.

## Numerical findings
n=10,20,40,80,160: global energy = 0.5 to machine precision; window energy = 0.15 to machine precision; window fraction = 0.3. Naive unweighted sums of selected element energies are 2,3,6,12,24 and are not objective. The selection by element center also introduces boundary quantization. Thus a *fixed physical integration domain* and proper element measures are essential. The benchmark is deliberately too simple to establish nonuniform-field or mesh-rotation invariance.

## Parallel-bar redundancy / progressive removal
Three parallel unit-stiffness members, each with extension failure threshold 0.2,0.3,0.4. Under prescribed displacement, the intact response is P=3u until first failure at u=0.2; after removal P=2u until u=0.3; then P=u until u=0.4; afterwards P=0. Under force P=0.5, intact equilibrium u=1/6 is admissible. Removing first member externally gives u=0.25 (two survivors, admissible). Removing second gives u=0.5, exceeding survivor threshold 0.4: no stable equilibrium under P=0.5. Sum of individual force thresholds 0.9 is NOT the actual system peak force; the maximum of the displacement-controlled force envelope is 0.6 (immediately before first and second failure). This distinction is an explicit capacity-baseline check.

At fixed u=0.2, instantaneous deletion of a unit-stiffness member removes stored elastic energy 0.5*(0.2)^2=0.02. A fracture/dissipation/kinetic energy ledger must account for that release. The toy model does not determine which mechanism receives it. Therefore deletion alone cannot demonstrate thermodynamic consistency.

## Evidence levels and failures
Mathematical: exact integration of constant energy density gives 0.15; elementary spring-force formulas give above thresholds. Numerical: script reproduces the identities and shows naive sums vary 12x from n=10 to n=160. Empirical: none. No nonlinear fracture simulation, exact contact test, crack path convergence, rotated meshes, or trabecular-bone dataset evaluation performed. The example is an established finite-element integration and parallel-spring baseline, not evidence that SERT outperforms standard mechanics.

## Next falsification gate
Use a nonuniform, singularity-regularized strain field on rotated triangular meshes with a fixed physical averaging radius; compare volume-integrated localization and peak load at h/r=1/2,1/4,1/8,1/16, and quantify errors against an independent high-resolution reference. Then add progressive energy-consistent damage and compare crack initiation against standard Griffith/phase-field baselines. For public bone data, require documented dataset license, voxel spacing, specimen boundary conditions and independent measured load response before reporting validation.

## Reproduce
`python test.py` regenerates `mesh_localization.csv`, `truss_baselines.csv` and prints JSON. Python 3 with NumPy required. Exact source and results are included.
