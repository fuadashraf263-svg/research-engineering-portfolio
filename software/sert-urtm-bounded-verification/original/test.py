import numpy as np,csv,json
from pathlib import Path
p=Path(__file__).parent
# 1D bar length 1, E=A=1, u=x, strain=1, density 0.5, fixed physical window [0.35,0.65]
rows=[]
for n in (10,20,40,80,160):
 h=1/n; centers=(np.arange(n)+.5)*h; density=np.full(n,.5); total=(density*h).sum()
 # naive sum of element energy, mesh-dependent; physical integral with fractional cell overlap
 overlap=np.maximum(0,np.minimum((np.arange(n)+1)*h,.65)-np.maximum(np.arange(n)*h,.35))
 window=(density*overlap).sum()
 rows.append(dict(n=n,h=h,total=total,physical_window=window,naive_sum=(density[(centers>=.35)&(centers<=.65)]).sum(),fraction=window/total))
# parallel truss elements: each k=1, thresholds .2,.3,.4; displacement control, failed members removed
# force controlled load P=.5, intact stiffness 3, u=.1667, then forced failure of member 1 => u=.25; remaining thresholds .3,.4; stable; after member 2 fails at u=.3, survivor capacity .4
truss=[]
for alive in ([0,1,2],[1,2],[2],[]):
 k=len(alive); sum_thresholds=sum([.2,.3,.4][i] for i in alive)
 u=.5/k if k else None
 truss.append(dict(alive=','.join(map(str,alive)),stiffness=k,sum_member_thresholds_not_system_capacity=sum_thresholds,force_control_displacement=u,stable_at_P05=(u is not None and all(u<=[.2,.3,.4][i]+1e-12 for i in alive))))
# energy consistency of removal at fixed u=0.2: energy lost = 1/2*k*u^2 = .02, cannot silently discard
with open(p/'mesh_localization.csv','w',newline='') as f:
 w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
with open(p/'truss_baselines.csv','w',newline='') as f:
 w=csv.DictWriter(f,truss[0].keys());w.writeheader();w.writerows(truss)
print(json.dumps({'mesh':rows,'truss':truss,'released_energy_per_failed_member_at_u02':.02},indent=2))
