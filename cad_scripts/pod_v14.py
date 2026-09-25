"""v1.4 pod: clears the traveler and jib cars. Run inside Fusion via MCP exec: apply(design), after
servo_mounts.patch(design, 'full'), with the hulls built by build_full_hull (third socket for the pod beam).

The v1.3 pod ran from x = 160 to 840 mm over both crossbeams. The traveler car could not pass the centreline on the
rear beam, and with the boom inside about 7.5 deg the mainsheet (clew at x = 259 mm, 124 mm up, down to the car on
the beam) ran through the pod lid. The jib car on the front beam sat inside the pod for jib angles under about 12 deg.

v1.4: the pod ends in a flat transom at x = 270 mm, and its aft end rests on a light third crossbeam (10 mm carbon)
at x = 350 mm, which no mainsheet position reaches. The top of the rear beam stays clear for the traveler track, so
the rudder servo goes on a small printed bracket epoxied to the rear beam below the track (a 240 deg clamp open at
the top), under a printed cover. The mainsheet servo moves forward to x = 301 mm and the three control lines leave
through the transom. The jib track moves onto the lid (rig_model).
"""
import adsk.core, adsk.fusion, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_mini as bm
import servo_mounts as sm

AFT, WALL, F, Z0, Z1, HW, FIL = 270.0, 1.2, 71.2, 70.0, 120.0, 45.0, 12.0
MAIN_X = 301.0
BEAM = (180.0, 62.0)                                     # rear beam axis x, z (16 mm tube)
POD_BEAM = (350.0, 65.0, 5.0)                            # third beam x, axis z, radius; its top touches the pod bottom
# bracket: deck carrying the MG90S aft of the rear beam; clamp r 8.2-11.2 mm open over the top 120 deg
BRACKET = dict(z0=46.5, z1=50.5, x0=118.0, deck=(172.0, 23.0), r_in=8.2, r_out=11.2, open_deg=30.0, servo_x=142.0)
EXITS = [(-14.0, 104.0), (0.0, 104.0), (14.0, 104.0)]   # transom line exits (y, z): traveler loop x 2, mainsheet tail
COVER = (121.0, 164.0, 22.0, 96.0)                       # x0, x1, half-width, top


def _bool(a, b, kind):
    adsk.fusion.TemporaryBRepManager.get().booleanOperation(a, b, kind)
    return a


def obox(c, u, lu, lw, lh):
    """Box centred at c (mm) with its length along the unit vector u in the xz plane, width along y."""
    u3 = adsk.core.Vector3D.create(u[0], 0, u[1])
    return adsk.fusion.TemporaryBRepManager.get().createBox(adsk.core.OrientedBoundingBox3D.create(
        bm.P(*c), u3, adsk.core.Vector3D.create(0, 1, 0), lu / 10, lw / 10, lh / 10))


def transom():
    """Filled pod section (bottom corners rounded like the 12 mm hull fillet), WALL thick."""
    B = adsk.fusion.BooleanTypes
    w = bm.tbox(AFT, AFT + WALL, -HW, HW, Z0, Z1)
    for s in (1, -1):
        corner = bm.tbox(AFT - 1, AFT + WALL + 1, min(s * (HW - FIL), s * (HW + 1)), max(s * (HW - FIL), s * (HW + 1)), Z0 - 1, Z0 + FIL)
        _bool(corner, bm.tcyl((AFT - 2, s * (HW - FIL), Z0 + FIL), (AFT + WALL + 2, s * (HW - FIL), Z0 + FIL), FIL), B.DifferenceBooleanType)
        _bool(w, corner, B.DifferenceBooleanType)
    return w


def pod_beam_saddle():
    """(join, cut): a snap saddle under the pod floor. It reaches 1.7 mm below the axis of the 10 mm pod beam, so its
    opening (9.4 mm) snaps over the tube with the same ~0.5 mm interference as the 16 mm beam saddles."""
    x, z, r = POD_BEAM
    return bm.tbox(x - 7, x + 7, -12, 12, z - 1.7, F), bm.tcyl((x, -13, z), (x, 13, z), r + 0.05)


def bracket_body():
    B = adsk.fusion.BooleanTypes
    T = BRACKET
    bx, bz = BEAM
    t = bm.tbox(T['x0'], T['deck'][0], -T['deck'][1], T['deck'][1], T['z0'], T['z1'])                 # servo deck
    for part in (bm.tbox(T['deck'][0] - 1, bx + 8, -12, 12, T['z0'], T['z1']),                        # under the clamp
                 bm.tbox(bx - 8, bx + 8, -12, 12, T['z1'] - 0.5, bz - T['r_in'] - 0.3)):               # pad up to the clamp
        _bool(t, part, B.UnionBooleanType)
    ring = bm.tcyl((bx, -12, bz), (bx, 12, bz), T['r_out'])
    _bool(ring, bm.tcyl((bx, -13, bz), (bx, 13, bz), T['r_in']), B.DifferenceBooleanType)
    a = math.radians(T['open_deg'])     # open sector: above both lines through the axis at open_deg and 180 - open_deg
    halves = []
    for u, n in (((math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))), ((-math.cos(a), math.sin(a)), (math.sin(a), math.cos(a)))):
        halves.append(obox((bx + 30 * n[0], 0, bz + 30 * n[1]), u, 200, 40, 60))
    _bool(halves[0], halves[1], B.IntersectionBooleanType)
    _bool(ring, halves[0], B.DifferenceBooleanType)
    _bool(t, ring, B.UnionBooleanType)
    L = dict(servos=[('micro', T['servo_x'])], t_std=0.0, t_micro=6.0, well=0.0, wall=0.0, clear=[])
    _, join, cut, cases = sm.geometry(L, T['z1'])
    for j in join:
        _bool(t, j, B.UnionBooleanType)
    for c in cut:
        _bool(t, c, B.DifferenceBooleanType)
    return t, cases


def cover_body():
    B = adsk.fusion.BooleanTypes
    x0, x1, hw, top = COVER
    z0 = BRACKET['z1']
    c = bm.tbox(x0, x1, -hw, hw, z0, top)
    _bool(c, bm.tbox(x0 + WALL, x1 - WALL, -hw + WALL, hw - WALL, z0 - 1, top - WALL), B.DifferenceBooleanType)
    _bool(c, bm.tbox(x0 - 1, x0 + WALL + 1, 8, 21, 76, 90), B.DifferenceBooleanType)   # pushrod slot
    return c


def electronics(zt, zm):
    return {'Rudder Servo': bm.tbox(BRACKET['servo_x'] - 11.4, BRACKET['servo_x'] + 11.4, -6.1, 6.1, zt, zt + 28.5),
            'Rudder Pushrod': bm.tcyl((BRACKET['servo_x'], 15.0, zt + 34.0), (15.0, 15.0, 66.0), 1.0),
            'Mainsheet Servo': bm.tbox(MAIN_X - 20.05, MAIN_X + 20.05, -10.05, 10.05, zm, zm + 38.9),
            'Mainsheet Tail': bm.tcyl((MAIN_X - 15.0, 0, zm + 45.3), (AFT, 0, EXITS[1][1]), 0.6)}


def add_pod_beam(design):
    beams = [o.component for o in design.rootComponent.occurrences if o.component.name == 'Crossbeams'][0]
    x, z, r = POD_BEAM
    if not beams.bRepBodies.itemByName('Pod Beam'):
        bm.base_bodies(beams, [('Pod Beam', bm.tcyl((x, -300, z), (x, 300, z), r))])
        b = beams.bRepBodies.item(beams.bRepBodies.count - 1)
        b.name = 'Pod Beam'
        b.appearance = beams.bRepBodies.itemByName('Front Beam').appearance


def apply(design):
    comps = {o.component.name: o.component for o in design.rootComponent.occurrences}
    pod = comps['Center Pod']
    ops = adsk.fusion.FeatureOperations
    sm.combine(pod, 'Pod Shell', 'V14 Aft Cut', [bm.tbox(80, AFT, -60, 60, 30, 140)], ops.CutFeatureOperation)
    sm.combine(pod, 'Pod Lid', 'V14 Lid Cut', [bm.tbox(80, AFT, -60, 60, 100, 140)], ops.CutFeatureOperation)
    # v1.3 mainsheet mount at x = 295 (rails above the floor, well below it)
    sm.combine(pod, 'Pod Shell', 'V14 Clear', [bm.tbox(AFT, 330, -13.1, 13.1, F, 100), bm.tbox(AFT, 330, -12.5, 12.5, 60, Z0)],
               ops.CutFeatureOperation)
    L = dict(servos=[('std', MAIN_X)], t_std=7.2, t_micro=7.0, well=4.0, wall=WALL, clear=[])
    _, join, cut, cases = sm.geometry(L, F)
    saddle, bore = pod_beam_saddle()
    sm.combine(pod, 'Pod Shell', 'V14 Join', [bm.tbox(AFT, 330, -12.9, 12.9, Z0, F), transom(), saddle] + join, ops.JoinFeatureOperation)
    exits = [bm.tcyl((AFT - 2, y, z), (AFT + WALL + 2, y, z), 1.5) for y, z in EXITS]
    sm.combine(pod, 'Pod Shell', 'V14 Cut', cut + exits + [bore], ops.CutFeatureOperation)
    for f in pod.features.extrudeFeatures:     # lid hole for the old mainsheet lead
        p = f.profile
        p = p if hasattr(p, 'parentSketch') else p.item(0)
        if p.parentSketch.name == 'Mainsheet Fairlead':
            f.timelineObject.isSuppressed = True
    bracket, tcases = bracket_body()
    bm.base_bodies(pod, [('Rudder Servo Bracket', bracket), ('Rudder Servo Cover', cover_body())])
    add_pod_beam(design)
    sm.update_bodies(comps['RC Electronics'], electronics(tcases[0][2], cases[0][2]))
    shell = pod.bRepBodies.itemByName('Pod Shell')
    return dict(rudder_case_z=tcases[0][2], main_case_z=cases[0][2], shell_cm3=round(shell.volume, 2), shell_lumps=shell.lumps.count)


def migrate_tail(design):
    """Designs patched with the first v1.4 version (Pod Tail under the rear beam): turn the tail into the rudder
    servo bracket, add the pod-beam saddle and the pod beam. Rebuild the hulls afterwards (build_full_hull.rebuild)."""
    comps = {o.component.name: o.component for o in design.rootComponent.occurrences}
    pod = comps['Center Pod']
    ops = adsk.fusion.FeatureOperations
    bracket, _ = bracket_body()
    sm.update_bodies(pod, {'Pod Tail': bracket, 'Rudder Servo Cover': cover_body()})
    sm.rename_base_body(pod, 'Pod Tail', 'Rudder Servo Bracket')
    saddle, bore = pod_beam_saddle()
    sm.combine(pod, 'Pod Shell', 'V14 Pod Beam Saddle', [saddle], ops.JoinFeatureOperation)
    sm.combine(pod, 'Pod Shell', 'V14 Pod Beam Bore', [bore], ops.CutFeatureOperation)
    add_pod_beam(design)
    return {n: round(pod.bRepBodies.itemByName(n).volume, 2) for n in ('Pod Shell', 'Rudder Servo Bracket', 'Rudder Servo Cover')}
