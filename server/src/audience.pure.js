'use strict';
/**
 * audience.pure.js — pure, DOM-free logic shared by audience.js and its test suite.
 * CommonJS exports so Jest can require() without a build step.
 */

/**
 * Compute CSS transform parameters to letterbox an iframe inside a viewport.
 * @param {number} vw     - viewport width  (px)
 * @param {number} vh     - viewport height (px)
 * @param {number} frameW - iframe intrinsic width  (default 1280)
 * @param {number} frameH - iframe intrinsic height (default 720)
 * @returns {{ scale: number, tx: number, ty: number }}
 */
function computeFrameTransform(vw, vh, frameW, frameH) {
  frameW = frameW || 1280;
  frameH = frameH || 720;
  var scale = Math.min(vw / frameW, vh / frameH);
  var tx = (vw - frameW * scale) / 2;
  var ty = (vh - frameH * scale) / 2;
  return { scale: scale, tx: tx, ty: ty };
}

/**
 * Build the WebSocket URL matching the page's own protocol.
 * http: → ws:// / https: → wss://
 */
function buildWsUrl(protocol, host, port) {
  var scheme = protocol === 'https:' ? 'wss' : 'ws';
  return scheme + '://' + host + ':' + port + '/ws';
}

/** Build the /#print URL used for PDF export. */
function buildPdfUrl(protocol, host, port) {
  return protocol + '//' + host + ':' + port + '/#print';
}

/** Exponential back-off capped at maxDelay ms. */
function nextReconnectDelay(current, max) {
  return Math.min(current * 2, max);
}

/**
 * Parse a slide_update WebSocket message.
 * Returns the target slide index, or null if the message is not a slide_update.
 * Index 0 is valid — never coerce falsy to a default (I8).
 */
function parseSlideUpdate(msg) {
  if (!msg || msg.type !== 'slide_update') return null;
  return msg.index != null ? msg.index : 0;
}

module.exports = {
  computeFrameTransform,
  buildWsUrl,
  buildPdfUrl,
  nextReconnectDelay,
  parseSlideUpdate,
};
