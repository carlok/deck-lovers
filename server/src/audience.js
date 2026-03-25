(function(){'use strict';

var HOST = location.hostname;
var PORT = location.port || '8000';
var WS_SCHEME = location.protocol === 'https:' ? 'wss' : 'ws'; // C4: match page scheme
var WS_URL = WS_SCHEME + '://' + HOST + ':' + PORT + '/ws';

var frame    = document.getElementById('slide-frame');
var fab      = document.getElementById('like-fab');
var toast    = document.getElementById('toast');
var badge    = document.getElementById('badge');
var loading  = document.getElementById('loading');
var reconnEl = document.getElementById('reconnect');
var projWarn = document.getElementById('proj-warn');
var btnFs    = document.getElementById('btn-fs');

var myName      = '';
var currentIdx  = 0;
var ws          = null;
var reconnDelay = 1000;
var toastTimer  = null;

// ── Fullscreen toggle ─────────────────────────────────────
function isFullscreen(){
  return !!(document.fullscreenElement || document.webkitFullscreenElement);
}
function updateFsIcon(){
  btnFs.textContent = isFullscreen() ? '✕' : '⛶';
}
function toggleFullscreen(){
  if(isFullscreen()){
    var fn = document.exitFullscreen || document.webkitExitFullscreen;
    if(fn) fn.call(document);
  } else {
    var el = document.documentElement;
    var fn = el.requestFullscreen || el.webkitRequestFullscreen;
    if(fn) fn.call(el);
    if(screen.orientation && screen.orientation.lock){
      screen.orientation.lock('landscape').catch(function(){});
    }
  }
}
btnFs.addEventListener('click', toggleFullscreen);

// PDF: open slides in print mode in a new tab
document.getElementById('btn-pdf').addEventListener('click', function(){
  window.open(location.protocol + '//' + HOST + ':' + PORT + '/#print', '_blank');
});
document.addEventListener('fullscreenchange', updateFsIcon);
document.addEventListener('webkitfullscreenchange', updateFsIcon);

// ── Scale iframe to fill viewport ────────────────────────
function scaleFrame(){
  var vw = window.innerWidth;
  var vh = window.innerHeight;
  var scale = Math.min(vw / 1280, vh / 720);
  var tx = (vw - 1280 * scale) / 2;
  var ty = (vh - 720  * scale) / 2;
  frame.style.transform = 'translate('+tx+'px,'+ty+'px) scale('+scale+')';
}

// iOS reports stale dimensions immediately on orientation change — wait one frame
var resizeTimer = null;
function scheduleScale(){
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(scaleFrame, 80);
}
window.addEventListener('resize', scheduleScale);
if(screen.orientation) screen.orientation.addEventListener('change', scheduleScale);
scaleFrame();

// Show iframe once it loads (FAB only shown after name assigned — I6)
frame.addEventListener('load', function(){
  loading.hidden = true;
  frame.hidden   = false;
});

// ── Drive iframe slide ────────────────────────────────────
function goToSlide(n){
  currentIdx = n;
  frame.contentWindow.postMessage({type:'go_to_slide', index:n}, location.origin); // C5 target
}

// ── Like button ───────────────────────────────────────────
fab.addEventListener('click', function(){
  if(!ws || ws.readyState !== WebSocket.OPEN || !myName) return;
  ws.send(JSON.stringify({type:'like', user:myName, slide:currentIdx}));
  fab.classList.remove('pop');
  void fab.offsetWidth;
  fab.classList.add('pop');
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ toast.classList.remove('show'); }, 1500);
});

// ── WebSocket (audience role) ─────────────────────────────
function connect(){
  ws = new WebSocket(WS_URL);

  ws.onopen = function(){
    reconnDelay = 1000;
    reconnEl.hidden = true;
    // Check projector status immediately
    fetch('/health').then(function(r){return r.json();}).then(function(d){
      projWarn.classList.toggle('show', !d.projector_connected);
    }).catch(function(){});
  };

  ws.onmessage = function(e){
    var msg; try{ msg = JSON.parse(e.data); } catch(x){ return; }

    if(msg.type === 'assigned_name'){
      myName = msg.name;
      badge.textContent = '👤 ' + myName;
      badge.hidden = false;
      requestAnimationFrame(function(){  // M4: rAF more reliable than setTimeout(50)
        requestAnimationFrame(function(){ badge.style.opacity = '1'; });
      });
      fab.hidden = false;               // I6: show FAB only once name is confirmed
    }
    else if(msg.type === 'slide_update'){
      goToSlide(msg.index != null ? msg.index : 0);  // I8: 0 is valid, don't coerce
    }
    else if(msg.type === 'projector_status'){
      projWarn.classList.toggle('show', !msg.connected);
    }
  };

  ws.onclose = function(){
    if(ws !== this) return;            // I7: stale socket — a newer one took over
    ws = null;
    reconnEl.hidden = false;
    reconnDelay = Math.min(reconnDelay * 2, 30000);
    setTimeout(connect, reconnDelay);
  };

  ws.onerror = function(){ this.close(); }; // I7: close self, not the global ws ref
}

// Listen for bullet-tap likes coming from the slide iframe
window.addEventListener('message', function(e){
  if(e.origin !== location.origin) return;  // C5: reject cross-origin messages
  if(!e.data || e.data.type !== 'bullet_like') return;
  if(!ws || ws.readyState !== WebSocket.OPEN || !myName) return;
  ws.send(JSON.stringify({type:'like', user:myName, slide:currentIdx}));
  fab.classList.remove('pop');
  void fab.offsetWidth;
  fab.classList.add('pop');
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ toast.classList.remove('show'); }, 1500);
});

connect();
})();
