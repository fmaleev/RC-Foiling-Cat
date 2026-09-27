"""Design-rule checks, re-run after every analysis pass. Plain Python: reads the analysis results, the rig model and the
constants of the Fusion scripts (without importing adsk). The CAD interference sweep itself is cad_scripts/clearance.py.
Writes design_checks.json and exits non-zero if a rule fails."""
import ast, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
ADDIN = os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim')
sys.path.insert(0, HERE)
sys.path.insert(0, ADDIN)
import vpp
import rig_model

load = lambda *p: json.load(open(os.path.join(ROOT, *p)))
CAD, CTL, RH, SEN = load('analysis', 'cad_data.json'), load('analysis', 'control_results.json'), \
    load('analysis', 'ride_height_results.json'), load('analysis', 'sensitivity_results.json')
VPP, MINI = load('analysis', 'vpp_results.json'), load('mini', 'mini_results.json')
STR = load('analysis', 'structure_results.json')
DRUM_H = {'full': (8.0, 6.0), 'mini': (10.4,)}     # winch drum heights in the CAD (traveler, jib / stepped drum), mm
LID_UNDERSIDE = {'full': 120.05, 'mini': 94.0}      # mm, measured in the CAD
FLOOR_TOP = {'full': 71.2, 'mini': 45.0}            # mm, measured in the CAD by servo_mounts.floor_top


def consts(name, names):
    """Literal constants from a Fusion script, evaluated without importing it."""
    path = os.path.join(ROOT, 'cad_scripts', name)
    out = {}
    for node in ast.parse(open(path).read()).body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            val = lambda n: eval(compile(ast.Expression(n), path, 'eval'), {'__builtins__': {}, 'dict': dict})
            if isinstance(t, ast.Name) and t.id in names:
                out[t.id] = val(node.value)
            elif isinstance(t, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for tt, vv in zip(t.elts, node.value.elts):
                    if isinstance(tt, ast.Name) and tt.id in names:
                        out[tt.id] = val(vv)
    return out


def one_hull_reserve(cfg):
    vpp.configure()
    b = vpp.Boat(cfg, CAD)
    return vpp.integrate(lambda x: math.pi * vpp.section(x)[0] * vpp.section(x)[2], 0, 1, 400) * 1000 / b.M


rows = []
def check(rule, value, limit, ok, unit=''):
    rows.append(dict(rule=rule, value=round(value, 2), limit=limit, unit=unit, ok=bool(ok)))


# hydrostatics and stability
check('one hull floats the 1 m build-first boat', one_hull_reserve('displacement'), '>= 2', one_hull_reserve('displacement') >= 2, 'x weight')
check('one hull floats the 1 m foiling boat', one_hull_reserve('foiling'), '>= 2', one_hull_reserve('foiling') >= 2, 'x weight')
check('one hull floats the mini', MINI['statics']['one_hull_reserve'], '>= 2', MINI['statics']['one_hull_reserve'] >= 2, 'x weight')
hv = VPP['hull_volume_check']['error_pct']
check('station-table hull volume vs CAD loft', abs(hv), '<= 1', abs(hv) <= 1.0, '%')
# control
throw = CTL['rudder_throw_deg']
for cfg in ('displacement', 'foiling'):
    need = max(r['rudder_angle_deg'] for r in CTL[cfg])
    check(f'rudder angle needed, 1 m {cfg}', need, f'<= {throw / 2:g} (half the throw)', need <= throw / 2, 'deg')
need = max(r['rudder_angle_deg'] for r in MINI['rudder'])
check('rudder angle needed, mini', need, f"<= {MINI['rudder_throw_deg'] / 2:g}", need <= MINI['rudder_throw_deg'] / 2, 'deg')
for k, v in CTL['foil_pitch'].items():
    check(f'foil pitch static margin ({k})', v['static_margin_mm'], '> 0', v['static_margin_mm'] > 0, 'mm')
zmin = min(r['zeta'] for r in RH['rows'])
check('heave damping with wand-driven flaps', zmin, '>= 0.5', zmin >= 0.5 and all(r['within_travel'] for r in RH['rows']))
base = [s for s in SEN if s['scenario'] == 'baseline'][0]
check('take-off wind, beam reach', base['TWA90_takeoff_tws_kn'], '<= 8', base['TWA90_takeoff_tws_kn'] is not None and base['TWA90_takeoff_tws_kn'] <= 8, 'kn')

# rig against the v1.4 pod (1 m): the mainsheet must stay aft of the transom while the clew is over the pod,
# and the lid jib car must stay on the lid and under the boom
P = consts('pod_v14.py', {'AFT', 'HW', 'POD_BEAM', 'BEAM', 'BRACKET'})
rig_model.set_profile('full')
R = rig_model.RIG
worst_x, worst_car, worst_top = -1e9, 0.0, 0.0
for md in range(0, 41):
    for jd in range(5, 41, 5):
        hw = {h[0]: h[2] for h in rig_model.hardware(dict(main_deg=float(md), jib_deg=float(jd), tension=70.0))}
        clew = hw['Mainsheet'][0]
        if abs(clew[1]) < P['HW'] + 5:
            worst_x = max(worst_x, clew[0])
        car = hw['Jib Car']
        worst_car = max(worst_car, abs(car[2]), abs(car[3]))
        worst_top = max(worst_top, car[5])
check('clew over the pod stays aft of the transom', P['AFT'] - worst_x, '>= 5', P['AFT'] - worst_x >= 5, 'mm margin')
check('jib car stays on the lid', P['HW'] - worst_car, '>= 0', worst_car <= P['HW'], 'mm margin')
boom_under = R['boom_z'] - R['boom_r']
check('jib car under the boom', boom_under - worst_top, '> 0', worst_top < boom_under, 'mm margin')
# mainsheet over the pod beam: height of the sheet above the beam wherever it crosses the beam's x span
px, pz, pr = P['POD_BEAM']
gap = 1e9
for md in range(0, 41):
    hw = {h[0]: h[2] for h in rig_model.hardware(dict(main_deg=float(md), jib_deg=12.0, tension=70.0))}
    (x1, _, z1), (x0, _, z0) = hw['Mainsheet'][0], hw['Mainsheet'][1]
    for x in (px - pr, px + pr):
        if min(x0, x1) <= x <= max(x0, x1):
            gap = min(gap, z0 + (x - x0) / (x1 - x0) * (z1 - z0) - (pz + pr))
check('mainsheet clears the pod beam', gap if gap < 1e9 else 999, '>= 10', gap >= 10, 'mm')
bx, bz = P['BEAM']
clamp_top = bz + P['BRACKET']['r_out'] * math.sin(math.radians(P['BRACKET']['open_deg']))
check('servo bracket clamp under the traveler track', R['beam_top'] - clamp_top, '>= 1', R['beam_top'] - clamp_top >= 1, 'mm')

# structure (analysis/structure.py): worst case = sail loads at the heel limit plus the sheet servo at stall
for k in ('build_first_1m', 'foiling_1m', 'mini_600'):
    v = STR[k]
    check(f'mast buckling, {k}', v['buckling_safety']['servo_stall'], '>= 2', v['buckling_safety']['servo_stall'] >= 2, 'x load')
    worst = min(v[b]['safety_factor'] for b in ('front_beam', 'rear_beam', 'pod_beam') if b in v)
    check(f'crossbeam bending, {k}', worst, '>= 2', worst >= 2, 'x load')
    if 'daggerboard_joint' in v:
        dj = v['daggerboard_joint']['safety_factor']
        check('daggerboard joint (two-piece print)', dj, '>= 2', dj >= 2, 'x load')
    if 'traveler_car' in v:
        tc = v['traveler_car']['safety_factor']
        check(f'traveler car on its rail, {k}', tc, '>= 2', tc >= 2, 'x load')

# printing: every 1 m part must fit a 220 x 220 mm bed, lying on its smallest side, straight or diagonal (5 mm margin)
PL = json.load(open(os.path.join(ROOT, 'manual_1m', 'print_list_1m.json')))
need = {k: min(v['size_mm'][0], (v['size_mm'][0] + v['size_mm'][1]) / math.sqrt(2)) if v['size_mm'][1] <= 220 else 999 for k, v in PL.items()}
worst = max(need, key=need.get)
check(f'1 m print parts on a 220 mm bed (largest: {worst})', round(need[worst], 1), '<= 215', need[worst] <= 215, 'mm')

# servo fit (sizes from the manufacturers' drawings, as used in cad_scripts/servo_mounts.py)
S = consts('servo_mounts.py', {'STD', 'MICRO', 'CLEAR', 'LAYOUT'})
for kind in ('STD', 'MICRO'):
    g = S[kind]
    check(f'{kind.lower()} servo case between its rails', (g['gap'] - g['case'][0]) / 2, '>= 0.3', (g['gap'] - g['case'][0]) / 2 >= 0.3, 'mm per side')
for prof, L in S['LAYOUT'].items():
    top = FLOOR_TOP[prof] + S['CLEAR'] - L['well'] + S['STD']['case'][2] + max(DRUM_H[prof])
    check(f'winch drum under the lid ({prof})', LID_UNDERSIDE[prof] - top, '>= 3', LID_UNDERSIDE[prof] - top >= 3, 'mm')

json.dump(rows, open(os.path.join(HERE, 'design_checks.json'), 'w'), indent=1)
w = max(len(r['rule']) for r in rows)
for r in rows:
    print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['rule']:<{w}}  {r['value']:>8} {r['unit']:<12} limit {r['limit']}")
print(f"{sum(r['ok'] for r in rows)}/{len(rows)} rules pass")
sys.exit(0 if all(r['ok'] for r in rows) else 1)
