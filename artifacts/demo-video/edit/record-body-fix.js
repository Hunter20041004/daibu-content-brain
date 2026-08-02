async page => {
  const outputDir = '/Users/cengweiting/Developer/daibu-content-brain/artifacts/demo-video/edit';
  const size = { width: 1280, height: 720 };
  const pause = ms => page.waitForTimeout(ms);

  await page.setViewportSize(size);
  const body = page.getByRole('textbox', { name: '正文' }).first();
  await body.waitFor({ state: 'visible', timeout: 30000 });
  await body.evaluate(element => element.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
    inline: 'nearest',
  }));
  await pause(900);

  const bodyText = await body.inputValue();
  if (bodyText.length < 100) {
    throw new Error(`正文只有 ${bodyText.length} 字，拒絕錄製空白示範`);
  }

  await body.evaluate(element => {
    element.focus();
    element.setSelectionRange(0, 0);
    element.scrollTop = 0;
  });
  await pause(1200);

  await page.screencast.start({
    path: `${outputDir}/06-body-corrected.webm`,
    size,
  });
  try {
    await pause(5000);
    await body.evaluate(element => element.scrollTo({
      top: element.scrollHeight,
      behavior: 'smooth',
    }));
    await pause(4200);
  } finally {
    await page.screencast.stop();
  }

  return {
    bodyLength: bodyText.length,
    visibleStart: bodyText.slice(0, 32),
  };
}
