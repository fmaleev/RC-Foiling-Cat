"""Builds and re-trims the rig in the active Fusion design, driven by rig_model."""
import adsk.core, adsk.fusion

try:
    from . import rig_model as rm
    from . import fittings_geom as fg
except ImportError:
    import rig_model as rm
    import fittings_geom as fg

PARAMS = (('JibSheet', 'jib_deg', 'deg', 'Front sail (jib) sheet angle'),
          ('MainTraveler', 'main_deg', 'deg', 'Back sail (main) traveler angle'),
          ('MainSheetTension', 'tension', '', 'Back sail mainsheet tension, 0-100 % (twist / depth)'))
OLD = ('Rig', 'Sails', 'Rig Standing', 'Mast', 'Mainsail', 'Jib')
LOOKS = {'sail': 'Plastic - Translucent Matte (White)', 'carbon': 'Carbon Fiber - Plain', 'line': 'Plastic - Matte (Black)',
         'fitting': 'Aluminum - Anodized Glossy (Red)', 'sheet': 'Plastic - Matte (Red)'}


def P(x, y, z):
    return adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0)


def VI(mm):
    return adsk.core.ValueInput.createByReal(mm / 10.0)


# ------------------------------------------------------------------ profile + parameters
def profile_of(design):
    a = design.attributes.itemByName('RCCat', 'profile')
    return a.value if a else 'full'


def use_profile(design, name=None):
    if name:
        a = design.attributes.itemByName('RCCat', 'profile')
        if a:
            a.value = name
        else:
            design.attributes.add('RCCat', 'profile', name)
    rm.set_profile(name or profile_of(design))


def read_controls(design):
    c = dict(rm.DEFAULTS)
    for pname, key, unit, _ in PARAMS:
        p = design.userParameters.itemByName(pname)
        if p:
            c[key] = p.value * 180.0 / 3.141592653589793 if unit == 'deg' else p.value
    return c


def write_controls(design, c):
    for pname, key, unit, comment in PARAMS:
        lo, hi = rm.LIMITS[key]
        v = rm.clamp(c[key], lo, hi)
        expr = f'{v:.2f} deg' if unit == 'deg' else f'{v:.1f}'
        p = design.userParameters.itemByName(pname)
        if p:
            p.expression = expr
        else:
            design.userParameters.add(pname, adsk.core.ValueInput.createByString(expr), unit, comment)


# ------------------------------------------------------------------ helpers
def look(design, key):
    name = LOOKS[key]
    a = design.appearances.itemByName(name)
    if a is None:
        lib = adsk.core.Application.get().materialLibraries.itemByName('Fusion Appearance Library')
        a = design.appearances.addByCopy(lib.appearances.itemByName(name), name)
    return a


def new_comp(root, name):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


def comp_by_name(root, name):
    for occ in root.occurrences:
        if occ.component.name == name:
            return occ.component
    return None


def plane_z(comp, z):
    pi = comp.constructionPlanes.createInput()
    pi.setByOffset(comp.xYConstructionPlane, VI(z / comp.xYConstructionPlane.geometry.normal.z))
    pl = comp.constructionPlanes.add(pi)
    pl.isLightBulbOn = False
    return pl


def temp_body(item):
    tbm = adsk.fusion.TemporaryBRepManager.get()
    name, kind, d = item
    if kind == 'cyl':
        return tbm.createCylinderOrCone(P(*d[0]), d[2] / 10.0, P(*d[1]), d[2] / 10.0)
    if kind in ('tcar', 'jcar'):   # printed cars (fittings_geom), placed by their bounding box
        return (fg.traveler_car if kind == 'tcar' else fg.jib_car)((d[2] + d[3]) / 2)
    if kind == 'ribbon':  # batten pocket: thin vertical strip following the sail section (leech end trimmed)
        pts, h = d
        wires = []
        for dz in (-h / 2, h / 2):
            lines = [adsk.core.Line3D.create(P(a[0], a[1], a[2] + dz), P(b[0], b[1], b[2] + dz)) for a, b in zip(pts[:-1], pts[1:])]
            w = tbm.createWireFromCurves(lines)
            w = w[0] if isinstance(w, (tuple, list)) else w
            wires.append(w.wires.item(0))
        return tbm.createRuledSurface(wires[0], wires[1])
    x0, x1, y0, y1, z0, z1 = d
    obb = adsk.core.OrientedBoundingBox3D.create(P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), adsk.core.Vector3D.create(1, 0, 0),
                                                 adsk.core.Vector3D.create(0, 1, 0), abs(x1 - x0) / 10, abs(y1 - y0) / 10, abs(z1 - z0) / 10)
    return tbm.createBox(obb)


def section_sketch(comp, name, z, pts, closed):
    sk = comp.sketches.add(plane_z(comp, z))
    sk.name = name
    col = adsk.core.ObjectCollection.create()
    for x, y in pts:
        col.add(sk.modelToSketchSpace(P(x, y, z)))
    sp = sk.sketchCurves.sketchFittedSplines.add(col)
    if closed:
        sk.sketchCurves.sketchLines.addByTwoPoints(sp.endSketchPoint, sp.startSketchPoint)
    sk.isVisible = False
    return sk, sp


def move_section(sk, z, pts):
    sp = sk.sketchCurves.sketchFittedSplines.item(0)
    fp = sp.fitPoints
    for i in range(fp.count):
        p = fp.item(i)
        target = sk.modelToSketchSpace(P(pts[i][0], pts[i][1], z))
        v = p.geometry.vectorTo(target)
        if v.length > 1e-7:
            p.move(v)


def loft_surface(comp, sketches, name, appearance):
    lf = comp.features.loftFeatures
    li = lf.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    for sk in sketches:
        li.loftSections.add(comp.features.createPath(sk.sketchCurves.sketchFittedSplines.item(0), False))
    li.isSolid = False
    b = lf.add(li).bodies.item(0)
    b.name = name
    b.appearance = appearance
    return b


def add_base_bodies(comp, items, looks):
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    for it in items:
        comp.bRepBodies.add(temp_body(it), bf).name = it[0]
    bf.finishEdit()
    for b in comp.bRepBodies:
        if b.name in looks:
            b.appearance = looks[b.name]


def update_base_bodies(comp, items):
    new = {it[0]: temp_body(it) for it in items}
    for i in range(comp.features.baseFeatures.count):
        bf = comp.features.baseFeatures.item(i)
        bf.startEdit()
        for j in range(bf.bodies.count):
            b = bf.bodies.item(j)
            if b.name in new:
                bf.updateBody(b, new[b.name])
        bf.finishEdit()


# ------------------------------------------------------------------ build / update
def build(design, controls=None, profile=None):
    root = design.rootComponent
    for occ in list(root.occurrences):
        if occ.component.name in OLD:
            occ.deleteMe()
    use_profile(design, profile)
    c = controls or read_controls(design)
    write_controls(design, c)
    r = rm.RIG
    L = {k: look(design, k) for k in LOOKS}

    # standing rigging (static)
    st = new_comp(root, 'Rig Standing')
    tx, tz = r['tack']
    bx, by, bz = r['bow']
    cx, cy, cz = r['chainplate']
    wire = 0.75 if r['traveler'] else 0.5
    items = [
        ('Mast Tube Base' if r['wing_mast'] else 'Mast', 'cyl',
         ((r['mast_x'], 0, r['mast_z0']), (r['mast_x'], 0, r['mast_fair_z0'] if r['wing_mast'] else r['mast_top']), r['mast_r'])),
        ('Mast Cap', 'cyl', ((r['mast_x'], 0, r['mast_top']), (r['mast_x'], 0, r['mast_top'] + r['mast_r'] + 2), r['mast_r'] + 1)),
        ('Forestay', 'cyl', ((tx, 0, tz), (r['mast_x'], 0, r['hounds_z']), wire)),
        ('Shroud Port', 'cyl', ((r['mast_x'], r['mast_r'] - 1, r['hounds_z']), (cx, cy, cz), wire)),
        ('Shroud Stbd', 'cyl', ((r['mast_x'], 1 - r['mast_r'], r['hounds_z']), (cx, -cy, cz), wire)),
        ('Bridle Port', 'cyl', ((tx, 0, tz), (bx, by, bz), wire)),
        ('Bridle Stbd', 'cyl', ((tx, 0, tz), (bx, -by, bz), wire)),
    ]
    looks = {'Mast Tube Base': L['carbon'], 'Mast': L['carbon'], 'Mast Cap': L['fitting'], 'Forestay': L['line'], 'Shroud Port': L['line'],
             'Shroud Stbd': L['line'], 'Bridle Port': L['line'], 'Bridle Stbd': L['line'], 'Bridle Post': L['fitting'],
             'Traveler Track': L['fitting'], 'Jib Track': L['fitting']}
    if r['bridle_post']:
        items.append(('Bridle Post', 'cyl', ((tx, 0, 131), (tx, 0, tz), 3.0)))
    if r['traveler']:
        items += [traveler_track_item(r),
                  jib_track_item(r)]
    add_base_bodies(st, items, looks)

    if r['wing_mast']:  # rotating wing mast
        mc = new_comp(root, 'Mast')
        zm = (r['mast_fair_z0'] + r['mast_top']) / 2
        sk, _ = section_sketch(mc, 'Mast Section', zm, rm.mast_section(c), True)
        ex = mc.features.extrudeFeatures
        ei = ex.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setSymmetricExtent(VI(r['mast_top'] - r['mast_fair_z0']), True)
        b = ex.add(ei).bodies.item(0)
        b.name = 'Wing Mast'
        b.appearance = L['carbon']

    # mainsail (fully battened, square top) + boom, sheet, traveler car
    mn = new_comp(root, 'Mainsail')
    sks = [section_sketch(mn, f'Main Batten {k}', z, pts, False)[0] for k, (z, pts) in enumerate(rm.main_sections(c))]
    loft_surface(mn, sks, 'Mainsail', L['sail'])
    hw = rm.hardware(c)
    main_hw = [h for h in hw if h[0] in ('Main Boom', 'Mainsheet', 'Traveler Car') or h[0].startswith('Batten')]
    lk = {'Main Boom': L['carbon'], 'Mainsheet': L['sheet'], 'Traveler Car': L['fitting']}
    lk.update({h[0]: L['carbon'] for h in main_hw if h[0].startswith('Batten')})
    add_base_bodies(mn, main_hw, lk)

    # jib + sheet + car
    jb = new_comp(root, 'Jib')
    sks = [section_sketch(jb, f'Jib Section {k}', z, pts, False)[0] for k, (z, pts) in enumerate(rm.jib_sections(c))]
    loft_surface(jb, sks, 'Jib', L['sail'])
    add_base_bodies(jb, [h for h in hw if h[0] in ('Jib Sheet', 'Jib Car')], {'Jib Sheet': L['sheet'], 'Jib Car': L['fitting']})
    return c


def traveler_track_item(r):
    th = r.get('track_h', 0.0)
    z0 = r['beam_top'] if th else r['beam_top'] - 1
    return ('Traveler Track', 'box', (r['rear_beam_x'] - 5, r['rear_beam_x'] + 5, -r['car_limit'] - 10, r['car_limit'] + 10, z0, z0 + (th or 1)))


def jib_track_item(r):
    jt = r.get('jib_track')
    if jt:
        return ('Jib Track', 'box', (jt[0] - 4, jt[0] + 4, -jt[1] - 10, jt[1] + 10, jt[2] - 1, jt[2]))
    return ('Jib Track', 'box', (r['front_beam_x'] - 4, r['front_beam_x'] + 4, -160, 160, r['beam_top'] - 1, r['beam_top']))


def update(design, c):
    root = design.rootComponent
    use_profile(design)
    c = {k: rm.clamp(c[k], *rm.LIMITS[k]) for k in rm.LIMITS}
    write_controls(design, c)
    r = rm.RIG
    mc, mn, jb = comp_by_name(root, 'Mast'), comp_by_name(root, 'Mainsail'), comp_by_name(root, 'Jib')
    jobs = [(mc.sketches.itemByName('Mast Section'), (r['mast_fair_z0'] + r['mast_top']) / 2, rm.mast_section(c))] if r['wing_mast'] else []
    jobs += [(mn.sketches.itemByName(f'Main Batten {k}'), z, pts) for k, (z, pts) in enumerate(rm.main_sections(c))]
    jobs += [(jb.sketches.itemByName(f'Jib Section {k}'), z, pts) for k, (z, pts) in enumerate(rm.jib_sections(c))]
    for sk, _, _ in jobs:
        sk.isComputeDeferred = True
    for sk, z, pts in jobs:
        move_section(sk, z, pts)
    for sk, _, _ in jobs:
        sk.isComputeDeferred = False
    hw = rm.hardware(c)
    update_base_bodies(mn, [h for h in hw if h[0] in ('Main Boom', 'Mainsheet', 'Traveler Car') or h[0].startswith('Batten')])
    update_base_bodies(jb, [h for h in hw if h[0] in ('Jib Sheet', 'Jib Car')])
    return c
