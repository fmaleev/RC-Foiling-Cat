"""Controllability checks: rudder authority (displacement build) and foil pitch/heave/steering (foiling).

Yaw balance (first order, steady sailing): the rudders must cancel
  M_side = Fy * (x_CE - x_CLR)          sail side force acting ahead of the lateral centre
  M_drag = R_hull * u * s/2             extra drag of the loaded leeward hull (u = heel utilisation)
Both turn the bow to leeward, so the rudders hold the bow up.
"""
import json, math, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = json.load(open(os.path.join(HERE, 'cad_data.json')))

X_RUDDER = -19.25           # rudder stock / quarter chord (mm)
CL_MAX_RUDDER = 0.8         # NACA 0012 at Re ~ 1e5 (assumed, conservative)
TILLER_ARM = 34.25          # mm, stock to tie bar (from CAD)
SERVO_HORN = 15.0           # mm (assumed), +/-45 deg servo throw
CP_OFFSET = 0.10            # hinge moment arm as fraction of chord (conservative)
RUDDER_THROW = math.degrees(math.asin(SERVO_HORN * math.sin(math.radians(45)) / TILLER_ARM))


def lateral_centre(zw, zbot_board, trim=None, z_rud=vpp.Z_RUDDER):
    """x of the centre of lateral resistance (mm) from underwater lateral areas."""
    parts = []
    if trim is None:  # hull in the water
        for i in range(200):
            x = (i + 0.5) / 200 * vpp.L_HULL
            d = max(0.0, zw - vpp.ZB(x)); parts.append((2 * d * vpp.L_HULL / 200, x * 1000))
        parts.append((2 * vpp.STRUT_C * (min(zw, vpp.ZB(vpp.X_BOARD)) - zbot_board), vpp.X_BOARD * 1000))
        parts.append((2 * vpp.RUDDER_C * (zw - z_rud), X_RUDDER))
    else:                # flying: immersed strut and rudder from the flying trim (vpp.Boat.fly_trim)
        parts.append((2 * vpp.STRUT_C * trim['mD'], vpp.X_BOARD * 1000))
        parts.append((2 * vpp.RUDDER_C * trim['rudI'], X_RUDDER))
    A = sum(a for a, _ in parts)
    return sum(a * x for a, x in parts) / A, A


def rudder_check(boat, tws_kn, twa, span_override=None):
    r = boat.solve(tws_kn * 0.5144, twa)
    V = r['V']
    vto = boat.takeoff_speed()
    flying = bool(vto and V >= vto)
    fx, fy, s = boat.pitch_limit(*boat.forces(V, tws_kn * 0.5144, twa, flying), flying)
    R, info = boat.resistance(V, fy)
    ce_x = sum(x['area_m2'] * x['x_mm'] for x in CAD['sails']) / sum(x['area_m2'] for x in CAD['sails'])
    q = 0.5 * vpp.RHO * V * V
    u = min(1.0, abs(s['heel_util']))
    if flying:
        trim = boat.fly_trim(min(V, boat.vfly_max), fy)
        clr, _ = lateral_centre(None, None, trim)
        span = span_override or trim['rudI']
        M = abs(fy) * (ce_x - clr) / 1000
        n_rudders = 2
    else:
        zw = info['zw']
        clr, _ = lateral_centre(zw, vpp.Z_WING if boat.foiling else vpp.Z_BOARD, z_rud=boat.z_rud)
        span = zw - boat.z_rud
        hull_drag = info['friction'] + info['wave'] + info['transom']
        M = abs(fy) * (ce_x - clr) / 1000 + hull_drag * u * vpp.HULL_SPACING / 2
        n_rudders = 1 if u > 0.8 else 2          # windward rudder lifts out when flying a hull
    lever = (clr - X_RUDDER) / 1000
    F_r = M / lever
    A_r = n_rudders * vpp.RUDDER_C * span
    a_r = vpp.lift_slope(span / vpp.RUDDER_C)
    CL = F_r / (q * A_r) if q > 0 else 0
    hinge = F_r / n_rudders * CP_OFFSET * vpp.RUDDER_C          # N m per rudder
    servo = n_rudders * hinge * SERVO_HORN / TILLER_ARM          # N m at servo
    return dict(tws_kn=tws_kn, twa=twa, V=round(V, 2), mode='foiling' if flying else 'displacement',
                heel_util=round(u, 2), rudder_immersed_mm=round(span * 1000, 1), yaw_moment_Nm=round(M, 3), CE_minus_CLR_mm=round(ce_x - clr, 1),
                rudder_force_N=round(F_r, 2), rudders_working=n_rudders, CL_needed=round(CL, 3),
                rudder_angle_deg=round(math.degrees(CL / a_r), 1), stall_margin=round(1 - CL / CL_MAX_RUDDER, 2),
                servo_torque_kgcm=round(servo / 0.0981, 2))


def foil_pitch_heave(boat):
    a_m, S_m, x_m = boat.a_main, boat.S_main, vpp.X_MAIN_FOIL
    a_e, S_e, x_e = boat.a_el, boat.S_el, vpp.X_EL
    out = {}
    for label, eta in (('no downwash', 1.0), ('elevator efficiency 0.65 (downwash/wake)', 0.65)):
        x_np = (a_m * S_m * x_m + eta * a_e * S_e * x_e) / (a_m * S_m + eta * a_e * S_e)
        out[label] = dict(neutral_point_x_mm=round(x_np, 1), cg_x_mm=boat.lcg, static_margin_mm=round(boat.lcg - x_np, 1),
                          stable=boat.lcg > x_np)
    heave = []
    for V in (2.0, 2.5, 3.0, 3.5, 4.0):
        q = 0.5 * vpp.RHO * V * V
        L_fixed = q * (S_m * boat.cl_main + S_e * boat.cl_el)
        cl_req = (1 - boat.share_el) * boat.W / (q * S_m)
        heave.append(dict(V=V, lift_at_fixed_incidence_N=round(L_fixed, 1), weight_N=round(boat.W, 1),
                          excess_pct=round((L_fixed / boat.W - 1) * 100, 0),
                          main_foil_angle_change_needed_deg=round(math.degrees((cl_req - boat.cl_main) / a_m), 1)))
    return out, heave


def main():
    res = dict(rudder_throw_deg=round(RUDDER_THROW, 1), assumptions=dict(CL_MAX_RUDDER=CL_MAX_RUDDER, SERVO_HORN_mm=SERVO_HORN,
                                                                          TILLER_ARM_mm=TILLER_ARM, CP_OFFSET=CP_OFFSET))
    for cfg in ('displacement', 'foiling'):
        b = vpp.load_pitch_limits(vpp.Boat(cfg, CAD), 'build_first_1m' if cfg == 'displacement' else 'foiling_1m')
        rows = [rudder_check(b, tws, twa) for twa in (60, 90, 105) for tws in (4, 6, 8, 10, 12, 14)]
        res[cfg] = rows
        if cfg == 'foiling':
            res['foil_pitch'], res['foil_heave'] = foil_pitch_heave(b)
            assert abs(RUDDER_THROW - vpp.RUDDER_THROW_DEG) < 0.05, 'vpp.RUDDER_THROW_DEG out of date'
            env, V = [], b.vto          # steering over the flying range with the largest (heel-limited) side force
            while V <= b.vfly_max + 1e-9:
                t = b.fly_trim(V)
                env.append(dict(V=round(V, 2), rudder_angle_deg=round(t['steer_deg'], 2), rudder_immersed_mm=round(t['rudI'] * 1000, 1)))
                V += 0.1
            w = max(env, key=lambda x: x['rudder_angle_deg'])
            res['foiling_steering_envelope'] = dict(max_deg=w['rudder_angle_deg'], at_V=w['V'], immersed_mm=w['rudder_immersed_mm'],
                                                    limit_deg=round(vpp.STEER_MAX_DEG, 1), rows=env)
    json.dump(res, open(os.path.join(HERE, 'control_results.json'), 'w'), indent=1)
    return res


if __name__ == '__main__':
    r = main()
    print('rudder throw available (deg):', r['rudder_throw_deg'])
    for cfg in ('displacement', 'foiling'):
        print('\n==', cfg)
        for x in r[cfg]:
            print(x)
    print('\n== foil pitch'); print(json.dumps(r['foil_pitch'], indent=1))
    print('\n== foil heave'); [print(h) for h in r['foil_heave']]
