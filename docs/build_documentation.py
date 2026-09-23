# -*- coding: utf-8 -*-
"""Builds the JDUN | 15m ORB | Combined documentation PDF."""
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import *  # noqa: F403 - Platypus flowables

OUT = 'JDUN-ORB-Combined-Documentation.pdf'

INK   = colors.HexColor('#1a2332')
SLATE = colors.HexColor('#475569')
RULE  = colors.HexColor('#cbd5e1')
ACC   = colors.HexColor('#1e4f8f')
GREEN = colors.HexColor('#15803d')
RED   = colors.HexColor('#b91c1c')
AMBER = colors.HexColor('#b45309')
BG    = colors.HexColor('#f1f5f9')
BGW   = colors.HexColor('#fef9ec')

ss = getSampleStyleSheet()
def mk(name, **kw):
    base = kw.pop('parent', ss['BodyText'])
    return ParagraphStyle(name, parent=base, **kw)

S = {
 'title':  mk('t',  fontName='Helvetica-Bold', fontSize=27, leading=31, textColor=INK, spaceAfter=6),
 'sub':    mk('s',  fontName='Helvetica',      fontSize=12.5, leading=17, textColor=SLATE, spaceAfter=3),
 'h1':     mk('h1', fontName='Helvetica-Bold', fontSize=16, leading=19, textColor=ACC, spaceBefore=17, spaceAfter=7),
 'h2':     mk('h2', fontName='Helvetica-Bold', fontSize=11.7, leading=14.5, textColor=INK, spaceBefore=12, spaceAfter=4),
 'h3':     mk('h3', fontName='Helvetica-BoldOblique', fontSize=10.2, leading=13, textColor=SLATE, spaceBefore=9, spaceAfter=3),
 'body':   mk('b',  fontName='Helvetica', fontSize=9.7, leading=13.9, textColor=INK, spaceAfter=6, alignment=TA_LEFT),
 'bullet': mk('bu', fontName='Helvetica', fontSize=9.7, leading=13.6, textColor=INK,
              leftIndent=15, bulletIndent=4, spaceAfter=3.5),
 'code':   mk('c',  fontName='Courier', fontSize=8.6, leading=11.6, textColor=INK,
              backColor=BG, borderPadding=7, leftIndent=3, spaceBefore=3, spaceAfter=8),
 'cell':   mk('cl', fontName='Helvetica', fontSize=8.5, leading=11.3, textColor=INK),
 'cellb':  mk('cb', fontName='Helvetica-Bold', fontSize=8.5, leading=11.3, textColor=INK),
 'cellh':  mk('ch', fontName='Helvetica-Bold', fontSize=8.5, leading=11.3, textColor=colors.white),
 'cellm':  mk('cm', fontName='Courier', fontSize=8.1, leading=11, textColor=ACC),
 'cap':    mk('cp', fontName='Helvetica-Oblique', fontSize=8.6, leading=11.5, textColor=SLATE, spaceAfter=8),
}

def esc(t):
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'`(.+?)`', r'<font name="Courier" size="9">\1</font>', t)
    return t

story = []
def P(t, s='body'):  story.append(Paragraph(esc(t), S[s]))
def H1(t): story.append(Paragraph(esc(t), S['h1'])); story.append(HRFlowable(width='100%', thickness=0.8, color=RULE, spaceAfter=7))
def H2(t): P(t, 'h2')
def H3(t): P(t, 'h3')
def B(t):  story.append(Paragraph(esc(t), S['bullet'], bulletText='•'))
def N(i,t):story.append(Paragraph(esc(t), S['bullet'], bulletText='%d.'%i))
def SP(h=7): story.append(Spacer(1, h))
def CODE(t): story.append(Paragraph(esc(t).replace('\n','<br/>').replace(' ','&nbsp;'), S['code']))
def CAP(t): P(t, 'cap')

def callout(title, body, tone='warn'):
    bg, bd = (BGW, AMBER) if tone == 'warn' else (BG, ACC)
    inner = [[Paragraph('<b>%s</b>' % esc(title), S['cellb'])],
             [Paragraph(esc(body), S['cell'])]]
    t = Table(inner, colWidths=[6.45*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),bg),
        ('LINEBEFORE',(0,0),(0,-1),2.5,bd),
        ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
        ('TOPPADDING',(0,0),(-1,0),7),('BOTTOMPADDING',(0,-1),(-1,-1),7),
        ('TOPPADDING',(0,1),(-1,1),2),('BOTTOMPADDING',(0,0),(-1,0),2),
    ]))
    story.append(t); SP(9)

def table(header, rows, widths, mono_col=None):
    # Header cells carry their own WHITE style: a TableStyle TEXTCOLOR command does not
    # override the colour a Paragraph already has, so a dark style here goes invisible
    # against the dark header band.
    data = []
    if header:
        data.append([Paragraph(esc(h), S['cellh']) for h in header])
    for r in rows:
        data.append([Paragraph(esc(str(c)), S['cellm'] if (mono_col is not None and i == mono_col) else S['cell'])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    st = [('VALIGN',(0,0),(-1,-1),'TOP'),
          ('GRID',(0,0),(-1,-1),0.4,RULE),
          ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
          ('TOPPADDING',(0,0),(-1,-1),4.5),('BOTTOMPADDING',(0,0),(-1,-1),4.5)]
    if header:
        st.append(('BACKGROUND',(0,0),(-1,0),INK))
    start = 1 if header else 0
    for i in range(start, len(data)):
        if (i - start) % 2 == 1:
            st.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#f8fafc')))
    t.setStyle(TableStyle(st))
    story.append(t); SP(9)

# ══════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════
SP(52)
P('JDUN | 15m ORB | Combined', 'title')
P('TradingView Pine Script v6 indicator — complete technical documentation', 'sub')
SP(4)
story.append(HRFlowable(width='100%', thickness=2.5, color=ACC))
SP(16)
P('A 15-minute opening-range breakout indicator built from Jaydon\'s two webinars, with the '
  'GD context layer merged on top. It marks the session levels, waits out the opening range, '
  'validates the candle that breaks it, and enters the pullback into the fib golden pocket '
  'with R-multiple targets and a hard daily trade cap.')
P('This document describes exactly what the script does, how each stage works, what fires '
  'when, and every input — written against the code as it actually stands, not against intent.')
SP(12)
table(None, [
    ['File', 'JDUN-ORB-Combined.pine'],
    ['Language', 'Pine Script v6 (`//@version=6`), overlay indicator'],
    ['Repository', 'JinxedAgain/AI_Claude, branch claude/15m-orb-jinxed-indicator-egbxsn'],
    ['Intended chart', '5-minute (enforced by the Signal Timeframe lock)'],
    ['Opening range', '15 minutes, independent of chart timeframe'],
    ['Inputs', '67, across 10 groups'],
    ['Alert conditions', '10 (8 trade, 2 context-only)'],
    ['Order routing', 'Alert names match the prior script, so PickMyTrade webhooks carry over'],
], [1.45*inch, 5.0*inch])
SP(6)
callout('This is an indicator, not a strategy',
        'It draws levels and fires alertcondition() signals. It places no orders itself and has '
        'no TradingView strategy tester behind it. The backtest table is the script\'s own '
        'bar-close simulation — see "Backtest table: how R is scored" for exactly what it does '
        'and does not model.')

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════
H1('1. The method it implements')
P('Every rule below comes from Jaydon\'s two webinars. The script follows them in his order — '
  'this sequence is the spine of the whole indicator, and each stage maps to a named section in '
  'the source.')
for i, t in enumerate([
 'Before the open, mark the levels: pre-market high/low, previous day high/low, Asia high/low, VWAP, point of control.',
 'Let the first 15 minutes form the opening range. No trades in that window — "9:30 to 9:45 equals no trades. Let the market show you its hand."',
 'Wait for a 5-minute candle to CLOSE beyond the range. Never mid-candle.',
 'That candle must be a trend-setting candle: full body, minimal wick, rising volume. A big candle on weak volume is an "anomaly" — someone is lying — and is skipped.',
 'Draw a fib across that candle. Enter the pullback into the 0.5-0.618 golden pocket, ideally where it stacks with one of the marked levels.',
 'If the move is too aggressive to retrace that far, use the two-bar setup instead: a shallower pullback measured across both candles.',
 'Stop goes beyond the trend-setting candle. Hard stop, never mental.',
 'Trim ~70% at 1R and move the stop to break-even. Rest at 1.5R and 2R.',
 'Two trades a day maximum. Two losses and the day is over.',
 'Trade the first 1-2 hours. Flat before the close.'], 1):
    N(i, t)
SP(4)
P('**His numbers, as the shipped defaults.** Targets are R-multiples off the actual stop distance '
  '(1R / 1.5R / 2R), not ATR — that is how he sizes every trade he describes. The alert window is '
  '09:30-15:30, the whole session, though his own guidance favours the first one to two hours. Max stop is 40 points ("40-50 acceptable, 100 too wide"). All three are inputs.')

H1('2. Architecture: what came from where')
P('This file is a merge of two earlier scripts. Knowing which half you are looking at matters, '
  'because only one of them trades.')
H2('The trade engine — from JDUN-ORB.pine')
P('Opening range, trend-setting candle, golden pocket and two-bar entry, R-multiple targets, '
  'break-even stop, two-trade daily cap, and the R-denominated backtest table. This is the only '
  'thing that opens a position, and it is carried over unchanged.')
H2('The context layer — from USE-15m-ORB-Jinxed.pine (its GD merge)')
P('The fast/slow EMA pair, the EMA-cross-on-volume signals, and '
  'the alert-window background shading. **None of these open a position. They have no TP and no SL.** '
  'The EMA cross has its own two alerts.')
H2('Deliberately not carried over')
B('**The fluxchart state-machine engine** from the Jinxed script (Sensitivity, Dynamic/ATR take-profits, '
  'the retest counter). It fires on the same alert names as the JDUN engine — Buy / Sell / Take Profit 1-3 / '
  'Stop Loss — so running both would send two conflicting orders to one webhook. The Jinxed script\'s own '
  'Jay mode was already a reimplementation of the rules the JDUN engine implements here, so no behaviour was lost.')
B('**The volume profile.** That was the blue box drawn beside the opening range. It is gone; every level '
  'on the chart is now a line.')

H1('3. The trade lifecycle, stage by stage')
P('What follows is the actual order of operations on every bar.')

H2('Stage 0 — Session levels (continuous)')
P('Six reference prices are tracked and rebuilt each day. They gate nothing by default, but they feed the '
  'optional stacked-level filter.')
table(['Level', 'How it is built', 'Default window'], [
 ['PM high / low', 'Running extremes across the pre-market window', '04:00-09:30'],
 ['Previous day high / low', 'Yesterday\'s session extremes, frozen on the first bar of the new session', '09:30-16:00'],
 ['Asia high / low', 'Running extremes across the Asia window (crosses midnight; Pine handles it)', '18:00-03:00'],
 ['VWAP', '`ta.vwap(hlc3)` — resets automatically each trading day', 'session'],
 ['Point of control', 'Price bucket with the most volume so far today. A running max keeps this O(1) per bar instead of rescanning the map.', 'session, 4-tick buckets'],
 ['ORB midline', 'The 50% of the opening range. He calls it "the hidden gem".', 'derived'],
], [1.25*inch, 3.95*inch, 1.25*inch])
P('All session windows are read in one timezone, set by **Timezone for all session times** '
  '(default America/New_York), so the times you type are the times you mean. DST is handled.')

H2('Stage 1 — Opening range')
P('On the first bar of the regular session the script stamps the session open, then accumulates the high '
  'and low for **Opening range length** minutes (default 15 — three 5-minute candles). When that window '
  'closes the range locks and hunting begins. Nothing can arm or trade while the range is still forming.')
CODE("newSession   = inRTH and not inRTH[1]\n"
     "orbBuilding  = inRTH and (time - sessOpen) < orbMins * 60000\n"
     "orbMid       = (orbH + orbL) / 2.0")

H2('Stage 2 — The trend-setting candle (arming)')
P('A setup is armed when a candle CLOSES beyond the locked range AND passes all three quality tests. '
  'Fail any one and there is no setup at all — the script keeps waiting.')
table(['Test', 'Rule', 'Input'], [
 ['Body', 'Body must be at least 50% of the candle\'s high-to-low range. His "full body, no or minimal wick".', 'Minimum body % of range'],
 ['Volume', 'Volume above its 20-bar average AND higher than the previous bar. Rising volume means buyers are bidding aggressively, not merely that there are more of them.', 'Require rising volume'],
 ['Anomaly veto', 'A candle larger than 1.5x ATR on BELOW-average volume is rejected. Size and participation disagree, so the move is a trap.', 'Reject anomalies'],
], [1.0*inch, 4.2*inch, 1.25*inch])
P('On a valid break the script records the candle\'s high and low (these become both the stop and the fib '
  'anchors), stamps the bar index, and measures the golden pocket:')
CODE("r = high - low\n"
     "long : zoneHi = high - 0.500 * r     zoneLo = high - 0.618 * r\n"
     "short: zoneLo = low  + 0.500 * r     zoneHi = low  + 0.618 * r")
callout('One setup per excursion — a bug worth knowing about',
        'An armedRun latch allows only ONE arming per trip outside the range. Without it the script re-armed '
        'on EVERY bar that stayed beyond the level, pushing setBar forward each time; since the entry requires '
        'bar_index > setBar, the pullback test could then never pass and no entry would ever fire in a sustained '
        'trend. That was the "only one signal in the whole backtest" symptom. The latch clears when price closes '
        'back inside the range, so a genuine second break later in the day can still arm afresh.', 'warn')

H2('Stage 3 — The entry zone')
P('Three entry models are selectable. Golden Pocket is the default and his primary method.')
table(['Entry model', 'What triggers it'], [
 ['Golden Pocket', 'Price pulls back into the 0.5-0.618 fib of the trend-setting candle.'],
 ['Level Retest', 'The simpler first-webinar version: price comes back and touches the broken range level itself.'],
 ['Either', 'Whichever happens first.'],
], [1.3*inch, 5.15*inch])
H3('The two-bar fallback')
P('For aggressive trends that never retrace to 0.5. If the bar immediately after the trend-setting candle '
  'extends the move in the same direction on passing volume, the zone is re-measured across BOTH candles '
  'and made shallower — 0.236 to 0.382 by default. In his words: "the only reason you trade a two bar is in '
  'the cases of aggressive trends where you dont retest the 50%."')
H3('Why the entry cannot fire on the arming candle')
P('The zone is measured INSIDE the trend-setting candle, so the entry test requires `bar_index > setBar`. '
  'Without that guard the entry would trigger on the arming candle itself instead of waiting for the pullback '
  'he actually trades.')
H3('Expiry')
P('A setup is discarded when it goes stale (**Setup valid for N bars**, default 15) or is invalidated by price '
  'closing back inside the range, or when the session ends.')

story.append(PageBreak())

H2('Stage 4 — Execution timing: what waits for a candle and what does not')
P('This is the part most worth understanding, because it determines when alerts reach your broker.')
table(['Event', 'Timing', 'Why'], [
 ['Arming', 'Confirmed bar close, always', 'His non-negotiable rule. A wick through the range is not a break.'],
 ['Entry (Golden Pocket / two-bar)', 'Real time, on touch (default)', 'The zone test reads the bar\'s RUNNING high and low, which only widen as the candle forms. Once touched it is true and stays true through the close, so firing early cannot repaint — the bar-close answer is identical, the alert just arrives sooner.'],
 ['Entry (Level Retest)', 'Confirmed bar close, always', 'It tests close > orbH, and the close moves every tick. Firing early WOULD repaint: an alert would go out for a trade the script then discards.'],
 ['TP1 / TP2 / TP3 / SL', 'Real time, on touch', 'An exit should not wait for a candle to finish.'],
 ['Close All / Flatten', 'Real time', 'A safety net; it fires after hours by design.'],
], [1.55*inch, 1.35*inch, 3.55*inch])
callout('Set the TradingView alert to "Once Per Bar", not "Once Per Bar Close"',
        'A TradingView alert permanently captures the trigger frequency chosen when it was created. On "Once Per '
        'Bar Close" the platform holds every one of these signals until the candle finishes, and none of the '
        'real-time behaviour above applies. This affects the TP and SL alerts too.', 'warn')
H3('The entry bar and same-bar targets')
P('On any bar after the entry, the full high and low are the right thing to test. On the entry bar itself the '
  'high and low cover ground price crossed BEFORE the fill, so testing them would credit moves the trade never '
  'had. The script therefore tests `close` on the entry bar — which in real time IS the live price, tick by tick, '
  'and on a historical bar equals the entry price, making it inert. So a target reached seconds after a real-time '
  'fill is reported at once, and nothing before the fill can ever be credited.')

H2('Stage 5 — Risk and targets')
P('The stop is placed beyond the trend-setting candle, padded by **Stop padding** (default 2 ticks). Risk is '
  'the distance from the live price to that stop, and every target is a multiple of it.')
CODE("candSL  = long ? tcLo - stopPad*tick : tcHi + stopPad*tick\n"
     "riskPts = |entry - candSL|\n"
     "TP1 = entry +/- 1.0 * riskPts        TP2 = entry +/- 1.5 * riskPts\n"
     "TP3 = entry +/- 2.0 * riskPts        (all three are inputs)")
B('**Max stop distance** (default 40 points) rejects the setup outright if the stop is wider. His guidance: '
  '20-30 points on NQ is ideal, 40-50 acceptable, 100 far too wide. Set 0 to disable.')
B('**TP2 = high/low of day** is an optional alternative target — his stated primary target is a new high or low '
  'of day. It never sits closer than 1R, because a HOD already behind price is not a target.')
B('**Require a stacked key level** is his highest-probability condition: the fib zone lining up with a marked '
  'level. When on, the entry must also be within **Stacked level distance** of PM H/L, previous day H/L, Asia H/L, '
  'VWAP, POC or the ORB midline. It is a strict filter — expect noticeably fewer trades. Off by default, but '
  'always reported on the dashboard.')

H2('Stage 6 — Exits, and the break-even step')
P('TP1, TP2 and TP3 are each tested independently against their own price, so one candle running through all '
  'three fires all three. **Stop to '
  'break-even after TP1** is on by default, and it is the single most misread behaviour in the script:')
CODE("if not tp1Done and hiTest >= tp1Px - buf\n"
     "    tp1Hit  := true\n"
     "    tp1Done := true\n"
     "    if beAfterTP1\n"
     "        slPx := entryPx        // the live stop is now your entry")
callout('After TP1, a stop-out is a break-even exit, not a 1R loss',
        'The moment TP1 lands the live stop becomes your entry price. If price then comes back, the Stop Loss '
        'alert fires at entry — you keep what you trimmed at TP1 and give back nothing. On the chart the dashed '
        'There is ONE stop line and it moves with the stop. At TP1 it relocates, turns orange and is renamed, so '
        'what is drawn is always the stop that is actually live, and a stop-out after that lands on it marked BE '
        'rather than SL. Where it lands is set by Break-even offset: at 0 it sits exactly on the entry, and the '
        'entry line is dropped because the two would otherwise render as one line of alternating blue and orange '
        'dashes. Above 0 the stop sits that share of R into profit, the mark reads BE+, and both lines are kept '
        'because they no longer coincide.', 'warn')
H3('Flatten')
P('Anything still open when the **Flatten after** window ends — or when the session ends — gets a single Close All '
  'alert, once per day. The end time is your hard flat-by deadline; leave the start time early, only the end matters.')

H2('Stage 7 — Daily limits')
P('Two hard caps, both reset at each new session: **Max trades per day** (default 2) and **Max losses per day** '
  '(default 2). A loss counts only when the trade is stopped out without ever reaching TP1. "You are a day trader, '
  'not a trade-every-day trader." — "Two full-size losses and I am done. I do not care if the next setup is the best '
  'one of the year."')
P('Entries are additionally gated by the **Alert window** (default 09:30-15:30) and by the Signal Timeframe lock.')

story.append(PageBreak())

H1('4. Alerts and order routing')
P('Ten alert conditions populate TradingView\'s Condition dropdown. The first eight are the trade engine. '
  'The last two are the EMA-cross heads-up and are **not** trade signals — do not point an order webhook at '
  'them unless you mean to.')
table(['Alert name', 'Fires when', 'Gated by'], [
 ['Buy / Sell', 'Either direction enters', 'window + timeframe'],
 ['Buy', 'Long entry', 'window + timeframe'],
 ['Sell', 'Short entry', 'window + timeframe'],
 ['Take Profit 1', 'Price touches TP1', 'timeframe'],
 ['Take Profit 2', 'Price touches TP2 (after TP1)', 'timeframe'],
 ['Take Profit 3', 'Price touches TP3 (after TP2)', 'timeframe'],
 ['Stop Loss', 'Price touches the live stop (original, or break-even after TP1)', 'timeframe'],
 ['Close All / Flatten', 'Position still open past the flatten deadline', 'timeframe'],
 ['EMA Cross Buy (volume)', 'Context only — no position, no TP, no SL', 'session + timeframe'],
 ['EMA Cross Sell (volume)', 'Context only — no position, no TP, no SL', 'session + timeframe'],
], [1.75*inch, 3.25*inch, 1.45*inch])
H2('Prices in the alert message')
P('Five hidden plots carry the live levels into the alert payload. Reference them in the message body with '
  'TradingView placeholder syntax:')
CODE('{{plot("Entry")}}   {{plot("SL")}}\n'
     '{{plot("TP 1")}}    {{plot("TP 2")}}    {{plot("TP 3")}}')
P('They are `display.data_window` plots — visible in the Data Window, invisible on the chart.')
H2('The Signal Timeframe lock')
P('A TradingView alert permanently captures the chart timeframe it was created on. **Lock alerts to signal '
  'timeframe** (on by default) stops an alert accidentally created on the wrong chart from ever firing. The '
  'default Signal Timeframe is 5 minutes — he executes on the 5-minute and refuses to go lower. The dashboard\'s '
  'last-but-one row reads WRONG TF in red whenever the chart does not match.')
H2('The TP/SL buffer')
P('**TP/SL buffer** (default 1 tick) fires exit alerts that many ticks early, so a market order fills near the '
  'intended price rather than chasing through it.')

H1('5. Chart anatomy')
P('Everything the script can draw, and what each element means.')
H2('Level lines')
P('Every reference level is a full line running from the open of a PREVIOUS session to the live candle, with its '
  'name and price at the right-hand end so nothing needs scrolling. How far left it reaches is **Extend levels back '
  '(sessions)** — 1 (default) starts the line at yesterday\'s open, 0 starts it at today\'s. Width and style are '
  'shared across the whole set by **Level line width** (default 1) and **Level line style**; at width 1 Dotted reads '
  'lighter still than solid.')
table(['Drawing', 'Colour', 'Meaning'], [
 ['ORB high / low', 'green / red, solid', 'The locked opening range. Own width input.'],
 ['ORB Mid', 'grey', 'The 50% of the range.'],
 ['PM High / PM Low', 'orange', 'Pre-market extremes.'],
 ['Prev Day High / Low', 'blue', 'Yesterday\'s session extremes.'],
 ['Asia High / Low', 'purple', 'Overnight extremes.'],
 ['POC', 'red', 'Session point of control.'],
 ['VWAP', 'blue, continuous', 'Plotted across all bars, not a stub — it moves, so a stub would be meaningless. Label only.'],
 ['Golden pocket pair', 'yellow', 'The 0.5 and 0.618 of the trend-setting candle. Visible only while a setup is armed; gone the moment the entry fires or the setup expires.'],
 ['EMA fast / slow', 'teal / grey', 'Context layer. Gates nothing in the trade engine.'],
], [1.4*inch, 1.1*inch, 3.95*inch])
H2('Trade lines')
P('On every entry, five horizontal lines are drawn at Entry, SL, TP1, TP2 and TP3. They extend rightward for the '
  'rest of that trading day and then freeze, so past trades keep their levels — you can see every target including '
  'the ones price never reached. Each carries its name (ENTRY, SL, TP 1, TP 2, TP 3) at its right-hand end. Old sets '
  'are never deleted; Pine drops the oldest once the drawing budget is reached, which keeps roughly the last hundred '
  'trades visible.')
H2('Markers')
table(['Marker', 'Where', 'Meaning'], [
 ['BUY flag', 'below bar', 'Long entry.'],
 ['SELL flag', 'above bar', 'Short entry.'],
 ['BUY X / SELL X', 'above / below bar', 'The redundant entry mark — the same entry drawn a second time on the opposite side of the bar. Two independent draws off one signal, so if the flag is hidden behind another drawing or clipped at the pane edge, the X still shows.'],
 ['TP 1 / TP 2 / TP 3 X', 'on the target price', 'That target was reached; the mark sits on the level it hit. When two or three land on ONE candle their levels are only 0.5R apart, so separate marks and names just cluster — the group gets ONE X past the end of the wick and a single stacked block of names above it, TP 1 nearest the candle and TP 2, TP 3 above it (below, for a short), in the order price passed through them. Every target still fires its own alert on touch.'],
 ['SL X', 'on the stop price', 'Stopped out for a real loss, at the original stop.'],
 ['BE X', 'on the stop price', 'Stopped out at break-even, after TP1 had already pulled the stop up. Drawn in the orange of the break-even line it sits on, so the chart never calls a scratch a loss.'],
 ['BE+ X', 'on the stop price', 'The same, but with a break-even offset set, so the stop sat in profit and that exit banked a gain rather than scratching.'],
 ['CLOSE X', 'at the exit price', 'Forced flatten.'],
 ['EMA+ / EMA-', 'below / above bar', 'EMA cross on above-average volume. Context only.'],
], [1.3*inch, 1.15*inch, 4.0*inch])
callout('Exit marks sit on the level they hit',
        'They are plotted with location.absolute, at the value of the price they fired on, rather than '
        'floating above or below the candle. An exit mark therefore lands on its own line. Entry flags '
        'are the exception and still sit beside the bar, since an entry has no level of its own.', 'info')

story.append(PageBreak())

H1('6. The two tables')
H2('Dashboard (live state)')
table(['Row', 'Shows'], [
 ['State', 'RANGE FORMING -> WAITING -> ARMED LONG/SHORT -> LONG/SHORT'],
 ['Trades / Losses', 'Today\'s count against both daily caps; turns orange when either is hit'],
 ['Setup', 'Golden pocket, or Two-bar when the fallback re-measured the zone'],
 ['Entry zone', 'The live zone bounds'],
 ['Stacked level', 'YES when price is sitting on a marked level — reported even when the filter is off'],
 ['Risk if taken', 'Stop distance in points for the armed setup; reads TOO WIDE in red past the max'],
 ['Entry / SL', 'The open trade\'s entry and its CURRENT stop (so it shows break-even after TP1)'],
 ['Signal TF', 'OK, or WRONG TF in red'],
 ['EMA trend', 'UP / DOWN / flat from the context layer'],
], [1.25*inch, 5.2*inch])
H2('Backtest table: how R is scored')
P('A bar-close simulation of this engine over the loaded chart, denominated in R. Rows: Signals, Closed, Wins, '
  'Losses, Win rate, Profit factor, Total R, Avg R per trade, and TP1/TP2/TP3 hit counts.')
P('The scoring is position-weighted, which matters. A trade that trimmed at TP1 and then stopped at break-even is '
  'NOT a zero — the trimmed portion was banked, and scoring it flat would understate results badly:')
CODE("if not tp1Done          realised = -1.0        // stopped before any trim\n"
     "else                    realised = trimPct * tp1R\n"
     "  + tp3Done             ((1-trim)*0.5)*tp2R + ((1-trim)*0.5)*tp3R\n"
     "  + tp2Done only        (1-trim)*tp2R\n"
     "  + otherwise           nothing (runner came back to break-even)")
P('**Trim fraction at TP1** (default 0.7) drives that weighting. He states 60-75%. It affects the table only — it '
  'changes no alert and no signal.')
callout('What the backtest does not model',
        'It is not a record of live fills. If a TP and the SL are both touched inside one candle it credits the TP, '
        'because intrabar order is not knowable from OHLC. It assumes fills at the exact level with no slippage and '
        'no commission. It does not include the EMA cross signals, which are not trades. Treat it as a shape check '
        'on the rules, not as expected P&L.', 'warn')

H1('7. Full input reference')
P('67 inputs across 10 groups. Defaults shown are as shipped.')

def igroup(name, rows):
    # Keep a group heading from stranding itself at the foot of a page.
    story.append(CondPageBreak(1.5*inch))
    H2(name)
    table(['Setting', 'Default', 'What it does'], rows, [1.9*inch, 0.95*inch, 3.6*inch], mono_col=1)

igroup('Session & Opening Range', [
 ['Timezone for all session times', 'America/New_York', 'Every session field in the script is read in this timezone. Handles DST.'],
 ['Regular session', '0930-1600', 'The trading session that defines the day.'],
 ['Pre-market window', '0400-0930', 'He marks pre-market from 4:00am, not 8:00 — he calls this out explicitly.'],
 ['Asia session', '1800-0300', 'Crosses midnight, which Pine handles.'],
 ['Opening range length (minutes)', '15', 'The first three 5-minute candles. Nothing trades until this closes.'],
])
igroup('Entry', [
 ['Entry model', 'Golden Pocket', 'Golden Pocket / Level Retest / Either.'],
 ['Two-bar setup fallback', 'true', 'Shallower zone across both candles for aggressive trends.'],
 ['Two-bar zone start / end', '0.236 / 0.382', 'The shallower retracement band used by the fallback.'],
 ['Fire entries in real time (on touch)', 'true', 'Entry alert fires the instant price enters the zone. Off = wait for bar close.'],
 ['Setup valid for N bars', '15', 'How long the armed zone stays live before being discarded.'],
 ['Require a stacked key level', 'false', 'Entry must also sit on a marked level. Strict — far fewer trades.'],
 ['Stacked level distance (points)', '10.0', 'How close counts as stacked.'],
])
igroup('Trend-Setting Candle', [
 ['Minimum body % of range', '50', 'A wick more than half the candle invalidates it.'],
 ['Require rising volume', 'true', 'Above the average AND above the previous bar.'],
 ['Volume average length', '20', 'Bars in the volume average.'],
 ['Reject anomalies', 'true', 'Large candle on below-average volume is a trap.'],
 ['Anomaly size (x ATR)', '1.5', 'How large before the anomaly test applies.'],
])
igroup('Risk & Targets', [
 ['TP1 / TP2 / TP3 (R)', '1.0 / 1.5 / 2.0', 'Targets as multiples of the actual stop distance.'],
 ['Trim fraction at TP1', '0.7', 'Backtest weighting only. He states 60-75%.'],
 ['TP2 = high/low of day instead', 'false', 'Use a new HOD/LOD as TP2, never closer than 1R.'],
 ['Stop to break-even after TP1', 'true', 'The live stop becomes your entry once TP1 lands.'],
 ['Break-even offset (% of R)', '10.0', 'How far PAST break-even the stop goes. 0 is a true break-even. Above that it moves into profit by that share of the trade\'s own risk, so it scales with the stop instead of being a fixed number of points.'],
 ['Stop padding (ticks)', '2', 'How far beyond the trend-setting candle the stop sits.'],
 ['Max stop distance (points)', '40.0', 'Reject the setup if the stop is wider. 0 disables.'],
])
igroup('Daily Limits', [
 ['Max trades per day', '2', 'His cap. "One good trade a day, two max."'],
 ['Max losses per day', '2', 'Circuit breaker. A loss = stopped out without reaching TP1.'],
])
igroup('Alerts', [
 ['Alert window', '0930-1530', 'The hours an entry may fire. The default runs the whole session; his own guidance favours the first one to two hours.'],
 ['TP/SL buffer (ticks)', '1', 'Fire exits this many ticks early so the order fills near the level.'],
 ['Shade the alert window', 'false', 'Tints the background while the window is open.'],
 ['Lock alerts to signal timeframe', 'true', 'Stops an alert made on the wrong chart from ever firing.'],
 ['Signal timeframe (minutes)', '5', 'He executes on the 5-minute and refuses to go lower.'],
 ['Flatten after', '0930-1530', 'End time is your hard flat-by deadline.'],
])
igroup('Levels', [
 ['PM / Prev day / Asia / VWAP / POC', 'all true', 'Which reference levels to draw.'],
 ['POC bucket size (ticks)', '4', 'How coarsely prices are grouped when finding the POC.'],
 ['ORB midline', 'true', 'The 50% of the range — "the hidden gem".'],
 ['Level line width', '1', 'Shared by every reference level. 1 is the thinnest Pine draws.'],
 ['Level line style', 'Solid', 'Solid / Dashed / Dotted. Dotted reads lighter than a width-1 solid.'],
 ['Extend levels back (sessions)', '1', 'How far LEFT every level reaches. 1 = yesterday\'s open.'],
 ['Label every level', 'true', 'Name and price at the right-hand end.'],
])
igroup('Visuals', [
 ['Opening range lines', 'true', 'The green/red range lines, with their own width input.'],
 ['Entry zone while live', 'true', 'The yellow golden-pocket pair while a setup is armed.'],
 ['Entry / SL / TP lines on every trade', 'true', 'Five lines per trade, kept for past trades too.'],
 ['Redundant entry X marker', 'true', 'Second entry mark on the opposite side of the bar.'],
 ['Name each trade line at its right end', 'true', 'ENTRY / SL / TP 1-3 at the end of each dashed line.'],
 ['Target stack clearance (x ATR)', '0.35', 'How far past the end of the wick the stacked target names sit when one candle takes more than one target. In ATR, so the gap looks the same on any symbol.'],
 ['Label the live trade levels', 'true', 'TP/SL with prices at the right edge while a trade is open.'],
 ['Dashboard / Backtest table', 'true', 'The two panels, each with a position dropdown.'],
])
igroup('EMA Cross + Volume (context only)', [
 ['Enable EMA cross signals', 'true', 'EMA+ / EMA- labels and their two alerts. Not trades.'],
 ['Fast / Slow EMA', '10 / 20', '10/20, 9/21 and 8/20 all behave similarly.'],
 ['Cross which EMA', 'Fast', 'Both = close through the fast AND already the right side of the slow.'],
 ['Volume must exceed avg by', '1.2', '120% of the average. Raise it for fewer signals.'],
 ['Skip first N bars of session', '4', '4 bars on a 5-min chart skips the noisy first 20 minutes.'],
 ['Only during alert window', 'false', 'Off means crosses fire all session.'],
])

story.append(PageBreak())
H1('8. Limitations and things to watch')
B('**It is an indicator, not a strategy.** No orders are placed by the script and there is no TradingView '
  'strategy tester behind it. Everything downstream depends on your alert and webhook configuration.')
B('**"Once Per Bar" is mandatory** for the real-time entry and exit behaviour. On "Once Per Bar Close" every '
  'signal waits for the candle.')
B('**Intrabar order is unknowable.** If a TP and the SL are both touched inside one candle, the backtest credits '
  'the TP. Live, whichever your broker fills first is what you get.')
B('**No slippage or commission** anywhere in the R accounting.')
B('**Level Retest cannot go real time** by construction — it tests the close.')
B('**The daily-loss circuit breaker counts only full losses.** A trade that reached TP1 and then stopped at '
  'break-even is not a loss, so it does not count toward the cap.')
B('**Drawing budget.** Lines and labels are capped at 500 each. Trade lines are never deleted, so on a long '
  'history Pine drops the oldest — roughly the last hundred trades stay visible.')
B('**The chart must be finer than the opening range.** Run it on 5-minute as intended.')

H1('9. Version history')
table(['Change', 'What it did'], [
 ['Combined build', 'Merged the JDUN trade engine with the GD context layer. Dropped the second trade engine and the volume-profile box.'],
 ['Level extension', 'Every reference level became a full line from a previous session\'s open to the live candle, replacing the 3-bar stub.'],
 ['Real-time entry', 'Entries fire on touch rather than at bar close, with Level Retest excluded. Entry-bar TP/SL now measured from the live price.'],
 ['Entry redundancy', 'Second X marker per entry. Fixed a bug where SL and TP3 marks never drew, because pos was zeroed by the close block before plotshape evaluated it.'],
 ['Trade-line names', 'ENTRY / SL / TP 1-3 at the right-hand end of each dashed line.'],
 ['Thinner levels', 'Width and style inputs for the reference levels and the ORB lines.'],
 ['Break-even stop drawn', 'The SL line splits into a red "initial" segment and an orange "BE" segment at TP1, so a break-even exit lands on a visible line.'],
], [1.35*inch, 5.1*inch])

SP(14)
story.append(HRFlowable(width='100%', thickness=0.8, color=RULE))
SP(6)
CAP('Generated from JDUN-ORB-Combined.pine as committed on branch claude/15m-orb-jinxed-indicator-egbxsn. '
    'Where this document and the source disagree, the source is correct.')

# ══════════════════════════════════════════════════════════════════════════
def deco(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont('Helvetica', 7.8)
        canvas.setFillColor(SLATE)
        canvas.drawString(0.75*inch, 0.52*inch, 'JDUN | 15m ORB | Combined — technical documentation')
        canvas.drawRightString(LETTER[0]-0.75*inch, 0.52*inch, str(doc.page))
        canvas.setStrokeColor(RULE); canvas.setLineWidth(0.4)
        canvas.line(0.75*inch, 0.68*inch, LETTER[0]-0.75*inch, 0.68*inch)
    canvas.restoreState()

doc = BaseDocTemplate(OUT, pagesize=LETTER,
                      leftMargin=0.75*inch, rightMargin=0.75*inch,
                      topMargin=0.7*inch, bottomMargin=0.85*inch,
                      title='JDUN | 15m ORB | Combined - Technical Documentation',
                      author='JDUN', subject='TradingView Pine Script v6 indicator documentation')
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='n')
doc.addPageTemplates([PageTemplate(id='all', frames=[frame], onPage=deco)])
doc.build(story)
print('built', OUT)
