"""Build numbers for the mini manual: rigging lengths, drum turns, 1:1 sail patterns (TikZ), print list."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim'))
import rig_model as rm

rm.set_profile('mini')
R = rm.RIG
d3 = lambda a, b: math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

tack = (R['tack'][0], 0.0, R['tack'][1])
hounds = (R['mast_x'], 0.0, R['hounds_z'])
bow = R['bow']; chain = R['chainplate']
rig = dict(
    forestay_mm=d3(tack, hounds),
    bridle_leg_mm=d3(tack, bow),
    shroud_mm=d3((R['mast_x'], R['mast_r'] - 1, R['hounds_z']), chain),
    hounds_above_mast_foot_mm=R['hounds_z'] - R['mast_z0'],
    mast_length_mm=R['mast_top'] - R['mast_z0'],
    boom_length_mm=R['main_c0'],
    boom_height_above_lid_mm=R['boom_z'] - R['lead_z'],
    main_fairlead_x_mm=R['main_lead_x'][0], jib_fairlead_x_mm=R['jib_lead_x'],
)
r0 = rm.readout(rm.single_sheet(0.0)); r1 = rm.readout(rm.single_sheet(45.0))
drum = dict(main_travel_mm=r1['mainsheet_len_mm'] - r0['mainsheet_len_mm'], jib_travel_mm=r1['jib_sheet_len_mm'] - r0['jib_sheet_len_mm'],
            main_groove_dia_mm=30.0, jib_groove_dia_mm=16.2)
drum['main_turns'] = drum['main_travel_mm'] / (math.pi * drum['main_groove_dia_mm'])
drum['jib_turns'] = drum['jib_travel_mm'] / (math.pi * drum['jib_groove_dia_mm'])

# flat patterns in the sail plane, origin at the tack; mainsail luff is vertical (mast), jib luff follows the forestay
flat = dict(jib_deg=0.0, main_deg=0.0, tension=100.0)
main = []
for k in range(41):
    s = k / 40
    z = R['z_foot'] + s * (R['z_head'] - R['z_foot'])
    chord = R['main_c0'] - (R['main_c0'] - R['main_ch']) * s ** R['main_p']
    main.append((z - R['z_foot'], chord))
jib = []
for k in range(21):
    t = k / 20
    z = R['jib_z0'] + t * (R['jib_head_z'] - R['jib_z0'])
    chord = R['jib_c0'] * (1 - t) + R['jib_ch'] * t
    xl = rm.jib_luff_x(z) - rm.jib_luff_x(R['jib_z0'])
    jib.append((z - R['jib_z0'], xl, chord))
battens = [round(R['z_foot'] + (k / (R['n_battens'] + 1)) * (R['z_head'] - R['z_foot']) - R['z_foot'], 1) for k in range(1, R['n_battens'] + 1)]
batten_len = [round(R['main_c0'] - (R['main_c0'] - R['main_ch']) * (h / (R['z_head'] - R['z_foot'])) ** R['main_p'] - 8, 1) for h in battens]
SLEEVE = 25.0   # luff sleeve allowance for the 6 mm mast (folded over, taped)

luff_len_jib = math.hypot(jib[-1][0], jib[-1][1])


def tikz():
    L = []
    L.append(r'\documentclass[border=10mm]{standalone}')
    L.append(r'\usepackage{tikz}\usetikzlibrary{calc}')
    L.append(r'\begin{document}\begin{tikzpicture}[x=1mm,y=1mm,font=\sffamily\small]')
    # mainsail: x to the left = aft; draw mirrored so luff is on the left of the sheet
    pts = ' -- '.join(f'({c:.1f},{h:.1f})' for h, c in main)
    L.append(r'\draw[very thick] (0,0) -- ' + pts + f' -- (0,{main[-1][0]:.1f}) -- cycle;')
    L.append(f'\\draw[dashed] (0,0) -- (-{SLEEVE},0) -- (-{SLEEVE},{main[-1][0]:.1f}) -- (0,{main[-1][0]:.1f});')
    L.append(f'\\node[rotate=90,anchor=south] at (-{SLEEVE/2:.1f},{main[-1][0]/2:.1f}) {{luff sleeve fold ({SLEEVE:.0f} mm)}};')
    for h, bl in zip(battens, batten_len):
        L.append(f'\\draw[blue, thick] (4,{h}) -- ({bl + 4:.1f},{h}) node[right,black] {{batten {bl:.0f} mm}};')
    L.append(r'\node[anchor=north west] at (0,-3) {MAINSAIL 1:1  (foot %.0f mm, luff %.0f mm, head %.0f mm)};' % (main[0][1], main[-1][0], main[-1][1]))
    for h, c in main[::8]:
        L.append(f'\\draw[gray] (0,{h:.1f}) -- ({c:.1f},{h:.1f}); \\node[gray,anchor=west] at ({c + 2:.1f},{h:.1f}) {{h={h:.0f}: {c:.1f}}};')
    # jib, placed to the right
    ox = main[0][1] + 90
    pts = ' -- '.join(f'({ox - xl + c:.1f},{h:.1f})' for h, xl, c in jib)
    luff = ' -- '.join(f'({ox - xl:.1f},{h:.1f})' for h, xl, c in reversed(jib))
    L.append(r'\draw[very thick] ' + pts + ' -- ' + luff + ' -- cycle;')
    L.append(r'\node[anchor=north west] at (%.1f,-3) {JIB 1:1  (foot %.0f mm, luff %.0f mm)};' % (ox, jib[0][2], luff_len_jib))
    for h, xl, c in jib[::5]:
        L.append(f'\\draw[gray] ({ox - xl:.1f},{h:.1f}) -- ({ox - xl + c:.1f},{h:.1f}); \\node[gray,anchor=west] at ({ox - xl + c + 2:.1f},{h:.1f}) {{h={h:.0f}: {c:.1f}}};')
    # scale check bar
    L.append(r'\draw[thick] (0,-15) -- (100,-15) node[midway,below] {scale check: this bar must measure 100 mm};')
    L.append(r'\end{tikzpicture}\end{document}')
    return '\n'.join(L)


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'manual'), exist_ok=True)
    open(os.path.join(HERE, 'manual', 'sail_patterns_1to1.tex'), 'w').write(tikz())
    out = dict(rig={k: round(v, 1) for k, v in rig.items()}, drum={k: round(v, 2) for k, v in drum.items()},
               battens_height_mm=battens, battens_length_mm=batten_len, jib_luff_mm=round(luff_len_jib, 1),
               main_table=[(round(h, 1), round(c, 1)) for h, c in main[::4]], jib_table=[(round(h, 1), round(-xl, 1), round(c, 1)) for h, xl, c in jib[::4]])
    json.dump(out, open(os.path.join(HERE, 'manual', 'manual_data.json'), 'w'), indent=1)
    print(json.dumps({k: out[k] for k in ('rig', 'drum', 'battens_height_mm', 'battens_length_mm', 'jib_luff_mm')}, indent=1))
