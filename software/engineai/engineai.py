#!/usr/bin/env python3
"""
engineai.py - EngineAI end-to-end pipeline.

One command takes an engineering question and produces a cited, verified answer
plus a PDF report. Every stage degrades gracefully and says so.

  1 SOLVE    closed-form lookup from a cited reference library (never the LLM)
  2 COMPUTE  numeric evaluation, SI units
  3 CITE     BM25 retrieval from your textbooks (kb.py)
  4 GUARD    if a local LLM is present, its formula is checked and BLOCKED if wrong
  5 REPORT   PDF written to ~/engineai/out

Usage:
  python engineai.py run                       full demo, start to finish
  python engineai.py ask "cantilever deflection" --P 1000 --L 1.0 --E 200e9 --I 8.33e-6
  python engineai.py selftest                  prove the guard catches a wrong formula
  python engineai.py doctor                    what is wired up and what is missing
"""
import os, sys, re, json, random, argparse, subprocess, datetime

OUT = os.path.expanduser(os.environ.get("ENGINEAI_OUT", "~/engineai/out"))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:                                  # expression sandbox + owner identity
    from owner import safe_expr, Unsafe, OWNER, audit
except Exception:                     # never let a missing file stop the maths
    OWNER = {"name": "(owner.py not installed)", "email": "", "role": "", "product": "EngineAI"}
    class Unsafe(ValueError): pass
    def safe_expr(s, extra_names=(), maxlen=400): return s
    def audit(event, **k): return None

# ---------------------------------------------------------------- reference
# expr strings are plain python/sympy. Symbols are declared explicitly so that
# sympy never reads E as Euler's number or I as the imaginary unit.
REFERENCE = [
 dict(key="cantilever_point_tip", kw="cantilever tip deflection point load free end",
      expr="P*L**3/(3*E*I)", sym="P L E I", unit="m",
      src="Roark's Formulas for Stress and Strain, Table 8.1 case 1a"),
 dict(key="cantilever_udl_tip", kw="cantilever uniformly distributed load deflection",
      expr="w*L**4/(8*E*I)", sym="w L E I", unit="m",
      src="Roark's Table 8.1 case 2a"),
 dict(key="cantilever_point_at_a", kw="cantilever point load at distance a deflection",
      expr="P*a**2*(3*L-a)/(6*E*I)", sym="P a L E I", unit="m",
      src="Roark's Table 8.1 case 1b"),
 dict(key="simple_point_mid", kw="simply supported beam centre point load deflection",
      expr="P*L**3/(48*E*I)", sym="P L E I", unit="m",
      src="Roark's Table 8.1 case 1e"),
 dict(key="simple_udl_mid", kw="simply supported uniformly distributed load deflection",
      expr="5*w*L**4/(384*E*I)", sym="w L E I", unit="m",
      src="Roark's Table 8.1 case 2e"),
 dict(key="euler_pinned", kw="euler critical buckling load pinned column slender",
      expr="pi**2*E*I/L**2", sym="E I L", unit="N",
      src="Shigley's Mechanical Engineering Design, eq. 4-43"),
 dict(key="flexure", kw="bending stress flexure formula beam section modulus",
      expr="M*c/I", sym="M c I", unit="Pa", src="Hibbeler, Mechanics of Materials, flexure formula"),
 dict(key="axial", kw="axial extension bar elongation stiffness",
      expr="P*L/(A*E)", sym="P L A E", unit="m", src="Gere, Mechanics of Materials, ch.2"),
 dict(key="torsion_shear", kw="torsional shear stress shaft torque polar",
      expr="T*r/J", sym="T r J", unit="Pa", src="Shigley, eq. 3-37"),
 dict(key="torsion_angle", kw="angle of twist shaft torsion",
      expr="T*L/(G*J)", sym="T L G J", unit="rad", src="Gere, ch.3"),
 dict(key="hoop", kw="thin wall pressure vessel hoop circumferential stress",
      expr="p*r/t", sym="p r t", unit="Pa", src="Shigley, eq. 3-53"),
 dict(key="hagen_poiseuille", kw="laminar pipe flow pressure drop hagen poiseuille",
      expr="128*mu*Vdot*L/(pi*d**4)", sym="mu Vdot L d", unit="Pa", src="White, Fluid Mechanics, ch.6"),
 dict(key="laminar_friction", kw="laminar friction factor reynolds pipe",
      expr="64/Re", sym="Re", unit="-", src="White, Fluid Mechanics, ch.6"),
 dict(key="fin_efficiency", kw="fin efficiency straight adiabatic tip",
      expr="tanh(m*L)/(m*L)", sym="m L", unit="-", src="Incropera, Fundamentals of Heat and Mass Transfer, ch.3"),
 dict(key="conduction_wall", kw="steady conduction plane wall heat rate fourier",
      expr="kt*A*dT/L", sym="kt A dT L", unit="W", src="Sachdeva, Heat and Mass Transfer, ch.2"),
 dict(key="convection", kw="newton law cooling convection heat rate",
      expr="hc*A*dT", sym="hc A dT", unit="W", src="Sachdeva, Heat and Mass Transfer, ch.1"),
 dict(key="cantilever_freq", kw="cantilever first natural frequency vibration",
      expr="(1.875**2/(2*pi))*sqrt(E*I/(rho*A*L**4))", sym="E I rho A L", unit="Hz",
      src="Blevins, Formulas for Natural Frequency and Mode Shape"),
 # ---------------------------------------------------------------- beams
 dict(key="cantilever_udl_end_slope", kw="cantilever uniformly distributed load slope end",
      expr="w*L**3/(6*E*I)", sym="w L E I", unit="rad", src="Roark, cantilever UDL slope"),
 dict(key="cantilever_moment_tip", kw="cantilever end moment deflection tip",
      expr="M*L**2/(2*E*I)", sym="M L E I", unit="m", src="Gere, ch.9 cantilever end couple"),
 dict(key="simple_udl_slope_end", kw="simply supported uniformly distributed slope support end",
      expr="w*L**3/(24*E*I)", sym="w L E I", unit="rad", src="Gere, ch.9 table"),
 dict(key="fixed_fixed_udl_mid", kw="fixed both ends uniformly distributed deflection centre",
      expr="w*L**4/(384*E*I)", sym="w L E I", unit="m", src="Roark, fixed-fixed UDL"),
 dict(key="fixed_fixed_point_mid", kw="fixed both ends point load centre deflection",
      expr="P*L**3/(192*E*I)", sym="P L E I", unit="m", src="Roark, fixed-fixed centre load"),
 dict(key="propped_udl_max_moment", kw="propped cantilever uniformly distributed maximum moment",
      expr="w*L**2/8", sym="w L", unit="N*m", src="Hibbeler, Structural Analysis"),
 dict(key="simple_udl_max_moment", kw="simply supported uniformly distributed maximum bending moment",
      expr="w*L**2/8", sym="w L", unit="N*m", src="Hibbeler, Mechanics of Materials"),
 dict(key="cantilever_udl_max_moment", kw="cantilever uniformly distributed maximum moment root",
      expr="w*L**2/2", sym="w L", unit="N*m", src="Hibbeler, Mechanics of Materials"),
 dict(key="simple_point_max_moment", kw="simply supported centre point load maximum moment",
      expr="P*L/4", sym="P L", unit="N*m", src="Hibbeler, Mechanics of Materials"),
 dict(key="beam_shear_stress_rect", kw="transverse shear stress rectangular section maximum",
      expr="3*P/(2*A)", sym="P A", unit="Pa", src="Gere, ch.5 rectangular shear"),
 dict(key="beam_shear_stress_general", kw="transverse shear stress general section VQ It",
      expr="P*Q/(I*b)", sym="P Q I b", unit="Pa", src="Hibbeler, shear formula VQ/It"),
 # ------------------------------------------------------------- sections
 dict(key="I_rectangle", kw="second moment area rectangle section",
      expr="b*h**3/12", sym="b h", unit="m**4", src="standard section property"),
 dict(key="I_circle", kw="second moment area solid circle round section",
      expr="pi*d**4/64", sym="d", unit="m**4", src="standard section property"),
 dict(key="I_tube", kw="second moment area hollow tube annulus",
      expr="pi*(D**4-d**4)/64", sym="D d", unit="m**4", src="standard section property"),
 dict(key="J_solid_shaft", kw="polar second moment solid shaft",
      expr="pi*d**4/32", sym="d", unit="m**4", src="standard section property"),
 dict(key="J_hollow_shaft", kw="polar second moment hollow shaft tube",
      expr="pi*(D**4-d**4)/32", sym="D d", unit="m**4", src="standard section property"),
 dict(key="section_modulus", kw="section modulus bending elastic",
      expr="I/c", sym="I c", unit="m**3", src="standard section property"),
 dict(key="radius_gyration", kw="radius of gyration column section",
      expr="sqrt(I/A)", sym="I A", unit="m", src="Shigley, column analysis"),
 dict(key="parallel_axis", kw="parallel axis theorem transferred second moment",
      expr="I+A*d**2", sym="I A d", unit="m**4", src="parallel-axis theorem"),
 # -------------------------------------------------------------- columns
 dict(key="euler_fixed_free", kw="euler buckling fixed free cantilever column",
      expr="pi**2*E*I/(4*L**2)", sym="E I L", unit="N", src="Shigley, effective length 2L"),
 dict(key="euler_fixed_fixed", kw="euler buckling fixed both ends column",
      expr="4*pi**2*E*I/L**2", sym="E I L", unit="N", src="Shigley, effective length L/2"),
 dict(key="euler_fixed_pinned", kw="euler buckling fixed pinned column",
      expr="2.045*pi**2*E*I/L**2", sym="E I L", unit="N", src="Shigley, effective length 0.7L"),
 dict(key="slenderness_ratio", kw="slenderness ratio column effective length",
      expr="Le/k", sym="Le k", unit="-", src="Shigley, column analysis"),
 dict(key="euler_critical_stress", kw="euler critical buckling stress slenderness",
      expr="pi**2*E/(Le/k)**2", sym="E Le k", unit="Pa", src="Shigley, Euler stress"),
 # ------------------------------------------------------------- torsion
 dict(key="torsion_power", kw="shaft power torque rotational speed",
      expr="T*omega", sym="T omega", unit="W", src="power = torque x angular velocity"),
 dict(key="torsional_stiffness", kw="torsional stiffness shaft rate",
      expr="G*J/L", sym="G J L", unit="N*m", src="Gere, ch.3"),
 # ------------------------------------------------------- stress states
 dict(key="principal_stress_1", kw="principal stress maximum plane biaxial",
      expr="(sx+sy_)/2 + sqrt(((sx-sy_)/2)**2 + txy**2)", sym="sx sy_ txy", unit="Pa",
      src="Mohr's circle, Shigley ch.3"),
 dict(key="principal_stress_2", kw="principal stress minimum plane biaxial",
      expr="(sx+sy_)/2 - sqrt(((sx-sy_)/2)**2 + txy**2)", sym="sx sy_ txy", unit="Pa",
      src="Mohr's circle, Shigley ch.3"),
 dict(key="max_shear_stress", kw="maximum in plane shear stress mohr radius",
      expr="sqrt(((sx-sy_)/2)**2 + txy**2)", sym="sx sy_ txy", unit="Pa",
      src="Mohr's circle radius"),
 dict(key="von_mises_2d", kw="von mises equivalent stress plane biaxial",
      expr="sqrt(s1**2 - s1*s2 + s2**2)", sym="s1 s2", unit="Pa",
      src="Shigley ch.5, distortion energy"),
 dict(key="safety_factor", kw="factor of safety yield equivalent stress",
      expr="Sy/s1", sym="Sy s1", unit="-", src="Shigley ch.5"),
 # -------------------------------------------------- pressure vessels
 dict(key="thin_sphere", kw="thin wall sphere pressure stress",
      expr="p*r/(2*t)", sym="p r t", unit="Pa", src="Shigley, thin-wall sphere"),
 dict(key="lame_hoop_inner", kw="thick wall cylinder lame hoop stress inner surface",
      expr="p*(Ro**2+Ri**2)/(Ro**2-Ri**2)", sym="p Ro Ri", unit="Pa",
      src="Lame equations, Roark ch.13"),
 dict(key="thermal_stress_restrained", kw="thermal stress fully restrained bar temperature",
      expr="E*alpha*dT", sym="E alpha dT", unit="Pa", src="Roark ch.16"),
 dict(key="thermal_expansion", kw="thermal expansion length change temperature",
      expr="alpha*L*dT", sym="alpha L dT", unit="m", src="linear thermal expansion"),
 # ------------------------------------------------------------ springs
 dict(key="spring_rate_helical", kw="helical compression spring rate stiffness",
      expr="G*d**4/(8*D**3*n)", sym="G d D n", unit="N/m", src="Shigley eq. 10-9"),
 dict(key="spring_shear_stress", kw="helical spring shear stress wahl",
      expr="8*F*D/(pi*d**3)", sym="F D d", unit="Pa", src="Shigley eq. 10-3, uncorrected"),
 dict(key="spring_energy", kw="spring stored strain energy elastic",
      expr="kspr*x**2/2", sym="kspr x", unit="J", src="elastic strain energy"),
 # ------------------------------------------------------- machine design
 dict(key="bearing_life_L10", kw="rolling bearing life L10 dynamic load rating",
      expr="(F/P)**3", sym="F P", unit="-", src="Shigley ch.11, ball bearing a=3"),
 dict(key="goodman", kw="modified goodman fatigue mean alternating stress",
      expr="1/(sa/Se + sm/Su)", sym="sa Se sm Su", unit="-", src="Shigley eq. 6-46"),
 dict(key="soderberg", kw="soderberg fatigue criterion yield",
      expr="1/(sa/Se + sm/Sy)", sym="sa Se sm Sy", unit="-", src="Shigley ch.6"),
 dict(key="bolt_stiffness", kw="bolt member stiffness axial",
      expr="A*E/L", sym="A E L", unit="N/m", src="Shigley ch.8"),
 # ---------------------------------------------------------- vibration
 dict(key="natural_freq_spring_mass", kw="natural frequency spring mass undamped",
      expr="sqrt(kspr/mass)/(2*pi)", sym="kspr mass", unit="Hz", src="Rao, Mechanical Vibrations"),
 dict(key="damping_ratio", kw="damping ratio critical viscous",
      expr="cdamp/(2*sqrt(kspr*mass))", sym="cdamp kspr mass", unit="-", src="Rao ch.2"),
 dict(key="critical_damping", kw="critical damping coefficient",
      expr="2*sqrt(kspr*mass)", sym="kspr mass", unit="N*s/m", src="Rao ch.2"),
 # ------------------------------------------------------------- fluids
 dict(key="reynolds_pipe", kw="reynolds number pipe flow velocity diameter",
      expr="rho*V*d/mu", sym="rho V d mu", unit="-", src="White, Fluid Mechanics ch.6"),
 dict(key="darcy_weisbach", kw="darcy weisbach pressure drop pipe friction",
      expr="f*(L/d)*rho*V**2/2", sym="f L d rho V", unit="Pa", src="White ch.6"),
 dict(key="head_loss_darcy", kw="head loss friction pipe darcy",
      expr="f*(L/d)*V**2/(2*g)", sym="f L d V g", unit="m", src="White ch.6"),
 dict(key="minor_loss", kw="minor loss fitting valve elbow K factor",
      expr="Kf*rho*V**2/2", sym="Kf rho V", unit="Pa", src="White ch.6"),
 dict(key="continuity", kw="continuity volumetric flow rate area velocity",
      expr="A*V", sym="A V", unit="m**3/s", src="conservation of mass"),
 dict(key="dynamic_pressure", kw="dynamic pressure stagnation velocity head",
      expr="rho*V**2/2", sym="rho V", unit="Pa", src="Bernoulli"),
 dict(key="orifice_flow", kw="orifice discharge flow coefficient pressure drop",
      expr="Cd*A*sqrt(2*p/rho)", sym="Cd A p rho", unit="m**3/s", src="White ch.6 orifice"),
 dict(key="pump_power", kw="pump hydraulic power head flow efficiency",
      expr="rho*g*H*Vdot/eta", sym="rho g H Vdot eta", unit="W", src="pump shaft power"),
 dict(key="drag_force", kw="drag force coefficient frontal area",
      expr="Cd*A*rho*V**2/2", sym="Cd A rho V", unit="N", src="White ch.7"),
 # ------------------------------------------------------ heat transfer
 dict(key="conduction_cylinder", kw="radial conduction cylinder pipe wall heat rate",
      expr="2*pi*kt*L*dT/log(Ro/Ri)", sym="kt L dT Ro Ri", unit="W", src="Incropera ch.3"),
 dict(key="conduction_sphere", kw="radial conduction sphere shell heat rate",
      expr="4*pi*kt*dT/(1/Ri - 1/Ro)", sym="kt dT Ri Ro", unit="W", src="Incropera ch.3"),
 dict(key="thermal_resistance_wall", kw="thermal resistance plane wall conduction",
      expr="L/(kt*A)", sym="L kt A", unit="K/W", src="Incropera ch.3"),
 dict(key="thermal_resistance_conv", kw="thermal resistance convection film",
      expr="1/(hc*A)", sym="hc A", unit="K/W", src="Incropera ch.3"),
 dict(key="biot_number", kw="biot number lumped capacitance",
      expr="hc*L/kt", sym="hc L kt", unit="-", src="Incropera ch.5"),
 dict(key="nusselt_from_h", kw="nusselt number convection coefficient",
      expr="hc*L/kt", sym="hc L kt", unit="-", src="Incropera ch.6"),
 dict(key="radiation_exchange", kw="radiation heat transfer stefan boltzmann emissivity",
      expr="eps*sig_sb*A*(Ts**4 - Tinf**4)", sym="eps sig_sb A Ts Tinf", unit="W",
      src="Stefan-Boltzmann, Incropera ch.1"),
 dict(key="ntu_definition", kw="number of transfer units heat exchanger UA",
      expr="UA/Cmin", sym="UA Cmin", unit="-", src="Incropera ch.11"),
 dict(key="heat_capacity_rate", kw="heat capacity rate mass flow specific heat",
      expr="mdot*cp", sym="mdot cp", unit="W/K", src="Incropera ch.11"),
 dict(key="sensible_heat", kw="sensible heat rate mass flow temperature rise",
      expr="mdot*cp*dT", sym="mdot cp dT", unit="W", src="first law, steady flow"),
 # ----------------------------------------------------- thermodynamics
 dict(key="ideal_gas_density", kw="ideal gas density pressure temperature",
      expr="p/(Rg*Ts)", sym="p Rg Ts", unit="kg/m**3", src="ideal gas law"),
 dict(key="speed_of_sound", kw="speed of sound ideal gas",
      expr="sqrt(gamma*Rg*Ts)", sym="gamma Rg Ts", unit="m/s", src="Cengel, compressible flow"),
 dict(key="carnot_efficiency", kw="carnot efficiency thermal reservoir",
      expr="1 - Tc/Th", sym="Tc Th", unit="-", src="Cengel ch.6"),
 dict(key="carnot_cop_cooling", kw="carnot coefficient of performance refrigeration",
      expr="Tc/(Th-Tc)", sym="Tc Th", unit="-", src="Cengel ch.6"),
 dict(key="otto_efficiency", kw="otto cycle efficiency compression ratio",
      expr="1 - 1/n**(gamma-1)", sym="n gamma", unit="-", src="Cengel ch.9"),
 dict(key="isentropic_temperature", kw="isentropic temperature ratio pressure ratio",
      expr="Ts*n**((gamma-1)/gamma)", sym="Ts n gamma", unit="K", src="Cengel ch.7")]

def _sym(names):
    import sympy as sp
    return {n: sp.Symbol(n, positive=True) for n in names.split()}

def parse(expr, names):
    """sympify without letting E and I become Euler / imaginary unit.
    sympify() runs eval(), so the string is whitelist-checked first."""
    import sympy as sp
    safe_expr(expr, extra_names=names.split())      # raises Unsafe on anything odd
    loc = _sym(names)
    loc.update(pi=sp.pi, sqrt=sp.sqrt, tanh=sp.tanh, log=sp.log, exp=sp.exp)
    return sp.sympify(expr, locals=loc), loc

def lookup(question, n=3):
    STOP = {"a","an","the","of","for","in","on","at","to","and","is","what","with","under","its"}
    q = set(re.findall(r"[a-z]+", question.lower())) - STOP
    scored = []
    for r in REFERENCE:
        k = set(r["kw"].split())
        s = len(q & k)
        if s: scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:n]]

# ------------------------------------------------------------------- guard
def equivalent(a, b, names, trials=40):
    """True if two expressions agree numerically at random positive points.
    Rearrangements pass; different physics fails."""
    import sympy as sp
    ea, loc = parse(a, names)
    eb, _ = parse(b, names)
    syms = sorted(set(ea.free_symbols) | set(eb.free_symbols), key=str)
    rnd = random.Random(7)
    for _ in range(trials):
        sub = {s: rnd.uniform(0.4, 3.0) for s in syms}
        try:
            va = complex(ea.subs(sub)); vb = complex(eb.subs(sub))
        except Exception:
            return False
        if abs(va.imag) > 1e-9 or abs(vb.imag) > 1e-9: return False
        if abs(va.real - vb.real) > 1e-7 * max(1.0, abs(va.real)): return False
    return True

LATEX = [(r"\^\{([^{}]+)\}", r"^\1"), (r"_\{([^{}]+)\}", r"_\1"),
         (r"\\(delta|sigma|tau|theta|omega|rho|mu|lambda|eta|Delta)\b", ""),
         (r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)"), (r"\\cdot|\\,|\\!|\$", ""),
         (r"\\pi", "pi"), (r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)"), (r"\^", "**"), (r"\\", "")]

# Models write maths for humans: unicode, superscripts, greek. Normalise before parsing.
UNI = {"\u00b2": "**2", "\u00b3": "**3", "\u2074": "**4", "\u2070": "**0", "\u00b9": "**1",
       "\u2075": "**5", "\u2076": "**6", "\u00d7": "*", "\u00b7": "*", "\u2212": "-",
       "\u2044": "/", "\u03c0": "pi", "\u2261": "=", "\u00a0": " "}
# alternative symbol names for the same physical quantity
ALIAS = {"l_e": "L", "le": "L", "l": "L", "leff": "L", "l_eff": "L", "length": "L",
         "e_mod": "E", "young": "E", "i_z": "I", "i_x": "I", "second_moment": "I",
         "p_cr": "", "f_cr": "", "delta": "", "sigma": "", "tau": "", "q": "", "w_max": ""}
GREEK_LHS = "\u03b4\u03c3\u03c4\u0394\u03b8\u03c9\u03bb\u03bc\u03c1\u03b7"

def normalise(s):
    for k, v in UNI.items(): s = s.replace(k, v)
    s = "".join(ch for ch in s if ch not in GREEK_LHS or ch == " ")
    return s
FUNCS = ("sqrt", "tanh", "log", "exp", "sin", "cos", "tan")
def implicit_mult(s):
    """'3 E I' -> '3*E*I'.  Models write maths, not python."""
    s = re.sub(r"(?<=[\w\)])\s+(?=[\w\(])", "*", s)
    for f in FUNCS: s = s.replace(f + "*(", f + "(")
    return s

def delatex(s):
    for pat, rep in LATEX: s = re.sub(pat, rep, s)
    s = s.replace("{", "(").replace("}", ")")     # leftover braces, after \frac is gone
    return implicit_mult(s.strip())

DERIV = re.compile(r"\bd[A-Za-z_]\w*\s*/\s*d[A-Za-z_]\w*")

def expand_juxtaposed(expr, ref_syms):
    """Models write PL**3/(3EI). Turn that into P*L**3/(3*E*I)."""
    expr = re.sub(r"(\d)\s*([A-Za-z_])", r"\1*\2", expr)          # 3EI -> 3*EI
    def seg(m):
        w = m.group(0)
        if w in ref_syms or w in ("pi", "sqrt", "tanh", "log", "exp"): return w
        if len(w) > 1 and all(ch in ref_syms for ch in w):            # EI -> E*I
            return "*".join(w)
        return w
    return re.sub(r"[A-Za-z_]\w*", seg, expr)

def apply_alias(expr, ref_syms):
    """Rename l_e -> L etc, so notation differences are not treated as physics errors."""
    def sub(m):
        w = m.group(0)
        if w in ref_syms or w in ("pi", "sqrt", "tanh", "log", "exp"): return w
        a = ALIAS.get(w.lower())
        return a if a in ref_syms else w
    return re.sub(r"[A-Za-z_]\w*", sub, expr)

def check_claim(claim, ref):
    """Compare a claimed formula against the reference. -> (verdict, detail)"""
    c = normalise(claim)
    c = c.split("=")[-1].strip().rstrip(".,;")
    ref_syms = set(ref["sym"].split())
    # a derivative form (Fourier dT/dx) is a different but valid statement of the same law
    if DERIV.search(c):
        return "EQUIV-FORM", f"{c}  (differential form of {ref['expr']} - not directly comparable)"
    c = delatex(c)
    c = expand_juxtaposed(c, ref_syms)
    c = apply_alias(c, ref_syms)
    names = ref["sym"] + " " + " ".join(
        w for w in set(re.findall(r"[A-Za-z_]\w*", c))
        if w not in ref_syms and w not in ("pi", "sqrt", "tanh", "log", "exp"))
    try:
        safe_expr(c, extra_names=names.split())
    except Unsafe as u:
        audit("unsafe_expression", source="model", detail=str(u))
        return "BLOCK", f"refused to evaluate - {u}"
    try:
        if equivalent(c, ref["expr"], names):
            return "PASS", c
        if equivalent("-(" + c + ")", ref["expr"], names):
            return "PASS", c + "   (sign convention differs)"
    except Exception as e:
        return "UNVERIFIED", f"could not parse ({type(e).__name__})"
    return "BLOCK", f"{c}   should be   {ref['expr']}"

# --------------------------------------------------------------------- kb
def kb_search(q, k=3):
    sys.path.insert(0, HERE)
    try:
        import kb
    except Exception:
        return []
    try:
        return [(t, p, s) for t, p, s, _sc, _b in kb.search(q, k=k, quiet=True)]
    except Exception:
        return []

# -------------------------------------------------------------------- llm
def ollama(prompt, model=None, timeout=180):
    model = model or os.environ.get("ENGINEAI_MODEL")
    exe = None
    for cand in ("ollama", "/usr/local/bin/ollama", "/usr/bin/ollama"):
        try:
            subprocess.run([cand, "--version"], capture_output=True, timeout=10); exe = cand; break
        except Exception: continue
    if not exe: return None, "ollama not installed"
    if not model:                       # use whatever is actually installed
        try:
            ls = subprocess.run([exe, "list"], capture_output=True, text=True, timeout=20).stdout
            rows = [l.split()[0] for l in ls.splitlines()[1:] if l.strip()]
            model = rows[0] if rows else None
        except Exception: model = None
        if not model: return None, "no ollama model pulled"
    try:
        r = subprocess.run([exe, "run", model, prompt], capture_output=True,
                           text=True, timeout=timeout)
        return (r.stdout.strip() or None), (None if r.stdout.strip() else r.stderr[:120])
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

# ----------------------------------------------------------------- compute
def compute(ref, values):
    import sympy as sp
    e, loc = parse(ref["expr"], ref["sym"])
    need = [str(s) for s in e.free_symbols]
    miss = [n for n in need if n not in values]
    if miss: return None, miss
    val = float(e.subs({loc[n]: values[n] for n in need}))
    return val, []

# --------------------------------------------------------------- visualise
BEAM_CASES = {"cantilever_point_tip": "cantilever", "cantilever_udl_tip": "cantilever",
              "cantilever_point_at_a": "cantilever", "simple_point_mid": "simple",
              "simple_udl_mid": "simple"}

def visualise(ref, values):
    """2D figures + a 3D sandbox for the problem just solved. Never fatal."""
    figs, sandbox = [], None
    sys.path.insert(0, HERE)
    try:
        import generators as G
    except Exception:
        return figs, sandbox
    def go(name, **kw):
        """Generate, then stamp the filename with the case so a second
        question cannot silently overwrite the first one's figures."""
        try:
            if name not in G.REGISTRY or not G.available(name): return None
            f = G.REGISTRY[name](**kw)
            if not f or not os.path.exists(f): return f
            d, b = os.path.split(f)
            if b.startswith(ref["key"]): return f
            tagged = os.path.join(d, f'{ref["key"]}_{b}')
            os.replace(f, tagged)
            return tagged
        except Exception:
            return None
    if values:
        f = go("sensitivity", expr=ref["expr"], sym=ref["sym"], values=values,
               unit=ref["unit"], title=ref["key"])
        if f: figs.append(f)
    case = BEAM_CASES.get(ref["key"])
    if case and {"P", "L", "E", "I"} <= set(values):
        for n in ("beam_diagram", "shear_moment"):
            f = go(n, case=case, **{k: values[k] for k in ("P", "L", "E", "I") if k in values})
            if f: figs.append(f)
        stl = go("stl_deflected_beam", case=case, **{k: values[k] for k in ("P","L","E","I")})
        if stl: sandbox = go("viewer_3d", stl=stl, title=f"EngineAI - {ref['key']}")
    if ref["key"] == "flexure" and {"M"} <= set(values):
        f = go("stress_field", M=values["M"]); figs and None
        if f: figs.append(f)
    return figs, sandbox

# ------------------------------------------------------------------ report
def report(path, question, ref, value, values, cites, llm_block, figs=()):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except ImportError:
        with open(path.replace(".pdf", ".md"), "w") as f:
            f.write(f"# {question}\n\n{ref['expr']} = {value}\n\nSource: {ref['src']}\n")
        return path.replace(".pdf", ".md")
    ss = getSampleStyleSheet()
    mono = ParagraphStyle("m", parent=ss["Code"], fontSize=10, leading=13)
    doc = SimpleDocTemplate(path, pagesize=A4, title="EngineAI Report",
                            leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm)
    st = [Paragraph("EngineAI — Verified Engineering Report", ss["Title"]),
          Paragraph(datetime.datetime.now().strftime("%d %B %Y, %H:%M"), ss["Normal"]),
          Spacer(1, 8*mm), Paragraph("Question", ss["Heading2"]),
          Paragraph(question, ss["BodyText"]), Spacer(1, 4*mm),
          Paragraph("Closed-form solution", ss["Heading2"]),
          Paragraph(f"<b>{ref['expr']}</b>&nbsp;&nbsp;[{ref['unit']}]", mono),
          Paragraph(f"Source: {ref['src']}", ss["Italic"]), Spacer(1, 4*mm)]
    if values:
        rows = [["symbol", "value"]] + [[k, f"{v:g}"] for k, v in sorted(values.items())]
        if value is not None: rows.append(["RESULT", f"{value:.6g} {ref['unit']}"])
        t = Table(rows, colWidths=[40*mm, 60*mm])
        t.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .4, colors.grey),
                               ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
                               ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
                               ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
                               ("FONTSIZE", (0,0), (-1,-1), 9)]))
        st += [Paragraph("Computation", ss["Heading2"]), t, Spacer(1, 4*mm)]
    if cites:
        st.append(Paragraph("Textbook corroboration", ss["Heading2"]))
        for ti, pg, sn in cites:
            st.append(Paragraph(f"<b>{ti[:70]}</b>, p.{pg}", ss["BodyText"]))
            st.append(Paragraph(re.sub(r"[<>]", "", sn)[:300], ss["Italic"]))
            st.append(Spacer(1, 2*mm))
    for f in figs:
        try:
            from reportlab.platypus import Image as RLImage
            from PIL import Image as PILImage
            iw, ih = PILImage.open(f).size
            w = 165*mm; st += [Paragraph(os.path.basename(f), ss["Heading3"]),
                               RLImage(f, width=w, height=w*ih/iw), Spacer(1, 3*mm)]
        except Exception:
            pass
    if llm_block:
        st += [Spacer(1, 3*mm), Paragraph("Local model audit", ss["Heading2"]),
               Paragraph(llm_block, mono)]
    st += [Spacer(1, 6*mm),
           Paragraph("Generated by EngineAI. The formula above comes from a cited reference, "
                     "not from a language model. Any model output was checked against it.",
                     ss["Italic"])]
    doc.build(st)
    return path

# ------------------------------------------------------------------ stages
def ask(question, values, use_llm=True, quiet=False):
    os.makedirs(OUT, exist_ok=True)
    say = (lambda *a: None) if quiet else print
    say("\n" + "=" * 66)
    say("QUESTION  " + question)
    say("=" * 66)

    hits = lookup(question)
    if not hits:
        say("\n[1 SOLVE  ] no closed form in the reference library for this question.")
        return None
    ref = hits[0]
    say(f"\n[1 SOLVE  ] {ref['expr']}   [{ref['unit']}]")
    say(f"            source: {ref['src']}")
    if len(hits) > 1:
        say("            also considered: " + ", ".join(h["key"] for h in hits[1:]))

    for _n in globals().get("_UNIT_NOTES", []):
        say(f"[!  UNITS ] {_n}")
    try:
        from units import dimension_of
        import pint as _p
        _u = _p.UnitRegistry()
        _got = dimension_of(ref["expr"], ref["sym"], _u)
        if ref["unit"] != "-":
            _okd = _got.dimensionality == _u(ref["unit"]).dimensionality
            say(f"[1b DIMS   ] {'consistent' if _okd else 'MISMATCH'} - formula yields "
                f"{_got.units}, claims {ref['unit']}")
    except Exception:
        pass

    value, miss = compute(ref, values)
    if value is None:
        say(f"[2 COMPUTE] need values for: {', '.join(miss)}  (pass e.g. --{miss[0]} 1000)")
    else:
        say(f"[2 COMPUTE] = {value:.6g} {ref['unit']}   from " +
            ", ".join(f"{k}={v:g}" for k, v in sorted(values.items())))

    cites = kb_search(question, 2)
    if cites:
        for ti, pg, sn in cites:
            say(f"[3 CITE   ] {ti[:52]}  p.{pg}")
    else:
        say("[3 CITE   ] library empty or kb.py not found - run: python kb.py add ~/books")

    llm_block = None
    if use_llm:
        out, err = ollama(f"In one line, give only the formula for: {question}. No explanation.")
        if out is None:
            say(f"[4 GUARD  ] local model skipped ({err})")
        else:
            first = next((l for l in out.splitlines() if l.strip()), "")
            verdict, detail = check_claim(first, ref)
            mark = {"PASS": "PASS ", "BLOCK": "BLOCK", "UNVERIFIED": "?    ",
                    "EQUIV-FORM": "FORM "}[verdict]
            say(f"[4 GUARD  ] {mark} model said: {first[:60]}")
            if verdict == "BLOCK":
                say(f"            REJECTED - {detail}")
            llm_block = f"model: {first[:80]}\nverdict: {verdict}\n{detail}"

    figs, sandbox = visualise(ref, values)
    for f in figs: say(f"[5 VISUAL ] {f}")
    if sandbox: say(f"[5 VISUAL ] {sandbox}   <- open this in a browser: rotate/zoom the solved part")
    if not figs: say("[5 VISUAL ] no figure for this case (generators.py missing?)")

    stamp = re.sub(r"\W+", "_", question.lower())[:40]
    path = os.path.join(OUT, f"report_{stamp}.pdf")
    try:
        path = report(path, question, ref, value, values, cites, llm_block, figs)
        say(f"[6 REPORT ] {path}")
    except Exception as e:
        say(f"[6 REPORT ] failed ({type(e).__name__}: {e})")
        path = None
    return dict(ref=ref, value=value, cites=cites, report=path, figs=figs, sandbox=sandbox)

def selftest():
    """Prove the guard catches the exact error qwen2.5 made."""
    ref = next(r for r in REFERENCE if r["key"] == "cantilever_point_tip")
    cases = [("P*L**2/(E*I)", "BLOCK"),            # what the model actually said
             ("P*L**3/(3*E*I)", "PASS"),           # correct
             ("(P/(3*E*I))*L**3", "PASS"),         # rearranged, still correct
             (r"\frac{P L^3}{3 E I}", "PASS"),     # latex form
             (r"\delta = \frac{PL^{3}}{3EI}", "PASS"),   # latex, no spaces
             ("P*L*L*L/(E*I*3)", "PASS"),          # written out
             ("P*a**2*(3*L-a)/(6*E*I)", "BLOCK")]  # different case, correctly rejected here
    ok = True
    print("\nGUARD SELFTEST  reference:", ref["expr"])
    for claim, want in cases:
        got, detail = check_claim(claim, ref)
        flag = "ok " if got == want else "FAIL"
        if got != want: ok = False
        print(f"  {flag} expected {want:5s} got {got:11s} {claim}")
    print("\nguard selftest:", "PASSED" if ok else "FAILED")
    return ok

def doctor():
    print("\nENGINEAI DOCTOR")
    print(f"  python        {sys.version.split()[0]}  ({sys.executable})")
    for m in ("sympy", "fitz", "reportlab", "numpy", "scipy", "cadquery", "trimesh", "pint"):
        try:
            __import__(m); print(f"  {m:12s}  ok")
        except Exception: print(f"  {m:12s}  MISSING")
    for b in ("ccx", "ollama", "dot", "prusa-slicer", "FreeCADCmd"):
        from shutil import which
        print(f"  {b:12s}  {'ok  ' + (which(b) or '') if which(b) else 'MISSING'}")
    db = os.environ.get("ENGINEAI_KB", os.path.expanduser("~/engineai/library/kb.db"))
    print(f"  kb.db         {'ok  ' + db if os.path.exists(db) else 'not built - python kb.py add ~/books'}")
    print(f"  out dir       {OUT} {'ok' if os.path.isdir(OUT) else '(will be created)'}")
    try:
        from owner import posture
        print("  --- security ---")
        for n, ok, d in posture(): print(f"  {'ok  ' if ok else 'NO  '}{n:26s} {d}")
    except Exception:
        print("  security      owner.py not installed - no auth, no audit log")
    o, e = ollama("say ok", timeout=60)
    print(f"  local model   {'responds' if o else 'no (' + str(e) + ')'}")

def main():
    ap = argparse.ArgumentParser(allow_abbrev=False, add_help=True)
    # accept --selftest as well as the positional form, so every module in
    # the project responds to one uniform flag
    if "--selftest" in sys.argv:
        sys.argv = [sys.argv[0], "selftest"]
    ap.add_argument("cmd", choices=["run", "ask", "selftest", "doctor", "whoami"])
    ap.add_argument("question", nargs="*")
    ap.add_argument("--no-llm", action="store_true")
    a, extra = ap.parse_known_args()
    try:
        from units import parse_value
    except Exception:
        parse_value = None
    vals, unit_notes = {}, []
    i = 0
    while i < len(extra):
        if extra[i].startswith("--") and i + 1 < len(extra):
            name, raw = extra[i][2:], extra[i + 1]
            try:
                if parse_value:
                    v, _u, note = parse_value(raw, name)
                    if note: unit_notes.append(note)
                else:
                    v = float(raw)
                vals[name] = v; i += 2; continue
            except (ValueError, TypeError): pass
        i += 1
    globals()["_UNIT_NOTES"] = unit_notes
    if a.cmd == "whoami":
        print(f"\n  {OWNER.get('product','EngineAI')} belongs to {OWNER['name']} <{OWNER.get('email','')}>")
        print(f"  {OWNER.get('role','')}\n  {OWNER.get('note','')}\n")
        return
    if a.cmd == "selftest": sys.exit(0 if selftest() else 1)
    if a.cmd == "doctor": return doctor()
    if a.cmd == "run":
        selftest()
        ask("cantilever tip deflection under a point load at the free end",
            dict(P=1000.0, L=1.0, E=200e9, I=8.333e-6), use_llm=not a.no_llm)
        ask("euler critical buckling load of a slender pinned column",
            dict(E=200e9, I=8.333e-6, L=1.0), use_llm=not a.no_llm)
        ask("steady conduction heat rate through a plane wall",
            dict(k=45.0, A=0.5, dT=60.0, L=0.02), use_llm=not a.no_llm)
        print("\nDone. Reports in", OUT)
        return
    ask(" ".join(a.question), vals, use_llm=not a.no_llm)

if __name__ == "__main__":
    main()
