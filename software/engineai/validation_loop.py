#!/usr/bin/env python3
"""validation_loop.py - iterate until it converges, or until it is time to stop.

THE QUESTION THIS MODULE ANSWERS. Should the engine keep experimenting and
re-simulating until everything matches?

Not until everything MATCHES - until everything CONVERGES, which is a different
target, and the difference is the whole of scientific credibility.

  ITERATING TO CONVERGENCE is standard practice and this module does it.
  Refine the mesh, shrink the timestep, tighten the solver tolerance, add
  specimens, until the answer stops changing. You are removing NUMERICAL error
  from your own calculation. Nothing about the physics is being adjusted, so
  nothing is being talked into agreement.

  ITERATING UNTIL IT MATCHES is the failure mode, and it is how competent
  people produce false results. If the loop is allowed to change the MODEL
  until the model agrees with the DATA, then agreement is guaranteed and means
  nothing - you have fitted, not tested. ASME V&V 10 and V&V 20 draw this line
  explicitly: data used to CALIBRATE a model can never afterwards VALIDATE it.

So the loop here has three exits and only one of them is success:

  CONVERGED       numerical error fell below tolerance AND the result then
                  agreed with held-out data it was never tuned against
  BUDGET_SPENT    ran out of refinement steps while still moving - honest
                  incompleteness, reported as such
  IRRECONCILABLE  converged cleanly and STILL disagrees with the data. This is
                  not a failure of the loop. It is the most valuable result the
                  loop can produce, because it means the model is wrong about
                  the physics and no amount of further refinement will fix it.

A loop that cannot exit IRRECONCILABLE is not a validation loop, it is a
persuasion loop. This one can, and the selftest proves it does.

FIREWALL. Calibration data and validation data are separated at construction
and the loop physically cannot see the validation set while it is tuning. That
is enforced in code, not by discipline, because discipline is exactly what
fails at two in the morning near a deadline.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from research_credibility import validate_vv20

__all__ = ["Iteration", "LoopResult", "run_loop", "DataFirewall"]


class DataFirewall:
    """Holds validation data out of reach until tuning is finished.

    The split is made once, from a fixed seed, before any model is fitted.
    calibration() may be called freely; validation() raises until release() is
    called, and release() records that it happened so the audit trail shows
    when the model stopped being adjustable.
    """

    def __init__(self, data: Sequence[float], calib_frac: float = 0.5,
                 seed: int = 20260811):
        arr = np.asarray(list(data), dtype=float)
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(arr))
        cut = int(calib_frac * len(arr))
        self._calib = arr[idx[:cut]]
        self._valid = arr[idx[cut:]]
        self._released = False
        self.released_at: str | None = None

    def calibration(self) -> np.ndarray:
        return self._calib.copy()

    def release(self) -> None:
        self._released = True
        self.released_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    def validation(self) -> np.ndarray:
        if not self._released:
            raise PermissionError(
                "validation data is sealed until release(). Tuning a model "
                "against it and then validating on it is not validation.")
        return self._valid.copy()

    @property
    def sizes(self) -> tuple:
        return len(self._calib), len(self._valid)


@dataclass
class Iteration:
    n: int
    effort: float
    value: float
    drift: float
    elapsed_s: float

    def __str__(self) -> str:
        return (f"    pass {self.n:>2}  effort {self.effort:>10.4g}  "
                f"value {self.value:.8g}  drift {self.drift:.2e}")


@dataclass
class LoopResult:
    outcome: str
    value: float
    iterations: list = field(default_factory=list)
    numerical_converged: bool = False
    observed_order: float | None = None
    vv20: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    @property
    def n_passes(self) -> int:
        return len(self.iterations)

    def __str__(self) -> str:
        head = f"  [{self.outcome}] after {self.n_passes} passes -> {self.value:.8g}"
        body = "\n".join(str(i) for i in self.iterations)
        vv = ""
        if self.vv20:
            vv = (f"\n    V&V 20: E = {self.vv20['E']:.4g}, "
                  f"U_val = {self.vv20['U_val']:.4g} -> {self.vv20['verdict']}")
        notes = "".join(f"\n    note: {n}" for n in self.notes)
        return f"{head}\n{body}{vv}{notes}"


def run_loop(simulate: Callable[[float], float], efforts: Sequence[float],
             firewall: DataFirewall | None = None,
             tol: float = 1e-3, u_input: float = 0.0,
             max_seconds: float = 300.0, verbose: bool = False) -> LoopResult:
    """Refine until the computation stops moving, then test it once.

    `simulate(effort)` runs the model at a given refinement level - mesh count,
    timestep, iteration cap, whatever the effort axis is for this problem - and
    returns the quantity of interest.

    The order is fixed and matters. Refinement happens FIRST and alone, with no
    sight of the validation data; only when the numerical answer has stopped
    changing is the firewall released and the comparison made, ONCE. Comparing
    at every step and stopping when it happens to agree would select the
    refinement level that best flatters the model, which is the same error as
    stopping an experiment the moment it reads well.
    """
    t0 = time.time()
    hist: list[Iteration] = []
    res = LoopResult(outcome="BUDGET_SPENT", value=float("nan"))

    prev = None
    for n, eff in enumerate(efforts, start=1):
        if time.time() - t0 > max_seconds:
            res.notes.append(f"stopped on the {max_seconds:g} s wall clock")
            break
        try:
            v = float(simulate(eff))
        except Exception as e:
            res.notes.append(f"pass {n} failed: {type(e).__name__}: {e}")
            continue
        if not np.isfinite(v):
            res.notes.append(f"pass {n} returned a non-finite value")
            continue
        drift = abs(v - prev) / (abs(v) or 1.0) if prev is not None else float("inf")
        it = Iteration(n, float(eff), v, drift, time.time() - t0)
        hist.append(it)
        if verbose:
            print(it)
        prev = v
        if drift <= tol:
            res.numerical_converged = True
            break

    res.iterations = hist
    if not hist:
        res.outcome = "BUDGET_SPENT"
        res.notes.append("no pass produced a usable value")
        return res
    res.value = hist[-1].value
    res.observed_order = _order(hist)

    if not res.numerical_converged:
        res.outcome = "BUDGET_SPENT"
        res.notes.append(
            f"still drifting at {hist[-1].drift:.2e} after {len(hist)} passes - "
            "the number is NOT converged and must not be quoted as if it were")
        return res

    if firewall is None:
        res.outcome = "CONVERGED"
        res.notes.append("numerically converged; no measured data supplied, so "
                         "this is a converged PREDICTION and nothing more")
        return res

    # One comparison, after refinement is finished and only then.
    firewall.release()
    D = firewall.validation()
    u_data = float(np.std(D, ddof=1) / np.sqrt(len(D))) if len(D) > 1 else 0.0
    u_num = abs(hist[-1].value - hist[-2].value) if len(hist) > 1 else 0.0
    res.vv20 = validate_vv20(S=res.value, D=float(np.mean(D)),
                             u_num=u_num, u_input=u_input, u_data=u_data)

    if res.vv20["validated"]:
        res.outcome = "CONVERGED"
        res.notes.append(
            f"agrees with {len(D)} held-out measurements that were sealed "
            f"throughout refinement (released {firewall.released_at})")
    else:
        res.outcome = "IRRECONCILABLE"
        res.notes.append(
            "the calculation converged cleanly and STILL disagrees with the "
            "measurements. Further refinement cannot fix this - the discrepancy "
            "is physical, not numerical, and the model is wrong about something.")
        res.notes.append(
            "DO NOT loop again with adjusted model parameters and report the "
            "agreement that follows. Tuning against this data spends it: it can "
            "calibrate the model or validate it, never both.")
    return res


def _order(hist: list) -> float | None:
    """Observed order of convergence from the last three passes."""
    if len(hist) < 3:
        return None
    f1, f2, f3 = hist[-3].value, hist[-2].value, hist[-1].value
    d1, d2 = f2 - f1, f3 - f2
    if abs(d1) < 1e-15 or abs(d2) < 1e-15 or d2 / d1 <= 0:
        return None
    r = hist[-1].effort / hist[-2].effort if hist[-2].effort else 2.0
    if r <= 1:
        return None
    try:
        return float(abs(np.log(abs(d1 / d2)) / np.log(r)))
    except Exception:
        return None


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------

def _selftest() -> int:
    ok = fail = 0

    def chk(c, label):
        nonlocal ok, fail
        if c:
            ok += 1
        else:
            fail += 1
            print(f"  FAIL {label}")

    rng = np.random.default_rng(3)

    print("== the firewall really is sealed ==")
    fw = DataFirewall(rng.normal(100, 2, 40))
    chk(fw.sizes == (20, 20), f"split 50/50 ({fw.sizes})")
    try:
        fw.validation()
        sealed = False
    except PermissionError:
        sealed = True
    chk(sealed, "validation data cannot be read before release")
    chk(len(fw.calibration()) == 20, "calibration data is available freely")
    fw.release()
    chk(len(fw.validation()) == 20 and fw.released_at, "release opens it and is timestamped")

    print("== converges numerically, and agrees: CONVERGED ==")
    # a second-order scheme approaching 100.0
    truth = 100.0
    def sim_good(eff):
        return truth + 400.0 / (eff ** 2)
    fw2 = DataFirewall(rng.normal(100.0, 1.0, 40), seed=1)
    r = run_loop(sim_good, [10, 20, 40, 80, 160, 320, 640], firewall=fw2, tol=1e-4)
    chk(r.numerical_converged, "the refinement converged")
    chk(r.outcome == "CONVERGED", f"and validates (got {r.outcome})")
    chk(r.observed_order is not None and 1.5 < r.observed_order < 2.5,
        f"observed order is about 2 (got {r.observed_order})")

    print("== converges numerically and STILL disagrees: IRRECONCILABLE ==")
    # the model converges beautifully - to the wrong answer
    def sim_wrong(eff):
        return 130.0 + 400.0 / (eff ** 2)
    fw3 = DataFirewall(rng.normal(100.0, 1.0, 40), seed=2)
    r2 = run_loop(sim_wrong, [10, 20, 40, 80, 160, 320], firewall=fw3, tol=1e-4)
    chk(r2.numerical_converged, "a wrong model can still converge cleanly")
    chk(r2.outcome == "IRRECONCILABLE",
        f"and the loop says so instead of iterating on (got {r2.outcome})")
    chk(any("physical, not numerical" in n for n in r2.notes),
        "and explains that more refinement will not help")
    chk(any("never both" in n for n in r2.notes),
        "and warns against tuning on the validation data")

    print("== never converges: BUDGET_SPENT, not a quoted number ==")
    def sim_wander(eff):
        return float(np.random.default_rng(int(eff)).normal(50, 10))
    r3 = run_loop(sim_wander, [10, 20, 40], tol=1e-6)
    chk(r3.outcome == "BUDGET_SPENT", f"reported as unfinished (got {r3.outcome})")
    chk(not r3.numerical_converged, "and explicitly not converged")
    chk(any("must not be quoted" in n for n in r3.notes),
        "and says the number must not be quoted")

    print("== no data: a converged PREDICTION is not a validated result ==")
    r4 = run_loop(sim_good, [10, 20, 40, 80, 160, 320, 640], tol=1e-4)
    chk(r4.outcome == "CONVERGED", "converges without data")
    chk(any("nothing more" in n for n in r4.notes),
        "but is labelled a prediction, not a validation")
    chk(not r4.vv20, "and carries no validation comparison")

    print("== the comparison happens ONCE, after refinement ==")
    seen = []
    fw5 = DataFirewall(rng.normal(100.0, 1.0, 40), seed=4)
    orig = fw5.validation
    def spy():
        seen.append(1)
        return orig()
    fw5.validation = spy
    run_loop(sim_good, [10, 20, 40, 80, 160, 320, 640], firewall=fw5, tol=1e-4)
    chk(len(seen) == 1,
        f"validation data touched exactly once, not once per pass (got {len(seen)})")

    print("== a crashing simulation does not silently vanish ==")
    def sim_crash(eff):
        if eff > 20:
            raise RuntimeError("solver diverged")
        return 100.0 + 1.0 / eff
    r6 = run_loop(sim_crash, [10, 20, 40, 80], tol=1e-9)
    chk(any("solver diverged" in n for n in r6.notes), "the crash is reported")
    chk(r6.outcome == "BUDGET_SPENT", "and the run is not called converged")

    print(f"\nvalidation_loop.py: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
