#!/usr/bin/env python3
"""
agent_loop.py - the piece that turns EngineAI from a calculator into an agent.

Manus's advantage is not the browser. It is the loop: plan, call a tool, read the
result, decide the next call. You already own better tools than Manus for
engineering - validated CalculiX, validated OpenFOAM, a cited formula table, a
guard that catches wrong physics. What was missing is the loop over them.

Design decisions that matter:
  * BACKEND-AGNOSTIC. Local ollama today; any frontier API the day you go
    online. Same loop, same tools, one config line.
  * EVERY NUMBER IS VERIFIED. A tool result is data, not a claim. Anything the
    model asserts about a formula goes through guard checking before it is shown.
  * STRICT JSON PROTOCOL. Small local models cannot be trusted with native
    function calling, so the loop parses, validates, and re-prompts on malformed
    output instead of crashing.
  * FULL TRANSCRIPT. Every step is logged and replayable - which is what lets you
    show a customer why an answer is right.

  python agent_loop.py "deflection of a 1.2 m steel cantilever under 2.5 kN"
  python agent_loop.py --list-tools
  python agent_loop.py --selftest
"""
import os, re, sys, json, time, argparse, traceback, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
OUT  = os.path.expanduser(os.environ.get("ENGINEAI_OUT", "~/engineai/out"))

# ============================================================ tool registry
TOOLS = {}

def tool(name, desc, params):
    def deco(fn):
        fn.tool_name, fn.desc, fn.params = name, desc, params
        TOOLS[name] = fn
        return fn
    return deco

@tool("lookup_formula", "Find the cited closed-form formula for an engineering quantity. "
      "Returns found=false when the question is not a case in the reference table.",
      {"question": "plain-language description, e.g. 'cantilever tip deflection'"})
def t_lookup(question):
    from engineai import lookup, REFERENCE
    STOP = {"a","an","the","of","for","in","on","at","to","and","is","are","what","how",
            "find","solution","formula","equation","calculate","compute","value","me"}
    q = set(re.findall(r"[a-z]+", question.lower())) - STOP
    scored = []
    for r in REFERENCE:
        overlap = len(q & set(r["kw"].split()))
        if overlap >= 2: scored.append((overlap, r))
    scored.sort(key=lambda x: -x[0])
    hits = [r for _s, r in scored[:3]]
    if not hits:
        return {"found": False,
                "note": ("Not a case in the reference table. Do not guess - tell the user "
                         "this is outside the verified set, or use search_library.")}
    return {"found": True, "candidates": [
        {"key": h["key"], "formula": h["expr"], "symbols": h["sym"],
         "unit": h["unit"], "source": h["src"]} for h in hits]}

USER_GIVEN = {}          # set by the loop from the actual question, per run
CONTEXT = {}             # what the previous question established, for follow-ups

@tool("compute", "Evaluate a reference formula with numeric values. Returns the verified answer. "
      "Any value the user did not state is reported as an ASSUMPTION, not a fact.",
      {"key": "the formula key from lookup_formula", "values": "object of symbol->number in SI"})
def t_compute(key, values):
    from engineai import REFERENCE, compute
    ref = next((r for r in REFERENCE if r["key"] == key), None)
    if not ref: return {"error": f"unknown formula key '{key}'"}
    vals = {k: float(v) for k, v in values.items()}
    val, miss = compute(ref, vals)
    if val is None: return {"error": "missing values", "needed": miss}
    # A model will happily invent E and I. It cannot be stopped from inventing them,
    # but it must not be allowed to present them as given.
    assumed = {}
    for k, v in vals.items():
        g = USER_GIVEN.get(k)
        if g is None or abs(v - g) > max(abs(g)*1e-3, 1e-12):   # 0.1% = rounding, not invention
            assumed[k] = v
    out = {"value": val, "unit": ref["unit"], "formula": ref["expr"], "source": ref["src"],
           "from_question": {k: USER_GIVEN[k] for k in vals if k in USER_GIVEN}}
    if assumed:
        out["ASSUMED"] = assumed
        out["warning"] = ("These were NOT in the question and were assumed: "
                          + ", ".join(f"{k}={v:g}" for k, v in sorted(assumed.items()))
                          + ". State them to get a defensible answer.")
    return out

@tool("check_units", "Check inputs for unit mistakes and convert strings like '1200mm' to SI.",
      {"values": "object of symbol->value, values may carry units"})
def t_units(values):
    try: from units import parse_value
    except Exception: return {"note": "units.py not installed"}
    out, warn = {}, []
    for k, v in values.items():
        val, _u, note = parse_value(v, k)
        out[k] = val
        if note: warn.append(note)
    return {"si_values": out, "warnings": warn}

@tool("search_library", "Search the owner's engineering textbooks. Returns book, page and passage.",
      {"query": "engineering search terms"})
def t_search(query):
    try: import kb
    except Exception: return {"error": "kb.py not installed"}
    rows = kb.search(query, k=3, quiet=True, field="engineering")
    if not rows: return {"hits": [], "note": "nothing above the relevance floor - say you do not know"}
    return {"hits": [{"book": t, "page": p, "passage": " ".join(b.split())[:280]}
                     for t, p, _s, _sc, b in rows]}

@tool("verify_formula", "Check a formula claim against the cited reference. Use before stating any formula.",
      {"claim": "the formula as written", "key": "reference key to check against"})
def t_verify(claim, key):
    from engineai import REFERENCE, check_claim
    ref = next((r for r in REFERENCE if r["key"] == key), None)
    if not ref: return {"error": f"unknown key '{key}'"}
    verdict, detail = check_claim(claim, ref)
    return {"verdict": verdict, "detail": detail, "reference": ref["expr"], "source": ref["src"]}

@tool("run_generator", "Run one of the engineering generators (CAD, drawings, plots, solvers, documents).",
      {"name": "generator name from list_generators", "args": "object of arguments"})
def t_generator(name, args=None):
    import generators as G
    try: import generators_pro                       # extends the same registry
    except Exception: pass
    if name not in G.REGISTRY: return {"error": f"unknown generator '{name}'"}
    if not G.available(name):
        return {"error": f"'{name}' needs {', '.join(G.REGISTRY[name].needs)}"}
    r = G.REGISTRY[name](**(args or {}))
    return {"result": r}

@tool("list_generators", "List available generators and what each produces.", {})
def t_list():
    import generators as G
    try: import generators_pro
    except Exception: pass
    return {"generators": [{"name": k, "category": f.cat, "does": f.doc}
                           for k, f in sorted(G.REGISTRY.items()) if G.available(k)]}

@tool("visualise", "Produce the interactive 3D field view for a solved beam problem.",
      {"P": "load N", "L": "length m", "E": "modulus Pa", "b": "width m", "h": "depth m"})
def t_viz(P=1000.0, L=1.0, E=200e9, b=0.05, h=0.10):
    import viz3d
    path, tip, smax = viz3d.demo_beam(float(P), float(L), float(E), float(b), float(h))
    return {"view": path, "tip_deflection_m": tip, "sigma_max_Pa": smax}

@tool("make_beam_cad", "Make a CAD solid of the beam just analysed: STEP + STL + a 3D view. "
      "Use this when the user asks for CAD 'of it' after a beam calculation.",
      {"L": "length m", "b": "width m", "h": "depth m", "name": "file name"})
def t_beam_cad(L=None, b=0.05, h=0.10, name="beam"):
    import generators as G
    L = float(L or CONTEXT.get("values", {}).get("L") or 1.0)
    b, h = float(b), float(h)
    out = {}
    if G.available("cad_step"):
        r = G.REGISTRY["cad_step"](w=L*1000, d=b*1000, h=h*1000, hole=min(b, h)*1000*0.2,
                                   name=name)
        out["step"], out["stl"] = (r if isinstance(r, list) else [r, None])[:2]
    else:
        out["stl"] = G.REGISTRY["stl_part"](w=L*1000, d=b*1000, h=h*1000, rib=False, name=name)
    if out.get("stl"):
        out["view"] = G.REGISTRY["viewer_3d"](stl=out["stl"], title=f"{name} {L:g} m beam")
        CONTEXT["last_geometry"] = out["stl"]
    out["dimensions_m"] = {"L": L, "b": b, "h": h}
    return out

@tool("final_answer", "Give the finished answer. Call this once, last.",
      {"answer": "the answer for the user", "evidence": "what verified it"})
def t_final(answer, evidence=""):
    return {"answer": answer, "evidence": evidence}

# ============================================================== backends
class Backend:
    name = "base"
    def complete(self, system, messages): raise NotImplementedError

class OllamaBackend(Backend):
    """Uses the /api/chat endpoint with format=json, which CONSTRAINS decoding to
    valid JSON. `ollama run <model> "<wall of text>"` cannot do that and a 7B will
    reply with prose every time. This was the difference between 'reply was not
    valid JSON' and a working agent."""
    name = "ollama"
    def __init__(self, model=None, timeout=180, host=None):
        import shutil
        self.host = host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        if not self.host.startswith("http"): self.host = "http://" + self.host
        self.timeout = timeout
        self.model = model or os.environ.get("ENGINEAI_MODEL")
        self.exe = shutil.which("ollama")
        if not self.model:
            for m in self._tags():
                if "7b" in m.lower(): self.model = m; break
            else:
                t = self._tags(); self.model = t[0] if t else None

    def _tags(self):
        try:
            import urllib.request
            with urllib.request.urlopen(self.host + "/api/tags", timeout=8) as r:
                return [m["name"] for m in json.loads(r.read())["models"]]
        except Exception:
            pass
        if not self.exe: return []
        try:
            import subprocess
            ls = subprocess.run([self.exe, "list"], capture_output=True, text=True,
                                timeout=20).stdout
            return [l.split()[0] for l in ls.splitlines()[1:] if l.strip()]
        except Exception:
            return []

    def available(self): return bool(self.model)

    def complete(self, system, messages):
        import urllib.request
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
            "format": "json",                     # <- constrains output to valid JSON
            "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 400},
        }).encode()
        req = urllib.request.Request(self.host + "/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())["message"]["content"]
        except Exception as e:
            if not self.exe: raise
            import subprocess                      # last resort: the CLI
            convo = system + "\n\n" + "\n\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in messages)
            r = subprocess.run([self.exe, "run", self.model, "--format", "json", convo],
                               capture_output=True, text=True, timeout=self.timeout)
            return (r.stdout or "").strip()

class APIBackend(Backend):
    """For when you go online. Any OpenAI-compatible endpoint, or Anthropic."""
    name = "api"
    def __init__(self, provider=None, model=None):
        self.provider = provider or os.environ.get("ENGINEAI_PROVIDER", "openai")
        self.model = model or os.environ.get("ENGINEAI_API_MODEL", "")
    def available(self):
        k = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(self.provider)
        return bool(k and os.environ.get(k))
    def complete(self, system, messages):
        if self.provider == "anthropic":
            import anthropic
            c = anthropic.Anthropic()
            m = c.messages.create(model=self.model or "claude-sonnet-4-20250514",
                                  max_tokens=1500, system=system,
                                  messages=[{"role": x["role"], "content": x["content"]}
                                            for x in messages])
            return m.content[0].text
        import openai
        c = openai.OpenAI()
        m = c.chat.completions.create(model=self.model or "gpt-4o-mini",
                                      messages=[{"role": "system", "content": system}] +
                                               [{"role": x["role"], "content": x["content"]}
                                                for x in messages])
        return m.choices[0].message.content

class ScriptedBackend(Backend):
    """Deterministic backend for testing the loop itself."""
    name = "scripted"
    def __init__(self, script): self.script, self.i = script, 0
    def available(self): return True
    def complete(self, system, messages):
        r = self.script[min(self.i, len(self.script)-1)]; self.i += 1; return r

def pick_backend(prefer=None):
    """API-first. The local model is OFF unless you ask for it.

    ENGINEAI_MODEL_SOURCE = api     (default) hosted providers only
                          = local   ollama only
                          = auto    hosted, falling back to ollama
    """
    src = os.environ.get("ENGINEAI_MODEL_SOURCE", "api").lower()
    hosted = None
    try:
        from keypool import PoolBackend        # per-role pools, automatic failover
        h = PoolBackend()
        if h.available(): hosted = h
    except Exception:
        pass
    if hosted is None:
        try:
            from providers import HostedBackend
            h = HostedBackend()
            if h.available(): hosted = h
        except Exception:
            pass
    if src == "local":
        b = OllamaBackend()
        return b if b.available() else None
    if src == "api":
        return hosted                          # no silent fallback to a weak local model
    for b in (hosted, OllamaBackend()):        # auto
        if b is not None and b.available(): return b
    return None

def why_no_backend():
    """A useful message instead of a stack trace."""
    src = os.environ.get("ENGINEAI_MODEL_SOURCE", "api").lower()
    try:
        import keypool as K
        parked = [(n, e.get("why", ""), e.get("parked_until", 0))
                  for n, e in K.load().items() if e.get("parked_until", 0) > K.now()]
        keys = [p["name"] for p in K.POOL if K.has_key(p)]
        if not keys:
            return ("No API key set. Add one:\n"
                    "  python keypool.py add openrouter sk-or-...\n"
                    "  python keypool.py links      # where to get each one")
        if parked:
            n, why, u = min(parked, key=lambda x: x[2])
            return (f"All {len(keys)} provider(s) are parked. Soonest back: {n} ({why}) "
                    f"in {max(0,(u-K.now())/60):.0f} min.\n"
                    "Add another key to keep going: python keypool.py links")
    except Exception:
        pass
    return f"No model available (ENGINEAI_MODEL_SOURCE={src}). python keypool.py status"



@tool("derive_verified",
      "Generate and self-verify a solver for an engineering quantity that has NO closed-form "
      "entry in the reference table. Runs K independent solvers in an isolated sandbox and returns "
      "an answer ONLY if they agree and the units check out (else verified=false). Use only after "
      "lookup_formula and search_library both find nothing.",
      {"question": "the quantity to compute, including the given numbers and target unit",
       "expected_unit": "optional SI unit the answer must have, e.g. 'Pa' or 'm^2'"})
def t_derive_verified(question, expected_unit=None):
    import os
    from model_router import Router, ollama_source
    from consensus import solve_consensus
    from sandbox_runner import run as _sbx
    models = [m.strip() for m in os.environ.get(
        "ENGINEAI_LOCAL_MODELS", "qwen2.5:7b,qwen2.5:14b").split(",") if m.strip()]
    private = os.environ.get("ENGINEAI_PRIVATE", "1") != "0"
    k = int(os.environ.get("ENGINEAI_CONSENSUS_K", "3"))
    fn, names = Router([ollama_source(m) for m in models]).model_fn(k=k, private=private)
    if not names:
        return {"verified": False, "error": "no local model available for private derivation",
                "hint": "start ollama and pull a model, or set ENGINEAI_PRIVATE=0 to allow cloud"}
    rec = solve_consensus(question, fn, _sbx, k=k, expected_unit=expected_unit)
    rec["sources"], rec["diversity"] = names, len(set(names))
    return rec



@tool("vault_search",
      "Private semantic search over the owner's OWN indexed engineering files (local, never "
      "uploaded). Returns relevant passages with source + score. Use for prior designs, internal "
      "standards and notes; complements search_library (published textbooks).",
      {"query": "what to find", "k": "how many passages, default 4"})
def t_vault_search(query, k=4):
    import os
    from vault_rag import Vault, embed_ollama
    db = os.environ.get("ENGINEAI_VAULT_INDEX", "vault_index.json")
    if not os.path.exists(db):
        return {"found": False, "note": f"no vault index at {db}; build with: python vault_rag.py --index <dir> --out {db}"}
    try:
        hits = Vault(embed_fn=embed_ollama, path=db).load().query(query, int(k))
    except Exception as e:
        return {"found": False, "error": f"{type(e).__name__}: {e}"}
    return {"found": bool(hits), "results": hits}



@tool("beam_design",
      "Size/check a beam: section properties, bending stress, deflection and factor of safety vs a "
      "material yield. sections: rectangle(b,h) / solid_circle(do) / tube(do,di) / ibeam(b,h,tw,tf). "
      "beams: cantilever_point / cantilever_udl / simply_point / simply_udl. Units N, mm, MPa.",
      {"section": "rectangle|solid_circle|tube|ibeam", "beam": "cantilever_point|...",
       "load": "N (or N/mm for udl)", "length": "mm", "E": "MPa", "yield_mpa": "MPa",
       "b": "mm", "h": "mm", "do": "mm", "di": "mm", "tw": "mm", "tf": "mm", "target_fos": "e.g. 1.5"})
def t_beam_design(section="rectangle", beam="cantilever_point", load=500.0, length=300.0, E=200000.0,
                  yield_mpa=250.0, b=20.0, h=40.0, do=20.0, di=10.0, tw=6.0, tf=8.0, target_fos=1.5):
    import structural
    args = {"rectangle": {"b": float(b), "h": float(h)}, "solid_circle": {"d": float(do)},
            "tube": {"do": float(do), "di": float(di)},
            "ibeam": {"b": float(b), "h": float(h), "tw": float(tw), "tf": float(tf)}}
    if section not in args: return {"error": f"unknown section '{section}'"}
    return structural.design_check(section, args[section], beam, float(load), float(length),
                                   float(E), float(yield_mpa), float(target_fos))



@tool("make_drawing_sheet",
      "Generate a multi-view mechanical drawing SHEET (SVG + DXF) with title block and BOM from a "
      "parametric part; cross-checked against the 3D solid. Returns file paths, BOM and view dims. Units mm.",
      {"part": "e.g. mounting_plate", "material": "e.g. AL 6061-T6",
       "L": "mm", "W": "mm", "T": "mm", "hole_d": "mm"})
def t_make_drawing_sheet(part="mounting_plate", material="AL 6061-T6", L=None, W=None, T=None, hole_d=None):
    import os, drawings_sheet
    ov = {k: float(v) for k, v in dict(L=L, W=W, T=T, hole_d=hole_d).items() if v is not None}
    d = drawings_sheet.make_sheet(part, material, outdir=os.path.join("out", "sheets"), **ov)
    return {"svg": d["svg"], "dxf": d["dxf"], "bom": d["bom"],
            "views": {k: {"w": v["w"], "h": v["h"]} for k, v in d["views"].items()}, "params": d["params"]}



@tool("draw_part",
      "TRUE multi-view mechanical drawing (SVG+DXF, hidden lines) of a parametric part via OCC "
      "hidden-line projection. Parts: mounting_plate, l_bracket, shaft, flange, u_channel.",
      {"part": "part name", "material": "e.g. AL 6061-T6"})
def t_draw_part(part="mounting_plate", material="AL 6061-T6"):
    import os, drawings_project
    d = drawings_project.make_sheet(part, material, outdir=os.path.join("out", "proj"))
    return {"svg": d["svg"], "dxf": d["dxf"], "bom": d["bom"], "views": d["views"]}


@tool("design_part",
      "End-to-end: size a rectangular bar to carry a load at a target factor of safety, build the CAD "
      "solid, project a drawing, compute mass+BOM, return ONE verified report. Units N, mm.",
      {"load_N": "N", "span_mm": "mm", "width_mm": "mm", "material": "e.g. AISI_1018_steel",
       "target_fos": "e.g. 2.0", "beam": "cantilever_point|cantilever_udl|simply_point|simply_udl"})
def t_design_part(load_N=2000.0, span_mm=300.0, width_mm=40.0, material="AISI_1018_steel",
                  target_fos=2.0, beam="cantilever_point"):
    import os, design_part as dp
    r = dp.design_part(float(load_N), float(span_mm), float(width_mm), material,
                       float(target_fos), beam, outdir=os.path.join("out", "design"))
    return {k: r[k] for k in ("requirement", "result", "bom", "files", "verified", "content_hash")}

@tool("standard_section",
      "Look up a STANDARD steel section (EN 10365 IPE) by designation, e.g. 'IPE 200'. Returns real "
      "catalogue dimensions, area, second moment I and elastic modulus Z in mm units, ready for "
      "beam_design. Use this instead of inventing a rectangular bar when the user names a section "
      "or wants something a supplier actually stocks.",
      {"designation": "e.g. 'IPE 200'"})
def t_standard_section(designation):
    import standards
    try:
        return standards.section(designation)
    except KeyError as e:
        return {"error": str(e)}


@tool("select_section",
      "Choose the LIGHTEST standard IPE section that meets a required elastic section modulus Z "
      "(mm^3). Use after computing the required Z from the bending moment and allowable stress: "
      "Z_required = M / sigma_allowable. Returns the section or an error if nothing in the range fits.",
      {"required_Z_mm3": "required elastic section modulus in mm^3"})
def t_select_section(required_Z_mm3):
    import standards
    s = standards.lightest_section(float(required_Z_mm3))
    if s is None:
        return {"found": False,
                "note": f"no catalogued IPE reaches Z={float(required_Z_mm3):.0f} mm^3 "
                        f"(largest is IPE 600). A deeper or built-up section is needed."}
    return {"found": True, "section": s}


@tool("bolt_sizing",
      "ISO metric bolt capacity and bolt count. YOU MUST STATE THE LOAD DIRECTION: 'tension' pulls "
      "along the bolt axis and uses the ISO 898-1 proof load; 'shear' acts across the bolt (the "
      "usual case for a beam end reaction or a bracket) and uses the much smaller EN 1993-1-8 shear "
      "resistance. Sizing a shear connection on tensile capacity overstates it by roughly two. "
      "Returns fastener capacity only - plate bearing, block shear, edge distance, welds and "
      "eccentricity are separate checks this does not perform.",
      {"nominal_d_mm": "thread nominal diameter, e.g. 12 for M12",
       "property_class": "ISO 898-1 class: 4.6, 5.8, 8.8, 10.9 or 12.9",
       "loading": "REQUIRED when sizing a group: 'tension' or 'shear'",
       "load_N": "optional total load to size a bolt group for",
       "safety_factor": "optional, default 2.0 when sizing a group",
       "shear_planes": "1 for single shear (default), 2 for double shear"})
def t_bolt_sizing(nominal_d_mm=12.0, property_class="8.8", load_N=None, safety_factor=2.0,
                  loading="tension", shear_planes=1):
    import standards
    try:
        out = {"tension": standards.bolt_capacity(float(nominal_d_mm), property_class),
               "shear": standards.bolt_shear_capacity(float(nominal_d_mm), property_class,
                                                      shear_planes=int(shear_planes))}
        if load_N is not None:
            out["group"] = standards.bolts_required(float(load_N), float(nominal_d_mm),
                                                    property_class, float(safety_factor),
                                                    loading=loading)
        out["reminder"] = ("A beam end reaction, a bracket load and most lap joints are SHEAR. "
                           "Use loading='shear' for those.")
        return out
    except (KeyError, ValueError) as e:
        return {"error": str(e)}


@tool("steel_beam_check",
      "FULL EN 1993-1-1 check of a standard steel beam: cross-section classification, bending, "
      "SHEAR, and LATERAL-TORSIONAL BUCKLING, plus deflection. Use this instead of beam_design "
      "whenever the member is a real steel section - beam_design checks bending stress only and "
      "will badly overstate a long unrestrained beam (LTB can cut capacity to a fifth). "
      "restraint_spacing_mm is the unrestrained length of the compression flange; leave it out and "
      "the full span is assumed, which is the conservative case.",
      {"section": "e.g. 'IPE 300'", "grade": "S235|S275|S355|S420|S460",
       "span_mm": "mm", "udl_N_per_mm": "uniformly distributed load in N/mm",
       "point_load_N": "alternative: point load at mid-span, N",
       "restraint_spacing_mm": "unrestrained length for LTB, default = full span",
       "C1": "moment-shape factor, 1.0 for uniform moment (conservative)"})
def t_steel_beam_check(section="IPE 300", grade="S275", span_mm=6000.0, udl_N_per_mm=None,
                       point_load_N=None, restraint_spacing_mm=None, C1=1.0):
    import steel_design
    return steel_design.check_beam(
        section, grade, float(span_mm),
        None if udl_N_per_mm is None else float(udl_N_per_mm),
        None if point_load_N is None else float(point_load_N),
        None if restraint_spacing_mm is None else float(restraint_spacing_mm), float(C1))


@tool("steel_column_check",
      "EN 1993-1-1 6.3.1 axial compression check of a steel column: compression class, Euler "
      "critical load and flexural buckling about BOTH axes, taking the worse. Use this for any "
      "member carrying axial compression - a stress check (N/A vs fy) overstates a real column by "
      "three to five times, because it buckles long before it squashes. The compression "
      "slenderness limits are NOT the bending ones, so steel_beam_check cannot substitute. "
      "L_cr_z_mm is the override that matters most in practice: columns are usually braced about "
      "the weak axis at mid-height, which changes which axis governs.",
      {"section": "e.g. 'HEB 200', 'HEA 300', 'SHS 200x200x10', 'CHS 219.1x10'",
       "grade": "S235|S275|S355|S420|S460", "length_mm": "member length, mm",
       "end_condition": "pinned-pinned|fixed-fixed|fixed-pinned|fixed-free|fixed-fixed-sway",
       "N_Ed_N": "applied axial compression, N (omit for capacity only)",
       "L_cr_y_mm": "override major-axis buckling length, mm",
       "L_cr_z_mm": "override minor-axis buckling length, mm (e.g. mid-height bracing)"})
def t_steel_column_check(section="HEB 200", grade="S275", length_mm=3000.0,
                         end_condition="pinned-pinned", N_Ed_N=None,
                         L_cr_y_mm=None, L_cr_z_mm=None):
    import column_design
    return column_design.compression_resistance(
        section, grade, float(length_mm), end_condition,
        None if N_Ed_N is None else float(N_Ed_N),
        None if L_cr_y_mm is None else float(L_cr_y_mm),
        None if L_cr_z_mm is None else float(L_cr_z_mm))


@tool("beam_column_check",
      "EN 1993-1-1 6.3.3 combined axial compression AND major-axis bending (equations 6.61/6.62 "
      "with Annex B interaction factors). Use this whenever a member carries BOTH - which is most "
      "real columns, since beams frame into them eccentrically. Not optional refinement: a member "
      "at 0.6 axial and 0.6 bending passes each check alone and fails the combination at ~1.16, "
      "and neither individual check can reveal that.",
      {"section": "e.g. 'HEB 240'", "grade": "S235|S275|S355|S420|S460",
       "length_mm": "member length, mm", "N_Ed_N": "axial compression, N",
       "My_Ed_Nmm": "major-axis design moment, N.mm",
       "end_condition": "pinned-pinned|fixed-fixed|fixed-pinned|fixed-free|fixed-fixed-sway",
       "restraint_spacing_mm": "unrestrained length for LTB, default = member length",
       "C_my": "moment-shape factor for 6.61, 1.0 = uniform moment (conservative)",
       "C_mLT": "moment-shape factor for LTB, 1.0 conservative"})
def t_beam_column_check(section="HEB 200", grade="S275", length_mm=3000.0,
                        N_Ed_N=0.0, My_Ed_Nmm=0.0, end_condition="pinned-pinned",
                        restraint_spacing_mm=None, C_my=1.0, C_mLT=1.0):
    import column_design
    return column_design.beam_column(
        section, grade, float(length_mm), float(N_Ed_N), float(My_Ed_Nmm),
        end_condition, restraint_spacing_mm=(None if restraint_spacing_mm is None
                                             else float(restraint_spacing_mm)),
        C_my=float(C_my), C_mLT=float(C_mLT))


@tool("size_column",
      "Select the LIGHTEST catalogue section that carries a given axial load (and optional "
      "moment) over a given height, searching HEB, HEA and SHS. IPE is deliberately excluded - "
      "it is a beam section whose weak axis is ~7% of its strong axis, so it buckles sideways. "
      "Returns the choice, its utilisation, and the next three heavier options.",
      {"N_Ed_N": "axial compression, N", "length_mm": "column height, mm",
       "grade": "S235|S275|S355|S420|S460",
       "end_condition": "pinned-pinned|fixed-fixed|fixed-pinned|fixed-free|fixed-fixed-sway",
       "My_Ed_Nmm": "optional co-existing major-axis moment, N.mm"})
def t_size_column(N_Ed_N, length_mm=3000.0, grade="S275",
                  end_condition="pinned-pinned", My_Ed_Nmm=0.0):
    import column_design
    return column_design.size_column(float(N_Ed_N), float(length_mm), grade,
                                     end_condition, float(My_Ed_Nmm or 0.0))


@tool("load_combination",
      "EN 1990 load combinations - turn REAL loads into design actions. Use this BEFORE any "
      "structural check. Every other structural tool expects an already-factored load and cannot "
      "tell whether it got one; entering unfactored loads understates the design action by ~40%. "
      "Returns ULS (6.10 and the 6.10a/b pair, taking the worse) and all three SLS combinations - "
      "deflection must be checked at SLS, never at ULS.",
      {"permanent": "characteristic permanent action Gk (number, or list)",
       "variable": "characteristic variable action Qk (number, or list of "
                   "{'value':x,'category':'B_office'})",
       "category": "action category for a single variable action: A_domestic|B_office|"
                   "C_congregation|D_shopping|E_storage|H_roof|snow_le1000m|wind|thermal"})
def t_load_combination(permanent, variable=None, category="B_office"):
    import loads
    v = variable
    if isinstance(variable, (int, float)):
        v = [{"value": float(variable), "category": category}]
    return loads.combine(permanent, v)


@tool("imposed_load",
      "EN 1991-1-1 Table 6.2 imposed floor load for an occupancy, plus EN 1991-1-1 Annex A "
      "material densities for dead load. Use this when the user describes a BUILDING USE "
      "('office', 'storage') rather than giving a load.",
      {"occupancy": "A_domestic_floor|B_office|C1_tables|C3_no_obstacles|D1_retail|"
                    "E1_storage|H_roof_inaccessible|I_roof_accessible",
       "spacing_m": "optional beam spacing, to convert kN/m2 into a UDL in N/mm"})
def t_imposed_load(occupancy="B_office", spacing_m=None):
    import loads
    r = loads.imposed_load(occupancy)
    if spacing_m:
        r["udl_N_per_mm"] = loads.area_load_to_udl(r["qk_kN_per_m2"], float(spacing_m))
    r["densities_kN_per_m3"] = loads.DENSITY_kN_m3
    return r


@tool("torsion",
      "Shaft in torsion: J, maximum shear stress tau = Tr/J, angle of twist theta = TL/GJ, and "
      "the hollow-vs-solid trade. Also handles COMBINED bending and torsion by von Mises and "
      "Tresca - which matters because a bending-only check on a shaft that also carries torque "
      "reports a factor of safety that does not exist.",
      {"T_Nmm": "torque", "d_mm": "outer diameter", "L_mm": "length",
       "G_MPa": "shear modulus (79000 for steel)", "d_inner_mm": "bore, 0 for solid",
       "M_Nmm": "optional co-existing bending moment, triggers the combined check",
       "sigma_y_MPa": "optional yield, for factors of safety"})
def t_torsion(T_Nmm, d_mm, L_mm=1000.0, G_MPa=79000.0, d_inner_mm=0.0,
              M_Nmm=None, sigma_y_MPa=None):
    import mechanics
    out = mechanics.shaft_torsion(float(T_Nmm), float(d_mm), float(L_mm),
                                  float(G_MPa), float(d_inner_mm or 0.0))
    if M_Nmm:
        out["combined"] = mechanics.combined_bending_torsion(
            float(M_Nmm), float(T_Nmm), float(d_mm),
            float(sigma_y_MPa) if sigma_y_MPa else None)
    return out


@tool("pressure_vessel",
      "Thin- or thick-walled pressure vessel stresses. Hoop is exactly TWICE longitudinal in a "
      "cylinder, which is why vessels split lengthwise. Automatically flags when t/r > 0.1 and "
      "thin-wall theory no longer applies, and can solve the exact Lame thick-wall case.",
      {"p_MPa": "internal pressure", "r_mm": "inner radius", "t_mm": "wall thickness",
       "shape": "cylinder|sphere", "thick": "true to use the exact Lame solution"})
def t_pressure_vessel(p_MPa, r_mm, t_mm, shape="cylinder", thick=False):
    import mechanics
    p, r, t = float(p_MPa), float(r_mm), float(t_mm)
    if thick:
        return mechanics.thick_cylinder(p, r, r + t)
    return (mechanics.thin_sphere(p, r, t) if shape == "sphere"
            else mechanics.thin_cylinder(p, r, t))


@tool("stress_concentration",
      "Stress concentration factor Kt at a hole or notch, and what it does to the safety margin. "
      "The most commonly forgotten factor in mechanical design: a plain hole TRIPLES the local "
      "stress, so a nominal factor of safety of 2.5 is really 0.83.",
      {"sigma_nominal_MPa": "nominal stress on the net section",
       "feature": "circular_hole|elliptical|notch",
       "d_over_W": "hole diameter / plate width, for circular_hole",
       "a": "semi-axis across the load (elliptical) or notch depth",
       "b_or_rho": "semi-axis along the load, or notch root radius",
       "sigma_y_MPa": "optional yield, to show the margin collapse"})
def t_stress_concentration(sigma_nominal_MPa, feature="circular_hole", d_over_W=0.0,
                           a=None, b_or_rho=None, sigma_y_MPa=None):
    import mechanics
    if feature == "elliptical":
        kt = mechanics.kt_elliptical_hole(float(a), float(b_or_rho))
    elif feature == "notch":
        kt = mechanics.kt_notch_inglis(float(a), float(b_or_rho))
    else:
        kt = mechanics.kt_circular_hole(float(d_over_W or 0.0))
    return mechanics.stress_concentration(float(sigma_nominal_MPa), kt,
                                          float(sigma_y_MPa) if sigma_y_MPa else None)


@tool("beam_case",
      "Beam cases beyond the simply-supported and cantilever pair: fixed-fixed, propped "
      "cantilever, OFF-CENTRE point load, and overhanging beams. The overhang case reports "
      "UPLIFT at the far support, which is a detailing requirement a symmetric solver never "
      "reveals.",
      {"case": "fixed_fixed_point|fixed_fixed_udl|propped_cantilever_udl|"
               "simply_point_offset|overhang_point",
       "load": "P in N, or w in N/mm for a UDL", "L_mm": "span",
       "a_mm": "load position from the left support, or overhang length",
       "b_mm": "section width", "h_mm": "section depth", "E_MPa": "modulus"})
def t_beam_case(case, load, L_mm, a_mm=None, b_mm=30.0, h_mm=50.0, E_MPa=200000.0):
    import mechanics, structural
    sec = structural.rectangle(float(b_mm), float(h_mm))
    I, E, L, P = sec["I"], float(E_MPa), float(L_mm), float(load)
    fns = {"fixed_fixed_point": lambda: mechanics.fixed_fixed_point(P, L, E, I),
           "fixed_fixed_udl": lambda: mechanics.fixed_fixed_udl(P, L, E, I),
           "propped_cantilever_udl": lambda: mechanics.propped_cantilever_udl(P, L, E, I),
           "simply_point_offset": lambda: mechanics.simply_point_offset(
               P, float(a_mm), L - float(a_mm), E, I),
           "overhang_point": lambda: mechanics.overhang_point(P, L, float(a_mm), E, I)}
    if case not in fns:
        return {"error": f"unknown case '{case}'. Known: {', '.join(fns)}"}
    r = fns[case]()
    r["sigma_MPa"] = r.get("M", 0.0) / sec["Z"]
    r["section"] = {"b_mm": b_mm, "h_mm": h_mm, "I_mm4": I, "Z_mm3": sec["Z"]}
    return r


@tool("heat_transfer",
      "Conduction, convection, radiation, fins, transients and heat exchangers. Use for any "
      "'how hot does it get' question. SI units - W, m, K. Radiation REFUSES Celsius input, "
      "because using it is an order-of-magnitude error.",
      {"mode": "plane_wall|composite_wall|cylindrical|convection|radiation|fin|"
               "lumped|semi_infinite|contact|lmtd|heat_exchanger|resistance_network",
       "args": "JSON object of arguments for that mode - see thermal.py docstrings"})
def t_heat_transfer(mode, args=None):
    import thermal
    a = args or {}
    if isinstance(a, str):
        a = json.loads(a)
    fns = {"plane_wall": thermal.plane_wall, "composite_wall": thermal.composite_wall,
           "cylindrical": thermal.cylindrical_wall, "convection": thermal.convection,
           "radiation": thermal.radiation, "fin": thermal.fin_rectangular,
           "lumped": thermal.lumped_capacitance,
           "semi_infinite": thermal.semi_infinite_step,
           "contact": thermal.contact_temperature, "lmtd": thermal.lmtd,
           "heat_exchanger": thermal.heat_exchanger,
           "resistance_network": thermal.resistance_network}
    if mode not in fns:
        return {"error": f"unknown mode '{mode}'. Known: {', '.join(fns)}"}
    try:
        return fns[mode](**a)
    except (TypeError, ValueError, KeyError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool("electromagnetics",
      "Analytic electromagnetics: field around a wire/solenoid/toroid/loop, force between "
      "conductors, coaxial L and C and impedance, capacitance, magnetic circuits with air gaps, "
      "and skin depth. SI units. Note the force between conductors goes as I^2, so fault "
      "currents produce forces thousands of times the rated value.",
      {"quantity": "b_wire|b_solenoid|b_toroid|b_loop|force_wires|coax|capacitance|"
                   "magnetic_circuit|skin_depth|conductivity",
       "args": "JSON object of arguments - see emag.py docstrings"})
def t_electromagnetics(quantity, args=None):
    import emag
    a = args or {}
    if isinstance(a, str):
        a = json.loads(a)
    fns = {"b_wire": emag.b_wire, "b_solenoid": emag.b_solenoid,
           "b_toroid": emag.b_toroid, "b_loop": emag.b_loop_axis,
           "force_wires": emag.force_parallel_wires, "coax": emag.coax_line,
           "capacitance": emag.capacitance_parallel_plate,
           "magnetic_circuit": emag.magnetic_circuit, "skin_depth": emag.skin_depth,
           "conductivity": emag.conductivity}
    if quantity not in fns:
        return {"error": f"unknown quantity '{quantity}'. Known: {', '.join(fns)}"}
    try:
        return fns[quantity](**a)
    except (TypeError, ValueError, KeyError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool("flow_analysis",
      "Flow beyond pipe friction: Bernoulli, nozzles, Torricelli efflux, Pitot, sphere drag "
      "across all four Reynolds regimes, terminal velocity, Blasius boundary layer, thin-airfoil "
      "lift, induced drag, and Manning open-channel flow. SI units.",
      {"analysis": "bernoulli|nozzle|torricelli|pitot|drag_sphere|terminal_velocity|"
                   "boundary_layer|plate_drag|airfoil|lift|induced_drag|channel|normal_depth",
       "args": "JSON object of arguments - see fluid_mech.py docstrings"})
def t_flow_analysis(analysis, args=None):
    import fluid_mech
    a = args or {}
    if isinstance(a, str):
        a = json.loads(a)
    fns = {"bernoulli": fluid_mech.bernoulli, "nozzle": fluid_mech.nozzle,
           "torricelli": fluid_mech.torricelli, "pitot": fluid_mech.pitot,
           "drag_sphere": fluid_mech.drag_sphere,
           "terminal_velocity": fluid_mech.terminal_velocity,
           "boundary_layer": fluid_mech.blasius_boundary_layer,
           "plate_drag": fluid_mech.plate_drag, "airfoil": fluid_mech.thin_airfoil,
           "lift": fluid_mech.lift_force, "induced_drag": fluid_mech.induced_drag,
           "channel": fluid_mech.rectangular_channel,
           "normal_depth": fluid_mech.normal_depth}
    if analysis not in fns:
        return {"error": f"unknown analysis '{analysis}'. Known: {', '.join(fns)}"}
    try:
        return fns[analysis](**a)
    except (TypeError, ValueError, KeyError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool("fatigue_check",
      "Fatigue life and fracture. Use whenever loading is REPEATED - fatigue causes more "
      "in-service failures than static overload, and a static check cannot see it. Handles "
      "S-N life, Miner damage, mean-stress correction, EN 1993-1-9 weld detail categories, and "
      "linear-elastic fracture mechanics. If a CRACK is present, LEFM governs and the S-N answer "
      "is irrelevant - the tool says which model applies.",
      {"material": "AISI_1018_steel|AISI_4340_steel|AL_6061_T6|AL_7075_T6|Ti_6Al_4V|"
                   "stainless_304|cast_iron_grey",
       "sigma_max_MPa": "peak stress", "sigma_min_MPa": "trough stress (negative if reversed)",
       "crack_length_mm": "optional existing crack - switches to fracture mechanics",
       "weld_detail": "optional EN 1993-1-9 category, e.g. transverse_butt_weld_as_welded",
       "stress_range_MPa": "stress range for the weld-detail check",
       "cycles": "applied cycles, for a damage ratio"})
def t_fatigue_check(material="AISI_1018_steel", sigma_max_MPa=None, sigma_min_MPa=0.0,
                    crack_length_mm=None, weld_detail=None, stress_range_MPa=None,
                    cycles=None):
    import fatigue
    if weld_detail:
        return fatigue.en1993_fatigue(weld_detail, float(stress_range_MPa),
                                      float(cycles) if cycles else None)
    if sigma_max_MPa is None:
        return {"error": "give sigma_max_MPa, or weld_detail with stress_range_MPa"}
    return fatigue.assess(material, float(sigma_max_MPa), float(sigma_min_MPa or 0.0),
                          float(crack_length_mm) if crack_length_mm else None)


@tool("circuit_analysis",
      "Transients, op-amps, Thevenin equivalents, rectifiers and BJT bias - the electronics "
      "circuits.py could not do. Op-amp results CLIP against the supply rails rather than "
      "reporting an impossible ideal gain, and a loaded voltage divider reports its droop.",
      {"analysis": "thevenin|rc_step|rc_waveform|rl_step|rlc|opamp_inverting|"
                   "opamp_noninverting|opamp_difference|half_wave|full_wave|bjt|max_power",
       "args": "JSON object of arguments - see circuits_ext.py docstrings"})
def t_circuit_analysis(analysis, args=None):
    import circuits_ext as ce
    a = args or {}
    if isinstance(a, str):
        a = json.loads(a)
    fns = {"thevenin": ce.thevenin_divider, "rc_step": ce.rc_step,
           "rc_waveform": ce.rc_waveform, "rl_step": ce.rl_step,
           "rlc": ce.rlc_transient, "opamp_inverting": ce.opamp_inverting,
           "opamp_noninverting": ce.opamp_noninverting,
           "opamp_difference": ce.opamp_difference,
           "half_wave": ce.half_wave_rectifier, "full_wave": ce.full_wave_rectifier,
           "bjt": ce.bjt_common_emitter, "max_power": ce.max_power_transfer}
    if analysis not in fns:
        return {"error": f"unknown analysis '{analysis}'. Known: {', '.join(fns)}"}
    try:
        r = fns[analysis](**a)
        return {"waveform": r} if isinstance(r, list) else r
    except (TypeError, ValueError, KeyError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool("fea_cross_check",
      "THE METHOD-DIVERSITY GATE. Solves a cantilever by closed-form beam theory AND by 3D "
      "finite element (CalculiX), which share no code, equations or discretisation, then reports "
      "whether they agree. Use this to VERIFY a structural number rather than merely compute it - "
      "an analytic formula checked against itself is not verification. Can also run a mesh "
      "convergence study, which is what distinguishes a converged answer from a lucky one.",
      {"mode": "cross_check|cantilever|convergence|sections",
       "P_N": "tip load", "L_mm": "span", "b_mm": "width", "h_mm": "depth",
       "E_MPa": "modulus", "nu": "Poisson ratio", "tolerance": "agreement tolerance, default 0.05"})
def t_fea_cross_check(mode="cross_check", P_N=1000.0, L_mm=500.0, b_mm=20.0,
                      h_mm=40.0, E_MPa=210000.0, nu=0.3, tolerance=0.05):
    import fea
    P, L, b, h, E = float(P_N), float(L_mm), float(b_mm), float(h_mm), float(E_MPa)
    if mode == "cantilever":
        return fea.cantilever(P, L, b, h, E, float(nu))
    if mode == "convergence":
        return fea.mesh_convergence(P, L, b, h, E, float(nu))
    if mode == "sections":
        return fea.cross_check_sections(P, L, E, float(nu), tolerance=float(tolerance))
    return fea.cross_check(P, L, b, h, E, float(nu), float(tolerance))


@tool("multiphysics",
      "Chains where one physics drives another: electro-thermal Joule heating WITH the "
      "resistance-temperature feedback (which can run away, and the tool refuses to return a "
      "temperature when it does), thermo-mechanical restrained expansion, one-way wind-on-plate, "
      "magneto-structural busbar fault forces, temperature-derated shaft fatigue, and the full "
      "current-to-stress busbar chain. Use when a problem crosses disciplines - the answer is "
      "invisible to any single one of them.",
      {"chain": "joule_heating|thermal_stress|wind_on_plate|plate|lorentz_beam|"
                "fault_forces|shaft_life|busbar|steel_at_temperature",
       "args": "JSON object of arguments - see multiphysics.py docstrings"})
def t_multiphysics(chain, args=None):
    import multiphysics as mp
    a = args or {}
    if isinstance(a, str):
        a = json.loads(a)
    fns = {"joule_heating": mp.joule_heating_coupled,
           "thermal_stress": mp.thermal_stress_check,
           "wind_on_plate": mp.wind_on_plate, "plate": mp.plate_clamped_circular,
           "lorentz_beam": mp.lorentz_beam_deflection,
           "fault_forces": mp.fault_force_scaling, "shaft_life": mp.shaft_life,
           "busbar": mp.busbar_chain,
           "steel_at_temperature": mp.steel_at_temperature}
    if chain not in fns:
        return {"error": f"unknown chain '{chain}'. Known: {', '.join(fns)}"}
    try:
        return fns[chain](**a)
    except (TypeError, ValueError, KeyError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool("equation_lookup",
      "Search the self-checking equation library - 109 equations across 17 disciplines, every one "
      "EXECUTABLE and verified against a worked example at build time. Search by term, by "
      "discipline, by an input variable ('what uses a Reynolds number'), or by RESULT UNIT ('what "
      "can I compute that gives me a pressure'). Returns the expression, variables with units, "
      "validity conditions and the literature source. Use this before deriving anything by hand.",
      {"term": "free text, e.g. 'buckling' or 'skin depth'",
       "discipline": "solid mechanics|structural|fluid mechanics|heat transfer|thermodynamics|"
                     "electrical|electromagnetics|materials|machine design|fatigue|fracture|"
                     "dynamics|vibration|chemical|geotechnical|civil|aerodynamics",
       "variable": "an input symbol the equation must take",
       "unit": "the unit of the result, e.g. 'Pa', 'MPa', 'W', 'N'"})
def t_equation_lookup(term=None, discipline=None, variable=None, unit=None):
    import equations
    hits = equations.search(term, discipline, variable, unit)
    return {"matches": len(hits), "disciplines": equations.disciplines(),
            "equations": hits[:40],
            "note": "every entry is executed against a worked example at build time; "
                    "use equation_evaluate to run one"}


@tool("equation_evaluate",
      "Run an equation from the library by id and get the value with its unit, validity "
      "conditions and source. Safer than re-deriving: these are verified at build time, so a "
      "transcription slip cannot survive.",
      {"equation_id": "id from equation_lookup, e.g. 'mech.euler_buckling'",
       "args": "JSON object of the equation's input variables"})
def t_equation_evaluate(equation_id, args=None):
    import equations
    a = args or {}
    if isinstance(a, str):
        a = json.loads(a)
    try:
        return equations.evaluate(equation_id, **{k: float(v) for k, v in a.items()})
    except (KeyError, TypeError, ValueError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


@tool("reference_data",
      "Authoritative reference data, downloaded from public sources and VERIFIED on load: CODATA "
      "2022 fundamental constants, NASA thermodynamic polynomials, IAPWS steam properties, the ISO "
      "standard atmosphere, atomic weights and elemental solid-state data. Every dataset is checked "
      "against values known by an independent route, so a truncated or altered download is rejected "
      "rather than cached.",
      {"dataset": "codata|nasa_thermo|atomic_weights|steam|atmosphere|elements",
       "constant": "optional: substring of a CODATA constant name to look up"})
def t_reference_data(dataset="codata", constant=None):
    import refdata
    if dataset not in refdata.DATASETS:
        return {"error": f"unknown dataset '{dataset}'. "
                         f"Known: {', '.join(refdata.DATASETS)}"}
    r = refdata.DATASETS[dataset]()
    if dataset == "codata" and constant:
        hits = {k: v for k, v in r.get("constants", {}).items()
                if constant.lower() in k.lower()}
        return {"dataset": r["dataset"], "source": r["source"],
                "verified": r["verified"], "matches": len(hits),
                "constants": dict(list(hits.items())[:25])}
    return {k: v for k, v in r.items() if k != "constants"}


@tool("list_capabilities",
      "What EngineAI can actually compute, per discipline (fluids, thermal, chemical, structural, "
      "electrical, materials, geometry, methods). Each entry is PROBED at call time with a "
      "known-correct calculation, so it reports what genuinely works rather than what is merely "
      "installed. Use this when asked what the system can do, or before claiming a capability.",
      {"discipline": "optional filter: fluids|thermal|chemical|structural|electrical|materials|geometry|methods"})
def t_list_capabilities(discipline=None):
    import capabilities
    rows = capabilities.evaluate(discipline)
    return {"summary": capabilities.summary(rows),
            "available": [{"discipline": r["discipline"], "name": r["name"], "provides": r["what"]}
                          for r in rows if r["status"] == "ok"],
            "unavailable": [{"name": r["name"], "why": r["detail"]}
                            for r in rows if r["status"] != "ok"]}


@tool("fluid_property",
      "Thermophysical property of a real fluid at a given temperature and pressure, from CoolProp's "
      "NIST-quality equations of state (~120 fluids: Water, Air, Nitrogen, CO2, R134a, Methane, "
      "Ammonia, Hydrogen, ...). Use this instead of assuming a density or viscosity.",
      {"fluid": "e.g. Water, Air, CO2, R134a", "T_K": "temperature in kelvin",
       "P_Pa": "pressure in pascal (default 101325)",
       "prop": "D=density kg/m3, V=viscosity Pa.s, C=cp J/kg/K, L=conductivity W/m/K, "
               "H=enthalpy J/kg, S=entropy J/kg/K, A=speed of sound m/s"})
def t_fluid_property(fluid="Water", T_K=293.15, P_Pa=101325.0, prop="D"):
    try:
        from CoolProp.CoolProp import PropsSI
    except Exception as e:
        return {"error": f"CoolProp unavailable: {e}"}
    units = {"D": "kg/m^3", "V": "Pa*s", "C": "J/kg/K", "L": "W/m/K",
             "H": "J/kg", "S": "J/kg/K", "A": "m/s"}
    try:
        v = PropsSI(prop, "T", float(T_K), "P", float(P_Pa), fluid)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}",
                "hint": "check the fluid name and that T,P are inside its validity range"}
    return {"fluid": fluid, "property": prop, "value": v, "unit": units.get(prop, "?"),
            "T_K": float(T_K), "P_Pa": float(P_Pa),
            "source": "CoolProp (NIST-quality reference equations of state)"}


@tool("chemical_property",
      "Look up a pure chemical by name or CAS and return its key constants: molecular weight, "
      "normal boiling point, critical temperature and pressure. Backed by the `chemicals` "
      "database (~20,000 compounds).",
      {"name": "chemical name or CAS number, e.g. 'ethanol' or '64-17-5'"})
def t_chemical_property(name):
    try:
        from chemicals import CAS_from_any, MW, Tb, Tc, Pc
    except Exception as e:
        return {"error": f"chemicals library unavailable: {e}"}
    try:
        cas = CAS_from_any(str(name))
    except Exception:
        return {"found": False, "note": f"'{name}' not recognised as a chemical name or CAS"}
    def _safe(fn):
        try:
            return fn(cas)
        except Exception:
            return None
    return {"found": True, "query": name, "CAS": cas,
            "molecular_weight_g_mol": _safe(MW), "boiling_point_K": _safe(Tb),
            "critical_temperature_K": _safe(Tc), "critical_pressure_Pa": _safe(Pc),
            "source": "chemicals database (Caleb Bell), compiled from DIPPR/NIST/Yaws"}


@tool("preflight",
      "BEFORE running a task, report what it will cost and which tools it will touch: the exact "
      "number of model calls, the risk class of each tool (read_only / reversible_write / "
      "irreversible), and whether any step needs human approval. Most EngineAI work is "
      "deterministic local computation and costs ZERO model calls, so this is a count, not a "
      "guess. Use it when the user asks what something will cost or whether it is safe to run.",
      {"goal": "the task the user is considering"})
def t_preflight(goal):
    import task_ledger
    return task_ledger.preflight(goal, TOOLS)


@tool("pipe_spec",
      "Real dimensions of a STANDARD pipe (ASME B36.10M): outside diameter, wall, true bore, flow "
      "area and mass. Accepts NPS ('2', '1-1/2'), DN (50) or a bare number. IMPORTANT: nominal "
      "pipe size is a label, not a diameter - NPS 2\" has a 52.5 mm bore, not 50.8 mm - so use "
      "this rather than assuming the nominal number is the bore.",
      {"size": "NPS or DN, e.g. '2' or 'DN50'", "schedule": "40 or 80"})
def t_pipe_spec(size="2", schedule=40):
    import pipe_cable
    try:
        return pipe_cable.pipe(size, schedule)
    except KeyError as e:
        return {"error": str(e)}


@tool("size_pipe",
      "Choose the SMALLEST standard pipe that keeps velocity at or below a design limit for a "
      "given volumetric flow (default 3 m/s, a common upper bound for pumped water). Returns the "
      "pipe and its actual velocity, or a clear note if no catalogued size fits.",
      {"flow_m3_per_s": "volumetric flow in m^3/s", "max_velocity_m_per_s": "default 3.0",
       "schedule": "40 or 80"})
def t_size_pipe(flow_m3_per_s, max_velocity_m_per_s=3.0, schedule=40):
    import pipe_cable
    r = pipe_cable.select_pipe(float(flow_m3_per_s), float(max_velocity_m_per_s), int(schedule))
    if r is None:
        return {"found": False,
                "note": f"no catalogued pipe keeps {flow_m3_per_s} m^3/s below "
                        f"{max_velocity_m_per_s} m/s - a larger size or parallel runs are needed"}
    return {"found": True, "pipe": r}


@tool("pipe_pressure_drop",
      "Pressure drop for a real flow through a STANDARD pipe: uses the catalogue bore, real fluid "
      "properties from CoolProp, and Darcy-Weisbach with a Colebrook friction factor. Returns "
      "velocity, Reynolds number, flow regime, pressure drop and head loss. Straight pipe only - "
      "fittings, valves and elevation are excluded.",
      {"size": "NPS or DN", "schedule": "40 or 80", "flow_m3_per_s": "m^3/s",
       "length_m": "straight run in metres", "fluid": "e.g. Water, Air",
       "T_K": "temperature K", "roughness_mm": "absolute roughness, default 0.045 (steel)"})
def t_pipe_pressure_drop(size="2", schedule=40, flow_m3_per_s=0.005, length_m=50.0,
                         fluid="Water", T_K=293.15, roughness_mm=0.045):
    import pipe_cable
    try:
        return pipe_cable.pipe_pressure_drop(size, int(schedule), float(flow_m3_per_s),
                                             float(length_m), fluid, float(T_K),
                                             roughness_mm=float(roughness_mm))
    except KeyError as e:
        return {"error": str(e)}


@tool("conductor_spec",
      "AWG conductor properties, DERIVED from the AWG geometric definition rather than a table: "
      "diameter, cross-sectional area and resistance per km for copper or aluminium. Use negative "
      "gauges for the large sizes (1/0 = 0, 2/0 = -1, 3/0 = -2, 4/0 = -3).",
      {"gauge": "AWG number", "material": "copper or aluminium"})
def t_conductor_spec(gauge=12, material="copper"):
    import pipe_cable
    try:
        return pipe_cable.awg(float(gauge), material)
    except KeyError as e:
        return {"error": str(e)}


@tool("size_cable",
      "Choose the smallest AWG conductor whose VOLTAGE DROP stays within a limit (default 3%) for "
      "a given current, run length and supply voltage. Sizes for volt drop ONLY - it does not "
      "check ampacity, which depends on insulation, grouping, ambient temperature and installation "
      "method, so the result must be checked against the governing wiring regulation.",
      {"current_A": "amperes", "length_m": "one-way run length in metres",
       "max_drop_percent": "default 3.0", "material": "copper or aluminium",
       "phase": "single or three", "V_supply": "supply voltage, default 230"})
def t_size_cable(current_A, length_m, max_drop_percent=3.0, material="copper",
                 phase="single", V_supply=230.0):
    import pipe_cable
    r = pipe_cable.select_conductor(float(current_A), float(length_m), float(max_drop_percent),
                                    material, phase, float(V_supply))
    if r is None:
        return {"found": False,
                "note": "even the largest catalogued conductor exceeds the volt-drop limit - "
                        "shorten the run, raise the voltage, or use parallel conductors"}
    return {"found": True, "conductor": r}


# ================================================================== loop
SYSTEM = """You are EngineAI, an offline-capable engineering agent owned by Fuad Ashraf.

You answer by CALLING TOOLS, never by recalling numbers from memory. Your own
knowledge of formulas is not trusted - the reference table is.

Reply with ONE JSON object and nothing else:
  {"thought": "one short sentence", "tool": "<tool name>", "args": { ... }}

Rules:
 - Always lookup_formula before stating any formula.
 - Always check_units on user-supplied numbers before compute.
 - Use compute for the number. Never do arithmetic yourself.
 - If a question has no closed form, use search_library; if that returns nothing,
   first call derive_verified, which generates and independently verifies a solver in an isolated sandbox; only if it returns verified=false do you say it could not be verified.
 - NEVER invent a value. If E, I, a section or a material is not stated, say what is
   missing instead of assuming. Values you supply that were not in the question are
   reported to the user as ASSUMPTIONS.
 - If lookup_formula returns found=false, do not guess a different formula. Say it is
   outside the verified set.
 - NEVER write a book name and page number unless search_library actually returned it
   in this conversation. A citation you invent will be stripped and flagged.
 - If the question is not engineering, call final_answer immediately and say so. Do not
   search the library for history, geography, arithmetic or general knowledge.
 - Never call the same tool twice with the same arguments.
 - Call final_answer exactly once, at the end, quoting the value and its source.

Available tools:
%TOOLS%

Examples of correct replies - output EXACTLY this shape, nothing else:
{"thought":"find the cited formula","tool":"lookup_formula","args":{"question":"cantilever tip deflection point load"}}
{"thought":"convert the user's units","tool":"check_units","args":{"values":{"L":"1200mm","P":"2.5kN"}}}
{"thought":"evaluate","tool":"compute","args":{"key":"cantilever_point_tip","values":{"P":2500,"L":1.2,"E":200000000000,"I":8.333e-06}}}
{"thought":"report","tool":"final_answer","args":{"answer":"0.864 mm","evidence":"Roark Table 8.1 case 1a"}}

No prose. No markdown. One JSON object.
"""

def context_note():
    if not CONTEXT.get("question"): return ""
    bits = [f'The previous question was: "{CONTEXT["question"]}"']
    if CONTEXT.get("values"):
        bits.append("with " + ", ".join(f"{k}={v:g}" for k, v in sorted(CONTEXT["values"].items())))
    if CONTEXT.get("last_value"):
        bits.append(f'and the answer was {CONTEXT["last_value"]}')
    if CONTEXT.get("last_geometry"):
        bits.append(f'The last geometry produced was {os.path.basename(CONTEXT["last_geometry"])}')
    return ("\n\nCONTEXT FROM THE PREVIOUS QUESTION (use it when the user says "
            '"it", "that", "the same"):\n  ' + " ".join(bits) + "\n")

def tool_manifest():
    return "\n".join(f'  {n}: {f.desc}\n    args: {json.dumps(f.params)}'
                     for n, f in TOOLS.items())

def extract_json(text):
    """Small models wrap JSON in prose and code fences. Dig it out."""
    if not text: return None
    t = re.sub(r"```(?:json)?", "", text).strip()
    start = t.find("{")
    while start != -1:
        depth, instr, esc = 0, False, False
        for i in range(start, len(t)):
            c = t[i]
            if esc: esc = False; continue
            if c == "\\": esc = True; continue
            if c == '"': instr = not instr; continue
            if instr: continue
            if c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try: return json.loads(t[start:i+1])
                    except json.JSONDecodeError: break
        start = t.find("{", start+1)
    return None

INTENTS = [
    (r"(deflect|deflection|sag)\w*.*(cantilever|beam)|cantilever.*(deflect|sag)",
     "cantilever_point_tip"),
    (r"(buckl|critical load|euler)", "euler_pinned"),
    (r"(bending|flexur)\w*.*stress|stress.*(bending|flexur)", "flexure"),
    (r"(torsion|twist)\w*.*(stress|shear)|shaft.*(stress|shear|torque)", "torsion_shear"),
    (r"(hoop|circumferential)|pressure vessel|thin.?wall", "hoop"),
    (r"conduct\w*.*wall|plane wall|through.the.wall|heat rate.*wall", "conduction_wall"),
    (r"(elongat|extens|stretch)\w*.*(bar|rod)|axial.*(deflect|extens)", "axial"),
    (r"(natural frequency|resonan)", "cantilever_freq"),
]

NUM = r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*"

# lowercasing the text destroys unit case, and pint is case-sensitive:
# "gpa" is not GPa, "kn" is not kN. Map the token to its canonical spelling.
CANON = {"mm": "mm", "cm": "cm", "m": "m", "n": "N", "kn": "kN", "mn": "MN",
         "pa": "Pa", "kpa": "kPa", "mpa": "MPa", "gpa": "GPa", "bar": "bar",
         "nm": "N*m", "knm": "kN*m"}

def parse_quantities(text):
    """Pull numbers with units out of plain language: '3 m', '2.5 kN', '200 GPa'."""
    try: from units import parse_value
    except Exception: return {}
    got, t = {}, text.lower()
    def grab(pat):
        m = re.search(pat, t)
        if not m: return None
        unit = CANON.get(m.group(2))
        if not unit: return None
        try: return parse_value(f"{m.group(1)}{unit}")[0]
        except Exception: return None
    # alternation must be longest-first or "kn" never matches (n wins and fails)
    for sym, pat in (("P", NUM + r"(knm|kn|mn|nm|n)\b"),
                     ("E", NUM + r"(gpa|mpa|kpa|pa)\b"),
                     ("L", NUM + r"(mm|cm|m)\b")):
        v = grab(pat)
        if v is not None: got[sym] = v
    for word, sym in (("moment", "M"), ("torque", "T"), ("pressure", "p")):
        m = re.search(word + r"[^0-9]{0,12}" + NUM + r"(knm|kn|mn|mpa|kpa|gpa|pa|nm|n|bar)\b", t)
        if m and CANON.get(m.group(2)):
            try: got[sym] = parse_value(f"{m.group(1)}{CANON[m.group(2)]}")[0]
            except Exception: pass
    if "steel" in t: got.setdefault("E", 200e9)
    if "aluminium" in t or "aluminum" in t: got.setdefault("E", 70e9)
    m = re.search(NUM + r"(?:x|by|\*)\s*" + NUM + r"(mm|cm|m)\b", t)   # "50 x 100 mm"
    if m and CANON.get(m.group(3)):
        try:
            u = CANON[m.group(3)]
            b = parse_value(f"{m.group(1)}{u}")[0]; h = parse_value(f"{m.group(2)}{u}")[0]
            got["I"] = b*h**3/12; got["A"] = b*h; got["c"] = h/2
            got["J"] = b*h*(b*b + h*h)/12
        except Exception: pass
    return got

def fallback(goal):
    """Deterministic routing when the model will not produce a tool call.
    A weak model should degrade the experience, not break the product."""
    key = next((k for pat, k in INTENTS if re.search(pat, goal.lower())), None)
    if not key: return None
    vals = parse_quantities(goal)
    from engineai import REFERENCE
    ref = next(r for r in REFERENCE if r["key"] == key)
    need = ref["sym"].split()
    missing = [n for n in need if n not in vals]
    if missing:
        eg = {"I": "a section, e.g. '50 x 100 mm section'", "E": "a material, e.g. 'steel'",
              "P": "a load, e.g. '2.5 kN'", "L": "a length, e.g. '3 m'",
              "p": "a pressure, e.g. '2 MPa'", "r": "a radius, e.g. '300 mm'",
              "t": "a wall thickness, e.g. '6 mm'"}
        hints = "; ".join(eg.get(m, m) for m in missing)
        return {"ok": False, "goal": goal, "backend": "rule-based fallback", "steps": [],
                "answer": None,
                "error": (f"This is {key.replace('_',' ')}: {ref['expr']} ({ref['src']}). "
                          f"I still need {', '.join(missing)} — add {hints}")}
    r = TOOLS["compute"](key=key, values=vals)
    steps = [{"step": 1, "tool": "lookup_formula", "args": {"question": goal},
              "observation": {"found": True, "candidates": [
                  {"key": key, "formula": ref["expr"], "unit": ref["unit"], "source": ref["src"]}]},
              "thought": "rule-based intent match"},
             {"step": 2, "tool": "compute", "args": {"key": key, "values": vals},
              "observation": r, "thought": "deterministic"}]
    return {"ok": True, "goal": goal, "backend": "rule-based fallback", "steps": steps,
            "answer": {"answer": f"{r['value']:.6g} {r['unit']}",
                       "evidence": f"{ref['expr']} — {ref['src']} (routed without the model)"}}

class RunGuard:
    """Three failure modes seen in real use, all handled here so both the CLI loop
    and the studio stream behave identically:

      1. the model calls the same tool with the same arguments forever
      2. the model writes a book-and-page citation that no search actually returned
      3. the model answers an out-of-scope question as if it were verified
    """
    ARTIFACT_EXT = (".dxf", ".svg", ".step", ".stp", ".stl", ".png", ".pdf", ".docx",
                    ".xlsx", ".pptx", ".csv", ".html", ".json", ".md", ".inp")

    def __init__(self, goal):
        self.goal = goal
        self.seen = {}            # (tool, args) -> times called
        self.sources = set()      # book titles that a search really returned
        self.verified = False     # a compute or a real library hit happened
        self.assumed = {}
        self.claimed_files = set()   # every path any tool SAID it produced

    def _scan_artifacts(self, obs):
        """Collect every file path a tool claims to have written - whether or not it
        exists. Existence is checked later, at the completion gate; recording the
        claim is what makes a missing deliverable detectable instead of invisible."""
        def walk(v):
            if isinstance(v, str):
                if v.lower().endswith(self.ARTIFACT_EXT) and os.sep in v:
                    self.claimed_files.add(v)
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, (list, tuple)):
                for x in v:
                    walk(x)
        walk(obs)

    def check_repeat(self, name, args):
        k = (name, json.dumps(args, sort_keys=True, default=str))
        self.seen[k] = self.seen.get(k, 0) + 1
        if self.seen[k] > 1:
            return {"error": (f"You already called {name} with these exact arguments and got "
                              f"the same result. Repeating it will not help. Either try "
                              f"different arguments, or call final_answer and say plainly "
                              f"what you could not determine.")}
        return None

    def note(self, name, obs):
        if not isinstance(obs, dict): return
        self._scan_artifacts(obs)
        if name == "search_library":
            for h in obs.get("hits", []):
                self.sources.add(h["book"][:40].lower())
            if obs.get("hits"): self.verified = True
        if name == "compute" and "value" in obs:
            self.verified = True
        if name in ("run_generator", "visualise", "make_beam_cad", "make_cad"):
            # a tool that wrote a real file on disk is evidence, not model recall
            for v in list(obs.values()) + (list(obs.get("result", {}).values())
                                           if isinstance(obs.get("result"), dict) else []):
                for x in (v if isinstance(v, list) else [v]):
                    if isinstance(x, str) and os.path.exists(x):
                        self.verified = True
                        self.sources.add("generated file: " + os.path.basename(x))
            if obs.get("ASSUMED"): self.assumed.update(obs["ASSUMED"])
        if name == "lookup_formula" and obs.get("found"):
            for c in obs.get("candidates", []): self.sources.add(c["source"][:40].lower())

    def vet_answer(self, obs):
        """Strip a citation the run never earned; mark unverified answers as such."""
        obs = dict(obs)
        ev = str(obs.get("evidence", ""))
        # does the evidence name a book/page that no tool actually returned?
        claimed = re.findall(r"([A-Z][A-Za-z.,'&\- ]{8,40}?)\s*,?\s*(?:p\.?|page)\s*\d+", ev)
        bogus = [c for c in claimed
                 if not any(c[:18].lower() in src for src in self.sources)]
        if bogus:
            obs["evidence"] = ("⚠ CITATION REMOVED — the answer named "
                               + "; ".join(b.strip() for b in bogus)
                               + " but no search returned that passage. Treat as unverified.")
            obs["fabricated_citation"] = True
        elif not self.verified:
            obs["evidence"] = ((ev + "  ") if ev else "") + \
                "⚠ UNVERIFIED — answered from the model's own knowledge, not from a tool."
        if self.assumed:
            obs["evidence"] = obs.get("evidence", "") + \
                "  ⚠ assumed " + ", ".join(f"{k}={v:g}" for k, v in sorted(self.assumed.items())) + \
                ", which you did not state."
        # THE COMPLETION GATE. If any tool claimed to write a file, that file must
        # actually be there. "I produced the drawing" is a checkable statement, and
        # an agent reporting success over a missing deliverable is the single most
        # damaging failure mode an agent has - so it is checked, not trusted.
        if self.claimed_files:
            import task_ledger
            v = task_ledger.verify_completion(claimed_files=sorted(self.claimed_files),
                                              require_artifact=False)
            obs["deliverables"] = sorted(self.claimed_files)
            obs["deliverables_verified"] = v["complete"]
            if not v["complete"]:
                obs["evidence"] = ("⚠ DELIVERABLE MISSING — " + v["reason"] +
                                   ". The answer claims files that are not on disk; "
                                   "treat this task as INCOMPLETE.  ") + str(obs.get("evidence", ""))
                obs["failed_verification"] = True
        return obs

def run(goal, backend=None, max_steps=8, verbose=True, log=None):
    backend = backend or pick_backend()
    if backend is None:
        return {"ok": False, "error": why_no_backend()}
    system = SYSTEM.replace("%TOOLS%", tool_manifest()) + context_note()
    USER_GIVEN.clear(); USER_GIVEN.update(parse_quantities(goal))
    if not USER_GIVEN and CONTEXT.get("values"):
        USER_GIVEN.update(CONTEXT["values"])        # a follow-up inherits the last numbers
    guard = RunGuard(goal)
    if USER_GIVEN: CONTEXT["values"] = dict(USER_GIVEN)
    CONTEXT["question"] = goal
    msgs = [{"role": "user", "content": goal}]
    steps, answer, bad = [], None, 0
    for n in range(1, max_steps+1):
        raw = backend.complete(system, msgs)
        call = extract_json(raw)
        if not call or "tool" not in call:
            bad += 1
            msgs.append({"role": "user", "content":
                         'INVALID. Output only this, with no other text:\n'
                         '{"thought":"...","tool":"lookup_formula","args":{"question":"..."}}'})
            steps.append({"step": n, "error": "unparseable", "raw": (raw or "")[:200]})
            if verbose: print(f"  [{n}] reply was not a tool call ({bad}/2), re-prompting")
            if bad >= 2:
                fb = fallback(goal)
                if fb:
                    if verbose: print("       model unusable - routing deterministically instead")
                    return fb
                return {"ok": False, "goal": goal, "backend": backend.name, "steps": steps,
                        "answer": None,
                        "error": "the model would not produce a tool call and no rule matched"}
            continue
        name, args = call.get("tool"), call.get("args") or {}
        if verbose: print(f"  [{n}] {name}({', '.join(f'{k}={v}' for k, v in list(args.items())[:3])})"
                          f"   {call.get('thought','')[:60]}")
        rep = guard.check_repeat(name, args) if name != "final_answer" else None
        if rep:
            obs = rep
        elif name not in TOOLS:
            obs = {"error": f"no such tool '{name}'. Choose from: {', '.join(TOOLS)}"}
        else:
            try: obs = TOOLS[name](**args)
            except TypeError as e: obs = {"error": f"bad arguments: {e}"}
            except Exception as e: obs = {"error": f"{type(e).__name__}: {e}"}
        guard.note(name, obs)
        steps.append({"step": n, "tool": name, "args": args, "observation": obs,
                      "thought": call.get("thought", "")})
        if verbose and isinstance(obs, dict):
            k = next((x for x in ("value", "verdict", "found", "error", "answer", "view") if x in obs), None)
            if k: print(f"       -> {k}: {str(obs[k])[:80]}")
        if name == "final_answer":
            answer = guard.vet_answer(obs); break
        msgs.append({"role": "assistant", "content": json.dumps(call)})
        msgs.append({"role": "user", "content": "OBSERVATION: " + json.dumps(obs, default=str)[:1800]})
    rec = {"ok": answer is not None, "goal": goal, "backend": backend.name,
           "steps": steps, "answer": answer,
           "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    log = log or os.path.join(OUT, "agent_transcripts.jsonl")
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a") as f: f.write(json.dumps(rec, default=str) + "\n")
    except Exception: pass
    return rec

# ============================================================== selftest
def selftest():
    ok = True
    print("\nAGENT LOOP SELFTEST")
    # 1. the JSON extractor must survive how small models actually reply
    cases = [('{"thought":"a","tool":"list_generators","args":{}}', "list_generators"),
             ('Sure!\n```json\n{"thought":"b","tool":"lookup_formula","args":{"question":"beam"}}\n```',
              "lookup_formula"),
             ('I will now call: {"thought":"c","tool":"compute","args":{"key":"x","values":{"a":1}}} done',
              "compute"),
             ('no json here', None)]
    for raw, want in cases:
        got = extract_json(raw)
        g = got.get("tool") if got else None
        print(f"  {'ok  ' if g == want else 'FAIL'} extract {str(want):18s} from {raw[:40]!r}")
        ok &= (g == want)
    # 2. tools work standalone
    r = TOOLS["lookup_formula"](question="cantilever tip deflection point load")
    good = r.get("found") and r["candidates"][0]["key"] == "cantilever_point_tip"
    print(f"  {'ok  ' if good else 'FAIL'} lookup_formula -> {r.get('candidates',[{}])[0].get('formula')}")
    ok &= good
    r = TOOLS["compute"](key="cantilever_point_tip",
                         values={"P": 1000, "L": 1.0, "E": 200e9, "I": 8.333e-6})
    good = abs(r["value"] - 2.00008e-4)/2.00008e-4 < 1e-6
    print(f"  {'ok  ' if good else 'FAIL'} compute -> {r['value']:.6e} m")
    ok &= good
    r = TOOLS["check_units"](values={"L": "1200mm", "P": "2.5kN"})
    good = abs(r["si_values"]["L"] - 1.2) < 1e-9 and abs(r["si_values"]["P"] - 2500) < 1e-9
    print(f"  {'ok  ' if good else 'FAIL'} check_units -> {r['si_values']}")
    ok &= good
    r = TOOLS["verify_formula"](claim="P*L**2/(E*I)", key="cantilever_point_tip")
    good = r["verdict"] == "BLOCK"
    print(f"  {'ok  ' if good else 'FAIL'} verify_formula blocks the wrong one -> {r['verdict']}")
    ok &= good
    # 3. the LOOP: a scripted model must chain tools and reach an answer
    script = [
      '{"thought":"find the formula","tool":"lookup_formula","args":{"question":"cantilever tip deflection point load free end"}}',
      '{"thought":"convert units","tool":"check_units","args":{"values":{"L":"1200mm","P":"2.5kN"}}}',
      '{"thought":"compute it","tool":"compute","args":{"key":"cantilever_point_tip","values":{"P":2500,"L":1.2,"E":200000000000,"I":0.000008333}}}',
      'oops not json',
      '{"thought":"answer","tool":"final_answer","args":{"answer":"2.16 mm","evidence":"Roark Table 8.1 case 1a, computed"}}']
    rec = run("deflection of a 1.2 m cantilever under 2.5 kN",
              backend=ScriptedBackend(script), verbose=False, log="/tmp/_agent_test.jsonl")
    used = [s.get("tool") for s in rec["steps"]]
    good = rec["ok"] and used[:3] == ["lookup_formula", "check_units", "compute"] and "final_answer" in used
    print(f"  {'ok  ' if good else 'FAIL'} loop chained {len([u for u in used if u])} tools: {used}")
    ok &= good
    recovered = any(s.get("error") == "unparseable" for s in rec["steps"]) and rec["ok"]
    print(f"  {'ok  ' if recovered else 'FAIL'} loop recovered from a malformed reply and still finished")
    ok &= recovered
    val = next(s["observation"]["value"] for s in rec["steps"] if s.get("tool") == "compute")
    exact = 2500*1.2**3/(3*200e9*8.333e-6)
    good = abs(val - exact)/exact < 1e-6
    print(f"  {'ok  ' if good else 'FAIL'} chained answer {val*1000:.4f} mm matches closed form {exact*1000:.4f} mm")
    ok &= good
    # 4. transcript
    good = os.path.exists("/tmp/_agent_test.jsonl") and \
           json.loads(open("/tmp/_agent_test.jsonl").readline())["goal"].startswith("deflection")
    print(f"  {'ok  ' if good else 'FAIL'} transcript written and replayable")
    ok &= good
    # 5. the completion gate: an agent that CLAIMS a deliverable it never wrote must
    #    not be allowed to report success. This is the failure mode that independent
    #    reviews of general agent platforms document as "hallucinated success reports".
    g = RunGuard("make a drawing")
    g.note("run_generator", {"result": {"dxf": "/tmp/definitely_not_written_12345.dxf"}})
    vetted = g.vet_answer({"answer": "Drawing complete", "evidence": "wrote it"})
    good = vetted.get("failed_verification") is True and "DELIVERABLE MISSING" in vetted["evidence"]
    print(f"  {'ok  ' if good else 'FAIL'} claimed-but-missing deliverable is caught, not reported as success")
    ok &= good
    g2 = RunGuard("make a drawing")
    realf = "/tmp/_agent_real_artifact.dxf"
    open(realf, "w").write("0\nSECTION\n")
    g2.note("run_generator", {"result": {"dxf": realf}})
    v2 = g2.vet_answer({"answer": "done", "evidence": "wrote it"})
    good = v2.get("deliverables_verified") is True and not v2.get("failed_verification")
    print(f"  {'ok  ' if good else 'FAIL'} a real deliverable passes the same gate")
    ok &= good
    os.path.exists(realf) and os.remove(realf)
    # 6. preflight must be a count, not a guess
    pf = TOOLS["preflight"](goal="run a beam_design on a steel bar")
    good = pf["deterministic_local_only"] and pf["model_calls_for_tools"] == 0
    print(f"  {'ok  ' if good else 'FAIL'} preflight reports local-only work as ZERO model calls")
    ok &= good
    os.path.exists("/tmp/_agent_test.jsonl") and os.remove("/tmp/_agent_test.jsonl")
    b = pick_backend()
    print(f"  backend available now: {b.name if b else 'none - pull a model or set an API key'}")
    print("\nagent loop selftest:", "PASSED" if ok else "FAILED")
    return ok

def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("goal", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--backend", choices=["local", "api"], default="local")
    a = ap.parse_args()
    if a.selftest: sys.exit(0 if selftest() else 1)
    if a.list_tools:
        print("\n" + tool_manifest() + "\n"); return
    if not a.goal: sys.exit('give a goal, e.g. agent_loop.py "deflection of a steel cantilever"')
    rec = run(" ".join(a.goal), pick_backend("api" if a.backend == "api" else None), a.steps)
    print()
    if rec.get("answer"):
        print("  ANSWER:  ", rec["answer"].get("answer"))
        print("  EVIDENCE:", rec["answer"].get("evidence"))
    else:
        print("  no final answer:", rec.get("error", "ran out of steps"))

if __name__ == "__main__":
    main()
