"""Flying trim in heave and pitch (vpp.Boat.fly_trim) for the CAD foils and the two earlier foil sets.

The trim model (vpp.py): the sail drive equals the flying drag and acts at the sail centre of effort, the drag at the
appendages, so the foils must balance a bow-down couple F (z_ce - z_drag). The fixed-incidence elevators set the pitch,
the wand-driven flaps make up the main foils' lift, and the wand (hinged at the bow, tip on the water, read in the boat
frame) sets the bow height. Depths, rudder immersion and hull clearance follow from that attitude.
Writes pitch_trim_results.json and paper/data/trim_<design>.dat (speed, pitch, elevator depth, rudder immersion).
"""
import contextlib, json, math, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = json.load(open(os.path.join(HERE, 'cad_data.json')))
DATA = os.path.join(HERE, '..', 'paper', 'data')
KEYS = ('WING_SPAN', 'WING_C', 'INC_MAIN_DEG', 'EL_SPAN', 'EL_C', 'INC_EL_DEG', 'Z_EL')
DESIGNS = {'v2.0': (0.200, 0.060, 2.0, 0.150, 0.036, 3.0, -0.197), 'v2.1': (0.160, 0.040, 0.0, 0.140, 0.032, 4.0, -0.197)}


def foil_parts(ws, wc, es, ec, zel):
    """g and x (mm): both wings, both elevators (solid carbon) and the rudder blade added below the build-first rudder tip
    (CAD mass-export densities). Only differences between designs are used, so the reference height cancels."""
    z_ref = vpp.Z_RUDDER + vpp.RUDDER_BELOW_EL          # elevator height with no rudder extension (-0.197 m)
    return [(2 * 1.55 * vpp.area_coeff('4412') * wc ** 2 * ws * 1e6, vpp.X_MAIN_FOIL),
            (2 * 1.55 * vpp.area_coeff('0012') * ec ** 2 * es * 1e6, vpp.X_EL),
            (2 * 1.0 * vpp.area_coeff('0012') * vpp.RUDDER_C ** 2 * (z_ref - zel) * 1e6, vpp.X_RUDDER_TIP * 1000)]


@contextlib.contextmanager
def design(values):
    """Swap the foil geometry in vpp; the CAD mass and centre of gravity change with the foil and rudder masses."""
    saved = {k: getattr(vpp, k) for k in KEYS}
    cad = json.loads(json.dumps(CAD))
    new = foil_parts(*values[:2], *values[3:5], values[6])
    old = foil_parts(*[saved[k] for k in ('WING_SPAN', 'WING_C', 'EL_SPAN', 'EL_C', 'Z_EL')])
    m0, x0 = cad['foiling']['mass_g'], cad['foiling']['lcg_mm']
    m1 = m0 + sum(m for m, _ in new) - sum(m for m, _ in old)
    cad['foiling']['lcg_mm'] = (m0 * x0 + sum(m * x for m, x in new) - sum(m * x for m, x in old)) / m1
    cad['foiling']['mass_g'] = m1
    for k, v in zip(KEYS, values):
        setattr(vpp, k, v)
    try:
        yield vpp.Boat('foiling', cad)
    finally:
        for k, v in saved.items():
            setattr(vpp, k, v)


def rows(b, v_lo=2.0, v_hi=5.0, dv=0.1):
    out, V = [], v_lo
    while V <= v_hi + 1e-9:
        t = b.fly_trim(V)
        out.append(dict(V=round(V, 2), pitch_deg=round(math.degrees(t['theta']), 2), flap_deg=round(math.degrees(t['delta']), 2),
                        elevator_lift_N=round(t['Le'], 2), pitch_couple_Nm=round(t['Mp'], 3), el_depth_mm=round(t['elD'] * 1000, 1),
                        main_depth_mm=round(t['mD'] * 1000, 1), rudder_immersion_mm=round(t['rudI'] * 1000, 1),
                        hull_clearance_mm=round(t['hull'] * 1000, 1), feasible=t['feasible'], why=t['why']))
        V = round(V + dv, 2)
    return out


if __name__ == '__main__':
    vpp.configure()
    cad_values = tuple(getattr(vpp, k) for k in KEYS)
    out = {}
    for name, vals in list(DESIGNS.items()) + [('CAD', cad_values)]:
        with design(vals) as b:
            r = rows(b)
            out[name] = dict(geometry=dict(zip(KEYS, vals)), mass_g=round(b.M * 1000, 1), takeoff_ms=b.vto and round(b.vto, 3),
                             flying_range_top_ms=b.vfly_max and round(b.vfly_max, 3), flying_range_limit=b.fly_limit, rows=r)
            with open(os.path.join(DATA, f"trim_{name.replace('.', '')}.dat"), 'w') as f:
                f.write('V pitch eldepth rudder feasible\n' + ''.join(f"{x['V']} {x['pitch_deg']} {x['el_depth_mm']} {x['rudder_immersion_mm']} {int(x['feasible'])}\n" for x in r))
            print(name, out[name]['mass_g'], 'g, take-off', out[name]['takeoff_ms'], 'flies to', out[name]['flying_range_top_ms'], out[name]['flying_range_limit'])
    # robustness of the CAD design: pitch couple, mass and centre of gravity
    rob = []
    for label, couple, mass, dx, fr in (('model', 1.0, 1.0, 0, 'turbulent'), ('couple x0.5', 0.5, 1.0, 0, 'turbulent'),
                                        ('couple x1.5', 1.5, 1.0, 0, 'turbulent'), ('mass +10%', 1.0, 1.1, 0, 'turbulent'),
                                        ('mass -10%', 1.0, 0.9, 0, 'turbulent'), ('CG 20 mm forward', 1.0, 1.0, 20, 'turbulent'),
                                        ('CG 20 mm aft', 1.0, 1.0, -20, 'turbulent'), ('foil friction laminar (low Re)', 1.0, 1.0, 0, 'transitional')):
        vpp.COUPLE_FACTOR, vpp.FOIL_FRICTION = couple, fr
        cad = json.loads(json.dumps(CAD)); cad['foiling']['mass_g'] *= mass; cad['foiling']['lcg_mm'] += dx
        b = vpp.Boat('foiling', cad)
        rob.append(dict(case=label, takeoff_ms=b.vto and round(b.vto, 3), flying_range_top_ms=b.vfly_max and round(b.vfly_max, 3), limit=b.fly_limit))
        print(rob[-1])
    vpp.COUPLE_FACTOR, vpp.FOIL_FRICTION = 1.0, 'turbulent'
    out['robustness'] = rob
    json.dump(out, open(os.path.join(HERE, 'pitch_trim_results.json'), 'w'), indent=1)
