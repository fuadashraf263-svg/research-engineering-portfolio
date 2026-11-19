"""Hand-verified anchor values: force specific inputs and compare to known answers.
Catches formula typos that range/invariant checks cannot."""
import core, templates
REG = core.REGISTRY

def byf(formula):
    for t in REG:
        if t['formula'] == formula:
            return t
    for t in REG:
        if t['formula'].startswith(formula):
            return t
    raise KeyError(formula)

def close(a, b, tol=0.01):
    return abs(a - b) <= tol * max(1.0, abs(b))

# (exact formula string, params, expected answer)
ANCHORS = [
    ("V = I R", {'I':3,'R':10}, 30),
    ("Req = R1 R2 / (R1 + R2)", {'R1':10,'R2':15}, 6),
    ("P = V I", {'V':12,'I':2}, 24),
    ("P = I^2 R", {'I':2,'R':5}, 20),
    ("Req = R1 + R2 + R3", {'R1':10,'R2':20,'R3':30}, 60),
    ("Ns = 120 f / P", {'f':50,'P':4}, 1500),
    ("V2 = V1 (N2 / N1)", {'V1':230,'N1':100,'N2':50}, 115),
    ("Eb = V - Ia Ra", {'V':220,'Ia':20,'Ra':0.5}, 210),
    ("P = sqrt(3) VL IL cos(phi)", {'VL':400,'IL':10,'pf':0.8}, 5.5426),
    ("Mmax = W L / 4", {'W':60,'L':4}, 60),
    ("Mmax = w L^2 / 8", {'w':10,'L':6}, 45),
    ("Mmax = W L", {'W':10,'L':3}, 30),
    ("M = w L^2 / 12", {'w':12,'L':6}, 36),
    ("eta = 1 - Tc/Th", {'Th':600,'Tc':300}, 50),
    ("COP_ref = Tc / (Th - Tc)", {'Tc':270,'Th':300}, 9),
    ("eta = 1 - 1/r^(gamma-1)", {'r':8}, 56.47),
    ("sigma_h = P d / (2 t)", {'P':1,'d':1000,'t':10}, 50),
    ("Re = rho V D / mu", {'V':2,'D':0.1}, 200000),
    ("hf = f L V^2 / (2 g D)", {'f':0.02,'L':100,'V':2,'D':0.1}, 4.0775),
    ("L = 0.5 rho V^2 S CL", {'S':20,'V':100,'rho':1.225,'CL':1.0}, 122.5),
    ("M = V / a", {'V':340,'a':340}, 1),
    ("EOQ = sqrt(2 D S / H)", {'D':1000,'S':50,'H':25}, 63.2456),
    ("PW = F / (1 + i)^n", {'F':1000,'n':2,'i':10}, 826.446),
    ("R_series = r1 * r2 * r3", {'r1':0.9,'r2':0.9,'r3':0.9}, 0.729),
    ("e = V^2 / (127 R)", {'R':100,'V':50}, 0.19685),
    ("C = 2 B log2(M)", {'B':4,'M':16}, 32),
    ("C = B log2(1 + SNR)", {'B':3,'SNR':7}, 9),
    ("Ka = (1 - sin phi) / (1 + sin phi)", {'phi':30}, 0.33333),
    ("d = D - cover - (bar diameter)/2", {'D':500,'c':25,'dia':20}, 465),
    ("t_half = ln(2) / k", {'k':0.1}, 6.9315),
    ("p_i = x_i Psat", {'x':0.5,'Psat':100}, 50),
    ("delta = W L^3 / (48 E I)", {'W':40,'L':4,'E':200,'I':100}, 40000*4000**3/(48*200000*100e6)),
    ("Nmin = ln[(xD/(1-xD)) ((1-xW)/xW)] / ln(alpha)", {'xd':0.95,'xw':0.05,'al':2.0}, 8.497),
]

def run():
    fails = []
    for formula, p, exp in ANCHORS:
        t = byf(formula)
        got = t['solve'](p)
        if not close(float(got), float(exp), tol=0.01):
            fails.append((formula, p, got, exp))
    print(f"Anchor tests: {len(ANCHORS)} | passed: {len(ANCHORS)-len(fails)}")
    if fails:
        for f in fails:
            print("  MISMATCH:", f)
        raise SystemExit(1)
    print("ALL ANCHOR VALUES CORRECT")

if __name__ == "__main__":
    run()
