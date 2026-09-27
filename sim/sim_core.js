/* Foil flight simulator physics, shared by sim/foil_sim.html (inlined by build_sim.py) and sim/optimize.js.
   Ported from analysis/vpp.py; hull wave resistance is interpolated from sim_data.json. */
function makeSim(D) {
const C = D.const, A = D.app, H = D.hull, T = D.trim;
const DEG = Math.PI / 180, KN = 0.5144, CL_USABLE = 0.8;
const cfITTC = re => { const l = Math.log10(Math.max(re, 1e4)) - 2; return 0.075 / (l * l); };
const profileDrag = (q, V, chord, span, tc) => span > 0 ? q * 2 * chord * span * cfITTC(V * chord / C.NU) * (1 + 2 * tc + 60 * tc ** 4) : 0;
const induced = (F, q, span) => (span > 0 && q > 0) ? F * F / (q * Math.PI * C.E_FOIL * span * span) : 0;
const sideInduced = (F, q, chord, span) => (span <= 0 || q <= 0) ? 0 : induced(Math.min(Math.abs(F), q * chord * span * C.CL_SIDE_MAX), q, span);
const liftSlope = ar => 2 * Math.PI / (1 + 2 / (C.E_FOIL * ar));

function interp1(xs, ys, x) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let i = 0; while (xs[i + 1] < x) i++;
  const t = (x - xs[i]) / (xs[i + 1] - xs[i]);
  return ys[i] + t * (ys[i + 1] - ys[i]);
}
const HM = H.masses, HS = H.speeds;
const colZW = H.rows.map(r => r.zw), colS = H.rows.map(r => r.S), colL = H.rows.map(r => r.lwl), colAT = H.rows.map(r => r.at);
function hullAt(m) { return { zw: interp1(HM, colZW, m), S: interp1(HM, colS, m), lwl: interp1(HM, colL, m), at: interp1(HM, colAT, m) }; }
function waveR(m, V) {   // bilinear in (hull mass, speed)
  if (m <= 0 || V < 0.3) return 0;
  let i = 0; while (i < HM.length - 2 && HM[i + 1] < m) i++;
  const tm = Math.min(1, Math.max(0, (m - HM[i]) / (HM[i + 1] - HM[i])));
  const a = interp1(HS, H.rows[i].rw, V), b = interp1(HS, H.rows[i + 1].rw, V);
  return a + tm * (b - a);
}

function makeBoat(p) {
  const foiling = p.cfg === 'foiling';
  const M = p.massG / 1000, W = M * C.G;
  const lcg = (foiling ? D.mass.lcg_foiling_mm : D.mass.lcg_displacement_mm) + p.lcgShift;
  const b = { p, foiling, M, W, lcg, RM: W * C.HULL_SPACING / 2 };
  // sails: similar planform scaled about the boom (0.132 m up)
  const s = p.sailPct / 100;
  b.Asail = D.sail_area * s;
  b.ce_x = D.sails.reduce((a_, x) => a_ + x.area_m2 * x.x_mm, 0) / D.sails.reduce((a_, x) => a_ + x.area_m2, 0);   // mm
  b.ce_z = 0.132 + (D.ce_z - 0.132) * Math.sqrt(s);
  const AR = (C.RIG_HEIGHT * Math.sqrt(s)) ** 2 / b.Asail;
  b.k = 1 / (Math.PI * C.E_SAIL * AR);
  // foils
  b.wc = p.wchord / 1000; b.ws = p.wspan / 1000; b.ec = p.echord / 1000; b.es = p.espan / 1000;
  b.a_main = liftSlope(b.ws / b.wc); b.a_el = liftSlope(b.es / b.ec);
  // lift coefficients are capped at CL_USABLE: 0.8 of an assumed section maximum of 1.0 near Re 1e5 (analysis/foil_checks.py)
  b.cl_main = Math.min(CL_USABLE, b.a_main * (p.winc * DEG - A.aL0_4412));
  b.cl_el = Math.min(CL_USABLE, b.a_el * p.einc * DEG);
  b.cl_main_flap = Math.min(CL_USABLE, b.a_main * (p.winc * DEG - A.aL0_4412) + (p.flaps ? b.a_main * D.flap.tau_used * D.flap.travel_deg * DEG : 0));
  b.share_el = (A.X_MAIN_FOIL - lcg) / (A.X_MAIN_FOIL - A.X_EL);
  b.S_main = 2 * b.ws * b.wc; b.S_el = 2 * b.es * b.ec;
  b.zel = (p.zel ?? A.Z_EL * 1000) / 1000;               // elevator quarter-chord height, boat frame (m)
  b.zrud = foiling ? b.zel - T.rudder_below_el : A.Z_RUDDER;   // the rudder blade ends just below the elevator
  b.vol = { strut: A.area_0012 * A.STRUT_C ** 2, rudder: A.area_0012 * A.RUDDER_C ** 2,
            wing: A.area_4412 * b.wc ** 2 * b.ws, el: A.area_0012 * b.ec ** 2 * b.es };
  b.zbot = foiling ? A.Z_WING : A.Z_BOARD;
  // static waterline
  let zw = -0.016;
  for (let i = 0; i < 6; i++) zw = hullAt(Math.max(0, (W - appBuoy(b, zw)) / C.G)).zw;
  b.zw0 = zw;
  const armTbl = foiling ? H.heel_arm_disp : H.heel_arm_disp_boards;
  b.armDisp = interp1(colZW, armTbl, zw) + (b.ce_z - D.ce_z);
  b.armFly = b.ce_z - T.z_fly + (T.z_fly - A.Z_WING) / 2;   // flying: water at the wand's design ride height
  b.hPitch = b.ce_z - (zw - (zw - H.zmin) / 2);
  const pr = D.pitch;
  b.rmPitch = foiling ? { h1: pr.rm_1hull * M / pr.mass_ref_kg, h2: pr.rm_2hull * M / pr.mass_ref_kg }
                      : { h1: pr.rm_1hull_disp * M / pr.mass_ref_disp_kg, h2: pr.rm_2hull_disp * M / pr.mass_ref_disp_kg };
  flyRange(b);
  return b;
}
function foilParts(p) {   // g: both wings, both elevators (solid carbon, 1.55 g/cm3) and the extra rudder blade length (1.0 g/cm3), as in the CAD mass export
  const ext = A.Z_EL * 1000 - (p.zel ?? A.Z_EL * 1000);
  return { main: 2 * 1.55e-3 * A.area_4412 * p.wchord ** 2 * p.wspan, el: 2 * 1.55e-3 * A.area_0012 * p.echord ** 2 * p.espan,
           rud: 2 * 1.0e-3 * A.area_0012 * (A.RUDDER_C * 1000) ** 2 * ext };
}
function foilMassG(p) { const f = foilParts(p); return f.main + f.el + f.rud; }
function foilLcgShift(p, massG) {   // mm: how far resizing the foils (from the CAD foils) moves the boat's centre of gravity
  const a = foilParts(p), c = foilParts(CAD_FOILS), X = { main: A.X_MAIN_FOIL, el: A.X_EL, rud: T.x_rudder_tip * 1000 };
  const dmx = Object.keys(X).reduce((s_, k) => s_ + (a[k] - c[k]) * (X[k] - D.mass.lcg_foiling_mm), 0);
  return dmx / massG;
}
const CAD_FOILS = { wspan: A.WING_SPAN * 1000, wchord: A.WING_C * 1000, winc: A.INC_MAIN_DEG, espan: A.EL_SPAN * 1000, echord: A.EL_C * 1000, einc: A.INC_EL_DEG, zel: A.Z_EL * 1000 };
function appBuoy(b, zw) {
  let v = 2 * b.vol.rudder * Math.max(0, zw - b.zrud);
  if (b.foiling) v += 2 * (b.vol.strut * Math.max(0, zw - A.Z_WING) + b.vol.wing + b.vol.el);
  else v += 2 * b.vol.strut * Math.max(0, zw - A.Z_BOARD);
  return v * C.RHO * C.G;
}
/* Static trim of the flying boat in heave and pitch (analysis/vpp.py Boat.fly_trim, analysis/pitch_trim.py).
   The sail drive equals the flying drag and acts at the centre of effort, the drag at the appendages: a bow-down couple
   that moves load from the elevators to the main foils. The fixed-incidence elevators then set the pitch, the wand-driven
   flaps make up the main foils' lift, and the wand (hinged at the bow, tip on the water, read in the boat frame) sets the
   bow height. Depths, rudder immersion and hull clearance follow from that attitude. */
function flyTrim(b, V, side = 0) {
  const q = 0.5 * C.RHO * V * V, W = b.W, p = b.p;
  const xm = A.X_MAIN_FOIL / 1000, xe = A.X_EL / 1000, xcg = b.lcg / 1000, a = xm - xcg, c = xcg - xe;
  let dm = T.z_fly - A.Z_WING, de = T.z_fly - b.zrud, t = null;
  for (let it = 0; it < 3; it++) {
    const Lm0 = t ? t.Lm : (1 - b.share_el) * W, Le0 = t ? t.Le : b.share_el * W;
    dm = Math.max(0, dm); de = Math.max(0, de);
    const parts = [
      [profileDrag(q, V, b.wc, b.ws, 0.12) * 2 + induced(Lm0 / 2, q, b.ws) * 2, A.Z_WING],
      [profileDrag(q, V, b.ec, b.es, 0.12) * 2 + induced(Le0 / 2, q, b.es) * 2, b.zel],
      [profileDrag(q, V, A.STRUT_C, dm, 0.12) * 2 + sideInduced(0.35 * side, q, A.STRUT_C, dm) * 2, A.Z_WING + dm / 2],
      [profileDrag(q, V, A.RUDDER_C, de, 0.12) * 2 + sideInduced(0.15 * side, q, A.RUDDER_C, de) * 2, b.zrud + de / 2],
      [2 * 0.24 * q * ((0.12 * A.STRUT_C) ** 2 + (0.12 * A.RUDDER_C) ** 2), A.Z_WING + dm]];
    const R = parts.reduce((s_, x) => s_ + x[0], 0), zD = parts.reduce((s_, x) => s_ + x[0] * x[1], 0) / R;
    const Mp = (p.coupleFactor ?? 1) * R * (b.ce_z - zD);   // coupleFactor: sensitivity studies only
    const Le = (W * a - Mp) / (a + c), Lm = W - Le;
    const cle = Le / (q * b.S_el), clm = Lm / (q * b.S_main);
    const theta = cle / b.a_el - p.einc * DEG;
    let delta = 0, hp = T.wand_l * Math.sin(T.phi0_deg * DEG);
    if (p.flaps) {
      delta = (clm / b.a_main - (p.winc * DEG + theta - A.aL0_4412)) / D.flap.tau_used;
      hp = T.wand_l * Math.sin(T.phi0_deg * DEG - delta / T.gear - theta);
    }
    const Hh = hp - (T.x_pivot * Math.sin(theta) + T.z_pivot * Math.cos(theta));
    const Z = (x, z) => Hh + x * Math.sin(theta) + z * Math.cos(theta);
    const elD = -Z(xe, b.zel), mD = -Z(xm, A.Z_WING), rudI = -Z(T.x_rudder_tip, b.zrud);
    const hull = Math.min(...T.keel.map(([x, z]) => Z(x, z)));
    t = { V, R, Mp, Le, Lm, cle, clm, theta, delta, hp, elD, mD, rudI, hull,
          clmAvail: p.flaps ? Infinity : b.a_main * (p.winc * DEG + theta - A.aL0_4412) };
    dm = mD; de = rudI;
  }
  {   // steering: the largest side force the sails can apply before heeling past RM_FRACTION, held by the trimmed rudders
    const fy = C.RM_FRACTION * b.RM / b.armFly, aS = 2 * A.STRUT_C * Math.max(t.mD, 0), aR = 2 * A.RUDDER_C * Math.max(t.rudI, 0);
    if (aR > 0) {
      const clr = (aS * T.x_board + aR * T.x_rudder_qc) / (aS + aR), fr = fy * (b.ce_x / 1000 - clr) / (clr - T.x_rudder_qc);
      t.steerDeg = fr / (q * aR) / liftSlope(t.rudI / A.RUDDER_C) / DEG;
    } else t.steerDeg = Infinity;
  }
  const why = Math.abs(t.cle) > CL_USABLE || t.clm > CL_USABLE ? 'foil lift limit'
    : t.clm > t.clmAvail + 1e-9 ? 'fixed main foils cannot carry their load'
    : p.flaps && Math.abs(t.delta) > D.flap.travel_deg * DEG ? 'flap travel'
    : t.hp <= 0 ? 'wand out of the water'
    : t.elD < 0.5 * b.ec ? 'elevator near the surface'
    : t.mD < 0.5 * b.wc ? 'main foil near the surface'
    : t.rudI < T.rudder_min ? 'rudder immersion'
    : t.steerDeg > T.steer_max_deg ? 'steering'
    : t.hull < 0 ? 'hull touches the water' : null;
  return { ...t, feasible: !why, why, pitchDeg: t.theta / DEG, flapDeg: t.delta / DEG };
}
function flyRange(b) {   // take-off = lowest speed with a feasible flying trim; flying ends where the trim stops being feasible
  b.vto = Infinity; b.vflyMax = null; b.flyLimit = null; b.LeMaxAbs = b.share_el * b.W; b.LmMax = (1 - b.share_el) * b.W;
  if (!b.foiling) { b.vto = null; return; }
  let prev = false;
  const v0 = Math.floor(Math.sqrt(2 * b.W / (C.RHO * CL_USABLE * (b.S_main + b.S_el))) / 0.04) * 0.04;   // below this no lift is enough
  for (let k = 0; ; k++) {
    const V = v0 + 0.04 * k;
    if (V > 6.0 + 1e-9) break;
    const t = flyTrim(b, V);
    if (t.feasible) {
      if (!prev) { let lo = V - 0.04, hi = V; for (let i = 0; i < 8; i++) { const m = (lo + hi) / 2; if (flyTrim(b, m).feasible) hi = m; else lo = m; } b.vto = hi; }
      prev = true; b.vflyMax = V;
      b.LeMaxAbs = Math.max(b.LeMaxAbs, Math.abs(t.Le)); b.LmMax = Math.max(b.LmMax, t.Lm);
    } else if (prev) { b.flyLimit = t.why; break; }
  }
  if (b.vflyMax !== null && b.flyLimit) { let lo = b.vflyMax, hi = b.vflyMax + 0.04; for (let i = 0; i < 8; i++) { const m = (lo + hi) / 2; if (flyTrim(b, m).feasible) lo = m; else hi = m; } b.vflyMax = lo; }
}
function takeoffSpeed(b) { return b.foiling ? b.vto : null; }
function rmFly(b, V) {   // largest righting moment while flying: leeward main foil at its flap and lift limit (vpp.Boat.rm_fly)
  V = Math.min(V, b.vflyMax ?? V);
  const key = Math.round(V * 1e4);
  if (!b._rm) b._rm = new Map();
  if (!b._rm.has(key)) {
    const t = flyTrim(b, V), q = 0.5 * C.RHO * V * V, p = b.p;
    const cl1 = Math.min(CL_USABLE, b.a_main * (p.winc * DEG + t.theta - A.aL0_4412 + (p.flaps ? D.flap.tau_used * D.flap.travel_deg * DEG : 0)));
    const lee = Math.min(q * b.S_main / 2 * cl1, t.Lm);
    b._rm.set(key, Math.max(0, 2 * lee - t.Lm) * C.HULL_SPACING / 2);
  }
  return b._rm.get(key);
}
function flapAt(b, V) { return flyTrim(b, V).flapDeg; }   // flap angle (deg) that holds the ride height at V
function footLift(b, q) {
  const clm = b.p.flaps ? b.cl_main_flap : b.cl_main;
  return { Lm: Math.min(q * b.S_main * Math.max(0, clm), (1 - b.share_el) * b.W), Le: Math.min(q * b.S_el * Math.max(0, b.cl_el), b.share_el * b.W) };
}
function oneHull(V, N) {   // one hull carrying N newtons (leeward hull skimming): vpp.Boat.one_hull
  if (N <= 0.01) return 0;
  const q = 0.5 * C.RHO * V * V, m2 = 2 * N / C.G, h = hullAt(m2);   // hull tables are for both hulls: 2N total
  const S1 = h.S / 2, at1 = h.at / 2;
  const Rf = q * S1 * cfITTC(V * Math.max(h.lwl, 0.05) / C.NU) * C.FORM_FACTOR;
  let i = 0; while (i < HM.length - 2 && HM[i + 1] < m2) i++;
  const tm = Math.min(1, Math.max(0, (m2 - HM[i]) / (HM[i + 1] - HM[i])));
  const Rw = V < 0.3 ? 0 : interp1(HS, H.rows[i].rw1, V) + tm * (interp1(HS, H.rows[i + 1].rw1, V) - interp1(HS, H.rows[i].rw1, V));
  const fnt = at1 > 0 ? V / Math.sqrt(2 * C.G * at1 / (H.hw_transom + H.hw_transom * 0.9)) : 99;
  return Rf + Rw + (fnt < 5 ? q * at1 * 0.2 * (1 - 0.2 * fnt) : 0);
}
function resistance(b, V, side, forceHull) {
  const q = 0.5 * C.RHO * V * V;
  if (b.foiling && !forceHull && V >= b.vto) {
    const t = flyTrim(b, Math.min(V, b.vflyMax ?? V), side);
    const N = Math.max(0, (Math.abs(side) * b.armFly - rmFly(b, V)) / C.HULL_SPACING);   // leeward hull load beyond the foils' roll authority
    return N > 0.01 ? { R: t.R + oneHull(V, N), mode: 'skimming', liftFrac: 1 - N / b.W, hullN: N, trim: t } : { R: t.R, mode: 'flying', liftFrac: 1, trim: t };
  }
  let lift = 0, Lm = 0, Le = 0;
  if (b.foiling) { ({ Lm, Le } = footLift(b, q)); lift = Lm + Le; }
  let zw = b.zw0, load = 0;
  for (let i = 0; i < 4; i++) { load = Math.max(0, b.W - lift - appBuoy(b, zw)); zw = hullAt(load / C.G).zw; }
  const h = hullAt(load / C.G);
  const Rf = load > 0 ? q * h.S * cfITTC(V * Math.max(h.lwl, 0.05) / C.NU) * C.FORM_FACTOR : 0;
  const Rw = waveR(load / C.G, V);
  const fnt = h.at > 0 ? V / Math.sqrt(2 * C.G * h.at / (2 * H.hw_transom + 2 * H.hw_transom * 0.9)) : 99;
  const Rtr = fnt < 5 ? q * h.at * 0.2 * (1 - 0.2 * fnt) : 0;
  const spanB = Math.min(zw, H.zb_board) - b.zbot, spanR = zw - b.zrud;
  let Dapp = profileDrag(q, V, A.STRUT_C, spanB, 0.12) * 2 + profileDrag(q, V, A.RUDDER_C, spanR, 0.12) * 2
    + 2 * 0.24 * q * (0.12 * A.RUDDER_C) ** 2 + sideInduced(0.35 * side, q, A.STRUT_C, spanB) * 2 + sideInduced(0.15 * side, q, A.RUDDER_C, spanR) * 2;
  if (b.foiling) Dapp += profileDrag(q, V, b.wc, b.ws, 0.12) * 2 + induced(Lm / 2, q, b.ws) * 2 + profileDrag(q, V, b.ec, b.es, 0.12) * 2 + induced(Le / 2, q, b.es) * 2;
  return { R: Rf + Rw + Rtr + Dapp, mode: b.foiling && lift > 0.02 * b.W ? 'lifting' : 'displacement', liftFrac: lift / b.W };
}
function sailForces(b, V, tws, twaDeg, flying, clFrac = 1) {   // clFrac < 1 eases the sails (skimming boats, auto trim)
  const twa = twaDeg * DEG, vx = V + tws * Math.cos(twa), vy = tws * Math.sin(twa);
  const va = Math.hypot(vx, vy), beta = Math.atan2(vy, vx), qa = 0.5 * C.RHO_A * va * va * b.Asail;
  const h = flying ? b.armFly : b.armDisp, fyMax = C.RM_FRACTION * b.RM / h;   // flying too: beyond the foils' roll authority the leeward hull skims
  const manual = b.p.trim === 'manual';
  if (beta > Math.PI / 2) {
    const f = (beta - Math.PI / 2) / (Math.PI / 2), clm = (manual ? Math.min(b.p.clset, C.CL_MAX) : C.CL_MAX) * clFrac;
    const cl = clm * (1 - f), cd = (C.CD0_SAIL + b.k * clm ** 2) * (1 - f) + 1.2 * f;
    const fx = qa * (cl * Math.sin(beta) - cd * Math.cos(beta)), fy = qa * (cl * Math.cos(beta) + cd * Math.sin(beta));
    return { fx, fy, cl, depowered: clFrac < 1, heel: Math.abs(fy) * h / b.RM };
  }
  let cl = Math.min(C.CL_MAX, Math.tan(beta) / (2 * b.k));
  if (manual) cl = Math.min(b.p.clset, C.CL_MAX);
  cl *= clFrac;
  const heelF = c => qa * (c * Math.cos(beta) + (C.CD0_SAIL + b.k * c * c) * Math.sin(beta));
  let depowered = clFrac < 1;
  if (heelF(cl) > fyMax) {
    depowered = true;
    const a_ = b.k * Math.sin(beta), b_ = Math.cos(beta), c_ = C.CD0_SAIL * Math.sin(beta) - fyMax / qa, disc = b_ * b_ - 4 * a_ * c_;
    cl = disc >= 0 && a_ > 0 ? Math.max(0, (-b_ + Math.sqrt(disc)) / (2 * a_)) : 0;
  }
  const cd = C.CD0_SAIL + b.k * cl * cl;
  return { fx: qa * (cl * Math.sin(beta) - cd * Math.cos(beta)), fy: qa * (cl * Math.cos(beta) + cd * Math.sin(beta)), cl, depowered, heel: (qa * (cl * Math.cos(beta) + cd * Math.sin(beta))) * h / b.RM };
}
function pitchLimit(b, s, flying) {   // vpp.Boat.pitch_limit
  if (flying || s.fx <= 0) return { ...s, pitch: 0 };
  const u = Math.abs(s.heel), m = s.fx * b.hPitch;
  let k = Math.min(1, u > 0.8 ? 0.8 / u : 1, C.RM_FRACTION * b.rmPitch.h2 / m);
  if (u > 0.8) { const kf = Math.min(1, C.RM_FRACTION * b.rmPitch.h1 / m); if (u * kf > 0.8) k = Math.max(k, kf); }
  const pitch = s.fx * k * b.hPitch / b.rmPitch.h2;
  return k < 1 ? { ...s, fx: s.fx * k, fy: s.fy * k, heel: s.heel * k, depowered: true, pitchLimited: true, pitch } : { ...s, pitch };
}
function drive(b, V, tws, twa, clFrac = 1) {
  const flying = b.foiling && V >= b.vto;
  return pitchLimit(b, sailForces(b, V, tws, twa, flying, clFrac), flying);
}
function step(b, V, tws, twa) {   // sail forces and resistance at V; a skimming boat eases the sails if that gives more net thrust (vpp.Boat.solve)
  let s = drive(b, V, tws, twa), r = resistance(b, V, s.fy);
  if (r.mode === 'skimming' && b.p.trim !== 'manual' && s.fx - r.R < 0) {   // only when full sail would stop the boat
    let best = s.fx - r.R;
    for (const k of [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]) {
      const s2 = drive(b, V, tws, twa, k), r2 = resistance(b, V, s2.fy);
      if (s2.fx - r2.R > best) { best = s2.fx - r2.R; s = s2; r = r2; }
    }
  }
  return { s, r };
}
function solve(b, tws, twa, vmax = 6, dv = 0.02) {
  let V = dv, last = null;
  while (V < vmax) {
    if (b.foiling && b.vflyMax !== null && V > b.vflyMax && V >= b.vto) {   // faster than the foils can be trimmed: ease the sails
      const r = resistance(b, b.vflyMax, 0);
      return { V: b.vflyMax, mode: 'flying', trimLimited: true, s: drive(b, b.vflyMax, tws, twa), r };
    }
    const { s, r } = step(b, V, tws, twa);
    if (s.fx - r.R < 0) return { V: V - dv / 2, mode: (last || r).mode, s, r: last || r };
    last = r; V += dv;
  }
  return { V: vmax, mode: 'flying', s: drive(b, vmax, tws, twa), r: last };
}
function minWindToFly(b, twa, iters = 9) {   // lowest wind (kn) that flies: scan up in 1 kn steps, then bisect the bracket
  if (!b.foiling || !isFinite(b.vto)) return null;
  const flies = t => solve(b, t * KN, twa).mode === 'flying';
  if (flies(2)) return 2;
  let hi = null;
  for (let t = 3; t <= 25; t++) if (flies(t)) { hi = t; break; }
  if (hi === null) return null;
  let lo = hi - 1;
  for (let i = 0; i < iters; i++) { const m = (lo + hi) / 2; if (flies(m)) hi = m; else lo = m; }
  return hi;
}
function accelRun(b, tws, twa, tEnd = 25, dt = 0.02) {
  const mEff = 1.1 * b.M, out = [];
  let V = 0.02, t = 0, tTake = null;
  while (t <= tEnd) {
    const { s, r } = step(b, V, tws, twa);
    if (r.mode === 'flying' && tTake === null) tTake = t;
    out.push({ t, V, lift: Math.min(1, r.liftFrac) * 100 });
    V = Math.max(0.02, V + (s.fx - r.R) / mEff * dt);
    if (b.foiling && b.vflyMax !== null && tTake !== null) V = Math.min(V, b.vflyMax);
    t += dt;
  }
  return { pts: out, tTake };
}

return { C, A, H, T, DEG, KN, CAD_FOILS, foilMassG, foilLcgShift, flyTrim, rmFly, flyRange, cfITTC, profileDrag, induced, liftSlope, interp1, makeBoat, appBuoy, takeoffSpeed, flapAt, footLift, resistance, sailForces, pitchLimit, drive, solve, minWindToFly, accelRun };
}
if (typeof module !== 'undefined') module.exports = { makeSim };
