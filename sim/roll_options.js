/* Roll near take-off: options, for the CAD foils (sim_core.js physics).
   node sim/roll_options.js  ->  sim/roll_options.json
   - take-off wind at 90 / 60 / 45 deg (from rest, auto trim);
   - wind needed to STAY flying at each angle once already flying (take off on a beam reach, then head up): the lowest
     wind with a flying equilibrium, found by searching boat speed down from the top of the flying range;
   - the same with more flap travel (does the flap stop limit roll authority, or the 0.8 cap on usable lift?). */
const fs = require('fs'), path = require('path');
const { makeSim } = require('./sim_core.js');
const D0 = require('./sim_data.json');
const ANGLES = [90, 60, 45];

function evaluate(label, D) {
  const S = makeSim(D);
  const M0 = Object.values(D.mass.foiling).reduce((a, v) => a + v, 0);
  const b = S.makeBoat({ cfg: 'foiling', tws: 8, twa: 90, trim: 'auto', clset: 1, sailPct: 100, ...S.CAD_FOILS, flaps: true, lcgShift: 0, massG: M0 });
  const stay = twa => {
    for (let t = 4; t <= 16 + 1e-9; t += 0.25)
      for (let V = b.vflyMax; V >= b.vto; V -= 0.02) {
        const s = S.drive(b, V, t * S.KN, twa), r = S.resistance(b, V, s.fy);
        if (r.mode === 'flying' && s.fx - r.R >= 0) return t;
      }
    return null;
  };
  const r3 = x => x === null || !isFinite(x) ? null : Math.round(x * 100) / 100;
  const out = { label, vto: r3(b.vto), rm_fly_Nm: [2.0, 2.2, 2.4, 2.6, 2.8, 3.0].map(V => ({ V, rm: r3(S.rmFly(b, V)) })), rm_full_Nm: r3(b.RM) };
  for (const a of ANGLES) { out[`takeoff_${a}`] = r3(S.minWindToFly(b, a, 12)); out[`stay_${a}`] = stay(a); }
  return out;
}

const variants = [['CAD design', D0]];
for (const tr of [20, 25]) { const D = JSON.parse(JSON.stringify(D0)); D.flap.travel_deg = tr; variants.push([`flap travel +-${tr} deg`, D]); }
const out = { generated_by: 'sim/roll_options.js', foils: D0.app.FOIL_VERSION, rows: variants.map(([l, D]) => evaluate(l, D)) };
fs.writeFileSync(path.join(__dirname, 'roll_options.json'), JSON.stringify(out, null, 1));
for (const r of out.rows) console.log(r.label, '| take-off 90/60/45:', r.takeoff_90, r.takeoff_60, r.takeoff_45, '| stay 90/60/45:', r.stay_90, r.stay_60, r.stay_45);
