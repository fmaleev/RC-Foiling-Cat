"""v2.2 foils: the design chosen by the pitch-trim foil study (sim/optimize.js with the flying trim in heave and pitch,
paper Section 6). Run inside Fusion via MCP exec on the foiling master: apply(design, FOILS). It
- rebuilds the 'Foiling Kit' component like foils_v21.py (L-foils with a NACA 0012 strut and a NACA 4412 wing, flaps from
  10 mm inside the tip to the strut with 0.5 mm gaps, a 2.4 mm pushrod channel down each strut, NACA 0012 T-foil
  elevators), with the sizes and incidences of FOILS;
- lowers the elevators to FOILS['zel'] (quarter-chord height, boat frame) and adds a 'Rudder Extension' body under each
  rudder blade down to 3 mm below them, so the elevators stay at the rudder tips (the v2.1 elevators, 45 mm deep when
  flying level, came out of the water once the sail drive pitched the boat nose-down).
The ride-height linkage (component 'Ride Height Control') is unchanged: its horn still sits on the flap root.
"""
import adsk.core, adsk.fusion, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mini as bm
import servo_mounts as sm
import foils_v21 as f21

FOILS = dict(wspan=160.0, wchord=45.0, winc=1.5, espan=120.0, echord=28.0, einc=-1.0, zel=-210.0)   # sim/optimize.js 'adopted' (2026-09-24)
HULL_Y = f21.HULL_Y
STRUT, FLAP, PUSHROD = f21.STRUT, f21.FLAP, f21.PUSHROD
WING_QC_X, WING_Z, ELEV_QC_X = 575.0, -220.0, -15.0


def rudder_extensions(design, comp, zel):
    """Foiling rudder blades end 3 mm below the elevators. The 'Rudders' component is shared with the build-first boat
    (the mass export of both configurations reads this master), so the extra blade length is a separate body per side in
    the 'Foiling Kit': a NACA 0012 prism with the blade's section from the blade tip down to zel - 3 mm."""
    rud = [o.component for o in design.rootComponent.allOccurrences if o.component.name == 'Rudders'][0]
    out = {}
    for side in ('Port', 'Stbd'):
        bb = rud.bRepBodies.itemByName(f'Rudder Blade {side}').boundingBox
        x0, x1 = bb.minPoint.x * 10, bb.maxPoint.x * 10
        yc = (bb.minPoint.y + bb.maxPoint.y) * 5
        z_top, z_new = bb.minPoint.z * 10, zel - 3.0
        if z_top - z_new > 0.01:
            bm.vertical_foil(comp, f'Rudder Extension {side}', x1 - x0, x1, yc, z_new, z_top)
        out[side] = round(z_new, 2)
    return out


def apply(design, foils):
    root = design.rootComponent
    ops = adsk.fusion.FeatureOperations
    old = [o for o in root.occurrences if o.component.name == 'Foiling Kit'][0]
    look = old.component.bRepBodies.itemByName('L-Foil Port').appearance
    old.deleteMe()
    comp = bm.new_comp(root, 'Foiling Kit')
    tbm = adsk.fusion.TemporaryBRepManager.get()
    wc, ws = foils['wchord'], foils['wspan']
    flaps = []
    for side, s in (('Port', 1), ('Stbd', -1)):
        yc = s * HULL_Y
        lf = bm.vertical_foil(comp, f'L-Foil {side}', STRUT['chord'], STRUT['le_x'], yc, STRUT['z0'], STRUT['z1'])
        f21.horizontal_foil(comp, f'L-Foil {side} Wing', '4412', wc, WING_QC_X, WING_Z, foils['winc'],
                            s * (HULL_Y - ws / 2), ws, ops.JoinFeatureOperation, [lf])
        te_x = WING_QC_X - 0.75 * wc
        hinge_x = te_x + FLAP['ratio'] * wc
        tip = HULL_Y - ws
        y0, y1 = sorted((s * (tip + FLAP['tip_gap']), s * FLAP['root_y']))
        f = tbm.copy(lf)
        tbm.booleanOperation(f, bm.tbox(te_x - 5, hinge_x - FLAP['gap'] / 2, y0, y1, WING_Z - 20, WING_Z + 20), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        flaps.append((f'Flap {side}', f))
        sm.combine(comp, f'L-Foil {side}', f'Flap Cut {side}', [bm.tbox(te_x - 5, hinge_x + FLAP['gap'] / 2, y0 - FLAP['gap'], y1 + FLAP['gap'],
                                                                         WING_Z - 20, WING_Z + 20)], ops.CutFeatureOperation)
        (xt, zt), (xb, zb), rc = PUSHROD
        k = 3.0 / math.hypot(xt - xb, zt - zb)
        sm.combine(comp, f'L-Foil {side}', f'Pushrod Channel {side}', [bm.tcyl((xt + (xt - xb) * k, yc, zt + (zt - zb) * k), (xb - (xt - xb) * k, yc, zb - (zt - zb) * k), rc)],
                   ops.CutFeatureOperation)
        el = f21.horizontal_foil(comp, f'Elevator {side}', '0012', foils['echord'], ELEV_QC_X, foils['zel'], foils['einc'], yc, foils['espan'],
                                 ops.NewBodyFeatureOperation).bodies.item(0)
        el.name = f'Elevator {side}'
    bm.base_bodies(comp, flaps)
    for b in comp.bRepBodies:
        b.appearance = look
    rud = rudder_extensions(design, comp, foils['zel'])
    for n in ('Rudder Extension Port', 'Rudder Extension Stbd'):
        b = comp.bRepBodies.itemByName(n)
        if b:
            b.appearance = [o.component for o in design.rootComponent.allOccurrences if o.component.name == 'Rudders'][0].bRepBodies.itemByName('Rudder Blade Port').appearance
    return dict(rudder_bottom_mm=rud, bodies={b.name: (round(b.volume, 2), b.lumps.count, [round(v * 10, 1) for v in (b.boundingBox.minPoint.x, b.boundingBox.minPoint.y, b.boundingBox.minPoint.z,
                                                                                                            b.boundingBox.maxPoint.x, b.boundingBox.maxPoint.y, b.boundingBox.maxPoint.z)])
                                                for b in comp.bRepBodies})
