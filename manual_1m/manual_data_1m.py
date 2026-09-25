"""Build numbers for the 1 m boat's manual: rigging lengths, sheet travels, batten lengths and 1:1 sail patterns (TikZ),
from the Sail Trim add-in's rig model ('full' profile, the same geometry as the CAD rig). Writes manual_data_1m.json and
sail_patterns_1m_1to1.tex (compile with tectonic)."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim'))
import rig_model as rm

rm.set_profile('full')
R = rm.RIG
d3 = lambda a, b: math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
tack = (R['tack'][0], 0.0, R['tack'][1])
hounds = (R['mast_x'], 0.0, R['hounds_z'])
rig = dict(forestay_mm=d3(tack, hounds), bridle_leg_mm=d3(tack, R['bow']), shroud_mm=d3((R['mast_x'], R['mast_r'] - 1, R['hounds_z']), R['chainplate']),
           hounds_above_mast_foot_mm=R['hounds_z'] - R['mast_z0'], mast_length_mm=R['mast_top'] - R['mast_z0'], boom_length_mm=R['main_c0'])
# jib sheet between the add-in's jib limits, traveler car across the main limits (other controls at their defaults)
ro = lambda **c: rm.readout(dict(rm.DEFAULTS, **c))
(j0, j1), (m0, m1) = rm.LIMITS['jib_deg'], rm.LIMITS['main_deg']
travel = dict(jib_sheet_mm=ro(jib_deg=j1)['jib_sheet_len_mm'] - ro(jib_deg=j0)['jib_sheet_len_mm'],
              traveler_mm=ro(main_deg=m1)['traveler_car_y_mm'] - ro(main_deg=m0)['traveler_car_y_mm'])
main = []
for k in range(41):
    s = k / 40
    main.append((s * (R['z_head'] - R['z_foot']), R['main_c0'] - (R['main_c0'] - R['main_ch']) * s ** R['main_p']))
jib = []
for k in range(21):
    t = k / 20
    z = R['jib_z0'] + t * (R['jib_head_z'] - R['jib_z0'])
    jib.append((z - R['jib_z0'], rm.jib_luff_x(z) - rm.jib_luff_x(R['jib_z0']), R['jib_c0'] * (1 - t) + R['jib_ch'] * t))
battens = [round((k / (R['n_battens'] + 1)) * (R['z_head'] - R['z_foot']), 1) for k in range(1, R['n_battens'] + 1)]
batten_len = [round(R['main_c0'] - (R['main_c0'] - R['main_ch']) * (h / (R['z_head'] - R['z_foot'])) ** R['main_p'] - 8, 1) for h in battens]
luff_jib = math.hypot(jib[-1][0], jib[-1][1])


def tikz():
    L = [r'\documentclass[border=10mm]{standalone}', r'\usepackage{tikz}',
         r'\begin{document}\begin{tikzpicture}[x=1mm,y=1mm,font=\sffamily\small]']
    L.append(r'\draw[very thick] (0,0) -- ' + ' -- '.join(f'({c:.1f},{h:.1f})' for h, c in main) + f' -- (0,{main[-1][0]:.1f}) -- cycle;')
    for h, bl in zip(battens, batten_len):
        L.append(f'\\draw[blue, thick] (4,{h}) -- ({bl + 4:.1f},{h}) node[right,black] {{batten {bl:.0f} mm}};')
    L.append(r'\node[anchor=north west] at (0,-3) {MAINSAIL 1:1 (foot %.0f mm, luff %.0f mm, head %.0f mm). Luff attachment to the wing mast: add your own allowance.};' % (main[0][1], main[-1][0], main[-1][1]))
    for h, c in main[::8]:
        L.append(f'\\draw[gray] (0,{h:.1f}) -- ({c:.1f},{h:.1f}); \\node[gray,anchor=west] at ({c + 2:.1f},{h:.1f}) {{h={h:.0f}: {c:.1f}}};')
    ox = main[0][1] + 110
    L.append(r'\draw[very thick] ' + ' -- '.join(f'({ox - xl + c:.1f},{h:.1f})' for h, xl, c in jib) + ' -- '
             + ' -- '.join(f'({ox - xl:.1f},{h:.1f})' for h, xl, c in reversed(jib)) + ' -- cycle;')
    L.append(r'\node[anchor=north west] at (%.1f,-10) {JIB 1:1 (foot %.0f mm, luff %.0f mm)};' % (ox, jib[0][2], luff_jib))
    for h, xl, c in jib[::5]:
        L.append(f'\\draw[gray] ({ox - xl:.1f},{h:.1f}) -- ({ox - xl + c:.1f},{h:.1f}); \\node[gray,anchor=west] at ({ox - xl + c + 2:.1f},{h:.1f}) {{h={h:.0f}: {c:.1f}}};')
    L.append(r'\draw[thick] (0,-20) -- (100,-20) node[midway,below] {scale check: this bar must measure 100 mm};')
    L.append(r'\end{tikzpicture}\end{document}')
    return '\n'.join(L)


if __name__ == '__main__':
    open(os.path.join(HERE, 'sail_patterns_1m_1to1.tex'), 'w').write(tikz())
    out = dict(rig={k: round(v, 1) for k, v in rig.items()}, travel={k: round(v, 1) for k, v in travel.items()},
               battens_height_mm=battens, battens_length_mm=batten_len, jib_luff_mm=round(luff_jib, 1),
               main=dict(foot=round(main[0][1], 1), luff=round(main[-1][0], 1), head=round(main[-1][1], 1)), jib_foot=round(jib[0][2], 1))
    json.dump(out, open(os.path.join(HERE, 'manual_data_1m.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))
