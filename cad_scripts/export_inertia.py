"""Pitch and roll moments of inertia of the 1 m foiling boat about its centre of gravity, written to
analysis/cad_inertia.json. Run inside Fusion via MCP exec on the foiling master. Masses follow export_full_mass.mass_of
(the same rules as analysis/cad_data.json). Each solid body contributes its own inertia about its centroid, from Fusion's
physical properties rescaled from Fusion's material mass to that mass, plus the parallel-axis term. The sails are
surfaces: point masses at their planform centroid plus a thin triangle about it, m (dx^2 + dz^2) / 18 (assumed shape).
The 20 g wiring allowance is a point mass at the CAD export's location (x = 500, z = 80 mm)."""
import adsk.core, adsk.fusion, json, os, sys, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser('~/RC-Foiling-Cat/analysis/cad_inertia.json')


def export(design):
    sys.path.insert(0, HERE)
    import export_full_mass as efm
    importlib.reload(efm)
    efm.mast_print_g = efm.mast_print_mass(design)
    if efm.ADDIN not in sys.path:
        sys.path.insert(0, efm.ADDIN)
    import rig_model
    importlib.reload(rig_model)
    rig_model.set_profile('full')
    plan = {s['name']: s for s in rig_model.planform()}
    items = []                                    # (kg, x m, z m, Iyy_own kg m2, Ixx_own kg m2, y m)
    for occ in design.rootComponent.occurrences:
        c = occ.component.name
        if c in ('Print Segments', 'Foil Cores (print)', efm.MAST_PRINT, 'Displacement Kit'):
            continue
        for b in occ.component.bRepBodies:
            m = efm.mass_of(b) / 1000.0
            if b.name in plan:
                bb = b.boundingBox
                dx, dz = (bb.maxPoint.x - bb.minPoint.x) / 100, (bb.maxPoint.z - bb.minPoint.z) / 100
                own = m * (dx * dx + dz * dz) / 18
                items.append((m, plan[b.name]['x_mm'] / 1000, plan[b.name]['z_mm'] / 1000, own, m * dz * dz / 18, 0.0))
                continue
            pp = b.physicalProperties
            cg = pp.centerOfMass
            x, y, z = cg.x / 100, cg.y / 100, cg.z / 100
            if b.isSolid and pp.mass > 1e-9:
                _, ixx, iyy, izz, ixy, iyz, ixz = pp.getXYZMomentsOfInertia()      # kg cm2 about the world origin
                mf = pp.mass
                iyy_c = (iyy - mf * ((cg.x) ** 2 + (cg.z) ** 2)) / 1e4                # kg m2 about the centroid
                ixx_c = (ixx - mf * ((cg.y) ** 2 + (cg.z) ** 2)) / 1e4
                items.append((m, x, z, iyy_c * m / mf, ixx_c * m / mf, y))
            else:
                items.append((m, x, z, 0.0, 0.0, y))
    items.append((0.020, 0.500, 0.080, 0.0, 0.0, 0.0))
    M = sum(i[0] for i in items)
    xg = sum(i[0] * i[1] for i in items) / M
    zg = sum(i[0] * i[2] for i in items) / M
    iyy = sum(i[3] + i[0] * ((i[1] - xg) ** 2 + (i[2] - zg) ** 2) for i in items)
    ixx = sum(i[4] + i[0] * (i[5] ** 2 + (i[2] - zg) ** 2) for i in items)
    out = dict(mass_kg=round(M, 4), lcg_mm=round(xg * 1000, 1), vcg_mm=round(zg * 1000, 1), Iyy_kgm2=round(iyy, 5), Ixx_kgm2=round(ixx, 5),
               k_pitch_m=round((iyy / M) ** 0.5, 4), note='cad_scripts/export_inertia.py: foiling configuration, masses as in cad_data.json')
    json.dump(out, open(OUT, 'w'), indent=1)
    return out
