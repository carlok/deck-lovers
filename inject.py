#!/usr/bin/env python3
"""
inject.py — Inject interactive features into pandoc-generated Reveal.js HTML.

Usage:
    python inject.py --input /workspace/slides_base.html --output /workspace/slides.html

Environment:
    SERVER_HOST  Hostname/IP used for audience URL and WebSocket (default: localhost).
                 Set to your LAN IP for in-person use.
"""

import argparse
import os
import sys

from bs4 import BeautifulSoup

SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
WS_URL = f"ws://{SERVER_HOST}:8000/ws"
AUDIENCE_URL = f"http://{SERVER_HOST}:8000/audience"


# ── Font Awesome ─────────────────────────────────────────────────────────────

def inject_fontawesome(soup: BeautifulSoup) -> None:
    """Inject Font Awesome 6 Free CDN link into <head>."""
    link = soup.new_tag(
        "link",
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css",
    )
    head = soup.find("head")
    if head:
        head.append(link)


# ── Style injection ───────────────────────────────────────────────────────────

def inject_head_styles(soup: BeautifulSoup) -> None:
    """Inject CSS for theme override, QR overlay, like sidebar, floating hearts, stats."""
    style = soup.new_tag("style")
    style.string = """
/* ── Theme: light palette matching original Beamer ───────────── */
:root {
    --accent:      #E94560;
    --accent-dark: #C73E54;
    --success:     #2ECC71;
    --warning:     #F39C12;
    --text-dark:   #2C3E50;
    --text-muted:  #7F8C8D;
    --bg-white:    #FFFFFF;
    --bg-cream:    #FFF9F0;
    --bg-orange:   #FFF3E6;
    --link-blue:   #3498DB;
}

/* Slide background */
.reveal-viewport, .reveal, .slides { background: var(--bg-white) !important; }
.reveal .slide-background { background: var(--bg-white) !important; }

/* Body text */
.reveal { color: var(--text-dark) !important; font-family: 'Segoe UI', system-ui, sans-serif; }

/* Headings — accent underline rule */
.reveal h1, .reveal h2 {
    color: var(--text-dark) !important;
    border-bottom: 3px solid var(--accent);
    padding-bottom: 0.2em;
    margin-bottom: 0.6em;
}
.reveal h3, .reveal h4 { color: var(--accent) !important; }

/* Bullets */
.reveal ul > li::marker   { color: var(--accent); }
.reveal ol > li::marker   { color: var(--accent); }

/* Links */
.reveal a { color: var(--link-blue) !important; }

/* Code blocks */
.reveal pre, .reveal code {
    background: var(--bg-cream) !important;
    border: 1px solid #e8ddd0;
    border-radius: 4px;
    color: var(--text-dark) !important;
}

/* Slide number */
.reveal .slide-number { color: var(--text-muted) !important; background: transparent !important; }

/* Colour utility spans from tex_extract (e.g. color-accent) */
.color-accent      { color: var(--accent); }
.color-accentdark  { color: var(--accent-dark); }
.color-success     { color: var(--success); }
.color-successdark { color: #27AE60; }
.color-warning     { color: var(--warning); }
.color-textmuted   { color: var(--text-muted); }
.color-textdark    { color: var(--text-dark); }
.color-bgcream     { color: var(--bg-cream); }
.color-white       { color: #fff; }

/* Block boxes */
.block {
    background: var(--bg-cream);
    border-left: 4px solid var(--accent);
    border-radius: 0 6px 6px 0;
    margin: 0.5em 0;
    padding: 0.5em 1em;
}
.block-title { font-weight: bold; color: var(--accent); margin-bottom: 0.25em; }

/* Columns helper */
.reveal .columns { display: flex; gap: 1.5em; align-items: flex-start; }
.reveal .column  { flex: 1; }

/* ── QR overlay ──────────────────────────────────────────────── */
#qr-overlay {
    position: fixed;
    bottom: 20px;
    left: 16px;
    z-index: 9999;
    background: rgba(44, 62, 80, 0.85);
    padding: 8px;
    border-radius: 6px;
    line-height: 0;
}
#qr-overlay canvas { display: block; }

/* ── Like sidebar ─────────────────────────────────────────────── */
#like-sidebar {
    position: fixed;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    z-index: 9999;
    display: flex;
    align-items: center;
}
#sidebar-toggle {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 6px 0 0 6px;
    padding: 14px 7px;
    cursor: pointer;
    font-size: 14px;
    writing-mode: vertical-rl;
    user-select: none;
}
#sidebar-content {
    background: rgba(44, 62, 80, 0.92);
    border-radius: 6px 0 0 6px;
    padding: 16px 12px;
    min-width: 148px;
    overflow: hidden;
    transition: min-width 0.3s ease, padding 0.3s ease, opacity 0.3s ease;
}
#sidebar-content.collapsed {
    min-width: 0;
    padding: 0;
    opacity: 0;
    pointer-events: none;
}
#like-count {
    font-size: 52px;
    font-weight: bold;
    color: var(--accent);
    text-align: center;
    line-height: 1;
}
#like-count.pulse { animation: count-pulse 0.3s ease; }
@keyframes count-pulse {
    0%   { transform: scale(1);   }
    50%  { transform: scale(1.4); }
    100% { transform: scale(1);   }
}
#like-label {
    color: #aaa;
    font-size: 11px;
    text-align: center;
    margin-bottom: 10px;
    white-space: nowrap;
}
#like-feed {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 160px;
    overflow: hidden;
}
.like-entry {
    color: #f0f0f0;
    font-size: 12px;
    padding: 3px 6px;
    border-radius: 4px;
    background: rgba(233, 69, 96, 0.25);
    animation: slide-in-right 0.3s ease;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
@keyframes slide-in-right {
    from { transform: translateX(120%); opacity: 0; }
    to   { transform: translateX(0);    opacity: 1; }
}

/* ── Floating hearts ──────────────────────────────────────────── */
.floating-heart {
    position: fixed;
    font-size: 28px;
    pointer-events: none;
    z-index: 9998;
    animation: float-up 2s ease-out forwards;
    will-change: transform, opacity;
}
@keyframes float-up {
    0%   { transform: translateY(0)     translateX(0px);  opacity: 1;   }
    40%  { transform: translateY(-40vh) translateX(12px); opacity: 0.9; }
    100% { transform: translateY(-80vh) translateX(-8px); opacity: 0;   }
}
@media (prefers-reduced-motion: reduce) {
    .floating-heart { display: none !important; }
}

/* ── Stats slide ──────────────────────────────────────────────── */
#stats-slide h2 { margin-bottom: 1.2rem; }
.stats-row {
    display: flex;
    align-items: center;
    margin: 7px 0;
    gap: 12px;
    font-size: 0.82em;
}
.stats-label {
    width: 210px;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 0;
    color: var(--text-dark);
}
.stats-bar-wrap {
    flex: 1;
    background: #eee;
    border-radius: 4px;
    height: 24px;
    overflow: hidden;
}
.stats-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--warning));
    border-radius: 4px;
    width: 0%;
    transition: width 0.7s ease;
    display: flex;
    align-items: center;
    padding-left: 8px;
    font-size: 0.85em;
    font-weight: bold;
    color: #fff;
    white-space: nowrap;
    box-sizing: border-box;
}
"""
    head = soup.find("head")
    if head:
        head.append(style)


# ── QR overlay ────────────────────────────────────────────────────────────────

def inject_qr_overlay(soup: BeautifulSoup) -> None:
    """Inject QR code overlay using qrcode.js CDN (bottom-left, always visible)."""
    body = soup.find("body")
    if not body:
        return

    # CDN script tag first
    qrjs = soup.new_tag(
        "script",
        src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js",
    )
    body.insert(0, qrjs)

    # Overlay div (U3 fix: 20px bottom offset + background for AV overscan safety)
    overlay = BeautifulSoup('<div id="qr-overlay"><div id="qrcode"></div></div>', "html.parser")
    body.append(overlay)

    # Init script
    init = soup.new_tag("script")
    init.string = f"""
(function() {{
    new QRCode(document.getElementById('qrcode'), {{
        text: '{AUDIENCE_URL}',
        width: 96,
        height: 96,
        colorDark: '#2C3E50',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M
    }});
}})();
"""
    body.append(init)


# ── Like sidebar ──────────────────────────────────────────────────────────────

def inject_like_sidebar(soup: BeautifulSoup) -> None:
    """Inject collapsible like sidebar on the right edge."""
    sidebar_html = """
<div id="like-sidebar">
  <button id="sidebar-toggle" title="Toggle engagement panel">&#9829;</button>
  <div id="sidebar-content">
    <div id="like-count">0</div>
    <div id="like-label">likes this slide</div>
    <div id="like-feed"></div>
  </div>
</div>
"""
    body = soup.find("body")
    if body:
        body.append(BeautifulSoup(sidebar_html, "html.parser"))


# ── Stats slide ───────────────────────────────────────────────────────────────

def inject_stats_slide(soup: BeautifulSoup) -> None:
    """Append a live-updating engagement stats slide as the last Reveal.js section."""
    slides_container = soup.select_one(".reveal .slides")
    if not slides_container:
        return

    stats_html = """
<section id="stats-slide">
  <h2>Audience Engagement</h2>
  <div id="stats-chart"></div>
  <p style="font-size:0.45em; color:#888; margin-top:1.2rem;">
    Ranked by likes &mdash; updates live
  </p>
</section>
"""
    slides_container.append(BeautifulSoup(stats_html, "html.parser"))


# ── WebSocket client script ───────────────────────────────────────────────────

def inject_websocket_script(soup: BeautifulSoup) -> None:
    """Inject the full projector WebSocket client and interactive logic."""
    script = soup.new_tag("script")
    script.string = f"""
(function() {{
    'use strict';

    // ── State ─────────────────────────────────────────────────
    var ws = null;
    var reconnectDelay = 1000;
    var likesData = {{}};         // slide_idx -> count
    var currentSlideIdx = 0;
    var metaSentOnce = false;

    // ── Heart throttle (C4 fix) ───────────────────────────────
    var pendingHearts = 0;
    var heartTimer = null;
    var HEART_INTERVAL_MS = 200;
    var HEART_MAX_BURST = 5;

    function spawnHeart() {{
        var heart = document.createElement('div');
        heart.className = 'floating-heart';
        heart.textContent = '\\u2764\\uFE0F';
        heart.style.left = (10 + Math.random() * 80) + '%';
        heart.style.bottom = '10%';
        document.body.appendChild(heart);
        heart.addEventListener('animationend', function() {{ heart.remove(); }});
    }}

    function scheduleHearts(count) {{
        pendingHearts += count;
        if (heartTimer) return;
        var burst = 0;
        heartTimer = setInterval(function() {{
            if (pendingHearts <= 0 || burst >= HEART_MAX_BURST) {{
                clearInterval(heartTimer);
                heartTimer = null;
                pendingHearts = 0;
                burst = 0;
                return;
            }}
            spawnHeart();
            pendingHearts--;
            burst++;
        }}, HEART_INTERVAL_MS);
    }}

    // ── Sidebar ───────────────────────────────────────────────
    var sidebarToggle = document.getElementById('sidebar-toggle');
    var sidebarContent = document.getElementById('sidebar-content');
    if (sidebarToggle) {{
        sidebarToggle.addEventListener('click', function() {{
            sidebarContent.classList.toggle('collapsed');
            sidebarToggle.textContent = sidebarContent.classList.contains('collapsed')
                ? '\\u25B6' : '\\u25C0';
        }});
    }}

    function updateSidebar(slideIdx) {{
        var countEl = document.getElementById('like-count');
        var feedEl  = document.getElementById('like-feed');
        if (countEl) countEl.textContent = likesData[slideIdx] || 0;
        if (feedEl)  feedEl.innerHTML = '';
    }}

    function onLikeUpdate(data) {{
        likesData[data.slide] = data.count;
        scheduleHearts(1);

        if (data.slide === currentSlideIdx) {{
            var countEl = document.getElementById('like-count');
            if (countEl) {{
                countEl.textContent = data.count;
                countEl.classList.remove('pulse');
                void countEl.offsetWidth; // force reflow
                countEl.classList.add('pulse');
            }}
            var feedEl = document.getElementById('like-feed');
            if (feedEl && data.recent && data.recent.length) {{
                var name = data.recent[data.recent.length - 1];
                var entry = document.createElement('div');
                entry.className = 'like-entry';
                entry.textContent = '\\u2764 ' + name;
                feedEl.insertBefore(entry, feedEl.firstChild);
                while (feedEl.children.length > 5) {{
                    feedEl.removeChild(feedEl.lastChild);
                }}
            }}
        }}

        // Live-update stats slide if it is currently displayed
        var statsSlide = document.getElementById('stats-slide');
        if (statsSlide && statsSlide.classList.contains('present')) {{
            renderStats();
        }}
    }}

    // ── Stats rendering ───────────────────────────────────────
    function renderStats() {{
        var chart = document.getElementById('stats-chart');
        if (!chart) return;
        var sections = document.querySelectorAll('.reveal .slides > section:not(#stats-slide)');
        var entries = [];
        sections.forEach(function(el, idx) {{
            var titleEl = el.querySelector('h1,h2');
            var title = titleEl ? titleEl.textContent.trim() : ('Slide ' + (idx + 1));
            entries.push({{ title: title, idx: idx, count: likesData[idx] || 0 }});
        }});
        entries.sort(function(a, b) {{ return b.count - a.count; }});
        var maxCount = (entries[0] && entries[0].count > 0) ? entries[0].count : 1;

        chart.innerHTML = '';
        entries.forEach(function(e) {{
            var pct = Math.round((e.count / maxCount) * 100);
            var row = document.createElement('div');
            row.className = 'stats-row';
            row.innerHTML =
                '<span class="stats-label" title="' + e.title + '">' + e.title + '</span>' +
                '<div class="stats-bar-wrap">' +
                  '<div class="stats-bar" data-pct="' + pct + '" style="width:0%">' +
                    (e.count > 0 ? e.count : '') +
                  '</div>' +
                '</div>';
            chart.appendChild(row);
        }});

        // Trigger bar transition on next frame
        requestAnimationFrame(function() {{
            chart.querySelectorAll('.stats-bar').forEach(function(bar) {{
                bar.style.width = bar.dataset.pct + '%';
            }});
        }});
    }}

    // ── Reveal.js integration ─────────────────────────────────
    function attachReveal() {{
        Reveal.on('slidechanged', function(event) {{
            currentSlideIdx = event.indexh;
            updateSidebar(currentSlideIdx);
            if (ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{ type: 'slide_change', index: currentSlideIdx }}));
            }}
            if (event.currentSlide && event.currentSlide.id === 'stats-slide') {{
                renderStats();
            }}
        }});
    }}

    if (typeof Reveal !== 'undefined') {{
        Reveal.on('ready', attachReveal);
    }}

    // ── Metadata extraction ───────────────────────────────────
    function getSlideMeta() {{
        var sections = document.querySelectorAll('.reveal .slides > section:not(#stats-slide)');
        return Array.from(sections).map(function(s) {{
            return {{
                title: ((s.querySelector('h1,h2') || {{}}).textContent || '').trim(),
                summary: ((s.querySelector('p') || {{}}).textContent || '').slice(0, 120)
            }};
        }});
    }}

    // ── WebSocket with reconnect (S1 fix) ─────────────────────
    function connect() {{
        ws = new WebSocket('{WS_URL}');

        ws.onopen = function() {{
            reconnectDelay = 1000;
            ws.send(JSON.stringify({{ type: 'register_projector' }}));
            // Always re-send meta on reconnect so server merges (S2 fix)
            ws.send(JSON.stringify({{ type: 'slides_meta', slides: getSlideMeta() }}));
        }};

        ws.onmessage = function(event) {{
            var msg;
            try {{ msg = JSON.parse(event.data); }} catch(e) {{ return; }}
            if (msg.type === 'like_update') {{
                onLikeUpdate(msg);
            }}
        }};

        ws.onclose = function() {{
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, 30000);
        }};

        ws.onerror = function() {{ ws.close(); }};
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', connect);
    }} else {{
        connect();
    }}
}})();
"""
    body = soup.find("body")
    if body:
        body.append(script)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inject interactive features into pandoc Reveal.js output."
    )
    parser.add_argument("--input",  required=True, help="Path to slides_base.html")
    parser.add_argument("--output", required=True, help="Path to output slides.html")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(html, "html.parser")

    print(f"[inject] SERVER_HOST={SERVER_HOST}")
    print(f"[inject] Audience URL: {AUDIENCE_URL}")
    print(f"[inject] WebSocket:    {WS_URL}")

    inject_fontawesome(soup)
    inject_head_styles(soup)
    inject_qr_overlay(soup)
    inject_like_sidebar(soup)
    inject_stats_slide(soup)
    inject_websocket_script(soup)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"[inject] Done → {args.output}")


if __name__ == "__main__":
    main()
