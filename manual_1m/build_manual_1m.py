"""Generates the build manual for the 1 m boat and its foiling kit (LaTeX, compile with tectonic). Every number is read
from the analysis outputs, the parts lists (bom/), the rig model (manual_data_1m.json) or the CAD print list
(print_list_1m.json, from Fusion). python3 manual_1m/manual_data_1m.py && python3 manual_1m/build_manual_1m.py &&
tectonic manual_1m/RC_Catamaran_1m_Build_Manual.tex"""
import csv, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'fusion_addin', 'SailTrim'))
import vpp
import fittings_geom as fg

J = lambda *p: json.load(open(os.path.join(ROOT, *p)))
CAD, VR, MD, PL = J('analysis', 'cad_data.json'), J('analysis', 'vpp_results.json'), J('manual_1m', 'manual_data_1m.json'), J('manual_1m', 'print_list_1m.json')
TOW, CTL = J('analysis', 'takeoff_wind.json'), J('analysis', 'control_results.json')
full = list(csv.DictReader(open(os.path.join(ROOT, 'bom', 'bom_full_build_first.csv'))))
foil = list(csv.DictReader(open(os.path.join(ROOT, 'bom', 'bom_foiling_kit_v2.csv'))))
PETG = 1.27
V = lambda cfg, twa, tws: [x for x in VR['vpp'][cfg][str(twa)] if x['tws_kn'] == tws][0]['V']
D, F = CAD['displacement'], CAD['foiling']
WC, WS = vpp.WING_C * 1000, vpp.WING_SPAN * 1000


def esc(s):
    return s.replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('%', r'\%').replace('#', r'\#').replace('_', r'\_').replace('$', r'\$')


money = lambda x: r'\$' + f'{float(x):,.2f}'
total = lambda rows: sum(float(x['total_usd']) for x in rows)


def bom_rows(rows):
    return '\n'.join(f"{esc(x['group'])} & {esc(x['item'])} & {esc(x['use'])} & {x['qty']} & {money(x['total_usd'])} \\\\" for x in rows)


def sources(rows):
    seen, out = set(), []
    for x in rows:
        if x['url'] not in seen:
            seen.add(x['url']); out.append(f"\\item {esc(x['source'])}: \\url{{{x['url']}}}")
    return '\n'.join(out)


def print_rows(keys):
    out = []
    for k in keys:
        p = PL[k]
        g = p['cm3'] * PETG * p['qty']
        out.append(f"\\url{{{p['stl']}}} & {p['qty']} & {' x '.join(str(v) for v in p['size_mm'])} & {g:.0f} \\\\")
    return '\n'.join(out)


hull = sorted(k for k in PL if k.startswith('Hull'))
pod = sorted(k for k in PL if k.startswith('Pod'))
boat_parts = hull + pod + ['Rudder Servo Bracket (print)', 'Rudder Servo Cover (print)', 'Rudder Blade Port', 'Daggerboard Port', 'Gudgeon Port',
                          'Traveler Track Centre', 'Traveler Track Port', 'Traveler Track Stbd', 'Traveler Car', 'Jib Track', 'Jib Car',
                          'Bridle Post', 'Mast Cap', 'Hounds Collar', 'Mast Fairing Lower 1', 'Mast Fairing Upper 1', 'Gooseneck', 'Boom Jaw']
foil_parts = ['Core L-Foil Port', 'Core L-Foil Stbd', 'Core Elevator Port', 'Core Flap Port', 'Elevator Trim Pod Port', 'Rudder Extension Port',
              'Wand Pivot Port', 'Wand Hub Port', 'Bellcrank Mount Port', 'Strut Bellcrank Port', 'Flap Horn Port']
g_boat = sum(PL[k]['cm3'] * PETG * PL[k]['qty'] for k in boat_parts)
g_foil = sum(PL[k]['cm3'] * PETG * PL[k]['qty'] for k in foil_parts)
bat = ', '.join(f"{l:.0f}" for l in MD['battens_length_mm'])
hinge_from_le = 0.75 * WC
rig = MD['rig']

tex = r"""\documentclass[11pt]{article}
\usepackage[letterpaper,margin=0.85in]{geometry}
\usepackage{graphicx,booktabs,longtable,amsmath,xurl,enumitem,caption}
\usepackage[hidelinks]{hyperref}
\setlist{itemsep=2pt}
\newcommand{\step}[1]{\subsection*{#1}}
\title{\textbf{RC Catamaran 1\,m: Build Manual}\\\large Build-first boat and the """ + vpp.FOIL_VERSION + r""" foiling kit}
\author{Filip Maleev}
\date{September 2026}
\begin{document}
\maketitle
\begin{center}
\includegraphics[width=0.48\linewidth]{../images/build_first_v1.4.png}\hfill\includegraphics[width=0.48\linewidth]{../images/foiling_""" + vpp.FOIL_VERSION + r""".png}
\end{center}

\section{What you are building}
A 1\,m catamaran with a beach-cat rig: a square-top, fully battened main on a rotating wing mast, a jib on a forestay bridle, and three sail controls (jib sheet, traveler, mainsheet tension) on three servos. Build the boat with daggerboards first (the \emph{build-first} version, """ + f"{D['mass_g']:.0f}" + r"""\,g ready to sail). Once it sails well, the foiling kit replaces the daggerboards with L-foils, adds wand-driven flaps for ride-height control, and puts T-foil elevators on the rudders (""" + f"{F['mass_g']:.0f}" + r"""\,g).

Predicted, not yet measured: the build-first boat does """ + f"{V('displacement', 90, 8):.2f}" + r"""\,m/s on a beam reach in 8\,kn of wind. The foiling version flies from about """ + f"{TOW['90']:.1f}" + r"""\,kn on a beam reach and """ + (f"{TOW['60']:.1f}" if TOW['60'] else 'over 16') + r"""\,kn at 60$^\circ$ to the wind, and does """ + f"{V('foiling', 90, 12):.2f}" + r"""\,m/s on a beam reach in 12\,kn.

\textbf{Build the 0.6\,m Mini Cat first} (its own manual). Many steps here assume you have done them once at that size.

\section{What it costs}
Build-first boat \textbf{""" + money(total(full)) + r"""}; foiling kit \textbf{""" + money(total(foil)) + r"""} more. Prices were read on retailer pages in September 2026 (sources at the end). Shipping, tax, a NiMH charger, the printer and hand tools (including a 0.9\,mm hex key for the elevator trim screws) are not included. The FS-i6X radio and 4xAA pack from the Mini Cat carry over.

{\small
\begin{longtable}{p{1.6cm}p{4.4cm}p{6.6cm}cr}
\toprule
Group & Item & Use & Qty & Total \\
\midrule
\multicolumn{5}{l}{\textbf{Build-first boat}}\\
""" + bom_rows(full) + r"""
\midrule
\multicolumn{5}{l}{\textbf{Foiling kit}}\\
""" + bom_rows(foil) + r"""
\bottomrule
\end{longtable}}

\section{Printing}
PETG throughout. The hull and pod segments are real 0.8\,mm skins with the bulkheads built in: slice them with 2 perimeters and 0\,\% infill, so each segment prints as a sealed compartment. Print the rudder blades, daggerboards, foil cores, flaps and trim pods solid (100\,\% infill is our recommendation for stiffness, not a tested setting). Filament below is for solid parts at 1.27\,g/cm$^3$ and for the skins as modelled.

{\small
\begin{longtable}{lcrr}
\toprule
STL file (folder \texttt{stl/}) & Qty & Size (mm) & PETG (g) \\
\midrule
\multicolumn{4}{l}{\textbf{Boat}}\\
""" + print_rows(boat_parts) + r"""
\midrule
\multicolumn{4}{l}{\textbf{Foiling kit}}\\
""" + print_rows(foil_parts) + r"""
\bottomrule
\end{longtable}}
\noindent Total: about """ + f"{g_boat:.0f}" + r"""\,g for the boat and """ + f"{g_foil:.0f}" + r"""\,g for the foiling kit, before supports and failed prints.

\noindent Print the seven mast fairing pieces in spiral-vase mode: one """ + f"{fg.FAIR_WALL:.2f}" + r"""\,mm perimeter, no bottom or top layers. They are thin shells that slide over the mast tube. Print the tracks and cars standing on end, so the T-profile lies flat on the bed. The linkage parts marked x2 are handed: print the second one mirrored, for the starboard hull.

\section{Building the boat}
\step{1. Hulls}
\begin{enumerate}
\item Print the ten hull segments. Each ends in half of a bulkhead; the faces meet flat.
\item Epoxy the segments of each hull face to face in order (x = 0 is the transom), keeping the keel line straight on a flat surface.
\item Seal test: submerge each hull in a tub for 10 minutes and look for bubbles or water. Each segment is a separate compartment, so one leak floods only one.
\end{enumerate}
\step{2. Crossbeams and pod beam}
\begin{enumerate}
\item Cut two 600\,mm crossbeams from the 16\,x\,14\,mm tube, and a 600\,mm pod beam plus the 150\,mm mast joiner from the 10\,x\,8\,mm tube (wear a mask when cutting or sanding carbon).
\item Epoxy the crossbeams into the front and rear sockets of both hulls and the pod beam into the third socket, with the hulls parallel and the beams square.
\end{enumerate}
\step{3. Pod and electronics}
\begin{enumerate}
\item Bond the three pod shell segments and the three lid segments. The pod snaps onto the front beam and the pod beam.
\item Fit the two sail winches (traveler: 4-turn; jib sheet: 2-turn) and the mainsheet servo on their rails. The winches hang by their ears in 4--6\,mm wells. JX does not publish the winch's ear height; the rails use the FS5115M value (27.3\,mm above the case bottom). If a winch case touches the bottom of its well first, shim under the ears.
\item Hook the mainsheet tail to the servo horn 25\,mm from the shaft, not closer. The sheet runs twice between the traveler car and the boom, so a shorter arm lets the servo pull harder on the beams and mast than the structure check allows. Fit a longer horn if the supplied ones are shorter.
\item Receiver and the 4xAA pack with its switch go in the pod. The two ends of the traveler line and the mainsheet tail leave the pod through the three holes in its transom and run aft to the turning pins in the traveler track's end stops (Step 7).
\end{enumerate}
\step{4. Rudders}
\begin{enumerate}
\item Rudder stocks from the 0.156\,in music wire, through the printed blades (pivot at 25\,\% chord).
\item Epoxy a gudgeon to each transom, centred on the hull, with its plate flat on the transom face; its two lugs hold the stock 19\,mm behind the transom. Slide the stock down through both lugs into the blade; the tiller arm above the upper lug keeps it in.
\item Snap the rudder-servo bracket onto the rear beam from below, centred between the hulls, and epoxy it so it cannot rotate. The MG90S hangs by its ears on the bracket's rails, aft of the beam, under the printed cover. The pushrod (0.093\,in wire, Du-Bro clevises) runs from the slot in the cover to the tie bar, which joins the two tiller arms.
\end{enumerate}
\step{5. Rig}
\begin{enumerate}
\item Mast: the two 12\,x\,10\,mm tubes joined by the 150\,mm spigot, """ + f"{rig['mast_length_mm']:.0f}" + r"""\,mm overall. Plug the top with the mast cap (epoxy), so the tube stays sealed if the boat capsizes.
\item Wing: from the foot up, the gooseneck (tab and pin hole aft), the five lower fairing pieces, the hounds collar with its centre """ + f"{rig['hounds_above_mast_foot_mm']:.0f}" + r"""\,mm above the mast foot, and the two upper pieces. Line up the trailing edges and fix each piece to the tube with a drop of CA at both ends. The whole mast turns in the pod lid and the step, so the wing follows the sail.
\item Melt 1.2\,mm lacing holes through the fairing """ + f"{fg.LACING_IN:.0f}" + r"""\,mm ahead of its trailing edge, every """ + f"{fg.LACING_PITCH:.0f}" + r"""\,mm, starting """ + f"{fg.LACING_PITCH:.0f}" + r"""\,mm above the sail's foot; the marks on the sail pattern give the heights. Skip the hounds collar.
\item Standing rigging from the 30\,lb braided line (lengths between fittings): forestay """ + f"{rig['forestay_mm']:.0f}" + r"""\,mm, each bridle leg """ + f"{rig['bridle_leg_mm']:.0f}" + r"""\,mm, each shroud """ + f"{rig['shroud_mm']:.0f}" + r"""\,mm. Add your own allowance for knots. Tie the three stays to a loop of line in the hounds collar's groove, so the mast turns inside the loop. At the bridle post, the bridle line runs through the lower hole (fix it there with CA); the forestay and the jib tack tie through the upper hole.
\item Boom: """ + f"{rig['boom_tube_mm']:.0f}" + r"""\,mm of the 8\,x\,7\,mm tube, with the boom jaw epoxied into its front end. Pin the jaw to the gooseneck's tab with a piece of the 0.093\,in wire. Bend a small eye from the same wire for the mainsheet and epoxy it under the boom's aft end.
\item Traveler track: epoxy the centre piece on top of the rear beam, centred. Slide the car on from one end, then epoxy the two end pieces on so the rail runs continuously, and sand the joints smooth. Press a 19\,mm piece of the 0.093\,in wire into each end stop's pin hole. The car stops """ + f"{fg.CAR_LIMIT:.0f}" + r"""\,mm either side of the centre line (boom """ + f"{MD['travel']['boom_at_car_stop_deg']:.0f}" + r"""$^\circ$ out).
\item Jib track: slide the jib car on, then epoxy the track on the pod lid on the centre line, """ + f"{fg.JT_X:.0f}" + r"""\,mm forward of the transoms. Drill a 2\,mm hole through the lid under the hole at the track's centre, for the jib sheet.
\end{enumerate}
\step{6. Sails}
\begin{enumerate}
\item Print the 1:1 patterns (\texttt{manual\_1m/sail\_patterns\_1m\_1to1.pdf}, a single tall sheet: a copy shop's plotter, or tile it) and check the 100\,mm scale bar.
\item Cut the main (foot """ + f"{MD['main']['foot']:.0f}" + r""", luff """ + f"{MD['main']['luff']:.0f}" + r""", head """ + f"{MD['main']['head']:.0f}" + r"""\,mm) and the jib (foot """ + f"{MD['jib_foot']:.0f}" + r""", luff """ + f"{MD['jib_luff_mm']:.0f}" + r"""\,mm) from the Icarex. Tape the edges, corners and eight batten pockets with the sail tape.
\item Battens from the 1.2\,mm carbon rod, bottom to top (mm): """ + bat + r""".
\item Main luff: tape it, then melt the lacing holes 5\,mm in from the edge at the marks on the pattern. Lace it to the wing's trailing edge with the braided line, one turn round the edge per hole. Lash the tack to the hole in the boom jaw and the head to the top lacing hole.
\item Jib: fold a 10\,mm sleeve along the luff around the forestay, as on the Mini Cat.
\end{enumerate}
\step{7. Mainsheet routing}
The traveler car moves up to """ + f"{fg.CAR_LIMIT:.0f}" + r"""\,mm either side of the centre line. That is far more line than the mainsheet servo can take up, so the car must not pull on the mainsheet. Tie the mainsheet to the port end-stop pin in the upper slot. Run it through the car's port post, up through the eye under the boom and back down, through the starboard post, round the starboard pin in the upper slot and forward into the pod. Moving the car then shortens one side of the sheet exactly as much as it lengthens the other.

The traveler line is one loop. From the winch drum it runs out of the pod, round the port pin in the lower slot, through the car's lower hole, round the starboard pin and back into the pod to the drum. Fix the car on the line with a drop of CA through the hole in the top of the car.
\step{8. Radio setup}
\begin{enumerate}
\item Bind the receiver and assign four channels: rudder, traveler, jib sheet, mainsheet tension.
\item Traveler winch: set its end points so the car runs the full track (about """ + f"{MD['travel']['traveler_mm']:.0f}" + r"""\,mm of car travel in the rig model) without hitting the ends. Jib winch: about """ + f"{MD['travel']['jib_sheet_mm']:.0f}" + r"""\,mm of sheet from sheeted in to eased. Mainsheet servo: set its end points by eye, flattest leech without stalling the servo.
\item Rudder: stick right, bow right. The linkage gives $\pm""" + f"{CTL['rudder_throw_deg']:.0f}" + r"""^\circ$ of rudder.
\item Failsafe: rudders centred and sheets eased on signal loss.
\end{enumerate}
\step{9. Balance and float test}
Rigged, the build-first boat should balance """ + f"{D['lcg_mm']:.0f}" + r"""\,mm forward of the transoms (move the battery to correct it). Float it and check both hulls sit level; leave it 10 minutes and check the pod and hulls for water.

\section{The foiling kit}
Fit the kit only after the build-first boat sails well.
\step{10. Foil cores and carbon caps}
\begin{enumerate}
\item Print the L-foil cores (port and starboard are mirror images), the elevator cores and the flaps. The cores have 0.5\,mm deep, 25\,mm wide recesses on both faces of the strut, the wing and the elevator for the carbon caps.
\item Split the 2\,in unidirectional tape lengthwise into 25\,mm strips and lay 4 layers into each recess with the laminating epoxy, fibres along the span; the caps finish flush with the section. The caps use about 4.5\,m of the 7.3\,m of tape.
\item The strut has a 2.4\,mm channel for the flap pushrod (0.047\,in wire); keep it clear of epoxy.
\end{enumerate}
\step{11. Flaps}
The flap is the aft 25\,\% of each wing (""" + f"{0.25 * WC:.0f}" + r"""\,mm), from 10\,mm inside the tip to the strut. It hinges on 1.2\,mm carbon pins on its leading edge, """ + f"{hinge_from_le:.0f}" + r"""\,mm behind the wing's leading edge. The CAD does not model the hinge holes: drill them on that line at each end of the flap. The flap must swing $\pm""" + f"{vpp.FLAP_TRAVEL_DEG:.0f}" + r"""^\circ$ freely.
\step{12. Ride-height linkage}
One wand per hull, """ + f"{vpp.WAND_L * 1000:.0f}" + r"""\,mm of 2\,mm carbon rod, hinged at the bow. It drives its flap through a deck pushrod, a bellcrank and the pushrod inside the strut. The linkage must give:
\begin{itemize}
\item \textbf{zero flap} with the wand """ + f"{vpp.WAND_PHI0_DEG:.0f}" + r"""$^\circ$ below the deck line (the design ride height, hinge about """ + f"{vpp.WAND_L * 1000 * math.sin(math.radians(vpp.WAND_PHI0_DEG)):.0f}" + r"""\,mm above the water);
\item \textbf{""" + f"{vpp.GEAR:g}" + r"""$^\circ$ of flap per degree of wand}, wand down giving flap down;
\item the full $\pm""" + f"{vpp.FLAP_TRAVEL_DEG:.0f}" + r"""^\circ$ of flap without binding.
\end{itemize}
The printed linkage gives them. The wand hub's horn is 8.25\,mm long, the bellcrank's arms are 8\,mm, and the flap horn's hole is 5.5\,mm behind the flap hinge: $(8.25/5.5)\times(8/8) = 1.5^\circ$ of flap per degree of wand.
\begin{enumerate}
\item Epoxy a wand hinge bracket to each stem, cheeks forward. Put the wand hub between the cheeks on a 2\,mm carbon axle and push the wand into the hub's socket.
\item Epoxy the bellcrank mount on the deck beside the strut's top. Pin the bellcrank between its cheeks on a 2\,mm carbon axle, one arm up and one arm aft.
\item Bond the flap horn to the upper face of the flap's root, in line with the slot in the strut's inboard face.
\item Bend Z-ends on the 0.047\,in wire. The deck pushrod runs from the hub's horn to the bellcrank's upper arm; the strut pushrod runs from the bellcrank's aft arm down the strut's channel and out of the slot to the flap horn. Bend the last Z with the wand at """ + f"{vpp.WAND_PHI0_DEG:.0f}" + r"""$^\circ$ and the flap at zero.
\end{enumerate}
\step{13. Elevators and trim pods}
\begin{center}\includegraphics[width=0.6\linewidth]{../images/elevator_trim_pod.png}\end{center}
\begin{enumerate}
\item Bond a 3\,mm extension and then a trim pod under each rudder blade; the pod's slot is at the elevator's height.
\item Slide the elevator through the slot and pin it at its quarter chord with a 10\,mm piece of the 2\,mm carbon rod.
\item Two M2 set screws, one from above and one from below, clamp it 12\,mm behind the pin. One turn moves the elevator about $1.9^\circ$. Set $""" + f"{vpp.INC_EL_DEG:+g}" + r"""^\circ$ (nose down) to start.
\end{enumerate}
\step{14. Fit and set up}
\begin{enumerate}
\item Replace the daggerboards with the L-foils in the same trunks. Main wing incidence $""" + f"{vpp.INC_MAIN_DEG:+g}" + r"""^\circ$.
\item Rebalance: the foiling boat should balance """ + f"{F['lcg_mm']:.0f}" + r"""\,mm forward of the transoms, """ + f"{F['mass_g']:.0f}" + r"""\,g in total.
\item Run the bench checks and the tow test in \texttt{testing/RC\_Foiling\_Cat\_Tow\_Test\_Plan.pdf} before sailing on the foils.
\item First flights: take off on a beam reach, where the foils have enough roll authority, then head up. Near take-off the leeward hull may keep touching; that is expected.
\end{enumerate}

\section*{Price sources (read September 2026)}
{\small\begin{itemize}
""" + sources(full + foil) + r"""
\end{itemize}}
\end{document}
"""
open(os.path.join(HERE, 'RC_Catamaran_1m_Build_Manual.tex'), 'w').write(tex)
print('written', round(g_boat), round(g_foil))
