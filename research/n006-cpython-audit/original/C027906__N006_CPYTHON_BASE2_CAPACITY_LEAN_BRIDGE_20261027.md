# N006 normalized 30-bit base-two capacity bridge

Date: 2026-10-27

## Checked result

`CPythonBase2CapacityRefinement.lean` formalizes the normalized-limb boundary and proves that the typed limb emitter's body length agrees with an explicit model of CPython's base-two `size_a_in_bits` expression:

* `Normalized30` admits the empty list as zero, or a nonempty little-endian list whose limbs are all below `2^30` and whose final limb is positive.
* For a nonzero top limb, `binaryTopLength` proves that the source-shaped top loop emits `Nat.log2 top + 1` bits.
* `binaryLimbEmissionLength` composes 30 emitted bits for every lower limb with the top-limb bit length. The zero list follows the distinct one-character branch.
* `bodyBitCount_eq_sizeAInBits30` proves this count equals the model expression `sizeAInBits30`.
* `cIntLimbEmission_length` transfers the exact length to the existing signed-counter/BitVec64 emitter using its checked refinement theorem.
* `cIntLimbEmission_output_complete_of_sizeAInBits30` derives the prior composition theorem's `hcapacity` premise from an explicit cursor equation using `sizeAInBits30` plus the modeled sign and alternate-prefix counts.
* `normalized30_excludes_zero_top_counterexample` rejects `[5,0]`; that non-normalized list remains a real counterexample to the overbroad earlier claim.

The complete ten-module dependency chain, including this new file, compiled twice under native Windows Lean 4.34.1. Both builds used `-DwarningAsError=true` and one Lean thread. All module exit codes were 0, no log contained a warning, error, or `sorryAx`, and each OLean hash matched across the two builds. The exact source hashes, OLean hashes, logs, and release archive digest are recorded in `lean-chain-fresh-20261027T131612Z/verification.json` and queue record `n006_fresh_lean_cpython_final_chain_20261027`.

## Exact boundary

This closes a typed-model obligation, not the CPython implementation proof. `sizeAInBits30` is the formal arithmetic model of the pinned source's size formula; this theorem does not verify the C expression, `PyLong` memory layout, compiler configuration, a particular executable, or execution-character-set assumptions. The composition theorem still receives `buffer.cursor.val = sizeAInBits30 limbs + sign/prefix counts` as a model input. No theorem here shows CPython's allocator actually creates that buffer or that the C pointer writer obeys the abstract buffer model.

The remaining refinement boundary includes a formal source-to-Lean translation or proof-carrying parser for the pinned C fragment; C signed/unsigned operations and defined-behavior assumptions; `size_a_in_bits` and `sz` evaluation; allocation success and pointer safety; returned string/error behavior; executable/build identity; input-to-PyLong normalized representation; adapter and JSON behavior; and global snapshot coherence. The known concurrent-mutation counterexample remains. This is a concrete proof improvement in one N006 subproblem, not completion of N006, proof of physical accuracy, or evidence of universal superiority or novelty.

## Sources

The source arithmetic being modeled is in [CPython 3.14.7 `longobject.c`](https://github.com/python/cpython/blob/v3.14.7/Objects/longobject.c#L2288-L2408); the 30-bit digit layout and normalized top-limb contract are in [CPython 3.14.7 `longintrepr.h`](https://github.com/python/cpython/blob/v3.14.7/Include/cpython/longintrepr.h#L568-L687). The source comparison remains a human derivation; these citations do not imply a mechanically checked source translation.
