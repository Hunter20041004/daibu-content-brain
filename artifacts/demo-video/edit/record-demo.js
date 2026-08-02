async page => {
  const outputDir = '/Users/cengweiting/Developer/daibu-content-brain/artifacts/demo-video/edit';
  const size = { width: 1280, height: 720 };
  const pause = ms => page.waitForTimeout(ms);
  const smoothTo = async locator => {
    await locator.waitFor({ state: 'visible', timeout: 30000 });
    await locator.evaluate(element => element.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
      inline: 'nearest',
    }));
    await pause(900);
  };
  const record = async (filename, action) => {
    await page.screencast.start({
      path: `${outputDir}/${filename}`,
      size,
    });
    try {
      await action();
    } finally {
      await page.screencast.stop();
    }
  };

  await page.setViewportSize(size);
  await page.goto('http://localhost:8502/選題');
  await page.getByRole('heading', { name: '內容製作', exact: true })
    .waitFor({ state: 'visible', timeout: 30000 });
  await pause(1000);

  await record('01-title.webm', async () => {
    await page.screencast.showOverlay(`
      <div style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#eaf8fb;color:#11152f;font-family:'Noto Sans TC','PingFang TC',sans-serif;">
        <div style="position:absolute;top:44px;left:54px;font-size:18px;font-weight:800;letter-spacing:.14em;color:#438ea2;">呆一布 AI 實驗室</div>
        <div style="max-width:900px;padding:48px 64px;border:2px solid #b9dee7;border-radius:36px;background:rgba(255,255,255,.82);box-shadow:0 24px 70px rgba(37,104,122,.15);">
          <div style="font-size:22px;font-weight:800;color:#ec7e61;margin-bottom:18px;">DEMO · 內容工作站</div>
          <div style="font-size:52px;font-weight:900;line-height:1.18;letter-spacing:-.04em;">從找公司<br>到七張輪播</div>
        </div>
        <div style="position:absolute;right:65px;bottom:52px;width:24px;height:24px;border-radius:50%;background:#f3aa91;"></div>
      </div>
    `, { duration: 3000 });
    await pause(3000);
  });

  const seriesButton = page.getByRole('button', { name: 'AI 新創介紹' });
  await smoothTo(seriesButton);
  await record('02-search.webm', async () => {
    await pause(900);
    await seriesButton.click();
    const generateButton = page.getByRole('button', {
      name: /再產生 3 則|開始找題材/,
    });
    await smoothTo(generateButton);
    await pause(900);
    await generateButton.click();
    await page.getByText('正在閱讀來源並整理候選…')
      .waitFor({ state: 'visible', timeout: 15000 });
    await pause(2300);
  });

  await page.getByRole('heading', { name: /候選（[4-9]\d*）/ })
    .waitFor({ state: 'visible', timeout: 180000 });
  await pause(1200);

  const candidateHeading = page.getByRole('heading', { name: /候選（\d+）/ });
  const comparisonButton = page.locator('button')
    .filter({ hasText: '｜' })
    .first();
  await smoothTo(candidateHeading);
  await record('03-candidates.webm', async () => {
    await pause(1500);
    await smoothTo(comparisonButton);
    await pause(1000);
    await comparisonButton.click();
    const newBadge = page.locator('.candidate-card__new');
    await newBadge.waitFor({ state: 'visible', timeout: 30000 });
    await smoothTo(newBadge);
    await pause(3500);
  });

  const company = (await page.locator('.idea-company').first().innerText()).trim();
  const adoptButton = page.getByRole('button', { name: '採用並繼續寫內容' });
  await smoothTo(adoptButton);
  await record('04-adopt.webm', async () => {
    await pause(1200);
    await adoptButton.click();
    const draftButton = page.getByRole('button', { name: 'AI 幫我寫初稿' });
    await draftButton.waitFor({ state: 'visible', timeout: 30000 });
    await smoothTo(draftButton);
    await pause(2200);
  });

  const draftButton = page.getByRole('button', { name: 'AI 幫我寫初稿' });
  await record('05-draft-start.webm', async () => {
    await pause(1000);
    await draftButton.click();
    await page.getByRole('textbox', { name: '正文' })
      .waitFor({ state: 'visible', timeout: 180000 });
    await pause(2500);
  });

  const body = page.getByRole('textbox', { name: '正文' });
  await body.waitFor({ state: 'visible', timeout: 180000 });
  await page.waitForFunction(() => {
    const field = Array.from(document.querySelectorAll('textarea'))
      .find(element => element.getAttribute('aria-label') === '正文');
    return Boolean(field && field.value.trim().length >= 100);
  }, null, { timeout: 180000 });
  await pause(1500);

  await record('06-body-sources-logo.webm', async () => {
    await smoothTo(body);
    await pause(5000);
    const evidence = page.getByText('這篇內容的查證證據', { exact: true });
    await smoothTo(evidence);
    await pause(4500);
    const logoHeading = page.getByText('官方 Logo', { exact: true }).first();
    await smoothTo(logoHeading);
    await pause(5500);
  });

  return {
    company,
    candidateCount: await page.locator('.candidate-card__new').count(),
    bodyLength: await body.inputValue().then(value => value.length),
    logoCandidateVisible: await page.getByText('找到一張官方 Logo 候選', {
      exact: false,
    }).count(),
  };
}
