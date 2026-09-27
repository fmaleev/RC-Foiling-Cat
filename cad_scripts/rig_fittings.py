"""Printed rig fittings of the 1 m boat, replacing the placeholder blocks. Run inside Fusion via MCP exec on
'RC Foiling Catamaran v1': apply(design), then export_print(design).

Rudders: transom gudgeons (a plate bonded to the flat transom, two lugs round the 0.156 in music-wire stock, a web).
Rig Standing: traveler track in three pieces on the rear beam (T-rail, end stops with a 0.093 in wire turning pin and
two line slots each), jib track on the pod lid, bridle post, mast cap (seals the tube), hounds collar (the stays tie to
a loop of line in its groove, so the mast turns inside the loop). The cars are built by the Sail Trim add-in
(fittings_geom), which moves them with the trim.
'Mast Fittings (print)' (hidden, drawn with the wing at zero rotation): the wing-mast fairing as 0.45 mm shells in 7
pieces (5 below the hounds, 2 above), the gooseneck at the foot of the wing and the boom jaw. The main's luff is laced
to the fairing's trailing edge. Their mass is carried by the Wing Mast (export_full_mass.py).
"""
import adsk.core, adsk.fusion, importlib, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
ADDIN = os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim')
for p in (HERE, ADDIN):
    if p not in sys.path:
        sys.path.insert(0, p)
import fittings_geom as fg
import rig_model as rm
import fusion_rig
from fittings_geom import box, cyl, union, minus

HULL_Y, STOCK_X, STOCK_R = 280.0, -19.3, 0.156 * 25.4 / 2   # rudder stock axis and 0.156 in wire radius
MAST_X, TUBE_R = 620.0, 6.0
HOUNDS, WALL, GOOSE_Z, PIN_AFT, BOOM_TUBE_X0 = fg.HOUNDS_GAP, fg.FAIR_WALL, fg.GOOSE_Z, fg.BOOM_PIN_AFT, fg.BOOM_TUBE_X0
FAIR_Z = [GOOSE_Z[1] + k * (HOUNDS[0] - GOOSE_Z[1]) / 5 for k in range(6)] + [HOUNDS[1], (HOUNDS[1] + 1370.0) / 2, 1370.0]
BOOM_Z = 132.0                                               # boom axis (rig_model boom_z)


def T():
    return adsk.fusion.TemporaryBRepManager.get()


def comp_of(root, name):
    return [o.component for o in root.occurrences if o.component.name == name][0]


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


def keep_lump(body, key):
    if body.lumps.count < 2:
        return body
    return T().copy(max(body.lumps, key=key))


def replace(comp, names):
    """Removes the named bodies; returns their appearances."""
    look = {}
    for n in names:
        b = comp.bRepBodies.itemByName(n)
        if b:
            look[n] = b.appearance
            comp.features.removeFeatures.add(b)
    return look


def gudgeon(ys, hull):
    parts = [box(-2.5, 0.0, ys - 8, ys + 8, 26, 54), box(-14.3, -2.5, ys - 1.2, ys + 1.2, 34, 48)]
    for za, zb in ((28, 34), (48, 54)):
        parts += [box(STOCK_X, -2.5, ys - 5, ys + 5, za, zb), cyl((STOCK_X, ys, za), (STOCK_X, ys, zb), 5.0)]
    g = minus(union(parts), [cyl((STOCK_X, ys, 20), (STOCK_X, ys, 60), 2.1), T().copy(hull)])
    return keep_lump(g, lambda l: -l.boundingBox.minPoint.x)


def traveler_segment(s, y0, y1, beam, end):
    """Track piece from |y| = y0 to y1 on side s (+1 port, -1 starboard); end = True adds the end stop."""
    x, w = fg.BEAM_X, fg.TT_HALF_W
    Y = lambda a, b: (min(s * a, s * b), max(s * a, s * b))
    parts = [box(x - w, x + w, *Y(y0, y1), 64.0, fg.TT_TOP), fg.traveler_rail(*Y(y0, min(y1, fg.TT_STOP) if end else y1))]
    if end:
        parts.append(box(x - w, x + 8.0, *Y(fg.TT_STOP, fg.TT_END), 64.0, fg.TC_POST_TOP + 1.0))
    seg = keep_lump(minus(union(parts), [T().copy(beam)]), lambda l: l.boundingBox.maxPoint.z)
    if end:
        px, py, pd = fg.PIN
        seg = minus(seg, [box(x - w + 2.0, x + 8.5, *Y(fg.TT_STOP - 0.5, fg.TT_END - 2.0), z - 1.0, z + 1.0) for z in (fg.Z_TRAV, fg.Z_MAIN)]
                    + [cyl((px, s * py, 60.0), (px, s * py, 95.0), pd / 2)])
    return seg


def jib_track():
    (bw, bh) = fg.JT_BASE
    x, z0, e, s = fg.JT_X, fg.JT_Z0, fg.JT_END, fg.JT_STOP
    t = union([box(x - bw, x + bw, -e, e, z0, z0 + bh), fg.jib_rail(-s, s),
               box(x - 4.0, x + 4.0, s, e, z0, 126.5), box(x - 4.0, x + 4.0, -e, -s, z0, 126.5)])   # end stops clear of the sheet
    return minus(t, [cyl((x, 0, z0 - 1), (x, 0, 127.0), 1.0)])            # sheet lead into the pod


def section(inner):
    """Wing-mast section at zero rotation (rig_model), or its inward offset by WALL: closed polyline, TE first."""
    pts = rm.mast_section(dict(main_deg=-15.0, jib_deg=12.0, tension=70.0))   # mast_rot = main + 15 = 0
    if not inner:
        return pts
    n = len(pts)
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    le = max(range(n), key=lambda i: pts[i][0])
    out = []
    for i in range(1, n - 1):
        tx, ty = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(tx, ty)
        nx, ny = (ty / L, -tx / L) if area2 > 0 else (-ty / L, tx / L)      # outward normal
        q = (pts[i][0] - WALL * nx, pts[i][1] - WALL * ny)
        if i == le or (q[1] * pts[i][1] > 0 and abs(q[1]) > 0.02):
            out.append(q)
    return out


def prism(comp, loops, z0, h):
    """Extrudes the sketch profile bounded by the given closed polylines (outer first) from z0 by h; returns a copy."""
    pi = comp.constructionPlanes.createInput()
    pi.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(z0 / 10))
    pl = comp.constructionPlanes.add(pi)
    sk = comp.sketches.add(pl)
    for pts in loops:
        col = adsk.core.ObjectCollection.create()
        for x, y in pts:
            col.add(sk.modelToSketchSpace(adsk.core.Point3D.create(x / 10, y / 10, z0 / 10)))
        sp = sk.sketchCurves.sketchFittedSplines.add(col)
        sk.sketchCurves.sketchLines.addByTwoPoints(sp.endSketchPoint, sp.startSketchPoint)
    prof = [p for p in sk.profiles if p.profileLoops.count == len(loops)]
    prof = max(prof, key=lambda p: p.areaProperties().area)
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(h / 10))
    f = ex.add(ei)
    body = T().copy(f.bodies.item(0))
    f.deleteMe(); sk.deleteMe(); pl.deleteMe()
    return body


def mast_print(root, look):
    old = [o for o in root.occurrences if o.component.name == 'Mast Fittings (print)']
    for o in old:
        o.deleteMe()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = 'Mast Fittings (print)'
    outer, inner = section(False), section(True)
    shell = lambda z0, z1: prism(comp, [outer, inner], z0, z1 - z0)
    res = {}
    for k in range(5):
        res[f'Mast Fairing Lower {k + 1}'] = shell(FAIR_Z[k], FAIR_Z[k + 1])
    for k in range(2):
        res[f'Mast Fairing Upper {k + 1}'] = shell(FAIR_Z[6 + k], FAIR_Z[7 + k])
    te = min(p[0] for p in outer)
    pin = (te - PIN_AFT, 0.0)
    zg0, zg1 = GOOSE_Z
    g = prism(comp, [outer], zg0, zg1 - zg0)
    g = union([g, box(pin[0], te + 1.5, -2.0, 2.0, BOOM_Z - 4, BOOM_Z + 4), cyl((pin[0], 0, BOOM_Z - 4), (pin[0], 0, BOOM_Z + 4), 3.5)])
    res['Gooseneck'] = minus(g, [cyl((MAST_X, 0, zg0 - 1), (MAST_X, 0, zg1 + 1), TUBE_R + 0.05), cyl((pin[0], 0, zg0 - 1), (pin[0], 0, zg1 + 1), 1.25)])
    lo, hi = (BOOM_Z - 6.8, BOOM_Z - 4.3), (BOOM_Z + 4.3, BOOM_Z + 6.8)          # cheeks 0.3 mm clear of the 8 mm tab
    jaw = [box(BOOM_TUBE_X0, pin[0] - 4.0, -4.0, 4.0, lo[0], hi[1])]
    for za, zb in (lo, hi):
        jaw += [box(pin[0] - 4.0, pin[0], -3.0, 3.0, za, zb), cyl((pin[0], 0, za), (pin[0], 0, zb), 3.0)]
    jaw.append(cyl((BOOM_TUBE_X0 - 12.0, 0, BOOM_Z), (BOOM_TUBE_X0, 0, BOOM_Z), 3.45))     # plug into the 8 x 7 mm boom
    res['Boom Jaw'] = minus(union(jaw), [cyl((pin[0], 0, lo[0] - 1), (pin[0], 0, hi[1] + 1), 1.25),
                                          cyl((BOOM_TUBE_X0 + 4.0, -5, hi[0] + 0.2), (BOOM_TUBE_X0 + 4.0, 5, hi[0] + 0.2), 0.6)])
    out = {}
    for name, t in res.items():
        b = add_body(comp, name, t, look)
        out[name] = (round(b.volume * 1000, 1), b.lumps.count)
    occ.isLightBulbOn = False
    return out


def apply(design):
    root = design.rootComponent
    for m in (fg, rm, fusion_rig):
        importlib.reload(m)
    for suffix in ('fittings_geom', 'rig_model', 'fusion_rig'):     # the running add-in's own copies (package imports)
        for name, mod in list(sys.modules.items()):
            if name.endswith('.' + suffix) and os.path.dirname(getattr(mod, '__file__', '') or '') == ADDIN:
                importlib.reload(mod)
    rm.set_profile('full')
    rud, st = comp_of(root, 'Rudders'), comp_of(root, 'Rig Standing')
    beam = comp_of(root, 'Crossbeams').bRepBodies.itemByName('Rear Beam')
    out = {}
    look = replace(rud, ['Gudgeon Port', 'Gudgeon Stbd', 'Rudder Stock Port', 'Rudder Stock Stbd'])
    for side, s in (('Port', 1), ('Stbd', -1)):
        hull = comp_of(root, f'Hull {side}').bRepBodies.item(0)
        add_body(rud, f'Gudgeon {side}', gudgeon(s * HULL_Y, hull), look.get(f'Gudgeon {side}'))
        add_body(rud, f'Rudder Stock {side}', cyl((STOCK_X, s * HULL_Y, 20), (STOCK_X, s * HULL_Y, 68), STOCK_R), look.get(f'Rudder Stock {side}'))
    lk = replace(st, ['Traveler Track', 'Jib Track', 'Bridle Post', 'Mast Cap', 'Hounds Collar', 'Traveler Track Centre',
                      'Traveler Track Port', 'Traveler Track Stbd', 'Turning Pin Port', 'Turning Pin Stbd'])
    fit = lk.get('Traveler Track') or lk.get('Traveler Track Centre')
    parts = {'Traveler Track Centre': traveler_segment(1, -fg.TT_SPLIT, fg.TT_SPLIT, beam, False)}
    parts['Traveler Track Port'] = traveler_segment(1, fg.TT_SPLIT, fg.TT_END, beam, True)
    parts['Traveler Track Stbd'] = traveler_segment(-1, fg.TT_SPLIT, fg.TT_END, beam, True)
    px, py, pd = fg.PIN
    for side, s in (('Port', 1), ('Stbd', -1)):
        parts[f'Turning Pin {side}'] = cyl((px, s * py, 70.0), (px, s * py, fg.TC_POST_TOP + 1.0), 0.093 * 25.4 / 2)
    parts['Jib Track'] = jib_track()
    tx, tz = rm.RIG['tack']
    parts['Bridle Post'] = minus(cyl((tx, 0, 133.0), (tx, 0, 156.0), 3.5),
                                 [cyl((tx, -5, z), (tx, 5, z), 0.8) for z in (138.0, 151.0)])
    top = rm.RIG['mast_top']
    parts['Mast Cap'] = union([cyl((MAST_X, 0, top - 12), (MAST_X, 0, top), 4.9), cyl((MAST_X, 0, top), (MAST_X, 0, top + 2.5), 7.0)])
    z0, z1 = HOUNDS
    parts['Hounds Collar'] = minus(union([cyl((MAST_X, 0, z0), (MAST_X, 0, z0 + 2), 8.0), cyl((MAST_X, 0, z0 + 2), (MAST_X, 0, z1 - 2), 7.0),
                                          cyl((MAST_X, 0, z1 - 2), (MAST_X, 0, z1), 8.0)]), [cyl((MAST_X, 0, z0 - 1), (MAST_X, 0, z1 + 1), TUBE_R + 0.05)])
    for name, t in parts.items():
        b = add_body(st, name, t, fit)
        out[name] = (round(b.volume * 1000, 1), b.lumps.count)
    fusion_rig.update(design, fusion_rig.read_controls(design))           # rebuilds the moving cars from fittings_geom
    out.update(mast_print(root, fit))
    return out


def overlaps(design, names):
    """Volume (mm3) of every overlap between the named bodies and all other assembly bodies."""
    root = design.rootComponent
    skip = ('Print Segments', 'Foil Cores (print)', 'Mast Fittings (print)')
    allb = [(o.component.name, b) for o in root.occurrences if o.component.name not in skip for b in o.component.bRepBodies if b.isSolid]
    hits = []
    for cn, a in allb:
        if a.name not in names:
            continue
        for cn2, b in allb:
            if b is a or not a.boundingBox.intersects(b.boundingBox):
                continue
            t = T().copy(a)
            T().booleanOperation(t, T().copy(b), adsk.fusion.BooleanTypes.IntersectionBooleanType)
            v = t.volume * 1000
            if v > 0.01:
                hits.append((a.name, b.name, round(v, 2)))
    return hits


PRINT = [  # (print-list key, component, body, STL, qty)
    ('Gudgeon Port', 'Rudders', 'Gudgeon Port', 'Gudgeon_x2.stl', 2),
    ('Traveler Track Centre', 'Rig Standing', 'Traveler Track Centre', 'Traveler_Track_Centre.stl', 1),
    ('Traveler Track Port', 'Rig Standing', 'Traveler Track Port', 'Traveler_Track_Port.stl', 1),
    ('Traveler Track Stbd', 'Rig Standing', 'Traveler Track Stbd', 'Traveler_Track_Stbd.stl', 1),
    ('Traveler Car', 'Mainsail', 'Traveler Car', 'Traveler_Car.stl', 1),
    ('Jib Track', 'Rig Standing', 'Jib Track', 'Jib_Track.stl', 1),
    ('Jib Car', 'Jib', 'Jib Car', 'Jib_Car.stl', 1),
    ('Bridle Post', 'Rig Standing', 'Bridle Post', 'Bridle_Post.stl', 1),
    ('Mast Cap', 'Rig Standing', 'Mast Cap', 'Mast_Cap.stl', 1),
    ('Hounds Collar', 'Rig Standing', 'Hounds Collar', 'Hounds_Collar.stl', 1),
    ('Mast Fairing Lower 1', 'Mast Fittings (print)', 'Mast Fairing Lower 1', 'Mast_Fairing_Lower_x5.stl', 5),
    ('Mast Fairing Upper 1', 'Mast Fittings (print)', 'Mast Fairing Upper 1', 'Mast_Fairing_Upper_x2.stl', 2),
    ('Gooseneck', 'Mast Fittings (print)', 'Gooseneck', 'Gooseneck.stl', 1),
    ('Boom Jaw', 'Mast Fittings (print)', 'Boom Jaw', 'Boom_Jaw.stl', 1),
    ('Wand Pivot Port', 'Ride Height Control', 'Wand Pivot Port', 'Wand_Hinge_Bracket_x2.stl', 2),
    ('Wand Hub Port', 'Ride Height Control', 'Wand Hub Port', 'Wand_Hub_x2.stl', 2),
    ('Bellcrank Mount Port', 'Ride Height Control', 'Bellcrank Mount Port', 'Bellcrank_Mount_x2.stl', 2),
    ('Strut Bellcrank Port', 'Ride Height Control', 'Strut Bellcrank Port', 'Strut_Bellcrank_x2.stl', 2),
    ('Flap Horn Port', 'Ride Height Control', 'Flap Horn Port', 'Flap_Horn_x2.stl', 2),
]
KEEP_STL = ('Wand_', 'Bellcrank', 'Strut_Bellcrank', 'Flap_Horn')   # exported with the linkage (linkage.py)


def export_print(design):
    """Writes the STLs to stl/ and merges their entries into manual_1m/print_list_1m.json."""
    root = design.rootComponent
    em = design.exportManager
    path = os.path.join(ROOT, 'manual_1m', 'print_list_1m.json')
    pl = json.load(open(path))
    for key, cname, bname, stl, qty in PRINT:
        b = comp_of(root, cname).bRepBodies.itemByName(bname)
        fn = os.path.join(ROOT, 'stl', stl)
        if not stl.startswith(KEEP_STL) or not os.path.exists(fn):
            opt = em.createSTLExportOptions(b, fn)
            opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            em.execute(opt)
        bb = b.boundingBox
        size = sorted((round((bb.maxPoint.x - bb.minPoint.x) * 10), round((bb.maxPoint.y - bb.minPoint.y) * 10),
                       round((bb.maxPoint.z - bb.minPoint.z) * 10)), reverse=True)
        pl[key] = dict(stl=stl, qty=qty, cm3=round(b.volume, 2), size_mm=size, exists=os.path.exists(fn))
    json.dump(pl, open(path, 'w'), indent=1)
    return {k: (pl[k]['cm3'], pl[k]['size_mm']) for k, *_ in PRINT}
