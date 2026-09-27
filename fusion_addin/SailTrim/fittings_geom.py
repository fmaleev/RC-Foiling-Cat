"""Printed rig fittings of the 1 m boat shared by the Sail Trim add-in (the traveler and jib cars move with the trim)
and cad_scripts/rig_fittings.py (tracks, end stops and the other static fittings). mm, boat frame (x forward from
the transoms, z up). The constants import without Fusion; the builders need adsk.

Traveler: a printed T-rail track bonded on the rear beam (16 mm tube, axis x 180, z 62), in three pieces; the car
slides on the rail. One continuous traveler line runs from the winch drum to the port end-stop pin, through the car
(fixed there with a drop of CA), to the starboard pin and back to the drum. The mainsheet is dead-ended on the port
pin, runs through the car's port post, up to the boom and back down, through the starboard post, round the starboard
pin and into the pod. Jib: a shorter T-rail on the pod lid; the sheet comes up through the lid at the track centre,
runs along the track through the car and up to the clew.
"""
BEAM_X, BEAM_Z, BEAM_R = 180.0, 62.0, 8.0
TT_TOP, TT_HALF_W = 72.0, 3.5          # track saddle top z (2 mm over the beam), half width
TT_STEM, TT_HEAD = (1.0, 1.4), (3.0, 1.6)   # rail stem and head: (half width, height)
TT_END, TT_STOP, TT_SPLIT = 234.0, 222.0, 76.0   # track ends (2 mm inside the hull walls), end-stop faces, joints (|y|)
CLR = 0.2                              # sliding clearance
TC_HX, TC_HY, TC_TOP, TC_POST_TOP = 5.5, 9.0, 82.0, 88.0
LINE_X = 181.6                         # lines run just aft of the turning pins
Z_TRAV, Z_MAIN = 79.0, 85.0            # traveler line and mainsheet heights
PIN = (183.0, 228.0, 2.5)              # 0.093 in wire turning pin in each end stop: x, |y|, hole diameter
CAR_LIMIT = TT_STOP - TC_HY            # 213 mm: car centre travel each side

JT_X, JT_Z0, JT_END, JT_STOP = 590.0, 121.2, 48.0, 43.5   # jib track on the pod lid (lid top z 121.2)
JT_BASE, JT_STEM, JT_HEAD = (5.0, 0.8), (1.0, 1.4), (3.0, 1.4)   # (half width, height)
JC_HX, JC_HY, JC_H = 7.0, 7.0, 5.0     # jib car: bottom at JT_Z0 + base + CLR, top 127.2 (boom underside 128)
JC_SHEET = (595.2, 124.5, 1.6)         # sheet hole along y: x, z, diameter
JIB_HALF_TRAVEL = JT_STOP - JC_HY - 0.5

# wing mast (rig_fittings.py): printed fairing shells over the 12 mm tube, gooseneck at the foot, main laced to the TE
FAIR_WALL, LACING_PITCH, LACING_IN = 0.45, 50.0, 4.0   # shell wall; lacing holes every 50 mm, 4 mm ahead of the TE
HOUNDS_GAP = (994.0, 1006.0)                           # fairing gap for the hounds collar (hounds at z 1000)
GOOSE_Z, BOOM_PIN_AFT, BOOM_TUBE_X0 = (125.0, 141.0), 4.5, 586.0   # gooseneck; boom pin behind the TE; boom tube front x


def _t():
    import adsk.fusion
    return adsk.fusion.TemporaryBRepManager.get()


def box(x0, x1, y0, y1, z0, z1):
    import adsk.core
    return _t().createBox(adsk.core.OrientedBoundingBox3D.create(
        adsk.core.Point3D.create((x0 + x1) / 20, (y0 + y1) / 20, (z0 + z1) / 20), adsk.core.Vector3D.create(1, 0, 0),
        adsk.core.Vector3D.create(0, 1, 0), abs(x1 - x0) / 10, abs(y1 - y0) / 10, abs(z1 - z0) / 10))


def cyl(p0, p1, r):
    import adsk.core
    P = lambda p: adsk.core.Point3D.create(p[0] / 10, p[1] / 10, p[2] / 10)
    return _t().createCylinderOrCone(P(p0), r / 10, P(p1), r / 10)


def union(parts):
    import adsk.fusion
    out = parts[0]
    for p in parts[1:]:
        _t().booleanOperation(out, p, adsk.fusion.BooleanTypes.UnionBooleanType)
    return out


def minus(body, tools):
    import adsk.fusion
    for t in tools:
        _t().booleanOperation(body, t, adsk.fusion.BooleanTypes.DifferenceBooleanType)
    return body


def traveler_rail(y0, y1):
    (sw, sh), (hw, hh) = TT_STEM, TT_HEAD
    return union([box(BEAM_X - sw, BEAM_X + sw, y0, y1, TT_TOP, TT_TOP + sh),
                  box(BEAM_X - hw, BEAM_X + hw, y0, y1, TT_TOP + sh, TT_TOP + sh + hh)])


def traveler_car(yc):
    """Car centred on y = yc: T-slot for the rail, traveler line hole with a CA access hole, two mainsheet posts."""
    (sw, sh), (hw, hh) = TT_STEM, TT_HEAD
    x, y0, y1, z0 = BEAM_X, yc - TC_HY, yc + TC_HY, TT_TOP + CLR
    body = union([box(x - TC_HX, x + TC_HX, y0, y1, z0, TC_TOP)] +
                 [box(LINE_X - 3, LINE_X + 3, yc + s * 3, yc + s * 6, TC_TOP - 0.5, TC_POST_TOP) for s in (1, -1)])
    zh = TT_TOP + sh - CLR                 # underside of the rail head, less clearance
    return minus(body, [box(x - sw - CLR, x + sw + CLR, y0 - 1, y1 + 1, z0 - 1, zh),
                        box(x - hw - CLR, x + hw + CLR, y0 - 1, y1 + 1, zh, TT_TOP + sh + hh + CLR),
                        cyl((LINE_X, y0 - 1, Z_TRAV), (LINE_X, y1 + 1, Z_TRAV), 0.8),
                        cyl((LINE_X, yc, Z_TRAV), (LINE_X, yc, TC_TOP + 1), 0.8),
                        cyl((LINE_X, y0 - 1, Z_MAIN), (LINE_X, y1 + 1, Z_MAIN), 1.0)])


def jib_rail(y0, y1):
    (bw, bh), (sw, sh), (hw, hh) = JT_BASE, JT_STEM, JT_HEAD
    z = JT_Z0 + bh
    return union([box(JT_X - sw, JT_X + sw, y0, y1, z, z + sh), box(JT_X - hw, JT_X + hw, y0, y1, z + sh, z + sh + hh)])


def jib_car(yc):
    (bw, bh), (sw, sh), (hw, hh) = JT_BASE, JT_STEM, JT_HEAD
    z0 = JT_Z0 + bh + CLR
    zh = JT_Z0 + bh + sh - CLR
    body = box(JT_X - JC_HX, JT_X + JC_HX, yc - JC_HY, yc + JC_HY, z0, z0 + JC_H)
    sx, sz, sd = JC_SHEET
    return minus(body, [box(JT_X - sw - CLR, JT_X + sw + CLR, yc - JC_HY - 1, yc + JC_HY + 1, z0 - 1, zh),
                        box(JT_X - hw - CLR, JT_X + hw + CLR, yc - JC_HY - 1, yc + JC_HY + 1, zh, JT_Z0 + bh + sh + hh + CLR),
                        cyl((sx, yc - JC_HY - 1, sz), (sx, yc + JC_HY + 1, sz), sd / 2)])
