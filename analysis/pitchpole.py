"""Pitchpole wind limits: the true wind speed at which the sails' bow-down moment reaches the largest
longitudinal righting moment the hulls can give (from stability.py), per point of sail.

Bow-down moment = F_x * h_p, with h_p from the sail centre of effort down to the hull resistance centre
(half the hull draft below the waterline). Reaching with the windward hull up uses the one-hull limit;
otherwise the two-hull limit.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vpp


def limits(boat, stab):
    zr = boat.zw0 - (boat.zw0 - min(vpp.ZB(vpp.L_HULL * i / 50) for i in range(51))) / 2
    hp = boat.ce_z - zr
    out = {}
    for twa in (60, 90, 120, 150):
        lim = None
        rows = []
        for tws in [2 + 0.5 * k for k in range(37)]:
            r = boat.solve(tws * 0.5144, twa)
            vto = boat.takeoff_speed()
            fx, fy, s = boat.forces(r['V'], tws * 0.5144, twa, bool(vto and r['V'] >= vto))
            one_hull = abs(s['heel_util']) > 0.8
            rm_l = stab['pitch_1hull' if one_hull else 'pitch_2hull']['RM_L_max_Nm']
            ratio = fx * hp / rm_l
            rows.append((tws, round(fx, 2), round(ratio, 2), one_hull))
            if lim is None and ratio >= 1.0:
                lim = tws
        out[twa] = dict(pitchpole_tws_kn=lim, lever_m=round(hp, 3), rows=rows)
    return out


if __name__ == '__main__':
    stab = json.load(open(os.path.join(HERE, 'stability_results.json')))
    cad = json.load(open(os.path.join(HERE, 'cad_data.json')))
    vpp.configure()
    res = {'build_first_1m': limits(vpp.Boat('displacement', cad), stab['build_first_1m'])}
    sys.path.insert(0, os.path.join(HERE, '..', 'mini'))
    import mini_analysis
    res['mini_600'] = limits(vpp.Boat('displacement', mini_analysis.CAD), stab['mini_600'])
    json.dump(res, open(os.path.join(HERE, 'pitchpole_results.json'), 'w'), indent=1)
    for k, v in res.items():
        print(k, {twa: (d['pitchpole_tws_kn'], d['lever_m']) for twa, d in v.items()})
