"""Generates the RC Mini Cat 600 build manual (LaTeX) from the analysis + BOM outputs, then compile with tectonic."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
R = json.load(open(os.path.join(ROOT, 'mini', 'mini_results.json')))
D = json.load(open(os.path.join(HERE, 'manual_data.json')))
ST = R['statics']
bom = list(csv.DictReader(open(os.path.join(ROOT, 'bom', 'bom_mini.csv'))))
opt = list(csv.DictReader(open(os.path.join(ROOT, 'bom', 'bom_mini_options.csv'))))
full = list(csv.DictReader(open(os.path.join(ROOT, 'bom', 'bom_full_build_first.csv'))))
foil = list(csv.DictReader(open(os.path.join(ROOT, 'bom', 'bom_foiling_kit_v2.csv'))))
PL = json.load(open(os.path.join(HERE, 'print_list.json')))
MC = json.load(open(os.path.join(ROOT, 'mini', 'cad_data_mini.json')))
STB = json.load(open(os.path.join(ROOT, 'analysis', 'stability_results.json')))['mini_600']
PPM = json.load(open(os.path.join(ROOT, 'analysis', 'pitchpole_results.json')))['mini_600']
pg = lambda n: PL[n]['g']
sz = lambda n: ' x '.join(str(v) for v in PL[n]['size'])
PETG_USED = sum(v['g'] for k, v in PL.items() if 'Seg' in k or 'Half' in k) + 2 * (pg('Rudder Blade Port') + pg('Gudgeon Port') + pg('Daggerboard Port')) + pg('Winch Drum')
HULL_G = MC['displacement']['by_component_g']['Hull Port']
pp = lambda t: PPM[str(t)]['pitchpole_tws_kn']


def esc(s):
    return (s.replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('%', r'\%').replace('#', r'\#')
             .replace('_', r'\_').replace('$', r'\$'))


def money(x):
    return r'\$' + f'{float(x):,.2f}'


def bom_rows(rows):
    out = []
    for x in rows:
        out.append(f"{esc(x['group'])} & {esc(x['item'])} & {esc(x['use'])} & {x['qty']} & {money(x['unit_usd'])} & {money(x['total_usd'])} \\\\")
    return '\n'.join(out)


def total(rows):
    return sum(float(x['total_usd']) for x in rows)


def groups(rows):
    g = {}
    for x in rows:
        g[x['group']] = g.get(x['group'], 0) + float(x['total_usd'])
    return g


def sources(rows):
    seen, out = set(), []
    for x in rows:
        if x['url'] in seen:
            continue
        seen.add(x['url'])
        out.append(f"\\item {esc(x['source'])}: \\url{{{x['url']}}}")
    return '\n'.join(out)


def vpp_table():
    lines = []
    for i, tws in enumerate(range(2, 15, 2)):
        cells = []
        for twa in ('60', '90', '105'):
            row = [x for x in R['vpp'][twa] if x['tws_kn'] == tws][0]
            cells.append(f"{row['V']:.2f}" + ('*' if row.get('depowered') else ''))
        lines.append(f"{tws} & " + ' & '.join(cells) + r' \\')
    return '\n'.join(lines)


rig, drum = D['rig'], D['drum']
g = groups(bom)
T = total(bom)
PRINT = [  # part, qty, g each, size (mm), orientation / notes
    ('Hull Port Seg 1 / 2 / 3', '1 each', f"{pg('Hull Port Seg 1'):.0f} / {pg('Hull Port Seg 2'):.0f} / {pg('Hull Port Seg 3'):.0f}", sz('Hull Port Seg 2'), 'stand on the joint (bulkhead) face'),
    ('Hull Stbd Seg 1 / 2 / 3', '1 each', f"{pg('Hull Stbd Seg 1'):.0f} / {pg('Hull Stbd Seg 2'):.0f} / {pg('Hull Stbd Seg 3'):.0f}", sz('Hull Stbd Seg 2'), 'mirror of port'),
    ('Box Half 1 / 2', '1 each', f"{pg('Box Half 1'):.0f} / {pg('Box Half 2'):.0f}", sz('Box Half 1'), 'open side up'),
    ('Box Lid Half 1 / 2', '1 each', f"{pg('Box Lid Half 1'):.0f} / {pg('Box Lid Half 2'):.0f}", sz('Box Lid Half 1'), 'flat'),
    ('Daggerboard', '2', f"{pg('Daggerboard Port'):.0f}", '200 x 36 x 4.3', 'flat; 3 perimeters, 40 % infill'),
    ('Rudder Blade', '2', f"{pg('Rudder Blade Port'):.0f}", '130 x 27 x 3.2', 'flat; 3 perimeters, 40 % infill'),
    ('Gudgeon', '2', f"{pg('Gudgeon Port'):.0f}", '18 x 10 x 10', 'any'),
    ('Winch Drum (30 / 16.2 mm)', '1', f"{pg('Winch Drum'):.0f}", '34 x 34 x 10.4', 'large flange down'),
]
print_rows = '\n'.join(f"{esc(a)} & {b} & {c} & {d} & {esc(e)} \\\\" for a, b, c, d, e in PRINT)

tex = r"""\documentclass[11pt]{article}
\usepackage[letterpaper,margin=0.9in]{geometry}
\usepackage{graphicx,booktabs,longtable,tabularx,array,enumitem,xcolor,fancyhdr}
\usepackage{xurl}
\usepackage[hidelinks]{hyperref}
\usepackage{helvet}\renewcommand{\familydefault}{\sfdefault}
\definecolor{accent}{HTML}{1F4E79}
\setlist{itemsep=2pt,topsep=3pt}
\pagestyle{fancy}\fancyhf{}\lhead{\small RC Mini Cat 600: Build Manual}\rhead{\small F. Maleev}\cfoot{\small\thepage}
\newcommand{\step}[1]{\subsection*{\color{accent}#1}}
\newcommand{\chk}[1]{\par\noindent\textbf{Check:} #1\par}
\begin{document}
\begin{titlepage}
\centering
{\Huge\bfseries RC Mini Cat 600\par}\vspace{4pt}
{\Large Build Manual and Costed Parts List\par}\vspace{6pt}
{\large A simplified 600\,mm version of the RC Foiling Catamaran project\par}\vspace{14pt}
\includegraphics[width=0.78\textwidth]{../images/mini_iso.png}\par\vspace{10pt}
\begin{tabular}{ll}
\toprule
Length / overall beam & 600 mm / 394 mm \\
Sailing mass (estimate) & """ + f"{ST['mass_g']:.0f}" + r""" g \\
Sail area (main + jib) & """ + f"{ST['sail_area_m2']:.3f}" + r""" m$^2$ \\
Radio & 2 channels used: rudder + one sail winch \\
Parts cost (USD, Sep 2026) & \textbf{""" + money(T) + r"""} \\
\bottomrule
\end{tabular}\par\vfill
{\large Filip Maleev\par September 2026\par}
\end{titlepage}

\section{What you are building}
The Mini Cat is the smallest step toward the 1\,m RC catamaran: the same hull lines (scaled 0.6 in length and 0.68 in section), the same beach-cat sail plan (square-top main with 3 full-length battens, jib on a forestay bridle), and the same printed-hull construction (0.8\,mm PETG skin, every print segment a sealed compartment). It keeps what matters for learning to build and sail the big boat and drops what makes the big boat hard.

\begin{center}
\begin{tabularx}{\textwidth}{>{\raggedright}p{3.3cm}XX}
\toprule
& \textbf{1\,m boat (build-first v1.2)} & \textbf{Mini Cat 600 (this manual)} \\
\midrule
Sail controls & 3 servos: jib sheet, traveler, mainsheet tension & 1 winch pulls both sheets on a stepped drum \\
Mast & rotating wing mast & fixed 6\,mm carbon tube \\
Main battens & 8 & 3 \\
Mainsheet & traveler car on the rear beam & fixed fairlead on the box lid \\
Hull pieces to print & 10 (5 per hull) & 6 (3 per hull) \\
Radio channels used & 4 & 2 \\
Parts cost & """ + money(total(full)) + r""" & """ + money(T) + r""" \\
\bottomrule
\end{tabularx}
\end{center}

\subsection*{Predicted numbers (from the project's analysis code; not yet measured on the water)}
\begin{itemize}
\item Floats with the hulls """ + f"{ST['hull_draft_mm']:.0f}" + r"""\,mm deep and """ + f"{ST['freeboard_mid_mm']:.0f}" + r"""\,mm of freeboard at mid-length; level trim (centre of buoyancy """ + f"{ST['lcb_mm']:.0f}" + r"""\,mm, centre of gravity """ + f"{ST['lcg_mm']:.0f}" + r"""\,mm from the transom).
\item Each hull alone could float """ + f"{ST['one_hull_reserve']:.2f}" + r""" times the boat's weight (design target 2 or more).
\item Speed on a beam reach: """ + f"{[x for x in R['vpp']['90'] if x['tws_kn']==4][0]['V']:.2f}" + r"""\,m/s in 4\,kn of wind, """ + f"{[x for x in R['vpp']['90'] if x['tws_kn']==8][0]['V']:.2f}" + r"""\,m/s in 8\,kn. The rig must be eased (depowered) above about 8\,kn close-reaching and 11\,kn on a beam reach.
\item Steering: at most """ + f"{max(x['rudder_angle_deg'] for x in R['rudder']):.1f}" + r"""$^\circ$ of rudder is needed of the """ + f"{R['rudder_throw_deg']:.1f}" + r"""$^\circ$ the linkage gives, leaving at least """ + f"{min(x['stall_margin'] for x in R['rudder'])*100:.0f}" + r"""\,\% margin before the rudders stall.
\end{itemize}

\section{What it costs}
\begin{center}
\begin{tabular}{lr}
\toprule
\textbf{Group} & \textbf{Cost} \\
\midrule
""" + '\n'.join(f"{esc(k)} & {money(v)} \\\\" for k, v in g.items()) + r"""
\midrule
\textbf{Total parts} & \textbf{""" + money(T) + r"""} \\
\bottomrule
\end{tabular}
\end{center}
Prices were read on the retailers' pages on 23 September 2026 and re-checked on 24 September 2026 (links in Appendix C). Not included: shipping (HobbyTown charges a \$3.99 flat rate; other stores vary), sales tax, a NiMH charger for the eneloop cells, the 3D printer, paint, and hand tools. The FS-i6X radio is the largest single item and is reused unchanged for the 1\,m boat.

\noindent Options: """ + '; '.join(f"{esc(x['item'])} ({money(x['total_usd'])}, {esc(x['use'])})" for x in opt) + r""".

\section{Parts list}
{\small
\begin{longtable}{p{1.5cm}p{4.3cm}p{5.0cm}cp{1.2cm}p{1.2cm}}
\toprule
\textbf{Group} & \textbf{Item} & \textbf{Used for} & \textbf{Qty} & \textbf{Unit} & \textbf{Total} \\
\midrule\endhead
""" + bom_rows(bom) + r"""
\midrule
& \textbf{Total} & & & & \textbf{""" + money(T) + r"""} \\
\bottomrule
\end{longtable}}

\subsection*{Tools and shop supplies (assumed on hand)}
3D printer with a 220\,mm bed that prints PETG; hobby knife and a steel rule; drill bits 1.2, 1.5, 2.5 and 3.2\,mm (a pin vise is enough); side cutters and round-nose pliers for bending music wire; 240-grit sandpaper; masking tape; a fine-tip soldering iron or a hot needle to melt clean holes in the sailcloth; small screwdrivers for servo screws; a bucket or sink for leak tests; a kitchen scale.

\section{Printing}
Settings used for the design mass: PETG, 0.4\,mm nozzle, 0.2\,mm layers, \textbf{2 perimeters (0.8\,mm walls)} for hulls, box and lid, 5 top and 5 bottom layers, \textbf{0\,\% infill} for the hull segments (they are closed shells: each segment prints as a sealed compartment ending in half of a 2\,mm bulkhead). Rudders, daggerboards and the drum are solid parts: 3 perimeters and 40\,\% infill. About """ + f"{PETG_USED:.0f}" + r"""\,g of the 1\,kg spool is used.
\begin{center}
{\small
\begin{tabular}{lllll}
\toprule
\textbf{Part} & \textbf{Qty} & \textbf{g each} & \textbf{Size (mm)} & \textbf{Orientation / notes} \\
\midrule
""" + print_rows + r"""
\bottomrule
\end{tabular}}
\end{center}
Files: \texttt{mini/stl/} (STL, one file per part), \texttt{mini/cad/RC\_Mini\_Cat\_600.step} and \texttt{.f3d} (full assembly).

\section{Build steps}
\begin{center}\includegraphics[width=0.55\textwidth]{../images/mini_layout_top.png}\\ \small Layout from above (lid and sails hidden): mast step, winch with stepped drum, battery, receiver, rudder servo, pushrod to the tie bar.\end{center}

\step{1. Hulls}
\begin{enumerate}
\item Sand the joint faces of the three segments of each hull flat on sandpaper laid on a table.
\item Dry-fit: the segments must line up on the outside. Epoxy segment 1 to 2 and 2 to 3 face to face. Hold them against a straight edge (a steel rule taped to the table) while the epoxy cures.
\item Leak test: push each hull under water for 30 seconds. A stream of bubbles marks a leak: dry, then seal it with a drop of CA or epoxy. Because every segment is its own sealed compartment, a small leak floods only one segment.
\item Drill the chainplate eye: a 1.5\,mm hole fore-aft through the small boss on the deck, """ + f"{rig['main_fairlead_x_mm']*0+360:.0f}" + r"""\,mm from the transom. Drill a 1.2\,mm hole into each bow tip and epoxy in a small loop of 0.047\,in music wire for the bridle.
\end{enumerate}
\chk{each finished hull weighs about """ + f"{HULL_G:.0f}" + r"""\,g (design value including glue) and floats level.}

\step{2. Crossbeams and frame}
\begin{enumerate}
\item Cut the 10\,mm carbon tube into two 360\,mm beams (score around with a knife, then snap; wear a mask when sanding carbon).
\item Epoxy both beams into the sockets of one hull. Slide the other hull on, lay the frame on a flat table and measure the two diagonals (front-left beam end to rear-right, and the reverse). Shift until they are equal within 1\,mm, then epoxy the second hull.
\end{enumerate}
\chk{hull centre lines are 340\,mm apart at both beams.}

\step{3. Rudders and steering linkage}
\begin{enumerate}
\item Drill a 3.2\,mm hole down the pivot line of each rudder blade, 6.75\,mm behind the leading edge (25\,\% of the 27\,mm chord). This balanced pivot keeps the servo load tiny.
\item Push a 0.125\,in music-wire stock through each blade and its gudgeon, epoxy the blade to the wire (not the gudgeon), and epoxy the gudgeon to the transom.
\item Bend two tiller arms from 0.093\,in wire: 20.75\,mm from the stock to the tie-bar hole. Keep the arms level, about 6\,mm above the deck, so they clear it at full rudder. Join them with a straight 0.093\,in tie bar at the transoms so the rudders stay parallel.
\item Run a 0.047\,in pushrod from the rudder servo horn (hole 10\,mm from the centre) through the slot in the rear wall of the box to the middle of the tie bar, using the Du-Bro clevis at the servo end.
\end{enumerate}
\chk{with the servo centred both rudders point straight; full servo travel gives about $\pm$""" + f"{R['rudder_throw_deg']:.0f}" + r"""$^\circ$ of rudder.}

\step{4. Electronics box}
\begin{enumerate}
\item Epoxy the two box halves together, and separately the two lid halves.
\item Lower the sail winch into the well between the front rails (output shaft up) until its mounting ears rest on the rails, and set the MG90S between the rear rails the same way. Lead each servo wire out sideways through the notch at the foot of a rail. Drill 1.5\,mm pilot holes through the ear holes and fix both servos with the screws supplied with them.
\chk{each case hangs from its ears, clear of the floor. The rails are drawn from the Feetech FS5115M drawing because JX does not publish the winch's ear height: if the winch case touches the bottom of the well before its ears reach the rails, put a shim (a scrap of 1\,mm plastic) under each ear.}
\item Put four charged eneloop AA cells in the Traxxas holder and set it in the battery cradle; stick the receiver on the floor between the rudder servo and the battery with double-sided tape.
\item Plug in: rudder servo to \textbf{CH1} (right stick, self-centring); sail winch to \textbf{CH3} (left stick, which stays where you leave it); battery lead to a spare channel (for example CH6). Keep both receiver antennas straight and near the top of the box.
\item Glue the printed stepped drum to the winch's round horn and screw it on.
\item Snap the box onto the two beams (the saddles clip over the 10\,mm tubes). Seal the lid seam with electrical tape before sailing.
\end{enumerate}

\step{5. Mast and standing rigging}
\begin{enumerate}
\item Cut the 6\,mm tube to """ + f"{rig['mast_length_mm']:.0f}" + r"""\,mm. Plug the top with epoxy. Mark the hounds (where the stays attach) """ + f"{rig['hounds_above_mast_foot_mm']:.0f}" + r"""\,mm above the mast foot and whip a tight binding of line there, glued with CA.
\item Stand the mast in the socket on the box floor through the lid hole.
\item Tie the stays from braided line (lengths between knots): forestay """ + f"{rig['forestay_mm']:.0f}" + r"""\,mm from the hounds to the bridle point; two bridle legs of """ + f"{rig['bridle_leg_mm']:.0f}" + r"""\,mm from the bridle point to the bow loops; two shrouds of """ + f"{rig['shroud_mm']:.0f}" + r"""\,mm from the hounds to the chainplate eyes.
\item Cut the 4\,mm tube to a """ + f"{rig['boom_length_mm']:.0f}" + r"""\,mm boom. Tie a loose loop of line through its front end around the mast so the boom sits about 5\,mm above the lid and swings freely.
\end{enumerate}
\chk{the mast stands straight from the side and from behind; all stays are just tight.}

\step{6. Sails}
\begin{enumerate}
\item Print \texttt{mini/manual/sail\_patterns\_1to1.pdf} at 100\,\% (large-format print, or tile it). The 100\,mm scale bar must measure 100\,mm.
\item Lay the Icarex on the pattern and cut the main and jib with a hot knife or scissors. The main needs the extra """ + f"{25:.0f}" + r"""\,mm on the luff for the mast sleeve.
\item Main: fold the 25\,mm sleeve and close it with sail tape so it slides over the mast. Cut three battens from 1.2\,mm carbon rod (""" + ', '.join(f"{b:.0f}" for b in D['battens_length_mm']) + r"""\,mm) and tape them on at """ + ', '.join(f"{h:.0f}" for h in D['battens_height_mm']) + r"""\,mm above the foot.
\item Jib: fold a 10\,mm sleeve along the """ + f"{D['jib_luff_mm']:.0f}" + r"""\,mm luff around the forestay line.
\item Reinforce the head, tack and clew of both sails with two layers of sail tape and melt a 2\,mm hole in each clew.
\end{enumerate}

\step{7. Sheets and drum}
Both sheets end on the one drum, so one stick moves both sails.
\begin{itemize}
\item Mainsheet: from the boom end, down through the lid fairlead """ + f"{rig['main_fairlead_x_mm']:.0f}" + r"""\,mm from the transom, to the \textbf{30\,mm groove}.
\item Jib sheet: from the jib clew, down through the fairlead """ + f"{rig['jib_fairlead_x_mm']:.0f}" + r"""\,mm from the transom, to the \textbf{16.2\,mm groove}.
\item Wind both sheets the same way. From sheeted in to fully eased the mainsheet pays out """ + f"{drum['main_travel_mm']:.0f}" + r"""\,mm and the jib sheet """ + f"{drum['jib_travel_mm']:.0f}" + r"""\,mm. Both take """ + f"{drum['main_turns']:.2f}" + r""" drum turns, which is why the grooves have different diameters.
\end{itemize}

\step{8. Radio setup}
\begin{enumerate}
\item Bind the receiver to the transmitter (follow the FlySky manual) and select an airplane model.
\item Set the CH3 end points so full stick travel turns the drum """ + f"{drum['main_turns']:.2f}" + r""" turns. If the winch makes 2 turns at 100\,\%, that is about """ + f"{drum['main_turns']/2*100:.0f}" + r"""\,\%. Reverse CH3 if needed so that stick down means sheets in.
\item Set CH1 so the right stick steers the boat the way you expect: stick right, bow turns right.
\item Use the radio's failsafe function: on signal loss, rudders centred and sheets eased. An eased cat stops and drifts instead of sailing away.
\end{enumerate}

\step{9. Balance and float test}
\begin{enumerate}
\item Rig the boat. Balance it on two fingers under the beams: it should balance about """ + f"{ST['lcg_mm']:.0f}" + r"""\,mm forward of the transoms. If not, move the battery.
\item Float it in a tub: the hulls should sit level, about """ + f"{ST['hull_draft_mm']:.0f}" + r"""\,mm deep. Leave it 10 minutes and check for water in the box.
\end{enumerate}

\step{10. First sail}
\begin{itemize}
\item Pick 3 to 8\,kn of wind, a small pond, and a way to retrieve the boat that does not involve swimming (a friend's kayak, or a long pole and line). A capsized catamaran does not right itself.
\item Start on a beam reach with the sheets half out. Sheet in until the boat accelerates; ease when a hull starts to lift.
\item Above about 8\,kn, ease the sheets to keep the windward hull down.
\item Watch the bows. A catamaran more often trips over its bows (pitchpoles) than capsizes sideways. The analysis puts the bow-burying limit at about """ + f"{pp(60):g} / {pp(90):g} / {pp(120):g} / {pp(150):g}" + r"""\,kn of wind at 60 / 90 / 120 / 150$^\circ$ off the wind. Near those winds, ease the sheets as soon as the leeward bow starts to dig.
\item If the boat keeps turning away from the wind, sheet the jib less (the jib rides 4$^\circ$ wider than the main on the drum) or move the mast step aft. If it keeps turning into the wind, do the opposite.
\end{itemize}

\section{Troubleshooting}
\begin{tabularx}{\textwidth}{>{\raggedright}p{4cm}X}
\toprule
Symptom & Fix \\
\midrule
Water inside a hull segment & Leak test that segment again; seal with CA; paint the outside with thinned epoxy \\
Winch stalls or jitters & Check the battery charge; reduce the CH3 end points; make sure no line is caught under the drum \\
Rudders do not centre & Re-bend the pushrod or adjust the clevis; set CH1 sub-trim \\
Boat will not tack & Sail faster before turning; turn gradually with full rudder; ease the jib during the turn \\
Nose dives in gusts & Ease both sheets earlier; move the battery aft \\
\bottomrule
\end{tabularx}

\appendix
\section{Engineering numbers}
Hydrostatics (fresh water): mass """ + f"{ST['mass_g']:.0f}" + r"""\,g; waterline at z=""" + f"{ST['waterline_z_mm']:.1f}" + r"""\,mm on the design reference; hull volume """ + f"{ST['hull_volume_cm3_analytic']:.0f}" + r"""\,cm$^3$ per hull; maximum righting moment """ + f"{STB['RM_max_Nm']:.2f}" + r"""\,N\,m from the heeled-hull calculation (largest righting arm """ + f"{STB['gz_max_mm']:.0f}" + r"""\,mm at """ + f"{STB['gz_max_at_deg']}" + r"""$^\circ$, capsize near """ + f"{STB['capsize_angle_deg']}" + r"""$^\circ$); largest bow-down moment the hulls can resist """ + f"{STB['pitch_2hull']['RM_L_max_Nm']:.2f}" + r"""\,N\,m on two hulls, """ + f"{STB['pitch_1hull']['RM_L_max_Nm']:.2f}" + r"""\,N\,m on one; heeling arm """ + f"{ST['heel_arm_m']:.2f}" + r"""\,m.

\noindent Predicted boat speed in m/s (* = sails eased to keep the windward hull down):
\begin{center}
\begin{tabular}{cccc}
\toprule
True wind (kn) & TWA 60$^\circ$ & TWA 90$^\circ$ & TWA 105$^\circ$ \\
\midrule
""" + vpp_table() + r"""
\bottomrule
\end{tabular}
\end{center}
These come from the same velocity-prediction code as the 1\,m boat. Hull friction uses the ITTC-57 line; wave drag uses the Michell thin-ship integral with catamaran interference; sail forces use a lift/drag model. The code and its validation checks are in \texttt{analysis/vpp.py} and \texttt{mini/mini\_analysis.py}. They are predictions until measured with GPS on the water.

\section{Parts cost of the 1\,m build-first boat}
{\small
\begin{longtable}{p{1.5cm}p{4.3cm}p{5.0cm}cp{1.2cm}p{1.2cm}}
\toprule
\textbf{Group} & \textbf{Item} & \textbf{Used for} & \textbf{Qty} & \textbf{Unit} & \textbf{Total} \\
\midrule\endhead
""" + bom_rows(full) + r"""
\midrule
& \textbf{Total} & & & & \textbf{""" + money(total(full)) + r"""} \\
\bottomrule
\end{longtable}}
If you build the mini first, the radio and the NiMH pack carry over, which lowers the 1\,m boat's extra cost by """ + money(sum(float(x['total_usd']) for x in full if x['group'] in ('Radio', 'Power'))) + r""".

\section{Parts cost of the v2.2 foiling kit}
The kit is sized for the v2.2 foils in the CAD model: NACA\,4412 wings 160\,x\,45\,mm at $+1.5^\circ$, NACA\,0012 elevators 120\,x\,28\,mm at $-1^\circ$ (nose down), and 60\,mm-chord struts. The foiling rudders end 13\,mm lower than the build-first ones, in a printed trim pod: bond a 3\,mm extension (\url{stl/Foiling_Rudder_Extension_x2.stl}) and then the pod (\url{stl/Elevator_Trim_Pod_x2.stl}, 45\,x\,9\,x\,14\,mm) under each blade. The elevator passes through the pod's slot, pivots on a 2\,mm carbon pin at its quarter chord, and is clamped by two M2 set screws 12\,mm behind the pin (one from above, one from below): one turn moves it about $1.9^\circ$, so it can be trimmed on the water. Printable cores with 0.5\,mm recesses for the carbon caps are in \url{stl/} (\texttt{Foil\_Core\_*}, \texttt{Foil\_Flap\_x2}). The foils are printed PETG cores with unidirectional carbon caps (4 layers per face), laminated with epoxy; the caps take about 4.6\,m of the 7.3\,m of tape listed. The kit also includes flap hinges, the ride-height wands and their linkage. It is added to the 1\,m boat after the build-first version sails.
{\small
\begin{longtable}{p{1.5cm}p{4.3cm}p{5.0cm}cp{1.2cm}p{1.2cm}}
\toprule
\textbf{Group} & \textbf{Item} & \textbf{Used for} & \textbf{Qty} & \textbf{Unit} & \textbf{Total} \\
\midrule\endhead
""" + bom_rows(foil) + r"""
\midrule
& \textbf{Total} & & & & \textbf{""" + money(total(foil)) + r"""} \\
\bottomrule
\end{longtable}}

\section{Price sources (read 23-24 September 2026)}
{\small
\begin{itemize}
""" + sources(bom + opt + full + foil) + r"""
\end{itemize}}
Two prices carry extra uncertainty: the JX winch (AliExpress listed it on sale; the full price is used here) and the 16\,x\,14\,mm carbon tube (price taken from a search listing because the store's page was not reachable).
\end{document}
"""
open(os.path.join(HERE, 'RC_Mini_Cat_Build_Manual.tex'), 'w').write(tex)
print('written', len(tex))
