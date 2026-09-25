"""Coupled heave-pitch stability of the flying boat (linear, 2 degrees of freedom), across the flying range.

ride_height.py treats heave alone. Here heave h (CG, up +) and pitch theta (nose up +) move together, linearised about
the flying trim (vpp.Boat.fly_trim) at each speed:
  main foil:  dL_m = q S_m a_m (dtheta - (hdot + l_m thetadot)/V + tau d_delta)
  elevators:  dL_e = eta q S_e a_e (dtheta - (hdot + l_e thetadot)/V)
  wand:       d_delta = -G (dtheta + (dh + l_p dtheta) / (L cos phi_w))    (it reads bow height and boat-frame angle)
  m hddot = dL_m + dL_e,   I thetaddot = l_m dL_m + l_e dL_e
with l_m, l_e, l_p the distances of the main foil, elevator and wand hinge ahead of the CG, and I the pitch inertia
from the CAD (analysis/cad_inertia.json, cad_scripts/export_inertia.py). Left out: added mass of the foils, unsteady
(lagging) lift, downwash lag, changes of sail drive with attitude. Stability: Routh-Hurwitz on the characteristic
quartic; the modes (frequency, damping ratio) come from its roots. Writes pitch_heave_results.json and
paper/data/pitch_heave.dat.
"""
import cmath, json, math, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = json.load(open(os.path.join(HERE, 'cad_data.json')))
INERTIA = json.load(open(os.path.join(HERE, 'cad_inertia.json')))


def matrix(b, V, eta=1.0, wand=True):
    t = b.fly_trim(V)
    q = 0.5 * vpp.RHO * V * V
    A_m, A_e = q * b.S_main * b.a_main, eta * q * b.S_el * b.a_el
    xcg = b.lcg / 1000
    l_m, l_e, l_p = vpp.X_MAIN_FOIL / 1000 - xcg, vpp.X_EL / 1000 - xcg, vpp.X_PIVOT - xcg
    G = vpp.GEAR if wand else 0.0
    K = 1 / (vpp.WAND_L * math.cos(math.asin(min(1.0, t['hp'] / vpp.WAND_L))))
    tau = vpp.FLAP_TAU
    # dL_m and dL_e as coefficients of (h, theta, hdot, thetadot)
    Lm = [-A_m * tau * G * K, A_m * (1 - tau * G * (1 + K * l_p)), -A_m / V, -A_m * l_m / V]
    Le = [0.0, A_e, -A_e / V, -A_e * l_e / V]
    M, I = b.M, INERTIA['Iyy_kgm2']
    F = [Lm[i] + Le[i] for i in range(4)]
    My = [l_m * Lm[i] + l_e * Le[i] for i in range(4)]
    return [[0, 0, 1, 0], [0, 0, 0, 1], [f / M for f in F], [m / I for m in My]], t


def charpoly(A):
    """Coefficients [1, c1, c2, c3, c4] of det(sI - A) (Faddeev-LeVerrier)."""
    n = len(A)
    Mk = [[0.0] * n for _ in range(n)]
    c = [1.0]
    for k in range(1, n + 1):
        AM = [[sum(A[i][j] * Mk[j][l] for j in range(n)) for l in range(n)] for i in range(n)]
        Mk = [[AM[i][j] + (c[-1] if i == j else 0.0) for j in range(n)] for i in range(n)]
        AM = [[sum(A[i][j] * Mk[j][l] for j in range(n)) for l in range(n)] for i in range(n)]
        c.append(-sum(AM[i][i] for i in range(n)) / k)
    return c


def roots(c, iters=500):
    """Durand-Kerner roots of the monic polynomial with coefficients c."""
    n = len(c) - 1
    z = [(0.4 + 0.9j) ** k for k in range(n)]
    p = lambda s: sum(ci * s ** (n - i) for i, ci in enumerate(c))
    for _ in range(iters):
        z = [zi - p(zi) / math.prod((zi - zj) for j, zj in enumerate(z) if j != i) for i, zi in enumerate(z)]
    return z


def routh_stable(c):
    _, a3, a2, a1, a0 = c
    return all(x > 0 for x in (a3, a2, a1, a0)) and a3 * a2 > a1 and a3 * a2 * a1 > a1 * a1 + a3 * a3 * a0


def modes(rs):
    out = []
    for r in rs:
        if r.imag < -1e-9:
            continue
        wn = abs(r)
        out.append(dict(freq_hz=round(abs(r.imag) / (2 * math.pi), 3), damping=round(-r.real / wn, 3) if wn > 1e-12 else None,
                        real=round(r.real, 3)))
    return sorted(out, key=lambda m: (m['damping'] if m['damping'] is not None else 9))


if __name__ == '__main__':
    vpp.configure()
    b = vpp.Boat('foiling', CAD)
    rows = []
    V = b.vto
    while V <= min(b.vfly_max, 6.0) + 1e-9:
        row = dict(V=round(V, 2))
        for label, eta, wand in (('wand', 1.0, True), ('wand_eta065', 0.65, True), ('fixed', 1.0, False)):
            A, t = matrix(b, V, eta, wand)
            c = charpoly(A)
            ms = modes(roots(c))
            row[label] = dict(stable=routh_stable(c), min_damping=ms[0]['damping'], modes=ms)
        rows.append(row)
        V += 0.25
    worst = min((r['wand']['min_damping'] for r in rows), default=None)
    worst65 = min((r['wand_eta065']['min_damping'] for r in rows), default=None)
    out = dict(inertia=INERTIA, all_stable=all(r['wand']['stable'] and r['wand_eta065']['stable'] for r in rows),
               min_damping=worst, min_damping_eta065=worst65, fixed_foils_all_stable=all(r['fixed']['stable'] for r in rows), rows=rows)
    json.dump(out, open(os.path.join(HERE, 'pitch_heave_results.json'), 'w'), indent=1)
    with open(os.path.join(HERE, '..', 'paper', 'data', 'pitch_heave.dat'), 'w') as f:
        f.write('V zeta zeta65 f1 f2\n')
        for r in rows:
            fr = sorted(m['freq_hz'] for m in r['wand']['modes'])
            f.write(f"{r['V']} {r['wand']['min_damping']} {r['wand_eta065']['min_damping']} {fr[0]} {fr[-1]}\n")
    print('I_yy', INERTIA['Iyy_kgm2'], 'kg m2; stable everywhere (wand, eta 1 and 0.65):', out['all_stable'],
          '| min damping', worst, '/', worst65, '| fixed foils stable:', out['fixed_foils_all_stable'])
    for r in rows[::2]:
        print(r['V'], 'wand', r['wand']['stable'], r['wand']['modes'], '| fixed', r['fixed']['stable'], [(m['freq_hz'], m['damping']) for m in r['fixed']['modes']])
