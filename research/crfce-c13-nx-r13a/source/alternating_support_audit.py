import numpy as np,json,os, csv
OUT=os.path.dirname(__file__)
q,w=np.polynomial.legendre.leggauss(3);v1=np.array([wa*wb*wc*.012*.004*.028/8 for wa in w for wb in w for wc in w]);v=np.tile(v1,4)*np.repeat([.6,1.4,.6,1.4],len(v1))
dat=np.load(os.path.join(OUT,'3D_finite_conductor_source_basis.npz'));xs=dat['x'];G=dat['B'];Gp=dat['B_yplus'];Gm=dat['B_yminus'];dxG=np.gradient(G,xs,axis=0,edge_order=2)
Ms=1.3e6;Bs=.6;h=.00015;pitch=.08
phase=np.arange(4)*np.pi/2;phi=2.356194490192345; Ib=4.;Ia=9.5;z=xs*2*np.pi/pitch
J=np.zeros((len(xs),2,3));K=[];out=[]

def wprime(B):return np.dot(v,Ms*Bs*(np.sqrt(1+np.sum(B*B,axis=1)/Bs**2)-1))

def evaluate(k,iv):
 b=np.einsum('j,jpc->pc',iv,G[k]); bp=np.einsum('j,jpc->pc',iv,Gp[k]);bm=np.einsum('j,jpc->pc',iv,Gm[k]);dB=np.einsum('j,jpc->pc',iv,dxG[k]);
 m=Ms*b/np.sqrt(Bs*Bs+np.sum(b*b,axis=1))[:,None]
 fx=np.dot(v,np.sum(m*dB,axis=1));fy=(wprime(bp)-wprime(bm))/(2*h)
 Kvert=(wprime(bp)+wprime(bm)-2*wprime(b))/(h*h)
 return fx,fy,Kvert,wprime(b)
for k,x in enumerate(xs):
 base=Ib+Ia*np.cos(z[k]+phase+phi);I=np.r_[base,base]
 f= evaluate(k,I)
 # controls: quadrature propulsion (+ all upper and lower) and differential support upper/lower
 C=np.stack([np.tile(np.cos(phase),2),np.tile(np.sin(phase),2),np.r_[np.ones(4),-np.ones(4)]],axis=1)
 for a in range(3):
  plus=evaluate(k,I+.1*C[:,a]);minus=evaluate(k,I-.1*C[:,a]);J[k,:,a]=(np.array(plus[:2])-np.array(minus[:2]))/.2
 sv=np.linalg.svd(J[k],compute_uv=False)
 K.append(f[2]);out.append([x*1000,*f,sv[0],sv[1],J[k,1,2]])
K=np.array(K);out=np.array(out)
with open(os.path.join(OUT,'alternating_support_rank_thermal.csv'),'w',newline='') as f:
 c=csv.writer(f);c.writerow(['x_mm','Fx_N','Fy_N','Kyy_N_per_m_positive_destabilizing','Wprime_J','sigma_1_N_per_A','sigma_2_N_per_A','Fy_per_I_support_N_per_A']);c.writerows(out)
vertical_support_control=np.abs(out[:,7]);
# Support control required for 0.05mm displacement, using linearized local stiffness dFy/dy.
dy=.00005;target=K*dy
req=np.where(vertical_support_control>1e-10,np.abs(target)/vertical_support_control,np.inf)
res={'max_abs_Fx_N':float(np.max(np.abs(out[:,1]))),'mean_Fx_N':float(np.trapezoid(out[:,1],xs)/pitch),'Wmechanical_J_per_80mm':float(np.trapezoid(out[:,1],xs)),'max_abs_Fy_at_centerline_N':float(np.max(np.abs(out[:,2]))),'vertical_stiffness_Kyy_N_per_m_min':float(K.min()),'vertical_stiffness_Kyy_N_per_m_max':float(K.max()),'min_support_force_current_derivative_N_per_A':float(vertical_support_control.min()),'median_support_force_current_derivative_N_per_A':float(np.median(vertical_support_control)), 'min_two_axis_J_singular_value_N_per_A':float(out[:,6].min()),'positions_with_rank_below_1e_minus5':int(np.sum(out[:,6]<1e-5)), 'max_delta_support_current_A_for_0p05mm_deflection':float(req.max()),'median_delta_support_current_A_for_0p05mm_deflection':float(np.median(req)),'observations':'This normal stiffness is magnetic-only and about midplane; structural stiffness, feedback and dynamic stability not solved. Singular values depend on choice of ampere control normalization. Model has no self-consistent iron feedback; field lacks magnetic local return solids.'}
with open(os.path.join(OUT,'alternating_support_result.json'),'w') as f:json.dump(res,f,indent=2)
print(json.dumps(res,indent=2))
