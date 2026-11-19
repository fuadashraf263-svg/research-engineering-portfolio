"""End-to-end verification of the shipped JSONL: independently re-derive every
record from its stored parameters, and re-run numeric cross-checks."""
import json, sys, math
import core, templates
REG = {t['tid']: t for t in core.REGISTRY}

def run(path):
    n=0; uniq=set(); bad=[]; integ_ok=0; check_ok=0; check_n=0
    fields=["id","branch","topic","difficulty","question","answer","solution_steps","formula","tags","template_id","parameters"]
    from collections import Counter
    br=Counter(); df=Counter(); tp=Counter(); tid=Counter()
    with open(path) as f:
        for line in f:
            r=json.loads(line); n+=1
            for k in fields:
                if k not in r: bad.append((r.get('id'),'missing:'+k)); break
            else:
                if not r['question'] or not r['answer'] or len(r['solution_steps'])<2:
                    bad.append((r['id'],'empty-field'))
                uniq.add(r['question'])
                br[r['branch']]+=1; df[r['difficulty']]+=1; tp[r['topic']]+=1; tid[r['template_id']]+=1
                t=REG.get(r['template_id'])
                if t is None:
                    bad.append((r['id'],'unknown-template')); continue
                # independent re-derivation from stored parameters
                try:
                    v=t['solve'](r['parameters'])
                    if core.answer_str(t,v)==r['answer']:
                        integ_ok+=1
                    else:
                        bad.append((r['id'],f"recompute {core.answer_str(t,v)} != {r['answer']}"))
                    if t['check']:
                        check_n+=1
                        if t['check'](r['parameters'],v): check_ok+=1
                        else: bad.append((r['id'],'check-fail'))
                except Exception as e:
                    bad.append((r['id'],'recompute-error:'+str(e)[:40]))
            if len(bad)>40: break
    print(f"Records: {n}")
    print(f"Unique questions: {len(uniq)}  (duplicates: {n-len(uniq)})")
    print(f"Integrity (recompute==stored answer): {integ_ok}/{n}")
    print(f"Independent numeric cross-checks: {check_ok}/{check_n} passed")
    print(f"Distinct branches: {len(br)} | topics: {len(tp)} | templates used: {len(tid)}")
    print("By branch:", dict(br.most_common()))
    print("By difficulty:", dict(df.most_common()))
    if bad:
        print("PROBLEMS:", bad[:20]); sys.exit(1)
    print("DATASET FULLY VERIFIED — no mismatches")

if __name__=="__main__":
    run(sys.argv[1] if len(sys.argv)>1 else "engineering_questions.jsonl")
