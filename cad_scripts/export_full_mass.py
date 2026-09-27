"""Exports mass properties of the 1 m boat (both configurations) from the foiling master design to
analysis/cad_data.json. Run inside Fusion via MCP exec with the 'RC Foiling Catamaran v1' design active."""
import adsk.core, adsk.fusion, math, json, os, sys, importlib

ADDIN = os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim')
OUT = os.path.expanduser('~/RC-Foiling-Cat/analysis/cad_data.json')
PETG, CFRP, AL, STEEL = 1.27, 1.55, 2.7, 7.85
FIXED = {  # g
    'Traveler Winch Servo': 45, 'Winch Drum': 5, 'Mainsheet Servo': 62, 'Jib Sheet Winch Servo': 45, 'Jib Winch Drum': 4,
    'Mainsheet Tail': 1, 'Rudder Servo': 12.2, 'Receiver': 14.9, 'Battery 2S': 123,
    'Mast Tube Base': 0, 'Forestay': 3, 'Shroud Port': 3, 'Shroud Stbd': 3, 'Bridle Port': 2, 'Bridle Stbd': 2,
    'Mainsheet': 1, 'Jib Sheet': 1}
MAST_PRINT = 'Mast Fittings (print)'   # rig_fittings.py: fairing shells, gooseneck, boom jaw; their mass goes on the Wing Mast
mast_print_g = 0.0
NOTE = 'winches: JX W4505-4T / -2T 45 g (1.5T spec, same case assumed); mainsheet FS5115M 62 g (Pololu); rudder MG90S 12.2 g; receiver FS-iA6B 14.9 g; battery 4 x 27 g eneloop + 15 g holder'


def tube(od, wall, L):
    ro = od / 2; ri = ro - wall
    return math.pi * (ro * ro - ri * ri) * L * CFRP


def mass_of(b):
    n = b.name; v = b.volume if b.isSolid else 0.0
    if n in FIXED: return FIXED[n]
    if n.startswith('Hull'): return v * PETG * 1.05
    if n in ('Pod Shell', 'Pod Lid', 'Rudder Servo Bracket', 'Rudder Servo Cover'): return v * PETG
    if n in ('Front Beam', 'Rear Beam'): return tube(1.6, 0.1, 60)
    if n == 'Pod Beam': return tube(1.0, 0.1, 60)   # 10 x 8 mm, cut from the mast-joiner tube
    if n == 'Wing Mast': return tube(1.2, 0.1, 129.8) + mast_print_g
    if n == 'Main Boom': return tube(0.8, 0.1, 34.5)
    if n in ('Mainsail', 'Jib'): return b.area / 1e4 * 36 + (3.0 if n == 'Mainsail' else 1.0)
    if n.startswith('Batten'): return 0.4
    if n.startswith(('Rudder Blade', 'Rudder Extension', 'Daggerboard')): return v * 1.0
    if n.startswith('Elevator Trim Pod'): return v * PETG + 2 * 0.3   # printed pod + two M2 x 6 screws (about 0.3 g each, assumed)
    if n.startswith('Elevator Pivot Pin'): return v * CFRP
    if n.startswith('Gudgeon'): return v * PETG
    if n.startswith(('Wand Pivot', 'Wand Hub', 'Bellcrank Mount', 'Strut Bellcrank', 'Flap Horn')): return v * PETG   # linkage.py
    if n in ('Wand Port', 'Wand Stbd'): return v * CFRP
    if n.startswith(('Deck Pushrod', 'Strut Pushrod')): return v * STEEL
    if n.startswith(('Traveler Track', 'Jib Track', 'Traveler Car', 'Jib Car', 'Bridle Post', 'Mast Cap', 'Hounds Collar')): return v * PETG
    if n.startswith(('Rudder Stock', 'Tiller', 'Tie Bar', 'Rudder Pushrod', 'Turning Pin')): return v * STEEL   # music wire
    if n.startswith(('L-Foil', 'Elevator', 'Flap')): return v * CFRP
    raise Exception('no mass rule ' + n)


def mast_print_mass(design):
    mp = [o.component for o in design.rootComponent.occurrences if o.component.name == MAST_PRINT]
    return sum(b.volume for b in mp[0].bRepBodies) * PETG if mp else 10.0


def export(design):
    global mast_print_g
    if ADDIN not in sys.path:
        sys.path.insert(0, ADDIN)
    import rig_model
    importlib.reload(rig_model)
    rig_model.set_profile('full')
    plan = {s['name']: s for s in rig_model.planform()}
    bodies = {}
    mast_print_g = mast_print_mass(design)
    for occ in design.rootComponent.occurrences:
        if occ.component.name in ('Print Segments', 'Foil Cores (print)', MAST_PRINT):
            continue
        for b in occ.component.bRepBodies:
            bodies[b.name] = (occ.component.name, b)
    out = {}
    for cfg, exclude in (('displacement', ('Foiling Kit', 'Ride Height Control')), ('foiling', ('Displacement Kit',))):
        M = 20.0; mx = 20 * 500.0; mz = 20 * 80.0; comp_m = {}; items = []
        for n, (c, b) in bodies.items():
            if c in exclude:
                continue
            m = mass_of(b)
            if n in plan:
                cx, cz = plan[n]['x_mm'], plan[n]['z_mm']
            elif b.isSolid and b.volume > 1e-6:
                cg = b.physicalProperties.centerOfMass; cx, cz = cg.x * 10, cg.z * 10
            else:
                bb = b.boundingBox; cx = (bb.minPoint.x + bb.maxPoint.x) * 5; cz = (bb.minPoint.z + bb.maxPoint.z) * 5
            M += m; mx += m * cx; mz += m * cz
            comp_m[c] = comp_m.get(c, 0) + m
            items.append([c, n, round(m, 1)])
        comp_m['Wiring allowance'] = 20
        out[cfg] = dict(mass_g=round(M, 1), lcg_mm=round(mx / M, 1), vcg_mm=round(mz / M, 1),
                        by_component_g={k: round(v, 1) for k, v in comp_m.items()}, items=items, note=NOTE)
    out['sails'] = [dict(name=k, area_m2=v['area_m2'], x_mm=v['x_mm'], z_mm=v['z_mm']) for k, v in plan.items()]
    json.dump(out, open(OUT, 'w'), indent=1)
    return out
