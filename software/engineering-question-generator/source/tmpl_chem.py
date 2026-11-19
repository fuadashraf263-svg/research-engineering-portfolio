import math
from core import T, fmt
def close(a,b,rel=1e-3,ab=1e-6): return abs(a-b)<=max(ab,rel*max(abs(a),abs(b)))
B="Chemical Engineering"

T(B,"Chemical Thermodynamics","medium",
  lambda p:f"Find the number of moles of an ideal gas occupying {fmt(p['V'])} m^3 at {p['P']} kPa and {p['Tk']} K (R = 8.314 J/mol-K).",
  {'V':('float',0.1,3,1),'P':('int',100,500,10),'Tk':('int',300,600,10)},
  "n = P V / (R T)",
  lambda p: (p['P']*1000)*p['V']/(8.314*p['Tk']),"mol",
  subst=lambda p,v:f"n = ({p['P']}e3)*{fmt(p['V'])} / (8.314*{p['Tk']})", tags=['ideal-gas'])

T(B,"Reaction Engineering","medium",
  lambda p:f"A first-order reaction has rate constant k = {fmt(p['k'])} /min. Find the fractional conversion after {p['t']} minutes.",
  {'k':('float',0.05,0.4,2),'t':('int',2,20)},
  "X = 1 - e^(-k t)", lambda p: (1-math.exp(-p['k']*p['t'])),"",
  subst=lambda p,v:f"X = 1 - e^(-{fmt(p['k'])}*{p['t']})",
  check=lambda p,v: close(math.exp(-p['k']*p['t']), 1-v), tags=['first-order','conversion'])

T(B,"Reaction Engineering","hard",
  lambda p:f"A first-order liquid reaction (k = {fmt(p['k'])} /min) is to reach {p['X']}% conversion in a plug-flow reactor. Find the required space time in minutes.",
  {'k':('float',0.1,0.5,2),'X':('int',50,90,5)},
  "tau = -ln(1 - X) / k",
  lambda p: -math.log(1-p['X']/100)/p['k'],"min",
  subst=lambda p,v:f"tau = -ln(1 - {p['X']/100}) / {fmt(p['k'])}", tags=['PFR','space-time'])

T(B,"Reaction Engineering","hard",
  lambda p:f"A first-order liquid reaction (k = {fmt(p['k'])} /min) reaches {p['X']}% conversion in a CSTR. Find the required space time in minutes.",
  {'k':('float',0.1,0.5,2),'X':('int',50,90,5)},
  "tau = X / (k (1 - X))",
  lambda p: (p['X']/100)/(p['k']*(1-p['X']/100)),"min",
  subst=lambda p,v:f"tau = {p['X']/100} / ({fmt(p['k'])}*(1 - {p['X']/100}))", tags=['CSTR','space-time'])

T(B,"Reaction Engineering","easy",
  lambda p:f"A first-order reaction has a rate constant of {fmt(p['k'])} /min. Find its half-life in minutes.",
  {'k':('float',0.02,0.5,2)},
  "t_half = ln(2) / k", lambda p: math.log(2)/p['k'],"min",
  subst=lambda p,v:f"t_half = 0.6931 / {fmt(p['k'])}",
  check=lambda p,v: close(math.exp(-p['k']*v), 0.5), tags=['half-life'])

T(B,"Reaction Engineering","hard",
  lambda p:f"For a reaction with A = {p['A']}e10 /s and activation energy {p['Ea']} kJ/mol at {p['Tk']} K, find the rate constant (per second). Take R = 8.314 J/mol-K.",
  {'A':('int',1,9),'Ea':('int',50,90,5),'Tk':('int',300,500,10)},
  "k = A exp(-Ea / (R T))",
  lambda p: (p['A']*1e10)*math.exp(-(p['Ea']*1000)/(8.314*p['Tk'])),"/s",
  subst=lambda p,v:f"k = {p['A']}e10 * exp(-{p['Ea']}e3 / (8.314*{p['Tk']}))", tags=['arrhenius'])

T(B,"Mass Transfer","hard",
  lambda p:f"In a binary distillation, distillate mole fraction xD = {fmt(p['xd'])} and bottoms xW = {fmt(p['xw'])}, with relative volatility alpha = {fmt(p['al'])}. Find the minimum number of theoretical stages (Fenske).",
  {'xd':('float',0.90,0.99,2),'xw':('float',0.02,0.10,2),'al':('float',1.5,3.5,1)},
  "Nmin = ln[(xD/(1-xD)) ((1-xW)/xW)] / ln(alpha)",
  lambda p: math.log((p['xd']/(1-p['xd']))*((1-p['xw'])/p['xw']))/math.log(p['al']),"stages",
  subst=lambda p,v:f"Nmin = ln[({fmt(p['xd'])}/{fmt(1-p['xd'])})({fmt(1-p['xw'])}/{fmt(p['xw'])})] / ln({fmt(p['al'])})", tags=['fenske'])

T(B,"Mass Transfer","medium",
  lambda p:f"Vapour and liquid mole fractions of the light component are y = {fmt(p['y'])} and x = {fmt(p['x'])}. Find the relative volatility alpha (binary).",
  {'y':('float',0.55,0.9,2),'x':('float',0.2,0.5,2)},
  "alpha = [y/(1-y)] / [x/(1-x)]",
  lambda p: (p['y']/(1-p['y']))/(p['x']/(1-p['x'])),"",
  subst=lambda p,v:f"alpha = ({fmt(p['y'])}/{fmt(1-p['y'])}) / ({fmt(p['x'])}/{fmt(1-p['x'])})",
  valid=lambda p:p['y']>p['x'], tags=['relative-volatility'])

T(B,"Mass Transfer","easy",
  lambda p:f"A liquid has mole fraction {fmt(p['x'])} of a component whose pure-component vapour pressure is {p['Psat']} kPa. Using Raoult's law, find its partial pressure in kPa.",
  {'x':('float',0.1,0.9,2),'Psat':('int',20,120,5)},
  "p_i = x_i Psat", lambda p: p['x']*p['Psat'],"kPa",
  subst=lambda p,v:f"p_i = {fmt(p['x'])} * {p['Psat']}", tags=['raoult'])

T(B,"Heat Transfer","medium",
  lambda p:f"A stream of {fmt(p['m'])} kg/s with specific heat {fmt(p['cp'])} kJ/kg-K is heated through {p['dT']} deg C. Find the heat duty in kW.",
  {'m':('float',0.5,10,1),'cp':('float',1.0,4.2,1),'dT':('int',10,120,5)},
  "Q = m cp dT", lambda p: p['m']*p['cp']*p['dT'],"kW",
  subst=lambda p,v:f"Q = {fmt(p['m'])}*{fmt(p['cp'])}*{p['dT']}",
  check=lambda p,v: close(v, p['m']*p['cp']*p['dT']), tags=['heat-duty'])

T(B,"Fluid Mechanics","medium",
  lambda p:f"A reactor of volume {fmt(p['V'])} m^3 is fed at a volumetric rate of {fmt(p['Q'])} m^3/min. Find the mean residence time in minutes.",
  {'V':('float',1,20,1),'Q':('float',0.2,5,1)},
  "tau = V / Q", lambda p: p['V']/p['Q'],"min",
  subst=lambda p,v:f"tau = {fmt(p['V'])} / {fmt(p['Q'])}", tags=['residence-time'])

T(B,"Mass Transfer","hard",
  lambda p:f"Steady diffusion occurs with D = {fmt(p['D'])}e-9 m^2/s across a film of thickness {p['L']} mm with a concentration difference of {p['dC']} mol/m^3. Find the molar flux in micromol/m^2-s.",
  {'D':('float',1,9,1),'L':('int',1,5),'dC':('int',10,200,10)},
  "J = D (dC / L)",
  lambda p: (p['D']*1e-9)*p['dC']/(p['L']*1e-3)*1e6,"micromol/m^2-s",
  subst=lambda p,v:f"J = ({fmt(p['D'])}e-9)*{p['dC']} / ({p['L']}e-3)", tags=['fick','diffusion'])

T(B,"Process Control","medium",
  lambda p:f"A first-order process has time constant {fmt(p['tau'])} min and steady-state gain {fmt(p['K'])}. For a step input of magnitude {p['M']}, find the final (steady-state) change in output.",
  {'tau':('float',1,10,1),'K':('float',0.5,4,1),'M':('int',2,20)},
  "Delta y(inf) = K * M", lambda p: p['K']*p['M'],"units",
  subst=lambda p,v:f"Delta y = {fmt(p['K'])} * {p['M']}", tags=['first-order','gain'])

T(B,"Reaction Engineering","easy",
  lambda p:f"A reactor operates at a space time of {fmt(p['tau'])} min. Find its space velocity in per hour.",
  {'tau':('float',0.5,20,1)},
  "SV = 60 / tau  (per hour)", lambda p: 60/p['tau'],"/h",
  subst=lambda p,v:f"SV = 60 / {fmt(p['tau'])}", tags=['space-velocity'])
