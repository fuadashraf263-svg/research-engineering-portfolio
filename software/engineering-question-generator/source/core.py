"""Core framework for the parametric engineering-question generator.
Every template computes its own numeric answer, so answers are correct by construction.
A verification harness (verify.py) independently re-checks the math."""
import math, random

REGISTRY = []

# ---------------- number formatting ----------------
def fmt(x, sig=4):
    """Human-friendly number: integers stay integers, floats rounded to `sig` sig-figs.
    Strings (e.g. binary/hex answers) are returned unchanged."""
    if isinstance(x, str):
        return x
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(xf) or math.isinf(xf):
        return str(xf)
    if abs(xf - round(xf)) < 1e-9 and abs(xf) < 1e15:
        return str(int(round(xf)))
    d = sig - int(math.floor(math.log10(abs(xf)))) - 1
    d = max(d, 0)
    r = round(xf, d)
    s = ("%.*f" % (d, r)).rstrip('0').rstrip('.')
    return s if s not in ('', '-0') else '0'

# ---------------- parameter sampling ----------------
def samp(spec, rng):
    kind = spec[0]
    if kind == 'int':
        lo, hi = spec[1], spec[2]
        step = spec[3] if len(spec) > 3 else 1
        return rng.randrange(lo, hi + 1, step)
    if kind == 'float':
        lo, hi = spec[1], spec[2]
        dec = spec[3] if len(spec) > 3 else 2
        return round(rng.uniform(lo, hi), dec)
    if kind == 'choice':
        return rng.choice(spec[1])
    raise ValueError('bad spec ' + repr(spec))

# ---------------- template registration ----------------
def T(branch, topic, diff, q, params, formula, solve, unit,
      subst=None, gunits=None, steps=None, valid=None, tags=None,
      ans_unit=None, check=None):
    REGISTRY.append(dict(
        branch=branch, topic=topic, difficulty=diff, q=q, params=params,
        formula=formula, solve=solve, unit=unit, subst=subst,
        gunits=gunits or {}, steps=steps, valid=valid, tags=tags or [],
        ans_unit=ans_unit, check=check,
        tid=f"{branch[:3].upper()}-{len(REGISTRY):04d}"))
    return REGISTRY[-1]

# ---------------- instance construction ----------------
def make_instance(t, rng, tries=60):
    for _ in range(tries):
        p = {k: samp(s, rng) for k, s in t['params'].items()}
        if t['valid'] and not t['valid'](p):
            continue
        try:
            v = t['solve'](p)
        except (ZeroDivisionError, ValueError, OverflowError):
            continue
        if v is None:
            continue
        try:
            vf = float(v)
            if math.isnan(vf) or math.isinf(vf):
                continue
        except (TypeError, ValueError):
            pass
        qt = t['q']
        if callable(qt):
            q = qt(p)
        else:
            q = qt.format(**{k: fmt(val) for k, val in p.items()})
        return p, v, q
    return None

def poly_str(coeffs, var='x'):
    """Pretty polynomial from highest degree first, e.g. [2,-3,0,5] -> '2x^3 - 3x^2 + 5'."""
    n = len(coeffs) - 1
    terms = []
    for i, c in enumerate(coeffs):
        power = n - i
        if abs(c) < 1e-12:
            continue
        mag = fmt(abs(c))
        if power == 0:
            term = mag
        elif power == 1:
            term = (mag if mag != '1' else '') + var
        else:
            term = (mag if mag != '1' else '') + f"{var}^{power}"
        sign = '-' if c < 0 else '+'
        terms.append((sign, term))
    if not terms:
        return '0'
    first_sign, first_term = terms[0]
    s = ('-' if first_sign == '-' else '') + first_term
    for sign, term in terms[1:]:
        s += f" {sign} {term}"
    return s

def build_steps(t, p, v):
    if t['steps']:
        return t['steps'](p, v)
    givens = []
    for k in t['params']:
        u = t['gunits'].get(k, '')
        givens.append(f"{k} = {fmt(p[k])}{u}")
    steps = ["Given: " + ", ".join(givens), "Formula: " + t['formula']]
    if t['subst']:
        steps.append("Substitute: " + t['subst'](p, v))
    au = t['ans_unit'] or t['unit']
    steps.append(("Answer: " + fmt(v) + " " + au).strip())
    return steps

def answer_str(t, v):
    au = t['ans_unit'] or t['unit']
    return (fmt(v) + " " + au).strip()
