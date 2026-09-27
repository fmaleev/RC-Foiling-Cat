/* Foil optimization with the flight simulator (sim_core.js, the same code as foil_sim.html).
   node sim/optimize.js  ->  sim/optimization_results.json and paper/data/opt_*.dat

   Each design sets the foil sizes and incidences and the elevator depth (the rudder blades end just below the elevators).
   Its mass changes with the solid-carbon foil volume and the rudder length (as in the CAD mass export). The physics include
   the flying trim in heave and pitch (sim_core.js flyTrim): the sail drive's bow-down couple, the pitch set by the
   fixed-incidence elevators, the wand and flaps. A design flies only between take-off and the speed where the trim stops
   being feasible (flap travel, foil lift, elevator or main foil within half a chord of the surface, less than 30 mm of
   rudder in the water, or the hull touching). Metrics:
   - wind needed to fly on a beam reach and at 60 deg (auto trim), take-off speed and the top of the flying range;
   - boat speed at 8 and 12 kn on a beam reach, and the pitch, flap angle, elevator depth and rudder immersion at 12 kn;
   - main-foil and elevator root stress (the largest flight load of a pair on one foil at 2 g) and main-foil tip deflection.
   Feasible: stress <= 100 MPa (safety 3 on an assumed 300 MPa), tip deflection <= 2 mm, chord Reynolds number >= 5e4 on
   both foils at take-off (assumed threshold: below it thin-airfoil lift is optimistic), heave damping ratio >= 0.5 with
   the wand gearing of analysis/ride_height.py, pitch static margin >= 30 mm with an elevator efficiency of 0.65
   (analysis/control.py; about 5 % of the 590 mm foil spacing, assumed), and flying at 12 kn on a beam reach with the top
   of the flying range at least 5 % above that speed (assumed margin for gusts).
   Operating margins (for the adopted design, on top of feasibility): at the 12 kn beam-reach speed the main foils and
   elevators run at least one chord deep and at least one rudder chord (45 mm) of rudder is in the water, and the flying
   range reaches 10 % above that speed. Without them the search settles on the hard limits: nose-down pitch lifts the rudders out and cuts
   their drag, which the model rewards but a gust would turn into ventilation.
   Robust: the design with margins still flies, and is not trim-limited at 12 kn, with the sail-drive pitch couple halved
   or 1.5 times larger and with the centre of gravity 20 mm forward or aft.
   Rule: among robust designs within 5 % of the fastest robust design at 12 kn, the least wind to fly averaged over 60 and
   90 deg (ties: faster, then lighter). The CAD design stays adopted while it is robust, has the margins, is within the 5 %
   band and needs at most TOL_KN more wind than the rule's best; TOL_KN is below the 0.12-0.14 kn by which the simulator's
   take-off wind differs from the VPP's (analysis/takeoff_wind.py), so smaller differences are not resolved by the model. */
const fs = require('fs'), path = require('path');
const { makeSim } = require('./sim_core.js');
const D = require('./sim_data.json');
const RH = require('../analysis/ride_height_results.json');   // wand gearing and flap effectiveness (analysis/ride_height.py)
const S = makeSim(D);
const { A, C, KN } = S;

const BASE = { cfg: 'foiling', tws: 8, twa: 90, trim: 'auto', clset: 1, sailPct: 100, flaps: true, lcgShift: 0 };
const V20 = { wspan: 200, wchord: 60, winc: 2, espan: 150, echord: 36, einc: 3, zel: -197 };   // original foils
const V21 = { wspan: 160, wchord: 40, winc: 0, espan: 140, echord: 32, einc: 4, zel: -197 };   // first pick, without the pitch trim
const V22 = { wspan: 160, wchord: 45, winc: 1.5, espan: 120, echord: 28, einc: -1, zel: -210 };   // pitch-trim pick before the fittings' masses
const M0 = Object.values(D.mass.foiling).reduce((a, v) => a + v, 0);   // CAD mass with the CAD's own foils
const SIGMA_MAX = 100, DEFL_MAX = 2.0, E_CF = 70000, RE_MIN = 5e4, ZETA_MIN = 0.5, RANGE_MARGIN = 1.05, SM_MIN = 30, ETA_EL = 0.65;
const OP = { el_chords: 1.0, rudder_mm: 45, range: 1.10 };   // operating margins at the 12 kn beam-reach speed
const TOL_KN = 0.1;

// NACA section properties per unit chord (second moment about the centroid, extreme fibre distance)
function naca(code, n = 80) {
  const m = +code[0] / 100, p = +code[1] / 10, t = +code.slice(2) / 100, up = [], lo = [];
  for (let i = 0; i <= n; i++) {
    const x = 0.5 * (1 - Math.cos(Math.PI * i / n));
    const yt = 5 * t * (0.2969 * Math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4);
    let yc = 0, dy = 0;
    if (m && x < p) { yc = m / p ** 2 * (2 * p * x - x * x); dy = 2 * m / p ** 2 * (p - x); }
    else if (m) { yc = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x * x); dy = 2 * m / (1 - p) ** 2 * (p - x); }
    const th = Math.atan(dy);
    up.push([x - yt * Math.sin(th), yc + yt * Math.cos(th)]); lo.push([x + yt * Math.sin(th), yc - yt * Math.cos(th)]);
  }
  return up.reverse().concat(lo.slice(1));
}
function sectionUnit(code) {
  const pts = naca(code); let Ar = 0, Cy = 0, Ixx = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length], cr = x0 * y1 - x1 * y0;
    Ar += cr; Cy += (y0 + y1) * cr; Ixx += (y0 * y0 + y0 * y1 + y1 * y1) * cr;
  }
  Ar /= 2; Cy /= 6 * Ar; Ixx /= 12;
  return { I: Math.abs(Ixx) - Math.abs(Ar) * Cy * Cy, c: Math.max(...pts.map(q => Math.abs(q[1] - Cy))) };
}
const SEC = { w: sectionUnit('4412'), e: sectionUnit('0012') };
const massG = p => M0 - S.foilMassG(S.CAD_FOILS) + S.foilMassG(p);
const r3 = x => x === null || x === undefined || !isFinite(x) ? null : Math.round(x * 1000) / 1000;
let nEval = 0;

function evaluate(over, full = false) {
  nEval++;
  const p = { ...BASE, ...S.CAD_FOILS, ...over };
  const b = S.makeBoat({ ...p, massG: massG(p), lcgShift: p.lcgShift + S.foilLcgShift(p, massG(p)) });   // foils move the CG
  const flies = isFinite(b.vto);
  const stress = (L, span, chord, sec) => (2 * L * span / 2) * sec.c * chord / (sec.I * chord ** 4);   // N, mm -> MPa
  const sw = stress(b.LmMax, p.wspan, p.wchord, SEC.w), se = stress(b.LeMaxAbs, p.espan, p.echord, SEC.e);
  const defl = (2 * b.LmMax / p.wspan) * p.wspan ** 4 / (8 * E_CF * SEC.w.I * p.wchord ** 4);
  const reMain = flies ? b.vto * p.wchord / 1000 / C.NU : null, reEl = flies ? b.vto * p.echord / 1000 / C.NU : null;
  const q3 = 0.5 * C.RHO * 9, cH = q3 * (b.S_main * b.a_main + b.S_el * b.a_el) / 3,
    kH = q3 * b.S_main * b.a_main * RH.tau_used * RH.gear * RH.dphi_dh_rad_per_m, zeta = cH / (2 * Math.sqrt(kH * b.M));
  const xnp = (b.a_main * b.S_main * A.X_MAIN_FOIL + ETA_EL * b.a_el * b.S_el * A.X_EL) / (b.a_main * b.S_main + ETA_EL * b.a_el * b.S_el);
  const sm = b.lcg - xnp;                                   // mm, CG ahead of the neutral point (analysis/control.py)
  const why0 = !flies ? 'does not fly' : sm < SM_MIN ? 'pitch static margin' : sw > SIGMA_MAX || se > SIGMA_MAX ? 'stress' : defl > DEFL_MAX ? 'deflection'
    : Math.min(reMain, reEl) < RE_MIN ? 'Reynolds number' : zeta < ZETA_MIN ? 'heave damping' : null;
  const g = { wspan: p.wspan, wchord: p.wchord, winc: p.winc, espan: p.espan, echord: p.echord, einc: p.einc, zel: p.zel, flaps: p.flaps, lcgShift: p.lcgShift,
    mass_g: r3(massG(p)), lcg_mm: r3(b.lcg), vto: r3(flies ? b.vto : null), vfly_max: r3(b.vflyMax), fly_limit: b.flyLimit,
    stress_main: r3(sw), stress_el: r3(se), defl_main: r3(defl), re_main_to: reMain && Math.round(reMain), re_el_to: reEl && Math.round(reEl),
    static_margin_mm: r3(sm), heave_zeta: r3(zeta), heave_hz_3ms: r3(Math.sqrt(kH / b.M) / (2 * Math.PI)), feasible: false, why: why0 };
  if (why0 && !full) return g;
  const s8 = S.solve(b, 8 * KN, 90), s12 = S.solve(b, 12 * KN, 90);
  const t12 = s12.mode === 'flying' ? S.flyTrim(b, s12.V, s12.s.fy) : null;
  Object.assign(g, { tws90: r3(S.minWindToFly(b, 90, 15)), tws60: r3(S.minWindToFly(b, 60, 15)), v8: r3(s8.V), v8_mode: s8.mode,
    v12: r3(s12.V), v12_mode: s12.mode, trim_limited_12: !!s12.trimLimited,
    pitch12: t12 && r3(t12.pitchDeg), flap12: t12 && r3(t12.flapDeg), el_depth12_mm: t12 && r3(t12.elD * 1000),
    rudder12_mm: t12 && r3(t12.rudI * 1000), main_depth12_mm: t12 && r3(t12.mD * 1000), elevator_lift12_N: t12 && r3(t12.Le) });
  const why = why0 || (g.tws90 === null ? 'does not fly on a beam reach' : s12.mode !== 'flying' ? 'not flying at 12 kn'
    : s12.trimLimited ? 'trim-limited at 12 kn' : (b.vflyMax < 6 - 1e-6 && b.vflyMax < RANGE_MARGIN * s12.V) ? 'flying-range margin' : null);
  g.feasible = !why; g.why = why;
  g.margins = g.feasible && t12.elD >= OP.el_chords * p.echord / 1000 && t12.mD >= OP.el_chords * p.wchord / 1000 && t12.rudI * 1000 >= OP.rudder_mm
    && (b.vflyMax >= 6 - 1e-6 || b.vflyMax >= OP.range * s12.V);
  g.tws_avg = g.tws90 !== null && g.tws60 !== null ? r3((g.tws90 + g.tws60) / 2) : null;
  if (g.margins) {   // robustness: pitch couple x0.5 / x1.5, CG +-20 mm
    g.robust_fail = null;
    for (const [lab, o] of [['couple x0.5', { coupleFactor: 0.5 }], ['couple x1.5', { coupleFactor: 1.5 }], ['CG 20 mm forward', { dx: 20 }], ['CG 20 mm aft', { dx: -20 }]]) {
      const q = { ...p, coupleFactor: o.coupleFactor ?? 1 };
      const bb = S.makeBoat({ ...q, massG: massG(p), lcgShift: p.lcgShift + S.foilLcgShift(p, massG(p)) + (o.dx || 0) });
      const ss = isFinite(bb.vto) ? S.solve(bb, 12 * KN, 90) : null;
      if (!ss || ss.mode !== 'flying' || ss.trimLimited) { g.robust_fail = lab; break; }
    }
    g.robust = !g.robust_fail;
  }
  return g;
}

const t0 = Date.now();
const ref20 = evaluate(V20, true), ref21 = evaluate(V21, true), ref22 = evaluate(V22, true);

// A. grid: sizes x incidences x elevator depth
const WINC = [0, 1, 2], EINC = [0, 0.5, 1, 1.5, 2], ZEL = [-215, -235, -255, -275];
const grid = [];
for (let ws = 140; ws <= 300; ws += 20) for (let wc = 40; wc <= 80; wc += 5)
  for (let es = 100; es <= 260; es += 20) for (let ec = 28; ec <= 52; ec += 4)
    for (const wi of WINC) for (const ei of EINC) for (const z of ZEL)
      grid.push(evaluate({ wspan: ws, wchord: wc, winc: wi, espan: es, echord: ec, einc: ei, zel: z }));
const whyCount = {};
for (const g of grid) whyCount[g.why || 'feasible'] = (whyCount[g.why || 'feasible'] || 0) + 1;
console.log('grid', grid.length, 'evaluations in', (Date.now() - t0) / 1000, 's', whyCount);

function pareto(pts) {   // minimise tws90, maximise v12
  const sorted = [...pts].sort((a, b) => a.tws90 - b.tws90 || b.v12 - a.v12), front = [];
  let best = -Infinity;
  for (const q of sorted) if (q.v12 > best + 1e-9) { front.push(q); best = q.v12; }
  return front;
}
const byRule = (pts, frac) => {   // least wind to fly among designs within frac of the fastest; ties: faster, lighter
  const vmax = Math.max(...pts.map(g => g.v12));
  return pts.filter(g => g.v12 >= frac * vmax - 1e-9).sort((a, b) => a.tws90 - b.tws90 || b.v12 - a.v12 || a.mass_g - b.mass_g)[0];
};
let feas = grid.filter(g => g.feasible);
const sizes = ({ wspan, wchord, espan, echord }) => ({ wspan, wchord, espan, echord });
const topSizes = (() => {   // the three best distinct foil sizes in the grid by the rule
  const rb = feas.filter(g => g.margins && g.robust && g.tws_avg !== null), vmax = Math.max(...rb.map(g => g.v12)), seen = new Set(), out = [];
  for (const g of rb.filter(g => g.v12 >= 0.95 * vmax - 1e-9).sort((a, b) => a.tws_avg - b.tws_avg || b.v12 - a.v12 || a.mass_g - b.mass_g)) {
    const k = JSON.stringify(sizes(g)); if (!seen.has(k)) { seen.add(k); out.push(g); } if (out.length === 3) break;
  }
  return out;
})();
const gridAdopted = topSizes[0];

// B. refine incidences and elevator depth for the three best sizes
const refine = [];
for (const t of topSizes)
  for (let wi = -1; wi <= 3 + 1e-9; wi += 0.5) for (let ei = -1; ei <= 3 + 1e-9; ei += 0.25)
    for (let z = -200; z >= -300; z -= 5) refine.push(evaluate({ ...sizes(t), winc: wi, einc: ei, zel: z }));
feas = feas.concat(refine.filter(g => g.feasible));
const withMargins = feas.filter(g => g.margins), robust = withMargins.filter(g => g.robust);
const front = pareto(feas), frontMargins = pareto(withMargins), frontRobust = pareto(robust);
const fastest = [...feas].sort((a, b) => b.v12 - a.v12 || a.tws90 - b.tws90 || a.mass_g - b.mass_g)[0];
const byAvg = (pts, frac) => {   // least wind to fly averaged over 60 and 90 deg among designs within frac of the fastest
  pts = pts.filter(g => g.tws_avg !== null);             // must fly at both headings
  const vmax = Math.max(...pts.map(g => g.v12));
  return pts.filter(g => g.v12 >= frac * vmax - 1e-9).sort((a, b) => a.tws_avg - b.tws_avg || b.v12 - a.v12 || a.mass_g - b.mass_g)[0];
};
const ruleBest = byAvg(robust, 0.95);
const cadEval = evaluate({ ...S.CAD_FOILS }, true);
const vmaxAvg = Math.max(...robust.filter(g => g.tws_avg !== null).map(g => g.v12));   // the same reference speed as byAvg
const cadOk = Boolean(cadEval.robust && cadEval.margins && cadEval.tws_avg !== null
  && cadEval.v12 >= 0.95 * vmaxAvg - 1e-9 && cadEval.tws_avg <= ruleBest.tws_avg + TOL_KN);
const adopted = cadOk ? cadEval : ruleBest;
const speed = byRule(robust, 0.99);          // for comparison: the fastest robust design (least beam-reach take-off wind within 1 %)
const lightwind = byAvg(robust, 0.85);

// C. can the foils already drawn (v2.0, v2.1) be saved by incidences and elevator depth alone?
const retrim = sz => {
  const pts = [];
  for (let wi = -1; wi <= 3 + 1e-9; wi += 0.5) for (let ei = -1; ei <= 3 + 1e-9; ei += 0.25)
    for (let z = -200; z >= -300; z -= 5) pts.push(evaluate({ ...sz, winc: wi, einc: ei, zel: z }));
  const f = pts.filter(g => g.feasible && g.margins && g.robust), why = {}, sm = pts.map(g => g.static_margin_mm);
  for (const g of pts) { const k = g.robust ? 'robust with margins' : g.margins ? 'not robust: ' + g.robust_fail : g.why || 'no operating margins'; why[k] = (why[k] || 0) + 1; }
  return { best: f.length ? byAvg(f, 0.95) : null, why, static_margin_mm: [Math.min(...sm), Math.max(...sm)] };
};
const rt20 = retrim(sizes(V20)), rt21 = retrim(sizes(V21)), retrim20 = rt20.best, retrim21 = rt21.best;
const adoptedFixed = evaluate({ ...adopted, flaps: false }, true);

// D. one-at-a-time sensitivity around the adopted design
const RANGES = { wspan: [120, 320, 20], wchord: [40, 90, 5], winc: [-1, 4, 0.5], espan: [80, 260, 20], echord: [24, 60, 4], einc: [-1, 4, 0.5], zel: [-270, -190, 5], lcgShift: [-60, 60, 10] };
const oat = {};
for (const [k, [lo, hi, st]] of Object.entries(RANGES)) {
  oat[k] = [];
  for (let v = lo; v <= hi + 1e-9; v += st) oat[k].push(evaluate({ ...adopted, [k]: Math.round(v * 100) / 100 }, true));
}

const cad = evaluate({ ...S.CAD_FOILS }, true);
// agreement with the Python VPP at the CAD design (the page's reference table: 6-10 kn, 60 and 90 deg)
const agree = D.reference.filter(r => [60, 90].includes(r.twa) && [6, 8, 10].includes(r.tws)).map(r => {
  const b = S.makeBoat({ ...BASE, ...S.CAD_FOILS, cfg: r.cfg, massG: Object.values(D.mass[r.cfg]).reduce((a, v) => a + v, 0) });
  const s = S.solve(b, r.tws * KN, r.twa);
  return { cfg: r.cfg, twa: r.twa, tws: r.tws, vpp: r.V, vpp_mode: r.mode, sim: r3(s.V), sim_mode: s.mode, dV: r3(Math.abs(s.V - r.V)) };
});
const out = {
  generated_by: 'sim/optimize.js', seconds: (Date.now() - t0) / 1000, evaluations: nEval,
  constraints: { static_margin_mm_min: SM_MIN, elevator_efficiency: ETA_EL, stress_MPa_max: SIGMA_MAX, main_tip_deflection_mm_max: DEFL_MAX, re_min: RE_MIN, zeta_min: ZETA_MIN, range_margin: RANGE_MARGIN,
                 rudder_min_mm: D.trim.rudder_min * 1000, flap_travel_deg: D.flap.travel_deg },
  grid_axes: { WINC, EINC, ZEL, sizes: 'wspan 140-300/20, wchord 40-80/5, espan 100-260/20, echord 28-52/4' },
  grid_size: grid.length, grid_feasible: grid.filter(g => g.feasible).length, grid_why: whyCount, refine_size: refine.length,
  operating_margins: OP, feasible_total: feas.length, with_margins: withMargins.length, robust_total: robust.length,
  v20: ref20, v21: ref21, v22: ref22, v20_retrimmed: retrim20, v21_retrimmed: retrim21, v20_retrim_why: rt20.why, v21_retrim_why: rt21.why, v20_retrim_static_margin_mm: rt20.static_margin_mm,
  grid_adopted: gridAdopted, top_sizes: topSizes.map(sizes), rule_best: ruleBest, adoption_tolerance_kn: TOL_KN, cad_is_adopted: cadOk,
  adopted, adopted_fixed_foils: adoptedFixed, speed_design: speed, fastest, lightwind, cad_design: cad, pareto: front, pareto_margins: frontMargins, pareto_robust: frontRobust, oat,
  vpp_agreement: { n: agree.length, max_abs_dV: Math.max(...agree.map(x => x.dV)), cases: agree },
};
fs.writeFileSync(path.join(__dirname, 'optimization_results.json'), JSON.stringify(out, null, 1));
const dat = (name, cols, rows) => fs.writeFileSync(path.join(__dirname, '..', 'paper', 'data', name), cols.join(' ') + '\n' + rows.map(r => r.join(' ')).join('\n') + '\n');
dat('opt_cloud.dat', ['tws90', 'v12', 'robust'], feas.map(g => [g.tws90, g.v12, g.robust ? 1 : 0]));
dat('opt_cloud_robust.dat', ['tws90', 'v12', 'tws60'], robust.map(g => [g.tws90, g.v12, g.tws60]));
dat('opt_front_robust.dat', ['tws90', 'v12'], frontRobust.map(g => [g.tws90, g.v12]));
dat('opt_front.dat', ['tws90', 'v12'], front.map(g => [g.tws90, g.v12]));
dat('opt_front_margins.dat', ['tws90', 'v12'], frontMargins.map(g => [g.tws90, g.v12]));
for (const k of Object.keys(RANGES))
  dat(`opt_oat_${k}.dat`, [k, 'tws90', 'v12', 'vto', 'vfly'], oat[k].map(g => [g[k], g.tws90 ?? 'nan', g.feasible ? g.v12 : 'nan', g.vto ?? 'nan', g.vfly_max ?? 'nan']));
const brief = g => g ? `${g.wspan}x${g.wchord} @${g.winc} | el ${g.espan}x${g.echord} @${g.einc} z ${g.zel} | m ${g.mass_g} | vto ${g.vto} fly<= ${g.vfly_max} (${g.fly_limit}) | tws90 ${g.tws90} tws60 ${g.tws60} | v8 ${g.v8} v12 ${g.v12} ${g.v12_mode}${g.trim_limited_12 ? ' TRIM-LIMITED' : ''} | pitch12 ${g.pitch12} flap12 ${g.flap12} el ${g.el_depth12_mm} main ${g.main_depth12_mm} rud ${g.rudder12_mm} | sw ${g.stress_main} se ${g.stress_el} d ${g.defl_main} | Re ${g.re_main_to}/${g.re_el_to} | SM ${g.static_margin_mm} zeta ${g.heave_zeta} | avg ${g.tws_avg} | ${g.feasible ? 'ok' : g.why}` : 'none';
console.log({ seconds: out.seconds, evaluations: nEval, feasible: feas.length, with_margins: withMargins.length, robust: robust.length, front: front.length, vpp_agreement_max_dV: out.vpp_agreement.max_abs_dV }, rt21.why);
for (const g of frontRobust) console.log('  front robust', brief(g));
console.log('CAD adopted:', cadOk, 'rule best avg', ruleBest.tws_avg, 'CAD avg', cadEval.tws_avg, 'v2.0 static margin', rt20.static_margin_mm);
for (const [k, g] of Object.entries({ ref20, ref21, retrim20, retrim21, gridAdopted, ruleBest, adopted, adoptedFixed, speed, fastest, lightwind, cad })) console.log(k.padEnd(12), brief(g));
