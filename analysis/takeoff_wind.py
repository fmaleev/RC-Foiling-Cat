"""Least true wind to fly for the CAD foiling boat, by bisection on the VPP (to 0.02 kn), at 90 and 60 deg.
sensitivity.py steps the wind in 0.25 kn; this refines the baseline. Writes takeoff_wind.json."""
import json, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    vpp.configure()
    b = vpp.load_pitch_limits(vpp.Boat('foiling', json.load(open(os.path.join(HERE, 'cad_data.json')))), 'foiling_1m')
    flies = lambda tws, twa: b.solve(tws * 0.5144, twa)['mode'] == 'foiling'
    out = {}
    for twa in (90, 60):
        lo, hi = 4.0, 16.0
        if not flies(hi, twa):
            out[str(twa)] = None
            continue
        while hi - lo > 0.02:
            m = (lo + hi) / 2
            lo, hi = (lo, m) if flies(m, twa) else (m, hi)
        out[str(twa)] = round(hi, 2)
        print(twa, 'deg: flies from', out[str(twa)], 'kn', flush=True)
    json.dump(out, open(os.path.join(HERE, 'takeoff_wind.json'), 'w'), indent=1)
