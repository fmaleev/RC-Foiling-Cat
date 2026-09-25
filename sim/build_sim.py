"""Builds sim/foil_sim.html from the template, sim_core.js and sim_data.json (run export_sim_data.py first when the design changes)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, 'foil_sim.template.html')).read()
data = open(os.path.join(HERE, 'sim_data.json')).read()
assert '__SIM_DATA__' in tpl
core = open(os.path.join(HERE, 'sim_core.js')).read()
assert '__SIM_CORE__' in tpl
open(os.path.join(HERE, 'foil_sim.html'), 'w').write(tpl.replace('__SIM_CORE__', core).replace('__SIM_DATA__', data))
print('written', os.path.getsize(os.path.join(HERE, 'foil_sim.html')), 'bytes')
