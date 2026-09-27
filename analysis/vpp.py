"""First-order velocity prediction for the RC Foiling Catamaran v1.1.

Pure Python (no numpy). Inputs: hull station table (same as the Fusion loft) and
mass properties exported from Fusion (cad_data.json).

Models
- Hull statics: elliptic sections, natural cubic spline between stations.
- Hull friction: ITTC-57 line, form factor (1+k) = 1.25 (assumed, slender demihulls).
- Hull wave resistance: Michell thin-ship integral, catamaran interference
  factor 4 cos^2(ky s/2), panel-wise analytic (Filon-type) integration in x and z.
  Tabulated with draft, wetted area and waterline length over hull load and speed (hull_table()),
  for both hulls and for one, and interpolated exactly as the flight simulator does.
- Transom: Holtrop transom term.
- Appendages: ITTC friction (FOIL_FRICTION = 'transitional': laminar flat plate, a sensitivity case only)
  with Hoerner thickness form factor, spray drag,
  lifting-line induced drag for foil lift and for side force.
- Foils: thin-airfoil zero-lift angle, lifting-line slope; wand-driven flaps fully down below take-off.
- Sails: CL <= CLmax, CD = CD0 + CL^2/(pi e AR); CL reduced (flattened) so the
  heeling moment stays <= 0.9 x max righting moment.
"""
import hashlib, json, math, os

RHO, NU, G, RHO_A = 1000.0, 1.0e-6, 9.81, 1.225
HERE = os.path.dirname(os.path.abspath(__file__))

STATIONS = [  # x, half width, z bottom, z top (mm) - identical to the Fusion loft (v1.3: fuller bows)
    (0, 26.0, -28.0, 58.0), (150, 36.0, -40.0, 60.0), (350, 40.0, -45.0, 62.0),
    (550, 39.5, -44.0, 64.0), (750, 35.0, -37.0, 70.0), (880, 26.0, -26.0, 76.0),
    (960, 14.0, -12.0, 79.0), (1000, 4.0, 5.0, 81.0)]
HULL_SPACING = 0.560          # m, centre to centre
TRUNK = (0.064, 0.0092, 560)  # flooded foil trunk: length, width (m), x (mm)

# appendages (m): chord, bottom z in boat frame
STRUT_C, RUDDER_C, EL_C = 0.060, 0.045, 0.028
Z_WING, Z_BOARD, Z_RUDDER, Z_EL = -0.220, -0.250, -0.200, -0.210
# v2.2 foils (sim/optimize.js with the flying trim; paper Section 6). Earlier sets: v2.0 wing 200 x 60 mm at 2 deg,
# elevators 150 x 36 mm at 3 deg; v2.1 wing 160 x 40 mm at 0 deg, elevators 140 x 32 mm at 4 deg; both at Z_EL = -0.197.
# Z_RUDDER is the build-first rudder tip; the foiling rudders end RUDDER_BELOW_EL under the elevators.
FOIL_VERSION = 'v2.2'
WING_SPAN, EL_SPAN = 0.160, 0.120
WING_C = 0.045                             # main-foil wing chord; the strut keeps STRUT_C
INC_MAIN_DEG, INC_EL_DEG = 1.5, -1.0
# wand-driven flaps (analysis/ride_height.py): fully down until the boat flies, so take-off uses the flapped main foil.
# FLAP_TAU = thin-airfoil effectiveness of a 25 % chord flap x 0.8 viscous factor. Foil CL is capped at 0.8
# (0.8 of an assumed section maximum of 1.0 near Re 1e5), as in the flight simulator (sim/sim_core.js).
FLAP_TAU, FLAP_TRAVEL_DEG, CL_USABLE = 0.487, 15.0, 0.8
X_MAIN_FOIL, X_EL = 575.0, -15.0          # quarter-chord x (mm)
# ride-height wand (CAD 'Ride Height Control', analysis/ride_height.py): hinge at the bow, tip on the water
X_PIVOT, Z_PIVOT = 1.008, 0.074            # m, boat frame: wand hinge axle (cad_scripts/linkage.py PIVOT)
WAND_L, WAND_PHI0_DEG, GEAR = 0.30, 49.0, 1.5   # m; deg below the boat's x axis at the design ride height; flap deg per wand deg
Z_FLY = Z_PIVOT - WAND_L * math.sin(math.radians(WAND_PHI0_DEG))   # design waterline when flying, boat frame
X_RUDDER_TIP = -0.0305                     # m, rudder blade tip centre (CAD)
RUDDER_BELOW_EL = 0.003                    # m, foiling rudder blade tip below the elevator quarter chord (CAD)
X_RUDDER_QC = -0.01925                     # m, rudder stock / quarter chord (CAD; control.py X_RUDDER)
RUDDER_THROW_DEG = 18.0                    # deg, servo linkage throw (control.py computes it from the horn and tiller arm)
STEER_MAX_DEG = 0.8 * RUDDER_THROW_DEG     # steering needed while flying must leave 20 % of the throw in reserve (assumed)
COUPLE_FACTOR = 1.0                        # scales the sail-drive pitch couple (sensitivity study only)
RUDDER_MIN = 0.030                         # m of rudder immersed: the control analysis's worst foiling case then needs ~14 of 18 deg

# sails and aero (assumed)
CL_MAX, CD0_SAIL, E_SAIL = 1.3, 0.05, 0.9
RIG_HEIGHT = 1.19                          # m, main luff
RM_FRACTION = 0.9                          # sail at 90% of max righting moment


# ---------------------------------------------------------------- utilities
def spline(xs, ys):
    n = len(xs); h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    al = [0.0] * n
    for i in range(1, n - 1):
        al[i] = 3 / h[i] * (ys[i + 1] - ys[i]) - 3 / h[i - 1] * (ys[i] - ys[i - 1])
    l, mu, z = [1.0] * n, [0.0] * n, [0.0] * n
    for i in range(1, n - 1):
        l[i] = 2 * (xs[i + 1] - xs[i - 1]) - h[i - 1] * mu[i - 1]
        mu[i] = h[i] / l[i]; z[i] = (al[i] - h[i - 1] * z[i - 1]) / l[i]
    c, b, d = [0.0] * n, [0.0] * n, [0.0] * n
    for j in range(n - 2, -1, -1):
        c[j] = z[j] - mu[j] * c[j + 1]
        b[j] = (ys[j + 1] - ys[j]) / h[j] - h[j] * (c[j + 1] + 2 * c[j]) / 3
        d[j] = (c[j + 1] - c[j]) / (3 * h[j])
    def f(x):
        x = min(max(x, xs[0]), xs[-1])
        i = max(k for k in range(n - 1) if xs[k] <= x) if x < xs[-1] else n - 2
        dx = x - xs[i]
        return ys[i] + b[i] * dx + c[i] * dx * dx + d[i] * dx ** 3
    return f

X_BOARD = 0.56          # m, daggerboard / L-foil strut position
X_RUDDER_M = -0.01925   # m, rudder stock (quarter chord)
HW = ZB = ZT = None
L_HULL = 1.0


def configure(stations=None, spacing=None, trunk=None, **app):
    """(Re)define the hull and appendages, e.g. for the mini boat. Stations in mm, others in SI as the globals."""
    global STATIONS, HULL_SPACING, TRUNK, HW, ZB, ZT, L_HULL
    if stations is not None: STATIONS = stations
    if spacing is not None: HULL_SPACING = spacing
    if trunk is not None: TRUNK = trunk
    for k, v in app.items():
        assert k in globals(), k
        globals()[k] = v
    xs = [s[0] / 1000 for s in STATIONS]
    HW = spline(xs, [s[1] / 1000 for s in STATIONS])
    ZB = spline(xs, [s[2] / 1000 for s in STATIONS])
    ZT = spline(xs, [s[3] / 1000 for s in STATIONS])
    L_HULL = xs[-1]


configure()


def section(x):
    a, zb, zt = HW(x), ZB(x), ZT(x)
    return a, (zb + zt) / 2, (zt - zb) / 2, zb


def sub_area(x, zw):
    a, zc, b, zb = section(x)
    if zw <= zb: return 0.0
    t = min(1.0, (zw - zc) / b)
    return a * b * (t * math.sqrt(1 - t * t) + math.asin(t) + math.pi / 2)


def half_width(x, z):
    a, zc, b, _ = section(x)
    r = (z - zc) / b
    return a * math.sqrt(1 - r * r) if abs(r) < 1 else 0.0


def wet_girth(x, zw):
    a, zc, b, zb = section(x)
    if zw <= zb: return 0.0
    cw = max(-1.0, min(1.0, (zc - zw) / b)); th = math.acos(cw); n = 24
    return 2 * sum(math.sqrt((a * math.cos(th * (k + .5) / n)) ** 2 + (b * math.sin(th * (k + .5) / n)) ** 2) for k in range(n)) * th / n


def integrate(f, a, b, n=400):
    h = (b - a) / n
    return sum(f(a + (k + .5) * h) for k in range(n)) * h


def displaced_volume(zw):  # both hulls, minus flooded trunks
    v = integrate(lambda x: sub_area(x, zw), 0, L_HULL)
    trunk = TRUNK[0] * TRUNK[1] * max(0.0, zw - ZB(TRUNK[2] / 1000))
    return 2 * (v - trunk)


def sinkage(vol):
    lo, hi = min(ZB(L_HULL * i / 50) for i in range(51)) - 0.001, max(ZT(L_HULL * i / 50) for i in range(51))
    for _ in range(50):
        m = (lo + hi) / 2
        if displaced_volume(m) > vol: hi = m
        else: lo = m
    return (lo + hi) / 2


# ------------------------------------------------------------ foil sections
def naca(code, n=80):
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    up, lo = [], []
    for i in range(n + 1):
        x = 0.5 * (1 - math.cos(math.pi * i / n))
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4)
        if m and x < p: yc, dy = m / p ** 2 * (2 * p * x - x * x), 2 * m / p ** 2 * (p - x)
        elif m: yc, dy = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x * x), 2 * m / (1 - p) ** 2 * (p - x)
        else: yc, dy = 0.0, 0.0
        th = math.atan(dy)
        up.append((x - yt * math.sin(th), yc + yt * math.cos(th)))
        lo.append((x + yt * math.sin(th), yc - yt * math.cos(th)))
    return list(reversed(up)) + lo[1:]


def area_coeff(code):
    pts = naca(code); a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2  # x chord^2


def alpha_L0(code):
    m, p = int(code[0]) / 100, int(code[1]) / 10
    if not m: return 0.0
    n, s = 4000, 0.0
    for k in range(n):
        th = math.pi * (k + .5) / n; x = 0.5 * (1 - math.cos(th))
        dy = 2 * m / p ** 2 * (p - x) if x < p else 2 * m / (1 - p) ** 2 * (p - x)
        s += dy * (math.cos(th) - 1) * math.pi / n
    return -s / math.pi


def lift_slope(ar, e=0.85):
    return 2 * math.pi / (1 + 2 * math.pi / (math.pi * e * ar))


def cf_ittc(re):
    return 0.075 / (math.log10(max(re, 1e4)) - 2) ** 2


FOIL_FRICTION = 'turbulent'   # appendage friction line; 'transitional' is a sensitivity case (sensitivity.py, pitch_trim.py)


def cf_transitional(re):
    """Flat plate with a laminar start: Blasius below Re 5e5, Prandtl-Schlichting with the transition correction
    (A = 1700) above. At foil chord Re of 1-2e5 this is fully laminar, an optimistic bound on the ITTC line."""
    lam = 1.328 / math.sqrt(max(re, 1e3))
    return lam if re < 5e5 else max(lam, 0.455 / math.log10(re) ** 2.58 - 1700 / re)


def profile_drag(q, v, chord, span, tc):
    ff = 1 + 2 * tc + 60 * tc ** 4
    re = v * chord / NU
    return q * 2 * chord * span * (cf_transitional(re) if FOIL_FRICTION == 'transitional' else cf_ittc(re)) * ff


def induced(force, q, span, e=0.85):
    return force ** 2 / (q * math.pi * e * span ** 2) if span > 0 and q > 0 else 0.0


CL_SIDE_MAX = 0.8  # max side-force coefficient of a strut/board before it stalls and the boat drifts


def side_induced(force, q, chord, span):
    """Induced drag of a vertical surface carrying side force; force above stall capacity is leeway drift."""
    if span <= 0 or q <= 0: return 0.0
    return induced(min(abs(force), q * chord * span * CL_SIDE_MAX), q, span)


# --------------------------------------------------------- Michell integral
def michell(U, zw, catamaran=True, nx=100, nz=12, nu=2000, lam_max=60.0, halfwidth=None, xlen=None, zbot=None):
    """Wave resistance (N) for one demihull (or a catamaran pair). Frame: free surface at z = zw."""
    hwf = halfwidth or (lambda x, z: half_width(x, z))
    xlen = xlen if xlen is not None else L_HULL
    k0 = G / U ** 2
    zmin = zbot if zbot is not None else min(ZB(xlen * x / 50) for x in range(51))
    if zw <= zmin: return 0.0
    xe = [xlen * i / nx for i in range(nx + 1)]
    ze = [zmin + (zw - zmin) * j / nz for j in range(nz + 1)]
    zm = [(ze[j] + ze[j + 1]) / 2 for j in range(nz)]
    # Y_x per panel (piecewise constant), no transom jump (dry transom assumption)
    yx = [[(hwf(xe[i + 1], zm[j]) - hwf(xe[i], zm[j])) / (xe[i + 1] - xe[i]) for i in range(nx)] for j in range(nz)]
    umax = math.acosh(lam_max); du = umax / nu; tot = 0.0
    for k in range(nu):
        u = (k + .5) * du; lam = math.cosh(u); kx = lam * k0
        ex = [complex(math.cos(kx * x), math.sin(kx * x)) for x in xe]
        exi = [(ex[i + 1] - ex[i]) / (1j * kx) for i in range(nx)]
        kz = lam * lam * k0
        ez = [(math.exp(kz * (ze[j + 1] - zw)) - math.exp(kz * (ze[j] - zw))) / kz for j in range(nz)]
        s = 0j
        for j in range(nz):
            row = yx[j]; acc = 0j
            for i in range(nx):
                if row[i]: acc += row[i] * exi[i]
            s += ez[j] * acc
        f = abs(s) ** 2 * lam * lam  # (I^2+J^2) lambda^2 / sqrt(lam^2-1) * dlam, dlam = sqrt(lam^2-1) du
        if catamaran:
            ky = k0 * lam * math.sqrt(lam * lam - 1)
            step = k0 * HULL_SPACING / 2 * abs(2 * lam * lam - 1) / math.sqrt(max(lam * lam - 1, 1e-12)) * math.sinh(u) * du
            f *= 4 * math.cos(ky * HULL_SPACING / 2) ** 2 if step < 1.0 else 2.0
        tot += f * du
    return 4 * RHO * G ** 2 / (math.pi * U ** 2) * tot


def wigley_check():
    L, B, T = 1.0, 0.1, 0.0625
    hw = lambda x, z: (B / 2) * (1 - (2 * (x - 0.5)) ** 2) * (1 - (z / T) ** 2) if -T <= z <= 0 else 0.0
    yx = lambda x, z: (B / 2) * (-8 * (x - 0.5)) * (1 - (z / T) ** 2)
    yz = lambda x, z: (B / 2) * (1 - (2 * (x - 0.5)) ** 2) * (-2 * z / T ** 2)
    S = 2 * integrate(lambda x: integrate(lambda z: math.sqrt(1 + yx(x, z) ** 2 + yz(x, z) ** 2), -T, 0, 80), 0, 1, 300)
    rows = []
    for fn in (0.25, 0.30, 0.35, 0.40, 0.50):
        U = fn * math.sqrt(G * L)
        rw = michell(U, 0.0, catamaran=False, nx=120, nz=16, nu=3000, halfwidth=hw, zbot=-T)
        rows.append((fn, round(rw / (0.5 * RHO * U * U * S) * 1e3, 3)))
    return S, rows


# ----------------------------------------------------------------- the boat
class Boat:
    def __init__(self, cfg, cad):
        d = cad[cfg]
        self.cfg = cfg
        self.M = d['mass_g'] / 1000; self.W = self.M * G; self.lcg = d['lcg_mm']
        self.RM = self.W * HULL_SPACING / 2
        s = cad['sails']; self.A = sum(x['area_m2'] for x in s)
        self.ce_x = sum(x['area_m2'] * x['x_mm'] for x in s) / self.A          # mm
        self.ce_z = sum(x['area_m2'] * x['z_mm'] for x in s) / self.A / 1000
        self.AR = RIG_HEIGHT ** 2 / self.A; self.k = 1 / (math.pi * E_SAIL * self.AR)
        self.foiling = cfg == 'foiling'
        a_strut = area_coeff('0012') * STRUT_C ** 2
        self.app_vol = {  # m^3 per metre of immersed span, or absolute
            'strut': a_strut, 'rudder': area_coeff('0012') * RUDDER_C ** 2,
            'wing': area_coeff('4412') * WING_C ** 2 * WING_SPAN, 'el': area_coeff('0012') * EL_C ** 2 * EL_SPAN}
        self.a_main = lift_slope(WING_SPAN / WING_C); self.a_el = lift_slope(EL_SPAN / EL_C)
        self.cl_main = min(CL_USABLE, self.a_main * (math.radians(INC_MAIN_DEG) - alpha_L0('4412')))
        self.cl_el = min(CL_USABLE, self.a_el * math.radians(INC_EL_DEG))
        self.cl_main_flap = min(CL_USABLE, self.a_main * (math.radians(INC_MAIN_DEG) - alpha_L0('4412') + FLAP_TAU * math.radians(FLAP_TRAVEL_DEG)))
        self.share_el = (X_MAIN_FOIL - self.lcg) / (X_MAIN_FOIL - X_EL)
        self.S_main = 2 * WING_SPAN * WING_C; self.S_el = 2 * EL_SPAN * EL_C
        self.z_rud = Z_EL - RUDDER_BELOW_EL if self.foiling else Z_RUDDER    # foiling rudders end just below the elevators
        self._cache, self._rm, self._one = {}, {}, {}
        zw = -0.016
        for _ in range(5):  # static waterline (hull + appendage buoyancy)
            zw = sinkage((self.W - self.app_buoyancy(zw)) / (RHO * G))
        self.zw0 = zw
        z_res = zw - (zw - min(ZB(L_HULL * i / 50) for i in range(51))) / 2    # hull resistance centre
        self.h_pitch = self.ce_z - z_res
        self.rm_pitch = None   # {'1hull': N m, '2hull': N m} from stability.py; enables pitch-limited depowering
        self.vto = self.vfly_max = self.fly_limit = None
        if self.foiling:
            self.fly_range()

    def app_buoyancy(self, zw):
        v = 2 * self.app_vol['rudder'] * max(0.0, zw - self.z_rud)
        if self.foiling:
            v += 2 * (self.app_vol['strut'] * max(0.0, zw - Z_WING) + self.app_vol['wing'] + self.app_vol['el'])
        else:
            v += 2 * self.app_vol['strut'] * max(0.0, zw - Z_BOARD)
        return v * RHO * G

    def fly_trim(self, V, side_force=0.0):
        """Static trim of the flying boat in heave and pitch (analysis/pitch_trim.py explains the model).
        The sail drive equals the flying drag and acts at the centre of effort, the drag at the appendages: a bow-down
        couple that moves load from the elevators to the main foils. The fixed elevators set the pitch, the wand-driven
        flaps the main foils' lift, and the wand the bow height; depths and clearances follow from that attitude."""
        q = 0.5 * RHO * V * V; W = self.W
        xm, xe, xcg = X_MAIN_FOIL / 1000, X_EL / 1000, self.lcg / 1000
        a, c = xm - xcg, xcg - xe
        dm, de, t = Z_FLY - Z_WING, Z_FLY - self.z_rud, None
        for _ in range(3):
            Lm0, Le0 = (t['Lm'], t['Le']) if t else ((1 - self.share_el) * W, self.share_el * W)
            dm, de = max(0.0, dm), max(0.0, de)
            parts = [(profile_drag(q, V, WING_C, WING_SPAN, 0.12) * 2 + induced(Lm0 / 2, q, WING_SPAN) * 2, Z_WING),
                     (profile_drag(q, V, EL_C, EL_SPAN, 0.12) * 2 + induced(Le0 / 2, q, EL_SPAN) * 2, Z_EL),
                     (profile_drag(q, V, STRUT_C, dm, 0.12) * 2 + side_induced(0.35 * side_force, q, STRUT_C, dm) * 2, Z_WING + dm / 2),
                     (profile_drag(q, V, RUDDER_C, de, 0.12) * 2 + side_induced(0.15 * side_force, q, RUDDER_C, de) * 2, self.z_rud + de / 2),
                     (2 * 0.24 * q * ((0.12 * STRUT_C) ** 2 + (0.12 * RUDDER_C) ** 2), Z_WING + dm)]
            R = sum(x for x, _ in parts); zD = sum(x * z for x, z in parts) / R
            Mp = COUPLE_FACTOR * R * (self.ce_z - zD)
            Le = (W * a - Mp) / (a + c); Lm = W - Le
            cle, clm = Le / (q * self.S_el), Lm / (q * self.S_main)
            theta = cle / self.a_el - math.radians(INC_EL_DEG)
            delta = (clm / self.a_main - (math.radians(INC_MAIN_DEG) + theta - alpha_L0('4412'))) / FLAP_TAU
            hp = WAND_L * math.sin(math.radians(WAND_PHI0_DEG) - delta / GEAR - theta)
            H = hp - (X_PIVOT * math.sin(theta) + Z_PIVOT * math.cos(theta))
            Z = lambda x, z: H + x * math.sin(theta) + z * math.cos(theta)
            t = dict(V=V, R=R, Mp=Mp, Le=Le, Lm=Lm, cle=cle, clm=clm, theta=theta, delta=delta, hp=hp,
                     elD=-Z(xe, Z_EL), mD=-Z(xm, Z_WING), rudI=-Z(X_RUDDER_TIP, self.z_rud),
                     hull=min(Z(x, ZB(x)) for x in (L_HULL * i / 50 for i in range(51))))
            dm, de = t['mD'], t['rudI']
        # steering: the largest side force the sails can apply before heeling past RM_FRACTION, held by the trimmed rudders
        fy = RM_FRACTION * self.RM / self.heel_arm(True)
        a_s, a_r = 2 * STRUT_C * max(t['mD'], 0.0), 2 * RUDDER_C * max(t['rudI'], 0.0)
        if a_r > 0:
            clr = (a_s * X_BOARD + a_r * X_RUDDER_QC) / (a_s + a_r)
            f_r = fy * (self.ce_x / 1000 - clr) / (clr - X_RUDDER_QC)
            t['steer_deg'] = math.degrees(f_r / (q * a_r) / lift_slope(t['rudI'] / RUDDER_C))
        else:
            t['steer_deg'] = float('inf')
        why = ('foil lift limit' if abs(t['cle']) > CL_USABLE or t['clm'] > CL_USABLE else
               'flap travel' if abs(t['delta']) > math.radians(FLAP_TRAVEL_DEG) else
               'wand out of the water' if t['hp'] <= 0 else
               'elevator near the surface' if t['elD'] < 0.5 * EL_C else
               'main foil near the surface' if t['mD'] < 0.5 * WING_C else
               'rudder immersion' if t['rudI'] < RUDDER_MIN else
               'steering' if t['steer_deg'] > STEER_MAX_DEG else
               'hull touches the water' if t['hull'] < 0 else None)
        return dict(t, feasible=why is None, why=why)

    def fly_range(self):
        """Take-off = lowest speed with a feasible flying trim; the flying range ends where the trim stops being feasible."""
        prev = False
        self.vto, self.vfly_max, self.fly_limit = None, None, None
        v0 = math.floor(math.sqrt(2 * self.W / (RHO * CL_USABLE * (self.S_main + self.S_el))) / 0.04) * 0.04   # below this no lift is enough
        k = 0
        while v0 + 0.04 * k <= 6.0 + 1e-9:
            V = v0 + 0.04 * k
            t = self.fly_trim(V)
            if t['feasible']:
                if not prev:
                    lo, hi = V - 0.04, V
                    for _ in range(8):
                        m = (lo + hi) / 2
                        lo, hi = (lo, m) if self.fly_trim(m)['feasible'] else (m, hi)
                    self.vto = hi
                prev = True; self.vfly_max = V
            elif prev:
                self.fly_limit = t['why']
                break
            k += 1
        if self.fly_limit:
            lo, hi = self.vfly_max, self.vfly_max + 0.04
            for _ in range(8):
                m = (lo + hi) / 2
                lo, hi = (m, hi) if self.fly_trim(m)['feasible'] else (lo, m)
            self.vfly_max = lo

    def takeoff_speed(self):
        return self.vto if self.foiling else None

    def rm_fly(self, V):
        """Largest righting moment the foils can make while flying at V: the leeward main foil at its flap and lift limit,
        the windward one carrying the rest of the main-foil load (the fixed elevators take equal loads each side)."""
        V = min(V, self.vfly_max or V)
        key = round(V, 4)
        if key not in self._rm:
            t = self.fly_trim(V)
            q = 0.5 * RHO * V * V
            cl1 = min(CL_USABLE, self.a_main * (math.radians(INC_MAIN_DEG) + t['theta'] - alpha_L0('4412') + FLAP_TAU * math.radians(FLAP_TRAVEL_DEG)))
            lee = min(q * self.S_main / 2 * cl1, t['Lm'])
            self._rm[key] = max(0.0, 2 * lee - t['Lm']) * HULL_SPACING / 2
        return self._rm[key]

    def one_hull(self, V, N):
        """Resistance (N) of one hull carrying N newtons: the leeward hull skimming while the foils fly. Friction,
        transom term and single-hull Michell wave resistance, interpolated in hull_table() exactly as sim_core.js oneHull."""
        if N <= 0.01:
            return 0.0
        m2 = 2 * N / G                                      # the table is for both hulls: each carries half
        h = hull_at(m2)
        q = 0.5 * RHO * V * V
        S1, lwl, at1 = h['S'] / 2, h['lwl'], h['at'] / 2
        Rf = q * S1 * cf_ittc(V * max(lwl, 0.05) / NU) * 1.25
        Rw = wave_r(m2, V, 'rw1')
        fnt = V / math.sqrt(2 * G * at1 / (HW(0) + HW(0) * 0.9)) if at1 > 0 else 99
        return Rf + Rw + (q * at1 * 0.2 * (1 - 0.2 * fnt) if fnt < 5 else 0.0)

    def heel_arm(self, flying):
        if flying:  # water surface at the wand's design ride height; side force centred on the immersed struts
            zs = Z_FLY
            return self.ce_z - zs + (zs - Z_WING) / 2
        zw = self.zw0; zbot = Z_WING if self.foiling else Z_BOARD
        a_b, z_b = 2 * STRUT_C * (zw - zbot), (zw + zbot) / 2
        a_r, z_r = 2 * RUDDER_C * (zw - self.z_rud), (zw + self.z_rud) / 2
        a_h = 2 * integrate(lambda x: max(0.0, zw - ZB(x)), 0, L_HULL, 200)
        z_h = zw - 0.015
        return self.ce_z - (a_b * z_b + a_r * z_r + a_h * z_h) / (a_b + a_r + a_h)

    def resistance(self, V, side_force):
        """Returns (total drag N, info dict). Chooses flying branch when V >= takeoff speed."""
        q = 0.5 * RHO * V * V
        vto = self.takeoff_speed()
        info = {}
        if self.foiling and vto and V >= vto:
            t = self.fly_trim(min(V, self.vfly_max or V), side_force)
            # roll: the foils supply rm_fly; any larger heeling moment is taken by the leeward hull, which then carries N
            N = max(0.0, (abs(side_force) * self.heel_arm(True) - self.rm_fly(V)) / HULL_SPACING)
            R = t['R'] + (self.one_hull(V, N) if N > 0.01 else 0.0)
            info.update(mode='foiling' if N <= 0.01 else 'skimming', hull=N, wave=0.0, trim=t)
            return R, info
        key = round(V, 4)
        if key not in self._cache:
            lift = 0.0
            if self.foiling:
                lift = min(q * self.S_main * self.cl_main_flap, (1 - self.share_el) * self.W) + min(q * self.S_el * self.cl_el, self.share_el * self.W)
            zw, load = self.zw0, 0.0
            for _ in range(4):                              # hull load <-> draft, appendage buoyancy included
                load = max(0.0, self.W - lift - self.app_buoyancy(zw))
                zw = hull_at(load / G)['zw']
            h = hull_at(load / G)                           # hull_table(), interpolated as in sim/sim_core.js
            S, lwl, at = h['S'], h['lwl'], h['at']
            Rf = q * S * cf_ittc(V * max(lwl, 0.05) / NU) * 1.25 if load > 0 else 0.0
            Rw = wave_r(load / G, V)
            fnt = V / math.sqrt(2 * G * at / (2 * HW(0) + 2 * HW(0) * 0.9)) if at > 0 else 99
            Rtr = q * at * 0.2 * (1 - 0.2 * fnt) if fnt < 5 else 0.0
            self._cache[key] = (zw, lift, S, lwl, Rf, Rw, Rtr)
        zw, lift, S, lwl, Rf, Rw, Rtr = self._cache[key]
        zbot = Z_WING if self.foiling else Z_BOARD
        span_b = min(zw, ZB(X_BOARD)) - zbot
        span_r = zw - self.z_rud
        Dapp = (profile_drag(q, V, STRUT_C, span_b, 0.12) * 2 + profile_drag(q, V, RUDDER_C, span_r, 0.12) * 2
                + 2 * 0.24 * q * (0.12 * RUDDER_C) ** 2
                + side_induced(0.35 * side_force, q, STRUT_C, span_b) * 2 + side_induced(0.15 * side_force, q, RUDDER_C, span_r) * 2)
        if self.foiling:
            Lm = min(q * self.S_main * self.cl_main_flap, (1 - self.share_el) * self.W)
            Le = min(q * self.S_el * self.cl_el, self.share_el * self.W)
            Dapp += (profile_drag(q, V, WING_C, WING_SPAN, 0.12) * 2 + induced(Lm / 2, q, WING_SPAN) * 2
                     + profile_drag(q, V, EL_C, EL_SPAN, 0.12) * 2 + induced(Le / 2, q, EL_SPAN) * 2)
        info.update(mode='displacement' if not self.foiling else 'lifting', zw=zw, foil_lift=lift, S_wet=S, Lwl=lwl,
                    friction=Rf, wave=Rw, transom=Rtr, appendages=Dapp)
        return Rf + Rw + Rtr + Dapp, info

    def sail(self, V, tws, twa_deg):
        twa = math.radians(twa_deg)
        vx, vy = V + tws * math.cos(twa), tws * math.sin(twa)   # apparent wind components (boat frame)
        va = math.hypot(vx, vy); beta = math.atan2(vy, vx)
        qa = 0.5 * RHO_A * va * va * self.A
        return va, beta, qa

    def forces(self, V, tws, twa_deg, flying, cl_frac=1.0):
        """Sail forces; cl_frac < 1 eases the sails (used when easing lets a skimming boat accelerate onto its foils)."""
        va, beta, qa = self.sail(V, tws, twa_deg)
        h = self.heel_arm(flying)
        fy_max = RM_FRACTION * self.RM / h      # flying too: beyond the foils' roll authority the leeward hull skims (resistance)
        if beta > math.pi / 2:  # past a beam reach the sails progressively stall: blend to CD = 1.2 at 180 deg
            f = (beta - math.pi / 2) / (math.pi / 2)
            clm = CL_MAX * cl_frac
            cl = clm * (1 - f); cd = (CD0_SAIL + self.k * clm ** 2) * (1 - f) + 1.2 * f
            fx = qa * (cl * math.sin(beta) - cd * math.cos(beta)); fy = qa * (cl * math.cos(beta) + cd * math.sin(beta))
            return fx, fy, dict(va=va, awa=math.degrees(beta), cl=cl, depowered=cl_frac < 1, heel_util=abs(fy) * h / self.RM)
        cl = min(CL_MAX, math.tan(beta) / (2 * self.k)) * cl_frac
        heel = lambda c: qa * (c * math.cos(beta) + (CD0_SAIL + self.k * c * c) * math.sin(beta))
        depowered = cl_frac < 1
        if heel(cl) > fy_max:
            depowered = True
            a_, b_, c_ = self.k * math.sin(beta), math.cos(beta), CD0_SAIL * math.sin(beta) - fy_max / qa
            disc = b_ * b_ - 4 * a_ * c_
            cl = max(0.0, (-b_ + math.sqrt(disc)) / (2 * a_)) if disc >= 0 and a_ > 0 else 0.0
        cd = CD0_SAIL + self.k * cl * cl
        fx = qa * (cl * math.sin(beta) - cd * math.cos(beta))
        fy = qa * (cl * math.cos(beta) + cd * math.sin(beta))
        return fx, fy, dict(va=va, awa=math.degrees(beta), cl=cl, depowered=depowered, heel_util=fy * h / self.RM)

    def pitch_limit(self, fx, fy, s, flying):
        """Ease the sails (scale both forces) so the bow-down moment stays within 90 % of the hulls' limit.
        Like a skipper, take the better of: sailing flat on both hulls (larger pitch limit), or flying the
        windward hull (more heel allowed, one-hull pitch limit)."""
        if not self.rm_pitch or flying or fx <= 0:
            return fx, fy, s
        u = abs(s['heel_util'])
        m = fx * self.h_pitch
        k_flat = min(1.0, (0.8 / u) if u > 0.8 else 1.0, RM_FRACTION * self.rm_pitch['2hull'] / m)
        k = k_flat
        if u > 0.8:
            k_fly = min(1.0, RM_FRACTION * self.rm_pitch['1hull'] / m)
            if u * k_fly > 0.8:
                k = max(k_flat, k_fly)
        if k < 1.0:
            fx, fy = fx * k, fy * k
            s = dict(s, depowered=True, pitch_limited=True, heel_util=s['heel_util'] * k)
        return fx, fy, s

    def solve(self, tws, twa_deg, vmax=6.0, dv=0.02):     # same search limit as sim/sim_core.js solve()
        vto = self.takeoff_speed()
        V, last = dv, None
        while V < vmax:
            flying = bool(vto and V >= vto)
            if flying and self.vfly_max is not None and V > self.vfly_max:   # faster than the foils can be trimmed: ease the sails
                fx, fy, s = self.pitch_limit(*self.forces(self.vfly_max, tws, twa_deg, True), True)
                s = dict(s, depowered=True, trim_limited=True)
                return dict(V=round(self.vfly_max, 3), mode='foiling', **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()})
            fx, fy, s = self.pitch_limit(*self.forces(V, tws, twa_deg, flying), flying)
            R, info = self.resistance(V, fy)
            if flying and info['mode'] == 'skimming' and fx - R < 0:   # ease the sails if that lets the boat accelerate onto its foils
                best = (fx - R, fx, fy, s, R, info)
                for k in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1):
                    fx2, fy2, s2 = self.forces(V, tws, twa_deg, True, k)
                    R2, info2 = self.resistance(V, fy2)
                    if fx2 - R2 > best[0]:
                        best = (fx2 - R2, fx2, fy2, s2, R2, info2)
                _, fx, fy, s, R, info = best
            if fx - R < 0:
                return dict(V=round(V - dv / 2, 3), mode=(last or info)['mode'], **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()})
            last = info
            V += dv
        return dict(V=vmax, mode='>vmax')


TABLE_MASSES = [round(0.2 * i, 1) for i in range(19)]        # kg carried by both hulls, 0 .. 3.6
TABLE_SPEEDS = [round(0.1 * j, 1) for j in range(1, 46)]      # m/s, 0.1 .. 4.5
_TABLE = {}


def interp_clamped(xs, ys, x):
    """Linear interpolation, clamped at the ends (sim_core.js interp1)."""
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = 0
    while xs[i + 1] < x:
        i += 1
    return ys[i] + (x - xs[i]) / (xs[i + 1] - xs[i]) * (ys[i + 1] - ys[i])


def hull_at(m):
    """Draft, wetted area, waterline length and transom area with both hulls carrying m kg (hull_table())."""
    T = hull_table()
    return {k: interp_clamped(T['masses'], [r[k] for r in T['rows']], m) for k in ('zw', 'S', 'lwl', 'at')}


def wave_r(m, V, key='rw'):
    """Michell wave resistance (N), bilinear in hull load and speed (sim_core.js waveR); key 'rw1' for one hull."""
    if m <= 0 or V < 0.3:
        return 0.0
    T = hull_table()
    HM, rows = T['masses'], T['rows']
    i = 0
    while i < len(HM) - 2 and HM[i + 1] < m:
        i += 1
    tm = min(1.0, max(0.0, (m - HM[i]) / (HM[i + 1] - HM[i])))
    a, b = interp_clamped(T['speeds'], rows[i][key], V), interp_clamped(T['speeds'], rows[i + 1][key], V)
    return a + tm * (b - a)


def hull_table():
    """Hull resistance table by the load both hulls carry and speed (the simulator's hull table): draft, wetted area,
    waterline length, transom area, catamaran and single-hull Michell wave resistance. Built once per hull shape
    (about 7 minutes of Michell integrals) and cached in analysis/hull_table_<hash>.json."""
    sig = hashlib.md5(json.dumps([[round(v, 6) for v in section(L_HULL * i / 40)] for i in range(41)] + [L_HULL]).encode()).hexdigest()[:10]
    if sig in _TABLE:
        return _TABLE[sig]
    path = os.path.join(HERE, f'hull_table_{sig}.json')
    if os.path.exists(path):
        _TABLE[sig] = json.load(open(path))
        return _TABLE[sig]
    zmin = min(ZB(L_HULL * i / 50) for i in range(51))
    rows = []
    for m in TABLE_MASSES:
        zw = sinkage(m / RHO) if m > 0 else zmin
        wet = [x for x in (L_HULL * i / 400 for i in range(401)) if ZB(x) < zw]
        rows.append(dict(m=m, zw=zw, S=2 * integrate(lambda x: wet_girth(x, zw), 0, L_HULL, 300) if m > 0 else 0.0,
                         lwl=(max(wet) - min(wet)) if wet else 0.0, at=2 * sub_area(0.0, zw) if m > 0 else 0.0,
                         rw=[michell(V, zw) if (m > 0 and V >= 0.3) else 0.0 for V in TABLE_SPEEDS],
                         rw1=[michell(V, zw, catamaran=False) if (m > 0 and V >= 0.3) else 0.0 for V in TABLE_SPEEDS]))
    _TABLE[sig] = dict(masses=TABLE_MASSES, speeds=TABLE_SPEEDS, zmin=zmin, rows=rows)
    json.dump(_TABLE[sig], open(path, 'w'))
    return _TABLE[sig]


def load_pitch_limits(boat, key, path=None):
    path = path or os.path.join(HERE, 'stability_results.json')
    if os.path.exists(path):
        st = json.load(open(path)).get(key)
        if st:
            boat.rm_pitch = {'1hull': st['pitch_1hull']['RM_L_max_Nm'], '2hull': st['pitch_2hull']['RM_L_max_Nm']}
    return boat


def main():
    cad = json.load(open(os.path.join(HERE, 'cad_data.json')))
    out = {}
    # 1) hull statics check against the CAD loft volume (v1.3 loft before cuts and shell, read in Fusion 2026-09-24)
    CAD_LOFT_CM3 = 5584.0
    full = integrate(lambda x: section(x)[0] * section(x)[2] * math.pi, 0, 1, 800)
    out['hull_volume_check'] = dict(analytic_cm3=round(full * 1e6, 1), cad_cm3=CAD_LOFT_CM3, error_pct=round((full * 1e6 / CAD_LOFT_CM3 - 1) * 100, 2))
    # 2) Michell implementation check on the Wigley hull
    S, rows = wigley_check()
    out['wigley_michell_Cw_x1e3'] = dict(S_m2=round(S, 4), rows=rows)
    boats = {c: load_pitch_limits(Boat(c, cad), 'build_first_1m' if c == 'displacement' else 'foiling_1m') for c in ('displacement', 'foiling')}
    fb = boats['foiling']
    out['foil'] = dict(cl_main=round(fb.cl_main, 3), cl_el=round(fb.cl_el, 3), elevator_share=round(fb.share_el, 3),
                       takeoff_speed_ms=round(fb.takeoff_speed(), 3))
    # 3) resistance curves
    curves = {}
    for c, b in boats.items():
        rows = []
        for i in range(2, 31):
            V = i * 0.1
            R, info = b.resistance(V, 0.0)
            rows.append(dict(V=round(V, 2), Fn=round(V / math.sqrt(G * 0.95), 3), R=round(R, 3),
                             **{k: round(v, 4) if isinstance(v, float) else v for k, v in info.items()}))
        curves[c] = rows
    out['resistance'] = curves
    # 4) VPP
    vpp = {}
    for c, b in boats.items():
        tab = {}
        for twa in (60, 75, 90, 105):
            tab[twa] = [dict(tws_kn=tws, **b.solve(tws * 0.5144, twa)) for tws in range(3, 17)]
        vpp[c] = tab
    out['vpp'] = vpp
    for c, b in boats.items():
        out.setdefault('meta', {})[c] = dict(mass_kg=b.M, RM_Nm=round(b.RM, 3), sail_area=round(b.A, 4), AR=round(b.AR, 2),
                                             heel_arm_disp=round(b.heel_arm(False), 3), heel_arm_fly=round(b.heel_arm(True), 3))
    json.dump(out, open(os.path.join(HERE, 'vpp_results.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    import sys
    r = main()
    print(json.dumps({k: r[k] for k in ('hull_volume_check', 'wigley_michell_Cw_x1e3', 'foil', 'meta')}, indent=1))
    for c in ('displacement', 'foiling'):
        print('\n==', c, 'resistance (N) at zero side force')
        for row in r['resistance'][c]:
            print(row['V'], row['Fn'], row['R'], row['mode'], 'wave', round(row.get('wave', 0), 3), 'fric', round(row.get('friction', 0), 3), 'app', round(row.get('appendages', 0), 3))
        print('\n==', c, 'VPP boat speed m/s (mode)')
        for twa, rows in r['vpp'][c].items():
            print('TWA', twa, ' '.join(f"{x['tws_kn']}kn:{x['V']}{'F' if x['mode']=='foiling' else ''}{'*' if x.get('depowered') else ''}" for x in rows))
