"""Costed bills of materials (USD, prices read on retailer pages 2026-09-23; two re-read 2026-09-24). Writes CSV + LaTeX tables."""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
HT = 'https://www.hobbytown.com'
CST_T = 'https://www.cstsales.com/Carbon_Fiber_Tubes.html'
CST_R = 'https://www.cstsales.com/carbon_rods.html'
KS = 'https://ksmetals.com/collections/12-long-music-wire'
S = dict(
    gt2=(38.99, HT + '/flysky-fsgt2e-2channel-transmitter-w-fsa3-receiver-fsy-fs-gt2ea3/p1592822', 'HobbyTown (re-read 2026-09-24; now sold with the FS-A3 receiver)'),
    i6x=(69.99, HT + '/flysky-i6x-6channel-afhds-2a-air-radio-system-w-ia6b-receiver-fsy-i6xia6b/p1674181', 'HobbyTown'),
    jx=(11.13, 'https://www.aliexpress.com/item/1005003265131874.html', 'AliExpress: listed $5.79 at 48% off; full price used'),
    mg90s=(2.59, 'https://www.waveshare.com/mg90s-servo.htm', 'Waveshare'),
    ecp640=(29.99, HT + '/ecopower-640t-13g-waterproof-metal-gear-digital-sub-micro-servo-ecp-640t/p859667', 'HobbyTown'),
    hs785=(56.99, 'https://hitecrcd.com/hs-785hb-karbonite-3-5-turn-winch-servo/', 'Hitec RCD'),
    fs5115=(32.06, 'https://www.pololu.com/product/3426', 'Pololu'),
    enel_aa=(12.75, 'https://www.microbattery.com/panasonic-bk-3mcca4ba-eneloop-aa-2100-cycle-ni-mh-pre-charged-rechargeable-batteries-4-pack80.html', 'MicroBattery'),
    holder=(4.00, HT + '/traxxas-4cell-aa-battery-holder-w-switch-cover-tra1523/p49945', 'HobbyTown'),
    aa_alk=(2.99, HT + '/flysky-fsgt2e-2channel-transmitter-w-fsa3-receiver-fsy-fs-gt2ea3/p1592822', 'HobbyTown (EcoPower AA x4 add-on)'),
    petg=(13.99, 'https://us.elegoo.com/products/rapid-petg-filament-1-75mm-colored-1kg', 'Elegoo US'),
    cf8x7=(17.20, CST_T, 'CST CS-529 1M'),
    cf6x4=(15.25, CST_T, 'CST CS-518 1M'),
    cf4=(8.49, CST_T, 'CST CS-508 1M'),
    cf10x8=(16.15, CST_T, 'CST CS-525 1M'),
    cf16x14=(16.28, 'https://windcatcherrc.com/product/carbon-fiber-tube-16mm-x-14mm-x-1000mm/', 'Wind Catcher RC (price from search listing, page not reachable from here)'),
    cf12x10=(12.26, 'https://www.readymaderc.com/products/details/carbon-fiber-tube-12mm-x-10mm-1m-long', 'RMRC'),
    rod12_1m=(3.47, CST_R, 'CST CS-316 1M'),
    rod12_2m=(5.25, CST_R, 'CST CS-316 2M'),
    mw125=(3.99, KS, 'K&S 0.125 in x 12 in'),
    mw093=(3.99, KS, 'K&S 0.093 in x 12 in'),
    mw047=(3.99, KS, 'K&S 0.047 in x 12 in (3 pcs)'),
    mw156=(4.99, KS, 'K&S 0.156 in x 12 in'),
    pushrod=(8.55, HT + '/dubro-pushrod-system-micro-dub847/p29360', 'HobbyTown'),
    m2set=(0.43, 'https://boltdepot.com/Product-Details?product=8697', 'Bolt Depot, per piece (read 2026-09-25)'),
    icarex=(21.99, 'https://jonesairfoils.com/products/icarex', 'Jones Airfoils, per metre (138 cm wide)'),
    tape10=(20.85, 'https://kiteboarding.com/proddetail.asp?prod=ripstop_2inch', 'kiteboarding.com: $15.00 base + $5.85 for 10 ft'),
    tape_half=(24.00, 'https://kiteboarding.com/proddetail.asp?prod=ripstop_2inch', 'kiteboarding.com: $15.00 base + $9.00 half roll'),
    line=(14.43, 'https://www.walmart.com/ip/PowerPro-Braided-Fishing-Line-30lb-x-150yd-ylw-21100300150Y/17117880', 'Walmart, PowerPro 30 lb x 150 yd (read 2026-09-24; the original eBay listing had ended)'),
    epoxy45=(13.99, HT + '/bob-smith-industries-quickcure-5-minute-epoxy-4-1-2oz-bsi201/p37081', 'HobbyTown'),
    epoxy9=(22.99, HT + '/bob-smith-industries-quickcure-5-minute-epoxy-9o-bsi202/p37082', 'HobbyTown'),
    ca=(4.79, HT + '/bob-smith-industries-instacure-gap-filling-ca-1-2oz-bsi106/p37055', 'HobbyTown'),
    ud12ft=(19.95, 'https://www.cstsales.com/heat_tack.html', 'CST CU-379: 2 in unidirectional carbon, 0.005 in, 12 ft'),
    el2=(20.70, 'https://www.easycomposites.us/el2-epoxy-laminating-resin', 'Easy Composites EL2, 500 g kit'),
    rod2_1m=(8.85, CST_R, 'CST CS-323 1M (2 mm)'),
)

MINI = [  # (group, item, what it is for, qty, source key)
    ('Radio', 'FlySky FS-i6X + FS-iA6B receiver', 'CH1 rudder, CH3 sails (non-centering stick); reused on the 1 m boat', 1, 'i6x'),
    ('Radio', 'AA alkaline x4', 'transmitter power', 1, 'aa_alk'),
    ('Servos', 'JX W4505-2T sail winch servo', 'both sheets on the stepped drum', 1, 'jx'),
    ('Servos', 'MG90S metal-gear micro servo', 'rudders via pushrod + tie bar', 1, 'mg90s'),
    ('Power', 'Panasonic eneloop AA 2000 mAh, 4-pack', 'receiver pack (4.8 V)', 1, 'enel_aa'),
    ('Power', 'Traxxas 4-cell AA holder with switch (TRA1523)', 'receiver battery box + on/off', 1, 'holder'),
    ('Printed', 'PETG filament 1 kg', 'hulls, box, lid, rudders, boards, drum (~470 g used)', 1, 'petg'),
    ('Carbon', 'Carbon tube 10 x 8 mm x 1 m', 'two 360 mm crossbeams', 1, 'cf10x8'),
    ('Carbon', 'Carbon tube 6 x 4 mm x 1 m', 'mast (800 mm)', 1, 'cf6x4'),
    ('Carbon', 'Carbon tube 4 mm OD x 1 m', 'boom (210 mm)', 1, 'cf4'),
    ('Carbon', 'Carbon rod 1.2 mm x 1 m', '3 battens', 1, 'rod12_1m'),
    ('Hardware', 'Music wire 0.125 in', 'rudder stocks', 1, 'mw125'),
    ('Hardware', 'Music wire 0.093 in', 'tie bar, tiller arms', 1, 'mw093'),
    ('Hardware', 'Music wire 0.047 in', 'rudder pushrod, sheet hooks', 1, 'mw047'),
    ('Hardware', 'Du-Bro micro pushrod system', 'clevis + tube for the rudder pushrod', 1, 'pushrod'),
    ('Sails', 'Icarex PC31 ripstop polyester, 1 m', 'main + jib (0.145 m2)', 1, 'icarex'),
    ('Sails', 'Ripstop sail tape 2 in, 10 ft', 'luff, batten pockets, corners', 1, 'tape10'),
    ('Rigging', 'Braided PE line 30 lb', 'stays, bridle, sheets', 1, 'line'),
    ('Adhesives', 'BSI 5-minute epoxy 4.5 oz', 'hull segment joints, beams, fittings', 1, 'epoxy45'),
    ('Adhesives', 'BSI gap-filling CA 1/2 oz', 'small parts, knots', 1, 'ca'),
]
MINI_OPTIONS = [('Upgrade', 'EcoPower 640T waterproof micro servo', 'instead of MG90S', 1, 'ecp640'),
                ('Budget', 'FlySky FS-GT2E + FS-A3 (car radio)', 'instead of FS-i6X; throttle trigger springs back to centre', 1, 'gt2')]

FULL = [
    ('Radio', 'FlySky FS-i6X + FS-iA6B receiver', '4 channels used: rudder, traveler, jib, mainsheet', 1, 'i6x'),
    ('Radio', 'AA alkaline x4', 'transmitter power', 1, 'aa_alk'),
    ('Servos', 'JX W4505-4T sail winch servo', 'traveler (about 231 mm of car travel, rig model)', 1, 'jx'),
    ('Servos', 'JX W4505-2T sail winch servo', 'jib sheet (about 93 mm of sheet, rig model)', 1, 'jx'),
    ('Servos', 'Feetech FS5115M standard servo', 'mainsheet tension', 1, 'fs5115'),
    ('Servos', 'MG90S metal-gear micro servo', 'rudders via pushrod + tie bar', 1, 'mg90s'),
    ('Power', 'Panasonic eneloop AA 2000 mAh, 4-pack', 'receiver pack (4.8 V)', 1, 'enel_aa'),
    ('Power', 'Traxxas 4-cell AA holder with switch (TRA1523)', 'receiver battery box + on/off', 1, 'holder'),
    ('Printed', 'PETG filament 1 kg', 'hulls, pod, lid, rudder-servo bracket and cover, rudders, boards, gudgeons, tracks, cars, mast fairing and fittings (~1.5 kg used, 1 m manual print list)', 2, 'petg'),
    ('Carbon', 'Carbon tube 16 x 14 mm x 1 m', 'two 600 mm crossbeams', 2, 'cf16x14'),
    ('Carbon', 'Carbon tube 12 x 10 mm x 1 m', 'two-piece mast (1.3 m)', 2, 'cf12x10'),
    ('Carbon', 'Carbon tube 10 x 8 mm x 1 m', 'mast joiner spigot (150 mm) and pod beam (600 mm)', 1, 'cf10x8'),
    ('Carbon', 'Carbon tube 8 x 7 mm x 1 m', 'boom (345 mm)', 1, 'cf8x7'),
    ('Carbon', 'Carbon rod 1.2 mm x 2 m', '8 battens', 1, 'rod12_2m'),
    ('Hardware', 'Music wire 0.156 in', 'rudder stocks, tie bar', 2, 'mw156'),
    ('Hardware', 'Music wire 0.093 in', 'rudder pushrod, track end-stop turning pins, gooseneck pin, boom sheet eye', 1, 'mw093'),
    ('Hardware', 'Du-Bro micro pushrod system', 'clevises', 1, 'pushrod'),
    ('Sails', 'Icarex PC31 ripstop polyester, 1 m', 'main + jib (0.40 m2)', 1, 'icarex'),
    ('Sails', 'Ripstop sail tape 2 in, half roll', 'luff, batten pockets, corners', 1, 'tape_half'),
    ('Rigging', 'Braided PE line 30 lb', 'stays, bridle, sheets', 1, 'line'),
    ('Adhesives', 'BSI 5-minute epoxy 9 oz', 'hull joints, beams, fittings', 1, 'epoxy9'),
    ('Adhesives', 'BSI gap-filling CA 1/2 oz', 'small parts', 1, 'ca'),
]


FOIL = [  # v2 foiling kit, printed cores + unidirectional carbon caps (0.5 mm = 4 layers per face)
    ('Printed', 'PETG filament 1 kg', 'L-foil, elevator and flap cores, trim pods, ride-height linkage (~290 g, 1 m manual print list)', 1, 'petg'),
    ('Carbon', 'Unidirectional carbon tape 2 in x 12 ft', 'spar caps: 4 layers per face on struts, wings, elevators', 2, 'ud12ft'),
    ('Adhesives', 'EL2 laminating epoxy 500 g', 'wet-out of the caps', 1, 'el2'),
    ('Carbon', 'Carbon rod 1.2 mm x 1 m', 'flap hinge pins', 1, 'rod12_1m'),
    ('Carbon', 'Carbon rod 2 mm x 1 m', 'two 300 mm ride-height wands, elevator pivot pins, wand and bellcrank axles', 1, 'rod2_1m'),
    ('Hardware', 'Music wire 0.047 in', 'wand-to-flap pushrods', 1, 'mw047'),
    ('Hardware', 'Du-Bro micro pushrod system', 'clevises for the flap linkage', 1, 'pushrod'),
    ('Hardware', 'M2 x 6 mm stainless set screw, cup point (Bolt Depot 8697)', 'elevator trim screws, two per trim pod', 4, 'm2set'),
]


def rows(items):
    out = []
    for g, name, use, q, k in items:
        p, url, src = S[k]
        out.append(dict(group=g, item=name, use=use, qty=q, unit_usd=p, total_usd=round(p * q, 2), source=src, url=url))
    return out


def tex_escape(s):
    return s.replace('&', r'\&').replace('%', r'\%').replace('#', r'\#').replace('_', r'\_')


def write(name, items):
    r = rows(items)
    with open(os.path.join(HERE, f'{name}.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(r[0].keys()))
        w.writeheader(); w.writerows(r)
    total = round(sum(x['total_usd'] for x in r), 2)
    with open(os.path.join(HERE, f'{name}.tex'), 'w') as f:
        for x in r:
            f.write(f"{tex_escape(x['group'])} & {tex_escape(x['item'])} & {tex_escape(x['use'])} & {x['qty']} & "
                    f"\\${x['unit_usd']:.2f} & \\${x['total_usd']:.2f} & \\href{{{x['url']}}}{{{tex_escape(x['source'].split(' (')[0].split(':')[0])}}} \\\\\n")
    return r, total


if __name__ == '__main__':
    for name, items in (('bom_mini', MINI), ('bom_mini_options', MINI_OPTIONS), ('bom_full_build_first', FULL), ('bom_foiling_kit_v2', FOIL)):
        r, total = write(name, items)
        by = {}
        for x in r:
            by[x['group']] = round(by.get(x['group'], 0) + x['total_usd'], 2)
        print(name, 'items', len(r), 'total $', total, by)
