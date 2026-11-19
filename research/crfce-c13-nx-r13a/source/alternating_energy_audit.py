import os,numpy as np,json,csv
OUT=os.path.dirname(__file__);D=np.load(os.path.join(OUT,'3D_finite_conductor_source_basis.npz'));x=D['x'];G=D['B'];
q,w=np.polynomial.legendre.leggauss(3);vv=np.array([wa*wb*wc*.012*.004*.028/8 for wa in w for wb in w for wc in w]);v=np.tile(vv,4)*np.repeat([.6,1.4,.6,1.4],len(vv))
Ms=1.3e6;Bs=.6;phase=np.arange(4)*np.pi/2;Ib=4.;Ia=9.5;phi=2.356194490192345
I=np.array([np.r_[Ib+Ia*np.cos(2*np.pi*t/.08+phase+phi),Ib+Ia*np.cos(2*np.pi*t/.08+phase+phi)] for t in x]);B=np.einsum('nj,njpi->npi',I,G)
W=np.einsum('np,p->n',Ms*Bs*(np.sqrt(1+np.sum(B*B,axis=2)/Bs**2)-1),v)
M=Ms*B/np.sqrt(Bs**2+np.sum(B*B,axis=2))[...,None]
link=np.einsum('npi,njpi,p->nj',M,G,v)
U=np.einsum('nj,nj->n',I,link)-W
f=np.genfromtxt(os.path.join(OUT,'alternating_support_rank_thermal.csv'),delimiter=',',skip_header=1)
force=f[:,1]
rows=[]
for step in [1,2,4]:
 xx=x[::step];ii=I[::step];ll=link[::step];uu=U[::step];fx=force[::step]
 mech=np.trapezoid(fx,xx)
 src=np.sum(.5*(ii[1:]+ii[:-1])*(ll[1:]-ll[:-1]))
 du=uu[-1]-uu[0]
 rows.append({'n_intervals':len(xx)-1,'W_mech_J':mech,'E_magnetic_source_J':src,'Delta_U_J':du,'energy_residual_J':src-mech-du,'residual_fraction_of_copper_energy':(src-mech-du)/0.034565216253})
print(json.dumps(rows,indent=2));json.dump(rows,open(os.path.join(OUT,'alternating_energy_reciprocity.json'),'w'),indent=2)
