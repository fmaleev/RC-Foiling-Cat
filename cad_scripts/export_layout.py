"""Bounding boxes (mm, boat frame) of the bodies the 1 m manual's diagrams label, written to manual_1m/layout_1m.json.
Run inside Fusion via MCP exec on the foiling master: export(design)."""
import json, os

OUT = os.path.expanduser('~/RC-Foiling-Cat/manual_1m/layout_1m.json')
BODIES = {
    'Crossbeams': ('Front Beam', 'Rear Beam', 'Pod Beam'),
    'Center Pod': ('Pod Shell', 'Rudder Servo Cover'),
    'RC Electronics': ('Traveler Winch Servo', 'Winch Drum', 'Mainsheet Servo', 'Jib Sheet Winch Servo', 'Jib Winch Drum',
                       'Rudder Servo', 'Receiver', 'Battery 2S', 'Rudder Pushrod'),
    'Rudders': ('Rudder Blade Port', 'Rudder Blade Stbd', 'Tie Bar', 'Gudgeon Port', 'Gudgeon Stbd'),
    'Rig Standing': ('Mast Tube Base', 'Traveler Track Centre', 'Traveler Track Port', 'Traveler Track Stbd', 'Jib Track', 'Bridle Post',
                     'Turning Pin Port', 'Turning Pin Stbd'),
    'Displacement Kit': ('Daggerboard Port', 'Daggerboard Stbd'),
    'Mainsail': ('Main Boom', 'Traveler Car'),
    'Jib': ('Jib Car',),
}


def export(design):
    comps = {o.component.name: o.component for o in design.rootComponent.occurrences}
    out = {}
    for cn, names in BODIES.items():
        for n in names:
            b = comps[cn].bRepBodies.itemByName(n)
            bb = b.boundingBox
            out[n] = [round(v * 10, 2) for v in (bb.minPoint.x, bb.maxPoint.x, bb.minPoint.y, bb.maxPoint.y, bb.minPoint.z, bb.maxPoint.z)]
    json.dump(out, open(OUT, 'w'), indent=1)
    return out
