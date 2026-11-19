# CRFCE C13-NX — R12-B source-CAD and winding feasibility audit

**Date:** 14 November 2026 | **Scientific status:** Conditional geometry/energy screen completed; **NOT VIRTUALLY PROVEN**.

## 1. Evidence and limits

This study programmatically reopens `C13_NX_source_trial_58solids.step` using CadQuery/OpenCascade, checks the source-solid extents, and calculates independent idealized Maxwell-stress, copper-window and gap-dominated magnetic-MMF necessary conditions. It is **not** nonlinear 3D electromagnetic simulation, measured material characterization or an experiment. The STEP product itself identifies a research geometry not approved as hardware. All values should be checked against original CAD before fabrication.

The archived full-period reduced-source model is a *different, air-core/surrogate magnetic-material calculation*; its predicted forces cannot be transferred to the present STEP iron/magnet assembly. Likewise, the R9/R10 failed force-convergence gates remain open.

## 2. Source STEP facts (verified by script)

| Source property | Inspected value |
|---|---:|
| Source-solid count | 58 |
| Moving high-permeance islands | 4 |
| Island dimensions (x,y,z) | 12 × 4 × 28 mm |
| Island x centers | -28.0, -8.0, 12.0, 32.0 mm |
| Repeated pitch | 20 mm |
| Upper/lower pole face air gaps | 1.5 / 1.5 mm |
| Nominal active x-z island face area (one side, four islands) | 1344 mm² |
| Winding placeholder bars | 32; each 1 × 1 mm transverse section |
| Continuous carrier rails | 2 |

The field-face area is the **sum of four planar moving-island projections**. It is not a guaranteed effective Maxwell stress integration surface: flux fringes, end effects, and the full closed surface must be solved in a conforming 3D model.

## 3. C13-NX vs R11 active-area mismatch

R11 used A = 8,000 mm² for simultaneous Fₓ=879.38 N and Fᵤ=3,679 N. The source CAD has 4×12×28 = **1,344 mm² per one face**, 5.95× less. Conditional ideal *uniform* same-face Maxwell stress is

- tau = Bn Bt / μ0 = Fx / A
- p = (Bn² − Bt²)/(2μ0) = Fz / A.

| Assumed area | Bn required | Bt required | Combined | Interpretation |
|---|---:|---:|---:|---|
| 8,000 mm² | 1.083 T | 0.128 T | **1.090 T** | R11_assumed_area |
| 1,344 mm² | 2.641 T | 0.311 T | **2.660 T** | CAD_4_islands_one_face |
| 2,688 mm² | 1.868 T | 0.220 T | **1.881 T** | conditional_two_faces |
| 25,000 mm² | 0.612 T | 0.072 T | **0.617 T** | historical_250cm2_assumed_area |

This condition is only relevant **if the traction and full 3,679 N support load are required through the same active face**. The actual static road load can be transmitted through mechanical supports rather than magnetic suspension, and upper/lower Maxwell stress surfaces may partly oppose, not simply add. Do not apply this table as an unconditional design rejection.

Under an illustrative maximum combined working-gap field of 1.5 T, the ideal same-face requirement gives A ≥ **4225 mm²**, or **3.14×** the current source island area, before allowing for leakage, fringing and nonuniform stress. This is a necessary screening condition for that explicitly chosen force-allocation scenario, not a validated material performance cap.

## 4. Actual conductor packaging — fundamental CAD mismatch

The STEP stores each loop as four solid bars with 1 × 1 mm transverse sections. These are placeholders for **eight electrically excited 36-turn windings**. The STEP has no insulated 36-turn copper packing solids, no manufactured terminals or end turn geometry. For a reference fill factor 0.60 and provisional allowable current density 5 A/mm² RMS,

`A_pack >= N * I_RMS / (J_allow * fill)`.

| Current condition | RMS A | Minimum pack per circuit | Copper heat, all eight* |
|---|---:|---:|---:|
| reduced model I rms | 7.818 | 93.8 mm² | 15.35 W |
| peak 13p5 as continuous | 13.500 | 162.0 mm² | 26.51 W |
| peak 150 sinusoidal | 106.066 | 1,272.8 mm² | 208.26 W |
| 150 continuous | 150.000 | 1,800.0 mm² | 294.52 W |

*Joule-loss estimates are DC-resistivity-only using a **64 mm mean path per turn**, 36 turns, copper resistivity 1.724×10⁻⁸ Ω·m at 20°C, α=0.00393/K and 80°C winding temperature, with conductor size **redesigned for each current case** to meet 5 A/mm². No proximity/skin/core/inverter losses; loop-only length excludes winding bends and added terminations. These are hypothetical design sizes, not the unchanged STEP geometry.*

The prior reduced calculation specified a separate, hypothetical **120 mm² pack** (60% fill, 36 turns, 2 mm² bare copper per turn), which gives RMS current 7.818 A, current density **3.909 A/mm²**, 80°C resistance **0.02454 Ω/circuit** and eight-winding Joule loss **12.00 W**. That arithmetic is internally consistent under the assumed 64 mm mean turn path, but the 120 mm² pack is not in the STEP CAD. It must be physically placed, insulated, and checked for collision with the core, magnets, neighboring loops and thermal network.

At 13.5 A continuously and 5 A/mm², a 36-turn coil requires **162 mm² of winding pack**; with the reduced-model waveform, the **RMS** pack requirement is approximately **93.8 mm²**, with potentially higher instantaneous current density. For the earlier 150 A-peak sinusoidal trial, **1273 mm²** is needed per winding at this RMS criterion. These requirements cannot be interpreted as 1 mm² wire placeholders in the present STEP file.

## 5. Gap-only magnetomotive force limit (conditional)

For two series 1.5 mm gaps, with no permanent-magnet bias or return-path reluctance, Ampere's law gives `NI >= B * 0.003/mu0`.

To produce only the **R11 ideal Bn=1.083 T** from a winding source: NI ≥ **2585 A-turns**. The archived 36-turn × 13.5 A trial produces only **486 A-turns**, giving **0.204 T** in that *ideal, coil-only two-gap series circuit*. A permanent magnet can provide bias, and the real circuit may not present both gaps in series to each winding; therefore this is **not** a bound on the complete magnet-assisted C13-NX device. Its use is to reject the unsubstantiated claim that low-current coils alone can supply all assumed R11 fields.

## 6. Verification register

| Gate | Decision |
|---|---|
| Source STEP solids, island size, core gaps | **Checked in source CAD** |
| R11 A=8000 mm² assigned to four-island face | **FAIL: source face only 1344 mm²** |
| 36-turn finite conductor pack in saved STEP | **FAIL: 1×1 mm placeholder only** |
| 120 mm² copper-pack arithmetic | Conditional algebra check consistent; CAD pack **missing** |
| R9 physical flux linkage / independent vertical authority | Prior **FAIL** retained |
| R10 nonlinear force and linkage convergence | Prior **FAIL** retained |
| Source-resolved measured-BH nonlinear 3D fields | **OPEN** |
| Independent Maxwell-stress vs co-energy force | **OPEN** |
| Rank-2 practical current-to-force G over full pitch | **OPEN** |
| ≥70.35 J period work, full electrical ledger | **OPEN** |
| Thermostructural support/clearance/braking | **OPEN** |
| Complete engine virtually proven | **NO** |

## 7. Next geometry/physics decisions (no design approval)

1. Resolve whether the **3,679 N module load** is carried mechanically, magnetically or by a quantified combination; allocate an actual force-contour area for each mechanism.
2. Generate a physically packed 36-turn coil in CAD with specified strand size, insulation, lead routing, current waveforms and fill; permit shared excitation or a changed turn count if packaging fails.
3. Specify **measured** iron B–H and losses, permanent-magnet recoil/demagnetization and copper conductivity; the current surrogate cannot support material approval.
4. Independently perturb propulsion and support windings over each moving position; calculate the real winding-to-field matrix G, then force-control rank, singular values, voltage and current limits.
5. Require converged 3D H(curl) moving-mesh/circuit force and linkage, both via Maxwell stress and virtual work, followed by energy, thermal, structural and braking closure.

The existing STEP is a useful source record of a *trial solid layout*, but it does not contain enough authoritative physics or conductor assembly geometry to claim virtual proof. This R12-B audit adds independently inspectable geometric **rejection criteria**, not a new successful engine.

## Reproduction

`python r12b_cad_winding_audit.py --step C13_NX_source_trial_58solids.step --out .`

The accompanying CSVs, JSON, charts and input STEP are provided to audit these calculations. No numerical field-solver run was performed in this investigation.
