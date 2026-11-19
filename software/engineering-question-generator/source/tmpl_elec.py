import math
from core import T, fmt
def close(a,b,rel=1e-3,ab=1e-6): return abs(a-b)<=max(ab,rel*max(abs(a),abs(b)))
PI=math.pi
B="Electrical Engineering"

# ---- DC circuits ----
T(B,"Circuit Theory","easy",
  lambda p:f"A resistor of {p['R']} ohm carries a current of {fmt(p['I'])} A. Find the voltage across it.",
  {'R':('int',2,200),'I':('float',0.1,10,1)},
  "V = I R", lambda p: p['I']*p['R'],"V",
  subst=lambda p,v:f"V = {fmt(p['I'])} * {p['R']}",
  check=lambda p,v: close(v, p['I']*p['R']), tags=['ohms-law'])

T(B,"Circuit Theory","easy",
  lambda p:f"Three resistors {p['R1']} ohm, {p['R2']} ohm and {p['R3']} ohm are connected in series. Find the equivalent resistance.",
  {'R1':('int',1,100),'R2':('int',1,100),'R3':('int',1,100)},
  "Req = R1 + R2 + R3", lambda p: p['R1']+p['R2']+p['R3'],"ohm",
  subst=lambda p,v:f"Req = {p['R1']} + {p['R2']} + {p['R3']}", tags=['series'])

T(B,"Circuit Theory","medium",
  lambda p:f"Two resistors {p['R1']} ohm and {p['R2']} ohm are connected in parallel. Find the equivalent resistance.",
  {'R1':('int',2,120),'R2':('int',2,120)},
  "Req = R1 R2 / (R1 + R2)", lambda p: p['R1']*p['R2']/(p['R1']+p['R2']),"ohm",
  subst=lambda p,v:f"Req = {p['R1']}*{p['R2']} / ({p['R1']}+{p['R2']})",
  check=lambda p,v: close(1/v, 1/p['R1']+1/p['R2']), tags=['parallel'])

T(B,"Circuit Theory","easy",
  lambda p:f"A device draws {fmt(p['I'])} A at {p['V']} V. Find the power consumed.",
  {'V':('int',5,240,5),'I':('float',0.1,15,1)},
  "P = V I", lambda p: p['V']*p['I'],"W",
  subst=lambda p,v:f"P = {p['V']} * {fmt(p['I'])}",
  check=lambda p,v: close(v, p['V']*p['I']), tags=['power'])

T(B,"Circuit Theory","medium",
  lambda p:f"A current of {fmt(p['I'])} A flows through a {p['R']} ohm resistor. Find the power dissipated.",
  {'I':('float',0.2,12,1),'R':('int',2,150)},
  "P = I^2 R", lambda p: p['I']**2*p['R'],"W",
  subst=lambda p,v:f"P = ({fmt(p['I'])})^2 * {p['R']}",
  check=lambda p,v: close(v, p['I']**2*p['R']), tags=['power','i2r'])

T(B,"Circuit Theory","medium",
  lambda p:f"Two capacitors {fmt(p['C1'])} uF and {fmt(p['C2'])} uF are connected in series. Find the equivalent capacitance in uF.",
  {'C1':('float',1,50,1),'C2':('float',1,50,1)},
  "Ceq = C1 C2 / (C1 + C2)", lambda p: p['C1']*p['C2']/(p['C1']+p['C2']),"uF",
  subst=lambda p,v:f"Ceq = {fmt(p['C1'])}*{fmt(p['C2'])} / ({fmt(p['C1'])}+{fmt(p['C2'])})",
  check=lambda p,v: close(1/v,1/p['C1']+1/p['C2']), tags=['capacitors-series'])

T(B,"Circuit Theory","easy",
  lambda p:f"A resistor {p['R']} kohm and capacitor {fmt(p['C'])} uF form a series RC circuit. Find the time constant in ms.",
  {'R':('int',1,100),'C':('float',0.1,20,1)},
  "tau = R C", lambda p: p['R']*1000*p['C']*1e-6*1000,"ms",
  subst=lambda p,v:f"tau = ({p['R']}k)({fmt(p['C'])}u) = {fmt(v)} ms", tags=['rc-time-constant'])

T(B,"Circuit Theory","easy",
  lambda p:f"An inductor {fmt(p['L'])} mH is in series with {p['R']} ohm. Find the time constant of the RL circuit in ms.",
  {'L':('float',10,500,1),'R':('int',5,200)},
  "tau = L / R", lambda p: (p['L']*1e-3)/p['R']*1000,"ms",
  subst=lambda p,v:f"tau = ({fmt(p['L'])}e-3) / {p['R']}", tags=['rl-time-constant'])

# ---- AC circuits ----
T(B,"AC Circuits","easy",
  lambda p:f"Find the inductive reactance of a {fmt(p['L'])} mH inductor at {p['f']} Hz.",
  {'L':('float',5,200,1),'f':('int',50,1000,10)},
  "XL = 2 pi f L", lambda p: 2*PI*p['f']*p['L']*1e-3,"ohm",
  subst=lambda p,v:f"XL = 2 pi ({p['f']})({fmt(p['L'])}e-3)", tags=['reactance','inductive'])

T(B,"AC Circuits","easy",
  lambda p:f"Find the capacitive reactance of a {fmt(p['C'])} uF capacitor at {p['f']} Hz.",
  {'C':('float',1,50,1),'f':('int',50,1000,10)},
  "XC = 1 / (2 pi f C)", lambda p: 1/(2*PI*p['f']*p['C']*1e-6),"ohm",
  subst=lambda p,v:f"XC = 1 / (2 pi ({p['f']})({fmt(p['C'])}e-6))", tags=['reactance','capacitive'])

T(B,"AC Circuits","medium",
  lambda p:f"A series RLC circuit has R = {p['R']} ohm, XL = {p['XL']} ohm and XC = {p['XC']} ohm. Find the magnitude of the impedance.",
  {'R':('int',5,100),'XL':('int',10,150),'XC':('int',10,150)},
  "Z = sqrt(R^2 + (XL - XC)^2)", lambda p: math.hypot(p['R'], p['XL']-p['XC']),"ohm",
  subst=lambda p,v:f"Z = sqrt({p['R']}^2 + ({p['XL']} - {p['XC']})^2)",
  check=lambda p,v: close(v*v, p['R']**2+(p['XL']-p['XC'])**2), tags=['impedance'])

T(B,"AC Circuits","hard",
  lambda p:f"Find the resonant frequency of a series circuit with L = {fmt(p['L'])} mH and C = {fmt(p['C'])} uF (in Hz).",
  {'L':('float',1,100,1),'C':('float',0.1,10,1)},
  "f0 = 1 / (2 pi sqrt(L C))", lambda p: 1/(2*PI*math.sqrt(p['L']*1e-3*p['C']*1e-6)),"Hz",
  subst=lambda p,v:f"f0 = 1 / (2 pi sqrt({fmt(p['L'])}e-3 * {fmt(p['C'])}e-6))",
  check=lambda p,v: close(2*PI*v*(p['L']*1e-3), 1/(2*PI*v*p['C']*1e-6), rel=2e-3), tags=['resonance'])

T(B,"AC Circuits","medium",
  lambda p:f"A capacitor of {fmt(p['C'])} uF is charged to {p['V']} V. Find the energy stored in millijoules.",
  {'C':('float',1,100,1),'V':('int',10,400,5)},
  "E = 0.5 C V^2", lambda p: 0.5*p['C']*1e-6*p['V']**2*1000,"mJ",
  subst=lambda p,v:f"E = 0.5*{fmt(p['C'])}e-6*({p['V']})^2", tags=['capacitor-energy'])

T(B,"AC Circuits","easy",
  lambda p:f"An alternating voltage has a peak value of {p['Vp']} V. Find its RMS value.",
  {'Vp':('int',10,340,2)},
  "Vrms = Vp / sqrt(2)", lambda p: p['Vp']/math.sqrt(2),"V",
  subst=lambda p,v:f"Vrms = {p['Vp']} / sqrt(2)",
  check=lambda p,v: close(v*math.sqrt(2), p['Vp']), tags=['rms'])

# ---- Machines & Power ----
T(B,"Electrical Machines","easy",
  lambda p:f"A transformer has primary voltage {p['V1']} V with {p['N1']} primary turns and {p['N2']} secondary turns. Find the secondary voltage.",
  {'V1':('int',110,440,10),'N1':('int',200,1000,10),'N2':('int',20,500,10)},
  "V2 = V1 (N2 / N1)", lambda p: p['V1']*p['N2']/p['N1'],"V",
  subst=lambda p,v:f"V2 = {p['V1']} * {p['N2']}/{p['N1']}",
  check=lambda p,v: close(v/p['V1'], p['N2']/p['N1']), tags=['transformer'])

T(B,"Electrical Machines","medium",
  lambda p:f"A DC motor is supplied at {p['V']} V and draws an armature current of {p['Ia']} A. If the armature resistance is {fmt(p['Ra'])} ohm, find the back EMF.",
  {'V':('int',110,440,10),'Ia':('int',5,60),'Ra':('float',0.1,1.5,2)},
  "Eb = V - Ia Ra", lambda p: p['V']-p['Ia']*p['Ra'],"V",
  subst=lambda p,v:f"Eb = {p['V']} - {p['Ia']}*{fmt(p['Ra'])}", tags=['back-emf'])

T(B,"Electrical Machines","easy",
  lambda p:f"Find the synchronous speed of a {p['P']}-pole machine on a {p['f']} Hz supply, in rpm.",
  {'P':('choice',[2,4,6,8,12]),'f':('choice',[50,60])},
  "Ns = 120 f / P", lambda p: 120*p['f']/p['P'],"rpm",
  subst=lambda p,v:f"Ns = 120*{p['f']} / {p['P']}",
  check=lambda p,v: close(v*p['P'], 120*p['f']), tags=['synchronous-speed'])

T(B,"Electrical Machines","medium",
  lambda p:f"A {p['P']}-pole induction motor on a {p['f']} Hz supply runs at {p['N']} rpm. Find the slip (%).",
  {'P':('choice',[4,6,8]),'f':('choice',[50,60]),'N':('int',700,1150,10)},
  "s = (Ns - N) / Ns,  Ns = 120 f / P",
  lambda p: (120*p['f']/p['P']-p['N'])/(120*p['f']/p['P'])*100,"%",
  steps=lambda p,v:[f"Ns = 120*{p['f']}/{p['P']} = {fmt(120*p['f']/p['P'])} rpm",
                    f"s = (Ns - N)/Ns = ({fmt(120*p['f']/p['P'])} - {p['N']})/{fmt(120*p['f']/p['P'])}",
                    f"Answer: {fmt(v)} %"],
  valid=lambda p: 0 < (120*p['f']/p['P']-p['N']) < 120*p['f']/p['P'], tags=['slip'])

T(B,"Power Systems","medium",
  lambda p:f"A balanced 3-phase load draws a line current of {p['IL']} A at {p['VL']} V (line) with a power factor of {fmt(p['pf'])}. Find the total real power in kW.",
  {'IL':('int',5,200,5),'VL':('choice',[400,415,433]),'pf':('float',0.7,0.98,2)},
  "P = sqrt(3) VL IL cos(phi)",
  lambda p: math.sqrt(3)*p['VL']*p['IL']*p['pf']/1000,"kW",
  subst=lambda p,v:f"P = sqrt(3)*{p['VL']}*{p['IL']}*{fmt(p['pf'])} / 1000", tags=['three-phase-power'])

T(B,"Power Systems","easy",
  lambda p:f"A load has real power {p['P']} kW and apparent power {p['S']} kVA. Find the power factor.",
  {'P':('int',10,180,5),'S':('int',20,220,5)},
  "pf = P / S", lambda p: p['P']/p['S'],"",
  subst=lambda p,v:f"pf = {p['P']} / {p['S']}", valid=lambda p:p['S']>=p['P'], tags=['power-factor'])

T(B,"Power Systems","medium",
  lambda p:f"A machine delivers {p['Po']} kW output while drawing {p['Pi']} kW input. Find its efficiency (%).",
  {'Po':('int',10,190,5),'Pi':('int',12,220,5)},
  "eta = (P_out / P_in) * 100", lambda p: p['Po']/p['Pi']*100,"%",
  subst=lambda p,v:f"eta = {p['Po']}/{p['Pi']} * 100", valid=lambda p:p['Pi']>p['Po'],
  check=lambda p,v: 0<v<100, tags=['efficiency'])

# ---- Electronics / Control ----
T(B,"Electronics","easy",
  lambda p:f"In a voltage divider, Vin = {p['Vin']} V across R1 = {p['R1']} ohm and R2 = {p['R2']} ohm in series. Find the output voltage across R2.",
  {'Vin':('int',5,30),'R1':('int',1,50),'R2':('int',1,50)},
  "Vout = Vin R2 / (R1 + R2)", lambda p: p['Vin']*p['R2']/(p['R1']+p['R2']),"V",
  subst=lambda p,v:f"Vout = {p['Vin']}*{p['R2']} / ({p['R1']}+{p['R2']})", tags=['voltage-divider'])

T(B,"Electronics","medium",
  lambda p:f"An inverting op-amp amplifier has Rf = {p['Rf']} kohm and Rin = {p['Rin']} kohm. Find the voltage gain (magnitude).",
  {'Rf':('int',10,220,10),'Rin':('int',1,47)},
  "|A| = Rf / Rin", lambda p: p['Rf']/p['Rin'],"",
  subst=lambda p,v:f"|A| = {p['Rf']} / {p['Rin']}", tags=['opamp','inverting'])

T(B,"Electronics","medium",
  lambda p:f"A non-inverting op-amp amplifier has Rf = {p['Rf']} kohm and Rg = {p['Rg']} kohm. Find the voltage gain.",
  {'Rf':('int',10,200,10),'Rg':('int',1,47)},
  "A = 1 + Rf / Rg", lambda p: 1+p['Rf']/p['Rg'],"",
  subst=lambda p,v:f"A = 1 + {p['Rf']}/{p['Rg']}", tags=['opamp','non-inverting'])

T(B,"Control Systems","medium",
  lambda p:f"An amplifier has an output/input power ratio of {p['ratio']}. Express the gain in decibels (power).",
  {'ratio':('int',2,10000)},
  "Gain(dB) = 10 log10(Pout/Pin)", lambda p: 10*math.log10(p['ratio']),"dB",
  subst=lambda p,v:f"Gain = 10 log10({p['ratio']})",
  check=lambda p,v: close(10**(v/10), p['ratio'], rel=1e-3), tags=['decibel'])

T(B,"Control Systems","medium",
  lambda p:f"A first-order system has a time constant of {fmt(p['tau'])} s. Find the time (in s) to reach 63.2% of its final value.",
  {'tau':('float',0.5,10,1)},
  "At t = tau the response reaches 63.2% (one time constant)",
  lambda p: p['tau'],"s",
  steps=lambda p,v:["For a first-order step response, y = 1 - e^(-t/tau)",
                    "y = 0.632 when t = tau",
                    f"Answer: {fmt(v)} s"], tags=['first-order','time-constant'])

T(B,"Signals & Systems","easy",
  lambda p:f"A signal is sampled at {p['fs']} kHz. According to the Nyquist criterion, what is the maximum signal frequency that can be represented (in kHz)?",
  {'fs':('int',8,192,2)},
  "f_max = fs / 2", lambda p: p['fs']/2,"kHz",
  subst=lambda p,v:f"f_max = {p['fs']} / 2",
  check=lambda p,v: close(2*v, p['fs']), tags=['nyquist','sampling'])
