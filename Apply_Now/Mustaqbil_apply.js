// ============================================================
//  Mustakbil.com Auto-Apply Script — Playwright
//  Usage: node Mustaqbil_apply.js <job-url> [mustaqbil-email] [mustaqbil-password]
//  Env override: MUSTAQBIL_EMAIL, MUSTAQBIL_PASSWORD
// ============================================================

const { chromium } = require('playwright');

const JOB_URL = process.argv[2];

const CONFIG = {
  email:            process.env.MUSTAQBIL_EMAIL || process.argv[3],
  password:         process.env.MUSTAQBIL_PASSWORD || process.argv[4],
  answerAllToggles: true,   // true = Yes to all toggles
  headless:         false,  // false = watch it run
  slowMo:           600,
  dryRun:           false,  // true = stop before final Submit
};

async function loginViaNavbar(page) {
  console.log('🔑  Clicking navbar Login button…');

  // The login button is an Angular-routed <a> — clicking it navigates to the login page.
  // We use page.locator + Promise.all to catch the navigation that Angular triggers.
  const loginBtn = page.locator('a.login-button').first();
  await loginBtn.waitFor({ state: 'visible', timeout: 5000 });

  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(() => {}),
    loginBtn.click(),
  ]);

  console.log(`   Navigated to: ${page.url()}`);

  // Wait for Angular to render the email/password fields
  await page.waitForSelector(
    'input[type="email"], input[formcontrolname="email"]',
    { state: 'visible', timeout: 10000 }
  );
  await page.waitForTimeout(500);

  console.log('   Filling credentials…');
  const emailInput = page.locator('input[type="email"], input[formcontrolname="email"]').first();
const passwordInput = page.locator('input[type="password"], input[formcontrolname="password"]').first();

await emailInput.click();
await emailInput.fill(CONFIG.email);
await emailInput.press('Tab');   // trigger Angular change detection

await passwordInput.click();
await passwordInput.fill(CONFIG.password);
await passwordInput.press('Tab'); // VERY IMPORTANT

  // Submit and wait for post-login redirect
const loginSubmitBtn = page.locator('button:has-text("Login")').first();

await loginSubmitBtn.waitFor({ state: 'visible' });

console.log('🖱️ Clicking login submit...');

// Try normal click
try {
  await loginSubmitBtn.click({ force: true });
} catch (e) {
  console.log('⚠️ Click failed, trying Enter key...');
  await passwordInput.press('Enter');
}


  await page.waitForTimeout(1500);
  console.log(`✅  Logged in — now at: ${page.url()}`);

  // If login redirected away from the job page, go back to it
  if (!page.url().includes(new URL(JOB_URL).pathname)) {
    console.log('🔄  Not on job page — navigating back…');
    await page.goto(JOB_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
  }
}

async function handleWizardStep(page, stepNumber) {
  console.log(`\n📋  Step ${stepNumber}: setting toggles…`);

  const checkboxes = await page.locator('.wizard-step input[type="checkbox"][role="switch"]').all();
  const tracks     = await page.locator('.wizard-step .md-switch__track').all();

  console.log(`   Found ${checkboxes.length} toggle(s)`);

  for (let i = 0; i < checkboxes.length; i++) {
    const isChecked = await checkboxes[i].isChecked();

    if (isChecked !== CONFIG.answerAllToggles) {
      await tracks[i].evaluate(el => el.click());
      await page.waitForTimeout(300);
      console.log(`   Toggle ${i + 1} → ${CONFIG.answerAllToggles ? 'ON ✓' : 'OFF ✗'}`);
    } else {
      console.log(`   Toggle ${i + 1} → already ${CONFIG.answerAllToggles ? 'ON ✓' : 'OFF ✗'} (skipped)`);
    }
  }

  await page.waitForTimeout(500);
}

async function applyToJob() {
  const browser = await chromium.launch({ headless: CONFIG.headless, slowMo: CONFIG.slowMo });
  const context = await browser.newContext({
    viewport:  { width: 1280, height: 800 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    // 1. Open job page
    console.log(`\n🌐  Opening job page: ${JOB_URL}`);
    await page.goto(JOB_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // 2. Click Login in navbar → fill credentials → return to job page
    await loginViaNavbar(page);

    // 3. Click Apply Now
    console.log('🖱️   Clicking Apply Now…');
    const applyBtn = page.locator(
      'button.md-button.primary:has-text("Apply Now"), button.md-navigation-bar__primary-btn:has-text("Apply Now")'
    ).first();
    await applyBtn.waitFor({ state: 'visible', timeout: 10000 });
    await applyBtn.click();
    await page.waitForTimeout(1500);

    // 4. Wait for apply wizard
    await page.waitForSelector('job-apply .apply-container', { timeout: 10000 });
    console.log('✅  Apply wizard opened');

    // 5. Step 1 — Eligibility toggles + Continue
    await handleWizardStep(page, 1);
    const continueBtn1 = page.locator('button.wizard-btn:has-text("Continue")').first();
    await continueBtn1.waitFor({ state: 'visible' });
    await continueBtn1.click();
    console.log('➡️   Clicked Continue (Step 1)');
    await page.waitForTimeout(1200);

    // 6. Step 2 — Skills toggles + Continue
    await handleWizardStep(page, 2);
    const continueBtn2 = page.locator('button.wizard-btn:has-text("Continue")').first();
    await continueBtn2.waitFor({ state: 'visible' });
    await continueBtn2.click();
    console.log('➡️   Clicked Continue (Step 2)');
    await page.waitForTimeout(1200);

    // 7. Step 3 — Review & Submit
    console.log('\n📄  Step 3: Review screen reached');

    if (CONFIG.dryRun) {
      console.log('🚫  DRY RUN — not submitting. Set dryRun: false to submit for real.');
      await page.waitForTimeout(5000);
    } else {
      const submitBtn = page.locator(
        'button:has-text("Submit Application"), button.wizard-btn:has-text("Submit")'
      ).first();
      await submitBtn.waitFor({ state: 'visible', timeout: 10000 });
      await submitBtn.click();
      console.log('🚀  Clicked Submit Application!');
      await page.waitForTimeout(3000);

      const bodyText = await page.locator('body').innerText();
      if (/application submitted|successfully|applied/i.test(bodyText)) {
        console.log('🎉  Application submitted successfully!');
      } else {
        console.log('⚠️   Submit clicked — verify success manually.');
      }
    }

  } catch (err) {
    console.error('\n❌  Error:', err.message);
    await page.screenshot({ path: 'error_screenshot.png', fullPage: true });
    console.log('📸  Screenshot saved to error_screenshot.png');
  } finally {
    if (!CONFIG.headless) {
      console.log('\n👀  Browser staying open for 60s.');
      await page.waitForTimeout(60000);
    }
    await browser.close();
  }
}

// ── Entry point ──────────────────────────────────────────────
if (!JOB_URL) {
  console.error('❌  Usage: node Mustaqbil_apply.js <job-url> [mustaqbil-email] [mustaqbil-password]');
  process.exit(1);
}

if (!CONFIG.email || !CONFIG.password) {
  console.error('❌  Missing Mustaqbil credentials. Pass via args or MUSTAQBIL_EMAIL/MUSTAQBIL_PASSWORD env vars.');
  process.exit(1);
}

applyToJob();