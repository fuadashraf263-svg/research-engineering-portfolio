import math
from core import T, fmt
def close(a,b,rel=1e-3,ab=1e-6): return abs(a-b)<=max(ab,rel*max(abs(a),abs(b)))
B="Civil Engineering"

# ---- Structural analysis ----
T(B,"Structural Analysis","easy",
  lambda p:f"A simply supported beam of span {fmt(p['L'])} m carries a central point load of {p['W']} kN. Find the maximum bending moment in kN-m.",
  {'L':('float',3,10,1),'W':('int',10,120,5)},
  "Mmax = W L / 4", lambda p: p['W']*p['L']/4,"kN-m",
  subst=lambda p,v:f"Mmax = {p['W']}*{fmt(p['L'])} / 4",
  check=lambda p,v: close(4*v, p['W']*p['L']), tags=['bending-moment'])

T(B,"Structural Analysis","easy",
  lambda p:f"A simply supported beam of span {fmt(p['L'])} m carries a UDL of {p['w']} kN/m. Find the maximum bending moment in kN-m.",
  {'L':('float',3,10,1),'w':('int',5,60,5)},
  "Mmax = w L^2 / 8", lambda p: p['w']*p['L']**2/8,"kN-m",
  subst=lambda p,v:f"Mmax = {p['w']}*({fmt(p['L'])})^2 / 8",
  check=lambda p,v: close(8*v, p['w']*p['L']**2), tags=['bending-moment','udl'])

T(B,"Structural Analysis","easy",
  lambda p:f"A cantilever of length {fmt(p['L'])} m carries a point load {p['W']} kN at its free end. Find the maximum bending moment in kN-m.",
  {'L':('float',1,6,1),'W':('int',5,80,5)},
  "Mmax = W L", lambda p: p['W']*p['L'],"kN-m",
  subst=lambda p,v:f"Mmax = {p['W']}*{fmt(p['L'])}", tags=['cantilever'])

T(B,"Structural Analysis","medium",
  lambda p:f"A cantilever of length {fmt(p['L'])} m carries a UDL of {p['w']} kN/m over its whole length. Find the maximum bending moment in kN-m.",
  {'L':('float',1,6,1),'w':('int',4,40,2)},
  "Mmax = w L^2 / 2", lambda p: p['w']*p['L']**2/2,"kN-m",
  subst=lambda p,v:f"Mmax = {p['w']}*({fmt(p['L'])})^2 / 2", tags=['cantilever','udl'])

T(B,"Structural Analysis","medium",
  lambda p:f"A simply supported beam of span {fmt(p['L'])} m carries a point load {p['W']} kN at distance {fmt(p['a'])} m from the left support. Find the left reaction in kN.",
  {'L':('float',4,10,1),'a':('float',1,4,1),'W':('int',10,100,5)},
  "R_left = W (L - a) / L", lambda p: p['W']*(p['L']-p['a'])/p['L'],"kN",
  subst=lambda p,v:f"R_left = {p['W']}*({fmt(p['L'])} - {fmt(p['a'])}) / {fmt(p['L'])}",
  valid=lambda p:p['a']<p['L'], tags=['reactions'])

T(B,"Structural Analysis","hard",
  lambda p:f"A simply supported beam (span {fmt(p['L'])} m) carries a central point load {p['W']} kN. With E = {p['E']} GPa and I = {p['I']}e6 mm^4, find the maximum deflection in mm.",
  {'L':('float',3,8,1),'W':('int',10,80,5),'E':('choice',[25,30,200]),'I':('int',50,600,10)},
  "delta = W L^3 / (48 E I)",
  lambda p: (p['W']*1000)*(p['L']*1000)**3/(48*(p['E']*1000)*(p['I']*1e6)),"mm",
  steps=lambda p,v:[f"Use consistent N-mm units: W={p['W']*1000} N, L={p['L']*1000} mm, E={p['E']*1000} MPa, I={p['I']}e6 mm^4",
                    "delta = W L^3 / (48 E I)",
                    f"Answer: {fmt(v)} mm"], tags=['deflection'])

T(B,"Structural Analysis","medium",
  lambda p:f"A fixed beam of span {fmt(p['L'])} m carries a UDL of {p['w']} kN/m. Find the magnitude of the fixed-end moment in kN-m.",
  {'L':('float',4,9,1),'w':('int',6,45,3)},
  "M = w L^2 / 12", lambda p: p['w']*p['L']**2/12,"kN-m",
  subst=lambda p,v:f"M = {p['w']}*({fmt(p['L'])})^2 / 12", tags=['fixed-beam'])

# ---- RCC ----
T(B,"Reinforced Concrete","easy",
  lambda p:f"An RC beam has overall depth {p['D']} mm, clear cover {p['c']} mm and main bars of diameter {p['dia']} mm. Find the effective depth in mm.",
  {'D':('int',300,700,10),'c':('int',25,50,5),'dia':('choice',[12,16,20,25])},
  "d = D - cover - (bar diameter)/2",
  lambda p: p['D']-p['c']-p['dia']/2,"mm",
  subst=lambda p,v:f"d = {p['D']} - {p['c']} - {p['dia']}/2", tags=['effective-depth'])

T(B,"Reinforced Concrete","medium",
  lambda p:f"A column supports a floor area of {fmt(p['A'])} m^2 carrying a factored load of {fmt(p['w'])} kN/m^2. Find the total factored axial load in kN.",
  {'A':('float',10,40,1),'w':('float',8,20,1)},
  "P = w * tributary area", lambda p: p['w']*p['A'],"kN",
  subst=lambda p,v:f"P = {fmt(p['w'])} * {fmt(p['A'])}", tags=['tributary-load'])

T(B,"Reinforced Concrete","medium",
  lambda p:f"For a bar of diameter {p['dia']} mm with design bond stress {fmt(p['tbd'])} MPa and steel stress {p['fs']} MPa, find the development length in mm.",
  {'dia':('choice',[12,16,20,25]),'tbd':('float',1.2,2.4,1),'fs':('choice',[360,395,435])},
  "Ld = phi fs / (4 tau_bd)",
  lambda p: p['dia']*p['fs']/(4*p['tbd']),"mm",
  subst=lambda p,v:f"Ld = {p['dia']}*{p['fs']} / (4*{fmt(p['tbd'])})", tags=['development-length'])

# ---- Geotechnical ----
T(B,"Geotechnical","easy",
  lambda p:f"A soil sample has porosity n = {fmt(p['n'])}. Find its void ratio e.",
  {'n':('float',0.30,0.55,2)},
  "e = n / (1 - n)", lambda p: p['n']/(1-p['n']),"",
  subst=lambda p,v:f"e = {fmt(p['n'])} / (1 - {fmt(p['n'])})",
  check=lambda p,v: close(v/(1+v), p['n']), tags=['void-ratio'])

T(B,"Geotechnical","medium",
  lambda p:f"A cohesionless soil has an angle of internal friction phi = {p['phi']} degrees. Find Rankine's coefficient of active earth pressure Ka.",
  {'phi':('int',26,40)},
  "Ka = (1 - sin phi) / (1 + sin phi)",
  lambda p: (1-math.sin(math.radians(p['phi'])))/(1+math.sin(math.radians(p['phi']))),"",
  subst=lambda p,v:f"Ka = (1 - sin{p['phi']}) / (1 + sin{p['phi']})", tags=['active-pressure','Ka'])

T(B,"Geotechnical","hard",
  lambda p:f"A smooth vertical wall retains cohesionless backfill of height {fmt(p['H'])} m, unit weight {p['g']} kN/m^3, phi = {p['phi']} degrees. Find the total active thrust per metre run (kN/m).",
  {'H':('float',3,7,1),'g':('int',16,20),'phi':('int',28,38)},
  "Pa = 0.5 Ka gamma H^2,  Ka = (1 - sin phi)/(1 + sin phi)",
  lambda p: 0.5*((1-math.sin(math.radians(p['phi'])))/(1+math.sin(math.radians(p['phi']))))*p['g']*p['H']**2,"kN/m",
  steps=lambda p,v:[f"Ka = (1 - sin{p['phi']})/(1 + sin{p['phi']}) = {fmt((1-math.sin(math.radians(p['phi'])))/(1+math.sin(math.radians(p['phi']))))}",
                    f"Pa = 0.5 * Ka * {p['g']} * ({fmt(p['H'])})^2",
                    f"Answer: {fmt(v)} kN/m"], tags=['earth-pressure'])

T(B,"Geotechnical","medium",
  lambda p:f"At a depth of {fmt(p['z'])} m in a saturated soil (saturated unit weight {p['g']} kN/m^3, water table at surface), find the effective vertical stress in kPa (gamma_w = 9.81).",
  {'z':('float',2,12,1),'g':('int',18,21)},
  "sigma' = (gamma_sat - gamma_w) z",
  lambda p: (p['g']-9.81)*p['z'],"kPa",
  subst=lambda p,v:f"sigma' = ({p['g']} - 9.81)*{fmt(p['z'])}", tags=['effective-stress'])

T(B,"Geotechnical","medium",
  lambda p:f"In a constant-head permeameter, k = {fmt(p['k'])}e-4 m/s, hydraulic gradient i = {fmt(p['i'])}, area = {fmt(p['A'])}e-3 m^2. Find the seepage discharge in mm^3/s.",
  {'k':('float',1,9,1),'i':('float',0.2,1.5,1),'A':('float',1,8,1)},
  "q = k i A",
  lambda p: (p['k']*1e-4)*p['i']*(p['A']*1e-3)*1e9,"mm^3/s",
  subst=lambda p,v:f"q = ({fmt(p['k'])}e-4)*{fmt(p['i'])}*({fmt(p['A'])}e-3)", tags=['darcy-seepage'])

# ---- Hydraulics ----
T(B,"Hydraulics","medium",
  lambda p:f"An open channel has hydraulic radius {fmt(p['R'])} m, bed slope {fmt(p['S'])} (as a fraction) and Manning's n = {fmt(p['n'])}. Find the mean velocity in m/s.",
  {'R':('float',0.5,2.5,1),'S':('float',0.001,0.01,3),'n':('float',0.012,0.03,3)},
  "V = (1/n) R^(2/3) S^(1/2)",
  lambda p: (1/p['n'])*p['R']**(2/3)*p['S']**0.5,"m/s",
  subst=lambda p,v:f"V = (1/{fmt(p['n'])})*({fmt(p['R'])})^(2/3)*({fmt(p['S'])})^(1/2)", tags=['manning'])

T(B,"Hydraulics","hard",
  lambda p:f"Water flows over a rectangular weir of crest length {fmt(p['L'])} m under a head of {fmt(p['H'])} m. Taking Cd = {fmt(p['cd'])} (g = 9.81), find the discharge in m^3/s.",
  {'L':('float',1,5,1),'H':('float',0.2,1.2,1),'cd':('float',0.60,0.64,2)},
  "Q = (2/3) Cd sqrt(2 g) L H^(3/2)",
  lambda p: (2/3)*p['cd']*math.sqrt(2*9.81)*p['L']*p['H']**1.5,"m^3/s",
  subst=lambda p,v:f"Q = (2/3)*{fmt(p['cd'])}*sqrt(2*9.81)*{fmt(p['L'])}*({fmt(p['H'])})^1.5", tags=['weir'])

T(B,"Hydraulics","medium",
  lambda p:f"A rectangular channel {fmt(p['b'])} m wide carries a discharge of {fmt(p['Q'])} m^3/s. Find the critical depth in m (g = 9.81).",
  {'b':('float',2,6,1),'Q':('float',3,30,1)},
  "yc = (q^2 / g)^(1/3),  q = Q / b",
  lambda p: ((p['Q']/p['b'])**2/9.81)**(1/3),"m",
  steps=lambda p,v:[f"q = Q/b = {fmt(p['Q'])}/{fmt(p['b'])} = {fmt(p['Q']/p['b'])} m^2/s",
                    "yc = (q^2 / g)^(1/3)",
                    f"Answer: {fmt(v)} m"], tags=['critical-depth'])

# ---- Transportation ----
T(B,"Transportation","medium",
  lambda p:f"A highway curve has radius {p['R']} m and design speed {p['V']} km/h. Ignoring friction, find the superelevation required (as a ratio).",
  {'R':('int',100,600,10),'V':('int',40,100,5)},
  "e = V^2 / (127 R)  (V in km/h, R in m)",
  lambda p: p['V']**2/(127*p['R']),"",
  subst=lambda p,v:f"e = ({p['V']})^2 / (127*{p['R']})", tags=['superelevation'])

T(B,"Transportation","medium",
  lambda p:f"For a design speed of {p['V']} km/h with allowable superelevation {fmt(p['e'])} and lateral friction {fmt(p['f'])}, find the minimum curve radius in m.",
  {'V':('int',40,100,5),'e':('float',0.05,0.08,2),'f':('float',0.12,0.16,2)},
  "R = V^2 / (127 (e + f))",
  lambda p: p['V']**2/(127*(p['e']+p['f'])),"m",
  subst=lambda p,v:f"R = ({p['V']})^2 / (127*({fmt(p['e'])}+{fmt(p['f'])}))", tags=['curve-radius'])

# ---- Environmental & Hydrology ----
T(B,"Environmental","easy",
  lambda p:f"A tank of volume {p['V']} m^3 treats a flow of {p['Q']} m^3/h. Find the hydraulic retention time in hours.",
  {'V':('int',50,1000,10),'Q':('int',10,200,5)},
  "HRT = Volume / Flow rate", lambda p: p['V']/p['Q'],"h",
  subst=lambda p,v:f"HRT = {p['V']} / {p['Q']}", tags=['retention-time'])

T(B,"Environmental","medium",
  lambda p:f"The ultimate BOD of a sample is {p['L0']} mg/L and the deoxygenation rate constant k = {fmt(p['k'])} /day. Find the BOD exerted in {p['t']} days.",
  {'L0':('int',150,400,10),'k':('float',0.1,0.35,2),'t':('int',3,8)},
  "BOD_t = L0 (1 - e^(-k t))",
  lambda p: p['L0']*(1-math.exp(-p['k']*p['t'])),"mg/L",
  subst=lambda p,v:f"BOD_t = {p['L0']}*(1 - e^(-{fmt(p['k'])}*{p['t']}))", tags=['BOD'])

T(B,"Hydrology","medium",
  lambda p:f"Using the rational method with runoff coefficient C = {fmt(p['C'])}, rainfall intensity {p['i']} mm/h over a catchment of {fmt(p['A'])} hectares, find the peak runoff in m^3/s.",
  {'C':('float',0.3,0.9,2),'i':('int',30,120,5),'A':('float',5,60,1)},
  "Q = C i A / 360  (i in mm/h, A in hectares)",
  lambda p: p['C']*p['i']*p['A']/360,"m^3/s",
  subst=lambda p,v:f"Q = {fmt(p['C'])}*{p['i']}*{fmt(p['A'])} / 360", tags=['rational-method'])

T(B,"Surveying","easy",
  lambda p:f"A tape of nominal length {p['L']} m is actually {fmt(p['e'])} m too long. Find the correct length of a line measured as {p['M']} m with this tape.",
  {'L':('choice',[20,30]),'e':('float',0.01,0.08,2),'M':('int',100,800,10)},
  "True length = Measured * (L + e) / L",
  lambda p: p['M']*(p['L']+p['e'])/p['L'],"m",
  subst=lambda p,v:f"True = {p['M']}*({p['L']}+{fmt(p['e'])})/{p['L']}", tags=['tape-correction'])
