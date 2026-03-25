'use strict';
const { ytId, clampIndex, progressPct, sortStats, barPct } = require('../../src/slides.pure');

// ── ytId ──────────────────────────────────────────────────────────────────────

describe('ytId', () => {
  test('extracts ID from standard watch URL', () => {
    expect(ytId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });
  test('extracts ID from youtu.be short URL', () => {
    expect(ytId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });
  test('extracts ID from embed URL', () => {
    expect(ytId('https://www.youtube.com/embed/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });
  test('accepts a bare 11-char video ID', () => {
    expect(ytId('dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });
  test('returns empty string for a too-short ID', () => {
    expect(ytId('short')).toBe('');
  });
  test('returns empty string for a plain non-URL string', () => {
    expect(ytId('not-a-youtube-url-at-all')).toBe('');
  });
  test('returns empty string for empty input', () => {
    expect(ytId('')).toBe('');
  });
  test('returns empty string for null-ish input', () => {
    expect(ytId(null)).toBe('');
  });
  test('handles URL with extra query params', () => {
    expect(ytId('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s')).toBe('dQw4w9WgXcQ');
  });
});

// ── clampIndex ────────────────────────────────────────────────────────────────

describe('clampIndex', () => {
  test('clamps negative to 0', () => {
    expect(clampIndex(-1, 5)).toBe(0);
  });
  test('clamps above total-1 to total-1', () => {
    expect(clampIndex(10, 5)).toBe(4);
  });
  test('passes through a valid index unchanged', () => {
    expect(clampIndex(2, 5)).toBe(2);
  });
  test('handles single-slide deck (total=1)', () => {
    expect(clampIndex(0, 1)).toBe(0);
  });
  test('first valid index is 0', () => {
    expect(clampIndex(0, 10)).toBe(0);
  });
  test('last valid index is total-1', () => {
    expect(clampIndex(9, 10)).toBe(9);
  });
});

// ── progressPct ───────────────────────────────────────────────────────────────

describe('progressPct', () => {
  test('returns 100 for a single-slide deck', () => {
    expect(progressPct(0, 1)).toBe(100);
  });
  test('first slide of many is 0 %', () => {
    expect(progressPct(0, 5)).toBe(0);
  });
  test('last slide of many is 100 %', () => {
    expect(progressPct(4, 5)).toBe(100);
  });
  test('middle of 5 slides is 50 %', () => {
    expect(progressPct(2, 5)).toBeCloseTo(50);
  });
  test('two slides: first is 0, second is 100', () => {
    expect(progressPct(0, 2)).toBe(0);
    expect(progressPct(1, 2)).toBe(100);
  });
});

// ── sortStats ─────────────────────────────────────────────────────────────────

describe('sortStats', () => {
  test('sorts slides by like count descending', () => {
    const likes  = { 0: 3, 1: 7, 2: 1 };
    const titles = ['Alpha', 'Beta', 'Gamma'];
    const result = sortStats(likes, titles);
    expect(result[0].title).toBe('Beta');
    expect(result[1].title).toBe('Alpha');
    expect(result[2].title).toBe('Gamma');
  });
  test('returns all slides even when all have 0 likes', () => {
    const result = sortStats({}, ['X', 'Y', 'Z']);
    expect(result).toHaveLength(3);
    result.forEach(r => expect(r.count).toBe(0));
  });
  test('preserves original idx even after sort', () => {
    const likes  = { 0: 1, 1: 5 };
    const titles = ['First', 'Second'];
    const result = sortStats(likes, titles);
    expect(result[0].idx).toBe(1);   // slide 1 has most likes
    expect(result[0].title).toBe('Second');
  });
  test('empty titles array returns empty array', () => {
    expect(sortStats({}, [])).toHaveLength(0);
  });
});

// ── barPct ────────────────────────────────────────────────────────────────────

describe('barPct', () => {
  test('returns 100 when count equals maxCount', () => {
    expect(barPct(5, 5)).toBe(100);
  });
  test('returns 50 for half the max', () => {
    expect(barPct(3, 6)).toBe(50);
  });
  test('returns 0 for zero count', () => {
    expect(barPct(0, 5)).toBe(0);
  });
  test('returns 0 when maxCount is 0 (no division by zero)', () => {
    expect(barPct(0, 0)).toBe(0);
  });
  test('rounds to nearest integer', () => {
    expect(barPct(1, 3)).toBe(33);
  });
});
