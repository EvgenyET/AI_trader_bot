# post_generator.py
import json
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtGui import QPixmap

# --- НАЧАЛО ИЗМЕНЕНИЙ: Полностью переработанный HTML-шаблон для поста ---
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self' 'unsafe-inline' data:;">
<title>Chart Post</title>
<style>
  html, body { 
    margin:0; height:100%; 
    background: linear-gradient(to bottom, #000000, #1e1e1e);
    overflow:hidden; 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    display: flex;
    flex-direction: column;
  }

  .header, .footer {
    background: linear-gradient(to bottom, #3c3c3c, #2a2a2a);
    color: #eaeaea;
    padding: 15px 40px; 
    flex-shrink: 0;
    box-shadow: inset 0px 5px 10px -5px rgba(0,0,0,0.5);
  }
  .footer {
    box-shadow: inset 0px -5px 10px -5px rgba(0,0,0,0.5);
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    border-bottom: 3px solid #444; 
  }

  /* <<< ИЗМЕНЕНИЕ: Общие стили для градиентного текста в шапке >>> */
  .header .symbol, .position-text {
    text-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .header .symbol {
    font-size: 42px;
    font-weight: 500; /* <<< ДОБАВЬТЕ ЭТУ СТРОКУ >>> */
    background-image: linear-gradient(to bottom, #c9c4bb, #9f998e);
  }

  .position-text {
    font-size: 48px;
  }

  /* <<< ИЗМЕНЕНИЕ: Новый яркий градиент для LONG >>> */
  .long-text {
    background-image: linear-gradient(to bottom, #77ff26, #63ec11, #457f17);
  }
  .short-text {
    background-image: linear-gradient(to bottom, #ff5050, #e00000);
  }

  .footer {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    font-size: 34px;
    border-top: 3px solid #444;
  }
  .footer-item {
    display: flex;
    align-items: center;
    gap: 15px;
  }
  .footer-item span {
    font-weight: 500;
  }

  #wrap { position: relative; flex: 1 1 0; min-height: 0; overflow: hidden; }
  .label { font-weight:600; }
  .grid { stroke: rgba(255,255,255,0.10); stroke-width:1; } 

  .wick { stroke-width:1; }
  .bull-wick { stroke: #00f100; }
  .bear-wick { stroke: #f62425; }
  .bull { fill: #00f100; }
  .bear { fill: #f62425; }

  .level-line { stroke-width:1.5; fill:none; stroke-dasharray: 8 6; }
  .axis-text { fill: rgba(255,255,255,0.85); font-size:14px; } 
  .axis-time { fill: rgba(255,255,255,0.75); font-size:13px; }

  .axis-price-box { fill: #2a2a2a; stroke: #444; stroke-width:1; }
  .axis-price-text { fill:#eaeaea; font-size:14px; }
</style>
</head>
<body>

<div class="header">
  <span class="symbol">__SYMBOL__/USDT (15m)</span>
  <span class="position-text __POSITION_CLASS__">__POSITION__</span>
</div>
<div id="wrap"></div>
<div class="footer">
  <div class="footer-item">✅ <span>Вход: __ENTRY__</span></div>
  <div class="footer-item">🎯 <span>TP1: __TP1__</span></div>
  <div class="footer-item">🎯 <span>TP2: __TP2__</span></div>
  <div class="footer-item">🚫 <span>SL: __SL__</span></div>
  <div class="footer-item" style="grid-column: span 2;">📊 <span>R/R: __RR__</span></div>
</div>

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
    window.__postReady = false;
    const wrap = document.getElementById('wrap');
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    if (!w || !h) { requestAnimationFrame(build); return; }

    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.style.position = 'absolute';
    svg.style.left = '0';
    svg.style.top = '0';
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
    const numGridLines = 12;
    for (let i=0; i<=numGridLines; i++){
      const y = plotY + (i/numGridLines)*plotH;
      const ln = document.createElementNS(svg.namespaceURI,'line');
      ln.setAttribute('x1', plotX); ln.setAttribute('y1', y);
      ln.setAttribute('x2', plotX + plotW); ln.setAttribute('y2', y);
      ln.setAttribute('class','grid');
      gridGroup.appendChild(ln);
    }

    const separatorLine = document.createElementNS(svg.namespaceURI,'line');
    separatorLine.setAttribute('x1', plotX + plotW); separatorLine.setAttribute('y1', plotY);
    separatorLine.setAttribute('x2', plotX + plotW); separatorLine.setAttribute('y2', plotY + plotH);
    separatorLine.setAttribute('class','grid');
    gridGroup.appendChild(separatorLine);

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

    function placeLabel(y, text, color){
      const fontSize = 24;
      const textX = plotX + 5;
      const gap = 12;

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
      const text = `${lv.name}: ${lv.val.toFixed(0)}`;
      placeLabel(y, text, lv.color);
    }
    svg.appendChild(levelGroup);
    svg.appendChild(labelGroup);

    // RIGHT price axis
    const axisGroup = document.createElementNS(svg.namespaceURI,'g');
    const ticks = numGridLines;
    for (let i=0;i<=ticks;i++){
      const y = plotY + (i/ticks)*plotH;
      const v = maxP - (i/ticks)*(maxP-minP);
      const ln = document.createElementNS(svg.namespaceURI,'line');
      ln.setAttribute('x1', plotX + plotW); ln.setAttribute('y1', y);
      ln.setAttribute('x2', plotX + plotW + 4); ln.setAttribute('y2', y);
      ln.setAttribute('class','grid');
      axisGroup.appendChild(ln);

      const isMajorCoin = (maxP > 1000);
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
      const boxX = plotX + plotW + 6;

      let boxY = y - boxH/2;
      if (i === 0) { boxY = y; }
      if (i === ticks) { boxY = y - boxH; }

      const rect = document.createElementNS(svg.namespaceURI,'rect');
      rect.setAttribute('x', boxX); rect.setAttribute('y', boxY);
      rect.setAttribute('width', boxW); rect.setAttribute('height', boxH);
      rect.setAttribute('rx', 4); rect.setAttribute('ry', 4);
      rect.setAttribute('class','axis-price-box');
      const t = document.createElementNS(svg.namespaceURI,'text');
      t.textContent = txt;
      t.setAttribute('class','axis-price-text');
      t.setAttribute('x', boxX + paddingX);
      t.setAttribute('y', boxY + boxH / 2);
      t.setAttribute('dominant-baseline', 'middle');
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
        const showDate = (lastDate !== dateStr);
        lastDate = dateStr;
        const t1 = document.createElementNS(svg.namespaceURI,'text');
        t1.textContent = timeStr;
        t1.setAttribute('class','axis-time');

        const isLastTick = (i + step >= n);
        if (i === 0) {
            t1.setAttribute('text-anchor', 'start');
            t1.setAttribute('x', x);
        } else if (isLastTick) {
            t1.setAttribute('text-anchor', 'end');
            t1.setAttribute('x', x);
        } else {
            t1.setAttribute('text-anchor', 'middle');
            t1.setAttribute('x', x);
        }
        t1.setAttribute('y', plotY + plotH + 14);
        timeGroup.appendChild(t1);

        if (showDate){
          const t2 = document.createElementNS(svg.namespaceURI,'text');
          t2.textContent = dateStr;
          t2.setAttribute('class','axis-time');
          if (i === 0) {
              t2.setAttribute('text-anchor', 'start');
              t2.setAttribute('x', x);
          } else if (isLastTick) {
              t2.setAttribute('text-anchor', 'end');
              t2.setAttribute('x', x);
          } else {
              t2.setAttribute('text-anchor', 'middle');
              t2.setAttribute('x', x);
          }
          t2.setAttribute('y', plotY + plotH + 26);
          timeGroup.appendChild(t2);
        }
      }
    }
    svg.appendChild(timeGroup);
    window.__postReady = false;
    requestAnimationFrame(() => requestAnimationFrame(() => { window.__postReady = true; }));
  }

  window.addEventListener('resize', build);
  window.addEventListener('DOMContentLoaded', build);
})();
</script>
</body>
</html>"""


class PostImageGenerator(QWidget):
    def __init__(self, symbol, data, sl, tp1, tp2, entry_price, rr_text):
        super().__init__()
        self.setFixedSize(1080, 1080)
        self.view = QWebEngineView(self)
        self.view.setGeometry(0, 0, 1080, 1080)

        compact = [
            {'open': float(c['open']), 'high': float(c['high']), 'low': float(c['low']), 'close': float(c['close']),
             'time': int(c.get('timestamp', 0))} for c in data]
        levels = {'stop_loss': sl, 'tp1': tp1, 'tp2': tp2, 'entry': entry_price}

        if entry_price < tp1:
            position_text = "LONG"
            position_class = "long-text"
        else:
            position_text = "SHORT"
            position_class = "short-text"

        html = HTML_TEMPLATE.replace('__DATA__', json.dumps(compact)) \
            .replace('__LEVELS__', json.dumps(levels)) \
            .replace('__ZOOM__', 'true') \
            .replace('__SYMBOL__', symbol.replace("USDT", "")) \
            .replace('__POSITION_CLASS__', position_class) \
            .replace('__POSITION__', position_text) \
            .replace('__ENTRY__', str(round(entry_price))) \
            .replace('__TP1__', str(round(tp1))) \
            .replace('__TP2__', str(round(tp2))) \
            .replace('__SL__', str(round(sl))) \
            .replace('__RR__', rr_text)

        self.view.setHtml(html)


def generate_post_image(symbol, data, sl, tp1, tp2, entry_price, rr_text):
    generator = PostImageGenerator(symbol, data, sl, tp1, tp2, entry_price, rr_text)
    loop = QEventLoop()
    poll = QTimer(generator)
    deadline = QTimer(generator)
    deadline.setSingleShot(True)
    result = []
    state = {'active': True, 'pending': False}

    def capture_if_ready(bounds):
        state['pending'] = False
        if not state['active'] or not bounds:
            return
        # Снимаем сам WebEngineView после отрисовки SVG, а не его родителя.
        pixmap = generator.view.grab()
        image = pixmap.toImage()
        scale = pixmap.devicePixelRatio()
        left = max(0, int(bounds['x'] * scale))
        top = max(0, int(bounds['y'] * scale))
        right = min(image.width(), int((bounds['x'] + bounds['width']) * scale))
        bottom = min(image.height(), int((bounds['y'] + bounds['height']) * scale))
        # Шапка и подвал могут уже быть видны, когда свечи ещё не нарисованы.
        # Проверяем красные/зелёные пиксели только внутри области графика.
        candle_pixels = 0
        for y in range(top, bottom, 2):
            for x in range(left, right, 2):
                color = image.pixelColor(x, y)
                if (color.green() > 100 and color.green() > color.red() * 1.8 and color.green() > color.blue() * 1.8) or \
                   (color.red() > 150 and color.green() < 90 and color.blue() < 90):
                    candle_pixels += 1
            if candle_pixels >= 5:
                break
        if not pixmap.isNull() and candle_pixels >= 5:
            result.append(pixmap)
            state['active'] = False
            loop.quit()

    def check_ready():
        if state['active'] and not state['pending']:
            state['pending'] = True
            generator.view.page().runJavaScript('''(() => {
                const svg = document.querySelector('#wrap > svg');
                if (!window.__postReady || !svg || !svg.querySelector('rect.bull, rect.bear')) return null;
                const r = svg.getBoundingClientRect();
                return {x:r.x, y:r.y, width:r.width, height:r.height};
            })()''', capture_if_ready)

    poll.timeout.connect(check_ready)
    deadline.timeout.connect(loop.quit)
    try:
        generator.show()
        poll.start(100)
        deadline.start(15000)
        loop.exec_()
        if not result:
            raise RuntimeError('Не удалось отрисовать изображение поста за 15 секунд. Попробуйте ещё раз.')
        return result[0]
    finally:
        state['active'] = False
        poll.stop()
        deadline.stop()
        generator.close()
        generator.deleteLater()
# --- КОНЕЦ ИЗМЕНЕНИЙ ---
