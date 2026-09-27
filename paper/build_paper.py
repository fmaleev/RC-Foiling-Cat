"""Generates the technical paper (LaTeX) from the analysis outputs. Compile with tectonic."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'fusion_addin', 'SailTrim'))
import vpp
import fittings_geom as fg

CAD = json.load(open(os.path.join(ROOT, 'analysis', 'cad_data.json')))
RES = json.load(open(os.path.join(ROOT, 'analysis', 'vpp_results.json')))
CTL = json.load(open(os.path.join(ROOT, 'analysis', 'control_results.json')))
SEN = json.load(open(os.path.join(ROOT, 'analysis', 'sensitivity_results.json')))
MINI = json.load(open(os.path.join(ROOT, 'mini', 'mini_results.json')))
MINICAD = json.load(open(os.path.join(ROOT, 'mini', 'cad_data_mini.json')))
RH = json.load(open(os.path.join(ROOT, 'analysis', 'ride_height_results.json')))
DC = json.load(open(os.path.join(ROOT, 'analysis', 'design_checks.json')))
OPT = json.load(open(os.path.join(ROOT, 'sim', 'optimization_results.json')))
FC = json.load(open(os.path.join(ROOT, 'analysis', 'foil_checks.json')))
FCR = {r['rule']: r['value'] for r in FC['rules']}
PHR = json.load(open(os.path.join(ROOT, 'analysis', 'pitch_heave_results.json')))
TS = json.load(open(os.path.join(ROOT, 'analysis', 'takeoff_sim_results.json')))
RO = json.load(open(os.path.join(ROOT, 'sim', 'roll_options.json')))
STR = json.load(open(os.path.join(ROOT, 'analysis', 'structure_results.json')))
PL1 = json.load(open(os.path.join(ROOT, 'manual_1m', 'print_list_1m.json')))
MD1 = json.load(open(os.path.join(ROOT, 'manual_1m', 'manual_data_1m.json')))
D, F = CAD['displacement'], CAD['foiling']
CADM = sum(PL1[k]['cm3'] * PL1[k]['qty'] for k in ('Mast Fairing Lower 1', 'Mast Fairing Upper 1', 'Gooseneck', 'Boom Jaw')) * 1.27   # g, PETG
TIEBAR = [m for c, n, m in F['items'] if n == 'Tie Bar'][0]
import structure
with open(os.path.join(HERE, 'data', 'ride_height.dat'), 'w') as f:
    f.write('V pitch flap dh wn zeta\n')
    for r in RH['rows']:
        f.write(f"{r['V']} {r['pitch_deg']} {r['flap_deg']} {r['ride_height_shift_mm']} {r['wn_hz']} {r['zeta']}\n")
RHr = RH['rows']


def thin(src, dst, dx=0.03, dy=0.01):
    """One point per (tws90, v12) bin, so the design clouds stay within TeX's memory."""
    rows = [l.split() for l in open(os.path.join(HERE, 'data', src)).read().split('\n')[1:] if l.strip()]
    seen, out = set(), []
    for r in rows:
        k = (round(float(r[0]) / dx), round(float(r[1]) / dy))
        if k not in seen:
            seen.add(k); out.append(r[:2])
    open(os.path.join(HERE, 'data', dst), 'w').write('tws90 v12\n' + ''.join(f'{a} {b}\n' for a, b in out))


thin('opt_cloud.dat', 'opt_cloud_thin.dat'); thin('opt_cloud_robust.dat', 'opt_cloud_robust_thin.dat')

vpp.configure()


def statics(cfg):
    b = vpp.Boat(cfg, CAD)
    zw = b.zw0
    num = den = 0.0
    for i in range(400):
        x = (i + .5) / 400; a = vpp.sub_area(x, zw); num += a * x; den += a
    vol = vpp.integrate(lambda x: math.pi * vpp.section(x)[0] * vpp.section(x)[2], 0, 1, 400)
    return dict(M=b.M * 1000, zw=zw * 1000, draft=(zw + 0.045) * 1000, fb=(0.064 - zw) * 1000, lcb=num / den * 1000, lcg=b.lcg,
                res=vol * 1000 / b.M, RM=b.RM, h=b.heel_arm(False), hf=b.heel_arm(True), vto=b.takeoff_speed(), b=b)


SD, SF = statics('displacement'), statics('foiling')
bf = SF['b']


# foil structure (CAD foils from vpp: wing at z=-220, strut free length from hull bottom -45 to -220)
def section_props(code, chord, n=80):
    pts = [(chord * s, chord * t) for s, t in vpp.naca(code, n)]
    A = Cy = Ixx = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        cr = x0 * y1 - x1 * y0; A += cr; Cy += (y0 + y1) * cr; Ixx += (y0 * y0 + y0 * y1 + y1 * y1) * cr
    A /= 2; Cy /= (6 * A); Ixx /= 12
    return abs(Ixx) - abs(A) * Cy * Cy, max(abs(y - Cy) for _, y in pts)


WC, WS, SC = vpp.WING_C * 1000, vpp.WING_SPAN * 1000, vpp.STRUT_C * 1000
I_w, c_w = section_props('4412', WC)
I_s, _ = section_props('0012', SC)
L_main = FC['largest_flight_loads_N']['main']      # largest main-foil load in the flying range (elevators pushing down)
Lcase = 2 * L_main
Mroot = Lcase * WS / 2
q = Lcase / WS
strut_len = 220.0 - 45.0
STRUCT = {name: (Mroot * c_w / I_w, q * WS ** 4 / (8 * E * I_w), math.degrees(Mroot * strut_len / (E * I_s)))
          for name, E in (('CFRP ($E$ = 70 GPa)', 70000.0), ('Printed PETG ($E$ = 2 GPa)', 2000.0))}


def cap_props(code, chord, width=25.0, t=4 * 0.127, n=200):
    """UD carbon caps of the given width on both faces, centred on the thickest point and following the surfaces (core ignored)."""
    pts = [(chord * u, chord * v) for u, v in vpp.naca(code, 200)]
    half = len(pts) // 2
    def surf(ps, x):
        ps = sorted(ps)
        for (xa, ya), (xb, yb) in zip(ps, ps[1:]):
            if xa <= x <= xb:
                return ya + (yb - ya) * (x - xa) / (xb - xa) if xb > xa else ya
    up, lo = pts[:half], pts[half:]
    xm = max((chord * i / 400 for i in range(1, 400)), key=lambda x: surf(up, x) - surf(lo, x))
    x0 = max(0.5, xm - width / 2); x1 = min(chord - 0.5, x0 + width); dw = (x1 - x0) / n
    strips = [y for i in range(n) for y in (surf(up, x0 + (i + .5) * dw) - t / 2, surf(lo, x0 + (i + .5) * dw) + t / 2)]
    ybar = sum(strips) / len(strips)
    return sum(dw * t * (y - ybar) ** 2 for y in strips), max(abs(y - ybar) for y in strips) + t / 2


E_CAP = 120000.0                                            # MPa, UD cap laminate (assumed)
I_cap, y_cap = cap_props('4412', WC)
CAP_RATIO = E_CAP * I_cap / (70000.0 * I_w)
CAP_TIP = STRUCT['CFRP ($E$ = 70 GPa)'][1] / CAP_RATIO
CAP_STRESS = Mroot * y_cap / I_cap


def vrow(cfg, twa, tws):
    r = [x for x in RES['vpp'][cfg][str(twa)] if x['tws_kn'] == tws][0]
    return f"{r['V']:.2f}" + (r'\,F' if r.get('mode') == 'foiling' else '') + ('*' if r.get('depowered') else '')


vpp_tab = '\n'.join(f"{t} & {vrow('displacement', 60, t)} & {vrow('displacement', 90, t)} & {vrow('foiling', 60, t)} & {vrow('foiling', 90, t)} \\\\"
                    for t in (4, 6, 7, 8, 10, 12))
kn16 = lambda v: '$>$16' if v is None else f'{v:g}'    # sensitivity.py scans take-off wind up to 16 kn
sens_tab = '\n'.join(f"{s['scenario'].replace('%', r'\%')} & {s['takeoff_speed_ms']:.2f} & {kn16(s['TWA60_takeoff_tws_kn'])} & {kn16(s['TWA90_takeoff_tws_kn'])} \\\\" for s in SEN)
rud_disp = max(CTL['displacement'], key=lambda x: x['rudder_angle_deg'])
rud_foil = max((x for x in CTL['foiling'] if x['mode'] == 'foiling'), key=lambda x: x['rudder_angle_deg'])
pitch = CTL['foil_pitch']
heave = CTL['foil_heave']
MS = MINI['statics']
wig = json.load(open(os.path.join(ROOT, 'analysis', 'vpp_results.json')))['wigley_michell_Cw_x1e3']
bd = CAD['displacement']['by_component_g']
import csv
def bom_total(name):
    return sum(float(x['total_usd']) for x in csv.DictReader(open(os.path.join(ROOT, 'bom', name + '.csv'))))
MINI_COST, FULL_COST, FOIL_COST = bom_total('bom_mini'), bom_total('bom_full_build_first'), bom_total('bom_foiling_kit_v2')
tws_all = [s_[k] for s_ in SEN for k in ('TWA60_takeoff_tws_kn', 'TWA90_takeoff_tws_kn') if s_[k]]
TO_MIN, TO_MAX = min(tws_all), max(tws_all)
TOW = json.load(open(os.path.join(ROOT, 'analysis', 'takeoff_wind.json')))      # VPP bisection to 0.02 kn (analysis/takeoff_wind.py)
TO_BASE = round(TOW['90'], 1)
WAVE_MAX = max(r.get('wave', 0.0) for r in RES['resistance']['displacement'] if r['V'] <= 3.0)
def vpp_v(cfg, twa, tws):
    return [x for x in RES['vpp'][cfg][str(twa)] if x['tws_kn'] == tws][0]['V']
SLOW = [1 - vpp_v('foiling', 90, t) / vpp_v('displacement', 90, t) for t in (4, 6)]
def dep_onset(cfg, twa):
    return next((x['tws_kn'] for x in RES['vpp'][cfg][str(twa)] if x.get('depowered')), None)
DEP = [d for d in (dep_onset('displacement', 60), dep_onset('displacement', 90)) if d]
DEP_LO, DEP_HI = min(DEP), max(DEP)
FOILKIT_G = CAD['foiling']['by_component_g'].get('Foiling Kit', 0)
SERVO_MAX = max(x['servo_torque_kgcm'] for x in CTL['displacement'])
MD = json.load(open(os.path.join(ROOT, 'mini', 'manual', 'manual_data.json')))
MINI_V8 = [x for x in MINI['vpp']['90'] if x['tws_kn'] == 8][0]['V']
MINI_RUD = max(x['rudder_angle_deg'] for x in MINI['rudder'])
ST = json.load(open(os.path.join(ROOT, 'analysis', 'stability_results.json')))
PP = json.load(open(os.path.join(ROOT, 'analysis', 'pitchpole_results.json')))
HV = json.load(open(os.path.join(ROOT, 'analysis', 'hull_variants_results.json')))

tex = r"""\documentclass[10pt,twocolumn]{article}
\usepackage[letterpaper,margin=0.75in]{geometry}
\usepackage{amsmath,graphicx,booktabs,xcolor,pgfplots,caption,siunitx}
\usepackage[hidelinks]{hyperref}
\pgfplotsset{compat=1.17, every axis/.style={width=0.9\columnwidth, height=0.6\columnwidth, grid=major, grid style={gray!25},
  tick label style={font=\scriptsize}, label style={font=\small}, legend style={font=\scriptsize, draw=none, fill=white, fill opacity=0.8, text opacity=1}}}
\captionsetup{font=small}
\raggedbottom
\sisetup{detect-all}
\title{\textbf{Design and Analysis of a 1\,m RC Beach Catamaran\\ with a Hydrofoil Option}}
\author{Filip Maleev\\ \small Colorado College, Department of Mathematics and Computer Science}
\date{September 2026}
\begin{document}
\maketitle

\begin{abstract}
This paper describes the design of a 1\,m radio-controlled catamaran with a beach-cat rig, two appendage configurations (daggerboards, or L-foils with T-foil rudder elevators), and a simplified 0.6\,m version intended as a first build. The hulls are 3D-printed PETG shells with bonded bulkheads, so every printed segment is a sealed compartment. The rig follows full-size beach cats: a square-top, fully battened main on a rotating wing mast, and a jib on a forestay bridle. It is modelled parametrically in Autodesk Fusion, and a custom add-in trims it with three sliders (jib sheet, main traveler, mainsheet tension). Performance is estimated with a purpose-written velocity prediction program. It combines ITTC-57 friction, Michell thin-ship wave resistance with catamaran interference (validated on the Wigley hull), appendage and foil drag, and a depowering sail model. The displacement version reaches """ + f"{float(vrow('displacement', 90, 8).split(chr(92))[0].rstrip('*')):.1f}" + r"""\,m/s on a beam reach in 8\,kn of wind. Its rudders need at most """ + f"{rud_disp['rudder_angle_deg']:.1f}" + r"""$^\circ$ of an available $\pm$""" + f"{CTL['rudder_throw_deg']:.0f}" + r"""$^\circ$. The foiling version reaches its """ + f"{SF['vto']:.2f}" + r"""\,m/s take-off speed from about """ + f"{TO_BASE:g}" + r"""\,kn of true wind, and a sensitivity study places take-off between """ + f"{TO_MIN:g}" + r""" and """ + f"{TO_MAX:g}" + r"""\,kn. A controllability analysis shows that the foiling version is pitch-stable but has no heave stability with fixed-incidence foils: at """ + f"{heave[-1]['V']:g}" + r"""\,m/s the foils lift """ + f"{heave[-1]['excess_pct']:.0f}" + r"""\,\% more than the boat's weight. It therefore needs ride-height control. A wand-driven trailing-edge flap is sized here: it makes heave stable and well damped ($\zeta=""" + f"{RHr[0]['zeta']:.1f}" + r"""$) while using at most """ + f"{max(abs(r['flap_deg']) for r in RHr):.1f}" + r"""$^\circ$ of flap from take-off to 5\,m/s. This result led to building the non-foiling version first, preceded by a costed 0.6\,m version (\$""" + f"{MINI_COST:.2f}" + r""" in parts). A flight simulator built on the same physics, extended with the boat's trim in heave and pitch, then searched """ + f"{OPT['grid_size']:,}".replace(",", "{,}") + r""" foil designs. At speed the sail drive's bow-down couple makes the elevators push down. With a fixed positive incidence they do so by pitching the boat nose-down until they leave the water, so neither the original foils nor a first optimized set would fly. The adopted v2.2 foils set the elevators at $""" + f"{OPT['adopted']['einc']:+g}" + r"""^\circ$ and """ + f"{-197 - OPT['adopted']['zel']:.0f}" + r"""\,mm lower, and reach """ + f"{vpp_v('foiling', 90, 12):.2f}" + r"""\,m/s on a beam reach in 12\,kn of wind with the boat level.
\end{abstract}

\section{Introduction}
Beach catamarans such as the Hobie~16 and the Olympic Nacra~17 combine two slender hulls, a large, fully battened rig and, on the Nacra~17, foils that lift the boat clear of the water. The goal of this project was a radio-controlled model that is faithful to that type, can be built with a desktop 3D printer and off-the-shelf RC parts, and whose behaviour can be predicted before it is built. Three questions shaped the work: (i) how closely can a 1\,m model follow full-scale rig proportions; (ii) will the foiling version actually take off before it has to be depowered; (iii) will the boat be controllable. The answers set the build order: a 0.6\,m simplified version first, then the 1\,m displacement version, with foiling deferred until ride-height control is designed.

\begin{figure}[t]
\centering
\includegraphics[width=0.49\columnwidth]{../images/build_first_v1.4.png}\hfill
\includegraphics[width=0.49\columnwidth]{../images/foiling_v2.2.png}
\caption{The 1\,m design in Autodesk Fusion: build-first version with daggerboards (left) and foiling version with the v2.2 L-foils and T-foil rudders (right).}
\label{fig:renders}
\end{figure}

\section{Design}
\subsection{Hulls and structure}
Each hull is lofted through eight elliptical stations (Fig.~\ref{fig:plans}, right). It is 1000\,mm long, at most 80\,mm wide and 108\,mm deep, and the hull centres are 560\,mm apart. The printed hull is a 0.8\,mm PETG shell. Before shelling, 2\,mm slabs are cut from the solid loft at each print joint and bonded back in as bulkheads, so each 200\,mm segment prints as its own sealed compartment. Enclosed crossbeam sockets, foil trunks and chainplate bosses are part of the shell. The analytic hull volume from the station table matches the CAD loft to within """ + f"{abs(RES['hull_volume_check']['error_pct']):.2f}" + r"""\,\%.

\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{axis}[name=ga, width=0.66\textwidth, height=0.62\textwidth, axis equal image, xlabel={$x$ from transom (mm)}, ylabel={$z$ (mm)}, grid=none,
  xmin=-80, xmax=1050, ymin=-280, ymax=1420, title={\small general arrangement (build-first)}]
\addplot[thick, fill=gray!15] table[x=x, y=z] {data/profile_hull.dat};
\addplot[thick, fill=blue!12] table[x=x, y=z] {data/sail_main.dat};
\addplot[thick, fill=red!12] table[x=x, y=z] {data/sail_jib.dat};
\addplot[thick, fill=black!60] table[x=x, y=z] {data/profile_board.dat};
\addplot[thick, fill=black!60] table[x=x, y=z] {data/profile_rudder.dat};
\addplot[thick, fill=blue!30] table[x=x, y=z] {data/profile_pod.dat};
\addplot[thick, fill=blue!30, unbounded coords=jump] table[x=x, y=z] {data/profile_tail.dat};
\addplot[thick, fill=gray!50] table[x=x, y=z] {data/profile_cover.dat};
\addplot[thick, fill=black, unbounded coords=jump] table[x=x, y=z] {data/profile_beams.dat};
\addplot[thin] coordinates {(259,128) (180,77)};
\addplot[very thick] coordinates {(620,72) (620,1370)};
\addplot[thick] coordinates {(603,132) (258,132)};
\addplot[thin] coordinates {(818,150) (620,1000)};
\addplot[dashed, blue] coordinates {(-80,0) (1050,0)};
\end{axis}
\begin{axis}[at={(ga.east)}, anchor=west, xshift=12mm, width=0.3\textwidth, height=0.36\textwidth, axis equal image, xlabel={$y$ (mm)}, ylabel={$z$ (mm)},
  title={\small body plan}, unbounded coords=jump, grid=none, xmin=-48, xmax=48]
\addplot[thick, blue] table[x=y, y=z] {data/bodyplan.dat};
\addplot[dashed, gray] coordinates {(-48,0) (48,0)};
\addplot[thin] coordinates {(0,-50) (0,75)};
\end{axis}
\end{tikzpicture}
\caption{Left: general arrangement of the 1\,m build-first boat (hull, the three crossbeams, pod, rudder-servo bracket and cover on the rear beam, daggerboard, rudder, rotating mast, boom and mainsheet to the traveler, square-top main and jib; dashed line: reference waterline). Right: body plan of the hull, eight elliptical stations (aft half on the left, forward half on the right).}
\label{fig:plans}
\end{figure*}

\subsection{Rig: following real beach cats}
Table~\ref{tab:rig} compares the rig with the Hobie~16 and Nacra~17 \cite{hobie,nacra}. The main-to-jib ratio (3.2) lies between the two, and the planform follows their square-top main with 8 full-length battens. The rest also comes from the full-size boats: a rotating wing mast (24\,x\,14\,mm fairing on a 12\,mm carbon tube), a forestay bridle to both bows, a traveler on the rear beam, and a jib car on a short track (on the pod lid here, because the pod sits over the front beam). All the fittings are printed: transom gudgeons, T-rail tracks with sliding cars, a hounds collar whose groove carries the loop the stays tie to (so the mast turns inside it), a mast cap that seals the tube, a bridle post and a gooseneck. The fairing is printed as """ + f"{fg.FAIR_WALL:.2f}" + r"""\,mm shells in seven pieces, and the main's luff is laced to its trailing edge. Sail area and mast height, however, cannot follow geometric scaling. For a scale factor $\lambda$, righting moment scales as $\lambda^4$ (weight $\lambda^3$ times beam $\lambda$). In the same wind, the heeling moment of a similar rig scales only as $\lambda^3$ (area $\lambda^2$ times height $\lambda$). A 1:5 model with full-scale proportions would therefore be over-canvassed, so sail area was set by the VPP instead (Section~\ref{sec:results}).

\begin{table}[t]
\centering\small
\caption{Rig proportions.}
\label{tab:rig}
\begin{tabular}{lccc}
\toprule
& Hobie 16 & Nacra 17 & This boat \\
\midrule
Mast height / LOA & 1.60 & 1.71 & 1.37 \\
Main : jib area & 2.7 & 3.7 & 3.2 \\
Sail area / LOA$^2$ & 0.74 & 0.68 & 0.40 \\
\bottomrule
\end{tabular}
\end{table}

The three real-cat controls map to three RC channels and to three sliders in a Fusion add-in written for this project. Jib sheet sets the jib angle. Main traveler sets the boom angle and moves the traveler car. Mainsheet tension sets the main's twist, from $30^\circ$ loose to $3^\circ$ hard, and its depth, from 13\,\% to 8\,\%. The sails and wing mast are loft and extrude features on batten-station sketches. The add-in moves the sketch points, so the parametric model re-solves; booms, sheets and cars are updated as base-feature bodies.

\subsection{Appendages and foils}
The rudders are balanced NACA\,0012 blades (45\,mm chord, pivot at 25\,\% chord) linked by a tie bar. The build-first version has NACA\,0012 daggerboards; the foiling version replaces them with L-foils: a NACA\,0012 strut (""" + f"{SC:.0f}" + r"""\,mm chord) and a NACA\,4412 wing (""" + f"{WC:.0f}" + r"""\,mm chord, """ + f"{WS:.0f}" + r"""\,mm span per side) at """ + f"{vpp.INC_MAIN_DEG:g}" + r"""$^\circ$ incidence. Rudder T-foil elevators (NACA\,0012, """ + f"{vpp.EL_C * 1000:.0f}" + r"""\,mm chord, """ + f"{vpp.EL_SPAN * 1000:.0f}" + r"""\,mm span) sit at $+""" + f"{vpp.INC_EL_DEG:g}" + r"""^\circ$. The foiling rudders are """ + f"{(vpp.Z_RUDDER - vpp.Z_EL + vpp.RUDDER_BELOW_EL) * 1000:.0f}" + r"""\,mm longer than the build-first ones, so the elevators sit at $z=""" + f"{vpp.Z_EL * 1000:.0f}" + r"""$\,mm. These are the v2.2 foils chosen with the flight simulator (Section~\ref{sec:opt}). They replace the original v2.0 set (wings 200\,x\,60\,mm at $2^\circ$, elevators 150\,x\,36\,mm at $3^\circ$) and a first optimized set (v2.1) that the trim model showed would not fly. Every result in this paper is for v2.2 unless stated otherwise. An early layout placed the main foils 100\,mm deeper than the elevators. Because the elevators would breach first, that extra depth added weight and drag but no ride height, so the wings were moved up to the elevator depth, saving 73\,g of carbon.

\section{Analysis methods}
\subsection{Mass properties and hydrostatics}
Masses come from the CAD volumes, with densities or manufacturer weights for bought parts; assumptions are listed in the project README. Displacement and the centre of buoyancy are integrated over the station table with a natural cubic spline, and the flooded foil trunks are subtracted.

\subsection{Resistance}
Hull friction uses the ITTC-57 line with a form factor $(1+k)=1.25$:
\begin{equation}
R_F=\tfrac12\rho V^2 S\,C_F(1+k),\qquad C_F=\frac{0.075}{(\log_{10}Re-2)^2}.
\end{equation}
Wave resistance uses Michell's thin-ship integral \cite{michell,tuck,shipd} for a hull with half-breadth $Y(x,z)$:
\begin{equation}
R_W=\frac{4\rho g^2}{\pi U^2}\int_1^\infty \big(I^2+J^2\big)\,\frac{\lambda^2\,F_c(\lambda)}{\sqrt{\lambda^2-1}}\,d\lambda,
\end{equation}
\begin{equation}
I+iJ=\iint \frac{\partial Y}{\partial x}\,e^{\lambda^2k_0z}\,e^{i\lambda k_0x}\,dx\,dz,\qquad k_0=g/U^2,
\end{equation}
where $F_c=4\cos^2\!\big(k_0\lambda\sqrt{\lambda^2-1}\,s/2\big)$ accounts for interference between hulls a distance $s$ apart ($F_c=1$ for a single hull). The substitution $\lambda=\cosh u$ removes the endpoint singularity. $\partial Y/\partial x$ is taken as constant on each panel, and the exponential factors are integrated exactly in $x$ and $z$ (a Filon-type rule), which keeps the integral accurate at low Froude numbers. The integration was checked on the Wigley parabolic hull ($L/B=10$, $L/T=16$, Fig.~\ref{fig:wigley}): doubling the grid changes $C_W$ by less than 0.03\,\%, and the curve shows the expected hump-and-hollow shape. Thin-ship theory is reported to over-predict near the main hump \cite{tuck}, so wave drag here is, if anything, pessimistic. A transom term follows Holtrop and Mennen \cite{holtrop}. Wave resistance, wetted area, waterline length and draft are tabulated once for each hull shape, over the load the hulls carry (0--3.6\,kg in 0.2\,kg steps) and the speed (0.1--4.5\,m/s in 0.1\,m/s steps), for both hulls together and for one hull. The VPP and the flight simulator interpolate the same table; against direct evaluation, the interpolated hull drag differs by less than 1\,\%. Appendage profile drag uses the ITTC line with Hoerner's thickness factor $1+2t/c+60(t/c)^4$ and a spray term $0.24\,q\,t^2$ \cite{hoerner}. The ITTC line assumes turbulent flow from the leading edge. At the foils' chord Reynolds numbers ($1$--$2\times10^5$) much of the flow may be laminar, so a sensitivity case replaces it with the flat-plate laminar line $C_F=1.328/\sqrt{Re}$ (Prandtl--Schlichting with transition above $Re=5\times10^5$), about half the turbulent value. This is an optimistic bound: a laminar separation bubble adds drag that a flat plate does not have. Induced drag is $D_i=L^2/(q\pi e b^2)$, applied both to foil lift and to the side force carried by boards and rudders.

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[xlabel={Froude number $Fn$}, ylabel={$10^3\,C_W$}, ymin=0]
\addplot[thick, blue] table[x=Fn, y=Cw] {data/wigley.dat};
\end{axis}
\end{tikzpicture}
\caption{Michell wave-resistance coefficient of the Wigley hull from this project's code (grid-converged to 0.03\,\%).}
\label{fig:wigley}
\end{figure}

\subsection{Foils and sails}
Foil lift uses the thin-airfoil zero-lift angle, $\alpha_{L0}=-\frac1\pi\int_0^\pi \frac{dy_c}{dx}(\cos\theta-1)\,d\theta = """ + f"{math.degrees(vpp.alpha_L0('4412')):.2f}" + r"""^\circ$ for NACA\,4412, and the lifting-line slope $a=2\pi/(1+2/(e\,AR))$ with $e=0.85$ \cite{anderson}. The sails produce $F_x=q_aA(C_L\sin\beta-C_D\cos\beta)$ (drive) and $F_y=q_aA(C_L\cos\beta+C_D\sin\beta)$ (heel), with $C_D=C_{D0}+C_L^2/(\pi e_sAR_s)$, $C_{L,\max}=1.3$ and $C_{D0}=0.05$. $C_L$ is reduced (the sails are flattened) whenever $F_yh$ would exceed 90\,\% of the maximum righting moment $W s/2$. The sails are also eased (both forces scaled down) whenever the bow-down moment $F_xh_p$ would exceed 90\,\% of the largest longitudinal righting moment the hulls can provide (Section~\ref{sec:stab}); $h_p$ is measured from the centre of effort to the hull resistance centre. Beyond a beam reach the model blends to a stalled sail ($C_D\to1.2$). The VPP marches boat speed up from rest until drive equals drag; for the foiling version it switches to the flying branch once both foils can carry their share of the weight. Below take-off the wand holds the flaps fully down, so the main foils' lift (and its induced drag) uses the full $15^\circ$ of flap (Section~\ref{sec:rh}). Every foil lift coefficient is capped at 0.8, i.e. 0.8 of an assumed section maximum of 1.0 near $Re=10^5$.

\subsection{Flying trim in heave and pitch}\label{sec:trim}
Once flying, the foils must carry the weight and also balance the pitching moment. The sail drive $F$ equals the flying drag. It acts at the sail centre of effort, while the drag acts at the appendages, so the boat feels a bow-down couple $M=F\,(z_{CE}-z_D)$, with $z_D$ the drag-weighted height of the appendage forces. Moment balance about the centre of gravity gives the foil loads
\begin{equation}
L_e=\frac{W a-M}{a+c},\qquad L_m=W-L_e,
\end{equation}
where $a$ and $c$ are the distances from the CG to the main-foil and elevator quarter chords. The couple moves load from the elevators to the main foils, and at speed the elevators must push down. The fixed-incidence elevators then set the pitch, $\theta=L_e/(qS_ea_e)-i_e$, and the wand-driven flaps make up the main foils' lift. The wand is hinged at the bow with its tip on the water, and its angle is read in the boat frame, so the bow height is $h_p=L\sin(\phi_0-\delta/G-\theta)$. The depth of every appendage follows from $h_p$ and $\theta$, and the strut and rudder drag use those immersed lengths. A speed belongs to the flying range when:
\begin{itemize}\itemsep1pt
\item both foils stay within the usable lift coefficient and the flaps within $\pm15^\circ$;
\item the main foils and elevators stay at least half a chord deep;
\item at least """ + f"{vpp.RUDDER_MIN * 1000:.0f}" + r"""\,mm of rudder stays in the water (an assumed immersion limit);
\item the rudders, at their trimmed immersion, can hold the largest side force the sails can apply before the boat heels out, using at most 80\,\% of their $\pm""" + f"{CTL['rudder_throw_deg']:.0f}" + r"""^\circ$ throw (the reserve is assumed);
\item the hulls stay clear.
\end{itemize}
Take-off is the lowest such speed. Above the range the sails must be eased, and the VPP caps the speed there.

\noindent\textbf{Roll.} Flying, the boat resists heel only by moving lift to the leeward foil. With the leeward wing at its flap and lift limit $L_1$ and the windward one carrying the rest of $L_m$, the foils' largest righting moment is $RM_f=(2L_1-L_m)\,s/2$. At the take-off speed both wings are at that limit, so $RM_f=0$; it reaches $Ws/2$ only as speed builds. Any larger heeling moment $M$ is taken by the leeward hull, which then carries $N=(M-RM_f)/s$ and adds its single-hull resistance (friction, transom and Michell wave drag for one hull). The boat counts as flying only when $N=0$; otherwise it is \emph{skimming}. While skimming, the VPP also eases the sails (scales their lift down) whenever that gives more net thrust, as a sailor would to get onto the foils.

\subsection{Controllability}
Steady yaw balance requires the rudders to cancel $M=F_y(x_{CE}-x_{CLR})+R_{\text{hull}}\,u\,s/2$, where $u$ is the fraction of righting moment in use; the second term is the extra drag of the loaded leeward hull. The rudder force $F_r=M/(x_{CLR}-x_r)$ is converted to a rudder angle with the lifting-line slope, and the windward rudder is taken as clear of the water for $u>0.8$. Foil pitch stability uses the neutral point $x_{np}=(a_mS_mx_m+\eta a_eS_ex_e)/(a_mS_m+\eta a_eS_e)$ with $\eta=1$ or $0.65$ to bracket downwash on the elevators.

\section{Results}\label{sec:results}
\subsection{Mass and hydrostatics}
\begin{table}[t]
\centering\small
\caption{Mass properties and hydrostatics.}
\label{tab:hydro}
\resizebox{\columnwidth}{!}{\begin{tabular}{lccc}
\toprule
& 1\,m build-first & 1\,m foiling & 0.6\,m mini \\
\midrule
Mass (g) & """ + f"{SD['M']:.0f} & {SF['M']:.0f} & {MS['mass_g']:.0f}" + r""" \\
Hull draft (mm) & """ + f"{SD['draft']:.1f} & {SF['draft']:.1f} & {MS['hull_draft_mm']:.1f}" + r""" \\
LCG / LCB (mm) & """ + f"{SD['lcg']:.0f} / {SD['lcb']:.0f} & {SF['lcg']:.0f} / {SF['lcb']:.0f} & {MS['lcg_mm']:.0f} / {MS['lcb_mm']:.0f}" + r""" \\
One-hull buoyancy / weight & """ + f"{SD['res']:.2f} & {SF['res']:.2f} & {MS['one_hull_reserve']:.2f}" + r""" \\
Max righting moment (N\,m) & """ + f"{SD['RM']:.2f} & {SF['RM']:.2f} & {MS['RM_Nm']:.2f}" + r""" \\
Sail area (m$^2$) & 0.401 & 0.401 & 0.144 \\
\bottomrule
\end{tabular}}
\end{table}
Table~\ref{tab:hydro} lists the three boats. The heaviest items on the 1\,m build-first boat are the hulls (""" + f"{bd['Hull Port'] + bd['Hull Stbd']:.0f}" + r"""\,g), the centre pod (""" + f"{bd['Center Pod']:.0f}" + r"""\,g) and the RC electronics (""" + f"{bd['RC Electronics']:.0f}" + r"""\,g); the foiling kit adds """ + f"{FOILKIT_G:.0f}" + r"""\,g. The design target was that one hull alone could float at least twice the boat's weight; all three versions meet it.

\subsection{Resistance and speed}
\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[xlabel={Boat speed $V$ (m/s)}, ylabel={Resistance (N)}, legend pos=north west, ymin=0]
\addplot[thick, blue] table[x=V, y=R] {data/resistance_displacement.dat}; \addlegendentry{build-first (total)}
\addplot[thick, red] table[x=V, y=R] {data/resistance_foiling.dat}; \addlegendentry{foiling (total)}
\addplot[dashed, blue] table[x=V, y=wave] {data/resistance_displacement.dat}; \addlegendentry{build-first wave (Michell)}
\addplot[dotted, thick, blue] table[x=V, y=fric] {data/resistance_displacement.dat}; \addlegendentry{build-first hull friction}
\end{axis}
\end{tikzpicture}
\caption{Resistance at zero side force. The foiling curve peaks just before take-off (""" + f"{SF['vto']:.2f}" + r"""\,m/s) and drops once the hulls leave the water.}
\label{fig:res}
\end{figure}

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[xlabel={True wind speed (kn)}, ylabel={Boat speed (m/s)}, legend pos=north west, ymin=0, xmin=3, xmax=16, ymax=6.2]
\addplot[thick, blue, mark=*, mark size=1pt] table[x=tws, y=V] {data/vpp_displacement_90.dat}; \addlegendentry{build-first, TWA 90$^\circ$}
\addplot[thick, blue, dashed] table[x=tws, y=V] {data/vpp_displacement_60.dat}; \addlegendentry{build-first, TWA 60$^\circ$}
\addplot[thick, red, mark=square*, mark size=1pt] table[x=tws, y=V] {data/vpp_foiling_90.dat}; \addlegendentry{foiling, TWA 90$^\circ$}
\addplot[thick, red, dashed] table[x=tws, y=V] {data/vpp_foiling_60.dat}; \addlegendentry{foiling, TWA 60$^\circ$}
\end{axis}
\end{tikzpicture}
\caption{Predicted boat speed. The jump in the foiling curves is take-off. The build-first boat must depower above about """ + f"{DEP_LO:g}--{DEP_HI:g}" + r"""\,kn.}
\label{fig:vpp}
\end{figure}

Figures~\ref{fig:res} and~\ref{fig:vpp} show the predicted resistance and speed. Hull friction and appendage drag dominate the build-first boat; Michell wave drag stays below """ + f"{WAVE_MAX:.2f}" + r"""\,N up to 3\,m/s because the hulls are slender ($L/B=12.5$). Below take-off, the foils cost the foiling version """ + f"{min(SLOW)*100:.0f}--{max(SLOW)*100:.0f}" + r"""\,\% of its speed. The foiling version takes off from about """ + f"{TO_BASE:g}" + r"""\,kn of true wind, which is below the """ + f"{DEP_LO:g}--{DEP_HI:g}" + r"""\,kn where the rig starts to depower, so a usable foiling window exists. Table~\ref{tab:sens} shows that this conclusion holds across the least certain inputs.

\begin{table}[t]
\centering\small
\caption{Take-off speed and the lowest true wind (kn) at which the foiling version takes off.}
\label{tab:sens}
\resizebox{\columnwidth}{!}{\begin{tabular}{lccc}
\toprule
Scenario & $V_{to}$ (m/s) & TWA 60$^\circ$ & TWA 90$^\circ$ \\
\midrule
""" + sens_tab + r"""
\bottomrule
\end{tabular}}
\end{table}

\subsection{Controllability}
\textbf{Build-first version.} Over 4--14\,kn and TWA 60--105$^\circ$ the rudders need at most """ + f"{rud_disp['rudder_angle_deg']:.1f}" + r"""$^\circ$ (TWA """ + f"{rud_disp['twa']}" + r"""$^\circ$, """ + f"{rud_disp['tws_kn']}" + r"""\,kn, one rudder working) of the $\pm""" + f"{CTL['rudder_throw_deg']:.0f}" + r"""^\circ$ that the linkage gives. That leaves at least """ + f"{min(x['stall_margin'] for x in CTL['displacement'])*100:.0f}" + r"""\,\% margin to stall, and the servo torque needed is below """ + f"{SERVO_MAX + 0.005:.2f}" + r"""\,kg\,cm.

\noindent\textbf{Foiling version.} Steering while flying needs at most """ + f"{rud_foil['rudder_angle_deg']:.1f}" + r"""$^\circ$, with """ + f"{rud_foil['rudder_immersed_mm']:.0f}" + r"""\,mm of rudder immersed in that case (from the flying trim). The foil system is statically pitch-stable: the CG lies """ + f"{pitch['elevator efficiency 0.65 (downwash/wake)']['static_margin_mm']:.0f}" + r"""--""" + f"{pitch['no downwash']['static_margin_mm']:.0f}" + r"""\,mm ahead of the neutral point. Heave is the problem (Fig.~\ref{fig:heave}). With fixed incidence, lift grows as $V^2$ while weight is constant, so nothing sets the flying height: the boat would climb until a foil breaches and ventilates, then drop. Holding height requires the main-foil angle to change by """ + f"{heave[0]['main_foil_angle_change_needed_deg']:+.1f}" + r"""$^\circ$ at """ + f"{heave[0]['V']:g}" + r"""\,m/s but """ + f"{heave[-1]['main_foil_angle_change_needed_deg']:+.1f}" + r"""$^\circ$ at """ + f"{heave[-1]['V']:g}" + r"""\,m/s. If the boat is also free to pitch, the fixed-incidence elevators trim it nose-down as speed rises. That reduces the excess but does not remove it, and nothing still ties lift to height, so heave stays neutral. Ride-height control is therefore required before the foiling version can fly under control (Section~\ref{sec:rh}).

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[width=0.78\columnwidth, xlabel={Boat speed (m/s)}, ylabel={Lift excess over weight (\%)}, axis y line*=left]
\addplot[thick, red, mark=*] table[x=V, y=excess] {data/heave.dat};
\end{axis}
\begin{axis}[width=0.78\columnwidth, ylabel={Foil angle change ($^\circ$)}, axis y line*=right, axis x line=none, grid=none]
\addplot[thick, blue, dashed, mark=square*] table[x=V, y=dalpha] {data/heave.dat};
\end{axis}
\end{tikzpicture}
\caption{Fixed-incidence foils: lift in excess of weight (solid, left axis) and the main-foil angle change needed to hold height (dashed, right axis).}
\label{fig:heave}
\end{figure}

@@STAB@@

\subsection{Foil structure}
With the largest main-foil flight load, which occurs at speed when the elevators push down, all on one wing under a 2\,g gust (""" + f"{Lcase:.1f}" + r"""\,N; root moment """ + f"{Mroot:.0f}" + r"""\,N\,mm), the section properties computed from the NACA coordinates give the results in Table~\ref{tab:struct}. Printed PETG is strong enough but far too flexible, so the foils must be carbon. A home-buildable alternative to solid carbon is a printed core with unidirectional carbon caps (4 layers of 0.127\,mm tape, 25\,mm wide, on each face). Taking $E\approx120$\,GPa for the cap laminate (assumed), centring the caps on the thickest point and ignoring the core, the caps give """ + f"{CAP_RATIO * 100:.0f}" + r"""\,\% of the solid-carbon bending stiffness: tip deflection """ + f"{CAP_TIP:.2f}" + r"""\,mm and cap stress """ + f"{CAP_STRESS:.0f}" + r"""\,MPa in the load case above. The v2 foiling kit (cores, carbon tape, laminating epoxy, flap hinges, wands and linkage) costs \$""" + f"{FOIL_COST:.2f}" + r""".
\begin{table}[t]
\centering\small
\caption{L-foil structural check (v2.2 foils).}
\label{tab:struct}
\resizebox{\columnwidth}{!}{\begin{tabular}{lccc}
\toprule
Material & Root stress & Tip deflection & Strut rotation \\
\midrule
""" + '\n'.join(f"{k} & {v[0]:.1f} MPa & {v[1]:.2f} mm & {v[2]:.2f}$^\\circ$ \\\\" for k, v in STRUCT.items()) + r"""
\bottomrule
\end{tabular}}
\end{table}

@@RIG@@

@@RH@@

@@OPT@@

\section{Simplified 0.6\,m version}
Because the RC electronics do not shrink with the boat, geometric scaling would leave the small hulls overloaded. The mini therefore scales length by 0.6 but hull sections by 0.68, which brings one-hull buoyancy back to """ + f"{MS['one_hull_reserve']:.2f}" + r""" times the """ + f"{MS['mass_g']:.0f}" + r"""\,g sailing weight. One winch drives both sheets on a stepped drum. Its 30\,mm and 16.2\,mm grooves are sized so that the mainsheet (""" + f"{MD['drum']['main_travel_mm']:.0f}" + r"""\,mm) and jib sheet (""" + f"{MD['drum']['jib_travel_mm']:.0f}" + r"""\,mm) reach full ease in the same """ + f"{MD['drum']['main_turns']:.2f}" + r""" turns. The same analysis predicts """ + f"{MINI_V8:.1f}" + r"""\,m/s on a beam reach in 8\,kn of wind, and at most """ + f"{MINI_RUD:.1f}" + r"""$^\circ$ of rudder needed. Parts cost \$""" + f"{MINI_COST:.2f}" + r""" at September 2026 prices, with every price read from a retailer page. A build manual with 1:1 sail patterns accompanies this paper.

\section{Design iterations driven by analysis}
Several changes came directly from the checks above rather than from the first layout:
\begin{enumerate}\itemsep1pt
\item \textbf{Foil depth.} The main foils were raised 80\,mm to the elevator depth, because the elevators breach first. This saved 73\,g of carbon at no cost in ride height.
\item \textbf{Mini hull sections.} The mini's section scale was raised from 0.65 to 0.68 so that one hull still floats at least twice the boat's weight despite full-size electronics.
\item \textbf{Stepped winch drum.} The mini's jib groove was reduced from 18 to 16.2\,mm so both sheets reach full ease in the same number of turns.
\item \textbf{Winch fit.} The first-choice 3.5-turn winches are 50\,mm tall and did not fit the 48.8\,mm pod. A torque estimate showed standard-size 45\,g winches carry the sheet loads with margin, which also saved 130\,g and \$""" + f"{2*56.99 - 2*11.13:.0f}" + r""".
\item \textbf{Bow volume.} The pitchpole study led to the v1.3 hull (Table~\ref{tab:bows}).
\item \textbf{Pitch-limited depowering.} Adding the bow limit to the VPP first produced a speed that fell as the wind rose. That was traced to the model switching to the one-hull limit, and fixed by letting the model choose, as a skipper would, between sailing flat and flying a hull.
\item \textbf{Servo fit.} Checking every mount against the manufacturers' drawings found three misfits: the 40.5\,mm winch cases did not fit between rails 40.2\,mm apart (40\,mm on the mini); the 1\,m rails sat 3.5\,mm below the FS5115M's ears (27.3\,mm above the case bottom); and the mini's micro-servo rails sat 6\,mm below the MG90S ear line. The rails were redrawn from the drawings with 0.3--0.4\,mm clearance and a wire notch at each rail. Each winch now hangs in a 4--6\,mm well, so its drum clears the lid by 5.6--7.9\,mm instead of 0.4\,mm on the mini.
\item \textbf{Mini crossbeams.} The rig-load check (Section~\ref{sec:rigload}) replaced the mini's 8\,x\,7\,mm beams with 10\,x\,8\,mm tube.
\item \textbf{Rig clearance.} A clearance sweep of the Fusion model over nine trims (boom and jib from 0/5$^\circ$ to 40/40$^\circ$) showed that the original pod, which ran over both beams, blocked the traveler car for boom angles below about 7.5$^\circ$. In that range the mainsheet from the clew (259\,mm from the transom) to the car also passed through the pod lid, and the jib car sat inside the pod. The pod now ends 11\,mm forward of the clew. Its aft end first hung on a printed cradle under the rear beam, but a load check showed that a cradle under the beam can only hold the pod down, not up. The aft end now rests on a light third crossbeam: 10\,mm carbon, cut from the tube already bought for the mast joiner, at 350\,mm from the transom, where no mainsheet position reaches. The rudder servo sits aft of the rear beam on a printed bracket, under a cover. The bracket clamps the beam from below, so the car can cross the centreline, and the jib track moved onto the lid. The same interference check found the tiller arms and ride-height wands rubbing the hulls. The tiller arms are now level, and the wands hinge ahead of the stems. The sweep is now clear at all nine trims.
\item \textbf{Pitch trim (v2.2 foils).} A first simulator search (v2.1) picked smaller foils with $4^\circ$ elevators. Adding the trim in heave and pitch (Section~\ref{sec:trim}) showed that the sail drive's couple makes the elevators push down at speed, and that fixed positive-incidence elevators then pitch the boat nose-down until they leave the water: neither v2.0 nor v2.1 would fly. The search was repeated with the elevator height as a variable, a pitch static-margin limit, operating margins and robustness checks. The adopted v2.2 foils have the elevators at $-1^\circ$, 13\,mm lower on slightly longer rudders, and fly level at 12\,kn (Section~\ref{sec:opt}).
\item \textbf{Fittings and masses.} Designing the printed fittings and the mast fairing replaced placeholder blocks and assumed masses. The fairing, gooseneck and boom jaw weigh """ + f"{CADM:.0f}" + r"""\,g, where 10\,g had been assumed for the fairing. The rudder stocks, tiller arms, tie bar and pushrod had been weighed as aluminium, but they are music wire (the steel tie bar alone is """ + f"{TIEBAR:.0f}" + r"""\,g). The build-first boat went from 2037 to """ + f"{D['mass_g']:.0f}" + r"""\,g and the foiling boat from 2242 to """ + f"{F['mass_g']:.0f}" + r"""\,g, with the centre of gravity about 7\,mm further aft; every result here uses the new masses. The traveler's end stops also limit the boom to about """ + f"{MD1['travel']['boom_at_car_stop_deg']:.0f}" + r"""$^\circ$ off the centre line.
\end{enumerate}
These checks are now automated. After every analysis run, a design-rule script re-checks """ + f"{len(DC)}" + r""" rules against the results, the rig model and the CAD constants: one-hull buoyancy, rudder and foil-pitch margins, heave damping, take-off wind, rig-to-pod clearances, servo fit and drum-to-lid clearance. """ + (f"All {len(DC)} pass." if all(r['ok'] for r in DC) else f"{sum(r['ok'] for r in DC)} of {len(DC)} pass.") + r""" (The script first caught a stale CAD volume in the hull-volume check.)

\section{Discussion and limitations}
All performance numbers are model predictions and remain to be checked on the water. The main uncertainties are the sail coefficients ($C_{L,\max}$), foil lift at $Re\approx10^5$ and near the free surface, and the form factor. Thin-ship theory also neglects sinkage, trim and spray. The yaw balance uses geometric centres of effort and lateral resistance, which is a conservative simplification. In the trim model the three sail controls are independent. On the boat this depends on the mainsheet routing. If the tail simply ran from the traveler car to the pod, moving the car would change the tail length by up to """ + f"{fg.CAR_LIMIT:.0f}" + r"""\,mm, more than the mainsheet servo can take up. The mainsheet is therefore dead-ended on a pin in one of the traveler track's end stops and led out of the car round a pin in the other, so any car movement shortens one side exactly as much as it lengthens the other. The sensitivity study addresses the first two uncertainties. Next steps: (1) build and GPS-log the mini and the 1\,m build-first boat and compare speeds with Fig.~\ref{fig:vpp}; (2) build the v2.2 foils (Section~\ref{sec:opt}), with an adjustable elevator incidence, and tow-test them; (3) build the wand-and-flap ride-height system of Section~\ref{sec:rh} and tune its gearing on the water.

\section{Conclusion}
A 1\,m RC beach catamaran was designed with printable, compartmented hulls, a real-cat rig trimmed by three sliders, and two appendage options. A validated velocity prediction program and a controllability analysis support four conclusions: the displacement version is controllable with large margins; the foiling version can reach take-off in moderate wind; with fixed foils it has no heave stability, but a wand-driven flap on each L-foil makes heave stable and well damped; and a 0.6\,m simplified version is the sensible first build. A flight simulator built on the same physics, with the boat's trim in heave and pitch, showed that the sail drive's bow-down couple decides the elevator design: elevators at a positive fixed incidence would pitch the boat nose-down and leave the water at speed. The adopted v2.2 foils, with the elevators at $-1^\circ$ and slightly deeper, fly level at 12\,kn and are in the CAD model.

\begin{thebibliography}{9}\small
\bibitem{hobie} Hobie 16 specifications. \url{https://en.wikipedia.org/wiki/Hobie_16}
\bibitem{nacra} Nacra 17 specifications. \url{https://en.wikipedia.org/wiki/Nacra_17}
\bibitem{michell} J.\,H. Michell, ``The wave-resistance of a ship,'' \emph{Philosophical Magazine}, 45, 1898.
\bibitem{tuck} E.\,O. Tuck, ``The wave resistance formula of J.\,H. Michell (1898) and its significance to recent research in ship hydrodynamics,'' \emph{J. Austral. Math. Soc. Ser. B}, 30, 1989.
\bibitem{shipd} N. Bagazinski and F. Ahmed, ``Ship-D: Ship hull dataset for design optimization using machine learning,'' arXiv:2305.08279.
\bibitem{holtrop} J. Holtrop and G.\,G.\,J. Mennen, ``An approximate power prediction method,'' \emph{International Shipbuilding Progress}, 29, 1982.
\bibitem{hoerner} S.\,F. Hoerner, \emph{Fluid-Dynamic Drag}, 1965.
\bibitem{anderson} J.\,D. Anderson, \emph{Fundamentals of Aerodynamics}, McGraw-Hill.
\end{thebibliography}
\end{document}
"""
rh = RH
r2, r5 = RHr[0], RHr[-1]                       # ends of the flying range tabulated by ride_height.py (at most 5 m/s)
pmin, pmax = min(r['pitch_deg'] for r in RHr), max(r['pitch_deg'] for r in RHr)
sg = lambda x, d=1, plus=True: '$' + (f"{round(x, d) + 0.0:+.{d}f}" if plus else f"{round(x, d) + 0.0:.{d}f}") + '$'   # math minus, no negative zero
fmin, fmax = min(r['flap_deg'] for r in RHr), max(r['flap_deg'] for r in RHr)
RH_SECTION = r"""\section{Ride-height control}\label{sec:rh}
Each L-foil wing gets a trailing-edge flap of """ + f"{rh['flap_chord_ratio']*100:.0f}" + r"""\,\% chord (""" + f"{rh['flap_chord_ratio'] * WC:.0f}" + r"""\,mm) from 10\,mm inside the tip to the strut, """ + f"{WS - 14.5:.0f}" + r"""\,mm of the """ + f"{WS:.0f}" + r"""\,mm span. A carbon wand hinged at each bow trails on the water and drives that hull's flap through a deck pushrod, a bellcrank and a rod inside the strut. Each foil therefore regulates its own height, which also adds roll stability. Thin-airfoil theory gives the flap effectiveness
\begin{equation}
\tau = 1-\frac{\theta_h-\sin\theta_h}{\pi},\qquad \cos\theta_h = 2E-1,
\end{equation}
so $\tau=""" + f"{rh['tau_thin_airfoil']:.3f}" + r"""$ for $E=0.25$; """ + f"{rh['tau_used']:.3f}" + r""" is used after a 20\,\% viscous reduction. The wand is """ + f"{rh['wand_length_m']*1000:.0f}" + r"""\,mm long at """ + f"{rh['wand_angle_deg']:.0f}" + r"""$^\circ$, so its angle changes by """ + f"{rh['dphi_dh_rad_per_m']:.2f}" + r"""\,rad per metre of height. The linkage gearing is """ + f"{rh['gear']:.1f}" + r"""$^\circ$ of flap per degree of wand.

\noindent\textbf{Trim.} At each speed the elevators set the pitch and the flaps make up the main foils' lift, with the sail-drive couple included (Section~\ref{sec:trim}). From take-off at """ + f"{RH['takeoff_ms']:.2f}" + r""" to """ + f"{r5['V']:.1f}" + r"""\,m/s the flap angle stays between """ + sg(fmin, 1, False) + r"""$^\circ$ and """ + sg(fmax, 1, False) + r"""$^\circ$, inside the $\pm15^\circ$ travel (Fig.~\ref{fig:rh}). The boat pitches between """ + sg(pmin) + r"""$^\circ$ and """ + sg(pmax) + r"""$^\circ$ (nose up $+$), and the bow flies """ + sg(r2['ride_height_shift_mm'], 0) + r""" to """ + sg(r5['ride_height_shift_mm'], 0) + r"""\,mm from its design height.

\noindent\textbf{Heave stability.} Linearised heave dynamics are
\begin{gather}
m\ddot h + c\,\dot h + k\,h = 0,\\
c=\frac{q(S_ma_m+S_ea_e)}{V},\qquad k=q\,S_ma_m\,\tau\,G\,\frac{d\phi}{dh},
\end{gather}
where $c$ comes from the change of foil angle of attack with vertical velocity ($\dot h/V$) and $k$ from the wand feedback. With fixed foils $k=0$, so nothing restores height. With the wand, $k$ rises from """ + f"{r2['k_N_per_m']:.0f}" + r""" to """ + f"{r5['k_N_per_m']:.0f}" + r"""\,N/m and the natural frequency from """ + f"{r2['wn_hz']:.1f}" + r""" to """ + f"{r5['wn_hz']:.1f}" + r"""\,Hz. Because $c\propto V$ and $\sqrt{k}\propto V$, the damping ratio is the same at every speed, $\zeta=""" + f"{r2['zeta']:.1f}" + r"""$ (over-damped): disturbances die out without oscillating. A time-domain run of the same model (\texttt{analysis/foil\_checks.py}) confirms this: across the flying range a 20\,mm height disturbance decays to 5\,\% in """ + f"{min(x['settling_s'] for x in FC['heave_time_domain']):.2f}--{max(x['settling_s'] for x in FC['heave_time_domain']):.2f}" + r"""\,s with no overshoot, while with fixed foils it does not decay at all. The same script checks the trim over the flying range up to the 12\,kn beam-reach speed: the elevators stay at least """ + f"{FCR['elevator depth over the flying range (to the 12 kn speed)']:.2f}" + r""" chords deep, the main foils """ + f"{FCR['main foil depth over the flying range']:.2f}" + r""" chords, and at least """ + f"{FCR['rudder immersion over the flying range']:.0f}" + r"""\,mm of rudder stays in the water. At take-off, with the flaps fully down, the main foils need $C_L=""" + f"{FCR['main foil CL at take-off (flaps down)']:.2f}" + r"""$. """ + f"{sum(r['ok'] for r in FC['rules'])} of {len(FC['rules'])}" + r""" foil checks pass.

\noindent\textbf{Heave and pitch together.} The wand sits a metre ahead of the elevators, so heave and pitch are coupled: the wand reads the bow height and the boat-frame angle, and each foil feels the vertical velocity of its own station, $\dot h + l\,\dot\theta$. Linearising both degrees of freedom about the trim, with the pitch inertia from the CAD model ($I_{yy}=""" + f"{PHR['inertia']['Iyy_kgm2']:.3f}" + r"""$\,kg\,m$^2$, radius of gyration """ + f"{PHR['inertia']['k_pitch_m'] * 1000:.0f}" + r"""\,mm), gives a fourth-order system (\texttt{analysis/pitch\_heave.py}). Across the flying range it is stable (Routh--Hurwitz), with one oscillating mode at """ + f"{min(m['freq_hz'] for r in PHR['rows'] for m in r['wand']['modes'] if m['freq_hz'] > 0):.1f}--{max(m['freq_hz'] for r in PHR['rows'] for m in r['wand']['modes']):.1f}" + r"""\,Hz and damping ratio at least """ + f"{PHR['min_damping']:.2f}" + r""" (""" + f"{PHR['min_damping_eta065']:.2f}" + r""" with an elevator efficiency of 0.65), and two non-oscillating decaying modes. That is less damping than the heave-only estimate ($\zeta=""" + f"{r2['zeta']:.2f}" + r"""$), but the motion stays well damped. With fixed foils one root sits at zero: heave stays neutral. Unsteady lift, added mass and downwash lag are left out.

\noindent\textbf{Take-off in time.} The trims above are equilibria. The transition was also integrated in time (\texttt{analysis/takeoff\_sim.py}): surge, heave and pitch with RK4 in 2\,ms steps, hull buoyancy from the stations at the instantaneous attitude, the wand and flap stops, foil lift fading over the last half chord below the surface, and sail drive from the VPP (the boat is held flat). From rest in 8\,kn on a beam reach the hulls leave the water after """ + f"{TS['beam reach, 8 kn']['takeoff_s']:.1f}" + r"""\,s. The bow then rises at most """ + f"{TS['beam reach, 8 kn']['max_bow_rise_mm']:.0f}" + r"""\,mm above its design height, the elevators stay at least """ + f"{TS['beam reach, 8 kn']['min_el_depth_mm']:.0f}" + r"""\,mm deep, and the boat settles at """ + f"{TS['beam reach, 8 kn']['end']['V']:.2f}" + r"""\,m/s, matching the VPP's steady speed (Fig.~\ref{fig:ts}). A 4\,kn gust for 5\,s while flying in 9\,kn raises the bow at most """ + f"{TS['beam reach, 9 kn, 4 kn gust at 20-25 s']['max_bow_rise_mm']:.0f}" + r"""\,mm and leaves the elevators at least """ + f"{TS['beam reach, 9 kn, 4 kn gust at 20-25 s']['min_el_depth_mm']:.0f}" + r"""\,mm deep; no foil breaches. Hull damping when afloat is an assumed 30\,\% of critical; it only affects the hull-borne phase.

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[width=0.8\columnwidth, height=0.55\columnwidth, xlabel={Time (s)}, ylabel={Speed (m/s)}, axis y line*=left, xmin=0, xmax=12, ymin=0, legend style={at={(0.97,0.35)}, anchor=east}]
\addplot[thick, blue] table[x=t, y=V] {data/takeoff_ts.dat}; \addlegendentry{speed}
\end{axis}
\begin{axis}[width=0.8\columnwidth, height=0.55\columnwidth, ylabel={Bow height, flap}, axis y line*=right, axis x line=none, xmin=0, xmax=12, grid=none, legend style={at={(0.97,0.12)}, anchor=east}]
\addplot[thick, red] table[x=t, y=bow] {data/takeoff_ts.dat}; \addlegendentry{bow (mm)}
\addplot[thick, black!60, dashed] table[x=t, y=flap] {data/takeoff_ts.dat}; \addlegendentry{flap ($^\circ$)}
\end{axis}
\end{tikzpicture}
\caption{Take-off from rest in 8\,kn on a beam reach (time-domain simulation): boat speed, bow height relative to the design ride height, and flap angle. The flaps sit on their $+15^\circ$ stops until the boat rises.}
\label{fig:ts}
\end{figure}

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[xlabel={Boat speed (m/s)}, ylabel={Angle ($^\circ$)}, legend pos=south west]
\addplot[thick, red] table[x=V, y=flap] {data/ride_height.dat}; \addlegendentry{flap angle}
\addplot[thick, blue, dashed] table[x=V, y=pitch] {data/ride_height.dat}; \addlegendentry{boat pitch}
\end{axis}
\end{tikzpicture}
\caption{Wand-controlled flight across the flying range: flap angle and boat pitch from the trim of Section~\ref{sec:trim}, sail-drive couple included. Flap travel is $\pm15^\circ$.}
\label{fig:rh}
\end{figure}"""
tex = tex.replace('@@RH@@', RH_SECTION)
PT = json.load(open(os.path.join(ROOT, 'analysis', 'pitch_trim_results.json')))
LAM = [x for x in PT['robustness'] if x['case'].startswith('foil friction')][0]
o20, o21, oad, osp, olw, orb = OPT['v20'], OPT['v21'], OPT['adopted'], OPT['speed_design'], OPT['lightwind'], OPT['rule_best']
assert OPT['cad_is_adopted'], 'the CAD foils are no longer within tolerance of the search rule: update the CAD'
assert all(abs(oad[k] - OPT['cad_design'][k]) < 1e-6 for k in ('wspan', 'wchord', 'winc', 'espan', 'echord', 'einc', 'zel')), 'CAD foils differ from the adopted design'
flies = lambda g: g['vto'] is not None and g['tws90'] is not None
def geo(g):
    return f"{g['wspan']:.0f}\\,x\\,{g['wchord']:.0f} at ${g['winc']:g}^\\circ$", f"{g['espan']:.0f}\\,x\\,{g['echord']:.0f} at ${g['einc']:g}^\\circ$"
fl = lambda g, f: f(g) if flies(g) else '--'
hb = lambda g, k: f"{g[k]:.2f}" + ('' if g[k + '_mode'] == 'flying' else '\\,h')
opt_cols = [o20, o21, oad, olw, osp]
opt_rows = [
    ('Main foil, span x chord (mm), incidence', [geo(g)[0] for g in opt_cols]),
    ('Elevator, span x chord (mm), incidence', [geo(g)[1] for g in opt_cols]),
    ('Elevator height $z$ (mm)', [f"{g['zel']:.0f}" for g in opt_cols]),
    ('Sailing mass (g)', [f"{g['mass_g']:.0f}" for g in opt_cols]),
    ('Take-off speed / flies to (m/s)', [fl(g, lambda g: f"{g['vto']:.2f} / " + ('6+' if g['vfly_max'] >= 6 - 1e-6 else f"{g['vfly_max']:.2f}")) for g in opt_cols]),
    ('Wind to fly at 90 / 60$^\\circ$ (kn)', [fl(g, lambda g: f"{g['tws90']:.2f} / {g['tws60']:.2f}") for g in opt_cols]),
    ('Speed at 8 / 12\\,kn, beam reach (m/s)', [f"{hb(g, 'v8')} / {hb(g, 'v12')}" for g in opt_cols]),
    ('At 12\\,kn: pitch, flap', [fl(g, lambda g: f"{round(g['pitch12'], 1) + 0.0:+.1f}$^\\circ$, {round(g['flap12'], 1) + 0.0:+.1f}$^\\circ$") for g in opt_cols]),
    ('At 12\\,kn: elev. / main / rudder depth (mm)', [fl(g, lambda g: f"{g['el_depth12_mm']:.0f} / {g['main_depth12_mm']:.0f} / {g['rudder12_mm']:.0f}") for g in opt_cols]),
    ('Root stress main / elev. (MPa)', [fl(g, lambda g: f"{g['stress_main']:.0f} / {g['stress_el']:.0f}") for g in opt_cols]),
    ('Main tip deflection (mm)', [fl(g, lambda g: f"{g['defl_main']:.2f}") for g in opt_cols]),
    ('Static margin (mm), heave $\\zeta$', [f"{g['static_margin_mm']:.0f}, {g['heave_zeta']:.2f}" for g in opt_cols]),
]
pct = lambda a, b: (a / b - 1) * 100
t21 = [r for r in PT['v2.1']['rows'] if r['V'] >= 3.0]
cad_rows = PT['CAD']['rows']
c45 = min(cad_rows, key=lambda r: abs(r['V'] - 4.5))
wet21 = next((r['V'] for r in PT['v2.1']['rows'] if r['el_depth_mm'] < 0), None)
defl21 = OPT['v21_retrim_why'].get('deflection', 0); n21 = sum(OPT['v21_retrim_why'].values())
OPT_SECTION = r"""\section{Foil design with the flight simulator}\label{sec:opt}
The VPP answers whether a given design flies; to ask which foils fly best, it was turned into an interactive flight simulator (a web page, \texttt{sim/foil\_sim.html}). Its physics are the VPP's, including the flying trim of Section~\ref{sec:trim}: the Michell wave resistance is tabulated against boat speed and the weight the hulls carry, and every other term is computed live. At the CAD design it reproduces the Python VPP's boat speed to """ + f"{OPT['vpp_agreement']['max_abs_dV']:.2f}" + r"""\,m/s in all """ + f"{OPT['vpp_agreement']['n']}" + r""" reference cases (build-first and foiling, 6--10\,kn, 60 and 90$^\circ$). It adds:
\begin{itemize}\itemsep1pt
\item foil span, chord and incidence, and the elevator height, as inputs;
\item foil and rudder mass and the resulting shift of the centre of gravity, with the densities of the CAD mass export;
\item the wand-driven flaps: fully down below take-off (they add induced drag there), then trimmed to hold ride height;
\item a cap on the usable foil lift coefficient of 0.8 (0.8 of an assumed section maximum of 1.0 near $Re=10^5$).
\end{itemize}

\noindent\textbf{A first search, and why it was withdrawn.} A first search was run before the trim model existed. It assumed each foil pair carried a fixed share of the weight at level attitude, so the elevators set the take-off speed. It recommended smaller foils with the elevators at $4^\circ$ (v2.1: wings 160\,x\,40\,mm at $0^\circ$, elevators 140\,x\,32\,mm at $4^\circ$), and these were drawn in CAD. The trim model reverses that result. At """ + f"{c45['V']:.1f}" + r"""\,m/s the v2.2 foils must balance a """ + f"{c45['pitch_couple_Nm']:.1f}" + r"""\,N\,m bow-down couple, more than the elevators' share of the weight times the foil spacing, so the elevators must push down. Fixed at $+4^\circ$, they can only do that by pitching the whole boat nose-down. The stern, a metre behind the wand that holds the bow, then rises until the elevators leave the water: for v2.1 the elevator reaches the surface at """ + (f"{wet21:.1f}" if wet21 else '--') + r"""\,m/s (Fig.~\ref{fig:trim}). Neither the original v2.0 foils nor v2.1 has any speed at which the trim is feasible: as drawn, they would not fly.

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[width=\columnwidth, height=0.62\columnwidth, xlabel={Boat speed (m/s)}, ylabel={Elevator depth (mm)}, ymin=-60, ymax=100, xmin=2, xmax=5, legend style={font=\scriptsize, at={(0.5,-0.26)}, anchor=north, legend columns=3, draw=none}]
\addplot[thick, red!70!black, dashed] table[x=V, y=eldepth] {data/trim_v21.dat}; \addlegendentry{v2.1}
\addplot[thick, blue] table[x=V, y=eldepth] {data/trim_CAD.dat}; \addlegendentry{v2.2}
\addplot[gray, thin] coordinates {(2,0) (5,0)}; \addlegendentry{water surface}
\end{axis}
\end{tikzpicture}
\caption{Elevator depth from the flying trim, sail-drive couple included. The v2.1 elevators at $+4^\circ$ pitch the boat nose-down and come out of the water; the v2.2 elevators at $-1^\circ$, 13\,mm lower, stay in. (The v2.1 curve is shown where no feasible trim exists, to show why.)}
\label{fig:trim}
\end{figure}

\noindent\textbf{The search with the trim model.} The search was repeated with the trim model and with the elevator height as a variable (the rudder blades end 3\,mm below the elevators). A grid of """ + f"{OPT['grid_size']:,}".replace(",", "{,}") + r""" designs covered:
\begin{itemize}\itemsep1pt
\item main-foil span 140--300\,mm and chord 40--80\,mm, at 0, 1 or 2$^\circ$;
\item elevator span 100--260\,mm and chord 28--52\,mm, at 0--2$^\circ$;
\item elevator height $z=-215$ to $-275$\,mm (the v2.1 elevators sit at $-197$\,mm).
\end{itemize}
Incidences from $-1$ to $3^\circ$ and the height were then refined for the best sizes. A design counts as feasible when:
\begin{itemize}\itemsep1pt
\item root stress with the largest flight load of a foil pair on one foil at 2\,g stays within 100\,MPa (safety 3 on an assumed 300\,MPa), and main-foil tip deflection within 2\,mm;
\item both foils see a chord Reynolds number of at least $5\times10^4$ at take-off (an assumed threshold, below which thin-airfoil lift is optimistic);
\item heave damping with the wand gearing of Section~\ref{sec:rh} is at least $\zeta=0.5$;
\item the pitch static margin is at least 30\,mm with an elevator efficiency of 0.65 (about 5\,\% of the 590\,mm foil spacing, assumed);
\item the boat flies at 12\,kn on a beam reach, with the flying range reaching at least 5\,\% above that speed.
\end{itemize}
Feasible designs tended to sit on these limits. Nose-down pitch lifts the rudders and struts out of the water and cuts their drag, which the model rewards and a gust would punish. The adopted design therefore also needs operating margins at the 12\,kn speed: main foils and elevators at least one chord deep, at least 45\,mm of rudder in the water, and a flying range reaching 10\,\% above that speed. It must also be robust: it must still fly, without hitting the top of the flying range at 12\,kn, with the sail-drive couple halved or 1.5 times larger and with the CG 20\,mm forward or aft. Of """ + f"{OPT['feasible_total']:,}".replace(",", "{,}") + r""" feasible designs, """ + f"{OPT['with_margins']:,}".replace(",", "{,}") + r""" had the margins and """ + f"{OPT['robust_total']:,}".replace(",", "{,}") + r""" were also robust. Among robust designs within 5\,\% of the fastest, the rule picks the one needing the least wind to fly, averaged over 60 and 90$^\circ$. The design in CAD stays adopted while it passes every check and needs at most """ + f"{OPT['adoption_tolerance_kn']:.1f}" + r"""\,kn more wind than the rule's pick. That tolerance is below the model's resolution (see below), and in this run the difference is """ + f"{oad['tws_avg'] - orb['tws_avg']:+.2f}" + r"""\,kn.

\noindent\textbf{v2.2.} The adopted foils are wings of """ + f"{oad['wspan']:.0f}\\,x\\,{oad['wchord']:.0f}" + r"""\,mm at $""" + f"{oad['winc']:+g}" + r"""^\circ$ and elevators of """ + f"{oad['espan']:.0f}\\,x\\,{oad['echord']:.0f}" + r"""\,mm at $""" + f"{oad['einc']:+g}" + r"""^\circ$, set """ + f"{-197 - oad['zel']:.0f}" + r"""\,mm lower than before (Table~\ref{tab:opt}). The negative elevator incidence is the key change. At 12\,kn the elevators push down """ + f"{-oad['elevator_lift12_N']:.1f}" + r"""\,N with the boat at """ + f"{round(oad['pitch12'], 1) + 0.0:+.1f}" + r"""$^\circ$ of pitch, instead of pitching the boat nose-down to get there. In the simulator the boat takes off at """ + f"{oad['vto']:.2f}" + r"""\,m/s, from """ + f"{oad['tws90']:.1f}" + r"""\,kn on a beam reach and """ + f"{oad['tws60']:.1f}" + r"""\,kn at 60$^\circ$. It reaches """ + f"{oad['v12']:.2f}" + r"""\,m/s at 12\,kn, and its flying range extends to the end of the scan (6\,m/s). The original v2.0 sizes cannot be re-trimmed into the feasible set: whatever the incidences and elevator height, their static margin is at most """ + f"{OPT['v20_retrim_static_margin_mm'][1]:.1f}" + r"""\,mm, just under the 30\,mm limit. The v2.1 sizes cannot be rescued. Once the elevators push down, the main foils carry the weight plus that downforce, and in """ + f"{defl21}" + r""" of the """ + f"{n21}" + r""" re-trims tried the 40\,mm-chord wing bends past the 2\,mm limit.

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[width=\columnwidth, height=0.72\columnwidth, xlabel={Wind needed to fly, beam reach (kn)}, ylabel={Boat speed at 12\,kn (m/s)}, legend style={font=\scriptsize, at={(0.5,-0.24)}, anchor=north, legend columns=2, draw=none}]
\addplot[only marks, mark=*, mark size=0.4pt, gray!40] table[x=tws90, y=v12] {data/opt_cloud_thin.dat}; \addlegendentry{feasible designs}
\addplot[only marks, mark=*, mark size=0.5pt, blue!35] table[x=tws90, y=v12] {data/opt_cloud_robust_thin.dat}; \addlegendentry{robust, with margins}
\addplot[thick, blue] table[x=tws90, y=v12] {data/opt_front_robust.dat}; \addlegendentry{best robust trade-off}
\addplot[only marks, mark=diamond*, mark size=3pt, orange!80!black] coordinates {(""" + f"{olw['tws90']:.3f},{olw['v12']:.3f}" + r""")}; \addlegendentry{light-wind design}
\addplot[only marks, mark=triangle*, mark size=3pt, red!70!black] coordinates {(""" + f"{oad['tws90']:.3f},{oad['v12']:.3f}" + r""")}; \addlegendentry{v2.2 (adopted)}
\addplot[only marks, mark=square*, mark size=2.5pt, black] coordinates {(""" + f"{osp['tws90']:.3f},{osp['v12']:.3f}" + r""")}; \addlegendentry{speed design}
\end{axis}
\end{tikzpicture}
\caption{Foil search with the trim model: every feasible design (grey), those with operating margins that are also robust (blue), and the best robust trade-off. Up and to the left is better. The adopted design also weighs the take-off wind at 60$^\circ$, which this plot does not show.}
\label{fig:opt}
\end{figure}

\begin{table*}[t]
\centering\small
\caption{Foil sets with the trim model (flight simulator, auto trim; take-off wind to 0.01\,kn). v2.0 and v2.1 have no feasible flying trim; their speeds are hull-borne (h). v2.2 was adopted and built in CAD. The light-wind design needs the least wind among robust designs within 15\,\% of the fastest; the speed design is the fastest robust design.}
\label{tab:opt}
\resizebox{\textwidth}{!}{\begin{tabular}{lccccc}
\toprule
 & v2.0 (original) & v2.1 (first search) & v2.2 (adopted) & Light-wind design & Speed design \\
\midrule
""" + '\n'.join(f"{name} & " + ' & '.join(vals) + r" \\" for name, vals in opt_rows) + r"""
\bottomrule
\end{tabular}}
\end{table*}

The simulator interpolates the wave-resistance table, which smooths the drag hump just before take-off. Its take-off winds for v2.2 are therefore """ + f"{TOW['90'] - oad['tws90']:.2f}" + r""" and """ + f"{TOW['60'] - oad['tws60']:.2f}" + r"""\,kn below the VPP's (""" + f"{TOW['90']:.2f}" + r""" and """ + f"{TOW['60']:.2f}" + r"""\,kn at 90 and 60$^\circ$). Once the boat is flying the two agree. \noindent\textbf{Roll near take-off.} With the adopted foils the boat flies from """ + f"{RO['rows'][0]['takeoff_90']:.1f}" + r"""\,kn on a beam reach but needs """ + (f"{RO['rows'][0]['takeoff_60']:.1f}\\,kn" if RO['rows'][0]['takeoff_60'] else 'more than 25\\,kn') + r""" at 60$^\circ$ (simulator), because at take-off both wings are at their lift limit and the larger side force has to go onto the leeward hull (Section~\ref{sec:trim}). More flap travel does not help: with $\pm25^\circ$ instead of $\pm15^\circ$ the take-off winds are unchanged, because the usable lift coefficient, not the flap stop, limits the leeward wing. What does help is technique. Taken off on a beam reach and then headed up, the boat stays flying at 60$^\circ$ down to """ + (f"{RO['rows'][0]['stay_60']:.2f}\\,kn" if RO['rows'][0]['stay_60'] else '--') + r""" (\texttt{sim/roll\_options.js}). At 45$^\circ$ """ + (f"it takes off from {RO['rows'][0]['takeoff_45']:.1f}\\,kn" if RO['rows'][0]['takeoff_45'] else 'it does not take off below 25\\,kn') + (f" and stays flying down to {RO['rows'][0]['stay_45']:.2f}\\,kn." if RO['rows'][0]['stay_45'] else ', and once flying it cannot stay up below 16\\,kn.') + r"""

As with the rest of the paper, these are model predictions. The drag model sets the size of the sail-drive couple, which is why the design must also work with the couple halved or 1.5 times larger (take-off at """ + ' and '.join(f"{x['takeoff_ms']:.2f}" for x in PT['robustness'] if x['case'].startswith('couple')) + r"""\,m/s, flying to """ + ' and '.join(f"{x['flying_range_top_ms']:.2f}" for x in PT['robustness'] if x['case'].startswith('couple')) + r"""\,m/s). With laminar foil friction, the optimistic bound on the drag, it takes off at """ + f"{LAM['takeoff_ms']:.2f}" + r"""\,m/s and flies to """ + f"{LAM['flying_range_top_ms']:.2f}" + r"""\,m/s""" + (f" (limit: {LAM['limit']})" if LAM['limit'] else '') + r""". Lift near $Re=10^5$, the flap model and the wand gearing on the smaller foils are what the tow tests have to confirm, and the elevator incidence should be adjustable by at least $\pm1^\circ$ on the water.
"""
tex = tex.replace('@@OPT@@', OPT_SECTION)
b1, mi = ST['build_first_1m'], ST['mini_600']
hv_rows = '\n'.join(f"{k.split(':')[0]} & {v['RM_L_1hull']:.2f} & {v['RM_L_2hull']:.2f} & {v['drag_N']['2.0']:.3f} & {v['mass_change_g']:+.0f} & "
                    + ' / '.join(('>20' if v['pitchpole_kn'][t] is None else f"{v['pitchpole_kn'][t]:g}") for t in ('60', '90', '120')) + r" \\"
                    for k, v in HV.items())
pp1, ppm = PP['build_first_1m'], PP['mini_600']
fmt = lambda d, t: '>20' if d[t]['pitchpole_tws_kn'] is None else f"{d[t]['pitchpole_tws_kn']:g}"
STAB = r"""\subsection{Static stability and pitchpole}\label{sec:stab}
\textbf{Heel.} The transverse righting arm (Fig.~\ref{fig:gz}) comes from clipping the heeled elliptical sections of both hulls at the waterline, with the waterline height solved so displacement equals weight. The 1\,m build-first boat reaches its largest righting arm, """ + f"{b1['gz_max_mm']:.0f}" + r"""\,mm, at """ + f"{b1['gz_max_at_deg']}" + r"""$^\circ$ of heel, when the windward hull lifts. The maximum righting moment, """ + f"{b1['RM_max_Nm']:.2f}" + r"""\,N\,m, is within """ + f"{abs(1 - b1['RM_max_Nm'] / b1['RM_assumed_Nm']) * 100:.0f}" + r"""\,\% of the $Ws/2$ used in the VPP, which confirms that assumption. The boat capsizes at about """ + f"{b1['capsize_angle_deg']}" + r"""$^\circ$ (mini: """ + f"{mi['capsize_angle_deg']}" + r"""$^\circ$).

\noindent\textbf{Pitchpole.} A catamaran more often trips over its bows than capsizes sideways. Tilting the waterline bow-down and re-solving the sinkage gives the largest longitudinal righting moment the hulls can provide before the bows go under: """ + f"{b1['pitch_2hull']['RM_L_max_Nm']:.2f}" + r"""\,N\,m on both hulls and """ + f"{b1['pitch_1hull']['RM_L_max_Nm']:.2f}" + r"""\,N\,m on one hull (the windward hull flying). Setting that equal to the sails' bow-down moment gives the wind above which the sails must be eased on each point of sail. For the 1\,m boat that is """ + fmt(pp1, '60') + ' / ' + fmt(pp1, '90') + ' / ' + fmt(pp1, '120') + ' / ' + fmt(pp1, '150') + r"""\,kn at TWA 60/90/120/150$^\circ$, and for the mini """ + fmt(ppm, '60') + ' / ' + fmt(ppm, '90') + ' / ' + fmt(ppm, '120') + ' / ' + fmt(ppm, '150') + r"""\,kn. These limits sit close to the heel limits, so pitch-limited depowering was added to the VPP.

\noindent\textbf{Design iteration: bow volume.} Table~\ref{tab:bows} compares the original hull with three variants that add volume only to the forward stations, mostly above the waterline. Variant B was adopted as the v1.3 hull. It raises the one-hull pitch limit by """ + f"{(HV['B: A + fuller topsides']['RM_L_1hull'] / HV['baseline']['RM_L_1hull'] - 1) * 100:.0f}" + r"""\,\% for """ + f"{HV['B: A + fuller topsides']['mass_change_g']:.0f}" + r"""\,g and a """ + f"{(HV['B: A + fuller topsides']['drag_N']['2.0'] / HV['baseline']['drag_N']['2.0'] - 1) * 100:.1f}" + r"""\,\% drag increase at 2\,m/s. Variant C adds little more for 50\,\% more weight.

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[xlabel={Heel angle ($^\circ$)}, ylabel={Righting arm GZ (mm)}, legend pos=north east, xmin=0, xmax=90]
\addplot[thick, blue, mark=*, mark size=1pt] table[x=deg, y=gz] {data/gz_build_first_1m.dat}; \addlegendentry{1\,m build-first}
\addplot[thick, red, mark=square*, mark size=1pt] table[x=deg, y=gz] {data/gz_mini_600.dat}; \addlegendentry{0.6\,m mini}
\addplot[gray, dashed] coordinates {(0,0) (90,0)};
\end{axis}
\end{tikzpicture}
\caption{Transverse righting arm from the heeled hull geometry. It peaks when the windward hull lifts; the curve crosses zero at the capsize angle.}
\label{fig:gz}
\end{figure}

\begin{table}[t]
\centering\small
\caption{Bow-volume variants of the 1\,m hull (B adopted as v1.3). Pitchpole limits in kn at TWA 60/90/120$^\circ$.}
\label{tab:bows}
\resizebox{\columnwidth}{!}{
\begin{tabular}{lccccc}
\toprule
Variant & $RM_L$ 1 hull (N\,m) & $RM_L$ 2 hulls (N\,m) & Drag at 2\,m/s (N) & $\Delta m$ (g) & Pitchpole (kn) \\
\midrule
""" + hv_rows + r"""
\bottomrule
\end{tabular}}
\end{table}"""
tex = tex.replace('@@STAB@@', STAB)
S1, SM = STR['build_first_1m'], STR['mini_600']
OLD_MINI = structure.beam(SM['front_beam']['load_N'], 340.0, (8.0, 7.0))
rig_rows = [
    ('Side force at the heel limit (N)', f"{S1['side_force_N']:.1f}", f"{SM['side_force_N']:.1f}"),
    ('Shroud / forestay tension (N)', f"{S1['shroud_N']:.0f} / {S1['forestay_N']:.0f}", f"{SM['shroud_N']:.1f} / {SM['forestay_N']:.1f}"),
    ('Mainsheet at servo stall (N)', f"{S1['mainsheet_stall_N']:.0f}", f"{SM['mainsheet_stall_N']:.0f}"),
    ('Mast compression, sailing / stall (N)', f"{S1['mast_compression_N']['sailing']:.0f} / {S1['mast_compression_N']['servo_stall']:.0f}",
     f"{SM['mast_compression_N']['sailing']:.0f} / {SM['mast_compression_N']['servo_stall']:.0f}"),
    ('Mast Euler load (N) / safety at stall', f"{S1['mast_buckling_N']:.0f} / {S1['buckling_safety']['servo_stall']:.1f}",
     f"{SM['mast_buckling_N']:.0f} / {SM['buckling_safety']['servo_stall']:.1f}"),
    ('Front beam: MPa / mm / safety', f"{S1['front_beam']['stress_MPa']:.0f} / {S1['front_beam']['deflection_mm']:.1f} / {S1['front_beam']['safety_factor']:.1f}",
     f"{SM['front_beam']['stress_MPa']:.0f} / {SM['front_beam']['deflection_mm']:.1f} / {SM['front_beam']['safety_factor']:.1f}"),
    ('Rear beam: MPa / mm / safety', f"{S1['rear_beam']['stress_MPa']:.0f} / {S1['rear_beam']['deflection_mm']:.1f} / {S1['rear_beam']['safety_factor']:.1f}",
     f"{SM['rear_beam']['stress_MPa']:.0f} / {SM['rear_beam']['deflection_mm']:.1f} / {SM['rear_beam']['safety_factor']:.1f}"),
    ('Traveler car on its rail: uplift (N) / safety', f"{S1['traveler_car']['uplift_N']:.0f} / {S1['traveler_car']['safety_factor']:.1f}", '--'),
    ('Pod beam, 5\\,g: MPa / mm / safety', f"{S1['pod_beam']['stress_MPa']:.0f} / {S1['pod_beam']['deflection_mm']:.1f} / {S1['pod_beam']['safety_factor']:.1f}", '--'),
]
RIG = r"""\subsection{Rig and crossbeam loads}\label{sec:rigload}
The largest steady side force the sails can apply is set by the righting moment, $F = RM_{\max}/h$ with $h$ the heeling arm; beyond it the boat heels and sheds load. Carried by a mast pinned at the step and held by the windward shroud at the hounds, this force gives the shroud tension. The jib's share (by area), on a forestay with an assumed 2\,\% sag, gives the forestay tension, and the vertical components of both compress the mast. A harder case is the sheet servo at its stall torque (spec-sheet values at 4.8\,V), for example with the sheet held in against a stop. The mast is checked for Euler buckling between step and hounds. Each crossbeam is checked as a simply supported tube loaded at mid-span. On the 1\,m boat the mainsheet runs from the traveler car up to the boom and back (the loop that keeps the traveler from pulling on it), so the boom, the car and the rear beam carry twice the tail tension. With the tail 15\,mm from the servo shaft this failed the factor-of-2 rule (front beam 1.7, mast 2.0); the tail now attaches 25\,mm from the shaft. The printed traveler car is checked the same way: its lips under the rail head bend as cantilevers, with an assumed 25\,MPa bending strength for printed PETG. On the mini, the box levers the sheet load onto both beams. Table~\ref{tab:rigload} lists the results. $E = 70$\,GPa and a bending strength of 300\,MPa are assumed for the carbon tubes, since no values are published for the tubes used.

\begin{table}[h]
\centering\small
\caption{Rig and crossbeam loads (sails at the heel limit; ``stall'' adds the sheet servo at stall torque).}
\label{tab:rigload}
\resizebox{\columnwidth}{!}{\begin{tabular}{lcc}
\toprule
 & 1\,m build-first & Mini \\
\midrule
""" + '\n'.join(f"{a} & {b} & {c} \\\\" for a, b, c in rig_rows) + r"""
\bottomrule
\end{tabular}}
\end{table}

The sailing loads are small: the sheet servos, not the wind, set the structural load case. With its first 8\,x\,7\,mm beams (0.5\,mm wall), the mini's front beam reached a safety factor of only """ + f"{OLD_MINI['safety_factor']:.1f}" + r""" in the stall case and deflected """ + f"{OLD_MINI['deflection_mm']:.1f}" + r"""\,mm. It now uses 10\,x\,8\,mm tube, which costs \$1.05 less, for 18\,g more."""
tex = tex.replace('@@RIG@@', RIG)
open(os.path.join(HERE, 'RC_Catamaran_Paper.tex'), 'w').write(tex)
print('ok', {k: (round(v[0], 1), round(v[1], 2), round(v[2], 2)) for k, v in STRUCT.items()}, 'Lcase', round(Lcase, 1))
