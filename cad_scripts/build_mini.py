"""Builds the RC Mini Cat 600 (simplified) in a new Fusion design. Run inside Fusion (via MCP exec).

Scaling from the 1 m boat: length x0.6, hull sections x0.65 (fuller, because the RC gear does not shrink).
All dimensions mm, Z-up, X forward, Y port, Z=0 reference waterline.
"""
import adsk.core, adsk.fusion, math

K_L, K_S = 0.6, 0.68
FULL_STATIONS = [(0, 26.0, -28.0, 58.0), (150, 36.0, -40.0, 60.0), (350, 40.0, -45.0, 62.0), (550, 39.5, -44.0, 64.0),
                 (750, 35.0, -37.0, 70.0), (880, 26.0, -26.0, 76.0), (960, 14.0, -12.0, 79.0), (1000, 4.0, 5.0, 81.0)]   # v1.3 fuller bows
STATIONS = [(x * K_L, max(hw * K_S, 2.4), zb * K_S, zt * K_S) for x, hw, zb, zt in FULL_STATIONS]
HULL_Y = 170.0
BEAMS = (372.0, 108.0)
BEAM_Z, BEAM_R = 39.0, 5.0   # 10 x 8 mm carbon beams (analysis/structure.py); tube top at the box bottom (44 mm)
SADDLE_DROP = 1.2           # box saddles reach this far below the beam axis: ~0.3 mm snap interference
BOX = dict(c0=126.0, c1=354.0, r=30.0, z0=44.0, z1=94.0, wall=1.0, lid=1.0)
BOARD = dict(chord=36.0, le=354.0, z0=-150.0, z1=50.0)
RUDDER = dict(chord=27.0, le=-5.0, z0=-120.0, z1=10.0)
TIE_X, TIE_Z = 9.0, 46.0   # tie bar 5 mm above the stern deck (39.4 mm); tiller arms horizontal at the same height


def P(x, y, z):
    return adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0)


def VI(mm):
    return adsk.core.ValueInput.createByReal(mm / 10.0)


def naca(code, n=36):
    t = int(code[2:]) / 100.0
    up, lo = [], []
    for i in range(n + 1):
        x = 0.5 * (1 - math.cos(math.pi * i / n))
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4)
        up.append((x, yt)); lo.append((x, -yt))
    return list(reversed(up)) + lo[1:]


def plane_at(comp, base, value_mm):
    n = base.geometry.normal
    pi = comp.constructionPlanes.createInput()
    pi.setByOffset(base, VI(value_mm / (n.x + n.y + n.z)))
    pl = comp.constructionPlanes.add(pi)
    pl.isLightBulbOn = False
    return pl


def new_comp(root, name):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


def sym(comp, profs, total, op, bodies=None):
    col = adsk.core.ObjectCollection.create()
    for p in profs:
        col.add(p)
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(col, op)
    ei.setSymmetricExtent(VI(total), True)
    if bodies is not None:
        ei.participantBodies = bodies
    return ex.add(ei)


def circles(comp, base, off, name, centers, r, mapper):
    sk = comp.sketches.add(plane_at(comp, base, off))
    sk.name = name
    for c in centers:
        sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(mapper(c)), r / 10.0)
    sk.isVisible = False
    return [sk.profiles.item(i) for i in range(sk.profiles.count)]


def tbox(x0, x1, y0, y1, z0, z1):
    tbm = adsk.fusion.TemporaryBRepManager.get()
    return tbm.createBox(adsk.core.OrientedBoundingBox3D.create(P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                         adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                         abs(x1 - x0) / 10, abs(y1 - y0) / 10, abs(z1 - z0) / 10))


def tcyl(a, b, r):
    return adsk.fusion.TemporaryBRepManager.get().createCylinderOrCone(P(*a), r / 10.0, P(*b), r / 10.0)


def base_bodies(comp, items):
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    for name, t in items:
        comp.bRepBodies.add(t, bf).name = name
    bf.finishEdit()


def join_into(comp, target, name, temps):
    base_bodies(comp, [(f'{name} {i}', t) for i, t in enumerate(temps)])
    tools = adsk.core.ObjectCollection.create()
    for b in comp.bRepBodies:
        if b.name.startswith(name + ' '):
            tools.add(b)
    ci = comp.features.combineFeatures.createInput(target, tools)
    ci.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    comp.features.combineFeatures.add(ci)


def vertical_foil(comp, name, chord, le_x, yc, z0, z1):
    zm = (z0 + z1) / 2
    sk = comp.sketches.add(plane_at(comp, comp.xYConstructionPlane, zm))
    sk.name = name + ' Section'
    col = adsk.core.ObjectCollection.create()
    for s, t in naca('0012'):
        col.add(sk.modelToSketchSpace(P(le_x - chord * s, yc + chord * t, zm)))
    sp = sk.sketchCurves.sketchFittedSplines.add(col)
    sk.sketchCurves.sketchLines.addByTwoPoints(sp.endSketchPoint, sp.startSketchPoint)
    sk.isVisible = False
    b = sym(comp, [sk.profiles.item(0)], abs(z1 - z0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
    b.name = name
    return b


def planar_face_at_z(body, zmm):
    for f in body.faces:
        if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType and abs(f.pointOnFace.z * 10 - zmm) < 0.01:
            return f


def stadium(sk, x0, x1, r, z):
    S = lambda x, y: sk.modelToSketchSpace(P(x, y, z))
    sk.sketchCurves.sketchLines.addByTwoPoints(S(x0, r), S(x1, r))
    sk.sketchCurves.sketchLines.addByTwoPoints(S(x0, -r), S(x1, -r))
    sk.sketchCurves.sketchArcs.addByThreePoints(S(x1, -r), S(x1 + r, 0), S(x1, r))
    sk.sketchCurves.sketchArcs.addByThreePoints(S(x0, r), S(x0 - r, 0), S(x0, -r))


# ----------------------------------------------------------------------------- parts
def build_hull(root, name, yc):
    JOIN, CUT, NEW = (adsk.fusion.FeatureOperations.JoinFeatureOperation, adsk.fusion.FeatureOperations.CutFeatureOperation,
                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    tbm = adsk.fusion.TemporaryBRepManager.get()
    comp = new_comp(root, name)
    profs = []
    for x, hw, zb, zt in STATIONS:
        pl = plane_at(comp, comp.yZConstructionPlane, x)
        sk = comp.sketches.add(pl)
        sk.name = f'Station {x:g}'
        zc, b = (zb + zt) / 2, (zt - zb) / 2
        sk.sketchCurves.sketchEllipses.add(sk.modelToSketchSpace(P(x, yc, zc)), sk.modelToSketchSpace(P(x, yc, zc + b)),
                                           sk.modelToSketchSpace(P(x, yc + hw, zc)))
        sk.isVisible = False
        profs.append(sk.profiles.item(0))
    li = comp.features.loftFeatures.createInput(NEW)
    for p in profs:
        li.loftSections.add(p)
    li.isSolid = True
    hull = comp.features.loftFeatures.add(li).bodies.item(0)
    hull.name = name
    s = 1 if yc > 0 else -1
    # beam socket bosses, chainplate boss, sockets, foil trunk
    y0, y1 = yc - s * 26, s * 180
    ym = (y0 + y1) / 2
    sym(comp, circles(comp, comp.xZConstructionPlane, ym, 'Socket Bosses', [(bx, BEAM_Z) for bx in BEAMS], BEAM_R + 3.5,
                      lambda c: P(c[0], ym, c[1])), abs(y1 - y0), JOIN, [hull])
    sym(comp, circles(comp, comp.xYConstructionPlane, 42, 'Chainplate Boss', [(360, yc)], 3.5, lambda c: P(c[0], c[1], 42)), 8, JOIN, [hull])
    i0, i1 = yc - s * 30, s * 180
    im = (i0 + i1) / 2
    sym(comp, circles(comp, comp.xZConstructionPlane, im, 'Beam Sockets', [(bx, BEAM_Z) for bx in BEAMS], BEAM_R + 0.2,
                      lambda c: P(c[0], im, c[1])), abs(i1 - i0), CUT, [hull])
    sk = comp.sketches.add(plane_at(comp, comp.xYConstructionPlane, 5))
    sk.name = 'Board Trunk'
    sk.sketchCurves.sketchLines.addTwoPointRectangle(sk.modelToSketchSpace(P(316, yc - 3.2, 5)), sk.modelToSketchSpace(P(356, yc + 3.2, 5)))
    sk.isVisible = False
    sym(comp, [sk.profiles.item(0)], 150, CUT, [hull])
    # bulkhead slabs at the print joints, then shell to 0.8 mm and bond the bulkheads in
    slabs = []
    for xj in (200, 400):
        t = tbm.copy(hull)
        tbm.booleanOperation(t, tbox(xj - 1, xj + 1, -300, 300, -300, 300), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        slabs.append(t)
    col = adsk.core.ObjectCollection.create(); col.add(hull)
    si = comp.features.shellFeatures.createInput(col, False)
    si.insideThickness = VI(0.8)
    comp.features.shellFeatures.add(si)
    join_into(comp, comp.bRepBodies.itemByName(name), 'Bulkhead', slabs)
    return comp


def build_box(root):
    NEW, JOIN, CUT = (adsk.fusion.FeatureOperations.NewBodyFeatureOperation, adsk.fusion.FeatureOperations.JoinFeatureOperation,
                      adsk.fusion.FeatureOperations.CutFeatureOperation)
    comp = new_comp(root, 'Electronics Box')
    zm = (BOX['z0'] + BOX['z1']) / 2
    sk = comp.sketches.add(plane_at(comp, comp.xYConstructionPlane, zm)); sk.name = 'Box Outline'
    stadium(sk, BOX['c0'], BOX['c1'], BOX['r'], zm); sk.isVisible = False
    body = sym(comp, [sk.profiles.item(0)], BOX['z1'] - BOX['z0'], NEW).bodies.item(0)
    body.name = 'Box'
    edges = adsk.core.ObjectCollection.create()
    for e in planar_face_at_z(body, BOX['z0']).edges:
        edges.add(e)
    fi = comp.features.filletFeatures.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, VI(8), True)
    comp.features.filletFeatures.add(fi)
    faces = adsk.core.ObjectCollection.create(); faces.add(planar_face_at_z(body, BOX['z1']))
    si = comp.features.shellFeatures.createInput(faces, False)
    si.insideThickness = VI(BOX['wall'])
    comp.features.shellFeatures.add(si)
    floor = BOX['z0'] + BOX['wall']
    # beam saddles (snap fit), mast step boss, servo rails, battery cradle
    temps = [tbox(bx - 8, bx + 8, -12, 12, BEAM_Z - SADDLE_DROP, BOX['z0'] + 1) for bx in BEAMS]
    temps.append(tcyl((372, 0, BOX['z0']), (372, 0, floor + 8), 6))
    import servo_mounts as sm   # rails, winch well and wire channels sized from the manufacturers' drawings
    _, rails, rail_cuts, _ = sm.geometry(dict(sm.LAYOUT['mini'], clear=[]), floor)
    temps += rails
    temps += [tbox(197, 200, -24, 24, floor - 0.2, floor + 8), tbox(244, 247, -24, 24, floor - 0.2, floor + 8)]  # battery cradle
    join_into(comp, comp.bRepBodies.itemByName('Box'), 'BoxHW', temps)
    sm.combine(comp, 'Box', 'BoxCut', rail_cuts, CUT)
    box = comp.bRepBodies.itemByName('Box')
    sym(comp, circles(comp, comp.xZConstructionPlane, 0, 'Beam Saddle Bores', [(bx, BEAM_Z) for bx in BEAMS], BEAM_R + 0.05,
                      lambda c: P(c[0], 0, c[1])), 40, CUT, [box])
    sym(comp, circles(comp, comp.xYConstructionPlane, floor + 5, 'Mast Socket', [(372, 0)], 3.15, lambda c: P(c[0], c[1], floor + 5)), 8, CUT, [box])
    sym(comp, circles(comp, comp.yZConstructionPlane, 97, 'Pushrod Exit', [(0, 61)], 2.0, lambda c: P(97, c[0], c[1])), 10, CUT, [box])
    # lid with mast hole and two sheet fairleads
    zl = BOX['z1'] + BOX['lid'] / 2
    sk = comp.sketches.add(plane_at(comp, comp.xYConstructionPlane, zl)); sk.name = 'Lid Outline'
    stadium(sk, BOX['c0'], BOX['c1'], BOX['r'], zl)
    for x, r in ((372, 3.3), (165, 1.2), (355, 1.2)):
        sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(P(x, 0, zl)), r / 10.0)
    sk.isVisible = False
    best = max((sk.profiles.item(i) for i in range(sk.profiles.count)), key=lambda p: p.areaProperties().area)
    lid = sym(comp, [best], BOX['lid'], NEW).bodies.item(0)
    lid.name = 'Box Lid'
    return comp


def build_appendages(root):
    rud = new_comp(root, 'Rudders')
    for side, y in (('Port', HULL_Y), ('Stbd', -HULL_Y)):
        vertical_foil(rud, f'Rudder Blade {side}', RUDDER['chord'], RUDDER['le'], y, RUDDER['z0'], RUDDER['z1'])
    xs = RUDDER['le'] - 0.25 * RUDDER['chord']
    items = []
    for side, y in (('Port', HULL_Y), ('Stbd', -HULL_Y)):
        items += [(f'Rudder Stock {side}', tcyl((xs, y, 8), (xs, y, TIE_Z + 2), 1.5)),
                  (f'Gudgeon {side}', tbox(xs - 5, 1, y - 5, y + 5, 18, 28)),
                  (f'Tiller Arm {side}', tcyl((xs, y, TIE_Z), (TIE_X, y, TIE_Z), 1.2))]
    items.append(('Tie Bar', tcyl((TIE_X, -HULL_Y - 2, TIE_Z), (TIE_X, HULL_Y + 2, TIE_Z), 1.2)))
    base_bodies(rud, items)
    dk = new_comp(root, 'Daggerboards')
    for side, y in (('Port', HULL_Y), ('Stbd', -HULL_Y)):
        vertical_foil(dk, f'Daggerboard {side}', BOARD['chord'], BOARD['le'], y, BOARD['z0'], BOARD['z1'])


def build_beams_and_rc(root):
    beams = new_comp(root, 'Crossbeams')
    base_bodies(beams, [('Front Beam', tcyl((BEAMS[0], -180, BEAM_Z), (BEAMS[0], 180, BEAM_Z), BEAM_R)),
                        ('Rear Beam', tcyl((BEAMS[1], -180, BEAM_Z), (BEAMS[1], 180, BEAM_Z), BEAM_R))])
    rc = new_comp(root, 'RC Electronics')
    floor = BOX['z0'] + BOX['wall']
    base_bodies(rc, [
        ('Sail Winch Servo', tbox(289.75, 330.25, -10.1, 10.1, floor - 5, floor + 33)),   # hangs in the 6 mm well
        ('Winch Drum', tcyl((310, 0, floor + 33), (310, 0, floor + 43.4), 17)),
        ('Rudder Servo', tbox(110.1, 132.9, -6.1, 6.1, floor + 1, floor + 29.5)),
        ('Receiver', tbox(150, 185, -10, 10, floor, floor + 10)),
        ('Battery 4xAAA NiMH', tbox(200, 244, -21, 21, floor, floor + 11)),
        ('Rudder Pushrod', tcyl((121.5, 0, floor + 35), (TIE_X, 0, TIE_Z), 0.8)),
    ])


LOOK = {'Hull': 'Paint - Enamel Glossy (White)', 'Box': 'Paint - Enamel Glossy (White)', 'Box Lid': 'Paint - Metallic (Blue)',
        'Front Beam': 'Carbon Fiber - Plain', 'Rear Beam': 'Carbon Fiber - Plain', 'Rudder Blade': 'Carbon Fiber - Plain',
        'Daggerboard': 'Carbon Fiber - Plain', 'Rudder Stock': 'Aluminum - Satin', 'Gudgeon': 'Aluminum - Anodized Glossy (Red)',
        'Tiller Arm': 'Aluminum - Satin', 'Tie Bar': 'Aluminum - Satin', 'Sail Winch Servo': 'Plastic - Glossy (Black)',
        'Winch Drum': 'Aluminum - Anodized Glossy (Red)', 'Rudder Servo': 'Plastic - Glossy (Black)', 'Receiver': 'Plastic - Matte (Red)',
        'Battery': 'Plastic - Glossy (Yellow)', 'Rudder Pushrod': 'Aluminum - Satin'}


def apply_looks(design):
    lib = adsk.core.Application.get().materialLibraries.itemByName('Fusion Appearance Library')
    cache = {}
    for occ in design.rootComponent.occurrences:
        for b in occ.component.bRepBodies:
            key = next((k for k in LOOK if b.name.startswith(k)), None)
            if key is None or b.appearance.name in ('Plastic - Translucent Matte (White)',):
                continue
            n = LOOK[key]
            if n not in cache:
                cache[n] = design.appearances.itemByName(n) or design.appearances.addByCopy(lib.appearances.itemByName(n), n)
            b.appearance = cache[n]


def build(design):
    root = design.rootComponent
    build_hull(root, 'Hull Port', HULL_Y)
    build_hull(root, 'Hull Stbd', -HULL_Y)
    build_beams_and_rc(root)
    build_box(root)
    build_appendages(root)
    apply_looks(design)


def rebuild_hulls_and_segments(design):
    """v1.3: rebuild both mini hulls and all print segments."""
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name in ('Hull Port', 'Hull Stbd', 'Print Segments'):
            o.deleteMe()
    build_hull(root, 'Hull Port', HULL_Y)
    build_hull(root, 'Hull Stbd', -HULL_Y)
    apply_looks(design)
    return segments(design)


def segments(design):
    """(Re)creates the hidden 'Print Segments' component: hulls in 3 pieces, box and lid in halves."""
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name == 'Print Segments':
            o.deleteMe()
    tbm = adsk.fusion.TemporaryBRepManager.get()
    comps = {o.component.name: o.component for o in root.occurrences}
    jobs = []
    for hn in ('Hull Port', 'Hull Stbd'):
        src = comps[hn].bRepBodies.itemByName(hn)
        for i, (a, b) in enumerate(((-5, 200), (200, 400), (400, 605))):
            jobs.append((f'{hn} Seg {i + 1}', src, a, b))
    for bn in ('Box', 'Box Lid'):
        src = comps['Electronics Box'].bRepBodies.itemByName(bn)
        for i, (a, b) in enumerate(((80, 240), (240, 400))):
            jobs.append((f'{bn} Half {i + 1}', src, a, b))
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    ps = occ.component; ps.name = 'Print Segments'
    bf = ps.features.baseFeatures.add(); bf.startEdit()
    for name, src, a, b in jobs:
        t = tbm.copy(src)
        tbm.booleanOperation(t, tbox(a, b, -300, 300, -300, 300), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        ps.bRepBodies.add(t, bf).name = name
    bf.finishEdit()
    occ.isLightBulbOn = False
    return ps


def beams_10mm(design):
    """v1.4: 10 x 8 mm crossbeams in an existing mini design (box saddles and beam bodies). Rebuild the hulls afterwards
    with rebuild_hulls_and_segments so their sockets follow BEAM_Z / BEAM_R."""
    import servo_mounts as sm
    comps = {o.component.name: o.component for o in design.rootComponent.occurrences}
    ops = adsk.fusion.FeatureOperations
    box = comps['Electronics Box']
    sm.combine(box, 'Box', 'Beam Saddle', [tbox(bx - 8, bx + 8, -12, 12, BEAM_Z - SADDLE_DROP, BOX['z0'] + 1) for bx in BEAMS],
               ops.JoinFeatureOperation)
    sm.combine(box, 'Box', 'Beam Bore', [tcyl((bx, -13, BEAM_Z), (bx, 13, BEAM_Z), BEAM_R + 0.05) for bx in BEAMS], ops.CutFeatureOperation)
    sm.update_bodies(comps['Crossbeams'], {'Front Beam': tcyl((BEAMS[0], -180, BEAM_Z), (BEAMS[0], 180, BEAM_Z), BEAM_R),
                                           'Rear Beam': tcyl((BEAMS[1], -180, BEAM_Z), (BEAMS[1], 180, BEAM_Z), BEAM_R)})
    return round(box.bRepBodies.itemByName('Box').volume, 2)
