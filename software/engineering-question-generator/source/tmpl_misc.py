import math
from core import T, fmt
def close(a,b,rel=1e-3,ab=1e-6): return abs(a-b)<=max(ab,rel*max(abs(a),abs(b)))

# ================= Aerospace Engineering =================
A="Aerospace Engineering"
T(A,"Aerodynamics","medium",
  lambda p:f"An aircraft wing of area {p['S']} m^2 flies at {p['V']} m/s (air density {fmt(p['rho'])} kg/m^3) with lift coefficient {fmt(p['CL'])}. Find the lift force in kN.",
  {'S':('int',15,120,5),'V':('int',60,260,10),'rho':('choice',[1.225,1.0,0.7,0.4]),'CL':('float',0.3,1.4,1)},
  "L = 0.5 rho V^2 S CL",
  lambda p: 0.5*p['rho']*p['V']**2*p['S']*p['CL']/1000,"kN",
  subst=lambda p,v:f"L = 0.5*{fmt(p['rho'])}*({p['V']})^2*{p['S']}*{fmt(p['CL'])} / 1000", tags=['lift'])

T(A,"Aerodynamics","medium",
  lambda p:f"An aircraft of wing area {p['S']} m^2 flies at {p['V']} m/s (density {fmt(p['rho'])} kg/m^3) with drag coefficient {fmt(p['CD'])}. Find the drag force in kN.",
  {'S':('int',15,120,5),'V':('int',60,260,10),'rho':('choice',[1.225,1.0,0.7,0.4]),'CD':('float',0.02,0.12,2)},
  "D = 0.5 rho V^2 S CD",
  lambda p: 0.5*p['rho']*p['V']**2*p['S']*p['CD']/1000,"kN",
  subst=lambda p,v:f"D = 0.5*{fmt(p['rho'])}*({p['V']})^2*{p['S']}*{fmt(p['CD'])} / 1000", tags=['drag'])

T(A,"Aerodynamics","easy",
  lambda p:f"Find the dynamic pressure for air of density {fmt(p['rho'])} kg/m^3 moving at {p['V']} m/s, in Pa.",
  {'rho':('choice',[1.225,1.0,0.7]),'V':('int',50,300,10)},
  "q = 0.5 rho V^2", lambda p: 0.5*p['rho']*p['V']**2,"Pa",
  subst=lambda p,v:f"q = 0.5*{fmt(p['rho'])}*({p['V']})^2", tags=['dynamic-pressure'])

T(A,"Flight Mechanics","easy",
  lambda p:f"An aircraft flies at {p['V']} m/s where the speed of sound is {p['a']} m/s. Find the Mach number.",
  {'V':('int',150,600,10),'a':('choice',[295,310,340])},
  "M = V / a", lambda p: p['V']/p['a'],"",
  subst=lambda p,v:f"M = {p['V']} / {p['a']}", tags=['mach'])

T(A,"Orbital Mechanics","hard",
  lambda p:f"Find the circular orbital velocity of a satellite at altitude {p['alt']} km above Earth (Earth radius 6371 km, mu = 3.986e14 m^3/s^2), in km/s.",
  {'alt':('int',200,2000,50)},
  "v = sqrt(mu / r),  r = (R_earth + altitude)",
  lambda p: math.sqrt(3.986e14/((6371+p['alt'])*1000))/1000,"km/s",
  steps=lambda p,v:[f"r = (6371 + {p['alt']}) km = {(6371+p['alt'])} km",
                    f"v = sqrt(3.986e14 / {(6371+p['alt'])*1000})",
                    f"Answer: {fmt(v)} km/s"], tags=['orbital-velocity'])

# ================= Materials Engineering =================
M="Materials Engineering"
T(M,"Mechanical Properties","easy",
  lambda p:f"A specimen under stress {p['sig']} MPa shows an elastic strain of {fmt(p['eps'])}e-3. Find the Young's modulus in GPa.",
  {'sig':('int',80,400,10),'eps':('float',0.5,3,1)},
  "E = stress / strain", lambda p: p['sig']/(p['eps']*1e-3)/1000,"GPa",
  subst=lambda p,v:f"E = {p['sig']} / ({fmt(p['eps'])}e-3) MPa = {fmt(v)} GPa", tags=['youngs-modulus'])

T(M,"Physical Properties","easy",
  lambda p:f"A block of mass {p['m']} kg has a volume of {fmt(p['V'])}e-3 m^3. Find its density in kg/m^3.",
  {'m':('int',2,50),'V':('float',0.5,6,1)},
  "density = mass / volume", lambda p: p['m']/(p['V']*1e-3),"kg/m^3",
  subst=lambda p,v:f"rho = {p['m']} / ({fmt(p['V'])}e-3)", tags=['density'])

T(M,"Thermal Properties","medium",
  lambda p:f"A rod of length {p['L']} mm is heated through {p['dT']} deg C. With coefficient of thermal expansion {p['al']}e-6 /deg C, find the change in length in mm.",
  {'L':('int',500,3000,100),'dT':('int',20,150,5),'al':('choice',[11,12,17,23])},
  "dL = L alpha dT", lambda p: p['L']*(p['al']*1e-6)*p['dT'],"mm",
  subst=lambda p,v:f"dL = {p['L']}*{p['al']}e-6*{p['dT']}", tags=['thermal-expansion'])

# ================= Instrumentation =================
I="Instrumentation & Measurement"
T(I,"Bridges","medium",
  lambda p:f"A Wheatstone bridge is balanced with R1 = {p['R1']} ohm, R2 = {p['R2']} ohm and R3 = {p['R3']} ohm. Find the unknown resistance R4 (R1/R2 = R3/R4).",
  {'R1':('int',10,200,5),'R2':('int',10,200,5),'R3':('int',10,500,5)},
  "R4 = R2 R3 / R1", lambda p: p['R2']*p['R3']/p['R1'],"ohm",
  subst=lambda p,v:f"R4 = {p['R2']}*{p['R3']} / {p['R1']}",
  check=lambda p,v: close(p['R1']/p['R2'], p['R3']/v), tags=['wheatstone'])

T(I,"Sensors","medium",
  lambda p:f"A strain gauge of resistance {p['R']} ohm and gauge factor {fmt(p['GF'])} experiences a strain of {p['eps']}e-6. Find the change in resistance in milliohms.",
  {'R':('choice',[120,350,1000]),'GF':('float',2.0,2.2,1),'eps':('int',100,2000,50)},
  "dR = R * GF * strain", lambda p: p['R']*p['GF']*(p['eps']*1e-6)*1000,"milliohm",
  subst=lambda p,v:f"dR = {p['R']}*{fmt(p['GF'])}*{p['eps']}e-6", tags=['strain-gauge'])

T(I,"Errors","easy",
  lambda p:f"A measurement reads {fmt(p['meas'])} when the true value is {fmt(p['true'])}. Find the percentage error.",
  {'meas':('float',9,11,2),'true':('choice',[10,20,50,100])},
  "% error = |measured - true| / true * 100",
  lambda p: abs(p['meas']-p['true'])/p['true']*100,"%",
  subst=lambda p,v:f"% error = |{fmt(p['meas'])} - {p['true']}| / {p['true']} * 100", tags=['percentage-error'])

# ================= Industrial / Engineering Economics =================
IE="Industrial Engineering"
T(IE,"Inventory","hard",
  lambda p:f"Annual demand is {p['D']} units, ordering cost {p['S']} per order and holding cost {p['H']} per unit per year. Find the economic order quantity (EOQ).",
  {'D':('int',1000,50000,500),'S':('int',20,300,10),'H':('int',2,40)},
  "EOQ = sqrt(2 D S / H)", lambda p: math.sqrt(2*p['D']*p['S']/p['H']),"units",
  subst=lambda p,v:f"EOQ = sqrt(2*{p['D']}*{p['S']} / {p['H']})",
  check=lambda p,v: close(p['H']*v*v, 2*p['D']*p['S'], rel=1e-3), tags=['EOQ'])

T(IE,"Engineering Economics","easy",
  lambda p:f"An asset costs {p['C']} with salvage value {p['Sv']} after {p['n']} years. Find the annual straight-line depreciation.",
  {'C':('int',50000,500000,10000),'Sv':('int',2000,40000,2000),'n':('int',5,20)},
  "Depreciation = (Cost - Salvage) / life",
  lambda p: (p['C']-p['Sv'])/p['n'],"per year",
  subst=lambda p,v:f"D = ({p['C']} - {p['Sv']}) / {p['n']}", valid=lambda p:p['C']>p['Sv'], tags=['depreciation'])

T(IE,"Engineering Economics","medium",
  lambda p:f"A product sells for {p['P']} per unit with variable cost {p['V']} per unit and fixed costs {p['F']}. Find the break-even quantity in units.",
  {'P':('int',50,500,10),'V':('int',10,200,10),'F':('int',10000,200000,5000)},
  "Q_be = Fixed cost / (Price - Variable cost)",
  lambda p: p['F']/(p['P']-p['V']),"units",
  subst=lambda p,v:f"Q = {p['F']} / ({p['P']} - {p['V']})", valid=lambda p:p['P']>p['V'], tags=['break-even'])

T(IE,"Engineering Economics","medium",
  lambda p:f"Find the present worth of {p['F']} received {p['n']} years from now at an interest rate of {p['i']}% per year.",
  {'F':('int',10000,200000,5000),'n':('int',2,10),'i':('int',5,12)},
  "PW = F / (1 + i)^n", lambda p: p['F']/(1+p['i']/100)**p['n'],"currency units",
  subst=lambda p,v:f"PW = {p['F']} / (1 + {p['i']/100})^{p['n']}", tags=['present-worth'])

T(IE,"Reliability","medium",
  lambda p:f"Three components with reliabilities {fmt(p['r1'])}, {fmt(p['r2'])} and {fmt(p['r3'])} are connected in series. Find the system reliability.",
  {'r1':('float',0.90,0.99,2),'r2':('float',0.90,0.99,2),'r3':('float',0.90,0.99,2)},
  "R_series = r1 * r2 * r3", lambda p: p['r1']*p['r2']*p['r3'],"",
  subst=lambda p,v:f"R = {fmt(p['r1'])}*{fmt(p['r2'])}*{fmt(p['r3'])}", tags=['reliability-series'])

T(IE,"Reliability","medium",
  lambda p:f"Two components each of reliability {fmt(p['r'])} are connected in parallel. Find the system reliability.",
  {'r':('float',0.7,0.95,2)},
  "R_parallel = 1 - (1 - r)^2", lambda p: 1-(1-p['r'])**2,"",
  subst=lambda p,v:f"R = 1 - (1 - {fmt(p['r'])})^2", tags=['reliability-parallel'])

T(IE,"Quality Control","easy",
  lambda p:f"A process produces {p['def']} defective items in a batch of {p['N']}. Find the defect rate in parts per million (PPM).",
  {'def':('int',1,50),'N':('int',1000,20000,500)},
  "PPM = (defects / total) * 1e6", lambda p: p['def']/p['N']*1e6,"PPM",
  subst=lambda p,v:f"PPM = {p['def']}/{p['N']} * 1e6", tags=['ppm','quality'])
