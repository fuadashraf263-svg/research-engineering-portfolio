# N006 base-2 writer capacity: source derivation and checked boundary

Date: 2026-10-27

## Result

For the pinned CPython 3.14.7 base-two formatting path, the explicit exact-capacity premise used by `cIntLimbEmission_output_complete` reduces to a small identity once the representation is normalized and the build uses 30-bit digits. For a nonzero magnitude represented by `k >= 1` limbs `a[0] ... a[k-1]`, with each `0 <= a[i] < 2^30` and `a[k-1] != 0`, let `t = bit_length(a[k-1])` and `W = 30(k-1)+t`. Then the mathematical magnitude has bit length `W`, the base-two `WRITE_DIGITS` loop emits `W` bits, and CPython's computed character capacity is `W + negative + 2*alternate`. Thus it equals the body digits plus the optional sign and `0b` prefix. For zero, CPython takes a separate branch: capacity is one digit, plus an optional two-character prefix, and the writer emits the single character `0`.

This is a source-level derivation and a model bridge plan. It is **not** a Lean-checked theorem about CPython's C implementation or installed executable. The already compiled Lean composition still assumes exact capacity as `hcapacity`.

## Mathematical derivation

Set `B = 2^30`. CPython's published representation states that the magnitude is `N = sum(i=0..k-1) a[i] B^i`, each limb lies in `[0,B-1]`, and a normalized nonzero integer has nonzero highest limb. The 30-bit configuration uses unsigned 32-bit `digit`, unsigned 64-bit `twodigits`, and `PyLong_SHIFT = 30`.

For nonzero `a[k-1]`, define `t` by `2^(t-1) <= a[k-1] < 2^t`, where `1 <= t <= 30`. The top-limb contribution gives `N >= a[k-1] B^(k-1) >= 2^(t-1+30(k-1)) = 2^(W-1)`. The lower limbs together contribute at most `B^(k-1)-1`, so `N < 2^t B^(k-1) = 2^W`. Therefore `bit_length(N)=W`.

In the binary writer, `bits=1`. Each non-top limb contributes exactly 30 loop iterations: the `i < size_a-1 ? accumbits >= bits` guard drains all 30 accumulated limb bits, including zero-valued bits, before advancing. On the final limb the `accum > 0` guard drains through the most significant set bit. Since the normalized top limb is nonzero, exactly `t` final iterations occur. The total number of body writes is `30(k-1)+t=W`.

The source's nonzero capacity computation is `size_a_in_bits = (k-1)*PyLong_SHIFT + bit_length_digit(top)` followed by `sz = negative + (size_a_in_bits + (bits-1))/bits`; for base two, `bits=1`, so `sz = negative + W`. The alternate-form branch then adds 2 for the prefix. Thus `sz = W + negative + 2*alternate`, matching the writer's body, sign, and prefix count.

For `k=0`, CPython takes a distinct branch setting `sz=1`; the writer takes its `size_a==0` branch and writes `'0'`, never a negative sign for zero. The alternate branch adds two characters. This gives `sz=1+2*alternate`.

The overflow guard precedes the nonzero capacity arithmetic: `k <= floor((PY_SSIZE_T_MAX-3)/30)`. Since `W <= 30k`, `negative <= 1`, and the prefix is at most 2, `sz <= 30k+3 <= PY_SSIZE_T_MAX`. This is the source arithmetic argument that the final capacity expression itself does not overflow, under the stated 30-bit configuration and the source's integer-width assumptions. It does not prove allocation success.

## Essential counterexample to an overbroad model theorem

The existing Lean limb emitter's raw type admits `[5,0]`. In the source-shaped loop, the first limb emits 30 bits and the zero top limb still executes the `do` body once, for 31 emitted bits. The size formula computes `(2-1)*30 + bit_length(0) = 30`. Therefore arbitrary bounded limb lists do **not** satisfy the proposed capacity identity. This is a counterexample to a theorem over the current unconstrained list type, not a valid CPython integer: the normalized-PyLong invariant excludes a zero top limb. The formal theorem must encode either `k=0` or `k>0 ∧ top≠0`.

## Executed evidence

`CPythonBase2CapacityProbe.py` was rerun in this workspace and exited 0. It reports CPython 3.14.7, 30 bits per digit, 3,061 normalized magnitude cases (including zero), 12,242 actual `format(value, 'b')` / `format(value, '#b')` cases, a maximum tested magnitude width of 30,720 bits, and the `[5,0]` counterexample above. Its receipt pins the local CPython source SHA-256 `7a6d6cb8d6480c6e8b0d388e9898a136f19ded2013155357eb014405ebc55864`.

These are bounded runtime and transcription checks. They do not imply a universal result by induction, prove the source transcription correct, identify every compiler flag of the binary, or establish C pointer/allocation behavior.

## Formalization update — 2026-10-27

The model-level length gap is now closed in `CPythonBase2CapacityRefinement.lean`. Under `Normalized30`, Lean proves that the typed signed-counter limb emitter has exactly `sizeAInBits30 limbs` output bits, where the formal size function uses one character for the zero branch and, for a nonempty list, `(length - 1) * 30 + Nat.log2(final limb) + 1`. The theorem `cIntLimbEmission_output_complete_of_sizeAInBits30` then derives the output-composition theorem's prior `hcapacity` premise from the corresponding formal cursor-size equation. The proof explicitly excludes `[5,0]` through the nonzero-top-limb invariant.

The exact ten-module import closure, including this theorem, compiled twice with Lean 4.34.1, warnings-as-errors, no `sorryAx`, and identical OLean hashes. See `N006_CPYTHON_BASE2_CAPACITY_LEAN_BRIDGE_20261027.md` and queue key `n006_fresh_lean_cpython_final_chain_20261027` for hashes and compile logs. This is a proof about the typed model and its explicit size expression. It does not verify CPython's C source or executable, prove allocator/pointer behavior, or eliminate the model input equating the actual buffer cursor with `sizeAInBits30` plus the modeled sign/prefix characters. The Python/C/runtime refinement and other listed integration gaps remain open.

## Precise Lean target

Add a normalized limb predicate with two constructors/cases: (i) empty limbs represent zero, or (ii) nonempty limbs have all limbs `< 2^30` and a nonzero final limb. Prove, for case (ii), the limb value's bit length is `(length-1)*30 + Nat.log2(top)+1`; then prove the source-shaped binary loop emits a little-endian Boolean list of exactly that length whose value is the limb value. Prove the zero branch separately. Combine these with the arithmetic identity for `sz`, the sign/prefix counts, and the already checked output-writer theorem to discharge `hcapacity` **inside the model**.

The C-to-Lean correspondence still needs a checked source-fragment semantics or a proof-carrying AST/trace relation; the current source derivation is not that proof. Allocation success, pointer validity, Unicode representation/build profile, error/return behavior, the exact installed interpreter, adapter/JSON behavior, and global snapshot coherence remain separate obligations.

## Source basis

- CPython 3.14.7 `longobject.c`: base conversion capacity, overflow guard, binary digit loop, and output writer.
- CPython 3.14.7 `longintrepr.h`: 30-bit representation parameters, limb-value equation, normalization, and limb bounds.
- CPython 3.14.7 `pycore_bitutils.h`: `bit_length_digit`'s underlying bit-length convention.

## Scope statement

This is one concrete refinement step in N006 and evidence that a specific model-level premise is derivable from a normalized PyLong representation. It is not a completed proof of the Python/C runtime and does not complete the larger mathematics-of-discoverable-measurement program. No new universal mathematical system, novelty, or broad superiority claim is made.
