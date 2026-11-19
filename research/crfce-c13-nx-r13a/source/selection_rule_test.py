import numpy as np, csv,json,os
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=os.path.dirname(__file__); dat=np.load(os.path.join(OUT,'3D_finite_conductor_source_basis.npz'))
xs=dat['x'];B=dat['B']; dB=np.gradient(B,xs,axis=0,edge_order=2)
q,w=np.polynomial.legendre.leggauss(3)
vol=.012*.004*.028;w_1=np.array([wa*wb*wc*vol/8 for wa in w for wb in w for wc in w]);vw=np.tile(w_1,4)
assert B.shape[-2]==len(vw)
Ms=1.3e6;Bs=.6;pitch=.08;phase=np.arange(4)*np.pi/2;Ib=4.;Ia=9.5

def run(weights):
 vwmod=vw*np.repeat(np.array(weights),len(w_1))
 scan=[];best=None
 for phi in np.linspace(-np.pi,np.pi,145):
  I=np.array([np.r_[Ib+Ia*np.cos(2*np.pi*x/pitch+phase+phi),Ib+Ia*np.cos(2*np.pi*x/pitch+phase+phi)] for x in xs])
  BB=np.einsum('nj,njpc->npc',I,B);dBB=np.einsum('nj,njpc->npc',I,dB)
  M=Ms*BB/np.sqrt(Bs*Bs+np.sum(BB*BB,axis=-1))[...,None]
  Fx=np.einsum('npi,npi,p->n',M,dBB,vwmod)
  W=np.trapezoid(Fx,xs)
  scan.append([phi,W,float(Fx.min()),float(Fx.max())]);
  if best is None or W>best[0]:best=(W,phi,Fx)
 return best,scan
variants={'uniform':[1,1,1,1],'graded_0p6_to_1p4':[.6,.8,1.2,1.4],'alternating':[.6,1.4,.6,1.4],'asymmetric_1':[.4,1.,1.3,1.3],'single_island':[0,0,0,4],'one_small':[1.2,1.2,1.2,.4]}
res={}
for name,arr in variants.items():
 best,scan=run(arr)
 res[name]={'fill_fractions_scaled':arr,'mean_traction_N':float(best[0]/pitch),'work_J_80mm':float(best[0]),'peak_N':float(max(abs(best[2].min()),abs(best[2].max()))),'best_phase_rad':float(best[1])}
 print(name,res[name],flush=True)
 np.savetxt(os.path.join(OUT,f'{name}_force_curve.csv'),np.stack([xs*1000,best[2]],axis=1),delimiter=',',header='x_mm,Fx_N',comments='')
with open(os.path.join(OUT,'asymmetry_screen.json'),'w') as f:json.dump(res,f,indent=2)
fig,ax=plt.subplots(figsize=(9,5));
for name in ['uniform','graded_0p6_to_1p4','single_island']:
 a=np.genfromtxt(os.path.join(OUT,f'{name}_force_curve.csv'),delimiter=',',skip_header=1)
 ax.plot(a[:,0],a[:,1],label=name)
ax.set(xlabel='Carrier displacement (mm)',ylabel='Computed force (N)',title='Spatial symmetry-breaking screen (non-self-consistent polarizability model)')
ax.legend();fig.tight_layout();fig.savefig(os.path.join(OUT,'geometry_asymmetry_full_period.png'),dpi=160)
