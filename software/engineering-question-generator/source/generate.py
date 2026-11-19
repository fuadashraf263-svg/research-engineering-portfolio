import json, csv, random, sys, hashlib
import core, templates
REG = core.REGISTRY

def build_record(idx, t, p, v, q):
    steps = core.build_steps(t, p, v)
    try:
        av = float(v); 
        if av != av or av in (float('inf'), float('-inf')): av = None
    except (TypeError, ValueError):
        av = None
    return {
        "id": f"EQ-{idx:06d}",
        "branch": t['branch'],
        "topic": t['topic'],
        "difficulty": t['difficulty'],
        "question": q,
        "answer": core.answer_str(t, v),
        "answer_value": av,
        "unit": (t['ans_unit'] or t['unit']) or None,
        "solution_steps": steps,
        "solution": "\n".join(steps),
        "formula": t['formula'],
        "tags": t['tags'],
        "template_id": t['tid'],
        "parameters": p,
    }

def generate(target, seed=12345, cap=2000, max_fail=15):
    rng = random.Random(seed)
    seen = set()
    records = []
    order = list(range(len(REG)))
    counts = {i: 0 for i in order}
    fails = {i: 0 for i in order}
    active = set(order)
    idx = 0
    while len(records) < target and active:
        for i in list(order):
            if i not in active:
                continue
            if counts[i] >= cap:
                active.discard(i); continue
            t = REG[i]
            inst = core.make_instance(t, rng)
            placed = False
            for _ in range(6):
                if inst is None:
                    break
                p, v, q = inst
                if q not in seen:
                    seen.add(q)
                    idx += 1
                    records.append(build_record(idx, t, p, v, q))
                    counts[i] += 1
                    fails[i] = 0
                    placed = True
                    break
                inst = core.make_instance(t, rng)
            if not placed:
                fails[i] += 1
                if fails[i] >= max_fail:
                    active.discard(i)
            if len(records) >= target:
                break
    return records

def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    tag = sys.argv[2] if len(sys.argv) > 2 else ""
    recs = generate(target)
    base = f"engineering_questions{tag}"
    # JSONL
    with open(base + ".jsonl", "w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # CSV (flatten list fields)
    cols = ["id","branch","topic","difficulty","question","answer","answer_value","unit","solution","formula","tags","template_id"]
    with open(base + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            row = dict(r)
            row["solution"] = " | ".join(r["solution_steps"])
            row["tags"] = ";".join(r["tags"])
            w.writerow(row)
    print(f"Wrote {len(recs)} records -> {base}.jsonl / {base}.csv")

if __name__ == "__main__":
    main()
