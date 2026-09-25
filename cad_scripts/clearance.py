"""Rig-to-pod clearance sweep for the 1 m boat. Run inside Fusion via MCP exec: sweep(design, [(main_deg, jib_deg), ...])."""
import adsk.core, adsk.fusion, os, sys

ADDIN = os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim')
if ADDIN not in sys.path:
    sys.path.insert(0, ADDIN)
import fusion_rig

POD = ('Pod Shell', 'Pod Lid', 'Rudder Servo Bracket', 'Rudder Servo Cover')
SKIP = {('Main Boom', 'Main Boom'), ('Mainsheet', 'Main Boom'), ('Main Boom', 'Wing Mast'), ('Main Boom', 'Mast Tube Base'),
        ('Main Boom', 'Mast')}  # joined by design (gooseneck)
TOL = {('Mainsheet', 'Box Lid'): 0.5, ('Jib Sheet', 'Box Lid'): 0.5}   # mm3: sheet ends sit in the lid fairleads


def overlap(a, b):
    if not a.boundingBox.intersects(b.boundingBox):
        return 0.0
    tbm = adsk.fusion.TemporaryBRepManager.get()
    t = tbm.copy(a)
    tbm.booleanOperation(t, tbm.copy(b), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return round(t.volume * 1000, 2)


def sweep(design, trims):
    comps = {o.component.name: o.component for o in design.rootComponent.occurrences}
    if 'Center Pod' in comps:   # 1 m boats
        fixed = [comps['Center Pod'].bRepBodies.itemByName(n) for n in POD]
        fixed += [comps['Rig Standing'].bRepBodies.itemByName('Mast Tube Base'), comps['Mast'].bRepBodies.itemByName('Wing Mast')]
        fixed += list(comps['Crossbeams'].bRepBodies)
    else:                       # mini: electronics box, round mast, no cars
        fixed = [comps['Electronics Box'].bRepBodies.itemByName(n) for n in ('Box', 'Box Lid')]
        fixed += [comps['Rig Standing'].bRepBodies.itemByName('Mast')]
    c0 = fusion_rig.read_controls(design)
    out = []
    for md, jd in trims:
        fusion_rig.update(design, dict(jib_deg=float(jd), main_deg=float(md), tension=c0['tension']))
        boom = comps['Mainsail'].bRepBodies.itemByName('Main Boom')
        moving = [b for b in (comps['Mainsail'].bRepBodies.itemByName(n) for n in ('Mainsheet', 'Traveler Car', 'Main Boom')) if b]
        moving += [b for b in (comps['Jib'].bRepBodies.itemByName(n) for n in ('Jib Sheet', 'Jib Car')) if b]
        hits = [(m.name, f.name, v) for m in moving for f in fixed + [boom] if (m.name, f.name) not in SKIP and (v := overlap(m, f)) > TOL.get((m.name, f.name), 0.0)]
        out.append(dict(main=md, jib=jd, hits=hits))
    fusion_rig.update(design, c0)
    return out
