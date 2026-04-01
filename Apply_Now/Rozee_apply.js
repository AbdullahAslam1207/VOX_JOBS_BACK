// ============================================================
//  Rozee.pk Auto-Apply Script — Playwright
//  Usage: node Rozee_apply.js <upload-page-url> <resume-path> [expected-salary]
//  Env override: ROZEE_RESUME_PATH, ROZEE_EXPECTED_SALARY
// ============================================================

const { chromium } = require('playwright');
const path = require('path');

const CONFIG = {
  resumePath:     process.env.ROZEE_RESUME_PATH || process.argv[3],
  expectedSalary: process.env.ROZEE_EXPECTED_SALARY || process.argv[4] || '1000',
  headless:       false,
  slowMo:         800,
  dryRun:         true,     // ← set false to actually submit
};

async function applyToJob(uploadUrl) {
  const browser = await chromium.launch({ headless: CONFIG.headless, slowMo: CONFIG.slowMo });
  const context = await browser.newContext({
    viewport:  { width: 1280, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    // 1. Open upload page
    console.log(`\n🌐  Opening: ${uploadUrl}`);
    await page.goto(uploadUrl, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // 2. Upload resume
    // File input is hidden by CSS — use 'attached' (not 'visible') to wait for it
    console.log('\n📎  Uploading resume…');
    const resumeAbsPath = path.resolve(CONFIG.resumePath);
    console.log(`   File: ${resumeAbsPath}`);

    const fileInput = page.locator('input#resume, input[name="resume"], input[type="file"]').first();

    // Wait for element to exist in DOM (ignores CSS visibility)
    await fileInput.waitFor({ state: 'attached', timeout: 10000 });

    // setInputFiles works on hidden inputs directly — no need to click or make visible
    await fileInput.setInputFiles(resumeAbsPath);
    console.log('✅  File attached — waiting for upload to finish…');

    // Wait for submit button to become enabled (fires after upload completes)
    await page.waitForFunction(
      () => {
        const btn = document.getElementById('submitBtn');
        return btn && !btn.disabled;
      },
      { timeout: 30000 }
    );
    console.log('✅  Resume uploaded successfully');

    // 3. Fill salary
    console.log('\n💰  Filling salary…');
    const salaryInput = page.locator('input#salary, input[name="salary"]').first();
    await salaryInput.waitFor({ state: 'visible', timeout: 5000 });
    await salaryInput.click();
    await salaryInput.fill(CONFIG.expectedSalary);
    await salaryInput.dispatchEvent('input');
    console.log(`✅  Salary: ${CONFIG.expectedSalary}`);

    // 4. Survey questions (pause for manual fill if present)
    await page.waitForTimeout(1200);
    const surveyContainer = page.locator('#surveyContainer.loaded');
    const hasSurvey = await surveyContainer.isVisible().catch(() => false);
    if (hasSurvey) {
      const fields = await surveyContainer.locator('select, input[type="text"], input[type="number"]').all();
      if (fields.length > 0) {
        console.log(`\n📋  ${fields.length} survey question(s) found.`);
        console.log('⏸️   Pausing 45s — fill them manually, then script will submit.');
        await page.waitForTimeout(45000);
      }
    }

    // 5. Submit
    if (CONFIG.dryRun) {
      console.log('\n🚫  DRY RUN — not submitting. Set dryRun: false when ready.');
      await page.waitForTimeout(10000);
    } else {
      console.log('\n🚀  Submitting…');
      const submitBtn = page.locator('button#submitBtn').first();
      await submitBtn.waitFor({ state: 'visible', timeout: 10000 });
      await submitBtn.click();
      await page.waitForTimeout(4000);

      try {
        await page.waitForSelector('#successMsg', { timeout: 10000 });
        const title   = await page.locator('#resultTitle').innerText().catch(() => '');
        const message = await page.locator('#resultMessage').innerText().catch(() => '');
        console.log(`\n${/thank you|success/i.test(title) ? '🎉' : '⚠️'}  ${title} — ${message}`);
      } catch {
        const body = await page.locator('body').innerText().catch(() => '');
        console.log(/submitted|thank you/i.test(body)
          ? '🎉  Application submitted successfully!'
          : '⚠️   Submit clicked — verify in browser.');
      }
    }

  } catch (err) {
    console.error('\n❌  Error:', err.message);
    await page.screenshot({ path: 'rozee_error.png', fullPage: true }).catch(() => {});
    console.log('📸  Screenshot saved to rozee_error.png');
  } finally {
    if (!CONFIG.headless) {
      console.log('\n👀  Browser staying open for 60s.');
      await page.waitForTimeout(60000).catch(() => {});
    }
    await browser.close();
  }
}

const uploadUrl = process.argv[2];
if (!uploadUrl) {
  console.error('❌  Usage: node Rozee_apply.js <upload-page-url> <resume-path> [expected-salary]');
  process.exit(1);
}

if (!CONFIG.resumePath) {
  console.error('❌  Missing resume path. Pass via args or ROZEE_RESUME_PATH env var.');
  process.exit(1);
}
applyToJob(uploadUrl);