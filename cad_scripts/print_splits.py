"""Print pieces for a 220 x 220 mm bed. Run inside Fusion via MCP exec, after build_full_hull and foil_cores:
apply(design) on each 1 m document, then export(design) on the foiling master.

- Pod shell and lid: four pieces each (build_full_hull.segments, cuts at x = 455, 600 and 720 mm).
- Daggerboards: two pieces joined 20 mm above the hull bottom inside the trunk, where the trunk carries most of the
  moment; the lower piece (230 mm) prints diagonally. A 1.2 mm carbon rod bonded in a groove on each face runs 40 mm
  either side of the joint (analysis/structure.py checks it).
- L-foil cores: the strut splits inside the trunk, 16 mm above the hull bottom, so the lower piece (the wing and the lower
  strut) is 205 mm long. Two 2 mm carbon dowels align the pieces; the carbon caps, laid after bonding, run across the joint.
The one-piece STLs (Daggerboard_x2, Foil_Core_L_Port/Stbd) stay in stl/ for larger printers.
"""
import adsk.core, adsk.fusion, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import build_mini as bm
import build_full_hull as bfh

HULL_Y = 280.0
BOARD = dict(z_joint=-20.0, rod_x=572.0, rod_w=1.4, rod_half_len=40.0)   # rod groove at 30 % chord (LE x 590, chord 60)
CORE = dict(z_joint=-16.0, dowels=(580.0, 550.0), dowel_r=1.05, dowel_depth=12.0)


def T():
    return adsk.fusion.TemporaryBRepManager.get()


def comp_of(root, name):
    return [o.component for o in root.occurrences if o.component.name == name][0]


def clip(body, z0, z1):
    t = T().copy(body)
    T().booleanOperation(t, bm.tbox(-2000, 2000, -2000, 2000, z0, z1), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return t


def minus(t, tools):
    for x in tools:
        T().booleanOperation(t, x, adsk.fusion.BooleanTypes.DifferenceBooleanType)
    return t


def add_bodies(comp, items):
    bf = comp.features.baseFeatures.add()
    bf.startEdit()
    for name, t in items:
        comp.bRepBodies.add(t, bf)
    bf.finishEdit()
    n = comp.bRepBodies.count
    for i, (name, _) in enumerate(items):          # names set inside the edit can revert
        comp.bRepBodies.item(n - len(items) + i).name = name


def board_pieces(board):
    bb = board.boundingBox
    y0, y1 = bb.minPoint.y * 10, bb.maxPoint.y * 10
    zj, x, w, h = BOARD['z_joint'], BOARD['rod_x'], BOARD['rod_w'], BOARD['rod_half_len']
    grooves = [bm.tbox(x - w / 2, x + w / 2, y1 - w, y1 + 1.0, zj - h, zj + h), bm.tbox(x - w / 2, x + w / 2, y0 - 1.0, y0 + w, zj - h, zj + h)]
    lo = minus(clip(board, -1000, zj), [T().copy(g) for g in grooves])
    up = minus(clip(board, zj, 1000), [T().copy(g) for g in grooves])
    return lo, up


def core_pieces(core, yc):
    zj, r, d = CORE['z_joint'], CORE['dowel_r'], CORE['dowel_depth']
    holes = [bm.tcyl((x, yc, zj - d), (x, yc, zj + d), r) for x in CORE['dowels']]
    return minus(clip(core, -1000, zj), [T().copy(h) for h in holes]), minus(clip(core, zj, 1000), [T().copy(h) for h in holes])


def apply(design):
    root = design.rootComponent
    bfh.segments(design)                                   # hulls and the four-piece pod
    ps = comp_of(root, 'Print Segments')
    kit = comp_of(root, 'Displacement Kit')
    lo, up = board_pieces(kit.bRepBodies.itemByName('Daggerboard Port'))
    add_bodies(ps, [('Daggerboard Lower (print)', lo), ('Daggerboard Upper (print)', up)])
    out = {b.name: (round(b.volume, 2), b.lumps.count) for b in ps.bRepBodies if not b.name.startswith('Hull')}
    cores = [o.component for o in root.occurrences if o.component.name == 'Foil Cores (print)']
    if cores:
        fc = cores[0]
        items = []
        for side, s in (('Port', 1), ('Stbd', -1)):
            b = fc.bRepBodies.itemByName(f'Core L-Foil {side}')
            if b is None:                                  # already split
                continue
            lo, up = core_pieces(b, s * HULL_Y)
            items += [(f'Core L-Foil {side} Lower', lo), (f'Core L-Foil {side} Upper', up)]
            fc.features.removeFeatures.add(b)
        if items:
            add_bodies(fc, items)
        out.update({b.name: (round(b.volume, 2), b.lumps.count) for b in fc.bRepBodies if b.name.startswith('Core L-Foil')})
    return out


PRINT = [  # (print-list key, component, body, STL, qty); one-piece versions are left in stl/ for larger printers
    ('Daggerboard Lower (print)', 'Print Segments', 'Daggerboard Lower (print)', 'Daggerboard_Lower_x2.stl', 2),
    ('Daggerboard Upper (print)', 'Print Segments', 'Daggerboard Upper (print)', 'Daggerboard_Upper_x2.stl', 2),
    ('Core L-Foil Port Lower', 'Foil Cores (print)', 'Core L-Foil Port Lower', 'Foil_Core_L_Port_Lower.stl', 1),
    ('Core L-Foil Port Upper', 'Foil Cores (print)', 'Core L-Foil Port Upper', 'Foil_Core_L_Port_Upper.stl', 1),
    ('Core L-Foil Stbd Lower', 'Foil Cores (print)', 'Core L-Foil Stbd Lower', 'Foil_Core_L_Stbd_Lower.stl', 1),
    ('Core L-Foil Stbd Upper', 'Foil Cores (print)', 'Core L-Foil Stbd Upper', 'Foil_Core_L_Stbd_Upper.stl', 1),
]
DROP = ('Pod Shell Seg', 'Pod Lid Seg', 'Daggerboard Port', 'Core L-Foil Port', 'Core L-Foil Stbd')


def export(design):
    """Writes the pod, daggerboard and L-foil core pieces to stl/ and replaces their entries in the 1 m print list."""
    root = design.rootComponent
    em = design.exportManager
    path = os.path.join(ROOT, 'manual_1m', 'print_list_1m.json')
    pl = {k: v for k, v in json.load(open(path)).items() if not k.startswith(DROP)}
    ps = comp_of(root, 'Print Segments')
    jobs = [(b.name, 'Print Segments', b.name, b.name.replace(' (x', '_x').replace('-', '_').replace(')', '').replace(' ', '_') + '.stl', 1)
            for b in ps.bRepBodies if b.name.startswith(('Pod Shell Seg', 'Pod Lid Seg'))] + PRINT
    for key, cname, bname, stl, qty in jobs:
        b = comp_of(root, cname).bRepBodies.itemByName(bname)
        fn = os.path.join(ROOT, 'stl', stl)
        opt = em.createSTLExportOptions(b, fn)
        opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        em.execute(opt)
        bb = b.boundingBox
        size = sorted((round((bb.maxPoint.x - bb.minPoint.x) * 10), round((bb.maxPoint.y - bb.minPoint.y) * 10),
                       round((bb.maxPoint.z - bb.minPoint.z) * 10)), reverse=True)
        pl[key] = dict(stl=stl, qty=qty, cm3=round(b.volume, 2), size_mm=size, exists=os.path.exists(fn))
    json.dump(pl, open(path, 'w'), indent=1)
    return {k: (pl[k]['stl'], pl[k]['size_mm']) for k, *_ in jobs}
