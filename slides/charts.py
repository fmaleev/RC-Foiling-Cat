"""Charts for the slide deck, drawn with pgfplots from the paper's data files (paper/data) and rendered to PNG.
python3 slides/charts.py  ->  slides/charts/*.png (tectonic, then tools/pdf2png.swift)."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(HERE, 'charts')
DATA = os.path.join(ROOT, 'paper', 'data')
NAVY, SEA, CORAL, GREY = '1B2F4B', '2E7DB5', 'D9653B', '8A94A3'
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
import vpp

HEAD = r"""\documentclass[border=4pt]{standalone}
\usepackage{pgfplots}\pgfplotsset{compat=1.17}
\usepackage[scaled]{helvet}\renewcommand{\familydefault}{\sfdefault}\usepackage{sansmath}\sansmath
\definecolor{navy}{HTML}{%s}\definecolor{sea}{HTML}{%s}\definecolor{coral}{HTML}{%s}\definecolor{greyc}{HTML}{%s}
\pgfplotsset{every axis/.style={width=16cm, height=9cm, grid=major, grid style={greyc!30}, axis line style={greyc}, tick style={greyc},
  tick label style={font=\Large, text=navy}, label style={font=\Large, text=navy}, legend style={font=\Large, draw=none, fill=none, text=navy}}}
\begin{document}\begin{tikzpicture}[font=\sffamily]
""" % (NAVY, SEA, CORAL, GREY)
TAIL = r"""\end{tikzpicture}\end{document}
"""
CHARTS = {
    'speed': r"""\begin{axis}[xlabel={True wind speed (kn)}, ylabel={Boat speed, beam reach (m/s)}, xmin=3, xmax=16, ymin=0, legend pos=north west]
\addplot[line width=2.5pt, sea] table[x=tws, y=V] {DATA/vpp_displacement_90.dat}; \addlegendentry{build-first (daggerboards)}
\addplot[line width=2.5pt, coral] table[x=tws, y=V] {DATA/vpp_foiling_90.dat}; \addlegendentry{foiling}
\end{axis}""",
    'elevator': r"""\begin{axis}[xlabel={Boat speed (m/s)}, ylabel={Elevator depth (mm)}, xmin=2, xmax=5, xtick={2,2.5,...,5}, ymin=-60, ymax=100, legend pos=north east]
\addplot[line width=2.5pt, coral, dashed] table[x=V, y=eldepth] {DATA/trim_v21.dat}; \addlegendentry{v2.1: elevators at +4$^\circ$}
\addplot[line width=2.5pt, sea] table[x=V, y=eldepth] {DATA/trim_CAD.dat}; \addlegendentry{""" + vpp.FOIL_VERSION + r""": elevators at $""" + f"{vpp.INC_EL_DEG:+g}" + r"""^\circ$}
\addplot[line width=1.2pt, navy] coordinates {(2,0) (5,0)}; \addlegendentry{water surface}
\end{axis}""",
    'takeoff': r"""\begin{axis}[xlabel={Time (s)}, ylabel={Boat speed (m/s)}, xmin=0, xmax=12, ymin=0, axis y line*=left, legend style={at={(0.97,0.3)}, anchor=east}]
\addplot[line width=2.5pt, sea] table[x=t, y=V] {DATA/takeoff_ts.dat}; \addlegendentry{speed}
\end{axis}
\begin{axis}[xmin=0, xmax=12, axis y line*=right, axis x line=none, ylabel={Bow height (mm), flap ($^\circ$)}, grid=none, legend style={at={(0.97,0.12)}, anchor=east}]
\addplot[line width=2.5pt, coral] table[x=t, y=bow] {DATA/takeoff_ts.dat}; \addlegendentry{bow height}
\addplot[line width=2pt, greyc, dashed] table[x=t, y=flap] {DATA/takeoff_ts.dat}; \addlegendentry{flap}
\end{axis}""",
    'search': r"""\begin{axis}[xlabel={Wind needed to fly, beam reach (kn)}, ylabel={Boat speed at 12 kn (m/s)}, legend pos=south east]
\addplot[only marks, mark=*, mark size=0.8pt, greyc!60] table[x=tws90, y=v12] {DATA/opt_cloud_thin.dat}; \addlegendentry{feasible designs}
\addplot[only marks, mark=*, mark size=0.9pt, sea!55] table[x=tws90, y=v12] {DATA/opt_cloud_robust_thin.dat}; \addlegendentry{robust, with margins}
\addplot[line width=2.5pt, navy] table[x=tws90, y=v12] {DATA/opt_front_robust.dat}; \addlegendentry{best robust trade-off}
\end{axis}""",
}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, body in CHARTS.items():
        tex = os.path.join(OUT, name + '.tex')
        open(tex, 'w').write(HEAD + body.replace('DATA/', DATA + '/') + '\n' + TAIL)
        subprocess.run(['tectonic', tex], cwd=OUT, check=True, capture_output=True)
        subprocess.run(['swift', os.path.join(ROOT, 'tools', 'pdf2png.swift'), os.path.join(OUT, name + '.pdf'), OUT, '1', '3.0'], check=True, capture_output=True)
        os.replace(os.path.join(OUT, 'p1.png'), os.path.join(OUT, name + '.png'))
        print(name, os.path.getsize(os.path.join(OUT, name + '.png')))
