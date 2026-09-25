"""Adjustable elevator incidence: a printed trim pod at each rudder tip. Run inside Fusion via MCP exec after the foils
script (foils_v22.apply): apply(design, foils).
- Pod: a NACA 0020 prism with the rudder blade's 45 mm chord (9 mm thick), from 7 mm below the elevator to 7 mm above
  it (or up to the rudder blade tip). Above the pod, any remaining gap to the blade tip stays a NACA 0012 extension.
- The elevator passes through a slot in the pod (its thickness plus 1.5 mm, for about +-2 deg of rotation) and pivots on
  a 2 mm carbon pin through the pod at the elevator's quarter chord.
- Two M2 screws (1.6 mm tapping holes), one from the top and one from the bottom of the pod, clamp the elevator 12 mm
  behind the pivot. One turn (0.4 mm pitch) turns it about atan(0.4 / 12) = 1.9 deg.
Bodies (Foiling Kit): 'Elevator Trim Pod Port/Stbd' (printed PETG), 'Rudder Extension Port/Stbd' (only if needed),
'Elevator Pivot Pin Port/Stbd' (carbon rod), 'Trim Screw ... ' (M2 steel, fixed mass in export_full_mass)."""
import adsk.core, adsk.fusion, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mini as bm
import servo_mounts as sm

POD_HALF_H, POD_CODE, SLOT_CLEAR = 7.0, '0020', 1.5      # mm
PIN_D, TAP_D, SCREW_ARM = 2.0, 1.6, 12.0                  # mm
ELEV_QC_X = -15.0


def prism(comp, name, code, chord, le_x, yc, z0, z1):
    """Vertical NACA prism (leading edge forward, +x) between z0 and z1 (mm)."""
    zm = (z0 + z1) / 2
    sk = comp.sketches.add(bm.plane_at(comp, comp.xYConstructionPlane, zm))
    sk.name = name + ' Section'
    col = adsk.core.ObjectCollection.create()
    for s, t in bm.naca(code):
        col.add(sk.modelToSketchSpace(bm.P(le_x - chord * s, yc + chord * t, zm)))
    sp = sk.sketchCurves.sketchFittedSplines.add(col)
    sk.sketchCurves.sketchLines.addByTwoPoints(sp.endSketchPoint, sp.startSketchPoint)
    sk.isVisible = False
    b = bm.sym(comp, [sk.profiles.item(0)], abs(z1 - z0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
    b.name = name
    return b


def apply(design, foils):
    root = design.rootComponent
    comp = [o.component for o in root.occurrences if o.component.name == 'Foiling Kit'][0]
    rud = [o.component for o in root.allOccurrences if o.component.name == 'Rudders'][0]
    ops = adsk.fusion.FeatureOperations
    zel, ec = foils['zel'], foils['echord']
    t_el = 0.12 * ec
    out = {}
    for side in ('Port', 'Stbd'):
        old = comp.bRepBodies.itemByName(f'Rudder Extension {side}')
        if old:
            comp.features.removeFeatures.add(old)
        bb = rud.bRepBodies.itemByName(f'Rudder Blade {side}').boundingBox
        x0, x1 = bb.minPoint.x * 10, bb.maxPoint.x * 10
        yc = (bb.minPoint.y + bb.maxPoint.y) * 5
        tip = bb.minPoint.z * 10
        pod_top = min(tip, zel + POD_HALF_H)
        if tip - pod_top > 0.01:
            prism(comp, f'Rudder Extension {side}', '0012', x1 - x0, x1, yc, pod_top, tip)
        prism(comp, f'Elevator Trim Pod {side}', POD_CODE, x1 - x0, x1, yc, zel - POD_HALF_H, pod_top)
        # slot for the elevator, the pivot pin hole and the two trim-screw holes
        el_le, el_te = ELEV_QC_X + 0.25 * ec, ELEV_QC_X - 0.75 * ec
        h = t_el / 2 + SLOT_CLEAR / 2
        cuts = [bm.tbox(el_te - 0.5, el_le + 0.5, yc - 10, yc + 10, zel - h, zel + h),
                bm.tcyl((ELEV_QC_X, yc - 10, zel), (ELEV_QC_X, yc + 10, zel), PIN_D / 2),
                bm.tcyl((ELEV_QC_X - SCREW_ARM, yc, zel - POD_HALF_H - 1), (ELEV_QC_X - SCREW_ARM, yc, zel + POD_HALF_H + 1), TAP_D / 2)]
        sm.combine(comp, f'Elevator Trim Pod {side}', f'Trim Pod Cuts {side}', cuts, ops.CutFeatureOperation)
        sm.combine(comp, f'Elevator {side}', f'Elevator Pin Hole {side}', [bm.tcyl((ELEV_QC_X, yc - 10, zel), (ELEV_QC_X, yc + 10, zel), PIN_D / 2)],
                   ops.CutFeatureOperation)
        pin = bm.tcyl((ELEV_QC_X, yc - 5, zel), (ELEV_QC_X, yc + 5, zel), PIN_D / 2 - 0.02)
        bm.base_bodies(comp, [(f'Elevator Pivot Pin {side}', pin)])
        pod = comp.bRepBodies.itemByName(f'Elevator Trim Pod {side}')
        out[side] = dict(pod_z=[round(pod.boundingBox.minPoint.z * 10, 1), round(pod.boundingBox.maxPoint.z * 10, 1)],
                         pod_cm3=round(pod.volume, 2), lumps=pod.lumps.count)
    return out
