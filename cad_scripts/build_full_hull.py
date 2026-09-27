"""Rebuilds the 1 m hulls (station table v1.3: fuller bows for pitchpole margin) in the active design,
plus their print segments. Run inside Fusion via MCP exec."""
import adsk.core, adsk.fusion, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_mini as bm     # shared helpers (P, VI, plane_at, sym, circles, tbox, join_into, new_comp)

STATIONS = [(0, 26.0, -28.0, 58.0), (150, 36.0, -40.0, 60.0), (350, 40.0, -45.0, 62.0), (550, 39.5, -44.0, 64.0),
            (750, 35.0, -37.0, 70.0), (880, 26.0, -26.0, 76.0), (960, 14.0, -12.0, 79.0), (1000, 4.0, 5.0, 81.0)]
HULL_Y = 280.0
# crossbeams (x, axis z, tube radius): front and rear 16 mm, and the v1.4 pod beam (10 mm) under the aft end of the pod
BEAMS = ((620.0, 62.0, 8.0), (180.0, 62.0, 8.0), (350.0, 65.0, 5.0))


def build_hull(root, name, yc):
    JOIN, CUT, NEW = (adsk.fusion.FeatureOperations.JoinFeatureOperation, adsk.fusion.FeatureOperations.CutFeatureOperation,
                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    tbm = adsk.fusion.TemporaryBRepManager.get()
    P = bm.P
    comp = bm.new_comp(root, name)
    profs = []
    for x, hw, zb, zt in STATIONS:
        sk = comp.sketches.add(bm.plane_at(comp, comp.yZConstructionPlane, x))
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
    y0, y1 = yc - s * 44, s * 300
    ym = (y0 + y1) / 2
    for k, (bx, bz, br) in enumerate(BEAMS):
        bm.sym(comp, bm.circles(comp, comp.xZConstructionPlane, ym, f'Socket Boss {k + 1}', [(bx, bz)], br + 5,
                                lambda c: P(c[0], ym, c[1])), abs(y1 - y0), JOIN, [hull])
    bm.sym(comp, bm.circles(comp, comp.xYConstructionPlane, 66, 'Chainplate Boss', [(600, yc)], 5, lambda c: P(c[0], c[1], 66)), 12, JOIN, [hull])
    i0, i1 = yc - s * 50, s * 300
    im = (i0 + i1) / 2
    for k, (bx, bz, br) in enumerate(BEAMS):
        bm.sym(comp, bm.circles(comp, comp.xZConstructionPlane, im, f'Beam Socket {k + 1}', [(bx, bz)], br + 0.2,
                                lambda c: P(c[0], im, c[1])), abs(i1 - i0), CUT, [hull])
    sk = comp.sketches.add(bm.plane_at(comp, comp.xYConstructionPlane, 10))
    sk.name = 'Foil Trunk'
    sk.sketchCurves.sketchLines.addTwoPointRectangle(sk.modelToSketchSpace(P(528, yc - 4.6, 10)), sk.modelToSketchSpace(P(592, yc + 4.6, 10)))
    sk.isVisible = False
    bm.sym(comp, [sk.profiles.item(0)], 200, CUT, [hull])
    slabs = []
    for xj in (200, 400, 600, 800):
        t = tbm.copy(hull)
        tbm.booleanOperation(t, bm.tbox(xj - 1, xj + 1, -400, 400, -400, 400), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        slabs.append(t)
    col = adsk.core.ObjectCollection.create(); col.add(hull)
    si = comp.features.shellFeatures.createInput(col, False)
    si.insideThickness = bm.VI(0.8)
    comp.features.shellFeatures.add(si)
    bm.join_into(comp, comp.bRepBodies.itemByName(name), 'Bulkhead', slabs)
    return comp


def rebuild(design):
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name in ('Hull Port', 'Hull Stbd', 'Print Segments'):
            o.deleteMe()
    build_hull(root, 'Hull Port', HULL_Y)
    build_hull(root, 'Hull Stbd', -HULL_Y)
    bm.apply_looks(design)
    return segments(design)


def segments(design):
    """(Re)creates the hidden 'Print Segments' component: hulls 5 x 200 mm, pod and lid 4 pieces (every piece fits a
    220 mm bed; the pod cuts avoid the servo rails, wells and beam saddles)."""
    root = design.rootComponent
    for o in list(root.occurrences):
        if o.component.name == 'Print Segments':
            o.deleteMe()
    tbm = adsk.fusion.TemporaryBRepManager.get()
    comps = {o.component.name: o.component for o in root.occurrences}
    jobs = []
    cuts = [0, 200, 400, 600, 800, 1000]
    for hn in ('Hull Port', 'Hull Stbd'):
        src = comps[hn].bRepBodies.itemByName(hn)
        for i in range(5):
            jobs.append((f'{hn} Seg {i + 1} (x{cuts[i]}-{cuts[i + 1]})', src, cuts[i] - (5 if i == 0 else 0), cuts[i + 1] + (5 if i == 4 else 0)))
    pc = [260, 455, 600, 720, 850]   # v1.4 pod: transom at x = 270
    for pn in ('Pod Shell', 'Pod Lid'):
        src = comps['Center Pod'].bRepBodies.itemByName(pn)
        for i in range(len(pc) - 1):
            jobs.append((f'{pn} Seg {i + 1} (x{max(pc[i], 270)}-{min(pc[i + 1], 840)})', src, pc[i], pc[i + 1]))
    for pn in ('Rudder Servo Bracket', 'Rudder Servo Cover'):
        src = comps['Center Pod'].bRepBodies.itemByName(pn)
        if src:
            jobs.append((pn + ' (print)', src, -1000, 2000))
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    ps = occ.component; ps.name = 'Print Segments'
    bf = ps.features.baseFeatures.add(); bf.startEdit()
    for name, src, a, b in jobs:
        t = tbm.copy(src)
        tbm.booleanOperation(t, bm.tbox(a, b, -400, 400, -400, 400), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        ps.bRepBodies.add(t, bf).name = name
    bf.finishEdit()
    for i, (name, _, _, _) in enumerate(jobs):   # names set inside the base-feature edit can revert
        if ps.bRepBodies.item(i).name != name:
            ps.bRepBodies.item(i).name = name
    occ.isLightBulbOn = False
    return [(b.name, round(b.volume, 1), b.shells.count) for c in (comps['Hull Port'], comps['Hull Stbd']) for b in c.bRepBodies]
