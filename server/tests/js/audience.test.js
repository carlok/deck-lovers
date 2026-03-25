'use strict';
const {
  computeFrameTransform,
  buildWsUrl,
  buildPdfUrl,
  nextReconnectDelay,
  parseSlideUpdate,
} = require('../../src/audience.pure');

// ── computeFrameTransform ─────────────────────────────────────────────────────

describe('computeFrameTransform', () => {
  test('exact-fit viewport returns scale=1, tx=0, ty=0', () => {
    const r = computeFrameTransform(1280, 720, 1280, 720);
    expect(r.scale).toBeCloseTo(1);
    expect(r.tx).toBeCloseTo(0);
    expect(r.ty).toBeCloseTo(0);
  });
  test('half-width viewport halves the scale', () => {
    const r = computeFrameTransform(640, 720, 1280, 720);
    expect(r.scale).toBeCloseTo(0.5);
  });
  test('uses 1280×720 defaults when frameW/H omitted', () => {
    const r = computeFrameTransform(1280, 720);
    expect(r.scale).toBeCloseTo(1);
  });
  test('portrait viewport — height is the limiting axis', () => {
    // vw=720 vh=1280 → width-limit=720/1280≈0.5625, height-limit=1280/720≈1.78 → min=0.5625
    const r = computeFrameTransform(720, 1280, 1280, 720);
    expect(r.scale).toBeCloseTo(720 / 1280);
  });
  test('centres horizontally: tx=(vw-frameW*scale)/2', () => {
    const r = computeFrameTransform(640, 720, 1280, 720);
    expect(r.tx).toBeCloseTo((640 - 1280 * 0.5) / 2);
  });
  test('centres vertically: ty=(vh-frameH*scale)/2', () => {
    const r = computeFrameTransform(1280, 360, 1280, 720);
    const scale = 360 / 720; // height is the constraint
    expect(r.ty).toBeCloseTo((360 - 720 * scale) / 2);
  });
  test('scale is always positive', () => {
    const r = computeFrameTransform(100, 100, 1280, 720);
    expect(r.scale).toBeGreaterThan(0);
  });
});

// ── buildWsUrl ────────────────────────────────────────────────────────────────

describe('buildWsUrl', () => {
  test('http: → ws://', () => {
    expect(buildWsUrl('http:', 'localhost', '8000')).toBe('ws://localhost:8000/ws');
  });
  test('https: → wss://', () => {
    expect(buildWsUrl('https:', 'example.com', '443')).toBe('wss://example.com:443/ws');
  });
  test('always appends /ws path', () => {
    const url = buildWsUrl('http:', '192.168.1.1', '8000');
    expect(url.endsWith('/ws')).toBe(true);
  });
  test('unknown protocol falls back to ws://', () => {
    expect(buildWsUrl('ftp:', 'host', '21')).toBe('ws://host:21/ws');
  });
});

// ── buildPdfUrl ───────────────────────────────────────────────────────────────

describe('buildPdfUrl', () => {
  test('builds /#print URL for http', () => {
    expect(buildPdfUrl('http:', '192.168.1.1', '8000'))
      .toBe('http://192.168.1.1:8000/#print');
  });
  test('builds /#print URL for https', () => {
    expect(buildPdfUrl('https:', 'example.com', '443'))
      .toBe('https://example.com:443/#print');
  });
  test('always ends with /#print', () => {
    const url = buildPdfUrl('http:', 'localhost', '8000');
    expect(url.endsWith('/#print')).toBe(true);
  });
});

// ── nextReconnectDelay ────────────────────────────────────────────────────────

describe('nextReconnectDelay', () => {
  test('doubles current delay', () => {
    expect(nextReconnectDelay(1000, 30000)).toBe(2000);
  });
  test('caps at max delay', () => {
    expect(nextReconnectDelay(20000, 30000)).toBe(30000);
  });
  test('does not exceed max on large input', () => {
    expect(nextReconnectDelay(25000, 30000)).toBe(30000);
  });
  test('works from 500 ms initial delay', () => {
    expect(nextReconnectDelay(500, 30000)).toBe(1000);
  });
  test('sequence converges to max', () => {
    let d = 1000;
    const max = 30000;
    for (let i = 0; i < 20; i++) d = nextReconnectDelay(d, max);
    expect(d).toBe(max);
  });
});

// ── parseSlideUpdate ──────────────────────────────────────────────────────────

describe('parseSlideUpdate', () => {
  test('returns index from a slide_update message', () => {
    expect(parseSlideUpdate({ type: 'slide_update', index: 3 })).toBe(3);
  });
  test('returns 0 when index is null — 0 is a valid slide (I8)', () => {
    expect(parseSlideUpdate({ type: 'slide_update', index: null })).toBe(0);
  });
  test('returns 0 when index is undefined', () => {
    expect(parseSlideUpdate({ type: 'slide_update' })).toBe(0);
  });
  test('returns null for a non-slide_update message type', () => {
    expect(parseSlideUpdate({ type: 'like_update', slide: 2 })).toBeNull();
  });
  test('returns null for null message', () => {
    expect(parseSlideUpdate(null)).toBeNull();
  });
  test('returns null for undefined message', () => {
    expect(parseSlideUpdate(undefined)).toBeNull();
  });
  test('returns null for projector_status message', () => {
    expect(parseSlideUpdate({ type: 'projector_status', connected: true })).toBeNull();
  });
});
