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
    await page.screencast.start({ path: `${outputDir}/${filename}`, size });
    try {
      await action();
    } finally {
      await page.screencast.stop();
    }
  };

  await page.setViewportSize(size);
  const body = page.getByRole('textbox', { name: '正文' });
  await body.waitFor({ state: 'visible', timeout: 30000 });
  await record('06-body.webm', async () => {
    await smoothTo(body);
    await pause(5200);
    const carousel = page.locator('summary').filter({ hasText: '輪播製作' });
    await smoothTo(carousel);
    await pause(900);
    await carousel.click();
    await pause(1700);
  });

  const evidence = page.getByRole('heading', {
    name: '這篇內容的查證證據',
    level: 4,
  });
  await evidence.waitFor({ state: 'visible', timeout: 120000 });
  await record('07-sources-logo.webm', async () => {
    await smoothTo(evidence);
    await pause(5200);
    const logoHeading = page.getByRole('heading', {
      name: '官方 Logo',
      level: 4,
    });
    await smoothTo(logoHeading);
    await pause(6200);
  });

  return {
    company: 'Warp',
    bodyLength: await body.inputValue().then(value => value.length),
    logoCandidateVisible: await page.getByText('找到一張官方 Logo 候選', {
      exact: false,
    }).count(),
    verifiedLogoVisible: await page.getByText('Warp 官方 Logo', {
      exact: false,
    }).count(),
  };
}
