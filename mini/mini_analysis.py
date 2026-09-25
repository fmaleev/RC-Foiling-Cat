"""Hydrostatics, VPP and rudder check for the RC Mini Cat 600, reusing the full-size analysis code."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'analysis'))
import vpp, control

K_L, K_S = 0.6, 0.68
FULL = [(0, 26.0, -28.0, 58.0), (150, 36.0, -40.0, 60.0), (350, 40.0, -45.0, 62.0), (550, 39.5, -44.0, 64.0),
        (750, 35.0, -37.0, 70.0), (880, 26.0, -26.0, 76.0), (960, 14.0, -12.0, 79.0), (1000, 4.0, 5.0, 81.0)]   # v1.3 fuller bows
STATIONS = [(x * K_L, max(hw * K_S, 2.4), zb * K_S, zt * K_S) for x, hw, zb, zt in FULL]

vpp.configure(stations=STATIONS, spacing=0.340, trunk=(0.040, 0.0064, 336),
              STRUT_C=0.036, RUDDER_C=0.027, Z_BOARD=-0.150, Z_RUDDER=-0.120,
              X_BOARD=0.336, X_RUDDER_M=-0.01175, RIG_HEIGHT=0.714)
CAD = json.load(open(os.path.join(HERE, 'cad_data_mini.json')))
control.CAD = CAD
control.X_RUDDER = -11.75
control.TILLER_ARM = 20.75          # stock to tie bar (CAD)
control.SERVO_HORN = 10.0           # MG90S horn hole used (assumed)
control.RUDDER_THROW = math.degrees(math.asin(control.SERVO_HORN * math.sin(math.radians(45)) / control.TILLER_ARM))


def main():
    b = vpp.load_pitch_limits(vpp.Boat('displacement', CAD), 'mini_600')
    zw = b.zw0
    num = den = 0.0
    for i in range(400):
        x = (i + .5) / 400 * vpp.L_HULL; a = vpp.sub_area(x, zw); num += a * x; den += a
    hull_vol = vpp.integrate(lambda x: math.pi * vpp.section(x)[0] * vpp.section(x)[2], 0, vpp.L_HULL, 400)
    statics = dict(mass_g=CAD['displacement']['mass_g'], waterline_z_mm=round(zw * 1000, 1),
                   hull_draft_mm=round((zw - min(vpp.ZB(vpp.L_HULL * i / 50) for i in range(51))) * 1000, 1),
                   freeboard_mid_mm=round((vpp.ZT(0.33) - zw) * 1000, 1), lcb_mm=round(num / den * 1000, 1),
                   lcg_mm=b.lcg, hull_volume_cm3_analytic=round(hull_vol * 1e6, 1),
                   one_hull_reserve=round(hull_vol * 1000 / b.M, 2), RM_Nm=round(b.RM, 3), heel_arm_m=round(b.heel_arm(False), 3),
                   sail_area_m2=round(b.A, 4))
    tab = {}
    for twa in (60, 90, 105):
        tab[twa] = [dict(tws_kn=t, **b.solve(t * 0.5144, twa)) for t in range(2, 15)]
    rudder = [control.rudder_check(b, t, twa) for twa in (60, 90, 105) for t in (4, 6, 8, 10, 12)]
    out = dict(statics=statics, vpp=tab, rudder_throw_deg=round(control.RUDDER_THROW, 1), rudder=rudder)
    json.dump(out, open(os.path.join(HERE, 'mini_results.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    r = main()
    print(json.dumps(r['statics'], indent=1))
    for twa, rows in r['vpp'].items():
        print('TWA', twa, ' '.join(f"{x['tws_kn']}kn:{x['V']}{'*' if x.get('depowered') else ''}" for x in rows))
    print('rudder throw', r['rudder_throw_deg'])
    worst = max(r['rudder'], key=lambda x: x['rudder_angle_deg'])
    print('worst rudder case', worst)
    print('min stall margin', min(x['stall_margin'] for x in r['rudder']), 'max servo kg cm', max(x['servo_torque_kgcm'] for x in r['rudder']))
