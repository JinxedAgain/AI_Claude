# -*- coding: utf-8 -*-
"""Builds the JDUN | 15m ORB distribution guide (no internals, no defaults)."""
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import *  # noqa: F403 - Platypus flowables

OUT = 'JDUN-15m-ORB-Guide.pdf'

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
P('JDUN | 15m ORB', 'title')
P('Opening-range breakout indicator for TradingView — user guide', 'sub')
SP(4)
story.append(HRFlowable(width='100%', thickness=2.5, color=ACC))
SP(16)
P('A structured opening-range breakout tool that trades JDUN\'s model. It marks the session '
  'levels before the open, sits out the first fifteen minutes, waits for a breakout candle that '
  'passes a quality check, and then enters the pullback rather than chasing the break. Risk is '
  'defined by the breakout candle, targets are multiples of that risk, and the day is capped at '
  'a small number of trades.')
P('This guide covers what the indicator does, what appears on the chart, when each alert fires, '
  'and what every setting controls.')
SP(12)
table(None, [
    ['Platform', 'TradingView — Pine Script v6, overlay indicator'],
    ['Intended chart', '5-minute'],
    ['Opening range', '15 minutes, measured independently of the chart timeframe'],
    ['Markets', 'Designed around index futures; works on any liquid symbol with volume'],
    ['Signals', 'Entry, three take-profit levels, stop loss, and an end-of-day flatten'],
    ['Automation', 'Alert names are webhook-ready and unchanged across versions'],
], [1.35*inch, 5.1*inch])
SP(6)
callout('This is an indicator, not an automated strategy',
        'It draws levels and fires alerts. It does not place orders, and it is not a TradingView '
        'strategy with a built-in tester. Everything downstream depends on how you configure your '
        'alerts and, if you automate, your webhook. You remain responsible for every order that '
        'reaches your broker.')

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════
H1('1. The idea')
P('Most opening-range tools buy the moment price pokes above the range. That is the worst price '
  'of the move and the easiest one to be shaken out of. This indicator is built the other way '
  'round: the break is treated as information, not as an entry.')
P('The daily rhythm is the same every session:')
N(1, '**Mark the map.** Before the open, the levels price actually reacts to are drawn: pre-market '
      'high and low, the previous day\'s high and low, the overnight Asia range, VWAP, and the '
      'volume point of control.')
N(2, '**Sit out the open.** The first fifteen minutes form the opening range. Nothing can trade '
      'during that window — it is the noisiest part of the day and the range it builds is the '
      'reference for everything after it.')
N(3, '**Wait for a real break.** A candle has to CLOSE beyond the range, not wick through it. '
      'That candle is then quality-checked before it counts.')
N(4, '**Enter the pullback.** Rather than chasing the breakout candle, the indicator measures a '
      'retracement zone from it and waits for price to come back into that zone. Entering there '
      'means a tighter stop and a better reward-to-risk on the same move.')
N(5, '**Define risk from the candle that caused it.** The stop sits beyond the breakout candle\'s '
      'extreme, so the risk is whatever that candle actually was, not a fixed number of points.')
N(6, '**Scale out and protect.** Three targets, all expressed as multiples of that risk. Most of '
      'the position comes off at the first, and the stop moves to break-even at the same moment.')
N(7, '**Stop when the day is done.** A hard cap on trades per day and on losses per day, and a '
      'flatten deadline so nothing is carried into the close.')
SP(3)
P('Each of those stages has its own settings, so the behaviour can be loosened or tightened '
  'without changing the shape of the model.')

H1('2. The trading model')
H2('The opening range')
P('The high and low of the first fifteen minutes of the session. This is measured on its own '
  'clock, independently of your chart timeframe, so the range is the same whether you are '
  'watching 1-minute or 5-minute candles. The range and its midpoint are drawn on the chart; the '
  'midpoint matters more than most traders expect and is treated as a level in its own right.')
H2('The breakout candle')
P('A break only counts when a candle closes beyond the range — a wick through it is ignored. That '
  'candle is then tested for quality, because not every break is real. The indicator looks at '
  'three things:')
B('**Conviction in the body.** A candle that is mostly wick did not close where it wanted to. '
  'A minimum body proportion is required.')
B('**Participation.** Volume has to be expanding, not just present. Rising volume means buyers '
  'are bidding up, rather than there merely being more of them.')
B('**Agreement between size and volume.** A large candle on weak volume is treated as an anomaly '
  '— size and participation disagree, so the move is not backed by real money and is skipped.')
P('A candle that fails any of these does not arm a setup at all. The indicator simply keeps '
  'waiting. Only one setup arms per excursion outside the range, so a long trend does not '
  'generate a stream of overlapping signals; if price closes back inside the range, a genuine '
  'second break later in the day can arm afresh.')
H2('The entry')
P('Once a setup is armed, a retracement zone is measured from the breakout candle and drawn on '
  'the chart. The entry is a pullback into that zone. Three models are available:')
table(['Entry model', 'Behaviour'], [
 ['Golden Pocket', 'The primary model. Enter the pullback into a fibonacci retracement zone measured from the breakout candle.'],
 ['Level Retest', 'The simpler alternative. Enter when price comes back and touches the broken range level itself.'],
 ['Either', 'Whichever of the two happens first.'],
], [1.35*inch, 5.1*inch])
P('There is also a fallback for moves that never retrace far enough to reach the primary zone. '
  'When the break extends aggressively, the zone is re-measured across the extended move and '
  'sits shallower, so a strong trend is not simply missed. The dashboard tells you which of the '
  'two is currently armed.')
P('An optional confluence filter requires the entry zone to line up with one of the marked '
  'session levels. It is the highest-probability condition in the model and also the strictest — '
  'expect noticeably fewer trades with it on. It is off by default, but whether confluence is '
  'present is always reported on the dashboard so you can judge it yourself.')
H2('Risk and targets')
P('The stop is placed just beyond the breakout candle\'s extreme, with a small configurable pad. '
  'Risk is the distance from your entry to that stop, and it is different on every trade — which '
  'is the point. Everything else is expressed as a multiple of it:')
B('**Three take-profit levels**, each a configurable multiple of the trade\'s own risk. Each fires '
  'its own alert the moment price touches it, so a single candle that runs clean through all '
  'three fires all three on that candle rather than one per candle.')
B('**A maximum stop width.** If the breakout candle is so large that the stop would be wider than '
  'your limit, the setup is rejected rather than taken at bad risk. This can be switched off.')
B('**An optional high/low-of-day target** for the second level, for traders who prefer a '
  'structural target to a fixed multiple. It is never allowed to sit closer than the first target.')
H2('Protecting the trade')
P('When the first target is reached, the stop moves to your entry price. From that moment the '
  'trade cannot lose. This behaviour is on by default and it is the single most important thing '
  'to understand about reading the chart — see the next section.')

story.append(PageBreak())

H1('3. Reading the chart')
H2('Session levels')
P('Each reference level is drawn as a full line running from an earlier session\'s open across to '
  'the live candle, with its name and price sitting at the right-hand end beside the forming bar '
  '— so nothing needs scrolling to read. How far back the lines reach is adjustable, as are their '
  'thickness and line style, so the whole set can be made as light or as prominent as you like.')
table(['Drawing', 'Colour', 'What it is'], [
 ['ORB high / low', 'green / red', 'The locked opening range.'],
 ['ORB Mid', 'grey', 'The midpoint of the range.'],
 ['PM High / Low', 'orange', 'Pre-market extremes.'],
 ['Prev Day High / Low', 'blue', 'Yesterday\'s session extremes.'],
 ['Asia High / Low', 'purple', 'Overnight extremes.'],
 ['POC', 'red', 'Point of control — where the most volume has traded today.'],
 ['VWAP', 'blue', 'Session VWAP, resets each day.'],
 ['Entry zone', 'yellow pair', 'The live retracement zone. Visible only while a setup is armed, and gone the moment the entry fires or the setup expires.'],
 ['EMA pair', 'teal / grey', 'Trend context only. Gates nothing in the trade logic.'],
], [1.35*inch, 1.0*inch, 4.1*inch])
H2('Trade levels')
P('Every entry draws five horizontal lines — entry, stop, and the three targets — each named at '
  'its right-hand end. They extend for the rest of that trading day and then freeze, so previous '
  'trades keep their levels on the chart. You can see every target a trade had, including the '
  'ones price never reached, which makes reviewing a session much faster.')
callout('The stop line splits in two once the first target is hit',
        'Because the stop moves to break-even at the first target, the drawn stop changes as well. '
        'There is one stop line and it moves with your stop. When the first target is reached it '
        'relocates, turns orange and is renamed, so what is drawn is always the stop that is actually '
        'live, and a stop-out after that lands on it marked BE rather than SL — you kept what you took '
        'off at the first target and gave back nothing. Where it lands is up to you: by default it sits '
        'exactly on your entry, and the Break-even offset setting can push it into profit instead, so a '
        'come-back exit is green rather than flat. That is worth setting if your fills tend to arrive a '
        'moment after the alert.')
H2('Markers')
table(['Marker', 'Meaning'], [
 ['BUY / SELL flag', 'An entry fired. Each entry is also marked a second time as an X on the opposite side of the bar, so the signal is never lost behind another drawing or clipped at the edge of the pane.'],
 ['TP 1 / TP 2 / TP 3', 'That target was reached; the mark is drawn ON the target level. When one candle takes two or three targets at once, the marks stay on their own levels and the names move into a single block just clear of the wick — TP 1 nearest the candle, TP 2 and TP 3 stacked above it — so they never overlap and the order reads the way price travelled.'],
 ['SL', 'Stopped out for a real loss, marked on the original stop.'],
 ['BE', 'Stopped out at break-even, once the first target had already pulled the stop up to your entry. Marked in orange, so a scratch is never shown as a loss.'],
 ['BE+', 'The same, but with a break-even offset set, so the stop sat in profit and the exit banked a gain rather than scratching.'],
 ['CLOSE', 'The end-of-day flatten fired with a position still open.'],
 ['EMA+ / EMA-', 'Price closed through an EMA on above-average volume. A momentum heads-up, not a trade.'],
], [1.25*inch, 5.2*inch])
callout('Exit marks sit on the level they hit',
        'Each exit is drawn at the price it fired on rather than beside the candle, so it lands on '
        'its own line and you can read at a glance which level was reached. Entry flags are the '
        'exception and still sit beside the bar, because an entry has no level of its own.', 'info')

H1('4. When each signal fires')
P('Some signals wait for the candle to finish and some do not. The difference decides how quickly '
  'an order reaches your broker, so it is worth knowing.')
table(['Event', 'Timing', 'Why'], [
 ['Breakout / arming', 'Candle close, always', 'A break is only a break once a candle has closed beyond the range. A wick through it is not a signal.'],
 ['Entry', 'Immediately on touch', 'The pullback entry fires the instant price trades into the zone, the way a resting limit order would fill. It does not wait for the candle.'],
 ['Entry (Level Retest only)', 'Candle close, always', 'That model is defined by where the candle closes, so it cannot be known before the candle ends.'],
 ['Take profits and stop', 'Immediately on touch', 'An exit should never wait for a candle to finish.'],
 ['End-of-day flatten', 'Immediately', 'A safety net. It fires after hours by design.'],
], [1.5*inch, 1.35*inch, 3.6*inch])
callout('Set your alert to "Once Per Bar" — not "Once Per Bar Close"',
        'A TradingView alert permanently captures the trigger frequency you chose when you created it. '
        'On "Once Per Bar Close", TradingView holds every signal until the candle finishes and none of '
        'the immediate behaviour above applies — including your stop and your targets. This is the most '
        'common setup mistake with this indicator. If your fills feel consistently late, check this first.')
P('The entry can also be switched back to candle-close behaviour with a single setting, if you '
  'would rather have the confirmation than the speed.')

story.append(PageBreak())

H1('5. Alerts and automation')
P('Ten alert conditions appear in TradingView\'s Condition dropdown. The first eight are the trade '
  'engine. The last two are momentum context and are **not** trade signals — do not point an order '
  'webhook at them unless you specifically intend to.')
table(['Alert', 'Fires when'], [
 ['Buy / Sell', 'Either direction enters — one alert for both.'],
 ['Buy', 'A long entry.'],
 ['Sell', 'A short entry.'],
 ['Take Profit 1', 'The first target is reached.'],
 ['Take Profit 2', 'The second target is reached.'],
 ['Take Profit 3', 'The third target is reached.'],
 ['Stop Loss', 'The live stop is hit — the original stop, or break-even after the first target.'],
 ['Close All / Flatten', 'A position is still open at the flatten deadline.'],
 ['EMA Cross Buy (volume)', 'Context only. No position, no target, no stop.'],
 ['EMA Cross Sell (volume)', 'Context only. No position, no target, no stop.'],
], [1.6*inch, 4.85*inch])
H2('Putting prices into the alert message')
P('The live entry, stop and all three targets are exposed to the alert message, so an automation '
  'webhook can receive the actual numbers rather than just the fact that something fired. Use '
  'TradingView\'s placeholder syntax in the message body:')
CODE('{{plot("Entry")}}   {{plot("SL")}}\n'
     '{{plot("TP 1")}}    {{plot("TP 2")}}    {{plot("TP 3")}}')
P('These values are visible in TradingView\'s Data Window and are deliberately invisible on the chart.')
H2('The timeframe lock')
P('A TradingView alert permanently captures the chart timeframe it was created on. An alert set up '
  'by accident on the wrong chart would otherwise keep firing forever at the wrong resolution. The '
  'indicator therefore refuses to fire unless the chart matches the signal timeframe you have '
  'chosen, and the dashboard shows a red warning whenever the chart does not match. Leave this on.')
H2('Alert setup checklist')
N(1, 'Open the chart on the signal timeframe — the 5-minute unless you have changed it.')
N(2, 'Create one alert per action you want to automate, choosing the condition by name.')
N(3, 'Set the trigger frequency to **Once Per Bar**.')
N(4, 'Put your webhook payload in the message body, using the placeholders above for prices.')
N(5, 'Confirm the dashboard reads OK, not WRONG TF.')

H1('6. The on-chart panels')
H2('Dashboard')
P('A live read on where the session stands.')
table(['Row', 'Shows'], [
 ['State', 'Range forming, waiting, armed long or short, or in a position.'],
 ['Trades / Losses', 'Today\'s count against both daily caps. Turns orange when either is reached.'],
 ['Setup', 'Which entry model is currently armed.'],
 ['Entry zone', 'The live zone bounds.'],
 ['Stacked level', 'Whether the setup lines up with a marked session level — reported even when the confluence filter is switched off.'],
 ['Risk if taken', 'The stop distance for the armed setup, and a warning if it exceeds your maximum.'],
 ['Entry / SL', 'The open trade\'s entry and its CURRENT stop — so it shows break-even once the first target has hit.'],
 ['Signal TF', 'Whether the chart matches your signal timeframe.'],
 ['EMA trend', 'Trend context.'],
], [1.25*inch, 5.2*inch])
H2('Performance table')
P('A rolling review of every setup the indicator has produced on the chart you are looking at, '
  'expressed in R — that is, in multiples of each trade\'s own risk, which is the only honest way '
  'to compare trades whose stops were different widths. It reports signals taken, wins and losses, '
  'win rate, profit factor, total and average R, and how often each target was reached.')
P('The maths is position-weighted, so a trade that scaled out at the first target and then stopped '
  'at break-even is correctly counted as a small win rather than a scratch. The assumed scale-out '
  'proportion is a setting, and it affects this table only — it changes no signal and no alert.')
callout('What the performance table is not',
        'It is a simulation of the rules against historical candles, not a record of your fills. It '
        'assumes you were filled exactly at each level, with no slippage and no commission. When a '
        'target and the stop are both touched inside the same candle it credits the target, because '
        'the order they happened in cannot be known from historical data. Treat it as a way to sanity-'
        'check the rules on a symbol, never as expected profit.')

story.append(PageBreak())

H1('7. Settings')
P('Grouped as they appear in the indicator\'s settings panel. Shipped defaults are already tuned to '
  'the model — this section describes what each control does so you can judge whether to move it.')

def igroup(name, rows):
    story.append(CondPageBreak(1.5*inch))
    H2(name)
    table(['Setting', 'What it controls'], rows, [2.15*inch, 4.3*inch])

igroup('Session & Opening Range', [
 ['Timezone for all session times', 'One timezone for every session field in the indicator, so the times you type are the times you mean. Handles daylight saving.'],
 ['Regular session', 'The trading session that defines the day.'],
 ['Pre-market window', 'The window whose high and low are marked as pre-market levels.'],
 ['Asia session', 'The overnight window. It crosses midnight, which is handled.'],
 ['Opening range length', 'How many minutes of the open form the range. Nothing trades until it closes.'],
])
igroup('Entry', [
 ['Entry model', 'Golden Pocket, Level Retest, or whichever comes first.'],
 ['Two-bar setup fallback', 'Whether to re-measure a shallower zone when a break extends too aggressively to retrace into the primary one.'],
 ['Two-bar zone start / end', 'The bounds of that shallower fallback zone.'],
 ['Fire entries in real time', 'On: the entry fires the instant price touches the zone. Off: it waits for the candle to close.'],
 ['Setup valid for N bars', 'How long an armed zone stays live before it is discarded and the indicator waits for a fresh break.'],
 ['Require a stacked key level', 'The confluence filter. Requires the entry to also sit on a marked session level. Strict — far fewer trades.'],
 ['Stacked level distance', 'How close to a level counts as stacked.'],
])
igroup('Breakout candle quality', [
 ['Minimum body %', 'How much of the candle must be body rather than wick for the break to count.'],
 ['Require rising volume', 'Demand expanding volume on the breakout candle, not merely above-average volume.'],
 ['Volume average length', 'The lookback for the volume average.'],
 ['Reject anomalies', 'Discard a large candle that printed on weak volume, where size and participation disagree.'],
 ['Anomaly size', 'How large, relative to recent range, before that test applies.'],
])
igroup('Risk & Targets', [
 ['TP1 / TP2 / TP3', 'Each target as a multiple of the trade\'s own risk.'],
 ['Trim fraction at TP1', 'The scale-out proportion assumed by the performance table. Affects that table only.'],
 ['TP2 = high/low of day', 'Use a new high or low of day as the second target instead of a fixed multiple.'],
 ['Stop to break-even after TP1', 'Move the stop to your entry once the first target is reached. Strongly recommended.'],
 ['Break-even offset', 'How far PAST break-even that stop goes, as a share of the trade\'s own risk. Zero is a true break-even; above that the stop sits in profit, so a come-back exit is green rather than flat. It covers the gap between an alert firing and the order filling.'],
 ['Stop padding', 'How far beyond the breakout candle the stop sits.'],
 ['Max stop distance', 'Reject a setup whose stop would be wider than this. Set to zero to disable.'],
])
igroup('Daily Limits', [
 ['Max trades per day', 'A hard cap. No further entries fire once it is reached.'],
 ['Max losses per day', 'The circuit breaker. A loss counts only when a trade is stopped out without ever reaching the first target.'],
])
igroup('Alerts', [
 ['Alert window', 'The hours during which entries are allowed to fire.'],
 ['TP/SL buffer', 'Fire exit alerts fractionally early, so a market order fills near the intended price instead of chasing through it.'],
 ['Shade the alert window', 'Tint the chart background while the window is open.'],
 ['Lock alerts to signal timeframe', 'Prevent an alert created on the wrong chart from ever firing. Leave on.'],
 ['Signal timeframe', 'The chart resolution alerts are locked to.'],
 ['Flatten after', 'Your hard flat-by deadline. Anything still open when it passes gets the flatten alert.'],
])
igroup('Levels', [
 ['Which levels to draw', 'Independent toggles for pre-market, previous day, Asia, VWAP, point of control and the range midpoint.'],
 ['POC bucket size', 'How coarsely prices are grouped when locating the point of control.'],
 ['Level line width / style', 'Thickness and solid, dashed or dotted, shared across the whole level set.'],
 ['Extend levels back', 'How many sessions to the left each level line reaches.'],
 ['Label every level', 'Name and price at the right-hand end of each line.'],
])
igroup('Visuals', [
 ['Opening range lines', 'The range high and low, with their own colours and thickness.'],
 ['Entry zone while live', 'The yellow zone pair while a setup is armed.'],
 ['Trade lines', 'Entry, stop and all three targets drawn on every trade, past ones included.'],
 ['Redundant entry X marker', 'The second entry mark on the opposite side of the bar.'],
 ['Name each trade line', 'Labels at the right-hand end of each trade line.'],
 ['Dashboard / Performance table', 'Show or hide each panel, and choose where it sits.'],
])
igroup('Context layer (no trade signals)', [
 ['EMA cross signals', 'The EMA+ / EMA- momentum heads-up and its two alerts.'],
 ['Fast / Slow EMA', 'The EMA pair used for trend context and for those crosses.'],
 ['Cross which EMA', 'Which of the pair must be crossed, or require agreement from both.'],
 ['Volume must exceed average by', 'How large a volume surge a cross needs before it is marked.'],
 ['Skip first N bars', 'Ignore crosses in the noisy opening minutes.'],
])

story.append(PageBreak())
H1('8. Getting the most out of it')
B('**Run it on the signal timeframe.** The 5-minute unless you have deliberately changed it. The '
  'indicator needs a chart finer than the opening range itself.')
B('**Leave the daily caps on.** They exist because the model\'s edge is concentrated in the first '
  'part of the session. Trading past two losses is how a good week becomes a bad one.')
B('**Watch the dashboard before the entry, not after.** It tells you the stop distance and whether '
  'the setup has confluence while the setup is still armed — which is when that information is '
  'worth something.')
B('**Use the confluence filter to grade, not only to gate.** Even with the filter off, the '
  'dashboard reports whether the setup lines up with a marked level. Many traders prefer to size '
  'differently on that rather than skip the trade entirely.')
B('**Review with the frozen trade lines.** Because past trades keep their levels, a scroll back '
  'through the week shows you exactly which targets were reachable and which were not.')

H1('9. Limitations')
B('**It does not place orders.** It fires alerts. Your alert configuration and webhook decide what '
  'actually happens.')
B('**"Once Per Bar" is required** for the immediate entry and exit behaviour. On "Once Per Bar '
  'Close" every signal waits for the candle.')
B('**The order of events inside a single candle cannot be known** from historical data. Where a '
  'target and the stop are both touched in one candle, the performance table credits the target. '
  'Live, whichever your broker fills first is what you get.')
B('**No slippage or commission** is modelled anywhere in the performance figures.')
B('**The Level Retest model cannot fire before the candle closes**, by construction.')
B('**A break-even stop-out does not count toward the daily loss limit**, because it is not a loss.')
B('**Drawing history is finite.** TradingView caps how many lines and labels a script may keep, so '
  'on a long chart the oldest trade drawings are dropped. Roughly the last hundred trades stay visible.')

SP(12)
story.append(HRFlowable(width='100%', thickness=0.8, color=RULE))
SP(8)
P('**Risk disclaimer.** This indicator is a technical analysis tool provided for informational and '
  'educational purposes. It is not financial advice, and nothing in it is a recommendation to buy '
  'or sell any instrument. Trading futures and other leveraged products carries substantial risk '
  'of loss and is not suitable for every investor. Past performance, including any figure shown in '
  'the indicator\'s performance table, does not indicate future results. You are solely responsible '
  'for your own trading decisions and for any orders placed through automation.', 'cap')

def deco(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont('Helvetica', 7.8)
        canvas.setFillColor(SLATE)
        canvas.drawString(0.75*inch, 0.52*inch, 'JDUN | 15m ORB — user guide')
        canvas.drawRightString(LETTER[0]-0.75*inch, 0.52*inch, str(doc.page))
        canvas.setStrokeColor(RULE); canvas.setLineWidth(0.4)
        canvas.line(0.75*inch, 0.68*inch, LETTER[0]-0.75*inch, 0.68*inch)
    canvas.restoreState()

doc = BaseDocTemplate(OUT, pagesize=LETTER,
                      leftMargin=0.75*inch, rightMargin=0.75*inch,
                      topMargin=0.7*inch, bottomMargin=0.85*inch,
                      title='JDUN | 15m ORB - User Guide',
                      author='JDUN', subject='TradingView indicator user guide')
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='n')
doc.addPageTemplates([PageTemplate(id='all', frames=[frame], onPage=deco)])
doc.build(story)
print('built', OUT)
