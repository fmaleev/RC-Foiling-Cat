"""Foil stability and sizing test for the 1 m foiling version. Run after the analysis pipeline (reads its results).

Stability
- Pitch: static margin of the main-foil / elevator pair (control.py, two elevator-efficiency assumptions).
- Heave, fixed foils: stiffness k = 0 (neutral), confirmed by a time-domain run.
- Heave and pitch together (pitch_heave.py, 2 degrees of freedom): every mode stable across the flying range.
- Heave, wand-driven flaps: damping ratio over the flying range (ride_height.py), plus a time-domain test:
  m h'' + c h' + k h = 0 from a 20 mm height disturbance, RK4, at four speeds across the flying range.
Flying trim (vpp.Boat.fly_trim: heave and pitch with the sail drive's bow-down couple)
- The flying range (take-off to the top of the range) covers the 12 kn beam-reach speed with a 5 % margin, also with the
  couple halved or 1.5 times larger (sensitivity.py).
- Over the flying range up to that speed: elevator and main foil at least half a chord deep, at least 30 mm of rudder
  in the water, hull at least 50 mm clear, flaps within +-15 deg.
Sizing
- Take-off speed and take-off wind; Reynolds numbers; submergence at the design ride height (>= 1 chord).
- Structure: the largest main-foil (and elevator) flight load on one foil under 2 g, CFRP E = 70 GPa, strength 300 MPa (assumed).
Writes foil_checks.json and exits non-zero if a rule fails.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vpp

load = lambda n: json.load(open(os.path.join(HERE, n)))
CAD, CTL, RH, SEN, VR = load('cad_data.json'), load('control_results.json'), load('ride_height_results.json'), \
    load('sensitivity_results.json'), load('vpp_results.json')
NU = 1.0e-6              # m2/s, water at about 20 C
CL_MAX_SECTION = 1.0     # NACA 4412 at Re ~ 1e5 (assumed, conservative)
E_CF, SIGMA_CF = 70000.0, 300.0
H0 = 0.020               # m, heave disturbance for the time-domain test

vpp.configure()
b = vpp.Boat('foiling', CAD)
rows = []


def check(rule, value, limit, ok, unit=''):
    rows.append(dict(rule=rule, value=value if isinstance(value, str) else round(value, 3), limit=limit, unit=unit, ok=bool(ok)))


def heave_sim(m, c, k, h0=H0, t_end=3.0, dt=1e-4):
    """RK4 on m h'' + c h' + k h = 0. Returns (settling time to 5 % of h0, peak overshoot fraction, final |h|)."""
    h, v, t, settle, peak = h0, 0.0, 0.0, None, 0.0
    f = lambda h, v: (v, -(c * v + k * h) / m)
    while t < t_end:
        k1 = f(h, v); k2 = f(h + dt / 2 * k1[0], v + dt / 2 * k1[1])
        k3 = f(h + dt / 2 * k2[0], v + dt / 2 * k2[1]); k4 = f(h + dt * k3[0], v + dt * k3[1])
        h += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]); v += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        t += dt
        peak = max(peak, -h / h0)
        if abs(h) > 0.05 * h0:
            settle = None
        elif settle is None:
            settle = t
    return settle, peak, abs(h)


# ---------------------------------------------------------------- stability
for name, v in CTL['foil_pitch'].items():
    check(f'pitch static margin ({name})', v['static_margin_mm'], '> 0 mm (neutral point aft of CG)', v['static_margin_mm'] > 0, 'mm')

flying = RH['rows']
settle, peak, final = heave_sim(b.M, flying[len(flying) // 2]['c_Ns_per_m'], 0.0)
check('heave, fixed foils: 20 mm disturbance after 3 s (expected: does not return)', final * 1000, 'neutral (k = 0)',
      final > 0.5 * H0, 'mm left')
zeta = [r['zeta'] for r in flying]
check('heave with wand flaps: damping ratio over the flying range', f"{min(zeta):.2f}-{max(zeta):.2f}", '>= 0.5 everywhere', min(zeta) >= 0.5)
sims = []
for r in (flying[0], flying[len(flying) // 3], flying[2 * len(flying) // 3], flying[-1]):
    s_, p_, fin = heave_sim(b.M, r['c_Ns_per_m'], r['k_N_per_m'])
    sims.append(dict(V=r['V'], settling_s=round(s_, 3) if s_ else None, overshoot_pct=round(p_ * 100, 1), final_mm=round(fin * 1000, 3)))
worst = max(x['settling_s'] or 99 for x in sims)
check('heave with wand flaps: 20 mm disturbance settles (5 %) across the flying range', worst, '<= 1 s, overshoot <= 10 %',
      worst <= 1.0 and max(x['overshoot_pct'] for x in sims) <= 10, 's')

PH = load('pitch_heave_results.json')
check('coupled heave-pitch modes over the flying range (elevator efficiency 1 and 0.65)', f"{min(PH['min_damping'], PH['min_damping_eta065']):.2f}",
      'all stable (value: least damping ratio)', PH['all_stable'])

# ---------------------------------------------------------------- flying trim
v12 = [x for x in VR['vpp']['foiling']['90'] if x['tws_kn'] == 12][0]
check('flying range (take-off to top)', f"{b.vto:.2f}-{b.vfly_max:.2f}", f'info; ends by: {b.fly_limit or "end of scan (6 m/s)"}', True, 'm/s')
check('flying range covers the 12 kn beam-reach speed', b.vfly_max / v12['V'], '>= 1.05 and not trim-limited',
      b.vfly_max >= 1.05 * v12['V'] and not v12.get('trim_limited'), 'x speed')
worst_top = min((s['flying_range_top_ms'] or 0) / v12['V'] for s in SEN if 'couple' in s['scenario'])
check('same, sail-drive pitch couple x0.5 and x1.5', worst_top, '>= 1.0', worst_top >= 1.0, 'x speed')
span = []
V = b.vto
while V <= v12['V'] + 1e-9:
    span.append(b.fly_trim(V)); V += 0.05
span.append(b.fly_trim(v12['V']))
check('elevator depth over the flying range (to the 12 kn speed)', min(t['elD'] for t in span) / vpp.EL_C, '>= 0.5 chord',
      min(t['elD'] for t in span) >= 0.5 * vpp.EL_C, 'chords')
check('main foil depth over the flying range', min(t['mD'] for t in span) / vpp.WING_C, '>= 0.5 chord',
      min(t['mD'] for t in span) >= 0.5 * vpp.WING_C, 'chords')
check('rudder immersion over the flying range', min(t['rudI'] for t in span) * 1000, f'>= {vpp.RUDDER_MIN * 1000:.0f} mm',
      min(t['rudI'] for t in span) >= vpp.RUDDER_MIN, 'mm')
env = CTL['foiling_steering_envelope']
check('steering over the whole flying range, heel-limited side force', env['max_deg'], f"<= {env['limit_deg']} deg (0.8 x throw)", env['max_deg'] <= env['limit_deg'], 'deg')
check('hull clearance over the flying range', min(t['hull'] for t in span) * 1000, '>= 50 mm', min(t['hull'] for t in span) >= 0.050, 'mm')
check('flap angle over the flying range', max(abs(math.degrees(t['delta'])) for t in span), '<= 15 deg',
      max(abs(math.degrees(t['delta'])) for t in span) <= 15, 'deg')
check('pitch attitude over the flying range', f"{min(math.degrees(t['theta']) for t in span):+.1f} to {max(math.degrees(t['theta']) for t in span):+.1f}", 'info (nose up +)', True, 'deg')
check('elevator lift over the flying range', f"{min(t['Le'] for t in span):+.1f} to {max(t['Le'] for t in span):+.1f}", 'info (down -)', True, 'N')

# ---------------------------------------------------------------- sizing
base = [s for s in SEN if s['scenario'] == 'baseline'][0]
check('take-off speed', b.vto, 'info', True, 'm/s')
check('take-off wind, beam reach (baseline)', base['TWA90_takeoff_tws_kn'], '<= 8 kn', (base['TWA90_takeoff_tws_kn'] or 99) <= 8, 'kn')
worst_sens = max(s['TWA90_takeoff_tws_kn'] or 99 for s in SEN)
check('take-off wind, beam reach (worst sensitivity case)', worst_sens, '<= 10 kn', worst_sens <= 10, 'kn')
t_to = b.fly_trim(b.vto)
check('main foil CL at take-off (flaps down)', t_to['clm'], f'<= 0.8 x assumed CL max {CL_MAX_SECTION}', t_to['clm'] <= 0.8 * CL_MAX_SECTION)
check('Reynolds number, main foil at take-off', b.vto * vpp.WING_C / NU / 1e5, 'info (x 1e5)', True)
check('Reynolds number, elevator at take-off', b.vto * vpp.EL_C / NU / 1e5, 'info (x 1e5)', True)
water = vpp.Z_FLY                                            # design waterline, boat frame
depth_main, depth_el = water - vpp.Z_WING, water - vpp.Z_EL
check('main foil depth at design ride height, level', depth_main / vpp.WING_C, '>= 1 chord', depth_main >= vpp.WING_C, 'chords')
check('elevator depth at design ride height, level', depth_el / vpp.EL_C, '>= 1 chord', depth_el >= vpp.EL_C, 'chords')


def section_props(code, chord, n=80):
    pts = [(chord * s, chord * t) for s, t in vpp.naca(code, n)]
    A = Cy = Ixx = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        cr = x0 * y1 - x1 * y0; A += cr; Cy += (y0 + y1) * cr; Ixx += (y0 * y0 + y0 * y1 + y1 * y1) * cr
    A /= 2; Cy /= (6 * A); Ixx /= 12
    return abs(Ixx) - abs(A) * Cy * Cy, max(abs(y - Cy) for _, y in pts)


scan, V = [], b.vto
while V <= b.vfly_max + 1e-9:
    scan.append(b.fly_trim(V)); V += 0.02
LM_MAX, LE_MAX = max(t['Lm'] for t in scan), max(abs(t['Le']) for t in scan)
I_w, c_w = section_props('4412', vpp.WING_C * 1000)
I_e, c_e = section_props('0012', vpp.EL_C * 1000)
span = vpp.WING_SPAN * 1000
L_case = 2 * LM_MAX                            # largest main-foil flight load, all on one wing, 2 g
M_root = L_case * span / 2                     # uniform load: resultant at mid-span
stress = M_root * c_w / I_w
tip = (L_case / span) * span ** 4 / (8 * E_CF * I_w)
stress_el = 2 * LE_MAX * vpp.EL_SPAN * 1000 / 2 * c_e / I_e
check('main foil root stress, largest flight load on one wing at 2 g (CFRP)', stress, f'<= {SIGMA_CF / 3:.0f} MPa (safety 3)', stress <= SIGMA_CF / 3, 'MPa')
check('main foil tip deflection, same case', tip, '<= 2 mm', tip <= 2.0, 'mm')
check('elevator root stress, largest flight load (up or down) on one elevator at 2 g', stress_el, f'<= {SIGMA_CF / 3:.0f} MPa (safety 3)', stress_el <= SIGMA_CF / 3, 'MPa')

out = dict(rules=rows, heave_time_domain=sims, design_waterline_boat_z_mm=round(water * 1000, 1),
           largest_flight_loads_N=dict(main=round(LM_MAX, 2), elevator=round(LE_MAX, 2)),
           assumptions=dict(section_cl_max=CL_MAX_SECTION, nu_m2_s=NU, E_MPa=E_CF, strength_MPa=SIGMA_CF, disturbance_mm=H0 * 1000))
json.dump(out, open(os.path.join(HERE, 'foil_checks.json'), 'w'), indent=1)
w = max(len(r['rule']) for r in rows)
for r in rows:
    print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['rule']:<{w}}  {r['value']!s:>10} {r['unit']:<10} limit {r['limit']}")
print('time domain:', sims)
print(f"{sum(r['ok'] for r in rows)}/{len(rows)} foil rules pass")
sys.exit(0 if all(r['ok'] for r in rows) else 1)
