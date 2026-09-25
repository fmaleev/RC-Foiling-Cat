"""v2.1 foils: the speed design from the flight-simulator study (sim/optimize.js, paper Section 6). Run inside Fusion via
MCP exec on the foiling master: apply(design). Replaces the 'Foiling Kit' component:
- L-foils: NACA 0012 strut, 60 mm chord (unchanged), from inside the wing up to the deck; NACA 4412 wing, 160 mm span
  inboard of the strut, 40 mm chord, 0 deg incidence, chord line at z = -220 mm, quarter chord at x = 575 mm (as v2.0).
- Flaps: the aft 25 % of the wing chord, from 10 mm inside the tip to the strut (0.5 mm gaps), so the wand's flap horn
  (Ride Height Control) sits on the flap and not on the fixed wing.
- A 2.4 mm channel down each strut for the strut pushrod.
- Elevators: NACA 0012 T-foils on the rudders, 140 mm span, 32 mm chord, 4 deg nose up, quarter chord at x = -15 mm.
The ride-height linkage (component 'Ride Height Control') is unchanged: its horn still sits on the flap root.
"""
import adsk.core, adsk.fusion, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'analysis'))
import build_mini as bm
import servo_mounts as sm
import vpp

HULL_Y = 280.0
STRUT = dict(chord=60.0, le_x=590.0, z0=-221.0, z1=75.0)
WING = dict(chord=40.0, qc_x=575.0, span=160.0, inc=0.0, z=-220.0)
FLAP = dict(ratio=0.25, tip_gap=10.0, root_y=275.5, gap=0.5)      # strut face at about y = 277 at the flap chord
PUSHROD = ((566.0, 80.0), (547.0, -214.0), 1.2)                    # (x, z) top and bottom of the strut pushrod, channel radius
ELEV = dict(chord=32.0, qc_x=-15.0, span=140.0, inc=4.0, z=-197.0)


def section(code, chord, qc_x, z_qc, inc_deg):
    """Model-space (x, z) points of a NACA section; leading edge forward (+x), nose up by inc_deg about the quarter chord."""
    a = math.radians(inc_deg)
    le_x = qc_x + 0.25 * chord
    pts = []
    for u, t in vpp.naca(code, 60):
        dx, dz = (le_x - u * chord) - qc_x, t * chord
        pts.append((qc_x + dx * math.cos(a) - dz * math.sin(a), z_qc + dx * math.sin(a) + dz * math.cos(a)))
    return pts


def horizontal_foil(comp, name, code, chord, qc_x, z_qc, inc, y_mid, span, op, bodies=None):
    sk = comp.sketches.add(bm.plane_at(comp, comp.xZConstructionPlane, y_mid))
    sk.name = name + ' Section'
    col = adsk.core.ObjectCollection.create()
    for x, z in section(code, chord, qc_x, z_qc, inc):
        col.add(sk.modelToSketchSpace(bm.P(x, y_mid, z)))
    sp = sk.sketchCurves.sketchFittedSplines.add(col)
    sk.sketchCurves.sketchLines.addByTwoPoints(sp.endSketchPoint, sp.startSketchPoint)
    sk.isVisible = False
    return bm.sym(comp, [sk.profiles.item(0)], span, op, bodies)


def apply(design):
    root = design.rootComponent
    ops = adsk.fusion.FeatureOperations
    old = [o for o in root.occurrences if o.component.name == 'Foiling Kit'][0]
    look = old.component.bRepBodies.itemByName('L-Foil Port').appearance
    old.deleteMe()
    comp = bm.new_comp(root, 'Foiling Kit')
    tbm = adsk.fusion.TemporaryBRepManager.get()
    flaps = []
    for side, s in (('Port', 1), ('Stbd', -1)):
        yc = s * HULL_Y
        lf = bm.vertical_foil(comp, f'L-Foil {side}', STRUT['chord'], STRUT['le_x'], yc, STRUT['z0'], STRUT['z1'])
        horizontal_foil(comp, f'L-Foil {side} Wing', '4412', WING['chord'], WING['qc_x'], WING['z'], WING['inc'],
                        s * (HULL_Y - WING['span'] / 2), WING['span'], ops.JoinFeatureOperation, [lf])
        # flap: aft 25 % of the chord over the outer span, cut out of the wing with a hinge gap
        te_x = WING['qc_x'] - 0.75 * WING['chord']
        hinge_x = te_x + FLAP['ratio'] * WING['chord']
        tip = HULL_Y - WING['span']
        y0, y1 = sorted((s * (tip + FLAP['tip_gap']), s * FLAP['root_y']))
        f = tbm.copy(lf)
        tbm.booleanOperation(f, bm.tbox(te_x - 5, hinge_x - FLAP['gap'] / 2, y0, y1, WING['z'] - 20, WING['z'] + 20), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        flaps.append((f'Flap {side}', f))
        sm.combine(comp, f'L-Foil {side}', f'Flap Cut {side}', [bm.tbox(te_x - 5, hinge_x + FLAP['gap'] / 2, y0 - FLAP['gap'], y1 + FLAP['gap'],
                                                                         WING['z'] - 20, WING['z'] + 20)], ops.CutFeatureOperation)
        (xt, zt), (xb, zb), rc = PUSHROD
        k = 3.0 / math.hypot(xt - xb, zt - zb)
        sm.combine(comp, f'L-Foil {side}', f'Pushrod Channel {side}', [bm.tcyl((xt + (xt - xb) * k, yc, zt + (zt - zb) * k), (xb - (xt - xb) * k, yc, zb - (zt - zb) * k), rc)],
                   ops.CutFeatureOperation)
        el = horizontal_foil(comp, f'Elevator {side}', '0012', ELEV['chord'], ELEV['qc_x'], ELEV['z'], ELEV['inc'], yc, ELEV['span'],
                             ops.NewBodyFeatureOperation).bodies.item(0)
        el.name = f'Elevator {side}'
    bm.base_bodies(comp, flaps)
    for b in comp.bRepBodies:
        b.appearance = look
    return {b.name: (round(b.volume, 2), b.lumps.count, [round(v * 10, 1) for v in (b.boundingBox.minPoint.x, b.boundingBox.minPoint.y, b.boundingBox.minPoint.z,
                                                                                      b.boundingBox.maxPoint.x, b.boundingBox.maxPoint.y, b.boundingBox.maxPoint.z)])
            for b in comp.bRepBodies}
