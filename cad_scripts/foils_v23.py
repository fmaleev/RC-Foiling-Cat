"""v2.3 foils. Correcting the CAD masses (printed fittings and mast fairing, music-wire rudder parts) moved the centre of
gravity about 7 mm aft, which cut the v2.2 foils' pitch static margin to 25 mm, under the 30 mm limit. The same search
(sim/optimize.js, paper Section 6) then picked larger foils. Run inside Fusion via MCP exec on the foiling master:
foils_v22.apply(design, FOILS), then elevator_trim, linkage and foil_cores. The wing keeps its quarter chord at x = 575 mm,
so its flap hinge moves 2.5 mm aft; linkage.py follows the hinge.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foils_v22

FOILS = dict(wspan=180.0, wchord=50.0, winc=1.5, espan=160.0, echord=28.0, einc=-0.5, zel=-215.0)   # sim/optimize.js 'adopted' (2026-09-27)
apply = foils_v22.apply
