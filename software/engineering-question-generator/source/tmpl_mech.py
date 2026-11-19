import math
from core import T, fmt

def close(a,b,rel=1e-3,ab=1e-6): return abs(a-b)<=max(ab,rel*max(abs(a),abs(b)))
PI=math.pi
B="Mechanical Engineering"

# ---- Strength of Materials ----
T(B,"Strength of Materials","easy",
  lambda p:f"A circular rod of diameter {p['d']} mm carries an axial tensile load of {p['F']} kN. Find the direct stress in MPa.",
  {'d':('int',10,60),'F':('int',5,120)},
  "sigma = F / A,  A = (pi/4) d^2",
  lambda p: p['F']*1000/(PI/4*p['d']**2),"MPa",
  steps=lambda p,v:[f"A = (pi/4)({p['d']})^2 = {fmt(PI/4*p['d']**2)} mm^2",
                    f"sigma = ({p['F']}*1000 N) / {fmt(PI/4*p['d']**2)} mm^2",
                    f"Answer: {fmt(v)} MPa"],
  check=lambda p,v: close(v*(PI/4*p['d']**2), p['F']*1000, rel=1e-3), tags=['stress'])

T(B,"Strength of Materials","medium",
  lambda p:f"A rod of diameter {p['d']} mm and length {p['L']} mm carries an axial load of {p['F']} kN. Take E = {p['E']} GPa. Find the elongation in mm.",
  {'d':('int',12,40),'L':('int',500,3000,100),'F':('int',10,90),'E':('choice',[200,210,110,70])},
  "delta = F L / (A E)",
  lambda p: (p['F']*1000)*p['L']/((PI/4*p['d']**2)*(p['E']*1000)),"mm",
  steps=lambda p,v:[f"A = (pi/4)({p['d']})^2 = {fmt(PI/4*p['d']**2)} mm^2",
                    f"delta = ({p['F']}*1000)({p['L']}) / ({fmt(PI/4*p['d']**2)} * {p['E']*1000})",
                    f"Answer: {fmt(v)} mm"], tags=['elongation'])

T(B,"Strength of Materials","medium",
  lambda p:f"A solid shaft of diameter {p['d']} mm transmits a torque of {p['Tt']} N-m. Find the maximum torsional shear stress in MPa.",
  {'d':('int',20,80),'Tt':('int',100,3000,50)},
  "tau = 16 T / (pi d^3)",
  lambda p: 16*p['Tt']*1000/(PI*p['d']**3),"MPa",
  subst=lambda p,v:f"tau = 16*({p['Tt']}*1000) / (pi*({p['d']})^3)",
  check=lambda p,v: close(v*PI*p['d']**3, 16*p['Tt']*1000, rel=1e-3), tags=['torsion'])

T(B,"Strength of Materials","medium",
  lambda p:f"A shaft of diameter {p['d']} mm and length {p['L']} mm carries a torque of {p['Tt']} N-m. With G = {p['G']} GPa, find the angle of twist in degrees.",
  {'d':('int',25,70),'L':('int',500,2000,100),'Tt':('int',200,2000,50),'G':('choice',[80,77,45])},
  "theta = T L / (G J),  J = pi d^4 / 32",
  lambda p: math.degrees((p['Tt']*1000)*p['L']/((p['G']*1000)*(PI*p['d']**4/32))),"degrees",
  steps=lambda p,v:[f"J = pi ({p['d']})^4 / 32 = {fmt(PI*p['d']**4/32)} mm^4",
                    f"theta = ({p['Tt']}*1000)({p['L']}) / ({p['G']*1000} * {fmt(PI*p['d']**4/32)}) rad",
                    f"Convert to degrees. Answer: {fmt(v)} degrees"], tags=['angle-of-twist'])

T(B,"Strength of Materials","easy",
  lambda p:f"A rectangular beam section is {p['b']} mm wide and {p['h']} mm deep. Find its section modulus about the horizontal axis in mm^3.",
  {'b':('int',30,150),'h':('int',60,300,10)},
  "Z = b h^2 / 6",
  lambda p: p['b']*p['h']**2/6,"mm^3",
  subst=lambda p,v:f"Z = {p['b']}*({p['h']})^2 / 6", tags=['section-modulus'])

T(B,"Strength of Materials","medium",
  lambda p:f"A rectangular cross-section beam ({p['b']} mm x {p['h']} mm) carries a bending moment of {p['M']} kN-m. Find the maximum bending stress in MPa.",
  {'b':('int',40,120),'h':('int',80,260,10),'M':('int',2,40)},
  "sigma = M / Z,  Z = b h^2 / 6",
  lambda p: (p['M']*1e6)/(p['b']*p['h']**2/6),"MPa",
  steps=lambda p,v:[f"Z = {p['b']}*({p['h']})^2/6 = {fmt(p['b']*p['h']**2/6)} mm^3",
                    f"sigma = ({p['M']}*1e6 N-mm) / {fmt(p['b']*p['h']**2/6)} mm^3",
                    f"Answer: {fmt(v)} MPa"], tags=['bending-stress'])

T(B,"Strength of Materials","hard",
  lambda p:f"A rectangular column ({p['b']} mm x {p['h']} mm) has effective length {p['L']} mm and E = {p['E']} GPa. Find the Euler buckling load in kN (buckling about the weak axis).",
  {'b':('int',30,80),'h':('int',90,160,10),'L':('int',1500,4000,100),'E':('choice',[200,210])},
  "Pcr = pi^2 E I / Le^2,  I = h b^3 / 12 (weak axis)",
  lambda p: (PI**2*(p['E']*1000)*(p['h']*p['b']**3/12)/p['L']**2)/1000,"kN",
  steps=lambda p,v:[f"I(weak) = {p['h']}*({p['b']})^3/12 = {fmt(p['h']*p['b']**3/12)} mm^4",
                    f"Pcr = pi^2 ({p['E']*1000})({fmt(p['h']*p['b']**3/12)}) / ({p['L']})^2 N",
                    f"Answer: {fmt(v)} kN"], tags=['euler-buckling'])

T(B,"Strength of Materials","easy",
  lambda p:f"A component of ultimate strength {p['su']} MPa is designed for a working stress of {p['sw']} MPa. Find the factor of safety.",
  {'su':('int',300,900,10),'sw':('int',60,250,10)},
  "FoS = ultimate strength / working stress",
  lambda p: p['su']/p['sw'],"",
  subst=lambda p,v:f"FoS = {p['su']} / {p['sw']}", valid=lambda p:p['su']>p['sw'], tags=['factor-of-safety'])

T(B,"Strength of Materials","medium",
  lambda p:f"A steel bar is fully restrained and heated through {p['dT']} deg C. With E = {p['E']} GPa and alpha = {p['al']}e-6 /deg C, find the thermal stress in MPa.",
  {'dT':('int',20,120,5),'E':('choice',[200,210]),'al':('int',11,13)},
  "sigma = E alpha (dT)",
  lambda p: (p['E']*1000)*(p['al']*1e-6)*p['dT'],"MPa",
  subst=lambda p,v:f"sigma = {p['E']*1000} * {p['al']}e-6 * {p['dT']}", tags=['thermal-stress'])

T(B,"Strength of Materials","medium",
  lambda p:f"A thin cylindrical shell of internal diameter {p['d']} mm and wall thickness {p['t']} mm carries an internal pressure of {fmt(p['P'])} MPa. Find the hoop (circumferential) stress in MPa.",
  {'d':('int',300,1500,50),'t':('int',6,20),'P':('float',0.5,3,1)},
  "sigma_h = P d / (2 t)",
  lambda p: p['P']*p['d']/(2*p['t']),"MPa",
  subst=lambda p,v:f"sigma_h = {fmt(p['P'])}*{p['d']} / (2*{p['t']})", tags=['hoop-stress'])

# ---- Thermodynamics ----
T(B,"Thermodynamics","easy",
  lambda p:f"A Carnot engine operates between {p['Th']} K and {p['Tc']} K. Find its thermal efficiency (%).",
  {'Th':('int',600,1200,20),'Tc':('int',280,450,10)},
  "eta = 1 - Tc/Th",
  lambda p: (1-p['Tc']/p['Th'])*100,"%",
  subst=lambda p,v:f"eta = (1 - {p['Tc']}/{p['Th']}) * 100", valid=lambda p:p['Th']>p['Tc'],
  check=lambda p,v: 0<v<100, tags=['carnot'])

T(B,"Thermodynamics","easy",
  lambda p:f"A refrigerator works between {p['Tc']} K (cold) and {p['Th']} K (hot). Find the maximum (Carnot) COP.",
  {'Tc':('int',250,275,1),'Th':('int',300,330,2)},
  "COP_ref = Tc / (Th - Tc)",
  lambda p: p['Tc']/(p['Th']-p['Tc']),"",
  subst=lambda p,v:f"COP = {p['Tc']} / ({p['Th']} - {p['Tc']})", valid=lambda p:p['Th']>p['Tc'], tags=['COP','refrigerator'])

T(B,"Thermodynamics","easy",
  lambda p:f"A heat pump operates between {p['Tc']} K and {p['Th']} K. Find its maximum (Carnot) COP.",
  {'Tc':('int',260,285,1),'Th':('int',300,335,2)},
  "COP_hp = Th / (Th - Tc)",
  lambda p: p['Th']/(p['Th']-p['Tc']),"",
  subst=lambda p,v:f"COP = {p['Th']} / ({p['Th']} - {p['Tc']})", valid=lambda p:p['Th']>p['Tc'], tags=['COP','heat-pump'])

T(B,"Thermodynamics","medium",
  lambda p:f"An Otto cycle has a compression ratio of {p['r']}. Taking gamma = 1.4, find the air-standard efficiency (%).",
  {'r':('int',6,12)},
  "eta = 1 - 1/r^(gamma-1)",
  lambda p: (1-1/p['r']**0.4)*100,"%",
  subst=lambda p,v:f"eta = (1 - 1/{p['r']}^0.4) * 100", check=lambda p,v:0<v<100, tags=['otto'])

T(B,"Thermodynamics","medium",
  lambda p:f"{fmt(p['m'])} kg of air is heated at constant volume through {p['dT']} deg C. Taking cv = 0.718 kJ/kg-K, find the change in internal energy in kJ.",
  {'m':('float',1,8,1),'dT':('int',20,200,5)},
  "dU = m cv dT",
  lambda p: p['m']*0.718*p['dT'],"kJ",
  subst=lambda p,v:f"dU = {fmt(p['m'])} * 0.718 * {p['dT']}", tags=['internal-energy'])

T(B,"Thermodynamics","medium",
  lambda p:f"{fmt(p['m'])} kg of air is heated at constant pressure through {p['dT']} deg C. Taking cp = 1.005 kJ/kg-K, find the change in enthalpy in kJ.",
  {'m':('float',1,8,1),'dT':('int',20,200,5)},
  "dH = m cp dT",
  lambda p: p['m']*1.005*p['dT'],"kJ",
  subst=lambda p,v:f"dH = {fmt(p['m'])} * 1.005 * {p['dT']}", tags=['enthalpy'])

T(B,"Thermodynamics","medium",
  lambda p:f"Air (R = 0.287 kJ/kg-K) occupies {fmt(p['V'])} m^3 at {p['Tk']} K with mass {fmt(p['m'])} kg. Find the pressure in kPa (ideal gas).",
  {'V':('float',0.5,4,1),'Tk':('int',300,600,10),'m':('float',1,6,1)},
  "p V = m R T  =>  p = m R T / V",
  lambda p: p['m']*0.287*p['Tk']/p['V'],"kPa",
  subst=lambda p,v:f"p = {fmt(p['m'])}*0.287*{p['Tk']} / {fmt(p['V'])}", tags=['ideal-gas'])

T(B,"Thermodynamics","hard",
  lambda p:f"{fmt(p['m'])} kg of air expands isothermally at {p['Tk']} K from volume V1 to {p['ratio']}*V1. Take R = 0.287 kJ/kg-K. Find the work done in kJ.",
  {'m':('float',1,5,1),'Tk':('int',300,500,10),'ratio':('int',2,5)},
  "W = m R T ln(V2/V1)",
  lambda p: p['m']*0.287*p['Tk']*math.log(p['ratio']),"kJ",
  subst=lambda p,v:f"W = {fmt(p['m'])}*0.287*{p['Tk']}*ln({p['ratio']})", tags=['isothermal-work'])

# ---- Fluid Mechanics ----
T(B,"Fluid Mechanics","easy",
  lambda p:f"Water (rho = 1000 kg/m^3, mu = 0.001 Pa-s) flows at {fmt(p['V'])} m/s through a pipe of diameter {fmt(p['D'])} m. Find the Reynolds number.",
  {'V':('float',0.5,5,1),'D':('float',0.05,0.4,2)},
  "Re = rho V D / mu",
  lambda p: 1000*p['V']*p['D']/0.001,"",
  subst=lambda p,v:f"Re = 1000*{fmt(p['V'])}*{fmt(p['D'])} / 0.001",
  check=lambda p,v: close(v*0.001, 1000*p['V']*p['D']), tags=['reynolds'])

T(B,"Fluid Mechanics","easy",
  lambda p:f"Water flows at {fmt(p['V'])} m/s through a pipe of diameter {p['d']} mm. Find the volumetric discharge in litres/second.",
  {'V':('float',0.5,4,1),'d':('int',50,300,10)},
  "Q = A V,  A = (pi/4) d^2",
  lambda p: (PI/4*(p['d']/1000)**2)*p['V']*1000,"L/s",
  steps=lambda p,v:[f"A = (pi/4)({p['d']/1000})^2 = {fmt(PI/4*(p['d']/1000)**2)} m^2",
                    f"Q = A V = {fmt(PI/4*(p['d']/1000)**2)} * {fmt(p['V'])} m^3/s = {fmt(v)} L/s",
                    f"Answer: {fmt(v)} L/s"], tags=['discharge'])

T(B,"Fluid Mechanics","easy",
  lambda p:f"Find the gauge pressure at a depth of {fmt(p['h'])} m in water (rho = 1000 kg/m^3, g = 9.81 m/s^2), in kPa.",
  {'h':('float',1,30,1)},
  "p = rho g h",
  lambda p: 1000*9.81*p['h']/1000,"kPa",
  subst=lambda p,v:f"p = 1000*9.81*{fmt(p['h'])} / 1000", tags=['hydrostatic'])

T(B,"Fluid Mechanics","medium",
  lambda p:f"Water issues from an orifice under a head of {fmt(p['h'])} m. Taking Cv = {fmt(p['cv'])}, find the actual jet velocity in m/s (g = 9.81).",
  {'h':('float',1,20,1),'cv':('float',0.95,0.99,2)},
  "V = Cv sqrt(2 g h)",
  lambda p: p['cv']*math.sqrt(2*9.81*p['h']),"m/s",
  subst=lambda p,v:f"V = {fmt(p['cv'])}*sqrt(2*9.81*{fmt(p['h'])})", tags=['torricelli'])

T(B,"Fluid Mechanics","medium",
  lambda p:f"In a pipe (diameter {p['d1']} mm) water flows at {fmt(p['V1'])} m/s. It contracts to diameter {p['d2']} mm. Find the velocity in the smaller pipe (m/s).",
  {'d1':('int',150,400,10),'d2':('int',50,140,10),'V1':('float',0.5,3,1)},
  "A1 V1 = A2 V2  =>  V2 = V1 (d1/d2)^2",
  lambda p: p['V1']*(p['d1']/p['d2'])**2,"m/s",
  subst=lambda p,v:f"V2 = {fmt(p['V1'])}*({p['d1']}/{p['d2']})^2",
  check=lambda p,v: close((p['d1']/2)**2*p['V1'],(p['d2']/2)**2*v,rel=1e-3),
  valid=lambda p:p['d2']<p['d1'], tags=['continuity'])

T(B,"Fluid Mechanics","hard",
  lambda p:f"Water flows at {fmt(p['V'])} m/s through a pipe of diameter {fmt(p['D'])} m and length {p['L']} m. With friction factor f = {fmt(p['f'])}, find the head loss due to friction in m (Darcy, g = 9.81).",
  {'V':('float',1,4,1),'D':('float',0.1,0.5,2),'L':('int',50,500,10),'f':('float',0.02,0.04,3)},
  "hf = f L V^2 / (2 g D)",
  lambda p: p['f']*p['L']*p['V']**2/(2*9.81*p['D']),"m",
  subst=lambda p,v:f"hf = {fmt(p['f'])}*{p['L']}*({fmt(p['V'])})^2 / (2*9.81*{fmt(p['D'])})", tags=['darcy'])

# ---- Theory of Machines / Design ----
T(B,"Theory of Machines","easy",
  lambda p:f"A pinion of {p['z1']} teeth drives a gear of {p['z2']} teeth. If the pinion runs at {p['N1']} rpm, find the gear speed in rpm.",
  {'z1':('int',15,40),'z2':('int',45,120),'N1':('int',300,1500,50)},
  "N1 z1 = N2 z2  =>  N2 = N1 z1 / z2",
  lambda p: p['N1']*p['z1']/p['z2'],"rpm",
  subst=lambda p,v:f"N2 = {p['N1']}*{p['z1']} / {p['z2']}",
  check=lambda p,v: close(p['N1']*p['z1'], v*p['z2']), tags=['gear-ratio'])

T(B,"Theory of Machines","easy",
  lambda p:f"A pulley of diameter {p['D']} mm rotates at {p['N']} rpm. Find the belt (peripheral) speed in m/s.",
  {'D':('int',100,600,10),'N':('int',200,1500,50)},
  "v = pi D N / 60",
  lambda p: PI*(p['D']/1000)*p['N']/60,"m/s",
  subst=lambda p,v:f"v = pi*({p['D']/1000})*{p['N']} / 60", tags=['belt-speed'])

T(B,"Machine Design","medium",
  lambda p:f"A shaft transmits {fmt(p['P'])} kW at {p['N']} rpm. Find the mean torque transmitted in N-m.",
  {'P':('float',2,50,1),'N':('int',200,1500,50)},
  "T = 60 P / (2 pi N)  (P in W)",
  lambda p: 60*p['P']*1000/(2*PI*p['N']),"N-m",
  subst=lambda p,v:f"T = 60*({fmt(p['P'])}*1000) / (2*pi*{p['N']})",
  check=lambda p,v: close(2*PI*p['N']*v/60, p['P']*1000, rel=1e-3), tags=['power-torque'])

T(B,"Theory of Machines","medium",
  lambda p:f"A mass of {fmt(p['m'])} kg rotates at radius {fmt(p['r'])} m at {p['N']} rpm. Find the centrifugal force in N.",
  {'m':('float',0.5,10,1),'r':('float',0.1,0.6,2),'N':('int',200,1200,50)},
  "F = m w^2 r,  w = 2 pi N / 60",
  lambda p: p['m']*(2*PI*p['N']/60)**2*p['r'],"N",
  steps=lambda p,v:[f"w = 2 pi {p['N']} / 60 = {fmt(2*PI*p['N']/60)} rad/s",
                    f"F = {fmt(p['m'])} * ({fmt(2*PI*p['N']/60)})^2 * {fmt(p['r'])}",
                    f"Answer: {fmt(v)} N"], tags=['centrifugal-force'])

T(B,"Machine Design","medium",
  lambda p:f"A spring-mass system has stiffness {p['k']} N/m and mass {fmt(p['m'])} kg. Find the natural frequency in Hz.",
  {'k':('int',500,20000,100),'m':('float',1,20,1)},
  "fn = (1/2pi) sqrt(k/m)",
  lambda p: (1/(2*PI))*math.sqrt(p['k']/p['m']),"Hz",
  subst=lambda p,v:f"fn = (1/2pi) sqrt({p['k']}/{fmt(p['m'])})", tags=['natural-frequency'])

# ---- Heat Transfer ----
T(B,"Heat Transfer","easy",
  lambda p:f"A plane wall of area {fmt(p['A'])} m^2 and thickness {fmt(p['L'])} m has conductivity k = {fmt(p['k'])} W/m-K. The temperature difference across it is {p['dT']} deg C. Find the heat conduction rate in W.",
  {'A':('float',1,10,1),'L':('float',0.1,0.4,2),'k':('float',0.5,50,1),'dT':('int',20,200,5)},
  "Q = k A dT / L",
  lambda p: p['k']*p['A']*p['dT']/p['L'],"W",
  subst=lambda p,v:f"Q = {fmt(p['k'])}*{fmt(p['A'])}*{p['dT']} / {fmt(p['L'])}", tags=['conduction'])

T(B,"Heat Transfer","easy",
  lambda p:f"A surface of area {fmt(p['A'])} m^2 loses heat by convection with h = {p['h']} W/m^2-K to surroundings {p['dT']} deg C cooler. Find the heat loss in W.",
  {'A':('float',0.5,6,1),'h':('int',10,200,5),'dT':('int',20,150,5)},
  "Q = h A dT",
  lambda p: p['h']*p['A']*p['dT'],"W",
  subst=lambda p,v:f"Q = {p['h']}*{fmt(p['A'])}*{p['dT']}", tags=['convection'])

T(B,"Heat Transfer","hard",
  lambda p:f"In a counter-flow heat exchanger the terminal temperature differences are {p['dT1']} deg C and {p['dT2']} deg C. Find the log mean temperature difference (LMTD) in deg C.",
  {'dT1':('int',40,120,5),'dT2':('int',5,35,5)},
  "LMTD = (dT1 - dT2) / ln(dT1/dT2)",
  lambda p: (p['dT1']-p['dT2'])/math.log(p['dT1']/p['dT2']),"deg C",
  subst=lambda p,v:f"LMTD = ({p['dT1']} - {p['dT2']}) / ln({p['dT1']}/{p['dT2']})",
  valid=lambda p:p['dT1']!=p['dT2'], tags=['LMTD'])

# ---- Manufacturing ----
T(B,"Manufacturing","medium",
  lambda p:f"In turning, cutting speed = {p['v']} m/min, feed = {fmt(p['f'])} mm/rev, depth of cut = {fmt(p['d'])} mm. Find the material removal rate in mm^3/min.",
  {'v':('int',60,250,10),'f':('float',0.1,0.5,2),'d':('float',0.5,3,1)},
  "MRR = 1000 v f d",
  lambda p: 1000*p['v']*p['f']*p['d'],"mm^3/min",
  subst=lambda p,v:f"MRR = 1000*{p['v']}*{fmt(p['f'])}*{fmt(p['d'])}", tags=['MRR'])

T(B,"Manufacturing","easy",
  lambda p:f"A workpiece of length {p['L']} mm is turned at {p['N']} rpm with a feed of {fmt(p['f'])} mm/rev. Find the machining time for one pass in minutes.",
  {'L':('int',80,500,10),'N':('int',200,1200,50),'f':('float',0.1,0.4,2)},
  "t = L / (f N)",
  lambda p: p['L']/(p['f']*p['N']),"min",
  subst=lambda p,v:f"t = {p['L']} / ({fmt(p['f'])}*{p['N']})", tags=['machining-time'])
