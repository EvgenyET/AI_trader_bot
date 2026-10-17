# ui_widgets.py — HTML/SVG-рендер в QWebEngineView
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView

# --- НАЧАЛО ИЗМЕНЕНИЙ В ШАБЛОНЕ ---
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self' 'unsafe-inline' data:;">
<title>Chart</title>
<style>
  html, body { margin:0; height:100%; background:#1e1e1e; overflow:hidden; }
  #wrap { width:100%; height:100%; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; }
  .label { font-weight:600; }
  .grid { stroke: rgba(255,255,255,0.15); stroke-width:1; }

  /* <<< ИЗМЕНЕНИЕ 4: Новые цвета для свечей и теней >>> */
  .wick { stroke-width:1; } /* Общий стиль для теней */
  .bull-wick { stroke: #00f100; } /* Тень зеленой свечи */
  .bear-wick { stroke: #f62425; } /* Тень красной свечи */
  .bull { fill: #00f100; } /* Тело зеленой свечи */
  .bear { fill: #f62425; } /* Тело красной свечи */

  .level-line { 
    stroke-width: 1.5; 
    fill: none; 
    stroke-dasharray: 8 6;
  }
  .axis-text { fill: rgba(255,255,255,0.85); font-size:11px; }
  .axis-time { fill: rgba(255,255,255,0.75); font-size:10px; }
  .axis-price-box { fill: #2a2a2a; stroke: #444; stroke-width:1; }
  .axis-price-text { fill:#eaeaea; font-size:11px; }
</style>
</head>
<body>
<div id="wrap"></div>

<svg style="position:absolute; width:0; height:0;">
  <defs>
    <filter id="softShadow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="1.8" result="blur"></feGaussianBlur>
      <feOffset dx="0" dy="0" result="offsetBlur"></feOffset>
      <feMerge>
        <feMergeNode in="offsetBlur"></feMergeNode>
        <feMergeNode in="SourceGraphic"></feMergeNode>
      </feMerge>
    </filter>
  </defs>
</svg>

<script>
(function(){
  const DATA = __DATA__;
  const LEVELS = __LEVELS__;
  const ZOOM_TO_LEVELS = __ZOOM__;

  const PAD = {left:10, right:70, top:16, bottom:28};

  function computePriceRange(candles, levels, zoomToLevels){
    let minP = Math.min(...candles.map(c=>c.low));
    let maxP = Math.max(...candles.map(c=>c.high));
    const lvlVals = Object.values(levels).filter(v=>v!==null && v!==undefined);
    if (zoomToLevels && lvlVals.length){
      minP = Math.min(minP, ...lvlVals);
      maxP = Math.max(maxP, ...lvlVals);
      const pad = (maxP-minP)*0.15 || 1.0;
      minP -= pad; maxP += pad;
    } else {
      if (lvlVals.length){
        minP = Math.min(minP, ...lvlVals);
        maxP = Math.max(maxP, ...lvlVals);
      }
      const pad = (maxP-minP)*0.05 || 1.0;
      minP -= pad; maxP += pad;
    }
    if (!isFinite(minP) || !isFinite(maxP)) { minP = 0; maxP = 1; }
    if (minP === maxP) { minP -= 1; maxP += 1; }
    return {minP, maxP};
  }

  function yFor(price, minP, maxP, top, height){
    const norm = (price - minP)/(maxP - minP);
    return top + (1 - norm)*height;
  }

  function formatTime(ms){
    const d = new Date(ms);
    const hh = d.getUTCHours().toString().padStart(2,'0');
    const mm = d.getUTCMinutes().toString().padStart(2,'0');
    return `${hh}:${mm}`;
  }
  function formatDate(ms){
    const d = new Date(ms);
    const dd = d.getUTCDate().toString().padStart(2,'0');
    const mm = (d.getUTCMonth()+1).toString().padStart(2,'0');
    return `${dd}.${mm}`;
  }

  function build(){
    const wrap = document.getElementById('wrap');
    const w = wrap.clientWidth || 800;
    const h = wrap.clientHeight || 600;

    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width','100%');
    svg.setAttribute('height','100%');
    svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
    svg.setAttribute('preserveAspectRatio','none');
    wrap.innerHTML='';
    wrap.appendChild(svg);

    const plotX = PAD.left;
    const plotY = PAD.top;
    const plotW = Math.max(1, w - PAD.left - PAD.right);
    const plotH = Math.max(1, h - PAD.top - PAD.bottom);

    const pr = computePriceRange(DATA, LEVELS, ZOOM_TO_LEVELS);
    const minP = pr.minP, maxP = pr.maxP;

    // grid
    const gridGroup = document.createElementNS(svg.namespaceURI,'g');
    for (let i=0;i<=6;i++){
      const y = plotY + (i/6)*plotH;
      const ln = document.createElementNS(svg.namespaceURI,'line');
      ln.setAttribute('x1', plotX); ln.setAttribute('y1', y);
      ln.setAttribute('x2', plotX + plotW); ln.setAttribute('y2', y);
      ln.setAttribute('class','grid');
      gridGroup.appendChild(ln);
    }
    svg.appendChild(gridGroup);

    // candles
    const n = DATA.length;
    const candleGroup = document.createElementNS(svg.namespaceURI,'g');
    const candleW = Math.max(2, plotW / Math.max(60, n*1.2));
    for (let i=0;i<n;i++){
      const c = DATA[i];
      const x = plotX + (n<=1 ? plotW/2 : (i/(n-1))*plotW);
      const up = c.close >= c.open;

      const yO = yFor(c.open, minP, maxP, plotY, plotH);
      const yC = yFor(c.close, minP, maxP, plotY, plotH);
      const yH = yFor(c.high, minP, maxP, plotY, plotH);
      const yL = yFor(c.low,  minP, maxP, plotY, plotH);

      const wick = document.createElementNS(svg.namespaceURI,'line');
      wick.setAttribute('x1',x); wick.setAttribute('y1',yH);
      wick.setAttribute('x2',x); wick.setAttribute('y2',yL);
      // <<< ИЗМЕНЕНИЕ 4: Присваиваем класс тени в зависимости от направления свечи >>>
      wick.setAttribute('class', up ? 'wick bull-wick' : 'wick bear-wick');
      candleGroup.appendChild(wick);

      const body = document.createElementNS(svg.namespaceURI,'rect');
      const top = Math.min(yO,yC);
      const bh = Math.max(1, Math.abs(yC - yO));
      body.setAttribute('x', x - candleW/2);
      body.setAttribute('y', top);
      body.setAttribute('width', candleW);
      body.setAttribute('height', bh);
      body.setAttribute('class', up ? 'bull' : 'bear');
      candleGroup.appendChild(body);
    }
    svg.appendChild(candleGroup);

    // levels + labels
    const levelGroup = document.createElementNS(svg.namespaceURI,'g');
    const labelGroup = document.createElementNS(svg.namespaceURI,'g');

    const lvls = [];
    if (LEVELS.stop_loss != null) lvls.push({name:'Stop-Loss', val: LEVELS.stop_loss, color:'#ff5370'});
    if (LEVELS.tp1 != null)       lvls.push({name:'Take-Profit 1', val: LEVELS.tp1, color:'#64b5f6'});
    if (LEVELS.tp2 != null)       lvls.push({name:'Take-Profit 2', val: LEVELS.tp2, color:'#9575cd'});
    if (LEVELS.entry != null)     lvls.push({name:'Entry',    val: LEVELS.entry,     color:'#ffd54f'});

    lvls.sort((a, b) => b.val - a.val);

    let finalFontSize = 13;
    const minFontSize = 8;

    while (finalFontSize > minFontSize) {
        let collisionDetected = false;
        const testRects = [];
        const testTxt = document.createElementNS(svg.namespaceURI, 'text');
        svg.appendChild(testTxt);
        testTxt.setAttribute('class', 'label');
        testTxt.setAttribute('font-size', finalFontSize);

        for (const lv of lvls) {
            const y = yFor(lv.val, minP, maxP, plotY, plotH);
            testTxt.textContent = `${lv.name}: ${lv.val.toFixed(0)}`; // Используем округление для расчета
            let bbox = testTxt.getBBox();
            let testRect = { x: bbox.x, y: y - bbox.height / 2, width: bbox.width, height: bbox.height };
            const verticalPadding = 10;
            let overlaps = false;
            for (const r of testRects) {
                if (testRect.y < r.y + r.height + verticalPadding && testRect.y + testRect.height + verticalPadding > r.y) {
                    overlaps = true;
                    break;
                }
            }
            if (overlaps) {
                collisionDetected = true;
                break;
            }
            testRects.push(testRect);
        }
        svg.removeChild(testTxt);
        if (!collisionDetected) {
            break;
        } else {
            finalFontSize--;
        }
    }

    function drawLabel(y, text, color, fontSize){
      const textX = plotX + 5;
      const gap = 8;
      const txt = document.createElementNS(svg.namespaceURI,'text');
      txt.textContent = text;
      txt.setAttribute('class','label');
      txt.setAttribute('fill', color);
      txt.setAttribute('filter','url(#softShadow)');
      txt.setAttribute('dominant-baseline','middle');
      txt.setAttribute('text-anchor','start');
      txt.setAttribute('font-size', fontSize);
      txt.setAttribute('x', textX);
      txt.setAttribute('y', y);

      svg.appendChild(txt);
      const textWidth = txt.getBBox().width;
      svg.removeChild(txt);

      const lineStartX = textX + textWidth + gap;
      const levelLine = document.createElementNS(svg.namespaceURI,'line');
      levelLine.setAttribute('x1', lineStartX);
      levelLine.setAttribute('y1', y);
      levelLine.setAttribute('x2', plotX + plotW);
      levelLine.setAttribute('y2', y);
      levelLine.setAttribute('class','level-line');
      levelLine.setAttribute('stroke', color);

      levelGroup.appendChild(levelLine);
      labelGroup.appendChild(txt);
    }

    for (const lv of lvls){
      const y = yFor(lv.val, minP, maxP, plotY, plotH);
      // <<< ИЗМЕНЕНИЕ 1: Округляем значения уровней до целых чисел >>>
      const text = `${lv.name}: ${lv.val.toFixed(0)}`;
      drawLabel(y, text, lv.color, finalFontSize);
    }
    svg.appendChild(levelGroup);
    svg.appendChild(labelGroup);

    // RIGHT price axis
    const axisGroup = document.createElementNS(svg.namespaceURI,'g');
    const ticks = 6;
    for (let i=0;i<=ticks;i++){
      const y = plotY + (i/ticks)*plotH;
      const v = maxP - (i/ticks)*(maxP-minP);
      const ln = document.createElementNS(svg.namespaceURI,'line');
      ln.setAttribute('x1', plotX + plotW - 6); ln.setAttribute('y1', y);
      ln.setAttribute('x2', plotX + plotW);     ln.setAttribute('y2', y);
      ln.setAttribute('class','grid');
      axisGroup.appendChild(ln);

      // <<< ИЗМЕНЕНИЕ 2: Округляем шкалу для дорогих монет >>>
      const isMajorCoin = (maxP > 5000); // Эвристика для BTC, ETH
      const txt = isMajorCoin ? v.toFixed(0) : v.toFixed(4);

      const g = document.createElementNS(svg.namespaceURI,'g');
      const paddingX = 6, paddingY = 3;
      const m = document.createElementNS(svg.namespaceURI,'text');
      m.textContent = txt; m.setAttribute('class','axis-price-text');
      m.setAttribute('x', 0); m.setAttribute('y', 0);
      svg.appendChild(m);
      const bb = m.getBBox();
      svg.removeChild(m);
      const boxW = bb.width + paddingX*2;
      const boxH = bb.height + paddingY*2;
      const boxX = plotX + plotW + 4;
      const boxY = y - boxH/2 + 1;
      const rect = document.createElementNS(svg.namespaceURI,'rect');
      rect.setAttribute('x', boxX); rect.setAttribute('y', boxY);
      rect.setAttribute('width', boxW); rect.setAttribute('height', boxH);
      rect.setAttribute('rx', 4); rect.setAttribute('ry', 4);
      rect.setAttribute('class','axis-price-box');
      const t = document.createElementNS(svg.namespaceURI,'text');
      t.textContent = txt;
      t.setAttribute('class','axis-price-text');
      t.setAttribute('x', boxX + paddingX);
      t.setAttribute('y', boxY + boxH - paddingY - 2);
      g.appendChild(rect); g.appendChild(t);
      axisGroup.appendChild(g);
    }
    svg.appendChild(axisGroup);

    // BOTTOM time axis
    const timeGroup = document.createElementNS(svg.namespaceURI,'g');
    if (n>0){
      const target = 10;
      const step = Math.max(1, Math.round(n/target));
      let lastDate = null;
      for (let i=0;i<n;i+=step){
        const c = DATA[i];
        const x = plotX + (n<=1 ? plotW/2 : (i/(n-1))*plotW);
        const dateStr = formatDate(c.time);
        const timeStr = formatTime(c.time);
        const ln = document.createElementNS(svg.namespaceURI,'line');
        ln.setAttribute('x1', x); ln.setAttribute('y1', plotY + plotH);
        ln.setAttribute('x2', x); ln.setAttribute('y2', plotY + plotH + 4);
        ln.setAttribute('class','grid');
        timeGroup.appendChild(ln);

        // <<< ПУНКТ 3: Эта логика уже верна. Дата (t2) добавляется только при смене lastDate >>>
        const showDate = (lastDate !== dateStr);
        lastDate = dateStr;

        const t1 = document.createElementNS(svg.namespaceURI,'text');
        t1.textContent = timeStr;
        t1.setAttribute('class','axis-time');
        t1.setAttribute('x', x - 14);
        t1.setAttribute('y', plotY + plotH + 14);
        timeGroup.appendChild(t1);
        if (showDate){
          const t2 = document.createElementNS(svg.namespaceURI,'text');
          t2.textContent = dateStr;
          t2.setAttribute('class','axis-time');
          t2.setAttribute('x', x - 16);
          t2.setAttribute('y', plotY + plotH + 26);
          timeGroup.appendChild(t2);
        }
      }
    }
    svg.appendChild(timeGroup);
  }

  window.addEventListener('resize', build);
  window.addEventListener('DOMContentLoaded', build);
})();
</script>
</body>
</html>"""


# --- КОНЕЦ ИЗМЕНЕНИЙ В ШАБЛОНЕ ---

class CandlestickWidget(QWidget):
    def __init__(self, parent=None, label_font_size=11, align_left=False):
        super().__init__(parent)
        self.label_font_size = label_font_size
        self.align_left = align_left
        self.data = []
        self.stop_loss = None
        self.take_profit_1 = None
        self.take_profit_2 = None
        self.entry_price = None
        self.zoom_to_levels = False

        self.view = QWebEngineView(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)

        self._render_html()

    def set_data(self, candles):
        self.data = candles or []
        self._render_html()

    def set_levels(self, sl, tp1, tp2, entry):
        self.stop_loss = sl
        self.take_profit_1 = tp1
        self.take_profit_2 = tp2
        self.entry_price = entry
        self._render_html()

    def set_zoom_to_levels(self, enabled: bool):
        self.zoom_to_levels = bool(enabled)
        self._render_html()

    def _render_html(self):
        compact = []
        for c in self.data:
            compact.append({
                'open': float(c['open']),
                'high': float(c['high']),
                'low': float(c['low']),
                'close': float(c['close']),
                'time': int(c.get('time', 0))
            })
        levels = {
            'stop_loss': self.stop_loss if self.stop_loss is not None else None,
            'tp1': self.take_profit_1 if self.take_profit_1 is not None else None,
            'tp2': self.take_profit_2 if self.take_profit_2 is not None else None,
            'entry': self.entry_price if self.entry_price is not None else None,
        }
        html = HTML_TEMPLATE.replace('__DATA__', json.dumps(compact)) \
            .replace('__LEVELS__', json.dumps(levels)) \
            .replace('__ZOOM__', 'true' if self.zoom_to_levels else 'false')
        self.view.setHtml(html)