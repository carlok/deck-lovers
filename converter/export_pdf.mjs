#!/usr/bin/env node
/** Server-side PDF export — vector (Chromium print) by default, raster optional. */

import fs from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const inputHtml = process.argv[2] ?? "/workspace/slides.html";
const outputPdf = process.argv[3] ?? "/workspace/slides.pdf";
const downloadDir = "/workspace";
const downloadedPdf = path.join(downloadDir, path.basename(outputPdf));
const chromePath = process.env.CHROME_BIN ?? "/usr/bin/chromium";
const pdfMode = (process.env.PDF_MODE ?? "vector").toLowerCase();

const toFileUrl = (path) => (path.startsWith("file://") ? path : pathToFileURL(path).href);
const printUrl = `${toFileUrl(inputHtml)}#print`;

const waitForFile = async (path, timeoutMs = 120000) => {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      await fs.access(path, fsConstants.R_OK);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error(`Timed out waiting for file: ${path}`);
};

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  args: ["--disable-dev-shm-usage", "--no-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });

  console.log(`[pdf] Mode: ${pdfMode}`);
  console.log(`[pdf] Navigating: ${printUrl}`);
  await page.goto(printUrl, { waitUntil: "networkidle0", timeout: 120000 });

  if (pdfMode === "raster") {
    const client = await page.target().createCDPSession();
    await client.send("Page.setDownloadBehavior", {
      behavior: "allow",
      downloadPath: downloadDir,
    });
    try {
      await fs.unlink(downloadedPdf);
    } catch {}
    await waitForFile(downloadedPdf, 180000);
    if (downloadedPdf !== outputPdf) {
      await fs.copyFile(downloadedPdf, outputPdf);
    }
  } else {
    await page.waitForFunction(() => window.__DECK_PRINT_READY__ === true, {
      timeout: 180000,
    });
    await page.pdf({
      path: outputPdf,
      printBackground: true,
      preferCSSPageSize: true,
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    });
  }

  console.log(`[pdf] Generated: ${outputPdf}`);
} finally {
  await browser.close();
}
