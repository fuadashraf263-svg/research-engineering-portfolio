# N006: runtime integer-layout evidence and C counter reduction

**Date:** 2026-10-27
**Status:** runtime/build-layout evidence reproduced; source counter bound derived conditionally; formal C-to-Lean theorem still open.

## Runtime evidence

The active executable is `C:\Python314\python.exe`, CPython 3.14.7, 64-bit Windows, executable SHA-256 `4942B86A6597E5AEE0128DAA00050ED79BC21F6E709A78EB19CBFEB0C2F39AC9`. Its read-only `sys.int_info` reports `bits_per_digit = 30` and `sizeof_digit = 4`.

I downloaded the two pinned CPython v3.14.7 headers from the official GitHub raw source and compared them to the installed headers. Raw hashes differed because the installed copies use CRLF while GitHub's raw source uses LF. After UTF-8 BOM removal and newline normalization, contents were identical:

| Header | Official raw SHA-256 | Installed raw SHA-256 | Newline-normalized SHA-256 | Result |
|---|---|---|---|---|
| `Include/cpython/longintrepr.h` | `BA3E5C1E2E34CE5EC4F46C9DA6C7FA519D47C7392FB98D61E32BC6DB8CF8CEFC` | `01016962EBD3CD16B4D9BDF29AC71753C897B7A937EF6E32FF601C6C0CB755EC` | `BA3E5C1E2E34CE5EC4F46C9DA6C7FA519D47C7392FB98D61E32BC6DB8CF8CEFC` | text identical |
| `Include/pyport.h` | `76826E8D8C98FD82E4E9E83E4545DA3219A1052ACA056772E4E5CF06FBDD4983` | `CB07FE47E2CB58CFDDAEE0466759C7911B6E163AF2F105E822091D96CBBFC7DD` | `76826E8D8C98FD82E4E9E83E4545DA3219A1052ACA056772E4E5CF06FBDD4983` | text identical |

The tagged `longintrepr.h` states that the 30-bit configuration uses `digit = uint32_t`, `twodigits = uint64_t`, and `PyLong_SHIFT = 30`; it also states the normalized-top-digit and limb-bound conditions. `pyport.h` defaults `PYLONG_BITS_IN_DIGIT` to 30 unless a build configuration overrides it. The runtime `sys.int_info` directly reports the active digit size and width, agreeing with this header configuration. This is stronger runtime configuration evidence than assuming the default, but it does not prove that the executable was compiled from those exact headers or from the pinned C source.

## Conditional counter and shift derivation from the pinned source

The source's `long_format_binary` chooses `bits = 1` when `base == 2`; the `WRITE_DIGITS` loop initializes `accumbits = 0`, inserts a digit shifted by `accumbits`, adds `PyLong_SHIFT`, emits a bit, decrements `accumbits`, performs unsigned `accum >>= 1`, and uses the lower-limb guard `accumbits >= bits` or the top-limb guard `accum > 0`. Zero (`size_a == 0`) bypasses the accumulator loop.

Assume the runtime reports 30-bit digits as above, every nonzero PyLong is normalized, and the pinned source path is the one executed. Then:

1. Initially, and after every non-top limb, `accumbits = 0`. For a lower limb, insertion starts at shift 0 and `accumbits` becomes 30. Each do-while pass subtracts one; the lower-limb guard is true exactly while the new count is at least 1. Thus the loop executes 30 passes with counter values before decrement `30, 29, ..., 1`, and exits at 0. Shifting a 30-bit limb right 30 times leaves `accum = 0`.
2. A normalized nonzero top limb `d` satisfies `1 ≤ d < 2^30`. It begins with `accum = d`, `accumbits = 30`. Its do-while performs exactly `bit_length(d)` shifts, at most 30, because each pass applies unsigned right shift by 1 and the loop stops when `accum == 0`. The final counter is `30 - bit_length(d)`, hence in `[0,29]`.
3. The zero representation bypasses the loop. Therefore every executed `accumbits` value stays in `[0,30]`, and every signed-int increment/decrement stays in that range. WG14 N1570's minimum required `INT_MAX` is 32767, so these updates fit any conforming `int`.
4. The insertion shift count is 0 at each limb boundary, and the inner right-shift count is 1. Both are below 64. Under the unsigned 64-bit type premise, C's unsigned shift rules correspond to the 64-bit word operations in the Lean model: left shift is modular by the result width; unsigned right shift is division by the power of two. The mask is the low bit. A digit below `2^30` cast to `uint64_t` preserves its value.

This derivation isolates the remaining formalization: define an explicit C-fragment semantics with signed `int` counter and unsigned 32/64-bit operands; prove its valid transitions equal the existing Lean `BitVec 64` step; prove the source guard produces only the bounded transitions above; then bind the premises to the actual source and executable. The reasoning here is a human derivation from source, runtime metadata and the C committee draft, **not a Lean-checked C semantics theorem**.

## Primary sources

- CPython v3.14.7 [`longintrepr.h`](https://github.com/python/cpython/blob/v3.14.7/Include/cpython/longintrepr.h) and [`pyport.h`](https://github.com/python/cpython/blob/v3.14.7/Include/pyport.h).
- Pinned CPython [`Objects/longobject.c`](https://github.com/python/cpython/blob/v3.14.7/Objects/longobject.c), `long_format_binary` / `WRITE_DIGITS`.
- Python [`sys.int_info`](https://docs.python.org/3.14/library/sys.html#sys.int_info) documents the meaning of `bits_per_digit` and `sizeof_digit`.
- WG14 committee draft N1570, §5.2.4.2.1 gives the minimum `int` range and §6.5.7 defines shift-count and unsigned-shift semantics: [official N1570 PDF](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf).

## Evidence files and limitations

The machine-readable runtime evidence is `cpython_runtime_integer_layout_evidence_20261027.json`; the reproducible probe is `probe_cpython_runtime_integer_layout_20261027.py`. Official header snapshots are stored as `cpython-v3.14.7-longintrepr.h` and `cpython-v3.14.7-pyport.h` beside them.

Still open: compiled-source/build-configuration attestation; Lean formalization of C integer promotions, shifts, counter and loop; proof the Python transcription refines the Lean function; output and JSON/consumer correspondence; resource bounds; concurrent snapshot coherence; production adoption. No all-input CPython refinement or N006 completion is claimed.
