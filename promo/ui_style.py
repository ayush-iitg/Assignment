"""
Visual layer for app.py.

Kept separate so the interface file stays about data flow and this file stays
about presentation. Nothing here knows how a promo is chosen.

Dark neutral surfaces with Kuku FM's orange as the single accent. The output
is mostly timestamps and quotes, so: generous spacing, monospace for anything
an editor would copy, and colour reserved for the two things that carry
meaning (the accent marks what the tool chose, gold marks a timestamp).
"""

# Palette taken from Kuku FM's own brand colours: their site ships
# <meta name="theme-color" content="#E25506">, with #FF641C and #FFBB10 in the
# supporting set. ACCENT brightens the burnt orange slightly so it holds up on
# a dark surface; GOLD is the secondary note. Neutrals are warmed very
# slightly off pure grey so they sit with the orange rather than against it.
INK = "#0B0D12"
SURFACE = "#15181F"
SURFACE_2 = "#1C212B"
LINE = "#282E3A"
TEXT = "#ECEFF4"
MUTED = "#8E97A5"
FAINT = "#6B7483"
ACCENT = "#FF6A1F"
ACCENT_DEEP = "#E25506"
GOLD = "#FFBB10"
GOLD_SOFT = "#F2CE8C"
WASH = "#2A1608"
PASS = "#2FA84F"
WARN = "#D9960F"
FAIL = "#E5484D"

CSS = f"""
<style>
  /* ---------- shell ---------- */
  .stApp {{ background: {INK}; }}
  .block-container {{ padding-top: 2.1rem; padding-bottom: 3rem; max-width: 1180px; }}
  #MainMenu, footer, header {{ visibility: hidden; }}

  html, body, [class*="css"] {{
    font-feature-settings: "cv11", "ss01";
    -webkit-font-smoothing: antialiased;
  }}

  /* ---------- masthead ---------- */
  .masthead {{
    border-bottom: 1px solid {LINE};
    padding-bottom: 1.1rem;
    margin-bottom: 1.6rem;
  }}
  .masthead h1 {{
    font-size: 1.72rem; font-weight: 640; letter-spacing: -0.022em;
    margin: 0 0 .38rem 0; color: {TEXT}; line-height: 1.15;
  }}
  .masthead .sub {{
    color: {MUTED}; font-size: .885rem; line-height: 1.55; max-width: 74ch; margin: 0;
  }}
  .masthead .sub b {{ color: #DFE5EC; font-weight: 580; }}

  /* ---------- stat strip ---------- */
  .stats {{ display: flex; gap: .7rem; flex-wrap: wrap; margin: 0 0 1.5rem 0; }}
  .stat {{
    flex: 1 1 0; min-width: 158px;
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 10px;
    padding: .78rem .9rem .82rem .9rem;
  }}
  .stat .k {{
    color: {FAINT}; font-size: .665rem; font-weight: 620;
    letter-spacing: .085em; text-transform: uppercase; margin-bottom: .3rem;
  }}
  .stat .v {{
    color: {TEXT}; font-size: 1.44rem; font-weight: 600;
    letter-spacing: -0.02em; line-height: 1.1;
  }}
  .stat .n {{ color: {FAINT}; font-size: .715rem; margin-top: .2rem; }}
  .stat.good .v {{ color: {PASS}; }}

  /* ---------- promo card ---------- */
  .card {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 11px;
    padding: .95rem 1.05rem 1rem 1.05rem; margin-bottom: .62rem;
    transition: border-color .12s ease, background .12s ease;
  }}
  .card:hover {{ border-color: #3A4354; background: {SURFACE_2}; }}
  .card.lead {{
    border-color: rgba(255,106,31,.42);
    box-shadow: inset 2px 0 0 {ACCENT};
    background: linear-gradient(100deg, rgba(255,106,31,.07), {SURFACE} 52%);
  }}

  .card .top {{
    display: flex; align-items: center; gap: .58rem;
    margin-bottom: .62rem; flex-wrap: wrap;
  }}
  .rank {{
    font-size: .76rem; font-weight: 680; color: {FAINT};
    min-width: 1.6rem; letter-spacing: .02em;
  }}
  .card.lead .rank {{ color: {ACCENT}; }}

  .ts {{
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: .815rem; color: {GOLD_SOFT}; background: #121620;
    border: 1px solid {LINE}; border-radius: 6px; padding: .18rem .48rem;
    letter-spacing: -0.01em;
  }}
  .chip {{
    font-size: .685rem; font-weight: 560; color: {MUTED};
    border: 1px solid {LINE}; border-radius: 20px; padding: .14rem .58rem;
  }}
  .chip.ep {{ color: #A9BACB; }}
  .badge {{
    font-size: .685rem; font-weight: 660; border-radius: 20px;
    padding: .14rem .56rem; margin-left: auto;
  }}
  .badge.p4 {{ color: {PASS}; background: rgba(47,168,79,.12); border: 1px solid rgba(47,168,79,.32); }}
  .badge.p3 {{ color: {WARN}; background: rgba(217,150,15,.12); border: 1px solid rgba(217,150,15,.32); }}
  .badge.px {{ color: {FAIL}; background: rgba(229,72,77,.12); border: 1px solid rgba(229,72,77,.32); }}
  .badge.pn {{ color: {FAINT}; border: 1px solid {LINE}; }}

  .quote {{
    color: {TEXT}; font-size: .9rem; line-height: 1.5;
    border-left: 2px solid {ACCENT}; padding-left: .68rem; margin: 0 0 .5rem 0;
  }}
  .after {{
    color: {MUTED}; font-size: .835rem; line-height: 1.5;
    border-left: 2px solid {LINE}; padding-left: .68rem; margin: 0 0 .5rem 0;
  }}
  .why {{ color: {FAINT}; font-size: .79rem; line-height: 1.5; margin: 0; }}
  .lbl {{
    color: {GOLD}; font-size: .64rem; font-weight: 650;
    letter-spacing: .09em; text-transform: uppercase; display: block; margin-bottom: .16rem;
  }}

  /* ---------- section headings ---------- */
  .sec {{
    color: {TEXT}; border-left: 2px solid {ACCENT}; padding-left: .55rem; font-size: .935rem; font-weight: 620;
    letter-spacing: -0.012em; margin: 1.5rem 0 .3rem 0;
  }}
  .sec:first-child {{ margin-top: .2rem; }}
  .note {{ color: {FAINT}; font-size: .8rem; line-height: 1.55; margin: 0 0 .85rem 0; max-width: 86ch; }}

  /* ---------- tabs ---------- */
  .stTabs [data-baseweb="tab-list"] {{
    gap: .1rem; border-bottom: 1px solid {LINE}; margin-bottom: 1.25rem;
  }}
  .stTabs [data-baseweb="tab"] {{
    height: 2.4rem; padding: 0 .95rem; background: transparent;
    color: {MUTED}; font-size: .865rem; font-weight: 560;
  }}
  .stTabs [aria-selected="true"] {{ color: {TEXT} !important; }}
  .stTabs [data-baseweb="tab-highlight"] {{ background: {ACCENT}; height: 2px; }}

  /* ---------- controls ---------- */
  section[data-testid="stSidebar"] {{
    background: #080A0E; border-right: 1px solid {LINE};
  }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; }}
  .stButton button {{
    border-radius: 8px; font-weight: 600; font-size: .86rem;
    border: 1px solid rgba(255,106,31,.5);
  }}
  div[data-testid="stExpander"] {{
    border: 1px solid {LINE}; border-radius: 10px; background: {SURFACE};
  }}
  div[data-testid="stExpander"] summary {{ font-size: .85rem; color: #C2CEDB; }}
  .stDataFrame {{ border: 1px solid {LINE}; border-radius: 10px; }}
  .stDownloadButton button {{
    border-radius: 8px; font-size: .8rem; font-weight: 560;
    border: 1px solid {LINE}; background: {SURFACE}; color: {MUTED};
  }}
  code {{
    background: #121620; border: 1px solid {LINE}; border-radius: 5px;
    padding: .06rem .3rem; font-size: .85em; color: {GOLD_SOFT};
  }}
  hr {{ border-color: {LINE}; margin: 1.3rem 0; }}
</style>
"""


def masthead(title: str, subtitle: str) -> str:
    return f'<div class="masthead"><h1>{title}</h1><p class="sub">{subtitle}</p></div>'


def stat(key: str, value, note: str = "", good: bool = False) -> str:
    cls = "stat good" if good else "stat"
    return (f'<div class="{cls}"><div class="k">{key}</div>'
            f'<div class="v">{value}</div><div class="n">{note}</div></div>')


def stat_row(cards: list[str]) -> str:
    return f'<div class="stats">{"".join(cards)}</div>'


def gate_badge(score, verdict: str = "") -> str:
    """Colour the blind-test result by how many of the four criteria it met."""
    if not score or score == "n/a":
        return '<span class="badge pn">not tested</span>'
    try:
        n = int(str(score).split("/")[0])
    except ValueError:
        return f'<span class="badge pn">{score}</span>'
    cls = "p4" if n >= 4 else ("p3" if n == 3 else "px")
    label = f"blind test {score}" if verdict != "fail" else f"failed {score}"
    return f'<span class="badge {cls}">{label}</span>'


def esc(text) -> str:
    return (str(text or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def promo_card(promo: dict, segments_text: str, lead: bool = False) -> str:
    gate = promo.get("cold_viewer") or {}
    chips = [f'<span class="chip ep">ep {",".join(map(str, promo["episodes"]))}</span>',
             f'<span class="chip">{promo["total_duration_s"]:.0f}s</span>']
    hook_type = promo.get("hook_type")
    if hook_type and hook_type != "unclassified":
        chips.append(f'<span class="chip">{esc(hook_type)}</span>')

    parts = [f'<div class="card{" lead" if lead else ""}">', '<div class="top">',
             f'<span class="rank">{promo.get("rank", "—")}</span>',
             f'<span class="ts">{esc(segments_text)}</span>',
             "".join(chips),
             gate_badge(gate.get("score"), gate.get("verdict", "")),
             "</div>"]
    if promo.get("hook"):
        parts.append(f'<span class="lbl">Opens on</span>'
                     f'<p class="quote">{esc(promo["hook"])}</p>')
    if promo.get("cliffhanger"):
        parts.append(f'<span class="lbl">Cuts on</span>'
                     f'<p class="after">{esc(promo["cliffhanger"])}</p>')
    if promo.get("why_it_works"):
        parts.append(f'<p class="why">{esc(promo["why_it_works"])}</p>')
    parts.append("</div>")
    return "".join(parts)


def section(title: str, note: str = "") -> str:
    out = f'<div class="sec">{title}</div>'
    if note:
        out += f'<p class="note">{note}</p>'
    return out
