import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(here, 'survival-guide.html');
const outPath = path.join(here, 'CMMC_Level_2_Survival_Guide.pdf');

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file:///' + htmlPath.replace(/\\/g, '/'));
await page.waitForTimeout(400);

await page.pdf({
  path: outPath,
  format: 'Letter',
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: '<span></span>',
  footerTemplate: `
    <div style="width:100%; font-size:6.8px; font-family:Arial,sans-serif; color:#8a8577;
                padding:0 0.6in; display:flex; justify-content:space-between;">
      <span style="letter-spacing:1.5px;">CMMC LEVEL 2 SURVIVAL GUIDE &#183; PLAIN-ENGLISH EDITION &#183; CHRIS JUDKINS</span>
      <span>PAGE <span class="pageNumber"></span> OF <span class="totalPages"></span></span>
    </div>`,
  margin: { top: '0.55in', bottom: '0.62in', left: '0.6in', right: '0.6in' },
});

await browser.close();
console.log('PDF written:', outPath);
