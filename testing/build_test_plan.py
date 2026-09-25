"""Generates the tow-test plan for the 1 m foiling boat (LaTeX, compile with tectonic).
Every prediction comes from analysis/vpp.py (the flying trim, fly_trim, and the hull-borne branch) for the foils in the
CAD model, and from the foil test outputs (analysis/foil_checks.json). Pass bands are engineering judgment, stated as such.
python3 testing/build_test_plan.py && tectonic testing/RC_Foiling_Cat_Tow_Test_Plan.tex"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
import vpp

vpp.configure()
CAD = json.load(open(os.path.join(ROOT, 'analysis', 'cad_data.json')))
FC = json.load(open(os.path.join(ROOT, 'analysis', 'foil_checks.json')))
PH = json.load(open(os.path.join(ROOT, 'analysis', 'pitch_heave_results.json')))
TOW = json.load(open(os.path.join(ROOT, 'analysis', 'takeoff_wind.json')))
Z_MAST_FOOT = 0.125                      # m, boat frame (CAD: Wing Mast bottom)
SPEEDS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
H_REF = vpp.WAND_L * math.sin(math.radians(vpp.WAND_PHI0_DEG))


def boat(z_tow):
    """The foiling boat towed from height z_tow: the tow force takes the place of the sail drive, so the bow-down
    couple is F (z_tow - z_drag). No side force, so no heel."""
    b = vpp.Boat('foiling', CAD)
    b.ce_z = z_tow
    b.fly_range()
    return b


def predictions(b):
    rows = []
    for V in SPEEDS:
        if b.vto and b.vto <= V <= b.vfly_max:
            t = b.fly_trim(V)
            rows.append(dict(V=V, mode='flying', F=t['R'], pitch=math.degrees(t['theta']), flap=math.degrees(t['delta']),
                             bow=(t['hp'] - H_REF) * 1000, el=t['elD'] * 1000))
        else:
            R, info = b.resistance(V, 0.0)
            rows.append(dict(V=V, mode=info['mode'], F=R, lift=info.get('foil_lift', 0.0) / b.W * 100))
    return rows


sg = lambda x, d=1: '$' + f"{round(x, d) + 0.0:+.{d}f}" + '$'
B_CE, B_FOOT = boat(vpp.Boat('foiling', CAD).ce_z), boat(Z_MAST_FOOT)
P_CE, P_FOOT = predictions(B_CE), predictions(B_FOOT)
ce_above_foot = (B_CE.ce_z - Z_MAST_FOOT) * 1000


def table(rows):
    out = []
    for r in rows:
        if r['mode'] == 'flying':
            out.append(f"{r['V']:.1f} & flying & {r['F']:.1f} & {sg(r['pitch'])} & {sg(r['flap'])} & {sg(r['bow'], 0)} & {r['el']:.0f} \\\\")
        else:
            out.append(f"{r['V']:.1f} & {'hull-borne' if r['mode'] == 'displacement' else 'foils lifting'} ({r['lift']:.0f}\\,\\% of weight) & {r['F']:.1f} & -- & $+15$ (stop) & -- & -- \\\\")
    return '\n'.join(out)


dpitch = [(a['V'], a['pitch'] - b['pitch']) for a, b in zip(P_CE, P_FOOT) if a['mode'] == b['mode'] == 'flying']
settle = [x['settling_s'] for x in FC['heave_time_domain']]
osc = [m['freq_hz'] for r in PH['rows'] for m in r['wand']['modes'] if m['freq_hz'] > 0]
tex = r"""\documentclass[11pt]{article}
\usepackage[letterpaper,margin=0.9in]{geometry}
\usepackage{booktabs,amsmath,siunitx,xurl,graphicx,caption}
\usepackage[hidelinks]{hyperref}
\title{\textbf{Tow-Test Plan for the 1\,m Foiling Catamaran (""" + vpp.FOIL_VERSION + r""" foils)}}
\author{Filip Maleev}
\date{September 2026}
\begin{document}
\maketitle

\section*{Purpose}
The foiling version has only been analysed, not tested. This plan checks the numbers the design depends on before the boat sails on its foils: take-off speed, drag, pitch trim, flap angle and ride height, and whether the wand holds height without oscillating. Every prediction below comes from the same model as the paper (\texttt{analysis/vpp.py}, flying trim in heave and pitch) for the """ + vpp.FOIL_VERSION + r""" foils in the CAD model. The pass bands are engineering judgment, not model outputs.

Towing replaces the sails. The tow force equals the drag, just as the sail drive does, and the height of the tow point sets the bow-down couple. Two tow points are used:
\begin{itemize}
\item \textbf{A: at the sail's centre of effort}, a bridle on the mast """ + f"{ce_above_foot:.0f}" + r"""\,mm above its foot. This reproduces the couple the sails make, so the boat should trim as it would under sail (without heel).
\item \textbf{B: at the mast foot.} The couple is much smaller.
\end{itemize}
The pitch difference between A and B measures the couple directly, which is the model's largest uncertainty.

\section*{1. Bench checks (before the water)}
\begin{enumerate}
\item \textbf{Weight and balance.} Fully rigged without sails but with sails, battery and radio installed: """ + f"{CAD['foiling']['mass_g']:.0f}" + r"""\,g. Balance point (centre of gravity) """ + f"{CAD['foiling']['lcg_mm']:.0f}" + r"""\,mm forward of the transoms. Move the battery to correct it.
\item \textbf{Foil angles}, measured with a phone inclinometer against the deck: main wing $""" + f"{vpp.INC_MAIN_DEG:+g}" + r"""^\circ$, elevators $""" + f"{vpp.INC_EL_DEG:+g}" + r"""^\circ$ (nose down is negative).
\item \textbf{Wand and flap.} With the wand at """ + f"{vpp.WAND_PHI0_DEG:.0f}" + r"""$^\circ$ below the deck line (the design ride height, hinge """ + f"{H_REF * 1000:.0f}" + r"""\,mm above the water), the flap should be at $0^\circ$. Each degree of wand should move the flap """ + f"{vpp.GEAR:g}" + r"""$^\circ$ (wand down, flap down). Travel to both $\pm""" + f"{vpp.FLAP_TRAVEL_DEG:.0f}" + r"""^\circ$ stops without binding.
\item \textbf{Free play.} Less than about $0.5^\circ$ at the flap when the wand is held still (judgment: play acts like a dead band in the height control).
\end{enumerate}

\section*{2. Equipment}
A tow line of 3--5\,m with a weak link; a hanging scale with a 1--2\,kg range and 5\,g resolution in the line, filmed so the reading can be taken frame by frame; phone GPS for speed (average a steady 10\,s run); a camera filming the boat side-on from the tow vehicle, with a 50\,mm grid taped to the hull, for pitch and ride height; a bridle for tow point A. For speeds up to about 2\,m/s a kayak works; above that, a bicycle on a straight towpath with a short outrigger pole, or a slow powerboat. Wear a buoyancy aid, and stay away from boat traffic.

\section*{3. Tow runs and predictions}
Run each speed for at least 10\,s after it settles, first at tow point A, then at B. Record the tow force, speed, pitch and bow height from the video, and whether the hulls are clear. Predictions (no side force, no heel):

\begin{table}[h]
\centering\small
\caption*{\textbf{Tow point A (sail centre of effort).} Take-off at """ + f"{B_CE.vto:.2f}" + r"""\,m/s. Pitch nose up $+$; flap down $+$; bow height relative to the design ride height; elevator depth at its quarter chord.}
\resizebox{\textwidth}{!}{\begin{tabular}{llccccc}
\toprule
Speed (m/s) & State & Tow force (N) & Pitch ($^\circ$) & Flap ($^\circ$) & Bow (mm) & Elevator depth (mm) \\
\midrule
""" + table(P_CE) + r"""
\bottomrule
\end{tabular}}
\end{table}

\begin{table}[h]
\centering\small
\caption*{\textbf{Tow point B (mast foot).} Take-off at """ + f"{B_FOOT.vto:.2f}" + r"""\,m/s.}
\resizebox{\textwidth}{!}{\begin{tabular}{llccccc}
\toprule
Speed (m/s) & State & Tow force (N) & Pitch ($^\circ$) & Flap ($^\circ$) & Bow (mm) & Elevator depth (mm) \\
\midrule
""" + table(P_FOOT) + r"""
\bottomrule
\end{tabular}}
\end{table}

\noindent Predicted pitch difference, A minus B: """ + ', '.join(f"{sg(d)}$^\\circ$ at {v:.1f}\\,m/s" for v, d in dpitch) + r""".

\section*{4. Disturbance test}
At 3 and 4\,m/s (tow point A), push the bow down about 20\,mm with a pole and let go, or tow across a small wake. The model predicts the height returns within """ + f"{min(settle):.2f}--{max(settle):.2f}" + r"""\,s with no overshoot (heave alone) and a coupled heave--pitch mode at """ + f"{min(osc):.1f}--{max(osc):.1f}" + r"""\,Hz that is well damped (damping ratio at least """ + f"{PH['min_damping']:.2f}" + r"""). A visible oscillation that keeps going (porpoising) is a failure.

\section*{5. Roll near take-off (under sail)}
Straight towing does not load the foils sideways, so it cannot test roll. Near take-off both main wings are at their lift limit, and the leeward hull has to carry what the foils cannot of the sails' heeling moment (the paper, Section 3.4). The model has the boat flying from """ + f"{TOW['90']:.1f}" + r"""\,kn on a beam reach but only from """ + (f"{TOW['60']:.1f}" if TOW['60'] else 'over 16') + r"""\,kn at 60$^\circ$, where the side force is larger. Under sail at 60$^\circ$, note the wind at which the leeward hull stops touching after the windward one lifts. Much earlier than predicted means the foils have more roll authority than modelled; much later points to the flap limit or to foil lift at low speed.

\section*{6. Pass bands and what to change}
Pass bands (judgment): take-off speed within $\pm15\,\%$ of the prediction; tow force within $\pm30\,\%$; pitch within $\pm1^\circ$; flap within $\pm3^\circ$; no sustained oscillation. The model gives the direction and size of each correction:
\begin{itemize}
\item \textbf{Pitch off at speed:} change the elevator angle. Pitch follows it one for one: each $0.5^\circ$ more elevator nose-down brings the boat about $0.5^\circ$ more nose-down.
\item \textbf{Flap near a stop at speed:} change the main-wing angle. The flap compensates by about $1/\tau=""" + f"{1 / vpp.FLAP_TAU:.1f}" + r"""^\circ$ per degree of wing ($\tau=""" + f"{vpp.FLAP_TAU:.3f}" + r"""$ is the flap effectiveness).
\item \textbf{Take-off later than predicted:} foil lift is lower than modelled (the sensitivity study with foil lift $-20\,\%$ gives a later take-off). Add $0.5^\circ$ of main-wing angle.
\item \textbf{Pitch difference A$-$B much larger or smaller than predicted:} the drag model, and so the couple, is off. Re-run \texttt{analysis/pitch\_trim.py} with \texttt{vpp.COUPLE\_FACTOR} fitted to the measured difference, then re-check the elevator angle.
\item \textbf{Porpoising:} reduce the wand gearing (a shorter horn on the bellcrank), then re-check the height hold.
\item \textbf{Tow force much higher than predicted:} look for flow separation or ventilation at the strut roots and the flap gaps before changing the foils.
\end{itemize}

\section*{7. Data sheet}
\begin{tabular}{lllllll}
\toprule
Run & Tow point & Speed (m/s) & Force (N) & Pitch ($^\circ$) & Bow (mm) & Notes \\
\midrule
""" + '\n'.join(f"{i} & & & & & & \\\\[6pt]" for i in range(1, 15)) + r"""
\bottomrule
\end{tabular}
\end{document}
"""
open(os.path.join(HERE, 'RC_Foiling_Cat_Tow_Test_Plan.tex'), 'w').write(tex)
print('A: take-off', round(B_CE.vto, 3), [(r['V'], r['mode'], round(r['F'], 2), round(r.get('pitch', 0), 2)) for r in P_CE])
print('B: take-off', round(B_FOOT.vto, 3), [(r['V'], r['mode'], round(r['F'], 2), round(r.get('pitch', 0), 2)) for r in P_FOOT])
