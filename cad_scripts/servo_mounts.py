"""v1.3 servo mounts, sized from the manufacturers' drawings. Run inside Fusion via MCP exec: patch(design, 'full' | 'mini').

FS5115M (Feetech spec sheet, pololu.com/file/0J1270): case 40.1 x 20.1 x 38.9 mm, 44.3 mm to the spline top, ears 54 mm
long with holes 49.5 mm apart, ear underside 27.3 mm above the case bottom.
JX W4505 winches: 40.5 x 20.2 x 38 mm (retailer listing). The ear height is not published; the FS5115M value is used.
MG90S (Tower Pro drawing): body 22.5 x 12 mm (22.8 x 12.2 in the CAD), ears 32.5 mm long, 21 mm from the case bottom to
the ear line, 35.5 mm to the top of the horn.

Standard rails: inner gap 40.5 + 2 x 0.4 mm; the case hangs 1 mm above the bottom of a well sunk into the floor, so
the winch drums keep >= 4 mm under the lid. MG90S rails: gap 22.8 + 2 x 0.3 mm, case 1 mm above the floor.
Every rail has a 4 mm wire channel at its inner face so the lead can leave either end of the case.
"""
import adsk.core, adsk.fusion, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_mini as bm

STD = dict(case=(40.5, 20.2, 38.0), gap=40.5 + 0.8, ear=27.3, y=12.9, wire_z=8.0)
MICRO = dict(case=(22.8, 12.2, 28.5), gap=22.8 + 0.6, ear=21.0, y=9.0, wire_z=10.0)
WIRE_X, CLEAR = 4.0, 1.0
LAYOUT = {
    'full': dict(comp='Center Pod', body='Pod Shell', probe_x=350.0, wall=1.2, well=4.0, t_std=7.2, t_micro=7.0,
                 servos=[('micro', 240.0), ('std', 295.0), ('std', 420.0), ('std', 565.0)],
                 clear=[(212.0, 268.0, 13.0, 96.0), (392.0, 448.0, 13.0, 96.0)],
                 slot=(156.0, 168.0, -2.2, 2.2, 84.0, 100.0)),
    'mini': dict(comp='Electronics Box', body='Box', probe_x=180.0, wall=1.0, well=6.0, t_std=7.0, t_micro=6.5,
                 servos=[('micro', 121.5), ('std', 310.0)],
                 clear=[(103.9, 139.1, 9.1, 61.0), (283.9, 336.1, 13.1, 73.0)],
                 slot=(92.0, 102.0, -2.2, 2.2, 59.0, 76.0)),
}


def floor_top(body, x):
    inside = adsk.fusion.PointContainment.PointInsidePointContainment
    lo, hi = 20.0, 90.0
    while not body.pointContainment(bm.P(x, 0, lo)) == inside:
        lo += 0.5
    hi = lo + 5
    for _ in range(30):
        m = (lo + hi) / 2
        if body.pointContainment(bm.P(x, 0, m)) == inside: lo = m
        else: hi = m
    return round(lo, 2)


def geometry(L, F):
    """Temporary tool bodies (clear, join, cut) and the case bottom height per servo."""
    clear = [bm.tbox(x0, x1, -y, y, F, z1) for x0, x1, y, z1 in L['clear']]
    join, cut, cases = [], ([bm.tbox(*L['slot'])] if L.get('slot') else []), []
    for kind, xc in L['servos']:
        g = STD if kind == 'std' else MICRO
        t = L['t_std'] if kind == 'std' else L['t_micro']
        well = L['well'] if kind == 'std' else 0.0
        zc = F + CLEAR - well
        xi = g['gap'] / 2
        for s in (-1, 1):
            a, b = xc + s * xi, xc + s * (xi + t)
            join.append(bm.tbox(min(a, b), max(a, b), -g['y'], g['y'], F - 0.2, zc + g['ear']))
            a, b = xc + s * xi, xc + s * (xi + WIRE_X)
            cut.append(bm.tbox(min(a, b), max(a, b), -g['y'] - 1, g['y'] + 1, F, F + g['wire_z']))
        if well:
            hw = g['case'][1] / 2 + 0.5
            join.append(bm.tbox(xc - xi - L['wall'], xc + xi + L['wall'], -hw - L['wall'], hw + L['wall'], F - well - L['wall'], F))
            cut.append(bm.tbox(xc - xi, xc + xi, -hw, hw, F - well, F))
        cases.append((kind, xc, zc))
    return clear, join, cut, cases


def combine(comp, body_name, name, temps, op):
    bm.base_bodies(comp, [(f'{name} {i}', t) for i, t in enumerate(temps)])
    tools = adsk.core.ObjectCollection.create()
    for b in comp.bRepBodies:
        if b.name.startswith(name + ' '):
            tools.add(b)
    ci = comp.features.combineFeatures.createInput(comp.bRepBodies.itemByName(body_name), tools)
    ci.operation = op
    comp.features.combineFeatures.add(ci)


def update_bodies(comp, new):
    for i in range(comp.features.baseFeatures.count):
        bf = comp.features.baseFeatures.item(i)
        bf.startEdit()
        for j in range(bf.bodies.count):
            b = bf.bodies.item(j)
            if b.name in new:
                t = new[b.name]
                bf.updateBody(b, t(b) if callable(t) else t)
        bf.finishEdit()


def rename_base_body(comp, old, new):
    """Renames a base-feature body inside the feature edit (a rename outside it reverts on recompute)."""
    for i in range(comp.features.baseFeatures.count):
        bf = comp.features.baseFeatures.item(i)
        if any(bf.bodies.item(j).name == old for j in range(bf.bodies.count)):
            bf.startEdit()
            for j in range(bf.bodies.count):
                if bf.bodies.item(j).name == old:
                    bf.bodies.item(j).name = new
            bf.finishEdit()


def shifted(dz):
    def f(b):
        tbm = adsk.fusion.TemporaryBRepManager.get()
        t = tbm.copy(b)
        m = adsk.core.Matrix3D.create(); m.translation = adsk.core.Vector3D.create(0, 0, dz / 10.0)
        tbm.transform(t, m)
        return t
    return f


def electronics(profile, cases):
    """Servo, drum and pushrod bodies at their new heights (drums move with their winch, old case top 110 / 83.2 mm)."""
    z = {xc: zc for _, xc, zc in cases}
    box = lambda xc, zc, c: bm.tbox(xc - c[0] / 2, xc + c[0] / 2, -c[1] / 2, c[1] / 2, zc, zc + c[2])
    if profile == 'full':
        return {'Rudder Servo': box(240.0, z[240.0], MICRO['case']),
                'Rudder Pushrod': bm.tcyl((240.0, 0, z[240.0] + 34.0), (15.0, 0, 66.0), 1.0),
                'Mainsheet Servo': box(295.0, z[295.0], (40.1, 20.1, 38.9)),
                'Traveler Winch Servo': box(420.0, z[420.0], STD['case']),
                'Winch Drum': shifted(z[420.0] + 38.0 - 110.0),
                'Jib Sheet Winch Servo': box(565.0, z[565.0], STD['case']),
                'Jib Winch Drum': shifted(z[565.0] + 38.0 - 110.0)}
    return {'Rudder Servo': box(121.5, z[121.5], MICRO['case']),
            'Rudder Pushrod': bm.tcyl((121.5, 0, z[121.5] + 34.0), (bm.TIE_X, 0, bm.TIE_Z), 0.8),
            'Sail Winch Servo': box(310.0, z[310.0], STD['case']),
            'Winch Drum': shifted(z[310.0] + 38.0 - 83.2)}


def patch(design, profile):
    L = LAYOUT[profile]
    comps = {o.component.name: o.component for o in design.rootComponent.occurrences}
    comp = comps[L['comp']]
    F = floor_top(comp.bRepBodies.itemByName(L['body']), L['probe_x'])
    clear, join, cut, cases = geometry(L, F)
    ops = adsk.fusion.FeatureOperations
    combine(comp, L['body'], 'Mount Clear', clear, ops.CutFeatureOperation)
    combine(comp, L['body'], 'Mount Rail', join, ops.JoinFeatureOperation)
    combine(comp, L['body'], 'Mount Cut', cut, ops.CutFeatureOperation)
    update_bodies(comps['RC Electronics'], electronics(profile, cases))
    return dict(floor=F, cases=cases, volume_cm3=round(comp.bRepBodies.itemByName(L['body']).volume, 2))
