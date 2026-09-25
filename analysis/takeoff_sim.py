"""Time-domain take-off and gust simulation of the 1 m foiling boat (surge, heave, pitch; RK4, 2 ms steps).

The static trim (vpp.Boat.fly_trim) and the linear heave-pitch analysis (pitch_heave.py) describe equilibria. This
integrates the transition: the boat accelerates from rest on a beam reach, reaches take-off with both flaps on their
stops, and the wand must catch it before a foil breaches. Forces at every step:
- hulls: buoyancy of the elliptical stations at the instantaneous heave and pitch (both hulls, sub_area), and hull drag
  from the simulator's tables (friction, Michell wave, transom) at the load they carry; hull heave/pitch damping is a
  distributed linear term sized for 30 % of critical damping of the floating boat (assumed; not modelled otherwise);
- foils: lift from the local angle of attack (pitch, incidence, local vertical velocity, flap), capped at CL 0.8 and
  faded out over the last half chord below the surface (assumed ventilation model); profile and induced drag;
- wand: reads its hinge height and the boat's pitch, flap = G (phi0 - theta - phi_wand) within +-15 deg;
- struts and rudders: profile drag on the immersed length; sails: vpp.Boat.forces at the instantaneous speed, acting at
  the centre of effort; 10 % added mass in surge (as in the simulator's acceleration run).
The boat is held flat (no heel): roll near take-off is covered by the skimming model in vpp.py, not here.
Writes takeoff_sim_results.json and paper/data/takeoff_ts.dat.
"""
import json, math, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = json.load(open(os.path.join(HERE, 'cad_data.json')))
INERTIA = json.load(open(os.path.join(HERE, 'cad_inertia.json')))
SIM = json.load(open(os.path.join(HERE, '..', 'sim', 'sim_data.json')))
DT, ZETA_HULL, NST = 0.002, 0.3, 40
H_REF = vpp.WAND_L * math.sin(math.radians(vpp.WAND_PHI0_DEG))

HM, HS, ROWS = SIM['hull']['masses'], SIM['hull']['speeds'], SIM['hull']['rows']


def interp1(xs, ys, x):
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])


def hull_drag(m, V):
    """Resistance of both hulls carrying m kg (simulator tables, same formulas as sim_core.js)."""
    if m <= 0 or V <= 0: return 0.0
    q = 0.5 * vpp.RHO * V * V
    col = lambda k: [r[k] for r in ROWS]
    S, lwl, at = interp1(HM, col('S'), m), interp1(HM, col('lwl'), m), interp1(HM, col('at'), m)
    i = min(max(k for k in range(len(HM) - 1) if HM[k] <= m) if m >= HM[0] else 0, len(HM) - 2)
    tm = min(1.0, max(0.0, (m - HM[i]) / (HM[i + 1] - HM[i])))
    rw = interp1(HS, ROWS[i]['rw'], V) + tm * (interp1(HS, ROWS[i + 1]['rw'], V) - interp1(HS, ROWS[i]['rw'], V)) if V >= 0.3 else 0.0
    Rf = q * S * vpp.cf_ittc(V * max(lwl, 0.05) / vpp.NU) * 1.25
    hw = SIM['hull']['hw_transom']
    fnt = V / math.sqrt(2 * vpp.G * at / (2 * hw + 2 * hw * 0.9)) if at > 0 else 99
    return Rf + rw + (q * at * 0.2 * (1 - 0.2 * fnt) if fnt < 5 else 0.0)


class Boat:
    def __init__(self):
        self.b = vpp.load_pitch_limits(vpp.Boat('foiling', CAD), 'foiling_1m')
        self.M, self.W, self.I = self.b.M, self.b.W, INERTIA['Iyy_kgm2']
        self.xg, self.zg = self.b.lcg / 1000, CAD['foiling']['vcg_mm'] / 1000
        self.xs = [vpp.L_HULL * (k + 0.5) / NST for k in range(NST)]
        self.dx = vpp.L_HULL / NST
        # hull damping: 30 % of critical for the floating boat's heave (assumed), spread by waterplane width
        zw0 = self.b.zw0
        self.awp0 = 2 * sum(2 * vpp.half_width(x, zw0) * self.dx for x in self.xs)
        k = vpp.RHO * vpp.G * self.awp0
        self.c_per_area = 2 * ZETA_HULL * math.sqrt(k * self.M) / self.awp0

    def Z(self, Hg, th, x, z):
        return Hg + (x - self.xg) * math.sin(th) + (z - self.zg) * math.cos(th)

    def forces(self, s, tws, twa):
        V, Hg, th, w, om = s                       # speed, CG height, pitch (nose up +), heave rate, pitch rate
        b, q = self.b, 0.5 * vpp.RHO * s[0] ** 2
        Fz = Mnu = Dx = 0.0
        # hulls: buoyancy and damping by station
        B = 0.0
        for x in self.xs:
            zs = self.zg - (Hg + (x - self.xg) * math.sin(th)) / math.cos(th)     # water surface in the boat frame
            a = 2 * vpp.sub_area(x, zs)
            if a <= 0: continue
            dB = vpp.RHO * vpp.G * a * self.dx
            wl = 2 * 2 * vpp.half_width(x, zs) * self.dx
            dF = dB - self.c_per_area * wl * (w + (x - self.xg) * om)
            B += dB; Fz += dF; Mnu += (x - self.xg) * dF
        Rh = hull_drag(B / vpp.G, V)
        z_h = min(0.0, self.zg - Hg) / 2 + vpp.ZB(0.5) / 2               # rough height of the hull drag
        Dx += Rh; Mnu -= (z_h - self.zg) * (-Rh)
        # wand and flap
        hp = self.Z(Hg, th, vpp.X_PIVOT, vpp.Z_PIVOT)
        phw = math.asin(min(1.0, max(0.0, hp / vpp.WAND_L)))
        delta = max(-1, min(1, vpp.GEAR * (math.radians(vpp.WAND_PHI0_DEG) - th - phw) / math.radians(vpp.FLAP_TRAVEL_DEG))) * math.radians(vpp.FLAP_TRAVEL_DEG)
        # foils
        depths = {}
        for name, x, z, S_, a_, span, chord, inc, aL0, flap in (
                ('main', vpp.X_MAIN_FOIL / 1000, vpp.Z_WING, b.S_main, b.a_main, vpp.WING_SPAN, vpp.WING_C, vpp.INC_MAIN_DEG, vpp.alpha_L0('4412'), True),
                ('el', vpp.X_EL / 1000, vpp.Z_EL, b.S_el, b.a_el, vpp.EL_SPAN, vpp.EL_C, vpp.INC_EL_DEG, 0.0, False)):
            d = -self.Z(Hg, th, x, z)
            depths[name] = d
            f = min(1.0, max(0.0, d / (0.5 * chord)))
            if V <= 0.05 or f <= 0: continue
            alpha = th + math.radians(inc) - (w + (x - self.xg) * om) / V - aL0 + (vpp.FLAP_TAU * delta if flap else 0.0)
            cl = max(-vpp.CL_USABLE, min(vpp.CL_USABLE, a_ * alpha)) * f
            L = q * S_ * cl
            D = 2 * vpp.profile_drag(q, V, chord, span, 0.12) + 2 * vpp.induced(L / 2, q, span)
            Fz += L; Mnu += (x - self.xg) * L
            Dx += D; Mnu += (z - self.zg) * D
        # struts and rudders on their immersed length
        strut = max(0.0, min(depths['main'], vpp.ZB(vpp.X_BOARD) - vpp.Z_WING))
        rud = max(0.0, min(-self.Z(Hg, th, vpp.X_RUDDER_TIP, b.z_rud), vpp.ZB(0.0) - b.z_rud))
        # sails (flat boat; heel arm of the flying boat once the hulls carry under 2 % of the weight)
        flying = B < 0.02 * self.W
        fx, fy, sail = b.pitch_limit(*b.forces(max(V, 0.01), tws, twa, flying), flying)
        # struts and rudders: profile drag, spray at the surface and the induced drag of the side force they carry (as vpp.py)
        for c, l, z0, share in ((vpp.STRUT_C, strut, vpp.Z_WING, 0.35), (vpp.RUDDER_C, rud, b.z_rud, 0.15)):
            D = 2 * (vpp.profile_drag(q, V, c, l, 0.12) + 0.24 * q * (0.12 * c) ** 2 + vpp.side_induced(share * fy, q, c, l)) if l > 0 and V > 0 else 0.0
            Dx += D; Mnu += (z0 + l / 2 - self.zg) * D
        Mnu -= (b.ce_z - self.zg) * fx
        return dict(ax=(fx - Dx) / (1.1 * self.M), az=(Fz - self.W) / self.M, aq=Mnu / self.I, B=B, delta=delta, hp=hp, depths=depths, drive=fx)

    def deriv(self, s, tws, twa):
        f = self.forces(s, tws, twa)
        return [f['ax'], s[3], s[4], f['az'], f['aq']], f


def rk4(boat, s, tws, twa):
    k1, f = boat.deriv(s, tws, twa)
    k2, _ = boat.deriv([s[i] + DT / 2 * k1[i] for i in range(5)], tws, twa)
    k3, _ = boat.deriv([s[i] + DT / 2 * k2[i] for i in range(5)], tws, twa)
    k4, _ = boat.deriv([s[i] + DT * k3[i] for i in range(5)], tws, twa)
    return [s[i] + DT / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(5)], f


def run(boat, tws_fn, twa, t_end):
    # settle afloat at rest (no wind) first
    s = [0.0, boat.zg - boat.b.zw0, 0.0, 0.0, 0.0]
    for _ in range(int(3.0 / DT)):
        s, _ = rk4(boat, s, 0.0, twa)
        s[0] = 0.0
    rows, t, t_take = [], 0.0, None
    while t <= t_end:
        tws = tws_fn(t)
        s, f = rk4(boat, s, tws * 0.5144, twa)
        s[0] = max(0.0, s[0])
        if t_take is None and f['B'] < 0.01 * boat.W and s[0] > 0.5:
            t_take = t
        if abs(t / 0.05 - round(t / 0.05)) < DT / 0.05 / 2:
            rows.append(dict(t=round(t, 3), tws=tws, V=round(s[0], 4), pitch=round(math.degrees(s[2]), 3), bow=round((f['hp'] - H_REF) * 1000, 2),
                             flap=round(math.degrees(f['delta']), 2), main=round(f['depths']['main'] * 1000, 1), el=round(f['depths']['el'] * 1000, 1),
                             hullN=round(f['B'], 3)))
        t += DT
    return rows, t_take


if __name__ == '__main__':
    vpp.configure()
    boat = Boat()
    out = {}
    for name, fn, t_end in (('beam reach, 8 kn', lambda t: 8.0, 25.0),
                            ('beam reach, 9 kn, 4 kn gust at 20-25 s', lambda t: 13.0 if 20.0 <= t < 25.0 else 9.0, 35.0)):
        rows, t_take = run(boat, fn, 90, t_end)
        fly = [r for r in rows if t_take is not None and r['t'] >= t_take]
        out[name] = dict(takeoff_s=t_take and round(t_take, 2), rows=rows,
                         max_bow_rise_mm=max((r['bow'] for r in fly), default=None), min_main_depth_mm=min((r['main'] for r in fly), default=None),
                         min_el_depth_mm=min((r['el'] for r in fly), default=None), end=rows[-1])
        print(name, '| take-off at', out[name]['takeoff_s'], 's | after take-off: max bow rise', out[name]['max_bow_rise_mm'], 'mm, min depth main/el',
              out[name]['min_main_depth_mm'], '/', out[name]['min_el_depth_mm'], 'mm | end', rows[-1])
    json.dump(out, open(os.path.join(HERE, 'takeoff_sim_results.json'), 'w'), indent=1)
    with open(os.path.join(HERE, '..', 'paper', 'data', 'takeoff_ts.dat'), 'w') as f:
        f.write('t V bow flap pitch el\n' + ''.join(f"{r['t']} {r['V']} {r['bow']} {r['flap']} {r['pitch']} {r['el']}\n" for r in out['beam reach, 8 kn']['rows']))
