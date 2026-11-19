"""C13-NX physical-source 3D coil/island reduced-order *screen*, not FEM or proof.
Field is calculated from finite straight wire segments. Ferromagnetic volume is represented
by a local phenomenological saturating polarizability without mutual demagnetization.
It can verify its *own* coenergy/work reciprocity, NOT Maxwell-stress field convergence.
"""
import numpy as np, math, csv, json, os
from scipy.integrate import simpson
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=os.path.dirname(__file__)
MU0=4*np.pi*1e-7
phase_centers=np.array([-0.03,-0.01,0.01,0.03])
turns=36; pitch=.080
# The winding's 12x20 mm is interior geometric aperture, NOT the copper-pack cross-section.
loop_wx=.012;loop_wz=.020; coil_offset_y=.013
# 120 mm2 winding pack, copper fill 60%, 36 turns -> 2 mm2 copper per turn
pack_area_mm2=120.;packing=.60; conductor_area_mm2=pack_area_mm2*packing/turns
rho20=1.724e-8;alpha=.00393;Tcoil=80.;rho=rho20*(1+alpha*(Tcoil-20))
Rcoil=rho*(turns*2*(loop_wx+loop_wz))/(conductor_area_mm2*1e-6)
Jlim=5.; I_rms_max=conductor_area_mm2*Jlim
# 4 spherical-island equivalent *distributed* by numerical volume integration,
# volume equals original C13 12 x 4 x 28 mm islands; local saturation ignores demag interactions.
dims=(.012,.004,.028)
vol=np.prod(dims)
M_s=1.3e6;Bs=.60 # illustrative magnetic material response, not a measured B-H curve
# Gauss quadrature for island material sampling
from numpy.polynomial.legendre import leggauss
q,w=leggauss(3)
pts0=[]; vw=[]
for center in phase_centers:
 for a,wa in zip(q,w):
  for b,wb in zip(q,w):
   for c,wc in zip(q,w):
    pts0.append([center+a*dims[0]/2,b*dims[1]/2,c*dims[2]/2]);vw.append(wa*wb*wc*vol/8)
pts0=np.array(pts0); vw=np.array(vw)
# exact finite straight segment formula, avoids quadrature along the wire segments

def source_B_at(P,centre_x,side_y,repeat=6):
 B=np.zeros_like(P,dtype=float)
 for cell in range(-repeat,repeat+1):
  x=centre_x+pitch*cell
  # Approximate finite volume conductor with 4 sub-filaments in pack cross-section;
  # individual physical current fractions are equal and total effective turns stays 36.
  for dx in (-.001,.001):
   for dy in (-.001,.001):
    cx=x+dx;cy=side_y+dy
    corners=np.array([[cx-loop_wx/2,cy,-loop_wz/2],[cx+loop_wx/2,cy,-loop_wz/2],
                      [cx+loop_wx/2,cy,loop_wz/2],[cx-loop_wx/2,cy,loop_wz/2]])
    for i in range(4):
     a=corners[i];d=corners[(i+1)%4]-a;L=np.linalg.norm(d);u=d/L
     r=P-a; t=r@u;perp=r-t[:,None]*u[None,:];rr=np.einsum('ij,ij->i',perp,perp)
     rr=np.maximum(rr,1e-12)
     factor=((L-t)/np.sqrt(rr+(L-t)**2)+t/np.sqrt(rr+t*t))/rr
     B+=(MU0*turns/(4*np.pi*4))*np.cross(u[None,:],r)*factor[:,None]
 return B

N=121; xs=np.linspace(0,pitch,N); hs=.00015
# Coenergy defined from *explicit source fields*, not from prescribed B trajectory.
# For each x position compute the coil field basis for each of 8 independent circuits.
# Note numerical geometry is periodic by repeating the sources every 80 mm.
Bmat=[];Bplus=[];Bminus=[]
for ix,x in enumerate(xs):
 if ix%30==0: print('source-field sample',ix,'/',N-1,flush=True)
 pp=pts0.copy();pp[:,0]+=x
 pu=pp.copy();pu[:,1]+=hs
 pd=pp.copy();pd[:,1]-=hs
 b=np.empty((8,len(pp),3));bu=b.copy();bd=b.copy()
 for j in range(8):
  cy=(-coil_offset_y if j<4 else coil_offset_y)
  cent=phase_centers[j%4]
  b[j]=source_B_at(pp,cent,cy)
  bu[j]=source_B_at(pu,cent,cy)
  bd[j]=source_B_at(pd,cent,cy)
 Bmat.append(b);Bplus.append(bu);Bminus.append(bd)
Bmat=np.array(Bmat);Bplus=np.array(Bplus);Bminus=np.array(Bminus)
np.savez_compressed(os.path.join(OUT,'3D_finite_conductor_source_basis.npz'),x=xs,B=Bmat,B_yplus=Bplus,B_yminus=Bminus)
dBdx=np.gradient(Bmat,xs,axis=0,edge_order=2)

# Test drive profile is finite 2D actuation: four propulsion phases plus mirrored support coils.
phase=np.arange(4)*np.pi/2
Ib=4.;Ia=9.5
# maintain <= 13.5 A peak, 5 A/mm2 max for copper pack cross-section
Isupport=0.
# Phase sweep: optimize *only* the phase of a bounded traveling-wave control, never the source geometry.
def current_pattern(phi):
 return np.array([np.r_[Ib+Ia*np.cos(2*np.pi*x/pitch+phase+phi),Ib+Ia*np.cos(2*np.pi*x/pitch+phase+phi)] for x in xs])
def force_from_field(I0):
 B0=np.einsum('nj,njpc->npc',I0,Bmat)
 M0=M_s*B0/np.sqrt(Bs**2+np.einsum('npc,npc->np',B0,B0))[...,None]
 slope=np.einsum('nj,njpc->npc',I0,dBdx)
 return np.einsum('npi,npi,p->n',M0,slope,vw)
scan=[]
for phi in np.linspace(-np.pi,np.pi,73):
 Ii=current_pattern(phi);ff=force_from_field(Ii)
 scan.append([phi,np.trapezoid(ff,xs),np.max(np.abs(Ii)),np.min(ff),np.max(ff)])
scan=np.array(scan)
phi_best=scan[np.argmax(scan[:,1]),0]
I=current_pattern(phi_best)
with open(os.path.join(OUT,'drive_phase_scan.csv'),'w',newline='') as f:
 c=csv.writer(f);c.writerow(['phase_rad','Wmech_J_per_period','max_current_A','min_force_N','max_force_N']);c.writerows(scan)
assert np.max(np.abs(I))< I_rms_max*np.sqrt(2.)

def m_energy(B):
 norms=np.linalg.norm(B,axis=-1)
 return np.sum(vw*M_s*Bs*(np.sqrt(1+(norms/Bs)**2)-1),axis=-1)

def dWdB(B):
 return M_s*B/np.sqrt(Bs**2+np.einsum('...k,...k->...',B,B))[...,None]

# Evaluate coenergy W and incremental winding linkage from the same constitutive function.
B=np.einsum('nj,njpc->npc',I,Bmat)
Bp=np.einsum('nj,njpc->npc',I,Bplus)
Bm=np.einsum('nj,njpc->npc',I,Bminus)
W=m_energy(B);Fy=(m_energy(Bp)-m_energy(Bm))/(2*hs)
Lambda=np.einsum('npi,njpi,p->nj',dWdB(B),Bmat,vw)
# Exact shape derivative of the chosen local magnetic energy with respect to x at fixed current.
Fx=force_from_field(I)
# Electromagnetic electrical work via i d(lambda): only incremental island part;
# true air-coil self/mutual inductance not included; periodic delta U cancels if source states match.
Win=np.trapz(np.einsum('nj,nj->n',I,np.gradient(Lambda,xs,axis=0,edge_order=2)),xs)
Wmech=np.trapz(Fx,xs)
U=np.einsum('nj,nj->n',I,Lambda)-W
boundary=(W[-1]-W[0],U[-1]-U[0],np.max(np.abs(I[-1]-I[0])))
# Compute loop period (v=100 km/h), joule and current rms, return copper losses.
v=100/3.6; period_t=pitch/v
E_copper=np.trapz(Rcoil*np.sum(I**2,axis=1),xs)/v
P_copper=E_copper/period_t
I_rms=np.sqrt(np.mean(I**2,axis=0))
# Independent rank Jacobian in current input channels (Icos,Isin,Isupport differential).
# Evaluate at exactly each position using constitutive and energy gradients with I perturbs.
Jvals=[]
for k in range(1,N-1):
 def forces_3control(ua,ub,ud):
  ph=np.arange(4)*np.pi/2
  base=Ib+ua*np.cos(ph)+ub*np.sin(ph)
  iv=np.r_[base+ud,base-ud]
  Bn=np.einsum('j,jpc->pc',iv,Bmat[k]);Byp=np.einsum('j,jpc->pc',iv,Bplus[k]);Bym=np.einsum('j,jpc->pc',iv,Bminus[k]);
  xhi=np.einsum('j,jpc->pc',iv,Bmat[k+1]);xlo=np.einsum('j,jpc->pc',iv,Bmat[k-1]);
  return np.array([(m_energy(xhi)-m_energy(xlo))/(xs[k+1]-xs[k-1]),(m_energy(Byp)-m_energy(Bym))/(2*hs)])
 ua=Ia*np.cos(2*np.pi*xs[k]/pitch); ub=-Ia*np.sin(2*np.pi*xs[k]/pitch)
 eps=.1; columns=[]
 for j in range(3):
  dp=np.array([ua,ub,0.]);dp[j]+=eps
  dm=np.array([ua,ub,0.]);dm[j]-=eps
  columns.append((forces_3control(*dp)-forces_3control(*dm))/(2*eps))
 JJ=np.stack(columns,axis=1);sing=np.linalg.svd(JJ,compute_uv=False)
 Jvals.append([xs[k]*1000,*sing,*JJ.ravel()])
Jvals=np.array(Jvals)
# Simple carrier vertical structural response check as *parameterized* external stiffness, not FEA:
ky=1e6 # N/m illustrative, support linear spring stiffness; zero-drive air-core support field symmetry
vertical_deflection=Fy/ky

rows=[]
for n,x in enumerate(xs):rows.append([x*1000,*I[n],Fx[n],Fy[n],W[n],U[n],np.linalg.norm(B[n],axis=1).mean(),E_copper*n/(N-1),vertical_deflection[n]*1000])
with open(os.path.join(OUT,'full_period_3D_source_reduced.csv'),'w',newline='') as f:
 c=csv.writer(f);c.writerow(['x_mm']+[f'I{j}_A' for j in range(8)]+['Fx_N','Fy_N','Wprime_iron_J','U_iron_J','mean_B_source_T','cumulative_copper_energy_J_approx','Fy_over_1MNperM_mm']);c.writerows(rows)
with open(os.path.join(OUT,'control_jacobian_vs_position.csv'),'w',newline='') as f:
 c=csv.writer(f);c.writerow(['x_mm','singular_value_1_N_per_A','singular_value_2_N_per_A']+[f'J_{r}_{j}_N_per_A' for r in range(2) for j in range(3)]);c.writerows(Jvals)
result={'description':'3D Biot-Savart physical-coil + distributed saturating local magnetic-polarization surrogate; NOT nonlinear 3D FEM; does NOT model Maxwell stress self-consistently, eddy losses, material anisotropy, or moving material field','pitch_m':pitch,'best_phase_offset_rad':float(phi_best),'phase_scan_points':len(scan),'speed_m_s':v,'coils_total':8,'turns_each':turns,'winding_loop_interior_mm':[12,20],'coil_offsets_y_mm':[-13,13],'magnetic_islands_count':4,'island_dims_mm':[12,4,28], 'max_abs_current_A':float(np.max(np.abs(I))),'mean_current_rms_A':float(np.mean(I_rms)),'wire_area_mm2':conductor_area_mm2,'resistance_per_coil_ohm_80C':Rcoil,'iron_phenomenological_Ms_A_per_m':M_s,'iron_Bs_T':Bs,'mean_Fx_N':Wmech/pitch,'min_Fx_N':float(np.min(Fx)),'max_Fx_N':float(np.max(Fx)),'mean_abs_Fy_N':float(np.mean(np.abs(Fy))),'max_abs_Fy_N':float(np.max(np.abs(Fy))),'Wmechanical_per_80mm_J':float(Wmech),'E_source_increment_iron_J':float(Win),'delta_U_iron_J':float(U[-1]-U[0]),'energy_residual_J':float(Win-Wmech-(U[-1]-U[0])),'E_copper_J_per_80mm_8_coils':float(E_copper),'P_copper_W':float(P_copper),'boundary_Wprime_difference_J':float(W[-1]-W[0]),'max_end_current_difference_A':float(np.max(np.abs(I[-1]-I[0]))),'min_support_control_singular_value_N_per_A':float(np.min(Jvals[:,2])),'max_support_control_singular_value_N_per_A':float(np.max(Jvals[:,2])),'vertical_displacement_from_only_em_force_at_1MNperm_max_mm':float(np.max(np.abs(vertical_deflection))*1000),'vehicle_traction_requirement_N':879.38,'vehicle_work_per_80mm_J':70.35,'remarks':['Source field from finite rectangular current loops and 4-subfilament conductor cross-section; geometrical winding packs are a separate assumption, not a realizable finished coil CAD.','Moving ferromagnetic islands represented by local saturating polarization energy with no field feedback; this can seriously overpredict force and is not a validated steel law.','No Newton/Maxwell-stress cross-check; no convergence in geometry/material/mesh; rank here is reduced-model diagnostic only.','Full-period electromagnetic source power includes only island-induced incremental linkage and copper loss; self/mutual air-source field energy is omitted, though period boundary cancels it for an exact periodic solution.','E_copper accounts eight local coils only, periodic source array and full vehicle scale not accounted.']}
with open(os.path.join(OUT,'result.json'),'w') as f:json.dump(result,f,indent=2)
fig,ax=plt.subplots(figsize=(9,5));ax.plot(xs*1000,Fx,label='Calculated Fx (reduced model)');ax.plot(xs*1000,Fy,label='Calculated normal Fy (reduced model)');ax.axhline(879.38,color='k',ls='--',label='Module required Fx = 879.38 N');ax.axhline(0,color='grey',lw=.7);ax.set(xlabel='Moving carrier displacement (mm)',ylabel='Force (N)',title='C13-NX finite-coil-source screening — NOT 3D nonlinear FEM');ax.legend(loc='best');fig.tight_layout();fig.savefig(os.path.join(OUT,'force_full_period.png'),dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5));ax.plot(Jvals[:,0],Jvals[:,1],label='First singular value');ax.plot(Jvals[:,0],Jvals[:,2],label='Second singular value');ax.set(xlabel='Moving carrier displacement (mm)',ylabel='N/A (normalized input A)',title='Two-axis force-control authority — reduced model only');ax.legend();fig.tight_layout();fig.savefig(os.path.join(OUT,'controllability_full_period.png'),dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5));ax.plot(xs*1000,W,label="Magnetic island co-energy W'");ax.plot(xs*1000,U,label='Stored magnetic island energy U');ax.set(xlabel='Moving carrier displacement (mm)',ylabel='Energy (J)',title='Energy terms for reduced reciprocal model');ax.legend();fig.tight_layout();fig.savefig(os.path.join(OUT,'magnetic_energy_full_period.png'),dpi=160);plt.close(fig)
print(json.dumps(result,indent=2))
