"""One-page project summary (LaTeX, compile with tectonic). Every number is read from the analysis outputs.
python3 summary/build_summary.py && tectonic summary/RC_Catamaran_Project_Summary.tex"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
import vpp

J = lambda *p: json.load(open(os.path.join(ROOT, *p)))
CAD, VR, TOW = J('analysis', 'cad_data.json'), J('analysis', 'vpp_results.json'), J('analysis', 'takeoff_wind.json')
OPT, RO, PH, TS = J('sim', 'optimization_results.json'), J('sim', 'roll_options.json'), J('analysis', 'pitch_heave_results.json'), J('analysis', 'takeoff_sim_results.json')
FC, DC, MINI, RES = J('analysis', 'foil_checks.json'), J('analysis', 'design_checks.json'), J('mini', 'mini_results.json'), J('analysis', 'vpp_results.json')
cost = lambda n: sum(float(r['total_usd']) for r in csv.DictReader(open(os.path.join(ROOT, 'bom', n + '.csv'))))
V = lambda cfg, twa, tws: [x for x in VR['vpp'][cfg][str(twa)] if x['tws_kn'] == tws][0]['V']
ad, v21 = OPT['adopted'], OPT['v21']
rules_dc = DC if isinstance(DC, list) else DC.get('rules', [])
n_fc, n_dc = f"{sum(r['ok'] for r in FC['rules'])} of {len(FC['rules'])}", f"{sum(r['ok'] for r in rules_dc)} of {len(rules_dc)}"
ro = RO['rows'][0]
wig = RES['wigley_michell_Cw_x1e3']

tex = r"""\documentclass[10pt]{article}
\usepackage[letterpaper,margin=0.55in]{geometry}
\usepackage{graphicx,xcolor,enumitem,multicol}
\usepackage[hidelinks]{hyperref}
\definecolor{navy}{HTML}{1B2F4B}\definecolor{sea}{HTML}{2E7DB5}
\setlist{nosep,leftmargin=1.1em}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\newcommand{\head}[1]{\vspace{5pt}{\color{navy}\large\bfseries #1}\par\vspace{2pt}}
\begin{document}
{\color{navy}\LARGE\bfseries A 1\,m RC Foiling Beach Catamaran: Design, Analysis and Build Plan}\par
\vspace{2pt}{\large Filip Maleev \quad|\quad Colorado College, Mathematics \quad|\quad September 2026}\par
\vspace{6pt}
\begin{minipage}[t]{0.49\textwidth}\vspace{0pt}\includegraphics[width=\linewidth]{../images/build_first_v1.4.png}\end{minipage}\hfill
\begin{minipage}[t]{0.49\textwidth}\vspace{0pt}\includegraphics[width=\linewidth]{../images/foiling_""" + vpp.FOIL_VERSION + r""".png}\end{minipage}\par
{\small Build-first version (daggerboards) and foiling version (""" + vpp.FOIL_VERSION + r""" L-foils, wand-driven flaps), Autodesk Fusion.}
\begin{multicols}{2}
\head{Goal}
A radio-controlled catamaran that follows full-size beach cats (Hobie~16, Nacra~17), can be 3D-printed and built from off-the-shelf RC parts, can fly on hydrofoils, and whose behaviour is predicted before it is built.

\head{What was done}
\begin{itemize}
\item \textbf{Parametric CAD} in Autodesk Fusion, driven through its API: 1\,m hulls printed as sealed PETG segments, a beach-cat rig trimmed by three sliders, two appendage options, a 0.6\,m first build, clearance sweeps, and mass and inertia exported for analysis.
\item \textbf{Velocity prediction}: ITTC-57 friction, Michell thin-ship wave resistance with catamaran interference (checked on the Wigley hull), foil and appendage drag, and sails eased for heel and bow-down limits.
\item \textbf{Foils}: lifting-line wings with wand-driven flaps; flying trim in heave and pitch, roll authority, coupled heave--pitch stability, and a time-domain take-off simulation.
\item \textbf{Flight simulator} (web page, same physics) and a search of """ + f"{OPT['grid_size']:,}" + r""" foil designs under limits on stress, deflection, Reynolds number, pitch stability and damping, with depth margins and robustness checks.
\item \textbf{Build plan}: costed parts lists (every price read from a retailer page), a build manual for the 0.6\,m boat, and a tow-test plan for the foils.
\end{itemize}

\head{Findings}
\begin{itemize}
\item Fixed-incidence foils have no heave stability; a wand-driven flap on each foil makes heave and pitch stable (least damping ratio """ + f"{PH['min_damping']:.2f}" + r""").
\item The first optimized foils (v2.1) would not have flown: at speed the sail drive's bow-down couple makes the elevators push down, and at $+4^\circ$ they pitch the boat nose-down until they leave the water. The adopted """ + vpp.FOIL_VERSION + r""" foils set the elevators at $""" + f"{ad['einc']:+g}" + r"""^\circ$ and fly level.
\item Near take-off the foils have no roll authority left, so flying at 60$^\circ$ needs """ + (f"{TOW['60']:.1f}" if TOW['60'] else '--') + r"""\,kn against """ + f"{TOW['90']:.1f}" + r"""\,kn on a beam reach; taking off on a reach and heading up keeps it flying at 60$^\circ$ from """ + (f"{ro['stay_60']:.1f}" if ro['stay_60'] else '--') + r"""\,kn.
\item Predicted speed on a beam reach: build-first """ + f"{V('displacement', 90, 8):.2f}" + r"""\,m/s in 8\,kn; foiling """ + f"{V('foiling', 90, 12):.2f}" + r"""\,m/s in 12\,kn.
\end{itemize}

\head{Deliverables}
Technical paper, A0 poster, build manual with 1:1 sail patterns, tow-test plan, interactive simulator, STEP/Fusion models and print-ready STLs. Checks in the code: """ + n_fc + r""" foil rules and """ + n_dc + r""" design rules pass.

\head{Cost}
0.6\,m first build \$""" + f"{cost('bom_mini'):.2f}" + r"""; 1\,m build-first boat \$""" + f"{cost('bom_full_build_first'):.2f}" + r"""; foiling kit \$""" + f"{cost('bom_foiling_kit_v2'):.2f}" + r""" (September 2026 retailer prices, before shipping and tax).

\head{Next}
Build and GPS-log the 0.6\,m boat and compare with its predicted """ + f"{[x for x in MINI['vpp']['90'] if x['tws_kn'] == 8][0]['V']:.1f}" + r"""\,m/s in 8\,kn; build the 1\,m boat; tow-test the foils against the plan's predictions, then fly.
\end{multicols}
\vfill
{\footnotesize\color{black!65} All performance figures are model predictions; nothing has been tested on the water yet. Developed with Claude (Anthropic) as an AI engineering assistant for the CAD scripting, analysis code and documents.}
\end{document}
"""
open(os.path.join(HERE, 'RC_Catamaran_Project_Summary.tex'), 'w').write(tex)
print('written')
