# RC Mini Cat 600 - Build List

Compiled from `bom/make_bom.py`, `bom/bom_mini.csv`, `bom/bom_mini_options.csv`, `mini/manual/build_manual.py`,
`mini/manual/RC_Mini_Cat_Build_Manual.tex` (the compiled text of `RC_Mini_Cat_Build_Manual.pdf`), `mini/manual/print_list.json`
and `mini/manual_data.py`. Every purchased-part link below was checked today, 2026-09-24. The project's own baseline prices
were read 2026-09-23.

## Summary

- **Today's checked total (purchased parts, MINI list): $257.37**, vs the **$249.74** baseline in `bom_mini.csv` (+$7.63, +3.1%).
  The difference is entirely the one substituted part (braided rigging line, see below); every other item matched its
  baseline price exactly.
- Link status counts (20 MINI parts + 2 MINI_OPTIONS parts = 22 links checked):
  - **VERIFIED: 20** (includes 1 item, the FS-GT2 option, where the page loads and shows the same product line but the
    price has changed by more than 10%, and 1 item, the eneloop 4-pack, that is priced correctly but shown out of stock
    today)
  - **SUBSTITUTE: 1** (braided PE rigging line - original eBay listing was ended by the seller)
  - **NOT RE-VERIFIED: 1** (JX W4505-2T sail winch servo - AliExpress blocked automated access with a bot-check/CAPTCHA
    page on both the US and the geo-redirected `.ru` domain)
- Two purchased-part prices moved by more than 10% since 2026-09-23:
  - Rigging line: $6.80 to $14.43 (substitute; original listing dead)
  - FS-GT2 option (radio upgrade, not in the base total): $34.49 to $38.99 (+13.0%)

## Tools needed

From the manual's "Tools and shop supplies (assumed on hand)" list - none of these are in the costed parts list:

- 3D printer with a 220 mm bed that prints PETG
- Hobby knife and a steel rule
- Drill bits: 1.2, 1.5, 2.5 and 3.2 mm (a pin vise is enough)
- Side cutters and round-nose pliers (bending music wire)
- 240-grit sandpaper
- Masking tape
- Fine-tip soldering iron or a hot needle (melts clean holes in the sailcloth)
- Small screwdrivers (servo mounting screws)
- A bucket or sink (hull leak tests)
- A kitchen scale

## Parts to buy

| Part | Qty | Used for | Retailer | Link | Price checked 2026-09-24 | Status |
|---|---|---|---|---|---|---|
| FlySky FS-i6X + FS-iA6B receiver | 1 | CH1 rudder, CH3 sails; reused on the 1 m boat | HobbyTown | https://www.hobbytown.com/flysky-i6x-6channel-afhds-2a-air-radio-system-w-ia6b-receiver-fsy-i6xia6b/p1674181 | $69.99, In Stock Online | VERIFIED |
| AA alkaline x4 | 1 | transmitter power | HobbyTown (add-on shown on the transmitter page) | https://www.hobbytown.com/flysky-fsgt2e-2channel-transmitter-w-fsa3-receiver-fsy-fs-gt2ea3/p1592822 | $2.99 add-on | VERIFIED |
| JX W4505-2T sail winch servo | 1 | both sheets on the stepped drum | AliExpress | https://www.aliexpress.com/item/1005003265131874.html | UNKNOWN - page blocked | NOT RE-VERIFIED |
| MG90S metal-gear micro servo | 1 | rudders via pushrod + tie bar | Waveshare | https://www.waveshare.com/mg90s-servo.htm | $2.59, stock not stated | VERIFIED |
| Panasonic eneloop AA 2000 mAh, 4-pack | 1 | receiver pack (4.8 V) | MicroBattery | https://www.microbattery.com/panasonic-bk-3mcca4ba-eneloop-aa-2100-cycle-ni-mh-pre-charged-rechargeable-batteries-4-pack80.html | $12.75, **Out of stock today** | VERIFIED |
| Traxxas 4-cell AA holder w/switch (TRA1523) | 1 | receiver battery box + on/off | HobbyTown | https://www.hobbytown.com/traxxas-4cell-aa-battery-holder-w-switch-cover-tra1523/p49945 | $4.00, In Stock Online | VERIFIED |
| PETG filament 1 kg | 1 | hulls, box, lid, rudders, boards, drum (~462 g used) | Elegoo US | https://us.elegoo.com/products/rapid-petg-filament-1-75mm-colored-1kg | $13.99 | VERIFIED |
| Carbon tube 10 x 8 mm x 1 m | 1 | two 360 mm crossbeams | CST Sales | https://www.cstsales.com/Carbon_Fiber_Tubes.html | $16.15 (CS-525, 1 m) | VERIFIED |
| Carbon tube 6 x 4 mm x 1 m | 1 | mast (799 mm) | CST Sales | https://www.cstsales.com/Carbon_Fiber_Tubes.html | $15.25 (CS-518, 1 m) | VERIFIED |
| Carbon tube 4 mm OD x 1 m | 1 | boom (207 mm) | CST Sales | https://www.cstsales.com/Carbon_Fiber_Tubes.html | $8.49 (CS-508, 1 m) | VERIFIED |
| Carbon rod 1.2 mm x 1 m | 1 | 3 battens | CST Sales | https://www.cstsales.com/carbon_rods.html | $3.47 (CS-316, 1 m) | VERIFIED |
| Music wire 0.125 in x 12 in | 1 | rudder stocks | K&S (ksmetals.com) | https://ksmetals.com/collections/12-long-music-wire | $3.99, in stock | VERIFIED |
| Music wire 0.093 in x 12 in | 1 | tie bar, tiller arms | K&S (ksmetals.com) | https://ksmetals.com/collections/12-long-music-wire | $3.99, in stock | VERIFIED |
| Music wire 0.047 in x 12 in | 1 | rudder pushrod, sheet hooks | K&S (ksmetals.com) | https://ksmetals.com/collections/12-long-music-wire | $3.99, in stock | VERIFIED |
| Du-Bro micro pushrod system | 1 | clevis + tube for the rudder pushrod | HobbyTown | https://www.hobbytown.com/dubro-pushrod-system-micro-dub847/p29360 | $8.55, In Stock Online | VERIFIED |
| Icarex PC31 ripstop polyester, 1 m | 1 | main + jib (0.145 m2) | Jones Airfoils | https://jonesairfoils.com/products/icarex | $21.99/m, in stock (several colors; white and fluorescent orange sold out) | VERIFIED |
| Ripstop sail tape 2 in, 10 ft | 1 | luff, batten pockets, corners | kiteboarding.com | https://kiteboarding.com/proddetail.asp?prod=ripstop_2inch | $20.85 ($15.00 base roll + $5.85 for 10 ft) | VERIFIED |
| Braided PE line 30 lb | 1 | stays, bridle, sheets | ~~eBay~~ -> Walmart (SpiderWire out of stock; PowerPro substituted) | https://www.walmart.com/ip/PowerPro-Braided-Fishing-Line-30lb-x-150yd-ylw-21100300150Y/17117880 | $14.43 (PowerPro 30 lb x 150 yd) | SUBSTITUTE |
| BSI 5-minute epoxy 4.5 oz | 1 | hull segment joints, beams, fittings | HobbyTown | https://www.hobbytown.com/bob-smith-industries-quickcure-5-minute-epoxy-4-1-2oz-bsi201/p37081 | $13.99, In Stock Online | VERIFIED |
| BSI gap-filling CA 1/2 oz | 1 | small parts, knots | HobbyTown | https://www.hobbytown.com/bob-smith-industries-instacure-gap-filling-ca-1-2oz-bsi106/p37055 | $4.79, In Stock Online | VERIFIED |
| **Optional upgrade:** EcoPower 640T waterproof micro servo | 1 | replaces MG90S | HobbyTown | https://www.hobbytown.com/ecopower-640t-13g-waterproof-metal-gear-digital-sub-micro-servo-ecp-640t/p859667 | $29.99, In Stock Online | VERIFIED |
| **Optional budget swap:** FlySky FS-GT2E + FS-A3 (car radio) | 1 | replaces FS-i6X | HobbyTown | https://www.hobbytown.com/flysky-fsgt2e-2channel-transmitter-w-fsa3-receiver-fsy-fs-gt2ea3/p1592822 | $38.99, In Stock Online (was $34.49, +13.0%; page now bundles an FS-A3 receiver, not the FS-GR3E named in the parts list) | VERIFIED (price changed) |

Notes on the CST Sales and K&S rows: all three CST carbon-tube prices and the carbon-rod price, and all three K&S
music-wire prices, were confirmed on the vendor's single product-listing page (the URL is the same page for all
diameters/sizes in that group); each specific size and price matched the parts list exactly.

## Parts to print

From `mini/manual/print_list.json` and the manual's print table (PETG, 0.4 mm nozzle, 0.2 mm layers; hull/box/lid
segments: 2 perimeters, 0% infill, sealed-compartment shells; rudders/daggerboards/drum: 3 perimeters, 40% infill).
About 462 g of the 1 kg spool is used in total.

| Part | Qty | Grams each | Print notes | STL file (`mini/stl/`) |
|---|---|---|---|---|
| Hull Port Seg 1 | 1 | 44.1 | stand on the joint (bulkhead) face | Hull_Port_Seg_1.stl |
| Hull Port Seg 2 | 1 | 56.0 | stand on the joint (bulkhead) face | Hull_Port_Seg_2.stl |
| Hull Port Seg 3 | 1 | 38.3 | stand on the joint (bulkhead) face | Hull_Port_Seg_3.stl |
| Hull Stbd Seg 1 | 1 | 44.1 | mirror of port | Hull_Stbd_Seg_1.stl |
| Hull Stbd Seg 2 | 1 | 56.0 | mirror of port | Hull_Stbd_Seg_2.stl |
| Hull Stbd Seg 3 | 1 | 38.3 | mirror of port | Hull_Stbd_Seg_3.stl |
| Box Half 1 | 1 | 36.7 | open side up | Box_Half_1.stl |
| Box Half 2 | 1 | 42.1 | open side up | Box_Half_2.stl |
| Box Lid Half 1 | 1 | 10.5 | flat | Box_Lid_Half_1.stl |
| Box Lid Half 2 | 1 | 10.4 | flat | Box_Lid_Half_2.stl |
| Daggerboard | 2 | 27.1 each | flat; 3 perimeters, 40% infill | Daggerboard_x2.stl |
| Rudder Blade | 2 | 9.9 each | flat; 3 perimeters, 40% infill | Rudder_Blade_x2.stl |
| Gudgeon | 2 | 2.3 each | any orientation | Gudgeon_x2.stl |
| Winch Drum (30 / 16.2 mm stepped grooves) | 1 | 6.6 | large flange down | Winch_Drum_stepped_30_16mm.stl |

Assembly files (not printed): `mini/cad/RC_Mini_Cat_600.step` and `.f3d`.

## Not in the costed parts list

| Item | Checked link | Price | Notes |
|---|---|---|---|
| NiMH charger for the eneloop AA cells | Walmart - Panasonic Battery Charger with 4 eneloop AA Rechargeable Batteries, 4 Count: https://www.walmart.com/ip/Panasonic-Battery-Charger-with-4-eneloop-AA-Rechargeable-Batteries-4-Count/124706107 | $32.09, checked 2026-09-24, addable to cart | 4-position charger holds 2-4 cells; bundle includes 4 extra precharged eneloop AA cells (a spare set beyond the pack already in the BOM) |
| Small screws | UNKNOWN | UNKNOWN | Manual step 4 says both servos are fixed "with the screws supplied with them" - no separate screw purchase identified in the manual text |
| Zip ties | UNKNOWN | UNKNOWN | Not mentioned anywhere in the manual text |
| Sandpaper (240-grit) | UNKNOWN | UNKNOWN | The manual itself lists this under tools "assumed on hand," not as a purchased part; no specific product was checked |
| Servo extension lead | UNKNOWN | UNKNOWN | Not called for: the manual's wiring step plugs the rudder servo into CH1 and the winch into CH3 directly, both mounted in the same small electronics box as the receiver |

## Build steps

Numbered checklist in the manual's order, with the dimensions and checks the manual text gives.

1. **Hulls**
   - [ ] Sand the joint faces of the three segments of each hull flat.
   - [ ] Dry-fit so the segments line up on the outside; epoxy segment 1 to 2 and 2 to 3, held against a straight edge while curing.
   - [ ] Leak test each hull underwater for 30 seconds; seal any bubbling leak with CA or epoxy (each segment is its own sealed compartment).
   - [ ] Drill the chainplate eye: 1.5 mm hole fore-aft through the deck boss, 360 mm from the transom. Drill a 1.2 mm hole in each bow tip and epoxy in a loop of 0.047 in music wire for the bridle.
   - [ ] Check: each finished hull weighs about 145 g (with glue) and floats level.

2. **Crossbeams and frame**
   - [ ] Cut the 10 mm carbon tube into two 360 mm beams (score with a knife, then snap; wear a mask sanding carbon).
   - [ ] Epoxy both beams into one hull's sockets, slide the other hull on, lay the frame flat and equalize the two diagonals to within 1 mm before epoxying the second hull.
   - [ ] Check: hull centerlines are 340 mm apart at both beams.

3. **Rudders and steering linkage**
   - [ ] Drill a 3.2 mm pivot hole in each rudder blade, 6.75 mm behind the leading edge (25% of the 27 mm chord).
   - [ ] Push 0.125 in music-wire stock through each blade and gudgeon; epoxy blade to wire (not gudgeon), and gudgeon to the transom.
   - [ ] Bend two tiller arms from 0.093 in wire, 20.75 mm from stock to tie-bar hole, level and about 6 mm above the deck; join with a 0.093 in tie bar.
   - [ ] Run a 0.047 in pushrod from the rudder servo horn (hole 10 mm from center) through the box's rear-wall slot to the tie bar, with a Du-Bro clevis at the servo end.
   - [ ] Check: with the servo centred, both rudders point straight; full travel gives about +/-20 degrees of rudder.

4. **Electronics box and servos**
   - [ ] Epoxy the two box halves together, and separately the two lid halves.
   - [ ] Seat the sail winch (shaft up) in the front rails and the MG90S in the rear rails, ears resting on the rails; route each servo wire out through the rail notch; drill 1.5 mm pilot holes and screw down with the servos' own screws.
   - [ ] Check: each servo case hangs clear of the floor by its ears; shim under the ears with 1 mm plastic if the case touches bottom first (rails are sized from the Feetech FS5115M drawing since JX does not publish the winch's ear height).
   - [ ] Load four charged eneloop AA cells into the Traxxas holder, set it in the battery cradle; stick the receiver to the floor between rudder servo and battery.
   - [ ] Plug in: rudder servo to CH1, sail winch to CH3, battery lead to a spare channel (e.g. CH6); keep both antennas straight and near the top of the box.
   - [ ] Glue the printed stepped drum to the winch horn and screw it on.
   - [ ] Snap the box onto the two beams (saddles clip over the 10 mm tubes); seal the lid seam with electrical tape before sailing.

5. **Mast and standing rigging**
   - [ ] Cut the 6 mm tube to 799 mm; plug the top with epoxy; mark the hounds 574 mm above the mast foot and whip/CA a line binding there.
   - [ ] Stand the mast in the box-floor socket through the lid hole.
   - [ ] Tie the stays (braided line, length between knots): forestay 529 mm (hounds to bridle point); two bridle legs 206 mm (bridle point to bow loops); two shrouds 602 mm (hounds to chainplate eyes).
   - [ ] Cut the 4 mm tube to a 207 mm boom; loop line through its front end around the mast so it sits about 5 mm above the lid and swings freely.
   - [ ] Check: mast stands straight from the side and behind; all stays just tight.

6. **Rig and sails**
   - [ ] Print `mini/manual/sail_patterns_1to1.pdf` at 100%; confirm the 100 mm scale bar measures 100 mm.
   - [ ] Cut the main and jib from Icarex using the pattern; main needs the extra 25 mm luff allowance for the mast sleeve.
   - [ ] Main: fold and tape the 25 mm luff sleeve; cut three battens from 1.2 mm carbon rod (185, 155, 111 mm) and tape them at 178, 357, 536 mm above the foot.
   - [ ] Jib: fold a 10 mm sleeve along the 508 mm luff around the forestay line.
   - [ ] Reinforce head, tack and clew of both sails with two layers of sail tape; melt a 2 mm hole in each clew.
   - [ ] Sheets and drum: mainsheet from the boom end through the lid fairlead 165 mm from the transom to the 30 mm groove; jib sheet from the clew through the fairlead 355 mm from the transom to the 16.2 mm groove; wind both the same way (mainsheet pays out 153 mm, jib sheet 83 mm, both 1.63 drum turns).

7. **Radio setup**
   - [ ] Bind receiver to transmitter (FlySky procedure), select an airplane model.
   - [ ] Set CH3 end points so full stick travel gives 1.63 drum turns (about 82% if the winch makes 2 turns at 100%); reverse CH3 if needed so stick down means sheets in.
   - [ ] Set CH1 so the right stick steers as expected (stick right, bow turns right).
   - [ ] Set failsafe: rudders centred, sheets eased on signal loss.

8. **Balance and first float test**
   - [ ] Rig the boat; balance on two fingers under the beams - should balance about 258 mm forward of the transoms (move the battery if not).
   - [ ] Float in a tub: hulls should sit level, about 24 mm deep; leave 10 minutes and check for water in the box.

9. **First sail**
   - [ ] Choose 3-8 kn of wind, a small pond, and a non-swimming retrieval method (a capsized cat does not right itself).
   - [ ] Start on a beam reach, sheets half out; sheet in until it accelerates, ease when a hull lifts.
   - [ ] Above about 8 kn, ease sheets to keep the windward hull down.
   - [ ] Watch the bows (pitchpole risk) near 7.5/8.5/10/13.5 kn at 60/90/120/150 degrees off the wind; ease sheets as the leeward bow starts to dig.
   - [ ] If the boat won't hold a course, adjust jib sheeting (the jib rides 4 degrees wider than the main on the drum) or shift the mast step.

## Notes

- Baseline prices in `bom_mini.csv` were read 2026-09-23; the checks in this document were made the next day, 2026-09-24,
  so day-to-day price noise of a few cents on some items is expected and was not treated as a meaningful change.
- The manual's own price caveats (`RC_Mini_Cat_Build_Manual.tex`, appendix): "Two prices carry extra uncertainty: the JX
  winch (AliExpress listed it on sale; the full price is used here) and the 16 x 14 mm carbon tube (price taken from a
  search listing because the store's page was not reachable)." The 16 x 14 mm Wind Catcher RC tube is used only on the
  1 m boat's parts list, not the Mini's, so it was not in scope here. The JX winch caveat is directly relevant: this
  agent could not load the AliExpress listing at all (see below).
- **JX W4505-2T winch servo (AliExpress) - NOT RE-VERIFIED.** `https://www.aliexpress.com/item/1005003265131874.html`
  redirected to `aliexpress.ru/item/1005003265131874.html?gatewayAdapt=glo2rus`, which returned a bot-check page
  ("Пройдите проверку" / "Pass verification") instead of the listing. A web search independently found the same item
  URL titled "Jx W4505-4t Plastic Gears Standard Size Sail Servo Winch..." at "$5.79 US, 48% off," consistent with the
  parts list's note ($5.79 / 0.52 = $11.13 full price), and a related listing title mentions "W4505-2T/4T/6T" variants
  on one product page. This is corroborating evidence only, not a verified page load; the price is kept at $11.13 and
  marked NOT RE-VERIFIED per the task rules.
- **Braided PE line - SUBSTITUTED.** The original eBay listing (`https://ebay.com/itm/202929797830`, "Power Braided
  Fishing Line 100M-1000M Super Strong Dynema Spider 10LB-100LB," $6.80) shows "This listing was ended by the seller
  ... because there was an error in the listing." It is dead. Substituted with PowerPro Braided Fishing Line, 30 lb
  test, 150 yd, Hi-Vis Yellow, at Walmart ($14.43, checked 2026-09-24, addable to cart) - a name-brand 30 lb braided
  line from a reputable retailer, matching the original spec. A SpiderWire 30 lb/300 yd alternative was also checked
  at Walmart but is out of stock.
- **FlySky FS-GT2 option - price changed.** The parts list names this option "FlySky FS-GT2 + FS-GR3E (car radio)" at
  $34.49. The live page at the same URL is now titled "Flysky FS-GT2E 2-Channel Transmitter w/FS-A3 Receiver," priced
  at $38.99 (+13.0%). HobbyTown appears to have changed which receiver is bundled with this transmitter since the
  parts list was made; the transmitter itself (FS-GT2/FS-GT2E, 2-channel, AA-powered) is the same product line.
- **Eneloop AA 4-pack - out of stock.** MicroBattery.com still lists the Panasonic eneloop AA 2000 mAh 4-pack at the
  BOM's exact price ($12.75) but the page currently reads "Out of stock." The owner should either wait for restock or
  source the cells elsewhere before starting the build; a charger+battery bundle alternative is listed above under
  "Not in the costed parts list."
- All CST Sales (carbon tubes and rods) and K&S (music wire) prices and sizes were confirmed against the vendor's
  listing pages and matched the parts list exactly, including sizes used only on the 1 m boat (cf8x7, rod12_2m) that
  happened to appear on the same pages.
- Not checked (out of scope): `cf16x14` (Wind Catcher RC) and other keys in `bom/make_bom.py`'s `S` dict that are used
  only by the `FULL` (1 m boat) or `FOIL` (v2 foiling kit) lists, since the task scope is the Mini's `MINI` and
  `MINI_OPTIONS` lists only.
