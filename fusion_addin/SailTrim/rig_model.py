"""Beach-cat style rig geometry for the RC catamaran (pure Python, mm, Z-up, X forward, Y port).

Controls (what the three sliders set):
  jib_deg   - jib sheet: jib foot angle off centreline
  main_deg  - main traveler: boom angle off centreline
  tension   - mainsheet tension 0-100 %: leech tension, i.e. main twist and depth
Sails are shown on starboard tack (wind from starboard, sails to port, +Y).
"""
import math

try:
    from . import fittings_geom as fg
except ImportError:
    import fittings_geom as fg

PROFILES = {
    # 1 m boat: beach-cat rig with rotating wing mast, 8 battens, traveler + jib car, three sail controls
    'full': dict(
        mast_x=620.0, mast_z0=72.0, mast_fair_z0=125.0, mast_top=1370.0,
        wing_mast=True, mast_chord=24.0, mast_thick=14.0, mast_le=7.0, mast_r=6.0,
        z_foot=140.0, z_head=1330.0, main_c0=345.0, main_ch=105.0, main_p=1.7, n_battens=8,
        boom_z=132.0, boom_r=4.0,
        tack=(818.0, 150.0), hounds_z=1000.0, jib_z0=158.0, jib_head_z=985.0, jib_c0=221.0, jib_ch=12.0, jib_sections=8,
        rear_beam_x=180.0, front_beam_x=620.0, beam_top=70.0, car_limit=fg.CAR_LIMIT, traveler=True,
        track_h=fg.TT_TOP + fg.CLR - 70.0,  # car base above the beam top: T-rail track on the rear beam (fittings_geom)
        jib_track=(590.0, 36.0, 122.2),  # v1.4: on the pod lid (x, half travel, car base z); the pod covers the front beam
        bow=(985.0, 280.0, 70.0), chainplate=(600.0, 280.0, 66.0), bridle_post=True,
        limits=dict(jib_deg=(5.0, 40.0), main_deg=(0.0, 40.0), tension=(0.0, 100.0)),
        defaults=dict(jib_deg=12.0, main_deg=8.0, tension=70.0)),
    # 600 mm mini: same planform scaled 0.6, round fixed mast, 3 battens, one sail servo for both sheets
    'mini': dict(
        mast_x=372.0, mast_z0=46.2, mast_fair_z0=46.2, mast_top=845.0,
        wing_mast=False, mast_chord=0.0, mast_thick=0.0, mast_le=0.0, mast_r=3.0,
        z_foot=106.0, z_head=820.0, main_c0=207.0, main_ch=63.0, main_p=1.7, n_battens=3,
        boom_z=100.0, boom_r=2.0,
        tack=(491.0, 105.0), hounds_z=620.0, jib_z0=112.0, jib_head_z=607.0, jib_c0=133.0, jib_ch=7.0, jib_sections=6,
        rear_beam_x=108.0, front_beam_x=372.0, beam_top=44.0, car_limit=0.0, traveler=False,
        lead_z=95.2, main_lead_x=(165.0, 165.0), jib_lead_x=355.0,
        bow=(590.0, 170.0, 44.0), chainplate=(360.0, 170.0, 42.0), bridle_post=False,
        limits=dict(jib_deg=(5.0, 45.0), main_deg=(0.0, 45.0), tension=(70.0, 70.0)),
        defaults=dict(jib_deg=12.0, main_deg=8.0, tension=70.0)),
}
PROFILE = 'full'
RIG = PROFILES['full']
LIMITS = RIG['limits']
DEFAULTS = RIG['defaults']


def set_profile(name):
    global PROFILE, RIG, LIMITS, DEFAULTS
    PROFILE = name
    RIG = PROFILES[name]
    LIMITS = RIG['limits']
    DEFAULTS = RIG['defaults']


def single_sheet(main_deg):
    """Mini boat: one sail servo trims both sheets; the jib sits 4 deg wider than the main."""
    lo, hi = LIMITS['jib_deg']
    return dict(main_deg=main_deg, jib_deg=clamp(main_deg + 4.0, lo, hi), tension=DEFAULTS['tension'])
NPTS = 17


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def cos_spacing(n):
    return [0.5 * (1 - math.cos(math.pi * i / (n - 1))) for i in range(n)]


def camber_line(u, d, p):
    """NACA 4-digit mean line scaled to max camber d at chordwise position p."""
    if u < p:
        return d * (2 * p * u - u * u) / (p * p)
    return d * ((1 - 2 * p) + 2 * p * u - u * u) / ((1 - p) ** 2)


def frame(theta_deg):
    """Unit vectors of a section rotated theta to port: aft along chord, and leeward normal."""
    t = math.radians(theta_deg)
    return (-math.cos(t), math.sin(t)), (math.sin(t), math.cos(t))


def trim(c):
    T = clamp(c['tension'], 0, 100) / 100.0
    return dict(
        twist_top=3.0 + 27.0 * (1 - T),          # head angle above boom: 30 deg loose -> 3 deg sheeted hard
        main_camber=0.13 - 0.05 * T,             # leech tension + mast bend flatten the main
        main_draft=0.45,
        mast_rot=min(c['main_deg'] + 15.0, 85.0) if RIG['wing_mast'] else 0.0,
        jib_twist=8.0, jib_camber=0.10, jib_draft=0.40,
    )


def mast_axis_te(c):
    tr = trim(c); r = RIG
    if not r['wing_mast']:
        return (r['mast_x'] - r['mast_r'], 0.0)
    aft, _ = frame(tr['mast_rot'])
    k = r['mast_chord'] - r['mast_le']
    return (r['mast_x'] + k * aft[0], k * aft[1])


def mast_section(c):
    """Closed wing-mast section points (TE upper -> LE -> TE lower), XY at any height."""
    tr = trim(c); r = RIG
    aft, n = frame(tr['mast_rot'])
    le = (r['mast_x'] - r['mast_le'] * aft[0], -r['mast_le'] * aft[1])
    ch, t = r['mast_chord'], r['mast_thick'] / r['mast_chord']
    up, lo = [], []
    for u in cos_spacing(NPTS):
        yt = 5 * t * (0.2969 * math.sqrt(u) - 0.1260 * u - 0.3516 * u ** 2 + 0.2843 * u ** 3 - 0.1015 * u ** 4)
        up.append((le[0] + ch * (u * aft[0] + yt * n[0]), le[1] + ch * (u * aft[1] + yt * n[1])))
        lo.append((le[0] + ch * (u * aft[0] - yt * n[0]), le[1] + ch * (u * aft[1] - yt * n[1])))
    return list(reversed(up)) + lo[1:]


def main_sections(c):
    tr = trim(c); r = RIG
    luff = mast_axis_te(c)
    n_sec = r['n_battens'] + 2
    out = []
    for k in range(n_sec):
        s = k / (n_sec - 1)
        z = r['z_foot'] + s * (r['z_head'] - r['z_foot'])
        chord = r['main_c0'] - (r['main_c0'] - r['main_ch']) * s ** r['main_p']
        theta = c['main_deg'] + tr['twist_top'] * s ** 1.3
        d = tr['main_camber'] * (1 - 0.35 * s)
        aft, n = frame(theta)
        pts = [(luff[0] + chord * (u * aft[0] + camber_line(u, d, tr['main_draft']) * n[0]),
                luff[1] + chord * (u * aft[1] + camber_line(u, d, tr['main_draft']) * n[1])) for u in cos_spacing(NPTS)]
        out.append((z, pts))
    return out


def jib_luff_x(z):
    r = RIG
    return r['tack'][0] + (r['mast_x'] - r['tack'][0]) * (z - r['tack'][1]) / (r['hounds_z'] - r['tack'][1])


def jib_sections(c):
    tr = trim(c); r = RIG
    m = r['jib_sections']
    out = []
    for k in range(m):
        t = k / (m - 1)
        z = r['jib_z0'] + t * (r['jib_head_z'] - r['jib_z0'])
        chord = r['jib_c0'] * (1 - t) + r['jib_ch'] * t
        aft, n = frame(c['jib_deg'] + tr['jib_twist'] * t)
        x0 = jib_luff_x(z)
        pts = [(x0 + chord * (u * aft[0] + camber_line(u, tr['jib_camber'], tr['jib_draft']) * n[0]),
                chord * (u * aft[1] + camber_line(u, tr['jib_camber'], tr['jib_draft']) * n[1])) for u in cos_spacing(NPTS)]
        out.append((z, pts))
    return out


def hardware(c):
    """Moving hardware as (name, kind, data): cylinders (p0, p1, r) and boxes (x0,x1,y0,y1,z0,z1)."""
    r = RIG
    ms, js = main_sections(c), jib_sections(c)
    luff = mast_axis_te(c)
    clew = ms[0][1][-1]
    car_y = clamp(clew[1], -r['car_limit'], r['car_limit'])
    jclew = js[0][1][-1]
    jt = r.get('jib_track')
    jlim = jt[1] if jt else r['car_limit']
    jx, jz = (jt[0], jt[2]) if jt else (r['front_beam_x'], r['beam_top'])
    jh = 5.0 if jt else 6.0  # a lid car must stay under the boom (boom underside 128 mm)
    th = r.get('track_h', 0.0)
    jcar_y = clamp(jclew[1], -jlim, jlim)
    battens = [(f'Batten {k}', 'ribbon', ([(x, y, z) for x, y in pts[:-1]], 4.0 * r['boom_r'] / 4.0)) for k, (z, pts) in enumerate(ms) if 0 < k < len(ms) - 1]
    boom = ('Main Boom', 'cyl', ((luff[0], luff[1], r['boom_z']), (clew[0], clew[1], r['boom_z']), r['boom_r']))
    if not r['traveler']:  # both sheets led to fairleads on the box lid, trimmed by one sail servo
        lx = clamp(clew[0], *r['main_lead_x'])
        return battens + [boom,
            ('Mainsheet', 'cyl', ((clew[0], clew[1], r['boom_z'] - r['boom_r']), (lx, 0.0, r['lead_z']), 0.5)),
            ('Jib Sheet', 'cyl', ((jclew[0], jclew[1], js[0][0]), (r['jib_lead_x'], 0.0, r['lead_z']), 0.5))]
    return battens + [boom,
        ('Mainsheet', 'cyl', ((clew[0], clew[1], r['boom_z'] - 4), (fg.LINE_X, car_y, fg.Z_MAIN + 1), 0.6)),
        ('Traveler Car', 'tcar', (r['rear_beam_x'] - fg.TC_HX, r['rear_beam_x'] + fg.TC_HX, car_y - fg.TC_HY, car_y + fg.TC_HY,
                                  r['beam_top'] + th, fg.TC_POST_TOP)),   # bounding box; fusion_rig builds the printed car in it
        ('Jib Sheet', 'cyl', ((jclew[0], jclew[1], js[0][0]), (fg.JC_SHEET[0], jcar_y + math.copysign(fg.JC_HY, jcar_y), fg.JC_SHEET[1]), 0.6)),
        ('Jib Car', 'jcar', (jx - fg.JC_HX, jx + fg.JC_HX, jcar_y - fg.JC_HY, jcar_y + fg.JC_HY, jz, jz + jh)),
    ]


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def readout(c):
    r = RIG; tr = trim(c)
    hw = {h[0]: h[2] for h in hardware(c)}
    area = lambda secs: sum((secs[i + 1][0] - secs[i][0]) * (chord_len(secs[i][1]) + chord_len(secs[i + 1][1])) / 2 for i in range(len(secs) - 1))
    if not r['traveler']:
        return dict(boom_angle_deg=round(c['main_deg'], 1), jib_angle_deg=round(c['jib_deg'], 1),
                    mainsheet_len_mm=round(dist(*hw['Mainsheet'][:2]), 1), jib_sheet_len_mm=round(dist(*hw['Jib Sheet'][:2]), 1),
                    main_area_m2=round(area(main_sections(c)) / 1e6, 4), jib_area_m2=round(area(jib_sections(c)) / 1e6, 4))
    return dict(
        twist_top_deg=round(tr['twist_top'], 1), main_camber_pct=round(tr['main_camber'] * 100, 1),
        mast_rotation_deg=round(tr['mast_rot'], 1),
        traveler_car_y_mm=round(hw['Traveler Car'][2] + 9, 1), jib_car_y_mm=round(hw['Jib Car'][2] + 7, 1),
        mainsheet_len_mm=round(dist(*hw['Mainsheet'][:2]), 1), jib_sheet_len_mm=round(dist(*hw['Jib Sheet'][:2]), 1),
        main_area_m2=round(area(main_sections(c)) / 1e6, 4), jib_area_m2=round(area(jib_sections(c)) / 1e6, 4),
    )


def chord_len(pts):
    return math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])


def planform(c=None):
    """Sail areas and centroids (x, z) of the flat planform, for the VPP."""
    c = c or dict(jib_deg=0.0, main_deg=0.0, tension=100.0)
    out = []
    for name, secs in (('Mainsail', main_sections(c)), ('Jib', jib_sections(c))):
        A = Ax = Az = 0.0
        fine = []
        for i in range(len(secs) - 1):
            (z0, p0), (z1, p1) = secs[i], secs[i + 1]
            for j in range(20):
                f = (j + 0.5) / 20
                z = z0 + f * (z1 - z0)
                xl = p0[0][0] + f * (p1[0][0] - p0[0][0])
                ch = chord_len(p0) + f * (chord_len(p1) - chord_len(p0))
                dz = (z1 - z0) / 20
                A += ch * dz; Ax += (xl - ch / 2) * ch * dz; Az += z * ch * dz
        out.append(dict(name=name, area_m2=A / 1e6, x_mm=Ax / A, z_mm=Az / A))
    return out
