"""Ride-height linkage, detailed for printing (replaces the placeholder blocks in 'Ride Height Control').
Run inside Fusion via MCP exec on the foiling master after the foils: apply(design, foils).

Chain, per hull (starboard mirrored): wand (2 mm carbon rod, 300 mm) in a printed hub on a 2 mm axle at the stem ->
8.25 mm horn on the hub -> deck pushrod (0.047 in wire) aft to a bellcrank beside the strut top -> bellcrank arms 8 mm
(input up, output aft, 1:1) -> strut pushrod down the strut's channel -> out of a slot in the strut's inboard face ->
flap horn with its hole 5.5 mm aft of the flap hinge.
Gearing = (horn / flap arm) x (bellcrank output / input) = (8.25 / 5.5) x (8 / 8) = 1.5 deg of flap per deg of wand.
Sense: boat lower -> wand turns toward horizontal -> horn tip moves aft -> bellcrank turns, output arm down -> strut
pushrod down -> flap trailing edge down (more lift). The wand hinge sits 7 mm ahead of the stem (x = 1008 mm) so the hub
clears it; analysis/vpp.py X_PIVOT matches.
"""
import adsk.core, adsk.fusion, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mini as bm

HULL_Y = 280.0
PIVOT = (1008.0, 74.0)                 # wand hinge (x, z)
WAND_L, WAND_DEG, WAND_R = 300.0, 49.0, 1.0
HUB_R, HORN, AXLE_R, HOLE_R = 5.0, 8.25, 1.0, 0.6
Y_ROD = 8.0                            # deck pushrod, bellcrank and horn plane: 8 mm outboard of the hull centreline
BELL_C, BELL_ARM = (574.0, 88.0), 8.0  # bellcrank pivot (x, z) and arm length
FLAP_ARM = 5.5                         # flap horn hole 5.5 mm aft of the flap hinge (x = 575 - wing chord / 2)
ROD_R = 0.6                            # 0.047 in music wire
CHANNEL_TOP, CHANNEL_BOT = (566.0, 80.0), (547.0, -214.0)


def box(x0, x1, y0, y1, z0, z1):
    return bm.tbox(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1)


def cyl_y(x, z, y0, y1, r):
    return bm.tcyl((x, y0, z), (x, y1, z), r)


def union(parts):
    tbm = adsk.fusion.TemporaryBRepManager.get()
    out = parts[0]
    for p in parts[1:]:
        tbm.booleanOperation(out, p, adsk.fusion.BooleanTypes.UnionBooleanType)
    return out


def minus(body, tools):
    tbm = adsk.fusion.TemporaryBRepManager.get()
    for t in tools:
        tbm.booleanOperation(body, t, adsk.fusion.BooleanTypes.DifferenceBooleanType)
    return body


def top_lump(body):
    """The hulls are 0.8 mm skins, so subtracting one leaves the box's inside as a second piece: keep the highest piece."""
    tbm = adsk.fusion.TemporaryBRepManager.get()
    if body.lumps.count < 2:
        return body
    return tbm.copy(max(body.lumps, key=lambda l: l.boundingBox.maxPoint.z))


def add_body(comp, name, temp, look=None):
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    comp.bRepBodies.add(temp, bf)
    bf.finishEdit()
    b = bf.bodies.item(0)
    b.name = name
    if look:
        b.appearance = look
    return b


def side_parts(s, hull, lf_top_z, flap_top_z, horn_x):
    """Temporary bodies for one side; s = +1 port, -1 starboard. y is mirrored by s. horn_x: the flap horn hole's x."""
    tbm = adsk.fusion.TemporaryBRepManager.get()
    yc, yr = s * HULL_Y, s * (HULL_Y + Y_ROD)
    Y = lambda d: s * (HULL_Y + d)                         # y at offset d outboard of the hull centreline
    px, pz = PIVOT
    wd = (math.cos(math.radians(WAND_DEG)), -math.sin(math.radians(WAND_DEG)))
    out = {}
    # wand hinge bracket: a plate bonded to the stem face with two cheeks carrying the axle
    plate = box(999.5, 1003.0, Y(-6), Y(11), 64.0, 81.0)          # up to the stem top
    cheeks = [box(1003.0, 1013.0, Y(-5), Y(-3), 67.0, 81.0), box(1003.0, 1013.0, Y(9), Y(11), 67.0, 81.0)]
    out['Wand Pivot'] = top_lump(minus(union([plate] + cheeks), [cyl_y(px, pz, Y(-7), Y(13), AXLE_R + 0.1), tbm.copy(hull)]))
    # hub between the cheeks: axle boss, wand socket along the wand, horn up in the pushrod plane
    hub = cyl_y(px, pz, Y(-2.7), Y(8.7), HUB_R)
    sock = bm.tcyl((px, yc, pz), (px + 14 * wd[0], yc, pz + 14 * wd[1]), 3.0)
    horn = box(px - 1.5, px + 1.5, Y(5.5), Y(8.7), pz, pz + HORN + 2.0)
    out['Wand Hub'] = minus(union([hub, sock, horn]), [cyl_y(px, pz, Y(-8), Y(14), AXLE_R + 0.1),
                                                     bm.tcyl((px + 4 * wd[0], yc, pz + 4 * wd[1]), (px + 15 * wd[0], yc, pz + 15 * wd[1]), WAND_R + 0.1),
                                                     cyl_y(px, pz + HORN, Y(4), Y(10), HOLE_R + 0.1)])
    out['Wand'] = bm.tcyl((px + 4 * wd[0], yc, pz + 4 * wd[1]), (px + WAND_L * wd[0], yc, pz + WAND_L * wd[1]), WAND_R)
    # bellcrank mount on the deck beside the strut top, its base conformed to the deck
    cx, cz = BELL_C
    base = box(cx - 12, cx + 12, Y(4.5), Y(15), 55.0, 67.0)             # clear of the strut (its face is 3.6 mm out)
    mc = [box(cx - 6, cx + 6, Y(4.5), Y(6.5), 60.0, cz + 4), box(cx - 6, cx + 6, Y(9.5), Y(11.5), 60.0, cz + 4)]
    mount = union([base] + mc)
    out['Bellcrank Mount'] = top_lump(minus(mount, [cyl_y(cx, cz, Y(3), Y(13), AXLE_R + 0.1), tbm.copy(hull)]))
    # bellcrank: L plate, input arm up (deck pushrod), output arm aft (strut pushrod)
    bell = union([box(cx - 1.5, cx + 1.5, Y(6.8), Y(9.2), cz - 1.5, cz + BELL_ARM + 1.5), box(cx - BELL_ARM - 1.5, cx + 1.5, Y(6.8), Y(9.2), cz - 1.5, cz + 1.5),
                  cyl_y(cx, cz, Y(6.8), Y(9.2), 3.0)])
    out['Strut Bellcrank'] = minus(bell, [cyl_y(cx, cz, Y(5), Y(11), AXLE_R + 0.1), cyl_y(cx, cz + BELL_ARM, Y(5), Y(11), HOLE_R + 0.1),
                                          cyl_y(cx - BELL_ARM, cz, Y(5), Y(11), HOLE_R + 0.1)])
    # pushrods (music wire)
    a, b = (px, pz + HORN), (cx, cz + BELL_ARM)                           # ends stop 2 mm short of the arms (Z-bends not modelled)
    L = math.hypot(b[0] - a[0], b[1] - a[1]); u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    out['Deck Pushrod'] = bm.tcyl((a[0] + 2 * u[0], yr, a[1] + 2 * u[1]), (b[0] - 2 * u[0], yr, b[1] - 2 * u[1]), ROD_R)
    (xt, zt), (xb, zb) = CHANNEL_TOP, CHANNEL_BOT
    k = (cz - zt) / (zt - zb)
    top = (xt + (xt - xb) * k, cz)
    out['Strut Pushrod'] = union([bm.tcyl((cx - BELL_ARM, yr, cz), (top[0], yc, cz), ROD_R), bm.tcyl((top[0], yc, top[1]), (xb, yc, zb), ROD_R),
                                  bm.tcyl((xb, yc, zb), (horn_x, Y(-7.5), zb), ROD_R)])       # out of the slot, doglegged to the horn
    # flap horn: a tab on the flap root's upper surface, hole 5.5 mm aft of the hinge in line with the pushrod's foot
    out['Flap Horn'] = minus(box(horn_x - 1.5, horn_x + 1.5, Y(-9.0), Y(-6.0), flap_top_z - 1.0, zb + 2.5),
                             [cyl_y(horn_x, zb, Y(-10), Y(-5), HOLE_R + 0.1)])
    # exit slot for the strut pushrod through the strut's inboard face, above the wing
    out['_slot'] = box(min(xb, horn_x) - 1.7, max(xb, horn_x) + 1.7, Y(-4.5), Y(0.5), zb - 2.0, zb + 5.0)
    return out


def apply(design, foils):
    root = design.rootComponent
    rhc = [o.component for o in root.occurrences if o.component.name == 'Ride Height Control'][0]
    kit = [o.component for o in root.occurrences if o.component.name == 'Foiling Kit'][0]
    tbm = adsk.fusion.TemporaryBRepManager.get()
    look = {b.name: b.appearance for b in rhc.bRepBodies}
    for b in list(rhc.bRepBodies):
        rhc.features.removeFeatures.add(b)
    res = {}
    for side, s in (('Port', 1), ('Stbd', -1)):
        hull = [o.component for o in root.occurrences if o.component.name == f'Hull {side}'][0].bRepBodies.item(0)
        flap = kit.bRepBodies.itemByName(f'Flap {side}')
        parts = side_parts(s, tbm.copy(hull), None, flap.boundingBox.maxPoint.z * 10, 575.0 - foils['wchord'] / 2 - FLAP_ARM)
        horn = parts['Flap Horn']
        tbm.booleanOperation(horn, tbm.copy(flap), adsk.fusion.BooleanTypes.DifferenceBooleanType)
        for name in ('Wand Pivot', 'Wand Hub', 'Wand', 'Deck Pushrod', 'Bellcrank Mount', 'Strut Bellcrank', 'Strut Pushrod', 'Flap Horn'):
            b = add_body(rhc, f'{name} {side}', parts[name], look.get(f'{name} {side}') or look.get(f'Wand Pivot {side}'))
            res[b.name] = (round(b.volume * 1000), b.lumps.count)
        lf = kit.bRepBodies.itemByName(f'L-Foil {side}')
        slot = add_body(kit, f'Pushrod Exit {side}', parts['_slot'])
        col = adsk.core.ObjectCollection.create(); col.add(slot)
        ci = kit.features.combineFeatures.createInput(lf, col)
        ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        kit.features.combineFeatures.add(ci)
    return res
