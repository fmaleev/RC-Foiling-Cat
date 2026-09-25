"""Rig and crossbeam loads: shroud and forestay tension, mast compression and Euler buckling, crossbeam bending.

Load case 1 (sailing): the largest side force the boat can carry, F = RM_max / heel arm (RM_max from the heeled-hull
stability curve). Past it the boat heels further and sheds load, so it bounds the steady sail loads. The side force
acts at the area-weighted centre of effort and is carried by the mast (pinned at the step, held by the windward
shroud at the hounds); the jib's share (by area) loads the forestay, a cable with a 2 % sag ratio (assumed).
Load case 2 (servo at stall): case 1 plus the mainsheet at the sheet servo's stall torque. That is the hardest the boat
can pull on its own rig, e.g. a sheet held in against a stop, and it is taken as vertical mast compression.
Carbon tubes: E = 70 GPa and a bending strength of 300 MPa are assumed (no values are published for the tubes used).
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.expanduser('~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SailTrim'))
import rig_model

E_CF, SIGMA_CF = 70000.0, 300.0      # N/mm2 (assumed)
SAG = 0.02                           # forestay sag / length (assumed)
SLAM_G = 5.0                         # vertical acceleration for the pod-beam check (assumed)
KGCM = 0.0980665                     # N m per kg cm
load = lambda *p: json.load(open(os.path.join(ROOT, *p)))
ST, VPP, MINI = load('analysis', 'stability_results.json'), load('analysis', 'vpp_results.json'), load('mini', 'mini_results.json')
CAD, CADM = load('analysis', 'cad_data.json'), load('mini', 'cad_data_mini.json')

BOATS = {   # tube sizes (OD, ID mm) from the parts lists; sheet servo stall torque at 4.8 V from the spec sheets
    'build_first_1m': dict(profile='full', rm=ST['build_first_1m']['RM_max_Nm'], arm=VPP['meta']['displacement']['heel_arm_disp'],
                           sails=CAD['sails'], mast=(12.0, 10.0), beam=(16.0, 14.0), hull_y=280.0,
                           sheet=('Feetech FS5115M, 14 kg cm at 4.8 V, 15 mm arm (CAD)', 14.0, 15.0)),
    'foiling_1m': dict(profile='full', rm=ST['foiling_1m']['RM_max_Nm'], arm=VPP['meta']['foiling']['heel_arm_disp'],
                       sails=CAD['sails'], mast=(12.0, 10.0), beam=(16.0, 14.0), hull_y=280.0,
                       sheet=('Feetech FS5115M, 14 kg cm at 4.8 V, 15 mm arm (CAD)', 14.0, 15.0)),
    'mini_600': dict(profile='mini', rm=ST['mini_600']['RM_max_Nm'], arm=MINI['statics']['heel_arm_m'],
                     sails=CADM['sails'], mast=(6.0, 4.0), beam=(10.0, 8.0), hull_y=170.0,
                     sheet=('JX W4505-2T, 5.25 kg cm at 4.8 V, 15 mm radius drum groove', 5.25, 15.0)),
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
    C2 = C1 + T_ms
    I, _ = tube(*B['mast'])
    P_cr = math.pi ** 2 * E_CF * I / (zh - z0) ** 2
    span = 2 * B['hull_y']
    if R['traveler']:        # 1 m: mast step over the front beam, mainsheet to the traveler car on the rear beam
        f_front, f_rear = C2, T_ms
    else:                    # mini: sheet lead on the box lid; the box levers the sheet load onto both beams
        lever = (R['mast_x'] - R['main_lead_x'][0]) / (R['front_beam_x'] - R['rear_beam_x'])
        f_front, f_rear = C1 + lever * T_ms, lever * T_ms
    out = dict(side_force_N=round(F, 2), ce_above_step_mm=round(z_ce - z0, 1), shroud_N=round(T_s, 1), forestay_N=round(T_f, 1),
               mainsheet_stall_N=round(T_ms, 1), sheet_servo=B['sheet'][0], mast_compression_N=dict(sailing=round(C1, 1), servo_stall=round(C2, 1)),
               mast_buckling_N=round(P_cr, 1), mast_buckling_length_mm=round(zh - z0, 1),
               buckling_safety=dict(sailing=round(P_cr / C1, 1), servo_stall=round(P_cr / C2, 1)),
               front_beam=beam(f_front, span, B['beam']), rear_beam=beam(f_rear, span, B['beam']))
    if B['profile'] == 'full':
        R_pod = sum(m * (620 - x) for m, x in POD_ITEMS) / (620 - 350) * 9.81 / 1000
        out['pod_beam'] = dict(beam(R_pod * SLAM_G, span, (10.0, 8.0)), static_reaction_N=round(R_pod, 2), slam_g=SLAM_G)
    return out


if __name__ == '__main__':
    res = {k: rig(k, B) for k, B in BOATS.items()}
    res['assumptions'] = dict(E_carbon_MPa=E_CF, carbon_bending_strength_MPa=SIGMA_CF, forestay_sag_ratio=SAG,
                              pod_slam_g=SLAM_G, mast='pinned at the step and the hounds', beams='simply supported between hull centres, load at mid-span')
    json.dump(res, open(os.path.join(HERE, 'structure_results.json'), 'w'), indent=1)
    for k, v in res.items():
        print(k, json.dumps(v))
