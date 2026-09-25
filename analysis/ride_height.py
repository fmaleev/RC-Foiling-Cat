"""Ride-height control sizing for the foiling version: wand-driven trailing-edge flaps on the main L-foils.

Static trim per speed from vpp.Boat.fly_trim (heave and pitch, with the sail drive's bow-down couple): pitch from the
fixed-incidence elevators, flap angle from the main foils, bow height from the wand. Rows cover the flying range
(take-off to the top of the range, at most 5 m/s). Heave dynamics (1 DOF, linear):
  m h'' + c h' + k h = 0,  c = q (S_m a_m + S_e a_e) / V  (foil heave damping),
  k = q S_m a_m tau G dphi/dh  (wand feedback stiffness; k = 0 for fixed foils).
"""
import json, math, os
import vpp

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = json.load(open(os.path.join(HERE, 'cad_data.json')))

E_FLAP = 0.25                      # flap chord / foil chord (10 mm of 40 mm on the v2.1 foils)
VISC = 0.8                         # viscous reduction of the thin-airfoil flap effectiveness (assumed)
DELTA_MAX = 15.0                   # deg, flap travel each way
WAND_L, WAND_PHI0, GEAR = vpp.WAND_L, vpp.WAND_PHI0_DEG, vpp.GEAR   # m; deg below the boat's x axis; flap deg per wand deg
H_REF = WAND_L * math.sin(math.radians(WAND_PHI0))                   # m, wand hinge height above the water at the design ride height


def flap_tau(E):
    th = math.acos(2 * E - 1)
    return 1 - (th - math.sin(th)) / math.pi


def main():
    b = vpp.Boat('foiling', CAD)
    tau0 = flap_tau(E_FLAP)
    tau = tau0 * VISC
    assert abs(tau - vpp.FLAP_TAU) < 5e-4, 'vpp.FLAP_TAU out of date'
    dphi_dh = 1 / (WAND_L * math.cos(math.radians(WAND_PHI0)))    # rad of wand per m of height
    rows = []
    v_hi = min(b.vfly_max or 0.0, 5.0)
    V = math.ceil((b.vto or 99) * 10 - 1e-9) / 10
    while V <= v_hi + 1e-9:
        q = 0.5 * vpp.RHO * V * V
        t = b.fly_trim(V)
        theta, delta = t['theta'], t['delta']                                            # pitch (nose up +), flap (down +), rad
        dh = t['hp'] - H_REF                                                             # bow (wand hinge) height change
        c = q * (b.S_main * b.a_main + b.S_el * b.a_el) / V
        k = q * b.S_main * b.a_main * tau * GEAR * dphi_dh
        wn = math.sqrt(k / b.M); zeta = c / (2 * math.sqrt(k * b.M))
        rows.append(dict(V=round(V, 2), pitch_deg=round(math.degrees(theta), 2), flap_deg=round(math.degrees(delta), 2),
                         within_travel=abs(math.degrees(delta)) <= DELTA_MAX, ride_height_shift_mm=round(dh * 1000, 1),
                         elevator_lift_N=round(t['Le'], 2), main_lift_N=round(t['Lm'], 2), pitch_couple_Nm=round(t['Mp'], 3),
                         el_depth_mm=round(t['elD'] * 1000, 1), main_depth_mm=round(t['mD'] * 1000, 1),
                         rudder_immersion_mm=round(t['rudI'] * 1000, 1), hull_clearance_mm=round(t['hull'] * 1000, 1),
                         k_N_per_m=round(k, 1), c_Ns_per_m=round(c, 1), wn_hz=round(wn / (2 * math.pi), 2), zeta=round(zeta, 2),
                         static_mm_per_N=round(1000 / k, 2)))
        V = round(V + 0.1, 2)
    usable = [r for r in rows if r['within_travel']]
    out = dict(flap_chord_ratio=E_FLAP, tau_thin_airfoil=round(tau0, 3), tau_used=round(tau, 3), gear=GEAR,
               wand_length_m=WAND_L, wand_angle_deg=WAND_PHI0, dphi_dh_rad_per_m=round(dphi_dh, 2),
               controllable_speed_range_ms=[usable[0]['V'], usable[-1]['V']] if usable else None,
               takeoff_ms=b.vto and round(b.vto, 3), flying_range_top_ms=b.vfly_max and round(b.vfly_max, 3), flying_range_limit=b.fly_limit,
               fixed_foil_heave_stiffness='0 (neutral: nothing restores height)', rows=rows)
    json.dump(out, open(os.path.join(HERE, 'ride_height_results.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    r = main()
    print({k: v for k, v in r.items() if k != 'rows'})
    for x in r['rows'][::5]:
        print(x)
