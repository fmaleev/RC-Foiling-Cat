"""Exports mass properties of the active RC Mini Cat design to mini/cad_data_mini.json (run inside Fusion)."""
import adsk.core, adsk.fusion, math, json, os, sys, importlib

ADDIN = os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim')
OUT = os.path.expanduser('~/RC-Foiling-Cat/mini/cad_data_mini.json')
PETG, CFRP, STEEL = 1.27, 1.55, 7.85
FIXED = {'Sail Winch Servo': (45, 'JX W4505 spec'), 'Winch Drum': (5, 'printed, assumed'), 'Rudder Servo': (12.2, 'MG90S spec'),
         'Receiver': (14.9, 'FS-iA6B spec'), 'Battery 4xAA NiMH': (123, '4 x 27 g eneloop + 15 g holder (assumed)'),
         'Mast Cap': (1, 'allowance'), 'Forestay': (1, 'allowance'), 'Shroud Port': (1, 'allowance'), 'Shroud Stbd': (1, 'allowance'),
         'Bridle Port': (1, 'allowance'), 'Bridle Stbd': (1, 'allowance'), 'Mainsheet': (0.5, 'allowance'), 'Jib Sheet': (0.5, 'allowance')}


def tube(od, idd, L_mm):
    return math.pi * ((od / 2) ** 2 - (idd / 2) ** 2) * L_mm / 1000 * CFRP


def mass_of(b):
    n = b.name; v = b.volume if b.isSolid else 0.0
    if n.startswith('Battery'): return FIXED['Battery 4xAA NiMH']
    if n in FIXED: return FIXED[n]
    if n.startswith('Hull'): return v * PETG * 1.05, 'PETG 0.8 mm skin as modeled +5%'
    if n in ('Box', 'Box Lid'): return v * PETG, 'PETG as modeled'
    if n in ('Front Beam', 'Rear Beam'): return tube(10, 8, 360), 'CF tube 10x8 (CST CS-525)'
    if n == 'Mast': return tube(6, 4, 800), 'CF tube 6x4 (CST CS-518)'
    if n == 'Main Boom': return tube(4, 2, 207), 'CF tube 4 mm OD, ID assumed 2'
    if n in ('Mainsail', 'Jib'): return b.area / 1e4 * 36 + (3.0 if n == 'Mainsail' else 1.0), 'Icarex 36 g/m2 + tape'
    if n.startswith('Batten'): return 0.4, '1.2 mm CF rod'
    if n.startswith(('Rudder Blade', 'Daggerboard')): return v * 1.0, 'print, eff 1.0 g/cm3'
    if n.startswith('Gudgeon'): return v * PETG, 'PETG'
    if n.startswith(('Rudder Stock', 'Tiller', 'Tie Bar', 'Rudder Pushrod')): return v * STEEL, 'music wire'
    raise Exception('no mass rule ' + n)


def export(design):
    if ADDIN not in sys.path:
        sys.path.insert(0, ADDIN)
    import rig_model
    importlib.reload(rig_model)
    rig_model.set_profile('mini')
    plan = {s['name']: s for s in rig_model.planform()}
    M = 10.0; mx = 10 * 220.0; mz = 10 * 60.0; comp_m = {}; items = []
    for occ in design.rootComponent.occurrences:
        c = occ.component.name
        if c == 'Print Segments':
            continue
        for b in occ.component.bRepBodies:
            m, note = mass_of(b)
            if b.name in plan:
                cx, cz = plan[b.name]['x_mm'], plan[b.name]['z_mm']
            elif b.isSolid and b.volume > 1e-6:
                cg = b.physicalProperties.centerOfMass; cx, cz = cg.x * 10, cg.z * 10
            else:
                bb = b.boundingBox; cx = (bb.minPoint.x + bb.maxPoint.x) * 5; cz = (bb.minPoint.z + bb.maxPoint.z) * 5
            M += m; mx += m * cx; mz += m * cz
            comp_m[c] = comp_m.get(c, 0) + m
            items.append([c, b.name, round(m, 1), note])
    comp_m['Wiring allowance'] = 10
    out = {'displacement': dict(mass_g=round(M, 1), lcg_mm=round(mx / M, 1), vcg_mm=round(mz / M, 1),
                                by_component_g={k: round(v, 1) for k, v in comp_m.items()}, items=items),
           'sails': [dict(name=k, area_m2=v['area_m2'], x_mm=v['x_mm'], z_mm=v['z_mm']) for k, v in plan.items()]}
    json.dump(out, open(OUT, 'w'), indent=1)
    return out
