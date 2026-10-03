"""Diagrams for the Mini Cat build manual (TikZ), drawn from the project's geometry: the hull stations and layout in
cad_scripts/build_mini.py and servo_mounts.py, the rig model ('mini' profile) and manual_data.json. Each function returns
the LaTeX for one figure."""
import ast, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'fusion_addin', 'SailTrim'))
import rig_model as rm

rm.set_profile('mini')
R = rm.RIG
D = json.load(open(os.path.join(HERE, 'manual_data.json')))
RIG, DRUM = D['rig'], D['drum']


def consts(path, names):
    """Module-level constants of a Fusion script (it imports adsk, so it is parsed, not imported)."""
    out = {}
    for node in ast.parse(open(os.path.join(ROOT, path)).read()).body:
        if isinstance(node, ast.Assign):
            try:
                val = ast.literal_eval(node.value)
            except ValueError:
                try:                         # constants written with dict(...): only dict() is allowed
                    val = eval(compile(ast.Expression(node.value), path, 'eval'), {'__builtins__': {}, 'dict': dict})
                except Exception:
                    continue
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    out[t.id] = val
                elif isinstance(t, ast.Tuple):
                    for e, v in zip(t.elts, val):
                        if isinstance(e, ast.Name) and e.id in names:
                            out[e.id] = v
    return out


M = consts('cad_scripts/build_mini.py', {'STATIONS', 'FULL_STATIONS', 'K_L', 'K_S', 'HULL_Y', 'BEAMS', 'BOX', 'RUDDER', 'TIE_X', 'TIE_Z'})
if 'STATIONS' not in M:   # STATIONS is a comprehension in build_mini.py: rebuild it the same way
    M['STATIONS'] = [(x * M['K_L'], max(hw * M['K_S'], 2.4), zb * M['K_S'], zt * M['K_S']) for x, hw, zb, zt in M['FULL_STATIONS']]
LAY = consts('cad_scripts/servo_mounts.py', {'LAYOUT'})['LAYOUT']['mini']
ST = M['STATIONS']                       # (x, half-width, keel z, deck z), mm
STOCK_X = M['RUDDER']['le'] - 0.25 * M['RUDDER']['chord']
RUDDER_SERVO_X, WINCH_X = [x for _, x in LAY['servos']]
f0 = lambda v: f'{v:.0f}'


def fig(body, caption):
    return r"\begin{center}" + body + r"\par\captionof{figure}{" + caption + r"}\end{center}"


def hulls():
    """Side view of one hull in its three print segments, drawn apart (joints at x = 200 and 400 mm)."""
    s, gap = 0.022, 18.0                 # cm per mm; gap between the drawn segments (mm)
    cuts = [0.0, 200.0, 400.0, ST[-1][0]]
    def zat(x, k):
        for (x0, *a), (x1, *b) in zip(ST, ST[1:]):
            if x0 <= x <= x1:
                return a[k] + (b[k] - a[k]) * (x - x0) / (x1 - x0)
        return ST[-1][k + 1]
    parts = []
    for i in range(3):
        a, b = cuts[i], cuts[i + 1]
        xs = [a] + [p[0] for p in ST if a < p[0] < b] + [b]
        off = i * gap
        deck = ' '.join(f'({(x + off) * s:.3f},{zat(x, 2) * s:.3f})' for x in xs)
        keel = ' '.join(f'({(x + off) * s:.3f},{zat(x, 1) * s:.3f})' for x in reversed(xs))
        parts.append(rf"\draw[thick, fill=gray!12] plot[smooth, tension=0.4] coordinates {{{deck}}} -- plot[smooth, tension=0.4] coordinates {{{keel}}} -- cycle;")
        parts.append(rf"\node[font=\footnotesize] at ({((a + b) / 2 + off) * s:.3f},{(zat((a + b) / 2, 1) - 14) * s:.3f}) {{Segment {i + 1}}};")
        if i:
            xj = a + off
            parts.append(rf"\draw[very thick, blue!70] ({xj * s:.3f},{zat(a, 1) * s:.3f}) -- ({xj * s:.3f},{zat(a, 2) * s:.3f});")
            parts.append(rf"\draw[very thick, blue!70] ({(xj - gap) * s:.3f},{zat(a, 1) * s:.3f}) -- ({(xj - gap) * s:.3f},{zat(a, 2) * s:.3f});")
    parts.append(rf"\node[font=\footnotesize, blue!70, align=center] at ({(200 + gap / 2) * s:.3f},{(ST[2][3] + 18) * s:.3f}) {{half bulkheads:\\ faces meet flat}};")
    parts.append(rf"\node[font=\footnotesize, anchor=east] at ({-2 * s:.3f},{10 * s:.3f}) {{transom}};")
    parts.append(rf"\node[font=\footnotesize, anchor=west] at ({(cuts[-1] + 2 * gap + 4) * s:.3f},{ST[-1][3] * s:.3f}) {{bow}};")
    return fig(r"\begin{tikzpicture}" + '\n'.join(parts) + r"\end{tikzpicture}",
               "Each hull prints as three sealed segments. Sand the joint faces flat, then epoxy them face to face against a straight edge.")


def frame():
    """Top view of the two hulls and beams: square the frame by equal diagonals."""
    s = 0.019
    hy = M['HULL_Y']
    out = []
    for side in (1, -1):
        up = ' -- '.join(f'({x * s:.3f},{(side * hy + hw) * s:.3f})' for x, hw, _, _ in ST)
        lo = ' -- '.join(f'({x * s:.3f},{(side * hy - hw) * s:.3f})' for x, hw, _, _ in reversed(ST))
        out.append(rf"\draw[thick, fill=gray!12] {up} -- {lo} -- cycle;")
        out.append(rf"\draw[dashed, gray] ({-10 * s:.3f},{side * hy * s:.3f}) -- ({(ST[-1][0] + 10) * s:.3f},{side * hy * s:.3f});")
    for bx in M['BEAMS']:
        out.append(rf"\draw[line width=2.2pt] ({bx * s:.3f},{-180 * s:.3f}) -- ({bx * s:.3f},{180 * s:.3f});")
    b0, b1 = sorted(M['BEAMS'])
    out.append(rf"\draw[red!70!black, thick, <->] ({b0 * s:.3f},{-180 * s:.3f}) -- ({b1 * s:.3f},{180 * s:.3f});")
    out.append(rf"\draw[red!70!black, thick, <->] ({b0 * s:.3f},{180 * s:.3f}) -- ({b1 * s:.3f},{-180 * s:.3f});")
    out.append(rf"\node[red!70!black, font=\footnotesize, fill=white, inner sep=1pt] at ({(b0 + b1) / 2 * s:.3f},{40 * s:.3f}) {{diagonals equal within 1\,mm}};")
    out.append(rf"\draw[<->] ({(ST[-1][0] + 25) * s:.3f},{-hy * s:.3f}) -- node[right, font=\footnotesize, align=left] {{{f0(2 * hy)}\,mm\\between hull\\centre lines}} ({(ST[-1][0] + 25) * s:.3f},{hy * s:.3f});")
    for bx, name in zip(M['BEAMS'], ('front beam', 'rear beam')):
        out.append(rf"\node[font=\footnotesize, above] at ({bx * s:.3f},{(hy + 32) * s:.3f}) {{{name}, 360\,mm}};")
    out.append(rf"\node[font=\footnotesize, anchor=east] at ({-12 * s:.3f},0) {{transoms}};")
    return fig(r"\begin{tikzpicture}" + '\n'.join(out) + r"\end{tikzpicture}",
               "Squaring the frame (top view, bows to the right). With the second hull on the beams, shift it until the two diagonals match.")


def steering():
    """Top view of the stern, as a schematic: fore-and-aft to scale (2.2:1 of the drawing), the hull spacing compressed."""
    sx = 0.06                                  # cm per mm, fore and aft
    Y = 2.6                                    # cm, drawn hull centre line (the real spacing is 340 mm)
    sy = 0.06                                  # cm per mm for small offsets near a hull or the centre line
    tx, c, le = M['TIE_X'], M['RUDDER']['chord'], M['RUDDER']['le']
    bx0 = M['BOX']['c0'] - M['BOX']['r']
    out = []
    for side in (1, -1):
        yc = side * Y
        out.append(rf"\fill[gray!12] (0,{yc - 0.7:.3f}) rectangle ({60 * sx:.3f},{yc + 0.7:.3f});")
        out.append(rf"\draw[thick] (0,{yc - 0.7:.3f}) -- (0,{yc + 0.7:.3f});")
        out.append(rf"\fill[black!60] ({(le - c) * sx:.3f},{yc - 1.5 * sy:.3f}) rectangle ({le * sx:.3f},{yc + 1.5 * sy:.3f});")
        out.append(rf"\fill ({STOCK_X * sx:.3f},{yc:.3f}) circle (2.4pt);")
        out.append(rf"\draw[very thick, blue!70] ({STOCK_X * sx:.3f},{yc:.3f}) -- ({tx * sx:.3f},{yc:.3f});")
        out.append(rf"\fill[blue!70] ({tx * sx:.3f},{yc:.3f}) circle (1.6pt);")
    out.append(rf"\draw[very thick, blue!70] ({tx * sx:.3f},{-Y:.3f}) -- ({tx * sx:.3f},{Y:.3f});")
    out.append(rf"\draw[thick, rounded corners=4pt, fill=gray!8] ({bx0 * sx:.3f},-1.3) rectangle ({(bx0 + 75) * sx:.3f},1.3);")
    out.append(rf"\draw[fill=gray!40] ({(RUDDER_SERVO_X - 11.4) * sx:.3f},{-6 * sy:.3f}) rectangle ({(RUDDER_SERVO_X + 11.4) * sx:.3f},{6 * sy:.3f});")
    out.append(rf"\draw[thick] ({RUDDER_SERVO_X * sx:.3f},0) -- ({RUDDER_SERVO_X * sx:.3f},{10 * sy:.3f});")
    out.append(rf"\fill ({RUDDER_SERVO_X * sx:.3f},{10 * sy:.3f}) circle (1.4pt);")
    out.append(rf"\draw[thick, red!70!black] ({RUDDER_SERVO_X * sx:.3f},{10 * sy:.3f}) -- ({tx * sx:.3f},0);")
    out.append(rf"\draw[<->] ({STOCK_X * sx:.3f},{Y + 0.9:.3f}) -- node[above, font=\footnotesize] {{{tx - STOCK_X:.2f}\,mm}} ({tx * sx:.3f},{Y + 0.9:.3f});")
    out.append(rf"\draw[<->] ({(RUDDER_SERVO_X + 14) * sx:.3f},0) -- node[right, font=\footnotesize] {{10\,mm}} ({(RUDDER_SERVO_X + 14) * sx:.3f},{10 * sy:.3f});")
    lab = lambda x, y, t, a='west', col='black': rf"\node[font=\footnotesize, anchor={a}, align=left, {col}] at ({x:.3f},{y:.3f}) {{{t}}};"
    out += [lab((le - c - 2) * sx, Y, r'rudder blade, %s\,mm chord;\\stock (0.125\,in wire)\\at 25\,\%% of the chord' % f0(c), 'east'),
            lab((le - c - 2) * sx, -Y, r'tiller arm (0.093\,in wire)\\from the stock to the tie bar', 'east', 'blue!70'),
            lab((tx + 2) * sx, -Y + 0.9, r'tie bar (0.093\,in wire)', 'west', 'blue!70'),
            lab(((RUDDER_SERVO_X + tx) / 2 - 10) * sx, 1.0, r'pushrod (0.047\,in wire)', 'south', 'red!70!black'),
            lab((bx0 + 3) * sx, -0.75, r'electronics box:\\rudder servo (MG90S)', 'west'),
            lab((tx + 3) * sx, Y - 0.95, 'transom', 'west')]
    return fig(r"\begin{tikzpicture}" + '\n'.join(out) + r"\end{tikzpicture}",
               "Steering linkage (top view, bows to the right; fore and aft to scale, the hulls drawn closer together than the real 340\\,mm). "
               "Both tiller arms are the same length and the tie bar keeps the rudders parallel.")


def wiring():
    box = lambda x, y, w, h, t, col='gray!10': rf"\node[draw, thick, fill={col}, minimum width={w}cm, minimum height={h}cm, align=center, font=\footnotesize] at ({x},{y}) {{{t}}};"
    out = [box(0, 0, 3.0, 2.6, r'\textbf{Receiver}\\FS-iA6B', 'blue!8'),
           box(-5.7, 0.9, 4.0, 0.9, r'rudder servo (MG90S)'),
           box(-5.7, -0.9, 4.0, 0.9, r'sail winch (JX W4505-2T)'),
           box(6.3, 0, 3.8, 1.4, r'4 x eneloop AA\\in the holder with switch'),
           r"\draw[thick, ->] (-1.5,0.9) -- node[above, font=\footnotesize] {CH1} (-3.7,0.9);",
           r"\draw[thick, ->] (-1.5,-0.9) -- node[above, font=\footnotesize] {CH3} (-3.7,-0.9);",
           r"\draw[thick, ->] (4.4,0) -- node[above, font=\footnotesize, align=center] {any spare\\channel (CH6)} (1.5,0);",
           r"\node[font=\footnotesize, align=center] at (-5.7,2.1) {right stick, left--right:\\self-centring};",
           r"\node[font=\footnotesize, align=center] at (-5.7,-2.1) {left stick, up--down:\\stays where you leave it};"]
    return fig(r"\begin{tikzpicture}" + '\n'.join(out) + r"\end{tikzpicture}",
               "Receiver wiring. The battery powers the receiver through any free channel; both servos then take their power from the receiver.")


def rig():
    """Side view of the rig with every stay length, from the rig model (mini profile)."""
    s = 0.0105
    tx, tz = R['tack']
    bx, by, bz = R['bow']
    cx, cy, cz = R['chainplate']
    mx, z0, zt, zh = R['mast_x'], R['mast_z0'], R['mast_top'], R['hounds_z']
    deck = ' -- '.join(f'({x * s:.3f},{zd * s:.3f})' for x, _, _, zd in ST)
    keel = ' -- '.join(f'({x * s:.3f},{zk * s:.3f})' for x, _, zk, _ in reversed(ST))
    rows = D['main_table']
    luff_x = mx - R['mast_r']
    main = ' -- '.join(f'({(luff_x - c) * s:.3f},{(R["z_foot"] + h) * s:.3f})' for h, c in rows)
    jx = lambda z: rm.jib_luff_x(z)
    jtop = R['jib_head_z']
    out = [rf"\draw[thick, fill=gray!12] {deck} -- {keel} -- cycle;",
           rf"\fill[gray!35] ({(M['BOX']['c0'] - M['BOX']['r']) * s:.3f},{M['BOX']['z0'] * s:.3f}) rectangle ({(M['BOX']['c1'] + M['BOX']['r']) * s:.3f},{M['BOX']['z1'] * s:.3f});",
           rf"\draw[fill=blue!8] ({luff_x * s:.3f},{R['z_foot'] * s:.3f}) -- {main} -- ({luff_x * s:.3f},{R['z_head'] * s:.3f}) -- cycle;",
           rf"\draw[fill=red!8] ({jx(R['jib_z0']) * s:.3f},{R['jib_z0'] * s:.3f}) -- ({(jx(R['jib_z0']) - R['jib_c0']) * s:.3f},{R['jib_z0'] * s:.3f}) -- ({(jx(jtop) - R['jib_ch']) * s:.3f},{jtop * s:.3f}) -- ({jx(jtop) * s:.3f},{jtop * s:.3f}) -- cycle;",
           rf"\draw[line width=1.6pt] ({mx * s:.3f},{z0 * s:.3f}) -- ({mx * s:.3f},{zt * s:.3f});",
           rf"\draw[line width=1.2pt] ({luff_x * s:.3f},{R['boom_z'] * s:.3f}) -- ({(luff_x - RIG['boom_length_mm']) * s:.3f},{R['boom_z'] * s:.3f});",
           rf"\draw[red!70!black, thick] ({tx * s:.3f},{tz * s:.3f}) -- ({mx * s:.3f},{zh * s:.3f});",
           rf"\draw[red!70!black, thick, dashed] ({tx * s:.3f},{tz * s:.3f}) -- ({bx * s:.3f},{bz * s:.3f});",
           rf"\draw[orange!80!black, thick] ({mx * s:.3f},{zh * s:.3f}) -- ({cx * s:.3f},{cz * s:.3f});",
           rf"\fill ({mx * s:.3f},{zh * s:.3f}) circle (1.6pt);"]
    lab = lambda x, y, tgt, t: (rf"\draw[gray] ({x * s:.3f},{y * s:.3f}) -- ({tgt[0] * s:.3f},{tgt[1] * s:.3f});"
                                rf"\node[anchor=west, font=\footnotesize, align=left] at ({x * s:.3f},{y * s:.3f}) {{{t}}};")
    X = 640
    out += [lab(X, zt, (mx, zt), f"mast: {f0(RIG['mast_length_mm'])}\\,mm of 6\\,mm tube, top plugged"),
            lab(X, zh + 25, (mx, zh), f"hounds: line binding {f0(RIG['hounds_above_mast_foot_mm'])}\\,mm\\\\above the mast foot"),
            lab(X, 470, ((tx + mx) / 2, (tz + zh) / 2), f"forestay {f0(RIG['forestay_mm'])}\\,mm (jib sleeved on it)"),
            lab(X, 320, (mx + 1, (zh + cz) / 2), f"shrouds {f0(RIG['shroud_mm'])}\\,mm each,\\\\hounds to the chainplate eyes"),
            lab(X, 170, ((tx + bx) / 2, (tz + bz) / 2), f"bridle legs {f0(RIG['bridle_leg_mm'])}\\,mm each,\\\\bridle point to the bow loops")]
    out.append(rf"\node[anchor=south east, font=\footnotesize] at ({(luff_x - RIG['boom_length_mm'] - 4) * s:.3f},{R['boom_z'] * s:.3f}) {{boom {f0(RIG['boom_length_mm'])}\,mm}};")
    out.append(rf"\node[anchor=east, font=\footnotesize] at ({(M['BOX']['c0'] - M['BOX']['r'] - 4) * s:.3f},{(M['BOX']['z0'] + M['BOX']['z1']) / 2 * s:.3f}) {{electronics box}};")
    return fig(r"\begin{tikzpicture}" + '\n'.join(out) + r"\end{tikzpicture}",
               "Rig from the side (bow to the right): stay lengths between the knots. The shrouds run down to both sides; only the near one is drawn.")


def mainsail():
    """Flat mainsail with the batten positions and the luff sleeve allowance."""
    s = 0.0105
    rows = D['main_table']
    sleeve = 25.0
    outline = ' -- '.join(f'({c * s:.3f},{h * s:.3f})' for h, c in rows)
    out = [rf"\fill[blue!20] ({-sleeve * s:.3f},0) rectangle (0,{rows[-1][0] * s:.3f});",
           rf"\draw[thick, fill=blue!5] (0,0) -- {outline} -- (0,{rows[-1][0] * s:.3f}) -- cycle;",
           rf"\draw[thick] ({-sleeve * s:.3f},0) rectangle (0,{rows[-1][0] * s:.3f});",
           rf"\node[font=\footnotesize, anchor=east, align=right] at ({(-sleeve - 4) * s:.3f},{rows[-1][0] / 2 * s:.3f}) {{{f0(sleeve)}\,mm luff\\allowance: fold\\into the mast\\sleeve}};"]
    for h, L in zip(D['battens_height_mm'], D['battens_length_mm']):
        out.append(rf"\draw[line width=1.4pt, blue!70!black] ({4 * s:.3f},{h * s:.3f}) -- ({(4 + L) * s:.3f},{h * s:.3f}) node[right, font=\footnotesize, black] {{{f0(L)}\,mm at {f0(h)}\,mm}};")
    out.append(rf"\node[font=\footnotesize, below] at ({rows[0][1] / 2 * s:.3f},0) {{foot {f0(rows[0][1])}\,mm}};")
    out.append(rf"\node[font=\footnotesize, above] at ({rows[-1][1] / 2 * s:.3f},{rows[-1][0] * s:.3f}) {{head {f0(rows[-1][1])}\,mm}};")
    return fig(r"\begin{tikzpicture}" + '\n'.join(out) + r"\end{tikzpicture}",
               "Mainsail laid flat: batten lengths and their heights above the foot. The 1:1 pattern has the full outline.")


def sheets():
    """Side schematic of the two sheets from the stepped drum through the lid fairleads."""
    s = 0.02
    bx0, bx1 = M['BOX']['c0'] - M['BOX']['r'], M['BOX']['c1'] + M['BOX']['r']
    zb, zl = M['BOX']['z0'], M['BOX']['z1']
    mf, jf = RIG['main_fairlead_x_mm'], RIG['jib_fairlead_x_mm']
    out = [rf"\draw[thick, fill=gray!8] ({bx0 * s:.3f},{zb * s:.3f}) rectangle ({bx1 * s:.3f},{zl * s:.3f});",
           rf"\node[font=\footnotesize, anchor=north] at ({(bx0 + bx1) / 2 * s:.3f},{zb * s:.3f}) {{electronics box (side view, bow to the right)}};",
           rf"\draw[fill=gray!40] ({(WINCH_X - 20) * s:.3f},{(zb + 4) * s:.3f}) rectangle ({(WINCH_X + 20) * s:.3f},{(zl - 14) * s:.3f});",
           rf"\draw[fill=orange!30] ({(WINCH_X - DRUM['main_groove_dia_mm'] / 2) * s:.3f},{(zl - 14) * s:.3f}) rectangle ({(WINCH_X + DRUM['main_groove_dia_mm'] / 2) * s:.3f},{(zl - 9) * s:.3f});",
           rf"\draw[fill=orange!50] ({(WINCH_X - DRUM['jib_groove_dia_mm'] / 2) * s:.3f},{(zl - 9) * s:.3f}) rectangle ({(WINCH_X + DRUM['jib_groove_dia_mm'] / 2) * s:.3f},{(zl - 4) * s:.3f});",
           rf"\draw[blue!70!black, thick] ({(WINCH_X - DRUM['main_groove_dia_mm'] / 2) * s:.3f},{(zl - 11.5) * s:.3f}) -- ({mf * s:.3f},{zl * s:.3f}) -- ({mf * s:.3f},{(zl + 60) * s:.3f}) node[above, font=\footnotesize, align=center] {{to the boom end}};",
           rf"\draw[red!70!black, thick] ({(WINCH_X + DRUM['jib_groove_dia_mm'] / 2) * s:.3f},{(zl - 6.5) * s:.3f}) -- ({jf * s:.3f},{zl * s:.3f}) -- ({(jf + 30) * s:.3f},{(zl + 60) * s:.3f}) node[above, font=\footnotesize, align=center] {{to the jib clew}};",
           rf"\fill ({mf * s:.3f},{zl * s:.3f}) circle (1.6pt) node[above left, font=\footnotesize] {{fairlead {f0(mf)}\,mm}};",
           rf"\fill ({jf * s:.3f},{zl * s:.3f}) circle (1.6pt) node[above left, font=\footnotesize] {{fairlead {f0(jf)}\,mm}};",
           rf"\node[font=\footnotesize, align=left, anchor=west] at ({(bx1 + 14) * s:.3f},{(zb + 10) * s:.3f}) {{stepped drum on the winch:\\{DRUM['main_groove_dia_mm']:.0f}\,mm groove: mainsheet, pays out {f0(DRUM['main_travel_mm'])}\,mm\\{DRUM['jib_groove_dia_mm']:.1f}\,mm groove: jib sheet, pays out {f0(DRUM['jib_travel_mm'])}\,mm\\both in {DRUM['main_turns']:.2f} turns; wind both the same way}};"]
    return fig(r"\begin{tikzpicture}" + '\n'.join(out) + r"\end{tikzpicture}",
               "Both sheets on the one drum. Fairlead distances are measured from the transoms.")


if __name__ == '__main__':
    for f in (hulls, frame, steering, wiring, rig, mainsail, sheets):
        print(f.__name__, len(f()))
