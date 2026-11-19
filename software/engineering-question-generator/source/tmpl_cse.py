import math
from core import T, fmt
def close(a,b,rel=1e-3,ab=1e-6): return abs(a-b)<=max(ab,rel*max(abs(a),abs(b)))
B="Computer Science & Engineering"

# ---- Number systems ----
T(B,"Number Systems","easy",
  lambda p:f"Convert the decimal number {p['n']} to binary.",
  {'n':('int',5,255)},
  "Repeatedly divide by 2 and read remainders bottom-up",
  lambda p: format(p['n'],'b'),"",
  steps=lambda p,v:[f"Divide {p['n']} by 2 repeatedly, recording remainders",
                    f"Reading remainders in reverse gives {v}",
                    f"Answer: {v} (binary)"],
  check=lambda p,v: int(v,2)==p['n'], tags=['dec-to-bin'])

T(B,"Number Systems","easy",
  lambda p:f"Convert the decimal number {p['n']} to hexadecimal (uppercase).",
  {'n':('int',16,4095)},
  "Repeatedly divide by 16 and read remainders bottom-up",
  lambda p: format(p['n'],'X'),"",
  steps=lambda p,v:[f"Divide {p['n']} by 16 repeatedly, recording remainders",
                    f"Answer: {v} (hex)"],
  check=lambda p,v: int(v,16)==p['n'], tags=['dec-to-hex'])

T(B,"Number Systems","easy",
  lambda p:f"Convert the {p['k']}-bit binary number {format(p['n'],'0'+str(p['k'])+'b')} to decimal.",
  {'n':('int',1,255),'k':('choice',[8])},
  "Sum each bit times its positional weight (2^i)",
  lambda p: p['n'],"",
  steps=lambda p,v:[f"Binary {format(p['n'],'08b')} = sum of bit-weights",
                    f"Answer: {v} (decimal)"],
  check=lambda p,v: v==p['n'], tags=['bin-to-dec'])

T(B,"Number Systems","medium",
  lambda p:f"Compute the Hamming distance between the 8-bit words {format(p['a'],'08b')} and {format(p['b'],'08b')}.",
  {'a':('int',0,255),'b':('int',0,255)},
  "Hamming distance = number of differing bit positions",
  lambda p: bin(p['a']^p['b']).count('1'),"",
  steps=lambda p,v:[f"XOR: {format(p['a']^p['b'],'08b')}",
                    f"Count of 1s = {v}", f"Answer: {v}"],
  check=lambda p,v: v==bin(p['a']^p['b']).count('1'), valid=lambda p:p['a']!=p['b'], tags=['hamming-distance'])

# ---- Networking ----
T(B,"Computer Networks","medium",
  lambda p:f"An IPv4 subnet uses a /{p['prefix']} prefix. How many usable host addresses does it provide?",
  {'prefix':('int',20,30)},
  "hosts = 2^(32 - prefix) - 2",
  lambda p: 2**(32-p['prefix'])-2,"",
  subst=lambda p,v:f"hosts = 2^(32 - {p['prefix']}) - 2",
  check=lambda p,v: v==2**(32-p['prefix'])-2, tags=['subnetting'])

T(B,"Computer Networks","easy",
  lambda p:f"A file of {p['S']} megabits is sent over a link of {p['B']} Mbps. Find the transmission time in seconds.",
  {'S':('int',10,1000,10),'B':('int',1,100)},
  "t = size / bandwidth", lambda p: p['S']/p['B'],"s",
  subst=lambda p,v:f"t = {p['S']} / {p['B']}", tags=['transmission-time'])

T(B,"Computer Networks","medium",
  lambda p:f"A link has bandwidth {p['B']} Mbps and round-trip time {p['R']} ms. Find the bandwidth-delay product in kilobits.",
  {'B':('int',1,100),'R':('int',10,200,10)},
  "BDP = bandwidth * RTT",
  lambda p: p['B']*1e6*p['R']*1e-3/1000,"kilobits",
  subst=lambda p,v:f"BDP = {p['B']}e6 * {p['R']}e-3 bits = {fmt(v)} kb", tags=['bandwidth-delay'])

T(B,"Computer Networks","hard",
  lambda p:f"A channel has bandwidth {p['B']} kHz. Using Nyquist's theorem with {p['M']} signal levels, find the maximum data rate in kbps (noiseless).",
  {'B':('int',3,20),'M':('choice',[2,4,8,16])},
  "C = 2 B log2(M)",
  lambda p: 2*p['B']*math.log2(p['M']),"kbps",
  subst=lambda p,v:f"C = 2*{p['B']}*log2({p['M']})", tags=['nyquist-capacity'])

T(B,"Computer Networks","hard",
  lambda p:f"A channel of bandwidth {p['B']} kHz has a signal-to-noise ratio of {p['SNR']} (linear). Using Shannon's theorem, find the channel capacity in kbps.",
  {'B':('int',3,20),'SNR':('choice',[7,15,31,63,255])},
  "C = B log2(1 + SNR)",
  lambda p: p['B']*math.log2(1+p['SNR']),"kbps",
  subst=lambda p,v:f"C = {p['B']}*log2(1 + {p['SNR']})", tags=['shannon-capacity'])

# ---- Computer Organization ----
T(B,"Computer Organization","medium",
  lambda p:f"A memory has {p['N']} addressable locations. How many address bits are required?",
  {'N':('choice',[256,512,1024,2048,4096,8192,16384,65536])},
  "bits = log2(N)", lambda p: int(round(math.log2(p['N']))),"bits",
  subst=lambda p,v:f"bits = log2({p['N']})",
  check=lambda p,v: 2**v==p['N'], tags=['address-bits'])

T(B,"Computer Organization","hard",
  lambda p:f"A cache has a hit ratio of {fmt(p['h'])}, cache access time {p['tc']} ns and main-memory access time {p['tm']} ns. Find the effective (average) memory access time in ns.",
  {'h':('float',0.80,0.98,2),'tc':('int',1,10),'tm':('int',50,200,10)},
  "EAT = h * tc + (1 - h) * tm",
  lambda p: p['h']*p['tc']+(1-p['h'])*p['tm'],"ns",
  subst=lambda p,v:f"EAT = {fmt(p['h'])}*{p['tc']} + (1 - {fmt(p['h'])})*{p['tm']}", tags=['effective-access-time'])

T(B,"Computer Organization","medium",
  lambda p:f"A disk rotates at {p['rpm']} rpm. Find the average rotational latency in milliseconds.",
  {'rpm':('choice',[5400,7200,10000,15000])},
  "avg latency = 0.5 * (60 / rpm) * 1000 ms",
  lambda p: 0.5*60/p['rpm']*1000,"ms",
  subst=lambda p,v:f"latency = 0.5 * 60000 / {p['rpm']}", tags=['rotational-latency'])

# ---- Algorithms ----
T(B,"Algorithms","medium",
  lambda p:f"In the worst case, how many comparisons does binary search make on a sorted array of {p['n']} elements?",
  {'n':('int',10,1000000)},
  "comparisons = floor(log2(n)) + 1",
  lambda p: int(math.floor(math.log2(p['n'])))+1,"",
  subst=lambda p,v:f"floor(log2({p['n']})) + 1", tags=['binary-search'])

T(B,"Algorithms","medium",
  lambda p:f"An O(n^2) algorithm performs c*n^2 basic operations. If c = 1 and n = {p['n']}, how many operations are performed?",
  {'n':('int',10,3000,10)},
  "operations = n^2", lambda p: p['n']**2,"",
  subst=lambda p,v:f"= ({p['n']})^2", tags=['complexity'])

T(B,"Operating Systems","hard",
  lambda p:f"A program is {p['f']}% parallelisable and run on {p['N']} processors. Using Amdahl's law, find the maximum speedup.",
  {'f':('int',50,95,5),'N':('choice',[2,4,8,16,32])},
  "S = 1 / ((1 - f) + f/N)",
  lambda p: 1/((1-p['f']/100)+(p['f']/100)/p['N']),"x",
  steps=lambda p,v:[f"Parallel fraction f = {p['f']/100}",
                    f"S = 1 / ((1 - {p['f']/100}) + {p['f']/100}/{p['N']})",
                    f"Answer: {fmt(v)}x speedup"], tags=['amdahl'])

T(B,"Operating Systems","medium",
  lambda p:f"A demand-paging system has page-fault rate {fmt(p['pf'])}, memory access time {p['ma']} ns and page-fault service time {p['ps']} ms. Find the effective access time in microseconds.",
  {'pf':('float',0.001,0.02,3),'ma':('int',80,200,10),'ps':('int',3,10)},
  "EAT = (1 - pf) * ma + pf * (page-fault service time)",
  lambda p: ((1-p['pf'])*p['ma'] + p['pf']*(p['ps']*1e6))/1000,"microseconds",
  steps=lambda p,v:[f"Service time = {p['ps']} ms = {p['ps']*1e6} ns",
                    f"EAT = (1 - {fmt(p['pf'])})*{p['ma']} + {fmt(p['pf'])}*{p['ps']*1e6} ns",
                    f"Answer: {fmt(v)} microseconds"], tags=['page-fault','EAT'])

# ---- Digital Logic ----
T(B,"Digital Logic","medium",
  lambda p:f"How many distinct Boolean input combinations exist for a logic function of {p['n']} variables?",
  {'n':('int',2,10)},
  "combinations = 2^n", lambda p: 2**p['n'],"",
  subst=lambda p,v:f"= 2^{p['n']}", tags=['truth-table'])

T(B,"Digital Logic","medium",
  lambda p:f"A digital-to-analog converter has {p['n']} bits and a full-scale output of {p['Vfs']} V. Find its resolution (voltage per step) in mV.",
  {'n':('int',6,12),'Vfs':('choice',[5,10])},
  "resolution = Vfs / (2^n - 1)",
  lambda p: p['Vfs']/(2**p['n']-1)*1000,"mV",
  subst=lambda p,v:f"resolution = {p['Vfs']} / (2^{p['n']} - 1)", tags=['DAC','resolution'])

T(B,"Data Communication","medium",
  lambda p:f"A modem transmits at {p['baud']} baud using {p['M']}-level signalling. Find the bit rate in bps.",
  {'baud':('int',600,4800,300),'M':('choice',[2,4,8,16])},
  "bit rate = baud * log2(M)",
  lambda p: p['baud']*math.log2(p['M']),"bps",
  subst=lambda p,v:f"bit rate = {p['baud']} * log2({p['M']})", tags=['baud','bit-rate'])
