# N006 CPython uint64-shaped limb-emission refinement

Date: 2026-10-27

## Result

Lean 4.34.1 has checked a 64-bit `BitVec` accumulator model against the existing natural-number accumulator model for every finite little-endian limb list whose digits satisfy `digit < 2^30`.

The central results in `CPythonAccumulatorUInt64Refinement.lean` are:

1. `cWordLimbEmission_eq_cBinaryWriteLimbEmission`: the stateful 64-bit word model emits exactly the same LSB-first Boolean list as `cBinaryWriteLimbEmission 30` for every bounded limb list.
2. `cWordLimbEmission_value`: interpreting that output as a binary natural yields exactly `limbValue 30 limbs`.
3. `cWordLowerChunk_state_empty`: every bounded lower limb returns the 64-bit accumulator and pending-bit count to zero, so the next limb begins at the same boundary state.
4. `cWordTopChunk_value`: the final limb emits its canonical binary value and leaves accumulator zero.

This is a kernel-checked theorem about the explicit `BitVec 64` and `Nat` models. It is stronger than the previous Nat-only arithmetic result because the finite-width word operations are now simulated over the complete limb list. It is still **not** a formal theorem about CPython's C abstract machine, a compiler, or a built Python executable.

## Proof scope and dependencies

The model represents the unsigned accumulator with `BitVec 64`, extracts its low bit, inserts a 30-bit digit at the pending-bit position, shifts right logically, and models the lower-versus-top continuation guards. The induction uses the checked state-reset lemma after each lower digit and the normalized-digit bound `digit < 2^30`.

The successful compile's `#print axioms` output reports only `[propext]` and `[propext, Quot.sound]` for these results. The compile log contains `LEAN_EXIT=0` and no `sorryAx`.

Build details: Lean 4.34.1, commit `5045d0056413266e57c625dcd7c365b10e377c52`, native Windows executable. The workspace was the repository root; `LEAN_PATH` was the task directory. The compiler command was:

```powershell
& $lean -R (Get-Location).Path -o "$p\CPythonAccumulatorUInt64Refinement.olean" `
  "$p\CPythonAccumulatorUInt64Refinement.lean"
```

The relevant SHA-256 values are:

| Artifact | SHA-256 |
|---|---|
| Lean source | `38AF27C8BD4B333A64FE7A37AC15A5443514DB746852B57EEC88FA3BA0AB94EC` |
| Compiled OLean | `7FDDFA5BFAA1362D961ED4363432706AFCF3B3913BC802B120C17346870A8631` |
| Compile log | `66EEC27B40F286A15E69F3954B9B8FB4F58D4D25C0DC0748626290C7B985E669` |
| Imported Nat-model source | `805BCCEEB9F2052950EFC1C5B30AF762E794B429E2530E85B23013780BCB8095` |
| Imported Nat-model OLean | `86B0003A8EFD86AFFD891C39C2924E900A113E66CFB7380DABE995B05CBE7B3C` |
| Imported limb-model OLean | `1773BA8AB8095A34FFFD49E3078D56C38685BC188961FB41DF500E61089B5CE1` |
| Lean executable | `FCC4A10077D5FDD575592CEA5F2981C91CBD77C490C80BC74407908E57E8B87B` |

## Connection to the pinned source

The input source snapshot is the official CPython 3.14.7 `Objects/longobject.c` from the [`v3.14.7` tag](https://raw.githubusercontent.com/python/cpython/v3.14.7/Objects/longobject.c), saved beside this report and pinned by SHA-256 `7A6D6CB8D6480C6E8B0D388E9898A136F19DED2013155357EB014405EBC55864`. Direct enumeration of that exact local byte snapshot places `long_format_binary` at lines 2257–2419, the `WRITE_DIGITS` macro at 2330–2367, and the core accumulator update/guard at 2337–2351. The nearby source excerpt link in earlier records ended at line 2366, so it covered the accumulator core but not the entire function.

For the 30-bit configuration, CPython's pinned [`longintrepr.h`](https://raw.githubusercontent.com/python/cpython/v3.14.7/Include/cpython/longintrepr.h) selects `digit = uint32_t`, `twodigits = uint64_t`, and `PyLong_SHIFT = 30`; it describes little-endian digits, digit bounds, and the nonzero most-significant digit invariant for normalized nonzero values. `pyport.h` gives 30 as the default `PYLONG_BITS_IN_DIGIT`, but the headers document supported build configurations and do not attest the exact configuration of the separately installed Windows interpreter.

The code-level interpretation suggested by the proof is conditional: if the pinned routine executes with the stated 30-bit PyLong invariants and the standard unsigned 64-bit operations, then the word model captures the accumulator behavior. The source operations, C integer-conversion rules, shift-count preconditions, configuration macros, compiler output, executable identity, and runtime call path have not yet been formalized and proved to satisfy that condition.

### C shift-semantics reduction

The WG14 C11 committee draft N1570 supplies a precise bridge obligation: §6.5.7 requires each shift count to be nonnegative and less than the promoted left operand's width; an unsigned left shift is multiplication by the corresponding power of two modulo one more than the result type's maximum, and an unsigned right shift is integer division by that power of two. §7.20.1.1 defines an available `uintN_t` as an unsigned integer type of exactly N bits with no padding. These clauses are available in the [WG14 N1570 draft](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf).

Combined with the pinned CPython header's 30-bit configuration (`digit = uint32_t`, `twodigits = uint64_t`) and the checked word-model invariants, they reduce the C-expression proof to small obligations: (i) cast of a digit below `2^30` to `uint64_t` preserves its value; (ii) the insertion shift count at the start of each limb is zero, because every lower chunk resets the word state; (iii) the loop's right-shift count is the literal value 1; and (iv) `accumbits` remains in `[0,30]`, so its signed `int` updates do not overflow. Under those explicit premises, the C unsigned shift/OR/mask expressions have the corresponding 64-bit word values. This is a standards-guided proof plan and conditional derivation, **not** a Lean-checked C semantics theorem and not evidence about the actual interpreter's configure flags or binary.

## Remaining gap

Still open are: a formal C-fragment semantics and proof that the cast/left-shift/OR, low-bit mask, decrement, unsigned right shift, and branch guard refine the Lean word machine; the actual configured headers and compiler/build manifest for the running CPython; the `bin()` call path and returned Unicode data; the adapter's serialization and consumer parsing; resource limits; and the known concurrent-mutation snapshot-coherence counterexample. The result advances one precise arithmetic boundary and does not close Python-to-Lean refinement or complete N006.

## Preserved failed attempt

The first composition compile tried a nonexistent generated `.ext` theorem and failed to unfold the singleton reference emitter. That source state is preserved in `CPythonAccumulatorLowerChunk_FAILED_ATTEMPTS_20261027.md`. The accepted current Lean source is the one whose compile log above ends in exit 0; the failed attempt's `sorryAx` output is not accepted evidence.
