"""Shopping list for the whole project (Mini Cat, 1 m build-first boat, foiling kit) from the costed parts lists in bom/
(make_bom.py). python3 bom/build_shopping_list.py && tectonic bom/RC_Catamaran_Shopping_List.tex"""
import csv, os
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
load = lambda n: list(csv.DictReader(open(os.path.join(HERE, n + '.csv'))))
STAGES = [('Stage 1: Mini Cat 600 (build first)', 'mini', load('bom_mini')),
          ('Stage 2: 1 m boat with daggerboards', 'full', load('bom_full_build_first')),
          ('Stage 3: foiling kit (v2.3 foils)', 'foil', load('bom_foiling_kit_v2'))]
ALTS = load('bom_alternatives')
HAS_ALT = {r['item'] for r in ALTS if r['role'] == 'base'}
CARRY = ('Radio', 'Power')          # the mini's radio and NiMH pack carry over to the 1 m boat (both build manuals)
STORES = {'hobbytown.com': 'HobbyTown', 'aliexpress.com': 'AliExpress', 'waveshare.com': 'Waveshare', 'microbattery.com': 'MicroBattery',
          'us.elegoo.com': 'Elegoo US', 'cstsales.com': 'CST (cstsales.com)', 'ksmetals.com': 'K\\&S Metals', 'jonesairfoils.com': 'Jones Airfoils',
          'kiteboarding.com': 'kiteboarding.com', 'walmart.com': 'Walmart', 'pololu.com': 'Pololu', 'windcatcherrc.com': 'Wind Catcher RC',
          'readymaderc.com': 'RMRC', 'easycomposites.us': 'Easy Composites', 'boltdepot.com': 'Bolt Depot'}


def esc(s):
    return s.replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('%', r'\%').replace('#', r'\#').replace('_', r'\_').replace('$', r'\$').replace('~', 'about ')


money = lambda x: r'\$' + f'{x:,.2f}'
total = lambda rows: sum(float(r['total_usd']) for r in rows)
store = lambda url: STORES.get(urlparse(url).netloc.replace('www.', ''), esc(urlparse(url).netloc))
links = []                          # numbered product links, printed at the end


def ref(url):
    if url not in links:
        links.append(url)
    return links.index(url) + 1


def rows(items, carry_note=False):
    out = []
    for r in items:
        mark = (r'$^\dagger$' if carry_note and r['group'] in CARRY else '') + (r'$^\ast$' if r['item'] in HAS_ALT else '')
        note = '' if esc(r['source']) == store(r['url']) else f"\\newline{{\\footnotesize\\itshape {esc(r['source'])}}}"
        out.append(f"{esc(r['item'])}{mark}{note} & {esc(r['use'])} & {r['qty']} & {money(float(r['unit_usd']))} & {money(float(r['total_usd']))} & "
                   f"{store(r['url'])} [{ref(r['url'])}] \\\\")
    return '\n'.join(out)



def alt_blocks():
    out = []
    for k in dict.fromkeys(r['base_key'] for r in ALTS):
        grp = [r for r in ALTS if r['base_key'] == k]
        base = grp[0]
        body = '\n'.join(f"{'Recommended (listed)' if r['role'] == 'base' else esc(r['kind'])}: {esc(r['item'])}\\newline{{\\footnotesize {store(r['url'])} [{ref(r['url'])}]}} & {money(float(r['unit_usd']))} & {esc(r['pros'])} & {esc(r['cons'])} \\\\"
                         for r in grp)
        out.append(r"""\subsection*{""" + esc(base['item']) + r""" \normalfont\small (""" + esc(base['lists']) + r""")}
{\small
\begin{longtable}{L{3.6cm}rL{5.4cm}L{5.4cm}}
\toprule
Option & Unit & Pros & Cons \\
\midrule
""" + body + r"""
\bottomrule
\end{longtable}}""")
    return '\n'.join(out)


mini_t, full_t, foil_t = (total(s[2]) for s in STAGES)
carry_t = sum(float(r['total_usd']) for r in STAGES[1][2] if r['group'] in CARRY)
full_new = full_t - carry_t
by_store = {}
for title, key, items in STAGES:
    for r in items:
        if key == 'full' and r['group'] in CARRY:
            continue
        s = by_store.setdefault(store(r['url']), dict(n=0, usd=0.0, stages=set()))
        s['n'] += 1; s['usd'] += float(r['total_usd']); s['stages'].add(key)
STAGE_NO = {'mini': '1', 'full': '2', 'foil': '3'}

tables = ''
for i, (title, key, items) in enumerate(STAGES):
    extra = (r"\noindent $^\dagger$ Already bought for the Mini Cat: the radio, its AA cells and the NiMH pack move to the 1\,m boat, so if you build the Mini first, Stage 2 costs " + money(full_new) + r" instead of " + money(full_t) + ".\n") if key == 'full' else ''
    tables += r"""
\subsection*{""" + title + r""" \hfill """ + money(total(items)) + r"""}
{\small
\begin{longtable}{L{4.1cm}L{4.5cm}crrl}
\toprule
Item & Used for & Qty & Unit & Total & Store [link] \\
\midrule\endhead
""" + rows(items, key == 'full') + r"""
\midrule
\multicolumn{4}{l}{\textbf{Total}} & \textbf{""" + money(total(items)) + r"""} & \\
\bottomrule
\end{longtable}}
""" + extra

tex = r"""\documentclass[11pt]{article}
\usepackage[letterpaper,margin=0.75in]{geometry}
\usepackage{booktabs,longtable,array,xurl,enumitem}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\usepackage[hidelinks]{hyperref}
\setlist{itemsep=2pt}
\title{\textbf{RC Catamaran: What to Buy}\\\large Mini Cat, 1\,m boat and foiling kit}
\author{Filip Maleev}
\date{Prices read on retailer pages 23--25 September 2026, re-checked 4 October 2026}
\begin{document}
\maketitle

\section*{The plan}
Build in three stages, each after the one before sails well. The build manuals (\texttt{mini/manual/} and \texttt{manual\_1m/}) say what each part is for and how it goes together.
\begin{center}
\begin{tabular}{lrr}
\toprule
 & List price & To buy, in this order \\
\midrule
Stage 1: Mini Cat 600 & """ + money(mini_t) + r""" & """ + money(mini_t) + r""" \\
Stage 2: 1\,m boat (daggerboards) & """ + money(full_t) + r""" & """ + money(full_new) + r"""$^\dagger$ \\
Stage 3: foiling kit & """ + money(foil_t) + r""" & """ + money(foil_t) + r""" \\
\midrule
\textbf{All three} & & \textbf{""" + money(mini_t + full_new + foil_t) + r"""} \\
\bottomrule
\end{tabular}
\end{center}
$^\dagger$ The radio, its AA cells and the NiMH pack bought for the Mini (""" + money(carry_t) + r""") move to the 1\,m boat. Leftover filament, epoxy, glue, sail cloth and line from one stage may cover part of the next; the lists assume new stock.

Prices exclude shipping and tax. They were read on the retailers' pages in September and re-checked on 4 October 2026; the two that could not be re-checked say so. Check them before ordering. Under each item, in italics, is the listing the price came from, with the part number where there is one and a note where the price is uncertain.

\section*{Also needed, not priced above}
\begin{itemize}
\item \textbf{A 3D printer} that prints PETG, with a bed of at least 220\,x\,220\,mm. Every part is sized for that bed; two print diagonally (the 1\,m manual says which).
\item \textbf{A NiMH charger} for the eneloop AA cells. The Panasonic charger bundled with 4 more eneloop cells was \$32.09 at Walmart on 24 September 2026 [""" + str(ref('https://www.walmart.com/ip/Panasonic-Battery-Charger-with-4-eneloop-AA-Rechargeable-Batteries-4-Count/124706107')) + r"""] but out of stock on 4 October.
\item \textbf{Hand tools}, assumed on hand: hobby knife and steel rule; drill bits 1.2, 1.5, 2, 2.5 and 3.2\,mm (a pin vise is enough); side cutters and round-nose pliers for the music wire; 240-grit sandpaper; masking tape; a fine-tip soldering iron or hot needle for holes in the sailcloth; small screwdrivers; a 0.9\,mm hex key for the elevator trim screws; a bucket or sink for leak tests; a kitchen scale.
\item Servo screws come with the servos.
\end{itemize}

\section*{Choices: recommended parts and their alternatives}
Where a part has a cheaper or better option, the lists use the recommended one (marked $^\ast$ in the lists). Swapping to the alternative changes the totals by the difference in price.
""" + alt_blocks() + r"""

\clearpage
\section*{Order by store}
Orders grouped by store, with the carried-over radio and battery counted once.
\begin{center}
\begin{tabular}{lcrl}
\toprule
Store & Items & Subtotal & Stages \\
\midrule
""" + '\n'.join(f"{s} & {v['n']} & {money(v['usd'])} & {', '.join(STAGE_NO[k] for k in ('mini', 'full', 'foil') if k in v['stages'])} \\\\"
               for s, v in sorted(by_store.items(), key=lambda kv: -kv[1]['usd'])) + r"""
\bottomrule
\end{tabular}
\end{center}

\section*{Parts by stage}
""" + tables + r"""

\section*{Links}
{\small
\begin{enumerate}[label={[\arabic*]}]
""" + '\n'.join(f"\\item \\url{{{u}}}" for u in links) + r"""
\end{enumerate}}
\end{document}
"""
open(os.path.join(HERE, 'RC_Catamaran_Shopping_List.tex'), 'w').write(tex)
print('written', round(mini_t, 2), round(full_t, 2), round(full_new, 2), round(foil_t, 2), len(links))
