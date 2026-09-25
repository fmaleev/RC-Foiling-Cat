"""Writes pgfplots data files for the paper and poster from the analysis results."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'paper', 'data')
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim'))
import vpp, rig_model as rm


def dat(name, header, rows):
    with open(os.path.join(OUT, name), 'w') as f:
        f.write(' '.join(header) + '\n')
        for r in rows:
            f.write(' '.join(f'{v:.5g}' if isinstance(v, float) else str(v) for v in r) + '\n')


res = json.load(open(os.path.join(HERE, 'vpp_results.json')))
ctl = json.load(open(os.path.join(HERE, 'control_results.json')))
sens = json.load(open(os.path.join(HERE, 'sensitivity_results.json')))

for cfg in ('displacement', 'foiling'):
    dat(f'resistance_{cfg}.dat', ['V', 'R', 'fric', 'wave', 'app'],
        [(r['V'], r['R'], r.get('friction', 0.0), r.get('wave', 0.0), r.get('appendages', 0.0) if r['mode'] != 'foiling' else r['R'])
         for r in res['resistance'][cfg]])
    for twa, rows in res['vpp'][cfg].items():
        dat(f'vpp_{cfg}_{twa}.dat', ['tws', 'V', 'fly', 'dep'],
            [(x['tws_kn'], x['V'], 1 if x.get('mode') == 'foiling' else 0, 1 if x.get('depowered') else 0) for x in rows if x.get('mode') != '>vmax'])

dat('heave.dat', ['V', 'excess', 'dalpha'], [(h['V'], h['excess_pct'], h['main_foil_angle_change_needed_deg']) for h in ctl['foil_heave']])
for cfg in ('displacement', 'foiling'):
    for twa in (60, 90):
        dat(f'rudder_{cfg}_{twa}.dat', ['tws', 'angle'], [(x['tws_kn'], x['rudder_angle_deg']) for x in ctl[cfg] if x['twa'] == twa])

# body plan (half sections) of the 1 m hull
vpp.configure()
STATIONS_MM = vpp.STATIONS
rows = []
for x, hw, zb, zt in STATIONS_MM:
    zc, b = (zb + zt) / 2, (zt - zb) / 2
    side = 1 if x >= 500 else -1          # naval convention: forward sections on the right
    for k in range(41):
        th = math.pi * k / 40
        rows.append((x, side * hw * math.sin(th), zc - b * math.cos(th)))
    rows.append((x, 'nan', 'nan'))
dat('bodyplan.dat', ['x', 'y', 'z'], rows)
# side profile of the build-first boat: hull, appendages, rig
xs = [i * 5.0 for i in range(201)]
deck = [(x, vpp.ZT(x / 1000) * 1000) for x in xs]
keel = [(x, vpp.ZB(x / 1000) * 1000) for x in reversed(xs)]
dat('profile_hull.dat', ['x', 'z'], deck + keel + [deck[0]])
dat('profile_board.dat', ['x', 'z'], [(530, 75), (590, 75), (590, -250), (530, -250), (530, 75)])
dat('profile_rudder.dat', ['x', 'z'], [(-8, 26), (-53, 26), (-53, -200), (-8, -200), (-8, 26)])
dat('profile_pod.dat', ['x', 'z'], [(270, 70), (840, 70), (840, 122), (270, 122), (270, 70)])     # v1.4: transom at x = 270
# rudder-servo bracket: deck aft of the rear beam and a 240 deg clamp around the beam, open at the top (cad_scripts/pod_v14.py)
clamp = [(180 + 11.2 * math.cos(math.radians(a)), 62 + 11.2 * math.sin(math.radians(a))) for a in range(150, 391, 10)]
clamp += [(180 + 8.2 * math.cos(math.radians(a)), 62 + 8.2 * math.sin(math.radians(a))) for a in range(390, 149, -10)]
dat('profile_tail.dat', ['x', 'z'], [(118, 46.5), (188, 46.5), (188, 50.5), (118, 50.5), (118, 46.5), ('nan', 'nan')] + clamp + [clamp[0]])
dat('profile_cover.dat', ['x', 'z'], [(121, 50.5), (164, 50.5), (164, 96), (121, 96), (121, 50.5)])
dat('profile_beams.dat', ['x', 'z'], [(bx + r * math.cos(2 * math.pi * k / 24), bz + r * math.sin(2 * math.pi * k / 24)) if k < 25 else ('nan', 'nan')
                                     for bx, bz, r in ((180, 62, 8), (620, 62, 8), (350, 65, 5)) for k in range(26)])

# Wigley validation curve
L, B, T = 1.0, 0.1, 0.0625
hwf = lambda x, z: (B / 2) * (1 - (2 * (x - 0.5)) ** 2) * (1 - (z / T) ** 2) if -T <= z <= 0 else 0.0
S = 0.1488
wig = []
for i in range(21):
    fn = 0.2 + 0.02 * i
    U = fn * math.sqrt(9.81)
    rw = vpp.michell(U, 0.0, catamaran=False, nx=120, nz=16, nu=3000, halfwidth=hwf, zbot=-T)
    wig.append((fn, rw / (0.5 * 1000 * U * U * S) * 1e3))
dat('wigley.dat', ['Fn', 'Cw'], wig)

# sail plan outlines (full rig, flat)
rm.set_profile('full')
c = dict(jib_deg=0.0, main_deg=0.0, tension=100.0)
ms = rm.main_sections(c)
main = [(p[0][0], z) for z, p in ms] + [(p[-1][0], z) for z, p in reversed(ms)]
js = rm.jib_sections(c)
jib = [(p[0][0], z) for z, p in js] + [(p[-1][0], z) for z, p in reversed(js)]
dat('sail_main.dat', ['x', 'z'], main + [main[0]])
dat('sail_jib.dat', ['x', 'z'], jib + [jib[0]])
dat('sensitivity.dat', ['scenario', 'vto', 'tws60', 'tws90'],
    [(s['scenario'].replace(' ', '~').replace('%', 'pct'), s['takeoff_speed_ms'], s['TWA60_takeoff_tws_kn'], s['TWA90_takeoff_tws_kn']) for s in sens])
st = json.load(open(os.path.join(HERE, 'stability_results.json')))
for k in st:
    dat(f'gz_{k}.dat', ['deg', 'gz'], [(float(d), float(g)) for d, g in st[k]['gz']])
print('wrote', sorted(os.listdir(OUT)))
print('wigley', [(round(a, 2), round(b, 2)) for a, b in wig])
