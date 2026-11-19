# C13-NX: Full-period two-axis physical-source reduced-model screen

Executed: 14 November 2026. This is **not a virtually verified engine** and **not nonlinear 3D finite-element analysis**.

## Geometry and model

- Four moving magnetic islands nominally 12 x 4 x 28 mm, spaced at 20 mm within a repeating 80 mm carrier pitch; four lower and four upper stationary 36-turn rectangular winding circuits, with loop interiors 12 x 20 mm, nominal centerlines at y=+/-13 mm. The field contribution of replicated local windings is summed through +/-6 additional 80 mm periods.
- Source fields come from the finite-segment Biot-Savart expression evaluated for four subfilaments per coil per period. The subfilament packing is *not a fully consistent solid-conductor winding geometry*: the copper-pack calculation assumes a separate 120 mm² winding cross-section and 60% fill. Coil window collision and end turns are unverified. The source basis file includes 121 carrier positions, 8 coil circuits and island volume quadrature points.
- Material islands are a distributed, **non-self-consistent**, locally saturating polarization response: `w'(B)=Ms*Bs*(sqrt(1+(|B|/Bs)^2)-1)`, with Ms=1.3 MA/m and Bs=0.6 T, chosen hypothetically. No actual measured B-H curve, demagnetizing interaction, eddy current, hysteresis or nonlinear field feedback is implemented. This means results can be badly wrong in magnitude or sign relative to a real magnetic assembly.
- The source basis is spatially derived from actual wire-loop coordinates rather than a prescribed sinusoidal flux-linkage law, but it does **not** include stationary core/return iron or permanent magnet field, and does not reproduce C13-NX's previous 3D source assembly. It screens a distinct air-core configuration only.
- Drive `i_j(x)=4+9.5 cos(2π x/80mm + j π/2 + φ)` A (upper and lower mirrored). A 145-phase scan selects the maximum predicted period work for each candidate volume/fill distribution; max instantaneous current 13.5 A. Separate quadrature inputs and upper-minus-lower currents supply the reduced model's three control variables.
- Winding: hypothetical 120 mm² copper-pack area per circuit, fill 0.60, 36 turns -> nominal 2 mm²/turn, at 80°C copper resistivity based on ρ20=1.724e-8 Ωm, temp coefficient 0.00393/K. Loop-only resistance 0.02454 Ω/circuit; excluding extra end turns. Allowable current density screening uses 5 A/mm² RMS.
- Full-period mechanical force `Fx=∂W'/∂x|i` was computed using a spatial derivative of the *source-computed* 3D magnetic field basis. Normal force `Fy=∂W'/∂y|i` used y-shifted source-field samples (±0.15 mm). Incremental winding linkage `λj=∂W'/∂ij`, stored island energy `U=Σ iλ-W'`, and source incremental work `∫Σ i dλ` derive from the same assumed co-energy. This is an internal algebraic reciprocity test, **not independent Maxwell-stress verification**.

## Results

Vehicle reference: 879.38 N/module average traction, 70.35 J/module/80 mm, 97.71 kW mechanical for a four-module 1500 kg vehicle at 100 km/h and 2m/s² under assumed road loads. The source configuration under study is only a single eight-coil 80 mm repeating experimental cell.

- Uniform four-island arrangement: after 145 drive phase trials, maximal positive work ~5.84e-9 J/80 mm (essentially zero); the spatially uniform four-island comb removes its first and second harmonics in the Fourier sum.
- Alternating island magnetic fill weighting [0.6,1.4,0.6,1.4] at unchanged total fill: maximum phase-optimized work **0.000180473 J per 80 mm**; average tangential force **0.00225592 N**, peak |Fx| ~0.01167 N. This is ~389,808x lower than the full-module work requirement. These are **model outputs, not measured or nonlinear FEM validated force**.
- Estimated copper loss for eight local coils at 100 km/h ~12.0 W, or ~0.0345652 J over each 80 mm transit. Modeled output power ~0.06266 W at 100 km/h, giving an illustrative copper-only electromechanical fraction `Wmech/(Wmech+Ecopper)=0.5194%` (not actual motor efficiency, as source fields and losses are incomplete).
- The alternate supported symmetric mid-plane has Fy≈0 by geometric symmetry. Local magnetic normal stiffness `dFy/dy`=+3.80 to +8.37 N/m, with destabilizing sign in the assumed model; it is NOT a load-bearing or dynamically stable support system. Reduced local force-current control matrix `d(Fx,Fy)/d(u_cos,u_sin,u_support)` had positive minimum second singular value ~0.000185 N/A, establishing only the **approximate local rank** of the surrogate. Static module support load 3679 N, structural feedback, full control/thermal limits and guide stability are not solved.
- The alternating model's internal coenergy accounting at 120 intervals: `W_mechanical=0.000180473 J`, `∫i dλ≈0.000181450 J`, `ΔU≈2.4943e-9 J`, reconciliation residual ≈9.74e-7 J (about 0.54% of the tiny calculated mechanical work). At 60 intervals work is 0.000180493 J; at 30 it is 0.000180531 J. Those sampling comparisons do not constitute nonlinear 3D field/force convergence or Maxwell-stress independence.
- Spot check of finite-source repetition: comparing +/-6 and +/-8 unit-cell replicas changed the field by ~0.005%-0.054% of representative maximum values across four selected circuits and four positions, but this is not a full exterior boundary convergence test.

## Important newly identified mechanism

The Fourier coefficient of a four-island moving magnetic density for spatial harmonic n is proportional to `Σ_{j=0}^3 ρj exp(-i n j π/2)`. Equal `ρj` eliminate all n not multiples of four. Alternating fill introduces a second spatial harmonic and removes part of the cancellation. **This is a mathematical topology-selection principle, not proof that the altered geometry is optimal or manufacturable.**

## Failed/unperformed gates

- Does **not** generate 879.38 N average forward traction or 70.35 J positive full-module period work. It fails these by orders of magnitude in the trial source geometry.
- No self-consistent nonlinear 3D Maxwell field in actual iron, no measured B-H or conductivity, no finite-winding 3D magnetoquasistatic solve, no independent Maxwell-stress versus coenergy force convergence, no core/eddy/hysteresis loss and no thermal CFD or mechanical fatigue/braking model.
- The source and island positions and conductor-pack assumptions need actual CAD collision checks before being treated as physically fabricable.
- Positive rank of a reduced force-control Jacobian neither demonstrates 3679 N static structural support nor a stable closed-loop gap at operational field strength.
- The original R9/R10 failures remain **open**; this reduced model has not repaired them. No claim is made that C7-P1 or C13-NX is virtually proven.

## Next falsification test

Create interference-free stationary source and moving island CAD with **actual copper-pack cross sections and individually insulated material islands**. Solve the nonlinear, material-specific 3D vector-potential/circuit formulation with moving mesh/ALE or verified sliding interface; compute closed-surface Maxwell stress and force from magnetic virtual work for all positions over an entire 80 mm period, showing mesh/boundary/surface/time-step convergence. Only then compare independently controlled traction and normal support, actual winding power, induced currents and structural/thermal energy closure. Preserve these negative results and all R9/R10 failures.
