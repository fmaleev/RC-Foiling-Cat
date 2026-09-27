"""Rig and crossbeam loads: shroud and forestay tension, mast compression and Euler buckling, crossbeam bending.

Load case 1 (sailing): the largest side force the boat can carry, F = RM_max / heel arm (RM_max from the heeled-hull
stability curve). Past it the boat heels further and sheds load, so it bounds the steady sail loads. The side force
acts at the area-weighted centre of effort and is carried by the mast (pinned at the step, held by the windward
shroud at the hounds); the jib's share (by area) loads the forestay, a cable with a 2 % sag ratio (assumed).
Load case 2 (servo at stall): case 1 plus the mainsheet at the sheet servo's stall torque. That is the hardest the boat
can pull on its own rig, e.g. a sheet held in against a stop, and it is taken as vertical mast compression. On the 1 m
boat the mainsheet runs from the car up to the boom and back (the loop that keeps the traveler from pulling on it), so
the boom, the car and the rear beam see twice the tail tension. The printed traveler car is checked against that
uplift: its two lips under the rail head bend as cantilevers (printed PETG, bending strength assumed).
Carbon tubes: E = 70 GPa and a bending strength of 300 MPa are assumed (no values are published for the tubes used).
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim'))
import rig_model
import fittings_geom as fg
sys.path.insert(0, HERE)
import vpp

E_CF, SIGMA_CF = 70000.0, 300.0      # N/mm2 (assumed)
SAG = 0.02                           # forestay sag / length (assumed)
SLAM_G = 5.0                         # vertical acceleration for the pod-beam check (assumed)
SIGMA_PETG = 25.0                    # N/mm2, printed PETG in bending, load in the layer plane (assumed)
BOARD_JOINT = dict(z=-0.020, share=0.35, rod_d=1.2, groove=1.4)   # cad_scripts/print_splits.py; share of the side force per board as in vpp.py
KGCM = 0.0980665                     # N m per kg cm
load = lambda *p: json.load(open(os.path.join(ROOT, *p)))
ST, VPP, MINI = load('analysis', 'stability_results.json'), load('analysis', 'vpp_results.json'), load('mini', 'mini_results.json')
CAD, CADM = load('analysis', 'cad_data.json'), load('mini', 'cad_data_mini.json')

BOATS = {   # tube sizes (OD, ID mm) from the parts lists; sheet servo stall torque at 4.8 V from the spec sheets
    'build_first_1m': dict(profile='full', rm=ST['build_first_1m']['RM_max_Nm'], arm=VPP['meta']['displacement']['heel_arm_disp'],
                           sails=CAD['sails'], mast=(12.0, 10.0), beam=(16.0, 14.0), hull_y=280.0,
                           sheet=('Feetech FS5115M, 14 kg cm at 4.8 V, tail 25 mm from the shaft', 14.0, 25.0), purchase=2),
    'foiling_1m': dict(profile='full', rm=ST['foiling_1m']['RM_max_Nm'], arm=VPP['meta']['foiling']['heel_arm_disp'],
                       sails=CAD['sails'], mast=(12.0, 10.0), beam=(16.0, 14.0), hull_y=280.0,
                       sheet=('Feetech FS5115M, 14 kg cm at 4.8 V, tail 25 mm from the shaft', 14.0, 25.0), purchase=2),
    'mini_600': dict(profile='mini', rm=ST['mini_600']['RM_max_Nm'], arm=MINI['statics']['heel_arm_m'],
                     sails=CADM['sails'], mast=(6.0, 4.0), beam=(10.0, 8.0), hull_y=170.0,
                     sheet=('JX W4505-2T, 5.25 kg cm at 4.8 V, 15 mm radius drum groove', 5.25, 15.0), purchase=1),
}
# pod items carried by the front beam (x = 620) and the pod beam (x = 350): (mass g, x mm), CAD centroids 2026-09-24
POD_ITEMS = [(172.44 * 1.27, 532.1), (62.58 * 1.27, 559.7), (62, 301), (50, 420), (14.9, 357.5), (123, 500), (49, 565),
             (10, 590), (20, 450)]   # shell, lid, mainsheet servo, traveler winch+drum, receiver, battery, jib winch+drum,
                                     # jib track+car, wiring allowance (placed mid-pod, assumed)


def tube(od, idd):
    return math.pi / 64 * (od ** 4 - idd ** 4), od / 2


def beam(P, span, od_id):
    """Point load P (N) at mid-span of a simply supported tube: stress (MPa), deflection (mm), safety factor."""
    I, c = tube(*od_id)
    M = P * span / 4
    s = M * c / I
    return dict(load_N=round(P, 2), stress_MPa=round(s, 1), deflection_mm=round(P * span ** 3 / (48 * E_CF * I), 2),
                safety_factor=round(SIGMA_CF / s, 1) if s else None)


def board_joint(F):
    """Build-first daggerboard printed in two pieces joined inside the trunk (cad_scripts/print_splits.py). The board is a
    lever on the trunk: supported at the hull bottom and at the deck, loaded by its share of the side force at mid-draught.
    The joint moment is carried by two 1.2 mm carbon rods bonded across it, one in a groove on each face at the thickest
    point (carbon strength as SIGMA_CF, assumed)."""
    vpp.configure()
    zw = vpp.sinkage(CAD['displacement']['mass_g'] / 1000 / vpp.RHO)
    zb, zt, zj = vpp.ZB(vpp.X_BOARD), vpp.ZT(vpp.X_BOARD), BOARD_JOINT['z']
    Fb = BOARD_JOINT['share'] * F
    M = Fb * (zb - (zw + vpp.Z_BOARD) / 2) * (zt - zj) / (zt - zb) * 1000            # N mm
    t = 0.12 * vpp.STRUT_C * 1000                                                    # board thickness, mm
    cap = SIGMA_CF * math.pi * (BOARD_JOINT['rod_d'] / 2) ** 2 * (t - BOARD_JOINT['groove'])
    return dict(board_force_N=round(Fb, 2), joint_moment_Nmm=round(M, 1), rod_capacity_Nmm=round(cap, 1), safety_factor=round(cap / M, 1))


def rig(name, B):
    rig_model.set_profile(B['profile'])
    R = rig_model.RIG
    F = B['rm'] / B['arm']
    A = sum(s['area_m2'] for s in B['sails'])
    z_ce = sum(s['area_m2'] * s['z_mm'] for s in B['sails']) / A
    A_jib = [s for s in B['sails'] if s['name'] == 'Jib'][0]['area_m2']
    z0, zh = R['mast_z0'], R['hounds_z']
    H = F * (z_ce - z0) / (zh - z0)
    cx, cy, cz = R['chainplate']
    d = (cx - R['mast_x'], cy - (R['mast_r'] - 1), cz - zh)
    Ls = math.sqrt(sum(v * v for v in d))
    T_s = H * Ls / abs(d[1])
    tx, tz = R['tack']
    Lf = math.hypot(tx - R['mast_x'], tz - zh)
    T_f = F * A_jib / A / (8 * SAG)
    C1 = T_s * abs(d[2]) / Ls + T_f * (zh - tz) / Lf
    T_ms = B['sheet'][1] * KGCM / (B['sheet'][2] / 1000)
    C2 = C1 + B['purchase'] * T_ms
    I, _ = tube(*B['mast'])
    P_cr = math.pi ** 2 * E_CF * I / (zh - z0) ** 2
    span = 2 * B['hull_y']
    if R['traveler']:        # 1 m: mast step over the front beam, mainsheet to the traveler car on the rear beam
        f_front, f_rear = C2, B['purchase'] * T_ms
    else:                    # mini: sheet lead on the box lid; the box levers the sheet load onto both beams
        lever = (R['mast_x'] - R['main_lead_x'][0]) / (R['front_beam_x'] - R['rear_beam_x'])
        f_front, f_rear = C1 + lever * T_ms, lever * T_ms
    out = dict(side_force_N=round(F, 2), ce_above_step_mm=round(z_ce - z0, 1), shroud_N=round(T_s, 1), forestay_N=round(T_f, 1),
               mainsheet_stall_N=round(T_ms, 1), sheet_servo=B['sheet'][0], mast_compression_N=dict(sailing=round(C1, 1), servo_stall=round(C2, 1)),
               mast_buckling_N=round(P_cr, 1), mast_buckling_length_mm=round(zh - z0, 1),
               buckling_safety=dict(sailing=round(P_cr / C1, 1), servo_stall=round(P_cr / C2, 1)),
               front_beam=beam(f_front, span, B['beam']), rear_beam=beam(f_rear, span, B['beam']))
    if R['traveler']:        # printed car on its T-rail (fittings_geom): two lips under the rail head, and the head's flanges
        (sw, sh), (hw, hh), c = fg.TT_STEM, fg.TT_HEAD, fg.CLR
        t_lip, arm = sh - 2 * c, (hw + c) - ((sw + c) + hw) / 2          # lip thickness; root to the middle of the bearing strip
        cap = min(SIGMA_PETG * 2 * fg.TC_HY * t * t / (3 * a) for t, a in ((t_lip, arm), (hh, ((sw + c) + hw) / 2 - sw)))
        up = B['purchase'] * T_ms
        out['traveler_car'] = dict(uplift_N=round(up, 1), capacity_N=round(cap, 1), safety_factor=round(cap / up, 1), lip_mm=round(t_lip, 2))
    if name == 'build_first_1m':
        out['daggerboard_joint'] = board_joint(F)
    if B['profile'] == 'full':
        R_pod = sum(m * (620 - x) for m, x in POD_ITEMS) / (620 - 350) * 9.81 / 1000
        out['pod_beam'] = dict(beam(R_pod * SLAM_G, span, (10.0, 8.0)), static_reaction_N=round(R_pod, 2), slam_g=SLAM_G)
    return out


if __name__ == '__main__':
    res = {k: rig(k, B) for k, B in BOATS.items()}
    res['assumptions'] = dict(E_carbon_MPa=E_CF, carbon_bending_strength_MPa=SIGMA_CF, petg_bending_strength_MPa=SIGMA_PETG, forestay_sag_ratio=SAG,
                              pod_slam_g=SLAM_G, mast='pinned at the step and the hounds', beams='simply supported between hull centres, load at mid-span')
    json.dump(res, open(os.path.join(HERE, 'structure_results.json'), 'w'), indent=1)
    for k, v in res.items():
        print(k, json.dumps(v))
