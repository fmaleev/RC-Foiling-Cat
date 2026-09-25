"""Bow-volume study for the 1 m build-first hull: pitchpole margin vs drag vs skin weight.

Each variant changes only the forward stations (x >= 750 mm). The boat mass changes by the hull skin
area difference (0.8 mm PETG, both hulls); everything else is unchanged.
"""
import json, math, os, sys, copy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vpp, stability, pitchpole

BASE = [(0, 26.0, -28.0, 58.0), (150, 36.0, -40.0, 60.0), (350, 40.0, -45.0, 62.0), (550, 39.5, -44.0, 64.0),
        (750, 33.0, -37.0, 66.0), (880, 22.0, -26.0, 68.0), (960, 10.0, -12.0, 70.0), (1000, 2.5, 5.0, 72.0)]
VARIANTS = {
    'baseline': {},
    'A: +8 mm bow freeboard': {750: (33.0, -37.0, 70.0), 880: (22.0, -26.0, 75.0), 960: (10.0, -12.0, 78.0), 1000: (2.5, 5.0, 80.0)},
    'B: A + fuller topsides': {750: (35.0, -37.0, 70.0), 880: (26.0, -26.0, 76.0), 960: (14.0, -12.0, 79.0), 1000: (4.0, 5.0, 81.0)},
    'C: B + reserve at stem': {750: (36.0, -37.0, 72.0), 880: (28.0, -26.0, 80.0), 960: (17.0, -12.0, 84.0), 1000: (6.0, 5.0, 86.0)},
}


def stations(mod):
    return [(x,) + mod.get(x, (hw, zb, zt)) for x, hw, zb, zt in BASE]


def skin_area():
    tot = 0.0
    n = 400
    for i in range(n):
        x = (i + .5) / n * vpp.L_HULL
        a, zc, b, _ = vpp.section(x)
        per = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))   # Ramanujan
        tot += per * vpp.L_HULL / n
    return 2 * tot   # both hulls, m2


def evaluate(name, mod, cad0, area0):
    vpp.configure(stations=stations(mod))
    area = skin_area()
    dm = (area - area0) * 0.8e-3 * 1270 * 1000       # g
    cad = copy.deepcopy(cad0)
    cad['displacement']['mass_g'] += dm
    b = vpp.Boat('displacement', cad)
    stab = {}
    vol = b.M / vpp.RHO
    zg = cad['displacement']['vcg_mm'] / 1000; xg = b.lcg / 1000
    for hulls in (2, 1):
        pc = stability.pitch_curve(vol, xg, zg, hulls)
        before = [r for r in pc if r['bow_freeboard'] > 0]
        m = max(before, key=lambda r: r['GZL'])
        stab[f'pitch_{hulls}hull'] = dict(RM_L_max_Nm=b.W * m['GZL'], at_deg=m['theta'])
    drag = {V: round(b.resistance(V, 0.0)[0], 3) for V in (1.0, 2.0, 3.0)}
    pp = pitchpole.limits(b, stab)
    return dict(mass_change_g=round(dm, 1), RM_L_2hull=round(stab['pitch_2hull']['RM_L_max_Nm'], 2), RM_L_1hull=round(stab['pitch_1hull']['RM_L_max_Nm'], 2),
                drag_N=drag, pitchpole_kn={k: v['pitchpole_tws_kn'] for k, v in pp.items()},
                speed_8kn_tws90=b.solve(8 * 0.5144, 90)['V'])


if __name__ == '__main__':
    cad0 = json.load(open(os.path.join(HERE, 'cad_data.json')))
    vpp.configure(stations=BASE)
    area0 = skin_area()
    out = {}
    for name, mod in VARIANTS.items():
        out[name] = evaluate(name, mod, cad0, area0)
        print(name, out[name], flush=True)
    json.dump(out, open(os.path.join(HERE, 'hull_variants_results.json'), 'w'), indent=1)
