#!/bin/bash
set -e
cd "$(dirname "$0")"
for s in vpp.py control.py sensitivity.py; do echo "== $s $(date +%T)"; python3 $s > logs_$s.txt 2>&1; tail -2 logs_$s.txt; done
echo "== mini $(date +%T)"; (cd ../mini && python3 mini_analysis.py > ../analysis/logs_mini.txt 2>&1); tail -4 logs_mini.txt
echo "== figures $(date +%T)"; python3 figures_data.py > logs_figures.txt 2>&1
echo "== done $(date +%T)"
