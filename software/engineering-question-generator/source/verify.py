"""Independent verification: regenerate instances and re-check the math."""
import random, sys, math
import core, templates
REG = core.REGISTRY

def run(per=12, seed=7):
    rng = random.Random(seed)
    fails = []
    checked = 0
    for t in REG:
        for _ in range(per):
            inst = core.make_instance(t, rng)
            if inst is None:
                fails.append((t['tid'], t['topic'], 'no-instance'))
                break
            p, v, q = inst
            steps = core.build_steps(t, p, v)
            # invariant: answer finite
            try:
                vf = float(v)
                if math.isnan(vf) or math.isinf(vf):
                    fails.append((t['tid'], t['topic'], 'non-finite')); break
            except (TypeError, ValueError):
                pass
            # invariant: question and steps non-empty
            if not q or not steps or len(steps) < 2:
                fails.append((t['tid'], t['topic'], 'bad-steps')); break
            # template-specific numeric cross-check
            if t['check']:
                try:
                    ok = t['check'](p, v)
                except Exception as e:
                    fails.append((t['tid'], t['topic'], 'check-error:'+str(e)[:40])); break
                if not ok:
                    fails.append((t['tid'], t['topic'], f'check-fail q="{q[:60]}" v={v}')); break
                checked += 1
    n_checkable = sum(1 for t in REG if t['check'])
    print(f"Templates: {len(REG)} | with numeric cross-check: {n_checkable}")
    print(f"Cross-checks passed: {checked}")
    if fails:
        print(f"FAILURES ({len(fails)}):")
        for f in fails[:60]:
            print("  ", f)
        sys.exit(1)
    print("ALL CHECKS PASSED")

if __name__ == "__main__":
    run()
