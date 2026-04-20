#!/usr/bin/env node

import fs from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const inputHtml = process.argv[2] ?? "/workspace/slides.html";
const outputPdf = process.argv[3] ?? "/workspace/slides.pdf";
const downloadDir = "/workspace";
const downloadedPdf = `${downloadDir}/slides.pdf`;
const chromePath = process.env.CHROME_BIN ?? "/usr/bin/chromium";

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
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });

  const client = await page.target().createCDPSession();
  await client.send("Page.setDownloadBehavior", {
    behavior: "allow",
    downloadPath: downloadDir,
  });

  try {
    await fs.unlink(downloadedPdf);
  } catch {}

  console.log(`[pdf] Navigating: ${printUrl}`);
  await page.goto(printUrl, { waitUntil: "networkidle0", timeout: 120000 });
  await waitForFile(downloadedPdf, 120000);

  if (downloadedPdf !== outputPdf) {
    await fs.copyFile(downloadedPdf, outputPdf);
  }

  console.log(`[pdf] Generated: ${outputPdf}`);
} finally {
  await browser.close();
}
