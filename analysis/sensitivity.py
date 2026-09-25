"""Takeoff wind speed and its sensitivity to the least certain VPP inputs."""
import json, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = json.load(open(os.path.join(HERE, 'cad_data.json')))


def takeoff_tws(boat, twa, lo=4.0, hi=16.0, step=0.25):
    tws = lo
    while tws <= hi:
        r = boat.solve(tws * 0.5144, twa)
        if r['mode'] == 'foiling':
            return tws, r['V']
        tws += step
    return None, None


def scenario(name, cl_max=1.3, foil_lift=1.0, mass=1.0, couple=1.0):
    vpp.CL_MAX, vpp.COUPLE_FACTOR = cl_max, couple
    cad = json.loads(json.dumps(CAD))
    cad['foiling']['mass_g'] *= mass
    b = vpp.load_pitch_limits(vpp.Boat('foiling', cad), 'foiling_1m')
    b.cl_main *= foil_lift; b.cl_el *= foil_lift; b.cl_main_flap *= foil_lift; b.a_main *= foil_lift; b.a_el *= foil_lift
    b.fly_range()
    row = dict(scenario=name, takeoff_speed_ms=b.vto and round(b.vto, 2), flying_range_top_ms=b.vfly_max and round(b.vfly_max, 2),
               flying_range_limit=b.fly_limit)
    for twa in (60, 90):
        tws, v = takeoff_tws(b, twa)
        row[f'TWA{twa}_takeoff_tws_kn'] = tws
        row[f'TWA{twa}_speed_after_ms'] = v
    return row


if __name__ == '__main__':
    rows = [scenario('baseline'),
            scenario('sail CLmax 1.1', cl_max=1.1),
            scenario('sail CLmax 1.5', cl_max=1.5),
            scenario('foil lift -20% (low Re, free surface)', foil_lift=0.8),
            scenario('mass +10%', mass=1.10),
            scenario('mass -10%', mass=0.90),
            scenario('sail-drive pitch couple x0.5', couple=0.5),
            scenario('sail-drive pitch couple x1.5', couple=1.5)]
    vpp.CL_MAX, vpp.COUPLE_FACTOR = 1.3, 1.0
    json.dump(rows, open(os.path.join(HERE, 'sensitivity_results.json'), 'w'), indent=1)
    for r in rows:
        print(r)
