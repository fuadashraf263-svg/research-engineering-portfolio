import math
from core import T, fmt, poly_str

def close(a, b, rel=1e-3, ab=1e-6):
    return abs(a - b) <= max(ab, rel * max(abs(a), abs(b)))

B = "Engineering Mathematics"

# 1. derivative of cubic at a point
def _d1_q(p):
    return f"Find the derivative of f(x) = {poly_str([p['a'],p['b'],p['c'],p['d']])} evaluated at x = {fmt(p['x0'])}."
def _d1_solve(p):
    return 3*p['a']*p['x0']**2 + 2*p['b']*p['x0'] + p['c']
def _d1_steps(p, v):
    return [f"f(x) = {poly_str([p['a'],p['b'],p['c'],p['d']])}",
            f"f'(x) = {poly_str([3*p['a'],2*p['b'],p['c']])}",
            f"f'({fmt(p['x0'])}) = 3({fmt(p['a'])})({fmt(p['x0'])})^2 + 2({fmt(p['b'])})({fmt(p['x0'])}) + ({fmt(p['c'])})",
            f"Answer: f'({fmt(p['x0'])}) = {fmt(v)}"]
def _d1_check(p, v):
    f = lambda x: p['a']*x**3 + p['b']*x**2 + p['c']*x + p['d']
    h = 1e-4; fd = (f(p['x0']+h) - f(p['x0']-h))/(2*h)
    return close(fd, v, rel=1e-3, ab=1e-3)
T(B, "Calculus", "easy", _d1_q,
  {'a':('int',-6,6),'b':('int',-8,8),'c':('int',-9,9),'d':('int',-9,9),'x0':('int',-5,5)},
  "f'(x) = 3a x^2 + 2b x + c", _d1_solve, "", steps=_d1_steps, check=_d1_check,
  valid=lambda p: p['a'] != 0, tags=['derivative','polynomial'])

# 2. second derivative of cubic at a point
T(B, "Calculus", "easy",
  lambda p: f"For f(x) = {poly_str([p['a'],p['b'],p['c'],p['d']])}, find f''(x) at x = {fmt(p['x0'])}.",
  {'a':('int',-6,6),'b':('int',-8,8),'c':('int',-9,9),'d':('int',-9,9),'x0':('int',-5,5)},
  "f''(x) = 6a x + 2b", lambda p: 6*p['a']*p['x0'] + 2*p['b'], "",
  steps=lambda p,v: [f"f'(x) = {poly_str([3*p['a'],2*p['b'],p['c']])}",
                     f"f''(x) = {poly_str([6*p['a'],2*p['b']])}",
                     f"f''({fmt(p['x0'])}) = 6({fmt(p['a'])})({fmt(p['x0'])}) + 2({fmt(p['b'])})",
                     f"Answer: {fmt(v)}"],
  valid=lambda p: p['a'] != 0, tags=['second-derivative'])

# 3. definite integral of quadratic
def _i_solve(p):
    a,b,c,x1,x2 = p['a'],p['b'],p['c'],p['x1'],p['x2']
    F = lambda x: a*x**3/3 + b*x**2/2 + c*x
    return F(x2) - F(x1)
def _i_check(p, v):
    a,b,c,x1,x2 = p['a'],p['b'],p['c'],p['x1'],p['x2']
    f = lambda x: a*x**2 + b*x + c
    n = 1000; h = (x2 - x1)/n; s = f(x1) + f(x2)
    for i in range(1, n):
        s += (4 if i % 2 else 2)*f(x1 + i*h)
    return close(s*h/3, v, rel=1e-3, ab=1e-3)
T(B, "Calculus", "medium",
  lambda p: f"Evaluate the definite integral of ({poly_str([p['a'],p['b'],p['c']])}) dx from x = {fmt(p['x1'])} to x = {fmt(p['x2'])}.",
  {'a':('int',-5,5),'b':('int',-6,6),'c':('int',-8,8),'x1':('int',-4,2),'x2':('int',3,7)},
  "integral = a x^3/3 + b x^2/2 + c x", _i_solve, "",
  steps=lambda p,v: [f"Antiderivative F(x) = {fmt(p['a'])}x^3/3 + {fmt(p['b'])}x^2/2 + {fmt(p['c'])}x",
                     f"Evaluate F({fmt(p['x2'])}) - F({fmt(p['x1'])})",
                     f"Answer: {fmt(v)}"],
  check=_i_check, valid=lambda p: p['x2'] > p['x1'], tags=['integral','definite'])

# 4. larger real root of a quadratic
def _root_solve(p):
    a,b,c = p['a'],p['b'],p['c']
    D = b*b - 4*a*c
    return (-b + math.sqrt(D))/(2*a)
def _root_check(p, v):
    return close(p['a']*v*v + p['b']*v + p['c'], 0.0, ab=1e-4)
T(B, "Algebra", "medium",
  lambda p: f"Find the larger real root of {poly_str([p['a'],p['b'],p['c']])} = 0.",
  {'a':('int',1,6),'b':('int',-12,12),'c':('int',-12,12)},
  "x = (-b + sqrt(b^2 - 4ac)) / (2a)", _root_solve, "",
  steps=lambda p,v: [f"Discriminant D = ({fmt(p['b'])})^2 - 4*{fmt(p['a'])}*({fmt(p['c'])}) = {fmt(p['b']**2-4*p['a']*p['c'])}",
                     f"x = (-({fmt(p['b'])}) + sqrt({fmt(p['b']**2-4*p['a']*p['c'])})) / (2*{fmt(p['a'])})",
                     f"Answer: x = {fmt(v)}"],
  check=_root_check, valid=lambda p: p['b']*p['b'] - 4*p['a']*p['c'] > 0, tags=['quadratic','roots'])

# 5. determinant 2x2
T(B, "Linear Algebra", "easy",
  lambda p: f"Find the determinant of the 2x2 matrix [[{fmt(p['a'])}, {fmt(p['b'])}], [{fmt(p['c'])}, {fmt(p['d'])}]].",
  {'a':('int',-9,9),'b':('int',-9,9),'c':('int',-9,9),'d':('int',-9,9)},
  "det = ad - bc", lambda p: p['a']*p['d'] - p['b']*p['c'], "",
  subst=lambda p,v: f"det = ({fmt(p['a'])})({fmt(p['d'])}) - ({fmt(p['b'])})({fmt(p['c'])})",
  tags=['determinant','matrix'])

# 6. determinant 3x3
def _det3_solve(p):
    a,b,c,d,e,f,g,h,i = (p[k] for k in 'abcdefghi')
    return a*(e*i - f*h) - b*(d*i - f*g) + c*(d*h - e*g)
def _det3_check(p, v):
    import numpy as np
    M = np.array([[p['a'],p['b'],p['c']],[p['d'],p['e'],p['f']],[p['g'],p['h'],p['i']]], float)
    return close(float(np.linalg.det(M)), v, rel=1e-4, ab=1e-3)
T(B, "Linear Algebra", "medium",
  lambda p: ("Find the determinant of [[{a}, {b}, {c}], [{d}, {e}, {f}], [{g}, {h}, {i}]].".format(
      **{k: fmt(p[k]) for k in 'abcdefghi'})),
  {k:('int',-6,6) for k in 'abcdefghi'},
  "det = a(ei-fh) - b(di-fg) + c(dh-eg)", _det3_solve, "",
  steps=lambda p,v: ["Expand along the first row:",
                     "det = a(ei - fh) - b(di - fg) + c(dh - eg)",
                     f"Answer: {fmt(v)}"],
  check=_det3_check, tags=['determinant','3x3'])

# 7. dominant eigenvalue of 2x2 (real)
def _eig_solve(p):
    tr = p['a'] + p['d']; det = p['a']*p['d'] - p['b']*p['c']
    return (tr + math.sqrt(tr*tr - 4*det))/2
def _eig_check(p, v):
    import numpy as np
    w = np.linalg.eigvals(np.array([[p['a'],p['b']],[p['c'],p['d']]], float))
    return close(float(max(w.real)), v, rel=1e-4, ab=1e-3)
T(B, "Linear Algebra", "hard",
  lambda p: f"Find the larger eigenvalue of [[{fmt(p['a'])}, {fmt(p['b'])}], [{fmt(p['c'])}, {fmt(p['d'])}]].",
  {'a':('int',-8,8),'b':('int',-8,8),'c':('int',-8,8),'d':('int',-8,8)},
  "lambda = (tr + sqrt(tr^2 - 4 det)) / 2", _eig_solve, "",
  steps=lambda p,v: [f"Trace tr = {fmt(p['a']+p['d'])}, Determinant = {fmt(p['a']*p['d']-p['b']*p['c'])}",
                     f"lambda = (tr + sqrt(tr^2 - 4 det)) / 2",
                     f"Answer: {fmt(v)}"],
  check=_eig_check,
  valid=lambda p: (p['a']+p['d'])**2 - 4*(p['a']*p['d']-p['b']*p['c']) > 0, tags=['eigenvalue'])

# 8. solve 2x2 system (x by Cramer)
def _sys_solve(p):
    det = p['a']*p['d'] - p['b']*p['c']
    return (p['e']*p['d'] - p['b']*p['f'])/det
def _sys_check(p, v):
    det = p['a']*p['d'] - p['b']*p['c']
    y = (p['a']*p['f'] - p['e']*p['c'])/det
    return close(p['a']*v + p['b']*y, p['e'], ab=1e-4) and close(p['c']*v + p['d']*y, p['f'], ab=1e-4)
T(B, "Linear Algebra", "medium",
  lambda p: f"Solve for x: {fmt(p['a'])}x + {fmt(p['b'])}y = {fmt(p['e'])} and {fmt(p['c'])}x + {fmt(p['d'])}y = {fmt(p['f'])}.",
  {'a':('int',-6,6),'b':('int',-6,6),'c':('int',-6,6),'d':('int',-6,6),'e':('int',-12,12),'f':('int',-12,12)},
  "x = (e d - b f) / (a d - b c)  [Cramer's rule]", _sys_solve, "",
  steps=lambda p,v: [f"Determinant = {fmt(p['a'])}*{fmt(p['d'])} - {fmt(p['b'])}*{fmt(p['c'])} = {fmt(p['a']*p['d']-p['b']*p['c'])}",
                     f"x = (e d - b f) / det = {fmt(v)}",
                     f"Answer: x = {fmt(v)}"],
  check=_sys_check, valid=lambda p: p['a']*p['d'] - p['b']*p['c'] != 0, tags=['linear-system','cramer'])

# 9. mean of five numbers
T(B, "Statistics", "easy",
  lambda p: f"Find the arithmetic mean of the data set: {p['n1']}, {p['n2']}, {p['n3']}, {p['n4']}, {p['n5']}.",
  {f'n{i}':('int',1,100) for i in range(1,6)},
  "mean = (sum of values) / n", lambda p: sum(p[f'n{i}'] for i in range(1,6))/5, "",
  steps=lambda p,v: [f"Sum = {sum(p[f'n{i}'] for i in range(1,6))}",
                     f"Mean = Sum / 5 = {fmt(v)}", f"Answer: {fmt(v)}"],
  check=lambda p,v: close(sum(p[f'n{i}'] for i in range(1,6))/5, v), tags=['mean','statistics'])

# 10. sample standard deviation of five numbers
def _sd_solve(p):
    xs = [p[f'n{i}'] for i in range(1,6)]; m = sum(xs)/5
    return math.sqrt(sum((x-m)**2 for x in xs)/4)
def _sd_check(p, v):
    import statistics as st
    return close(st.stdev([p[f'n{i}'] for i in range(1,6)]), v, ab=1e-4)
T(B, "Statistics", "medium",
  lambda p: f"Find the sample standard deviation of: {p['n1']}, {p['n2']}, {p['n3']}, {p['n4']}, {p['n5']}.",
  {f'n{i}':('int',1,50) for i in range(1,6)},
  "s = sqrt( sum((x - mean)^2) / (n - 1) )", _sd_solve, "",
  steps=lambda p,v: [f"Mean = {fmt(sum(p[f'n{i}'] for i in range(1,6))/5)}",
                     "Compute squared deviations, sum them, divide by (n-1)=4, take the square root",
                     f"Answer: s = {fmt(v)}"],
  check=_sd_check, valid=lambda p: len(set(p[f'n{i}'] for i in range(1,6))) > 1, tags=['std-dev'])

# 11. slope of a line
T(B, "Coordinate Geometry", "easy",
  lambda p: f"Find the slope of the line through ({fmt(p['x1'])}, {fmt(p['y1'])}) and ({fmt(p['x2'])}, {fmt(p['y2'])}).",
  {'x1':('int',-9,9),'y1':('int',-9,9),'x2':('int',-9,9),'y2':('int',-9,9)},
  "m = (y2 - y1) / (x2 - x1)", lambda p: (p['y2']-p['y1'])/(p['x2']-p['x1']), "",
  subst=lambda p,v: f"m = ({fmt(p['y2'])} - {fmt(p['y1'])}) / ({fmt(p['x2'])} - {fmt(p['x1'])})",
  valid=lambda p: p['x2'] != p['x1'], tags=['slope','line'])

# 12. distance between two points
T(B, "Coordinate Geometry", "easy",
  lambda p: f"Find the distance between the points ({fmt(p['x1'])}, {fmt(p['y1'])}) and ({fmt(p['x2'])}, {fmt(p['y2'])}).",
  {'x1':('int',-9,9),'y1':('int',-9,9),'x2':('int',-9,9),'y2':('int',-9,9)},
  "d = sqrt((x2-x1)^2 + (y2-y1)^2)", lambda p: math.hypot(p['x2']-p['x1'], p['y2']-p['y1']), "units",
  subst=lambda p,v: f"d = sqrt(({fmt(p['x2']-p['x1'])})^2 + ({fmt(p['y2']-p['y1'])})^2)",
  valid=lambda p: (p['x1'],p['y1']) != (p['x2'],p['y2']), tags=['distance']),

# 13. triangle area from coordinates (shoelace)
T(B, "Coordinate Geometry", "medium",
  lambda p: f"Find the area of the triangle with vertices ({fmt(p['x1'])},{fmt(p['y1'])}), ({fmt(p['x2'])},{fmt(p['y2'])}), ({fmt(p['x3'])},{fmt(p['y3'])}).",
  {'x1':('int',-8,8),'y1':('int',-8,8),'x2':('int',-8,8),'y2':('int',-8,8),'x3':('int',-8,8),'y3':('int',-8,8)},
  "Area = 0.5 |x1(y2-y3) + x2(y3-y1) + x3(y1-y2)|",
  lambda p: 0.5*abs(p['x1']*(p['y2']-p['y3']) + p['x2']*(p['y3']-p['y1']) + p['x3']*(p['y1']-p['y2'])), "sq units",
  steps=lambda p,v: ["Apply the shoelace formula:",
                     "Area = 0.5 |x1(y2-y3) + x2(y3-y1) + x3(y1-y2)|",
                     f"Answer: {fmt(v)} sq units"],
  valid=lambda p: abs(p['x1']*(p['y2']-p['y3']) + p['x2']*(p['y3']-p['y1']) + p['x3']*(p['y1']-p['y2'])) > 0,
  tags=['area','triangle'])

# 14. combinations nCr
T(B, "Combinatorics", "easy",
  lambda p: f"Evaluate the number of combinations C({p['n']}, {p['r']}).",
  {'n':('int',5,20),'r':('int',1,19)},
  "C(n, r) = n! / (r! (n - r)!)", lambda p: math.comb(p['n'], p['r']), "",
  subst=lambda p,v: f"C({p['n']}, {p['r']}) = {p['n']}! / ({p['r']}! * {p['n']-p['r']}!)",
  check=lambda p,v: math.comb(p['n'],p['r']) == v, valid=lambda p: p['r'] <= p['n'], tags=['combinations'])

# 15. permutations nPr
T(B, "Combinatorics", "easy",
  lambda p: f"Evaluate the number of permutations P({p['n']}, {p['r']}).",
  {'n':('int',5,15),'r':('int',1,10)},
  "P(n, r) = n! / (n - r)!", lambda p: math.perm(p['n'], p['r']), "",
  subst=lambda p,v: f"P({p['n']}, {p['r']}) = {p['n']}! / {p['n']-p['r']}!",
  check=lambda p,v: math.perm(p['n'],p['r']) == v, valid=lambda p: p['r'] <= p['n'], tags=['permutations'])

# 16. AP nth term
T(B, "Sequences", "easy",
  lambda p: f"Find the {p['n']}th term of an arithmetic progression with first term {fmt(p['a'])} and common difference {fmt(p['d'])}.",
  {'a':('int',-20,20),'d':('int',-9,9),'n':('int',5,40)},
  "a_n = a + (n - 1) d", lambda p: p['a'] + (p['n']-1)*p['d'], "",
  subst=lambda p,v: f"a_n = {fmt(p['a'])} + ({p['n']} - 1)*{fmt(p['d'])}", tags=['AP'])

# 17. AP sum of n terms
T(B, "Sequences", "medium",
  lambda p: f"Find the sum of the first {p['n']} terms of an AP with first term {fmt(p['a'])} and common difference {fmt(p['d'])}.",
  {'a':('int',-15,15),'d':('int',-8,8),'n':('int',5,40)},
  "S_n = n/2 [2a + (n - 1) d]", lambda p: p['n']/2*(2*p['a'] + (p['n']-1)*p['d']), "",
  subst=lambda p,v: f"S_n = {p['n']}/2 [2*{fmt(p['a'])} + ({p['n']}-1)*{fmt(p['d'])}]", tags=['AP','series'])

# 18. GP nth term
T(B, "Sequences", "medium",
  lambda p: f"Find the {p['n']}th term of a geometric progression with first term {fmt(p['a'])} and common ratio {fmt(p['r'])}.",
  {'a':('int',1,9),'r':('int',2,4),'n':('int',3,8)},
  "a_n = a r^(n-1)", lambda p: p['a']*p['r']**(p['n']-1), "",
  subst=lambda p,v: f"a_n = {fmt(p['a'])} * {fmt(p['r'])}^({p['n']}-1)", tags=['GP'])

# 19. simple interest
T(B, "Engineering Economics", "easy",
  lambda p: f"Find the simple interest on a principal of {p['P']} at {fmt(p['R'])}% per annum for {p['Tt']} years.",
  {'P':('int',1000,50000,500),'R':('float',4,15,1),'Tt':('int',1,10)},
  "SI = P R T / 100", lambda p: p['P']*p['R']*p['Tt']/100, "currency units",
  subst=lambda p,v: f"SI = {p['P']} * {fmt(p['R'])} * {p['Tt']} / 100", tags=['simple-interest'])

# 20. compound interest amount
T(B, "Engineering Economics", "medium",
  lambda p: f"Find the amount when {p['P']} is invested at {fmt(p['R'])}% per annum compounded annually for {p['Tt']} years.",
  {'P':('int',1000,40000,500),'R':('float',4,12,1),'Tt':('int',2,6)},
  "A = P (1 + R/100)^T", lambda p: p['P']*(1 + p['R']/100)**p['Tt'], "currency units",
  subst=lambda p,v: f"A = {p['P']} * (1 + {fmt(p['R'])}/100)^{p['Tt']}", tags=['compound-interest'])

# 21. dot product
T(B, "Vectors", "easy",
  lambda p: f"Find the dot product of vectors ({fmt(p['a1'])}, {fmt(p['a2'])}, {fmt(p['a3'])}) and ({fmt(p['b1'])}, {fmt(p['b2'])}, {fmt(p['b3'])}).",
  {'a1':('int',-8,8),'a2':('int',-8,8),'a3':('int',-8,8),'b1':('int',-8,8),'b2':('int',-8,8),'b3':('int',-8,8)},
  "a . b = a1 b1 + a2 b2 + a3 b3",
  lambda p: p['a1']*p['b1'] + p['a2']*p['b2'] + p['a3']*p['b3'], "",
  subst=lambda p,v: f"= ({fmt(p['a1'])})({fmt(p['b1'])}) + ({fmt(p['a2'])})({fmt(p['b2'])}) + ({fmt(p['a3'])})({fmt(p['b3'])})",
  tags=['dot-product'])

# 22. magnitude of cross product
def _cross_solve(p):
    ax,ay,az,bx,by,bz = (p[k] for k in ['a1','a2','a3','b1','b2','b3'])
    cx,cy,cz = ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx
    return math.sqrt(cx*cx + cy*cy + cz*cz)
def _cross_check(p, v):
    import numpy as np
    a = np.array([p['a1'],p['a2'],p['a3']]); b = np.array([p['b1'],p['b2'],p['b3']])
    return close(float(np.linalg.norm(np.cross(a,b))), v, ab=1e-4)
T(B, "Vectors", "medium",
  lambda p: f"Find the magnitude of the cross product of ({fmt(p['a1'])}, {fmt(p['a2'])}, {fmt(p['a3'])}) and ({fmt(p['b1'])}, {fmt(p['b2'])}, {fmt(p['b3'])}).",
  {'a1':('int',-6,6),'a2':('int',-6,6),'a3':('int',-6,6),'b1':('int',-6,6),'b2':('int',-6,6),'b3':('int',-6,6)},
  "|a x b| = sqrt(cx^2 + cy^2 + cz^2)", _cross_solve, "",
  steps=lambda p,v: ["Cross product c = a x b, then take its magnitude",
                     f"Answer: {fmt(v)}"],
  check=_cross_check,
  valid=lambda p: _cross_solve(p) > 1e-6, tags=['cross-product'])

# 23. angle between vectors (degrees)
def _ang_solve(p):
    a=[p['a1'],p['a2'],p['a3']]; b=[p['b1'],p['b2'],p['b3']]
    dot=sum(x*y for x,y in zip(a,b))
    na=math.sqrt(sum(x*x for x in a)); nb=math.sqrt(sum(x*x for x in b))
    return math.degrees(math.acos(max(-1,min(1,dot/(na*nb)))))
T(B, "Vectors", "hard",
  lambda p: f"Find the angle (in degrees) between ({fmt(p['a1'])}, {fmt(p['a2'])}, {fmt(p['a3'])}) and ({fmt(p['b1'])}, {fmt(p['b2'])}, {fmt(p['b3'])}).",
  {'a1':('int',-6,6),'a2':('int',-6,6),'a3':('int',-6,6),'b1':('int',-6,6),'b2':('int',-6,6),'b3':('int',-6,6)},
  "cos(theta) = (a . b) / (|a| |b|)", _ang_solve, "degrees",
  steps=lambda p,v: ["Compute a.b, |a| and |b|, then theta = arccos(a.b/(|a||b|))",
                     f"Answer: {fmt(v)} degrees"],
  valid=lambda p: any(p[k] for k in ['a1','a2','a3']) and any(p[k] for k in ['b1','b2','b3']),
  tags=['angle','vectors'])

# 24. magnitude of a complex number
T(B, "Complex Numbers", "easy",
  lambda p: f"Find the modulus of the complex number {fmt(p['a'])} + {fmt(p['b'])}i.",
  {'a':('int',-12,12),'b':('int',-12,12)},
  "|z| = sqrt(a^2 + b^2)", lambda p: math.hypot(p['a'], p['b']), "",
  subst=lambda p,v: f"|z| = sqrt(({fmt(p['a'])})^2 + ({fmt(p['b'])})^2)",
  valid=lambda p: p['a'] or p['b'], tags=['complex','modulus'])

# 25. argument of a complex number (degrees)
T(B, "Complex Numbers", "medium",
  lambda p: f"Find the argument (in degrees) of the complex number {fmt(p['a'])} + {fmt(p['b'])}i.",
  {'a':('int',-12,12),'b':('int',-12,12)},
  "arg(z) = atan2(b, a)", lambda p: math.degrees(math.atan2(p['b'], p['a'])), "degrees",
  subst=lambda p,v: f"arg = atan2({fmt(p['b'])}, {fmt(p['a'])})",
  valid=lambda p: p['a'] or p['b'], tags=['complex','argument'])

# 26. evaluate polynomial at a point
T(B, "Algebra", "easy",
  lambda p: f"Evaluate f(x) = {poly_str([p['a'],p['b'],p['c'],p['d']])} at x = {fmt(p['x0'])}.",
  {'a':('int',-5,5),'b':('int',-7,7),'c':('int',-9,9),'d':('int',-9,9),'x0':('int',-5,5)},
  "f(x0) = a x0^3 + b x0^2 + c x0 + d",
  lambda p: p['a']*p['x0']**3 + p['b']*p['x0']**2 + p['c']*p['x0'] + p['d'], "",
  subst=lambda p,v: f"f({fmt(p['x0'])}) = {fmt(p['a'])}({fmt(p['x0'])})^3 + {fmt(p['b'])}({fmt(p['x0'])})^2 + {fmt(p['c'])}({fmt(p['x0'])}) + {fmt(p['d'])}",
  valid=lambda p: p['a'] != 0, tags=['evaluate','polynomial'])

# 27. Newton-Raphson one iteration for sqrt(N)
T(B, "Numerical Methods", "medium",
  lambda p: f"Using Newton-Raphson for f(x)=x^2-{p['N']} with initial guess x0={fmt(p['x0'])}, find x1 (one iteration).",
  {'N':('int',10,200),'x0':('int',2,15)},
  "x1 = x0 - (x0^2 - N)/(2 x0)", lambda p: p['x0'] - (p['x0']**2 - p['N'])/(2*p['x0']), "",
  subst=lambda p,v: f"x1 = {fmt(p['x0'])} - (({fmt(p['x0'])})^2 - {p['N']})/(2*{fmt(p['x0'])})",
  tags=['newton-raphson'])

# 28. trapezoidal rule with 4 intervals
def _trap_solve(p):
    return p['h']*(p['y0']/2 + p['y1'] + p['y2'] + p['y3'] + p['y4']/2)
T(B, "Numerical Methods", "medium",
  lambda p: f"Using the trapezoidal rule with step h={fmt(p['h'])} and ordinates {fmt(p['y0'])}, {fmt(p['y1'])}, {fmt(p['y2'])}, {fmt(p['y3'])}, {fmt(p['y4'])}, estimate the integral.",
  {'h':('float',0.5,2,1),'y0':('int',0,20),'y1':('int',0,20),'y2':('int',0,20),'y3':('int',0,20),'y4':('int',0,20)},
  "I = h [ y0/2 + y1 + y2 + y3 + y4/2 ]", _trap_solve, "",
  subst=lambda p,v: f"I = {fmt(p['h'])} [ {fmt(p['y0'])}/2 + {fmt(p['y1'])} + {fmt(p['y2'])} + {fmt(p['y3'])} + {fmt(p['y4'])}/2 ]",
  tags=['trapezoidal'])

# 29. GCD of two integers
T(B, "Number Theory", "easy",
  lambda p: f"Find the greatest common divisor (GCD) of {p['a']} and {p['b']}.",
  {'a':('int',12,600),'b':('int',12,600)},
  "GCD via the Euclidean algorithm", lambda p: math.gcd(p['a'], p['b']), "",
  steps=lambda p,v: [f"Apply the Euclidean algorithm to {p['a']} and {p['b']}",
                     f"Answer: GCD = {fmt(v)}"],
  check=lambda p,v: math.gcd(p['a'],p['b']) == v, tags=['gcd'])

# 30. LCM of two integers
T(B, "Number Theory", "easy",
  lambda p: f"Find the least common multiple (LCM) of {p['a']} and {p['b']}.",
  {'a':('int',4,80),'b':('int',4,80)},
  "LCM(a, b) = a b / GCD(a, b)", lambda p: p['a']*p['b']//math.gcd(p['a'], p['b']), "",
  subst=lambda p,v: f"LCM = {p['a']}*{p['b']} / {math.gcd(p['a'],p['b'])}",
  check=lambda p,v: (p['a']*p['b']//math.gcd(p['a'],p['b'])) == v, tags=['lcm'])
