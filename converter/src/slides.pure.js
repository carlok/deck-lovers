'use strict';
/**
 * slides.pure.js — pure, DOM-free logic shared by slides.js and its test suite.
 * CommonJS exports so Jest can require() without a build step.
 */

/**
 * Extract an 11-char YouTube video ID from a URL or bare ID.
 * Returns '' when the input cannot be resolved to a valid ID.
 */
function ytId(urlOrId) {
  var m = /(?:v=|youtu\.be\/|embed\/)([a-zA-Z0-9_-]{11})/.exec(urlOrId);
  var vid = m ? m[1] : (urlOrId || '').trim();
  return /^[a-zA-Z0-9_-]{11}$/.test(vid) ? vid : '';
}

/** Clamp a slide index to [0, total-1]. */
function clampIndex(n, total) {
  return Math.max(0, Math.min(n, total - 1));
}

/** Progress bar width % for a given current index and total slide count. */
function progressPct(current, total) {
  return total > 1 ? (current / (total - 1) * 100) : 100;
}

/**
 * Build a stats array from a likesData map and an array of slide titles.
 * Returns items sorted descending by like count.
 * @param {Object} likesData  - { slideIndex: count }
 * @param {Array}  titles     - slide title strings (stats slide excluded)
 */
function sortStats(likesData, titles) {
  return titles
    .map(function (title, i) {
      return { title: title, idx: i, count: (likesData[i] || 0) };
    })
    .sort(function (a, b) { return b.count - a.count; });
}

/** Bar fill percentage relative to the maximum count. */
function barPct(count, maxCount) {
  if (!maxCount || maxCount <= 0) return 0;
  return Math.round(count / maxCount * 100);
}

module.exports = { ytId, clampIndex, progressPct, sortStats, barPct };
