# VECTORONE XR — CS-02.2 first-principles prototype record

**Revision:** 0.2 · **Date:** 2 November 2026 · **Model scale:** 1:20  
**Design intent:** a printable, unpowered folding-mechanism demonstrator. It does not establish that a full-size road/air vehicle can fly, hover, drive, or carry people.

## Scope and rule for this study

This iteration uses the user's existing VECTORONE XR / CONTINUUM SPINE concept and first-principles geometry only. No external research, research papers, or other vehicle concepts were consulted. The dimensional starting points below are inherited from prior VECTORONE planning and remain provisional, not validated engineering requirements. The moving model demonstrates a proposed fold sequence; it does not include a lift system, flight-control system, continuous wing skin, road controls, or structural load qualification.

## Inputs and direct geometric results

| Quantity | Input / rule | 1:20 model result | Status |
|---|---:|---:|---|
| Overall body length | 5,200 mm ÷ 20 | 260 mm | inherited concept anchor, provisional |
| Deployed tip-to-tip span | 13,000 mm ÷ 20 | 650 mm | inherited concept anchor, provisional |
| Each centerline-to-tip distance | 650 mm ÷ 2 | 325 mm | direct geometry |
| Body width | chosen model packaging input | 52 mm | assumption; no road envelope supplied |
| Root hinge offset from body side | 52/2 + 6 mm | 32 mm from centerline | geometry / 6 mm offset assumption |
| Inner loop panel length | 180 − 32 mm | 148 mm each side | direct geometry |
| Outer loop panel length | 325 − 180 mm | 145 mm each side | direct geometry |
| Folded width envelope | 2 × (32 + 54/2) | about 118 mm | plan-view envelope from chosen chord and hinge geometry |
| Folded length envelope | 130 + 148 + 8 mm | about 286 mm | plan-view envelope; body half-length is 130 mm; 8 mm hinge offset |
| Folded height envelope | 44 + 145 + 2 mm | about 191 mm | raised mid-hinge plus outer-panel reach and 2 mm frame radius |
| Wheel radius | chosen model geometry | 15 mm | visual packaging assumption, not load-derived |
| Spine shell vertical offset | chosen model coordinate | 2.5 mm | CAD placement to keep the loft above the ground plane |
| Hinge pin / nominal bore | 3.0 / 3.6 mm | 0.6 mm diametral gap | provisional print fit; confirm with coupon |
| Wheel axle / hub bore | 4.6 / 5.4 mm | 0.8 mm diametral gap | axle is integral to spine; free-rolling fit is unverified |
| Wheel keeper bore | 4.8 mm over 4.6 mm axle | 0.2 mm nominal gap | split clip passes a 5.5 mm end shoulder; test before printing all |

The model geometry therefore fits the selected 1:20 length and span anchors exactly. Folded width, length, and height are calculated envelopes for this CAD arrangement, not a road-legality or storage claim. The selected wheel radius scales to a 600 mm full-size diameter; this conspicuously large result flags wheel packaging as an open design variable rather than a validated choice.

## Mechanism geometry

Each side uses a vertical-axis root pivot to swing its inner panel aft by 90°. A chordwise pin at the inner/outer joint lets the outer panel turn upward by 90° while stowed. That second hinge axis is set 8 mm above the wing frame; short vertical lugs connect it into the frame while keeping the pin bore clear of cross-members. When deployed, three 4 mm diameter spars and repeated cross-members form two open cells in each wing-loop panel. The root and outer pieces are separate print parts; the two hinge axes are represented with 3 mm pins and nominal 3.6 mm bores. The 0.6 mm diametral allowance is a starting geometry only. The fit coupon tests 3.2, 3.4, 3.6, and 3.8 mm bores against a 3 mm hinge pin. Its second row tests 4.4, 4.6, 4.8, and 5.0 mm bores against the 4.6 mm wheel axle before selecting the split keeper fit.

The spine has elliptical cross-sections along its 260 mm axis. The half-width and half-height are explicit station values in the parametric source; the tapered nose and tail avoid the earlier block-shaped shell. Paired diagonal yoke bars connect the root clevises to the spine shell. The inner wing root ribs stop at the outside of the root pin boss so the vertical hinge bore remains open.

Each wheel slides over a 4.6 mm axle that extends from the spine shell. A split printed keeper snaps over a 5.5 mm end shoulder; its 4.8 mm bore and 2.1 mm relief slot are provisional print geometry. The 5.4 mm wheel hub bore leaves 0.8 mm diametral running clearance around the axle. These are geometric fits only; rotation, retention force, wear, and printer/material behavior must be measured on the coupon and a single wheel corner.

The assembled STEP file is in the deployed pose. Individual STL files are the printable parts, in model coordinates. There are 21 part STLs including the coupon. A local STEP re-import reports valid geometry with 104 solids and an assembly envelope of 260 × 654 × 58 mm; the STL bounding box has a near-zero minimum Z from the wheel bottoms. The geometry uses no electric motors, propellers, batteries, suspension, steering, brakes, cabin interior, or aerodynamic skin. Do not use it as a powered model or load-bearing part.

## Physics findings and what is still unknown

### Hover

For an ideal static lifting disk of area `A` in fluid density `ρ`, let `vᵢ` be the induced speed through the disk. A steady momentum balance gives mass flow `ṁ = ρ A vᵢ`; the far-wake speed is `2vᵢ`, so thrust is `T = ṁ(2vᵢ) = 2ρ A vᵢ²`. Ideal power at the disk is `Pᵢ = T vᵢ`, therefore:

`vᵢ = √(T / (2ρA))` and `Pᵢ = T √(T / (2ρA))`.

For a vehicle in steady hover, total thrust must at least balance weight, `T ≥ mg`. This model supplies none of the needed vehicle mass, lifting-disk area, fluid-condition inputs, motor/drive efficiency, thermal limits, or safe control margin. Thus the equations identify required measurements but cannot justify a hover claim or size a propulsion system yet. The video’s lifted pose is explicitly a visual placeholder with no thrust model.

### Road motion

For a rolling wheel without slip, traveled distance per revolution is `2πr`, so this model's 15 mm radius implies 94.2 mm per wheel revolution. Wheel rotation in the animation illustrates this kinematic relation only; traction, suspension, steering, braking, tire deformation, and road stability are not modeled.

### Wingborne motion

These are open spars with no continuous lifting surface. They have no computed pressure distribution or momentum exchange, and no airspeed, mass, center of mass, control-surface geometry, or structural load case has been supplied. This version therefore cannot substantiate wingborne flight. The next useful engineering stage is to settle those inputs and create a continuous, measurable lifting surface before attempting fluid-flow calculations.

## Print and assembly sequence

1. Print one hinge/axle fit coupon and test both rows on the intended printer/material.
2. Print one wheel corner (axle + wheel + keeper) to measure free rolling and retention before making all four.
3. Select measured clearances, update the parameters, and regenerate all parts.
4. Print the spine/fairing, two clevises, four wing panels, four wheels, four keepers, and four hinge pins as separate files.
5. Dry-fit the root pins and chordwise pins; manually sweep both hinge axes and check full travel, body/wheel clearance, keeper retention, and free wheel rotation.
6. Record actual material, orientation, measured bore sizes, pin force, wheel drag, keeper force, and any interference as the first experiment receipt.

No printer build volume or material was supplied, so printer-specific orientations, supports, shrink compensation, and final fit remain to be set. The 4 mm frame bars are geometry suitable for a small demonstrator, not a strength rating.

## EngineAI Studio connection

The current local EngineAI Studio project is **VECTORONE XR CS-02.2 Prototype — Rev 0.2**; the initial iteration remains in **VECTORONE XR CS-02.2 Prototype — First Principles**. Rev 0.2 contains the 21 print-part STLs, assembly STL, STEP source, parametric source, findings, and visuals (29 files total). EngineAI's live 3D sandbox displays the deployed assembly STL and labels it “Visualization only—not engineering validation.” STL files do not encode units, so the STEP file remains the millimeter-based CAD source. The live preview endpoint did not convert the STEP source, so the sandbox uses the assembly STL. No FEA, CFD, or flight solver was run. Any future analysis there should use the explicit model inputs above and be reported as a new calculation or experiment; the unrelated built-in chamber-design preset is not part of this vehicle study.

## Findings log

1. A two-axis fold sequence can geometrically reduce the selected 650 mm spread to an estimated 118 mm plan width, with an estimated 191 mm folded height and 286 mm folded length.
2. The tapered station-loft spine and triangulated root yokes now provide printable geometry between the cabin shell, root clevises, and wing frame.
3. The concept’s provisional 5.2 m body and 13 m span scale to a model long enough to print as a 260 mm spine with 148 mm / 145 mm wing segments.
4. At these scale anchors, the chosen wheel geometry implies a 600 mm full-size diameter and should be revisited after road packaging requirements exist.
5. The open-loop frame alone is not a lifting wing. A propulsion concept and flight claim would be unsupported at this stage.
6. The first physical experiment should be the hinge/axle coupon, followed by one wheel corner; measured fits can update the parametric CAD without changing the concept scale.
