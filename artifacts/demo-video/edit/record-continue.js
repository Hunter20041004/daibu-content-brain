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
  const candidateHeading = page.getByRole('heading', { name: /候選（\d+）/ });
  const comparisonButton = page.locator('button')
    .filter({ hasText: '｜' })
    .first();
  await smoothTo(candidateHeading);
  await record('03-candidates.webm', async () => {
    await pause(1600);
    await smoothTo(comparisonButton);
    await pause(1000);
    await comparisonButton.click();
    const newBadge = page.locator('.candidate-card__new');
    await newBadge.waitFor({ state: 'visible', timeout: 30000 });
    await smoothTo(newBadge);
    await pause(4200);
  });

  const company = (await page.locator('.idea-company').first().innerText()).trim();
  const adoptButton = page.getByRole('button', { name: '採用並繼續寫內容' });
  await smoothTo(adoptButton);
  await record('04-adopt.webm', async () => {
    await pause(1500);
    await adoptButton.click();
    const draftButton = page.getByRole('button', { name: 'AI 幫我寫初稿' });
    await draftButton.waitFor({ state: 'visible', timeout: 30000 });
    await smoothTo(draftButton);
    await pause(2500);
  });

  const draftButton = page.getByRole('button', { name: 'AI 幫我寫初稿' });
  await record('05-draft-start.webm', async () => {
    await pause(1200);
    await draftButton.click();
    await page.getByRole('textbox', { name: '正文' })
      .waitFor({ state: 'visible', timeout: 180000 });
    await pause(2600);
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
    await pause(5200);
    const evidence = page.getByText('這篇內容的查證證據', { exact: true });
    await smoothTo(evidence);
    await pause(4800);
    const logoHeading = page.getByText('官方 Logo', { exact: true }).first();
    await smoothTo(logoHeading);
    await pause(5800);
  });

  return {
    company,
    bodyLength: await body.inputValue().then(value => value.length),
    logoCandidateVisible: await page.getByText('找到一張官方 Logo 候選', {
      exact: false,
    }).count(),
  };
}
