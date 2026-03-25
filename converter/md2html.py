#!/usr/bin/env python3
"""
md2html.py — Convert slides.md to a beautiful standalone HTML slide deck.

Slide separator : ---  (on its own line, no Reveal.js required)
YouTube embed   : !youtube[Title](url-or-video-id)
Checklists      : - [ ] open   /  - [x] done
"""

import argparse
import html as _esc
import os
import re
import sys

try:
    import markdown
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.tables import TableExtension
except ImportError:
    print("ERROR: pip install markdown", file=sys.stderr)
    sys.exit(1)

SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
PORT        = os.getenv("PORT", "8000")
WS_SCHEME   = os.getenv("WS_SCHEME", "ws")   # set to "wss" behind TLS

# Behind a reverse proxy the port is handled by the proxy — omit it from URLs
_port       = f":{PORT}" if WS_SCHEME == "ws" else ""
HTTP_SCHEME = "https" if WS_SCHEME == "wss" else "http"
WS_URL      = f"{WS_SCHEME}://{SERVER_HOST}{_port}/ws"
AUDIENCE_URL = f"{HTTP_SCHEME}://{SERVER_HOST}{_port}/audience"

# ── YouTube ───────────────────────────────────────────────────────────────────

def _yt_id(url_or_id: str) -> str:
    m = re.search(r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})', url_or_id)
    return m.group(1) if m else url_or_id.strip()

def _yt_block(title: str, url: str) -> str:
    vid   = _yt_id(url)
    label = _esc.escape(title or "Video")
    return (
        f'<div class="yt-wrap">'
        f'<iframe src="https://www.youtube.com/embed/{vid}" '
        f'title="{label}" allowfullscreen loading="lazy"></iframe>'
        f'</div>'
    )

# ── Markdown helpers ──────────────────────────────────────────────────────────

_MD_EXTS = [
    FencedCodeExtension(),
    TableExtension(),
    "attr_list",
]

def _preprocess(text: str) -> str:
    """Expand !youtube[...](url) and bare YouTube URLs before markdown parse."""
    # !youtube[Title](url)  ← primary syntax
    text = re.sub(
        r'!youtube\[([^\]]*)\]\(([^)]+)\)',
        lambda m: _yt_block(m.group(1), m.group(2)),
        text,
    )
    # Bare YouTube URL on its own paragraph line
    text = re.sub(
        r'^(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w\-&=?%]+)\s*$',
        lambda m: _yt_block("", m.group(1)),
        text,
        flags=re.MULTILINE,
    )
    return text

def _postprocess(html: str) -> str:
    """Style task-list items after markdown parse."""
    html = re.sub(
        r'<li>\[ \] ',
        '<li class="task-item task-open"><span class="cb cb-open"></span> ',
        html,
    )
    html = re.sub(
        r'<li>\[x\] ',
        '<li class="task-item task-done"><span class="cb cb-done">✓</span> ',
        html,
    )
    return html

def _md(text: str) -> str:
    text = _preprocess(text)
    result = markdown.markdown(text, extensions=_MD_EXTS)
    return _postprocess(result)

# ── Slide parsing ─────────────────────────────────────────────────────────────

def parse_slides(raw: str) -> list[str]:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    # Strip optional YAML front matter
    raw = re.sub(r'^---\n.*?\n---\n', '', raw, count=1, flags=re.DOTALL)
    parts = re.split(r'\n[ \t]*---[ \t]*\n', raw)
    return [p.strip() for p in parts if p.strip()]

def _is_title(md_text: str) -> bool:
    return bool(re.match(r'^#\s', md_text.strip()))

def _slide_title(md_text: str) -> str:
    m = re.search(r'^#{1,3}\s+(.+)$', md_text.strip(), re.MULTILINE)
    return m.group(1).strip() if m else ''

# ── Full HTML document ────────────────────────────────────────────────────────

_CSS = """\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --accent:#E94560;--success:#2ECC71;--warning:#F39C12;
  --dark:#1A2333;--text:#2C3E50;--muted:#7F8C8D;
  --bg:#FAFAF8;--bg-cream:#FFF9F0;--border:#E8E4DF;--link:#3498DB;
  --mono:"SF Mono","Fira Code","Consolas",monospace;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif;
  --ease:cubic-bezier(.4,0,.2,1);--dur:360ms;
}
html,body{height:100%;overflow:hidden;background:var(--bg);font-family:var(--sans);
  color:var(--text);-webkit-font-smoothing:antialiased;}

/* Progress */
#progress{position:fixed;top:0;left:0;height:3px;width:0%;background:var(--accent);
  z-index:300;transition:width var(--dur) var(--ease);border-radius:0 2px 2px 0;}

/* Deck */
#deck{position:fixed;inset:0;}
.slide{position:absolute;inset:0;display:flex;flex-direction:column;
  justify-content:center;padding:2vh 5vw 7vh;
  opacity:0;transform:translateX(48px);pointer-events:none;
  transition:opacity var(--dur) var(--ease),transform var(--dur) var(--ease);
  overflow:hidden;}
.slide.active{opacity:1;transform:translateX(0);pointer-events:auto;z-index:1;}
.slide.prev{opacity:0;transform:translateX(-48px);}
.slide.title{align-items:center;text-align:center;
  background:linear-gradient(160deg,#fff 0%,#FFF0F3 60%,#FFF8EC 100%);}

/* Headings */
.slide h1{font-size:clamp(2.8rem,6.5vw,5.5rem);font-weight:800;line-height:1.06;
  color:var(--dark);letter-spacing:-.03em;margin-bottom:.35em;}
.slide.title h1::after{content:'';display:block;height:4px;width:56px;
  background:var(--accent);border-radius:2px;margin:.35em auto 0;}
.slide h2{font-size:clamp(1.8rem,3.8vw,3rem);font-weight:700;color:var(--dark);
  margin-bottom:.45em;padding-bottom:.22em;border-bottom:3px solid var(--accent);
  align-self:stretch;}
.slide h3{font-size:clamp(1.1rem,2.2vw,1.7rem);font-weight:600;color:var(--accent);
  margin:.45em 0 .2em;}

/* Body text */
.slide p{font-size:clamp(1.15rem,2.2vw,1.65rem);line-height:1.6;margin-bottom:.5em;}
.slide.title p{font-size:clamp(1.2rem,2.4vw,1.8rem);color:var(--muted);}
.slide strong{color:var(--accent);font-weight:700;}
.slide em{font-style:italic;color:var(--muted);}
.slide a{color:var(--link);text-decoration:none;border-bottom:1px solid rgba(52,152,219,.3);
  transition:color .15s,border-color .15s;}
.slide a:hover{color:var(--accent);border-color:var(--accent);}

/* Lists */
.slide ul,.slide ol{padding-left:1.6em;margin-bottom:.5em;}
.slide li{font-size:clamp(1.05rem,2vw,1.5rem);line-height:1.6;margin-bottom:.28em;}
.slide ul li::marker{color:var(--accent);font-size:1.1em;}
.slide ol li::marker{color:var(--accent);font-weight:700;}

/* Task list */
li.task-item{list-style:none;margin-left:-1.6em;padding-left:.3em;}
.cb{display:inline-flex;align-items:center;justify-content:center;
  width:1.25em;height:1.25em;border-radius:4px;margin-right:.45em;vertical-align:middle;}
.cb-open{border:2px solid var(--border);}
.cb-done{background:var(--success);color:#fff;font-size:.72em;font-weight:700;}
li.task-done>span+*,li.task-done>span~*{text-decoration:line-through;color:var(--muted);}

/* Blockquote */
.slide blockquote{border-left:4px solid var(--accent);padding:.6em 1.2em;
  background:var(--bg-cream);border-radius:0 8px 8px 0;margin:.5em 0;}
.slide blockquote p{font-style:italic;color:var(--muted);margin:0;}

/* Code */
.slide :not(pre)>code{font-family:var(--mono);font-size:.87em;background:var(--bg-cream);
  padding:.14em .38em;border-radius:4px;border:1px solid var(--border);color:var(--accent);}
.slide pre{background:#1A2333;border-radius:10px;padding:1em 1.4em;overflow-x:auto;
  margin:.45em 0;box-shadow:0 4px 20px rgba(0,0,0,.14);}
.slide pre code{font-family:var(--mono);font-size:clamp(.85rem,1.5vw,1.1rem);
  color:#CBD5E1;line-height:1.6;background:none;border:none;padding:0;}
/* highlight.js — prevent theme overriding our pre background */
.slide pre code.hljs{background:none!important;padding:0!important;}

/* Graphviz */
.dot-diagram{display:flex;justify-content:center;margin:.4em 0;}
.dot-diagram svg{max-width:100%;max-height:62vh;height:auto;width:auto;}

/* Tables */
.slide table{border-collapse:collapse;width:100%;margin:.4em 0;
  font-size:clamp(1rem,1.7vw,1.3rem);border-radius:10px;overflow:hidden;
  box-shadow:0 2px 12px rgba(0,0,0,.07);}
.slide thead th{background:var(--dark);color:#fff;padding:.55em .9em;text-align:left;
  font-weight:600;letter-spacing:.03em;}
.slide tbody tr:nth-child(odd){background:#fff;}
.slide tbody tr:nth-child(even){background:#F7F5F2;}
.slide tbody tr:hover{background:#FFF0F2;}
.slide tbody td{padding:.5em .9em;border-bottom:1px solid var(--border);vertical-align:top;}

/* Icon link grid — contact / links slide */
.icon-links{display:flex;justify-content:center;align-items:flex-start;
  gap:clamp(1.5rem,4vw,4rem);flex-wrap:wrap;margin-top:1.2em;}
.icon-link{display:flex;flex-direction:column;align-items:center;gap:.5em;
  color:var(--dark);text-decoration:none;border:none;
  transition:color .15s,transform .18s;}
.icon-link:hover{color:var(--accent);transform:translateY(-4px);border:none;}
.icon-link i{font-size:clamp(2.4rem,5vw,4rem);}
.icon-link span{font-size:clamp(.75rem,1.3vw,.95rem);font-weight:600;
  color:var(--muted);text-align:center;}
.icon-qr img{border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.13);
  width:clamp(120px,14vw,180px);height:auto;}

/* YouTube */
.yt-wrap{position:relative;width:100%;max-width:min(960px,88vw);aspect-ratio:16/9;
  border-radius:14px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.18);margin:.4em 0;}
.yt-wrap iframe{position:absolute;inset:0;width:100%;height:100%;border:none;}

/* Stats slide */
#stats-slide h2{margin-bottom:.9em;}
.stats-grid{width:100%;display:flex;flex-direction:column;gap:8px;}
.stats-row{display:flex;align-items:center;gap:12px;font-size:clamp(.8rem,1.3vw,.94rem);}
.stats-label{width:190px;text-align:right;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;flex-shrink:0;color:var(--text);}
.stats-bar-bg{flex:1;background:#EEE;border-radius:6px;height:26px;overflow:hidden;}
.stats-bar{height:100%;width:0%;background:linear-gradient(90deg,var(--accent),#F39C12);
  border-radius:6px;transition:width .75s var(--ease);display:flex;align-items:center;
  padding-left:8px;color:#fff;font-weight:700;font-size:.82em;white-space:nowrap;box-sizing:border-box;}

/* Nav */
#nav{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:200;
  display:flex;align-items:center;gap:12px;
  background:rgba(26,35,51,.88);backdrop-filter:blur(14px);
  padding:8px 20px;border-radius:50px;box-shadow:0 4px 24px rgba(0,0,0,.22);user-select:none;}
#nav button{background:none;border:none;color:rgba(255,255,255,.6);font-size:1.1rem;
  cursor:pointer;padding:4px 10px;border-radius:8px;transition:color .14s,background .14s;line-height:1;}
#nav button:hover:not(:disabled){color:#fff;background:rgba(255,255,255,.12);}
#nav button:disabled{color:rgba(255,255,255,.2);cursor:default;}
#counter{color:rgba(255,255,255,.9);font-size:.8rem;font-weight:600;
  letter-spacing:.08em;min-width:4.5em;text-align:center;}

/* QR */
#qr-overlay{position:fixed;bottom:24px;left:24px;z-index:200;
  background:rgba(26,35,51,.9);padding:10px 10px 6px;border-radius:14px;
  box-shadow:0 6px 24px rgba(0,0,0,.24);backdrop-filter:blur(10px);
  text-align:center;cursor:pointer;transition:transform .2s var(--ease),box-shadow .2s;}
#qr-overlay:hover{transform:scale(1.06);box-shadow:0 10px 32px rgba(0,0,0,.3);}
#qr-overlay canvas,#qr-overlay img{display:block;border-radius:6px;}
#qr-label{color:rgba(255,255,255,.45);font-size:.58rem;text-transform:uppercase;
  letter-spacing:.12em;margin-top:5px;}

/* Like sidebar */
#like-sidebar{position:fixed;right:0;top:50%;transform:translateY(-50%);z-index:200;
  display:flex;align-items:center;}
#sidebar-toggle{background:var(--accent);color:#fff;border:none;border-radius:10px 0 0 10px;
  width:38px;height:90px;cursor:pointer;font-size:1rem;display:flex;align-items:center;
  justify-content:center;box-shadow:-3px 0 16px rgba(233,69,96,.35);
  transition:background .14s;flex-direction:column;gap:4px;}
#sidebar-toggle:hover{background:#C73E54;}
#sidebar-content{background:rgba(26,35,51,.94);backdrop-filter:blur(14px);
  border-radius:10px 0 0 10px;padding:16px 14px;width:168px;overflow:hidden;
  transition:width .3s var(--ease),padding .3s var(--ease),opacity .3s var(--ease);}
#sidebar-content.hidden{width:0;padding:0;opacity:0;pointer-events:none;}
#like-count{font-size:3.2rem;font-weight:800;color:var(--accent);text-align:center;
  line-height:1;font-variant-numeric:tabular-nums;}
#like-count.pulse{animation:count-pulse .35s var(--ease);}
@keyframes count-pulse{0%{transform:scale(1)}45%{transform:scale(1.38)}100%{transform:scale(1)}}
#like-sub{color:rgba(255,255,255,.35);font-size:.65rem;text-align:center;
  margin-bottom:10px;letter-spacing:.06em;}
#like-feed{display:flex;flex-direction:column;gap:4px;overflow:hidden;max-height:140px;}
.like-entry{color:rgba(255,255,255,.85);font-size:.68rem;padding:3px 8px;border-radius:20px;
  background:rgba(233,69,96,.22);animation:slide-in-r .28s var(--ease);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
@keyframes slide-in-r{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* Bullet like flash (mirror mode) */
@keyframes li-like{
  0%  {background:rgba(233,69,96,.22);transform:translateX(5px);}
  100%{background:transparent;transform:translateX(0);}
}
li.liked-flash{animation:li-like .45s ease-out forwards;border-radius:6px;}

/* Hearts */
.heart{position:fixed;font-size:1.8rem;pointer-events:none;z-index:9999;
  animation:float-up 2.4s ease-out forwards;will-change:transform,opacity;}
@keyframes float-up{
  0%  {opacity:.9;transform:translateY(0)    scale(.9) translateX(0);}
  25% {opacity:1; transform:translateY(-20%) scale(1.1) translateX(8px);}
  100%{opacity:0; transform:translateY(-90vh) scale(.6) translateX(-6px);}
}
@media(prefers-reduced-motion:reduce){.heart{display:none!important}}

/* Reconnect */
#reconnect{position:fixed;top:12px;left:50%;transform:translateX(-50%);
  background:var(--warning);color:#fff;padding:5px 18px;border-radius:20px;
  font-size:.78rem;font-weight:600;z-index:400;display:flex;align-items:center;gap:6px;
  animation:pulse-warn 1.6s ease-in-out infinite;}
#reconnect[hidden]{display:none!important;}
@keyframes pulse-warn{0%,100%{opacity:1}50%{opacity:.55}}

@media(max-width:640px){
  .slide{padding:2vh 4vw 10vh;}
  #qr-overlay,#like-sidebar{display:none;}
}

@media print{
  #nav,#qr-overlay,#like-sidebar,#progress,#reconnect{display:none!important;}
  html,body{height:auto;overflow:visible;background:#fff;}
  #deck{position:static;height:auto;}
  .slide{
    position:relative!important;opacity:1!important;transform:none!important;
    pointer-events:auto!important;display:flex!important;
    height:100vh;page-break-after:always;break-after:page;
  }
}
"""

# JS uses __TOKENS__ replaced in Python (avoids escaping all JS { } as {{ }})
_JS_TEMPLATE = """\
(function(){
'use strict';
var WS_URL='__WS_URL__';
var AUDIENCE_URL='__AUDIENCE_URL__';
var TOTAL=__TOTAL__;
var MIRROR=location.hash==='#mirror';
var PRINT=location.hash==='#print';
var current=0;
var ws=null;
var reconnectDelay=1000;
var likesData={};

// Slides
var slides=Array.from(document.querySelectorAll('.slide'));
var counter=document.getElementById('counter');
var progress=document.getElementById('progress');
var btnPrev=document.getElementById('btn-prev');
var btnNext=document.getElementById('btn-next');

function showSlide(n){
  var prev=current;
  current=Math.max(0,Math.min(n,TOTAL-1));
  slides.forEach(function(s,i){
    s.classList.remove('active','prev');
    if(i===current)s.classList.add('active');
    else if(i<current)s.classList.add('prev');
  });
  counter.textContent=(current+1)+' / '+TOTAL;
  progress.style.width=(TOTAL>1?(current/(TOTAL-1)*100):100)+'%';
  btnPrev.disabled=current===0;
  btnNext.disabled=current===TOTAL-1;
  updateSidebar(current);
  if(!MIRROR&&ws&&ws.readyState===WebSocket.OPEN){
    ws.send(JSON.stringify({type:'slide_change',index:current}));
  }
  if(slides[current]&&slides[current].id==='stats-slide') renderStats();
}

btnPrev.addEventListener('click',function(){showSlide(current-1);});
btnNext.addEventListener('click',function(){showSlide(current+1);});

document.addEventListener('keydown',function(e){
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();showSlide(current+1);}
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();showSlide(current-1);}
});

var touchX=0;
document.addEventListener('touchstart',function(e){touchX=e.changedTouches[0].clientX;},{passive:true});
document.addEventListener('touchend',function(e){
  var dx=e.changedTouches[0].clientX-touchX;
  if(Math.abs(dx)>50){dx<0?showSlide(current+1):showSlide(current-1);}
},{passive:true});

// QR
new QRCode(document.getElementById('qrcode'),{
  text:AUDIENCE_URL,width:128,height:128,
  colorDark:'#ffffff',colorLight:'rgba(0,0,0,0)',
  correctLevel:QRCode.CorrectLevel.M
});

// Sidebar
var sidebarContent=document.getElementById('sidebar-content');
document.getElementById('sidebar-toggle').addEventListener('click',function(){
  sidebarContent.classList.toggle('hidden');
});

function updateSidebar(idx){
  var el=document.getElementById('like-count');
  if(el)el.textContent=likesData[idx]||0;
  var feed=document.getElementById('like-feed');
  if(feed)feed.innerHTML='';
}

// Hearts
var pendingHearts=0,heartTimer=null;
function spawnHeart(){
  var h=document.createElement('div');
  h.className='heart';h.textContent='\u2764\uFE0F';
  h.style.left=(10+Math.random()*80)+'%';
  h.style.bottom='80px';
  document.body.appendChild(h);
  h.addEventListener('animationend',function(){h.remove();});
}
function scheduleHearts(n){
  pendingHearts+=n;
  if(heartTimer)return;
  var burst=0;
  heartTimer=setInterval(function(){
    if(pendingHearts<=0||burst>=5){clearInterval(heartTimer);heartTimer=null;pendingHearts=0;burst=0;return;}
    spawnHeart();pendingHearts--;burst++;
  },200);
}

// Stats
function renderStats(){
  var chart=document.getElementById('stats-chart');
  if(!chart)return;
  var rows=[];
  slides.forEach(function(s,i){
    if(s.id==='stats-slide')return;
    var h=s.querySelector('h1,h2');
    rows.push({title:h?h.textContent.trim():'Slide '+(i+1),idx:i,count:likesData[i]||0});
  });
  rows.sort(function(a,b){return b.count-a.count;});
  var maxC=rows[0]&&rows[0].count>0?rows[0].count:1;
  chart.innerHTML='';
  rows.forEach(function(r){
    var pct=Math.round(r.count/maxC*100);
    var row=document.createElement('div');
    row.className='stats-row';
    row.innerHTML='<span class="stats-label" title="'+r.title+'">'+r.title+'</span>'
      +'<div class="stats-bar-bg"><div class="stats-bar" data-pct="'+pct+'">'
      +(r.count>0?r.count:'')+'</div></div>';
    chart.appendChild(row);
  });
  requestAnimationFrame(function(){
    chart.querySelectorAll('.stats-bar').forEach(function(b){b.style.width=b.dataset.pct+'%';});
  });
}

// Like update handler
function onLikeUpdate(msg){
  likesData[msg.slide]=msg.count;
  scheduleHearts(1);
  if(msg.slide===current){
    var el=document.getElementById('like-count');
    if(el){el.textContent=msg.count;el.classList.remove('pulse');void el.offsetWidth;el.classList.add('pulse');}
    var feed=document.getElementById('like-feed');
    if(feed&&msg.recent&&msg.recent.length){
      var name=msg.recent[msg.recent.length-1];
      var entry=document.createElement('div');
      entry.className='like-entry';
      entry.textContent='\u2665 '+name;
      feed.insertBefore(entry,feed.firstChild);
      while(feed.children.length>5)feed.removeChild(feed.lastChild);
    }
  }
  if(slides[current]&&slides[current].id==='stats-slide') renderStats();
}

// WebSocket
var reconnectEl=document.getElementById('reconnect');
function connect(){
  ws=new WebSocket(WS_URL);
  ws.onopen=function(){
    reconnectDelay=1000;
    if(reconnectEl)reconnectEl.hidden=true;
    ws.send(JSON.stringify({type:'register_projector'}));
    var meta=slides.filter(function(s){return s.id!=='stats-slide';}).map(function(s){
      return{
        title:(s.querySelector('h1,h2')||{}).textContent||'',
        summary:((s.querySelector('p')||{}).textContent||'').slice(0,120)
      };
    });
    ws.send(JSON.stringify({type:'slides_meta',slides:meta}));
  };
  ws.onmessage=function(e){
    var msg;try{msg=JSON.parse(e.data);}catch(x){return;}
    if(msg.type==='like_update')onLikeUpdate(msg);
  };
  ws.onclose=function(){
    if(reconnectEl)reconnectEl.hidden=false;
    setTimeout(connect,reconnectDelay);
    reconnectDelay=Math.min(reconnectDelay*2,30000);
  };
  ws.onerror=function(){ws.close();};
}

if(PRINT){
  // Print mode: show all slides stacked, trigger browser print dialog
  ['nav','qr-overlay','like-sidebar','progress','reconnect'].forEach(function(id){
    var el=document.getElementById(id);
    if(el)el.style.display='none';
  });
  var deck=document.getElementById('deck');
  deck.style.cssText='position:static;height:auto;';
  slides.forEach(function(s){
    s.style.cssText='position:relative;opacity:1;transform:none;pointer-events:auto;display:flex;height:100vh;page-break-after:always;break-after:page;';
  });
  // Wait for fonts, images and MathJax/viz.js to settle before printing
  window.addEventListener('load',function(){
    setTimeout(function(){ window.print(); },1200);
  });
} else if(MIRROR){
  // Mirror mode: hide all projector chrome, receive postMessage from parent
  ['nav','qr-overlay','like-sidebar','progress','reconnect'].forEach(function(id){
    var el=document.getElementById(id);
    if(el)el.style.display='none';
  });
  // Attach tap-to-like handlers to list items on the active slide
  function attachLikeHandlers(){
    var activeSlide=slides[current];
    if(!activeSlide) return;
    activeSlide.querySelectorAll('li').forEach(function(li){
      if(li.dataset.likeAttached) return;
      li.dataset.likeAttached='1';
      li.style.cursor='pointer';
      var lastTap=0;
      li.addEventListener('click',function(){
        var now=Date.now();
        if(now-lastTap<600) return; // debounce double-taps
        lastTap=now;
        window.parent.postMessage({type:'bullet_like'},'*');
        li.classList.add('liked-flash');
        setTimeout(function(){li.classList.remove('liked-flash');},450);
      });
    });
  }
  window.addEventListener('message',function(e){
    if(e.data&&e.data.type==='go_to_slide'){
      showSlide(e.data.index);
      attachLikeHandlers();
    }
  });
  showSlide(0);
  attachLikeHandlers();
} else {
  showSlide(0);
  connect();
}
})();
"""

# ── HTML builder ──────────────────────────────────────────────────────────────

_FA_CDN   = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"
_QR_CDN   = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"
_HLJS_CSS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css"
_HLJS_JS  = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
_MATHJAX  = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"
_VIZ_JS   = "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js"
_VIZ_FULL = "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"

# MathJax config — must appear before the MathJax script loads
_MATHJAX_CONFIG = """\
<script>
window.MathJax = {
  tex: { inlineMath: [['$','$']], displayMath: [['$$','$$']] }
};
</script>"""

# Init scripts — run after hljs/viz.js are loaded synchronously
_INIT_SCRIPTS = """\
<script>
// Syntax highlighting — skip dot blocks (handled by viz.js)
document.querySelectorAll('pre code:not(.language-dot)').forEach(function(el){
  hljs.highlightElement(el);
});
// Graphviz: render dot blocks to SVG
(function(){
  var blocks = document.querySelectorAll('pre code.language-dot');
  if(!blocks.length) return;
  var viz = new Viz();
  blocks.forEach(function(el){
    var dot = el.textContent;
    var pre = el.parentNode;
    viz.renderSVGElement(dot).then(function(svg){
      var wrap = document.createElement('div');
      wrap.className = 'dot-diagram';
      wrap.appendChild(svg);
      pre.parentNode.replaceChild(wrap, pre);
    }).catch(function(err){
      pre.style.color = '#E94560';
      pre.textContent = 'Graphviz error: ' + err;
    });
  });
})();
</script>"""

def build_html(slide_texts: list[str], doc_title: str = "Presentation") -> str:
    total = len(slide_texts) + 1  # +1 for stats slide appended below

    slides_html_parts = []
    for i, raw in enumerate(slide_texts):
        cls   = "title" if _is_title(raw) else "content"
        inner = _md(raw)
        slides_html_parts.append(
            f'  <div class="slide {cls}" data-index="{i}">\n{inner}\n  </div>'
        )

    # Stats slide (always last)
    stats_idx = len(slide_texts)
    slides_html_parts.append(
        f'  <div class="slide content" id="stats-slide" data-index="{stats_idx}">\n'
        f'  <h2>Audience Engagement</h2>\n'
        f'  <div id="stats-chart" class="stats-grid"></div>\n'
        f'  <p style="margin-top:1.2em;font-size:.8em;color:var(--muted)">ranked by likes · updates live</p>\n'
        f'  </div>'
    )

    slides_html = "\n".join(slides_html_parts)

    js = (
        _JS_TEMPLATE
        .replace("__WS_URL__", WS_URL)
        .replace("__AUDIENCE_URL__", AUDIENCE_URL)
        .replace("__TOTAL__", str(total))
    )

    escaped_title = _esc.escape(doc_title)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{escaped_title}</title>
<link rel="stylesheet" href="{_FA_CDN}">
<link rel="stylesheet" href="{_HLJS_CSS}">
<script src="{_QR_CDN}"></script>
{_MATHJAX_CONFIG}
<script async src="{_MATHJAX}"></script>
<style>{_CSS}</style>
</head>
<body>

<div id="progress"></div>

<div id="deck" data-total="{total}">
{slides_html}
</div>

<nav id="nav">
  <button id="btn-prev" aria-label="Previous">&#8592;</button>
  <span id="counter">1 / {total}</span>
  <button id="btn-next" aria-label="Next">&#8594;</button>
</nav>

<div id="qr-overlay" title="Audience companion">
  <div id="qrcode"></div>
  <div id="qr-label">scan to join</div>
</div>

<div id="like-sidebar">
  <button id="sidebar-toggle" aria-label="Toggle likes">&#9829;</button>
  <div id="sidebar-content">
    <div id="like-count">0</div>
    <div id="like-sub">likes this slide</div>
    <div id="like-feed"></div>
  </div>
</div>

<div id="reconnect" hidden>&#9711; Reconnecting&hellip;</div>

<script src="{_HLJS_JS}"></script>
<script src="{_VIZ_JS}"></script>
<script src="{_VIZ_FULL}"></script>
{_INIT_SCRIPTS}
<script>{js}</script>
</body>
</html>"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="Convert slides.md to a standalone HTML slide deck."
    )
    p.add_argument("--input",  required=True, help="Path to slides.md")
    p.add_argument("--output", required=True, help="Path to output slides.html")
    p.add_argument("--title",  default="Presentation", help="Document <title>")
    args = p.parse_args()

    try:
        raw = open(args.input, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"ERROR: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    slide_texts = parse_slides(raw)
    if not slide_texts:
        print("ERROR: no slides found (are they separated by ---?)", file=sys.stderr)
        sys.exit(1)

    print(f"[md2html] {len(slide_texts)} slides + stats slide")
    print(f"[md2html] SERVER_HOST={SERVER_HOST}  WS={WS_URL}")
    print(f"[md2html] Audience: {AUDIENCE_URL}")

    html = build_html(slide_texts, doc_title=args.title)

    open(args.output, "w", encoding="utf-8").write(html)
    print(f"[md2html] → {args.output}")


if __name__ == "__main__":
    main()
