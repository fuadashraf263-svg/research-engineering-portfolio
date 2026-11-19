#!/usr/bin/env python3
"""
units.py - dimensional safety for EngineAI.

Two jobs:
  1. AUDIT   check every reference formula is dimensionally consistent with the
             unit it claims to produce. A formula that is dimensionally wrong is
             wrong, full stop - and this catches it without any test data.
  2. GUARD   accept inputs with units ("--L 1000mm"), convert to SI, and warn
             when a bare number looks like the wrong unit for that quantity.

  python units.py audit          check all reference formulas
  python units.py parse 1000mm   show the conversion
  python units.py selftest
"""
import os, re, sys, math

# physical dimension of every symbol used in the reference library
DIMS = {
    # loads and moments
    "P": "newton", "F": "newton", "W": "newton", "w": "newton/meter",
    "T": "newton*meter", "M": "newton*meter", "Mt": "newton*meter",
    # lengths
    "L": "meter", "a": "meter", "b": "meter", "c": "meter", "d": "meter",
    "r": "meter", "t": "meter", "h": "meter", "x": "meter", "y": "meter",
    "e": "meter", "D": "meter", "Ri": "meter", "Ro": "meter", "ri": "meter",
    "ro": "meter", "s": "meter", "Le": "meter", "k": "meter", "delta": "meter",
    # section properties
    "I": "meter**4", "J": "meter**4", "A": "meter**2", "Z": "meter**3",
    "Q": "meter**3", "Ip": "meter**4",
    # material
    "E": "pascal", "G": "pascal", "K": "pascal", "Sy": "pascal", "Su": "pascal",
    "Se": "pascal", "nu": "dimensionless", "alpha": "1/kelvin",
    "rho": "kilogram/meter**3",
    # stresses and pressures
    "p": "pascal", "pi_": "pascal", "po": "pascal", "sx": "pascal", "sy_": "pascal",
    "txy": "pascal", "s1": "pascal", "s2": "pascal", "sm": "pascal", "sa": "pascal",
    # thermal
    "kt": "watt/meter/kelvin", "hc": "watt/meter**2/kelvin", "dT": "kelvin",
    "Ts": "kelvin", "Tinf": "kelvin", "cp": "joule/kilogram/kelvin",
    "eps": "dimensionless", "sig_sb": "watt/meter**2/kelvin**4",
    "m": "1/meter", "UA": "watt/kelvin", "Cmin": "watt/kelvin", "NTU": "dimensionless",
    "mdot": "kilogram/second", "qdot": "watt", "q": "watt/meter**2",
    # fluids
    "mu": "pascal*second", "nu_k": "meter**2/second", "Vdot": "meter**3/second",
    "V": "meter/second", "v": "meter/second", "g": "meter/second**2",
    "Re": "dimensionless", "f": "dimensionless", "Kf": "dimensionless",
    "Cd": "dimensionless", "eta": "dimensionless", "Pr": "dimensionless",
    "Nu": "dimensionless", "Bi": "dimensionless", "Fo": "dimensionless",
    "hf": "meter", "H": "meter",
    # dynamics
    "mass": "kilogram", "kspr": "newton/meter", "cdamp": "newton*second/meter",
    "omega": "1/second", "N": "1/second", "n": "dimensionless",
    # thermodynamics
    "Rg": "joule/kilogram/kelvin", "gamma": "dimensionless",
    "Th": "kelvin", "Tc": "kelvin", "Pcomp": "watt",
}

# plausible magnitude in SI for a bare number, used only to warn
SANE = {
    "L": (1e-3, 1e2, "m"), "a": (1e-3, 1e2, "m"), "c": (1e-4, 1e0, "m"),
    "r": (1e-4, 1e1, "m"), "t": (1e-5, 1e0, "m"), "d": (1e-4, 1e1, "m"),
    "E": (1e6, 1e12, "Pa"), "G": (1e6, 1e12, "Pa"), "p": (1e0, 1e9, "Pa"),
    "I": (1e-12, 1e-2, "m^4"), "J": (1e-12, 1e-2, "m^4"), "A": (1e-8, 1e2, "m^2"),
    "P": (1e-3, 1e9, "N"), "rho": (1e0, 2e4, "kg/m3"),
}

def ureg():
    import pint
    return pint.UnitRegistry()

def dimension_of(expr, sym, u=None):
    """Evaluate the expression with unit-carrying quantities -> its dimension."""
    u = u or ureg()
    vals = {}
    for i, name in enumerate(sym.split()):
        if name not in DIMS: raise KeyError(f"no dimension declared for '{name}'")
        # distinct magnitudes: with every symbol at 1.0, Ro-Ri is zero and log(Ro/Ri)
        # divides by zero. Only the DIMENSION matters, so the values are free.
        vals[name] = (1.7 + 0.9*i) * u(DIMS[name])
    safe = dict(pi=math.pi, sqrt=lambda x: x**0.5,
                tanh=lambda x: math.tanh(x.magnitude if hasattr(x, "magnitude") else x),
                log=math.log, exp=math.exp)
    safe.update(vals)
    return eval(expr, {"__builtins__": {}}, safe)     # inputs come from our own table

def audit(references=None, verbose=True):
    """Check each formula produces the unit it claims. Returns (ok, rows)."""
    u = ureg()
    if references is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from engineai import REFERENCE as references
    rows, bad = [], 0
    for r in references:
        want = r["unit"]
        try:
            got = dimension_of(r["expr"], r["sym"], u)
            if want == "-":
                ok = got.dimensionless if hasattr(got, "dimensionless") else True
                gs = "dimensionless" if ok else str(got.units)
            else:
                target = u(want)
                ok = got.dimensionality == target.dimensionality
                gs = str(got.units)
            rows.append((r["key"], r["expr"], want, gs, ok))
            if not ok: bad += 1
        except Exception as e:
            rows.append((r["key"], r["expr"], want, f"{type(e).__name__}: {e}", False)); bad += 1
    if verbose:
        print(f"\n  {'formula':26s} {'claims':6s} {'dimensionally':22s} verdict")
        print("  " + "-"*74)
        for k, e, want, gs, ok in rows:
            print(f"  {k:26s} {want:6s} {gs[:22]:22s} {'ok' if ok else 'MISMATCH'}")
        print(f"\n  {len(rows)-bad}/{len(rows)} formulas dimensionally consistent")
        if bad: print("  A dimensional mismatch means the formula or its stated unit is WRONG.")
    return bad == 0, rows

_NUM = re.compile(r"^\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)\s*([A-Za-z°/^*\d]*)\s*$")

def parse_value(text, symbol=None, u=None):
    """'1000mm' -> (1.0, 'm', note). A bare number is taken as SI, with a warning
    when the magnitude looks like someone typed mm and meant m."""
    u = u or ureg()
    m = _NUM.match(str(text))
    if not m: raise ValueError(f"cannot read '{text}'")
    val, unit = float(m.group(1)), (m.group(2) or "").strip()
    if unit:
        q = (val * u(unit)).to_base_units()
        return float(q.magnitude), str(q.units), f"{val}{unit} -> {q.magnitude:.6g} {q.units}"
    note = ""
    if symbol in SANE:
        lo, hi, su = SANE[symbol]
        if not (lo <= abs(val) <= hi) and val != 0:
            guess = ""
            if symbol in ("L", "a", "c", "r", "t", "d") and lo <= abs(val)/1000 <= hi:
                guess = f"  Did you mean {val}mm = {val/1000:g} m?"
            note = (f"WARNING: {symbol}={val:g} is outside the usual range "
                    f"{lo:g}..{hi:g} {su}.{guess}")
    return val, "SI", note

def check_inputs(values, sym):
    """Return a list of warnings for suspicious bare numbers."""
    out = []
    for name in sym.split():
        if name in values:
            _v, _u, note = parse_value(values[name], name)
            if note: out.append(note)
    return out

def selftest():
    ok = True
    print("\nUNITS SELFTEST")
    v, un, n = parse_value("1000mm", "L");  print(f"  1000mm -> {v:g} {un}"); ok &= abs(v-1.0) < 1e-12
    v, un, n = parse_value("200GPa", "E");  print(f"  200GPa -> {v:g} {un}"); ok &= abs(v-2e11) < 1e3
    v, un, n = parse_value("2.5kN", "P");   print(f"  2.5kN  -> {v:g} {un}"); ok &= abs(v-2500) < 1e-6
    _v, _u, n = parse_value("1000", "L")
    print(f"  bare 1000 for L -> {'warned' if n else 'NO WARNING'}"); ok &= bool(n)
    print(f"     {n}")
    _v, _u, n2 = parse_value("1.0", "L")
    print(f"  bare 1.0 for L  -> {'no warning (correct)' if not n2 else 'spurious warning'}")
    ok &= not n2
    a, _rows = audit(verbose=False)
    print(f"  reference formulas dimensionally consistent: {'yes' if a else 'NO'}")
    ok &= a
    print("\nunits selftest:", "PASSED" if ok else "FAILED")
    return ok

if __name__ == "__main__":
    a = sys.argv[1:] or ["audit"]
    if a[0] == "audit": sys.exit(0 if audit()[0] else 1)
    elif a[0] == "selftest": sys.exit(0 if selftest() else 1)
    elif a[0] == "parse":
        v, un, n = parse_value(a[1], a[2] if len(a) > 2 else None)
        print(f"  {v:g} {un}"); print("  " + n if n else "")
