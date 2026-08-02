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

  await page.setViewportSize(size);
  const evidence = page.getByRole('heading', {
    name: '這篇內容的查證證據',
    level: 4,
  });
  const logoHeading = page.getByRole('heading', {
    name: '官方 Logo',
    level: 4,
  });
  await page.screencast.start({
    path: `${outputDir}/07-sources-logo.webm`,
    size,
  });
  try {
    await smoothTo(evidence);
    await pause(5600);
    await smoothTo(logoHeading);
    await pause(6800);
  } finally {
    await page.screencast.stop();
  }

  return {
    sourceSummaryVisible: await page.getByText('查證證據共 3 筆', {
      exact: false,
    }).count(),
    logoCandidateVisible: await page.getByText('找到一張官方 Logo 候選', {
      exact: false,
    }).count(),
  };
}
