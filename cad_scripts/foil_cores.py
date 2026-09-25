"""Printable foil cores with recesses for the unidirectional carbon caps (4 layers of 0.127 mm tape = 0.5 mm per face,
25 mm wide, centred on the thickest part of each section). Run inside Fusion via MCP exec after the foils and trim pods:
apply(design, foils, stl_dir). For the strut, the wing and the elevator of each side:
  1. cut the foil down to the cap band (a box 25 mm wide in chord, clear of the other members);
  2. subtract an 'inner' foil: the same NACA section with each surface moved 0.5 mm inward (half-thickness yt - 0.5 mm
     about the camber line), which leaves exactly the top and bottom 0.5 mm cap layers;
  3. subtract the caps from a copy of the foil: the core.
(A shell feature fails here: the strut's pushrod channel makes Fusion treat the chunk as already shelled.)
The flaps have no caps and are printed whole. Cores and caps go into a hidden component 'Foil Cores (print)' (not in the
mass export) and the cores are written as STLs."""
import adsk.core, adsk.fusion, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mini as bm
import foils_v21 as f21

CAP_T, CAP_W = 0.5, 25.0                      # mm
STRUT, HULL_Y, WING_QC_X, WING_Z, ELEV_QC_X = f21.STRUT, f21.HULL_Y, 575.0, -220.0, -15.0


def inner_section(code, chord, off, n=80):
    """Upper and lower (u, v) curves in mm of a NACA 4-digit section with each surface moved `off` inward, over the
    chord range where the section is thicker than 2 off + 0.1 mm. u from the leading edge, v normal to the chord."""
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    up, lo = [], []
    for i in range(n + 1):
        x = 0.5 * (1 - math.cos(math.pi * i / n))
        yt = 5 * t * chord * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4) - off
        if yt < 0.05:
            continue
        yc = dy = 0.0
        if m and x < p:
            yc, dy = m / p ** 2 * (2 * p * x - x * x), 2 * m / p ** 2 * (p - x)
        elif m:
            yc, dy = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x * x), 2 * m / (1 - p) ** 2 * (p - x)
        th = math.atan(dy)
        up.append((x * chord - yt * math.sin(th), yc * chord + yt * math.cos(th)))
        lo.append((x * chord + yt * math.sin(th), yc * chord - yt * math.cos(th)))
    return up, lo


def extrude_section(comp, name, plane, pts_up, pts_lo, total):
    """Closed profile from two fitted splines joined by lines at both ends, extruded symmetrically by `total` mm."""
    sk = comp.sketches.add(plane)
    sk.name = name + ' Section'
    mk = lambda pts: [sk.modelToSketchSpace(p) for p in pts]
    cu, cl = adsk.core.ObjectCollection.create(), adsk.core.ObjectCollection.create()
    for p in mk(pts_up): cu.add(p)
    for p in mk(pts_lo): cl.add(p)
    su = sk.sketchCurves.sketchFittedSplines.add(cu)
    sl = sk.sketchCurves.sketchFittedSplines.add(cl)
    sk.sketchCurves.sketchLines.addByTwoPoints(su.startSketchPoint, sl.startSketchPoint)
    sk.sketchCurves.sketchLines.addByTwoPoints(su.endSketchPoint, sl.endSketchPoint)
    sk.isVisible = False
    b = bm.sym(comp, [sk.profiles.item(0)], total, adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
    b.name = name
    return b


def inner_body(comp, member, side, foils, box):
    s = 1 if side == 'Port' else -1
    yc = s * HULL_Y
    x0, x1, y0, y1, z0, z1 = box
    if member == 'Strut':
        up, lo = inner_section('0012', STRUT['chord'], CAP_T)
        zm = (z0 + z1) / 2
        P = lambda u, v: bm.P(STRUT['le_x'] - u, yc + v, zm)
        return extrude_section(comp, f'Inner {member} {side}', bm.plane_at(comp, comp.xYConstructionPlane, zm),
                               [P(u, v) for u, v in up], [P(u, v) for u, v in lo], (z1 - z0) + 2)
    code, chord, qc_x, z_qc, inc = (('4412', foils['wchord'], WING_QC_X, WING_Z, foils['winc']) if member == 'Wing' else
                                    ('0012', foils['echord'], ELEV_QC_X, foils['zel'], foils['einc']))
    up, lo = inner_section(code, chord, CAP_T)
    a, le_x, ym = math.radians(inc), qc_x + 0.25 * chord, (y0 + y1) / 2

    def P(u, v):                                   # chord from the leading edge aft (-x), nose up by inc about the quarter chord
        dx, dz = (le_x - u) - qc_x, v
        return bm.P(qc_x + dx * math.cos(a) - dz * math.sin(a), ym, z_qc + dx * math.sin(a) + dz * math.cos(a))
    return extrude_section(comp, f'Inner {member} {side}', bm.plane_at(comp, comp.xZConstructionPlane, ym),
                           [P(u, v) for u, v in up], [P(u, v) for u, v in lo], abs(y1 - y0) + 2)


def bands(side, foils):
    """(member, box) cap bands for one side, as (x0, x1, y0, y1, z0, z1) in mm."""
    s = 1 if side == 'Port' else -1
    yc = s * HULL_Y
    wc, ws, ec, es, zel = foils['wchord'], foils['wspan'], foils['echord'], foils['espan'], foils['zel']
    xs = STRUT['le_x'] - 0.3 * STRUT['chord']                       # thickest point of NACA 0012 / 4412 at about 30 % chord
    xw = WING_QC_X + 0.25 * wc - 0.3 * wc
    xe = ELEV_QC_X + 0.25 * ec - 0.3 * ec
    tip = HULL_Y - ws
    y_w = sorted((s * (tip + 1.0), s * (HULL_Y - 0.12 * STRUT['chord'] / 2 - 0.5)))
    return [('Strut', (xs - CAP_W / 2, xs + CAP_W / 2, yc - 6, yc + 6, WING_Z + 0.12 * wc / 2 + 0.04 * wc + 1.0, STRUT['z1'] - 1.0)),
            ('Wing', (xw - CAP_W / 2, xw + CAP_W / 2, y_w[0], y_w[1], WING_Z - 8, WING_Z + 8)),
            ('Elevator', (max(xe - CAP_W / 2, ELEV_QC_X - 0.75 * ec + 1.5), min(xe + CAP_W / 2, ELEV_QC_X + 0.25 * ec - 1.0),
                          yc - es / 2 + 1.0, yc + es / 2 - 1.0, zel - 6, zel + 6))]


def add_body(comp, name, temp):
    """Add a temporary body in its own base feature and name it after finishEdit (names set inside the edit can revert)."""
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    comp.bRepBodies.add(temp, bf)
    bf.finishEdit()
    body = bf.bodies.item(0)
    body.name = name
    return body


def cut(comp, target, tools, keep):
    col = adsk.core.ObjectCollection.create()
    for t in tools: col.add(t)
    ci = comp.features.combineFeatures.createInput(target, col)
    ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    ci.isKeepToolBodies = keep
    comp.features.combineFeatures.add(ci)


def apply(design, foils, stl_dir):
    root = design.rootComponent
    kit = [o for o in root.occurrences if o.component.name == 'Foiling Kit'][0].component
    for o in list(root.occurrences):
        if o.component.name == 'Foil Cores (print)':
            o.deleteMe()
    comp = bm.new_comp(root, 'Foil Cores (print)')
    tbm = adsk.fusion.TemporaryBRepManager.get()
    out = {}
    for side in ('Port', 'Stbd'):
        caps = {'L': [], 'Elevator': []}
        for member, box in bands(side, foils):
            src = kit.bRepBodies.itemByName(f'Elevator {side}' if member == 'Elevator' else f'L-Foil {side}')
            chunk = tbm.copy(src)
            tbm.booleanOperation(chunk, bm.tbox(*box), adsk.fusion.BooleanTypes.IntersectionBooleanType)
            name = f'Cap {member} {side}'
            cap = add_body(comp, name, chunk)
            cut(comp, cap, [inner_body(comp, member, side, foils, box)], False)
            parts = [b for b in comp.bRepBodies if b.name == name or b.name.startswith(name + ' (')]   # the cut splits it: one per face
            for i, b in enumerate(sorted(parts, key=lambda b: (b.boundingBox.minPoint.y, b.boundingBox.minPoint.z))):
                b.name = f'{name} {"AB"[i] if i < 2 else i}'
                caps['Elevator' if member == 'Elevator' else 'L'].append(b.name)
            out[name] = (round(sum(b.volume for b in parts) * 1000, 0), len(parts))
        for core, src in ((f'Core L-Foil {side}', f'L-Foil {side}'), (f'Core Elevator {side}', f'Elevator {side}'), (f'Core Flap {side}', f'Flap {side}')):
            add_body(comp, core, tbm.copy(kit.bRepBodies.itemByName(src)))
        by = comp.bRepBodies.itemByName
        cut(comp, by(f'Core L-Foil {side}'), [by(n) for n in caps['L']], True)
        cut(comp, by(f'Core Elevator {side}'), [by(n) for n in caps['Elevator']], True)
    em = design.exportManager
    files = {'Core L-Foil Port': 'Foil_Core_L_Port.stl', 'Core L-Foil Stbd': 'Foil_Core_L_Stbd.stl',
             'Core Elevator Port': 'Foil_Core_Elevator_x2.stl', 'Core Flap Port': 'Foil_Flap_x2.stl'}
    for body_name, fn in files.items():
        b = comp.bRepBodies.itemByName(body_name)
        opt = em.createSTLExportOptions(b, os.path.join(stl_dir, fn))
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        em.execute(opt)
        out[fn] = (round(b.volume * 1000, 0), b.lumps.count)
    for o in root.occurrences:
        if o.component.name == 'Foil Cores (print)':
            o.isLightBulbOn = False
    return out
