#!/bin/bash
# Full analysis pipeline: stability -> pitchpole -> VPP -> control -> sensitivity -> take-off wind -> ride height -> pitch trim -> heave-pitch stability -> take-off in time -> mini -> structure -> foil checks -> figure data -> design checks -> simulator + foil optimization + roll options
set -e
cd "$(dirname "$0")"
for s in stability.py pitchpole.py vpp.py control.py sensitivity.py takeoff_wind.py ride_height.py pitch_trim.py pitch_heave.py takeoff_sim.py; do
  echo "== $s $(date +%T)"; python3 $s > logs_$s.txt 2>&1; tail -3 logs_$s.txt
done
echo "== mini $(date +%T)"; (cd ../mini && python3 mini_analysis.py > ../analysis/logs_mini.txt 2>&1); tail -4 logs_mini.txt
echo "== structure $(date +%T)"; python3 structure.py > logs_structure.txt 2>&1; tail -1 logs_structure.txt | cut -c1-120
echo "== foil checks $(date +%T)"; python3 foil_checks.py > logs_foil_checks.txt 2>&1 || true; tail -1 logs_foil_checks.txt
echo "== figures $(date +%T)"; python3 figures_data.py > logs_figures.txt 2>&1; tail -1 logs_figures.txt
echo "== design checks $(date +%T)"; python3 design_checks.py > logs_design_checks.txt 2>&1 || true; tail -1 logs_design_checks.txt
echo "== simulator $(date +%T)"; (cd ../sim && python3 export_sim_data.py > ../analysis/logs_sim.txt 2>&1 && python3 build_sim.py >> ../analysis/logs_sim.txt 2>&1 && node optimize.js >> ../analysis/logs_sim.txt 2>&1 && node roll_options.js >> ../analysis/logs_sim.txt 2>&1); tail -2 logs_sim.txt
echo "== done $(date +%T)"
