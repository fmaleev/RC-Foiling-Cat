"""Builds the slide deck's files (Slides artifact format: project/deck.json + project/slides/<id>.html) from the analysis
outputs. Images are uploaded to the deck's asset store first; their /_blob/ urls are read from slides/assets.json
(file name -> url). python3 slides/build_deck.py <out_root>"""
import csv, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
import vpp

J = lambda *p: json.load(open(os.path.join(ROOT, *p)))
CAD, VR, TOW, OPT = J('analysis', 'cad_data.json'), J('analysis', 'vpp_results.json'), J('analysis', 'takeoff_wind.json'), J('sim', 'optimization_results.json')
RO, PH, TS, FC, RES = J('sim', 'roll_options.json'), J('analysis', 'pitch_heave_results.json'), J('analysis', 'takeoff_sim_results.json'), J('analysis', 'foil_checks.json'), J('analysis', 'vpp_results.json')
ASSETS = json.load(open(os.path.join(HERE, 'assets.json')))
cost = lambda n: sum(float(r['total_usd']) for r in csv.DictReader(open(os.path.join(ROOT, 'bom', n + '.csv'))))
V = lambda cfg, twa, tws: [x for x in VR['vpp'][cfg][str(twa)] if x['tws_kn'] == tws][0]['V']
ad, ro = OPT['adopted'], RO['rows'][0]
ts8 = TS['beam reach, 8 kn']
FV = vpp.FOIL_VERSION

NAVY, SEA, CORAL, LIGHT, INK, MUTED, PALE = '#1B2F4B', '#2E7DB5', '#C8552E', '#F5F3EE', '#243447', '#5B6878', '#E6EEF5'
SANS, MONO = "'IBM Plex Sans', Arial, sans-serif", "'IBM Plex Mono', 'Courier New', monospace"
BASE = f"font-family:{SANS}; color:{INK}; padding:128px 128px 160px; display:flex; flex-direction:column; gap:40px"


def img(name, alt, w, h, fit='contain', extra=''):
    return f'<img src="{ASSETS[name]}" alt="{alt}" style="width:{w}px; height:{h}px; object-fit:{fit}; {extra}">'


def title(t, color=NAVY):
    return f'<h2 style="font-family:{SANS}; font-size:64px; font-weight:600; line-height:1.1; color:{color}">{t}</h2>'


def footer(n, dark=False):
    c = '#AFC2D6' if dark else MUTED
    return f'<p style="position:absolute; left:128px; bottom:64px; width:1664px; font-size:24px; color:{c}">RC foiling catamaran | model predictions, not yet measured | {n}</p>'


def card(head, body, bg='#FFFFFF'):
    return (f'<div style="flex:1; display:flex; flex-direction:column; gap:16px; background:{bg}; padding:40px; border-radius:16px; border:1px solid #DCE3EA">'
            f'<h3 style="font-size:40px; font-weight:600; line-height:1.2; color:{NAVY}">{head}</h3><p style="font-size:32px; line-height:1.4; color:{INK}">{body}</p></div>')


def big(num, label, color=SEA):
    return (f'<div style="display:flex; flex-direction:column; gap:8px"><p style="font-family:{MONO}; font-size:72px; font-weight:600; line-height:1.1; color:{color}">{num}</p>'
            f'<p style="font-size:28px; line-height:1.3; color:{MUTED}">{label}</p></div>')


S = {}
S['cover'] = f"""<section id="cover" data-transition="fade" style="background:{NAVY}; color:{LIGHT}; font-family:{SANS}; padding:128px; display:flex; flex-direction:row; align-items:center; gap:64px">
  <div style="flex:1; display:flex; flex-direction:column; gap:32px">
    <p style="font-size:28px; letter-spacing:4px; text-transform:uppercase; color:#8FB8DA">Design, analysis and build plan</p>
    <h1 style="font-size:96px; font-weight:600; line-height:1.05; color:{LIGHT}">A 1&#160;m RC foiling beach catamaran</h1>
    <p style="font-size:32px; color:#C9D6E3">Filip Maleev | Colorado College, Mathematics | September 2026</p>
  </div>
  {img('foiling.png', 'The foiling version in Autodesk Fusion', 760, 620, 'cover', 'border-radius:16px')}
  <aside>A radio-controlled catamaran modelled on full-size beach cats, with a hydrofoil option. Everything in this deck is a model prediction: nothing has been sailed yet.</aside>
</section>"""
S['question'] = f"""<section id="question" style="background:{LIGHT}; {BASE}">
  {title('Three questions before building')}
  <div style="display:flex; gap:32px">
    {card('Real proportions?', 'Can a 1&#160;m model follow the Hobie&#160;16 and Nacra&#160;17 rigs, or does scale get in the way?')}
    {card('Take-off?', 'Will the foiling version fly before the rig has to be depowered?')}
    {card('Control?', 'Can it be steered, and will it hold its height and pitch on the foils?')}
  </div>
  <p style="font-size:32px; line-height:1.4; color:{MUTED}">Answering them first set the build order: a 0.6&#160;m boat, then the 1&#160;m boat, then the foils.</p>
  {footer(2)}
  <aside>Heeling moment scales with length cubed but righting moment with length to the fourth, so a scaled-down rig is over-canvassed. Sail area was therefore set by the performance model, not by geometric scaling.</aside>
</section>"""
S['design'] = f"""<section id="design" style="background:{LIGHT}; {BASE}">
  {title('Designed in Autodesk Fusion, driven by scripts')}
  <div style="display:flex; gap:48px; align-items:start">
    <ul style="flex:1; font-size:32px; line-height:1.5; color:{INK}">
      <li>1&#160;m hulls printed as 0.8&#160;mm PETG skins, each segment a sealed compartment</li>
      <li>Square-top main and jib, {sum(x['area_m2'] for x in CAD['sails']):.2f}&#160;m&#178;, on a rotating wing mast</li>
      <li>Three sail controls (jib, traveler, mainsheet) on three servos</li>
      <li>Daggerboards first; L-foils with wand-driven flaps later</li>
      <li>Build-first {CAD['displacement']['mass_g']:.0f}&#160;g, foiling {CAD['foiling']['mass_g']:.0f}&#160;g, from the CAD</li>
    </ul>
    <div style="display:flex; flex-direction:column; gap:16px">
      {img('build_first.png', 'Build-first version with daggerboards', 620, 440, 'cover', 'border-radius:12px')}
    </div>
  </div>
  {footer(3)}
  <aside>The rig trims with three sliders in a custom Fusion add-in. Masses come from the CAD volumes with material densities and manufacturer weights for bought parts.</aside>
</section>"""
S['method'] = f"""<section id="method" style="background:{LIGHT}; {BASE}">
  {title('A purpose-written performance model')}
  <div style="display:flex; gap:24px">
    {card('Hulls', 'ITTC-57 friction and Michell thin-ship wave resistance with catamaran interference', PALE)}
    {card('Foils', 'Lifting-line lift and drag; flying trim in heave and pitch; roll authority', PALE)}
    {card('Sails', 'Lift and drag eased to stay within the heel and bow-down limits', PALE)}
  </div>
  <p style="font-size:32px; line-height:1.4; color:{INK}">Boat speed is where sail drive equals drag. The wave-resistance code was checked on the Wigley hull: grid-converged to 0.03&#160;%. A web flight simulator uses the same physics and matches the Python model to {OPT['vpp_agreement']['max_abs_dV']:.2f}&#160;m/s.</p>
  {footer(4)}
  <aside>All code is in the project repository; the analysis runs as one pipeline, and every document is regenerated from its outputs.</aside>
</section>"""
S['speed'] = f"""<section id="speed" style="background:{LIGHT}; {BASE}">
  {title('Predicted speed on a beam reach')}
  <div style="display:flex; gap:48px; align-items:center">
    {img('speed.png', 'Boat speed against true wind speed, build-first and foiling', 1100, 620)}
    <div style="flex:1; display:flex; flex-direction:column; gap:40px">
      {big(f"{V('displacement', 90, 8):.2f}&#160;m/s", 'build-first, 8&#160;kn of wind')}
      {big(f"{V('foiling', 90, 12):.2f}&#160;m/s", 'foiling, 12&#160;kn of wind', CORAL)}
    </div>
  </div>
  {footer(5)}
  <aside>Below take-off the foils cost the foiling version some speed; once flying it is much faster. The foiling curve starts where the boat leaves the water.</aside>
</section>"""
S['heave'] = f"""<section id="heave" data-transition="fade" style="background:{NAVY}; color:{LIGHT}; font-family:{SANS}; padding:128px 128px 160px; display:flex; flex-direction:column; justify-content:center; gap:48px">
  <h2 style="font-size:72px; font-weight:600; line-height:1.1; color:{LIGHT}">Fixed foils cannot hold their height</h2>
  <p style="font-size:40px; line-height:1.4; color:#C9D6E3">Lift grows with speed squared while weight stays the same, so nothing sets the flying height. A wand trailing from each bow drives a flap on that hull's foil. With it, heave and pitch are stable across the flying range: least damping ratio {PH['min_damping']:.2f}.</p>
  {footer(6, True)}
  <aside>The wand reads the bow height; the linkage gives {vpp.GEAR:g} degrees of flap per degree of wand. A linear two-degree-of-freedom model and a time-domain run both confirm the damping.</aside>
</section>"""
S['surprise'] = f"""<section id="surprise" style="background:{LIGHT}; {BASE}">
  {title('The first optimized foils would not have flown')}
  <div style="display:flex; gap:48px; align-items:center">
    {img('elevator.png', 'Elevator depth against boat speed for v2.1 and the adopted foils', 1100, 610)}
    <p style="flex:1; font-size:32px; line-height:1.4; color:{INK}">At speed the sail drive pitches the boat bow-down, so the elevators have to push down. Set at +4&#176;, they could only do that by tipping the whole boat forward, which lifts them out of the water.</p>
  </div>
  {footer(7)}
  <aside>The first simulator search (v2.1) assumed each foil carried a fixed share of the weight with the boat level. Adding the trim in heave and pitch reversed the result: neither the original foils nor v2.1 has any speed with a feasible trim.</aside>
</section>"""
S['fix'] = f"""<section id="fix" style="background:{LIGHT}; {BASE}">
  {title(f'The fix: point the elevators down ({FV})')}
  <div style="display:flex; gap:48px; align-items:center">
    <div style="flex:1; display:flex; flex-direction:column; gap:32px">
      {big(f"{ad['einc']:+g}&#176;", f"elevator angle, {-197 - ad['zel']:.0f}&#160;mm lower on longer rudders")}
      {big(f"{ad['wspan']:.0f} x {ad['wchord']:.0f}&#160;mm", f"main wings at {ad['winc']:+g}&#176;; elevators {ad['espan']:.0f} x {ad['echord']:.0f}&#160;mm")}
      <p style="font-size:32px; line-height:1.4; color:{INK}">Level at 12&#160;kn, elevators {ad['el_depth12_mm']:.0f}&#160;mm deep. A printed trim pod lets the angle be set on the water: one turn of an M2 screw is about 1.9&#176;.</p>
    </div>
    {img('trim_pod.png', 'Elevator trim pod at the rudder tip', 720, 520, 'cover', 'border-radius:12px')}
  </div>
  {footer(8)}
  <aside>Chosen from the search on the next slides: among robust designs within 5 percent of the fastest, the least wind to fly averaged over 60 and 90 degrees.</aside>
</section>"""
S['search'] = f"""<section id="search" style="background:{LIGHT}; {BASE}">
  {title(f"Searching {OPT['grid_size']:,} foil designs")}
  <div style="display:flex; gap:48px; align-items:center">
    {img('search.png', 'Wind needed to fly against speed at 12 kn for every feasible design', 1050, 600)}
    <ul style="flex:1; font-size:30px; line-height:1.45; color:{INK}">
      <li>Limits: stress, deflection, Reynolds number, pitch stability, damping</li>
      <li>Margins at 12&#160;kn: foils a chord deep, rudders 45&#160;mm in</li>
      <li>Robust to a halved or 1.5x drag couple and a 20&#160;mm CG shift</li>
      <li>{OPT['robust_total']:,} of {OPT['feasible_total']:,} feasible designs pass all of it</li>
    </ul>
  </div>
  {footer(9)}
  <aside>Without the margins the search settled on its limits: nose-down pitch lifts the rudders out and cuts their drag, which the model rewards and a gust would punish.</aside>
</section>"""
S['roll'] = f"""<section id="roll" style="background:{LIGHT}; {BASE}">
  {title('Near take-off the foils cannot hold the heel')}
  <div style="display:flex; gap:32px">
    {card(f"{TOW['90']:.1f}&#160;kn", 'wind to fly on a beam reach')}
    {card((f"{TOW['60']:.1f}&#160;kn" if TOW['60'] else 'over 16&#160;kn'), 'wind to fly at 60&#176; to the wind, where the side force is larger')}
    {card((f"{ro['stay_60']:.1f}&#160;kn" if ro['stay_60'] else '--'), 'enough to stay flying at 60&#176; after taking off on a reach and heading up')}
  </div>
  <p style="font-size:32px; line-height:1.4; color:{INK}">At take-off both wings are already at their lift limit, so the leeward hull must carry the heel and its drag holds the boat back. More flap travel does not help; technique does.</p>
  {footer(10)}
  <aside>Modelled as a skimming leeward hull: it carries whatever heeling moment the foils cannot, adding its drag, and the sails are eased when that gives more net thrust.</aside>
</section>"""
S['takeoff'] = f"""<section id="takeoff" style="background:{LIGHT}; {BASE}">
  {title('Take-off in time: no foil breaches')}
  <div style="display:flex; gap:48px; align-items:center">
    {img('takeoff.png', 'Speed, bow height and flap angle during take-off in 8 kn', 1100, 610)}
    <div style="flex:1; display:flex; flex-direction:column; gap:32px">
      {big(f"{ts8['takeoff_s']:.1f}&#160;s", 'from rest to flying, 8&#160;kn beam reach')}
      {big(f"{ts8['max_bow_rise_mm']:.0f}&#160;mm", 'largest bow rise above design height', CORAL)}
    </div>
  </div>
  {footer(11)}
  <aside>Surge, heave and pitch integrated in 2 ms steps with the wand and flap stops. The run settles at the performance model's steady speed, an independent check. A 4 kn gust while flying leaves the elevators at least {TS['beam reach, 9 kn, 4 kn gust at 20-25 s']['min_el_depth_mm']:.0f} mm deep.</aside>
</section>"""
S['build'] = f"""<section id="build" style="background:{PALE}; {BASE}">
  {title('Build plan and cost')}
  <div style="display:flex; gap:32px">
    {card(f"${cost('bom_mini'):.2f}", '0.6&#160;m Mini Cat, the first build', '#FFFFFF')}
    {card(f"${cost('bom_full_build_first'):.2f}", '1&#160;m boat with daggerboards', '#FFFFFF')}
    {card(f"${cost('bom_foiling_kit_v2'):.2f}", f'{FV} foiling kit, fitted later', '#FFFFFF')}
  </div>
  <p style="font-size:32px; line-height:1.4; color:{INK}">Every price was read on a retailer page (September 2026), before shipping and tax. Build manuals, 1:1 sail patterns, print-ready STLs and a tow-test plan with pass bands are ready.</p>
  {footer(12)}
  <aside>The tow test compares towing from the sail's centre of effort and from the mast foot; the pitch difference measures the bow-down couple, the model's largest uncertainty.</aside>
</section>"""
S['next'] = f"""<section id="next" style="background:{NAVY}; color:{LIGHT}; font-family:{SANS}; padding:128px 128px 160px; display:flex; flex-direction:column; justify-content:center; gap:40px">
  <h2 style="font-size:72px; font-weight:600; line-height:1.1; color:{LIGHT}">Next: put the model on the water</h2>
  <ul style="font-size:36px; line-height:1.5; color:#C9D6E3">
    <li>Build and GPS-log the Mini Cat against its predicted speed</li>
    <li>Build the 1&#160;m boat and check it the same way</li>
    <li>Tow-test the {FV} foils against the plan, then fly</li>
  </ul>
  <p style="font-size:26px; line-height:1.4; color:#AFC2D6">Developed with Claude (Anthropic) as an AI engineering assistant for the CAD scripting, analysis code and documents.</p>
  <aside>The first measurements will say which assumptions matter most: foil lift near Re 1e5, the drag model behind the pitch couple, and the flap effectiveness.</aside>
</section>"""
ORDER = ['cover', 'question', 'design', 'method', 'speed', 'heave', 'surprise', 'fix', 'search', 'roll', 'takeoff', 'build', 'next']

if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(os.path.join(out, 'project', 'slides'), exist_ok=True)
    for k in ORDER:
        open(os.path.join(out, 'project', 'slides', k + '.html'), 'w').write(S[k] + '\n')
    deck = {'v': 4, 'createdOnFiles': {'v': 1, 'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
            'title': 'RC Foiling Catamaran', 'order': ORDER,
            'sections': {'s1': {'description': 'The boat and the questions', 'start': 'cover'},
                         's2': {'description': 'How it was modelled and how fast it is', 'start': 'method'},
                         's3': {'description': 'What the foil analysis found and changed', 'start': 'heave'},
                         's4': {'description': 'Building and testing it', 'start': 'build'}},
            'faces': {'ibm-plex-sans': {'family': 'IBM Plex Sans', 'href': 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap'},
                      'ibm-plex-mono': {'family': 'IBM Plex Mono', 'href': 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap'}},
            'designSystems': []}
    json.dump(deck, open(os.path.join(out, 'project', 'deck.json'), 'w'), indent=1)
    print('written', len(ORDER), 'slides')
