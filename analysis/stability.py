"""Static stability of the catamarans: transverse GZ curve (capsize) and longitudinal pitchpole margin.

Transverse: each hull section (ellipse) is polygonised, heeled by phi, clipped at the waterline; the
waterline height is found so displacement equals weight. GZ = Y_G - Y_B (positive = restoring).
Longitudinal: the waterline is tilted bow-down by theta in the boat frame; for each theta the sinkage
is solved and GZ_L = (x_B - x_G) cos(theta) + (z_B - z_G) sin(theta). The largest GZ_L is compared
with the bow-down moment of the sails at full (heel-limited) drive.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vpp

N_SEC = 96


def section_poly(x, yc):
    a, zc, b, _ = vpp.section(x)
    return [(yc + a * math.sin(2 * math.pi * k / N_SEC), zc - b * math.cos(2 * math.pi * k / N_SEC)) for k in range(N_SEC)]


def clip_below(poly, h):
    out = []
    for i in range(len(poly)):
        P, Q = poly[i], poly[(i + 1) % len(poly)]
        pin, qin = P[1] <= h, Q[1] <= h
        if pin:
            out.append(P)
        if pin != qin:
            t = (h - P[1]) / (Q[1] - P[1])
            out.append((P[0] + t * (Q[0] - P[0]), h))
    return out


def area_centroid(poly):
    if len(poly) < 3:
        return 0.0, 0.0, 0.0
    A = cx = cy = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
        cr = x0 * y1 - x1 * y0
        A += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    A /= 2
    if abs(A) < 1e-12:
        return 0.0, 0.0, 0.0
    return abs(A), cx / (6 * A), cy / (6 * A)


def heeled(phi, h, nx=60):
    """Displaced volume and centroid (earth Y) for heel phi (rad), waterline at earth Z = h."""
    c, s = math.cos(phi), math.sin(phi)
    V = VY = 0.0
    dx = vpp.L_HULL / nx
    for i in range(nx):
        x = (i + 0.5) * dx
        for yc in (vpp.HULL_SPACING / 2, -vpp.HULL_SPACING / 2):
            poly = [(y * c - z * s, y * s + z * c) for y, z in section_poly(x, yc)]
            A, Y, _ = area_centroid(clip_below(poly, h))
            V += A * dx; VY += A * Y * dx
    return V, (VY / V if V > 0 else 0.0)


def gz_curve(vol, zg, angles):
    rows = []
    for deg in angles:
        phi = math.radians(deg)
        lo, hi = -0.3, 0.3
        for _ in range(40):
            h = (lo + hi) / 2
            if heeled(phi, h)[0] > vol: hi = h
            else: lo = h
        V, YB = heeled(phi, (lo + hi) / 2)
        YG = -zg * math.sin(phi)
        rows.append((deg, YG - YB))
    return rows


def pitched(theta, h0, hulls=2, nx=200):
    """Bow-down pitch theta: waterline in the boat frame z_w(x) = h0 + (x - L/2) tan(theta)."""
    V = VX = VZ = 0.0
    dx = vpp.L_HULL / nx
    for i in range(nx):
        x = (i + 0.5) * dx
        zw = h0 + (x - vpp.L_HULL / 2) * math.tan(theta)
        a, zc, b, zb = vpp.section(x)
        A = vpp.sub_area(x, zw)
        if A <= 0:
            continue
        t = max(-1.0, min(1.0, (zw - zc) / b))
        zcen = zc - (2 * a * b * (1 - t * t) ** 1.5 / 3) / A if A > 0 else zc   # centroid of the ellipse segment
        V += A * dx * hulls; VX += A * x * dx * hulls; VZ += A * zcen * dx * hulls
    return V, (VX / V if V else 0.0), (VZ / V if V else 0.0)


def pitch_curve(vol, xg, zg, hulls):
    rows = []
    for deg in [0.5 * k for k in range(0, 41)]:
        th = math.radians(deg)
        lo, hi = -0.4, 0.4
        for _ in range(40):
            h0 = (lo + hi) / 2
            if pitched(th, h0, hulls)[0] > vol: hi = h0
            else: lo = h0
        V, xb, zb = pitched(th, (lo + hi) / 2, hulls)
        bow_deck = vpp.ZT(vpp.L_HULL * 0.98) - ((lo + hi) / 2 + (vpp.L_HULL * 0.98 - vpp.L_HULL / 2) * math.tan(th))
        rows.append(dict(theta=deg, GZL=(xb - xg) * math.cos(th) + (zb - zg) * math.sin(th), bow_freeboard=bow_deck))
    return rows


def analyse(label, boat, ce_z, drive_max):
    vol = boat.M / vpp.RHO
    zg = boat_vcg[label] / 1000
    xg = boat.lcg / 1000
    gz = gz_curve(vol, zg, [0, 2, 4, 6, 8, 10, 12, 15, 20, 30, 40, 50, 60, 70, 80, 90])
    gzmax = max(gz, key=lambda r: r[1])
    cross = next((r[0] for r in gz[1:] if r[1] <= 0), None)
    out = dict(gz=[(d, round(g * 1000, 1)) for d, g in gz], gz_max_mm=round(gzmax[1] * 1000, 1), gz_max_at_deg=gzmax[0],
               RM_max_Nm=round(boat.W * gzmax[1], 3), RM_assumed_Nm=round(boat.RM, 3), capsize_angle_deg=cross,
               capsize_estimate_deg=round(math.degrees(math.atan2(vpp.HULL_SPACING / 2, zg)), 1))
    for hulls in (2, 1):
        pc = pitch_curve(vol, xg, zg, hulls)
        before = [r for r in pc if r['bow_freeboard'] > 0]
        m = max(before, key=lambda r: r['GZL']) if before else None
        M_pitch = drive_max * (ce_z - 0.0)
        out[f'pitch_{hulls}hull'] = dict(GZL_max_mm=round(m['GZL'] * 1000, 1) if m else None, at_deg=m['theta'] if m else None,
                                         RM_L_max_Nm=round(boat.W * m['GZL'], 3) if m else None, bow_down_moment_Nm=round(M_pitch, 3),
                                         margin=round(boat.W * m['GZL'] / M_pitch, 2) if m else None)
    return out


def max_drive(boat):
    best = 0.0
    for twa in (60, 75, 90, 105, 120):
        for tws in range(4, 21, 2):
            r = boat.solve(tws * 0.5144, twa)
            vto = boat.takeoff_speed()
            fx, fy, s = boat.forces(r['V'], tws * 0.5144, twa, bool(vto and r['V'] >= vto))
            best = max(best, fx)
    return best


if __name__ == '__main__':
    cad = json.load(open(os.path.join(HERE, 'cad_data.json')))
    boat_vcg = {'build_first_1m': cad['displacement']['vcg_mm']}
    vpp.configure()
    b = vpp.Boat('displacement', cad)
    res = {'build_first_1m': analyse('build_first_1m', b, b.ce_z, max_drive(b))}
    boat_vcg['foiling_1m'] = cad['foiling']['vcg_mm']
    bfo = vpp.Boat('foiling', cad)
    res['foiling_1m'] = analyse('foiling_1m', bfo, bfo.ce_z, max_drive(bfo))
    # mini
    sys.path.insert(0, os.path.join(HERE, '..', 'mini'))
    import mini_analysis  # configures vpp for the mini geometry
    b2 = vpp.Boat('displacement', mini_analysis.CAD)
    boat_vcg['mini_600'] = mini_analysis.CAD['displacement']['vcg_mm']
    res['mini_600'] = analyse('mini_600', b2, b2.ce_z, max_drive(b2))
    json.dump(res, open(os.path.join(HERE, 'stability_results.json'), 'w'), indent=1)
    for k, v in res.items():
        print(k, {kk: vv for kk, vv in v.items() if kk != 'gz'})
        print('  GZ (deg, mm):', v['gz'])
