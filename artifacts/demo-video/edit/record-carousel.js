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
  await record('08-transition.webm', async () => {
    await page.screencast.showOverlay(`
      <div style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(234,248,251,.96);color:#11152f;font-family:'Noto Sans TC','PingFang TC',sans-serif;">
        <div style="max-width:850px;padding:42px 56px;border:2px solid #b9dee7;border-radius:32px;background:#fff;box-shadow:0 22px 60px rgba(37,104,122,.14);">
          <div style="font-size:18px;font-weight:900;letter-spacing:.12em;color:#438ea2;margin-bottom:16px;">人工確認點</div>
          <div style="font-size:38px;font-weight:900;line-height:1.3;">Warp 的 Logo 等待確認<br><span style="color:#ec7e61;">接著看已完成的輪播案例</span></div>
        </div>
      </div>
    `, { duration: 2600 });
    await pause(2600);
  });

  const checklist = page.getByRole('list', { name: '輪播前置條件' });
  const logoHeading = page.getByRole('heading', { name: '官方 Logo', level: 4 });
  const draftHeading = page.getByRole('heading', { name: '七頁草稿', level: 4 });
  await record('09-checklist-draft.webm', async () => {
    await smoothTo(checklist);
    await pause(4200);
    await smoothTo(logoHeading);
    await pause(4000);
    await smoothTo(draftHeading);
    await pause(3200);
  });

  const cover = page.getByText('頁面標題｜封面', { exact: true });
  const aiRole = page.getByText('頁面標題｜AI 在裡面扮演什麼角色', { exact: true });
  const closing = page.getByText('頁面標題｜收束與互動', { exact: true });
  await record('10-seven-pages.webm', async () => {
    await smoothTo(cover);
    await pause(3500);
    await smoothTo(aiRole);
    await pause(3500);
    await smoothTo(closing);
    await pause(4200);
  });

  const renderButton = page.getByRole('button', { name: '產生七張圖' });
  await smoothTo(renderButton);
  await record('11-render.webm', async () => {
    await pause(1200);
    await renderButton.click();
    await page.getByRole('button', { name: '下載全部（ZIP）' })
      .waitFor({ state: 'visible', timeout: 120000 });
    await pause(2200);
  });

  const previewHeading = page.getByRole('heading', { name: '七張圖預覽', level: 4 });
  const downloadButton = page.getByRole('button', { name: '下載全部（ZIP）' });
  await record('12-preview-download.webm', async () => {
    await smoothTo(previewHeading);
    await pause(6500);
    await smoothTo(downloadButton);
    await pause(2200);
    const downloadPromise = page.waitForEvent('download');
    await downloadButton.click();
    const download = await downloadPromise;
    await download.saveAs(`${outputDir}/BillionToOne-carousel.zip`);
    await pause(2300);
  });

  await record('13-end.webm', async () => {
    await page.screencast.showOverlay(`
      <div style="position:fixed;inset:0;background:#11152f;color:#fff;font-family:'Noto Sans TC','PingFang TC',sans-serif;padding:68px 86px;box-sizing:border-box;">
        <div style="font-size:18px;font-weight:900;letter-spacing:.14em;color:#84cfdb;">目前已完成</div>
        <div style="font-size:44px;font-weight:900;line-height:1.2;margin:18px 0 34px;">一個人也能走完<br>完整的內容製作流程</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 30px;font-size:23px;line-height:1.5;">
          <div>✓ 可信來源找公司</div><div>✓ 人工選題與採用</div>
          <div>✓ AI 正文初稿</div><div>✓ 來源與官方 Logo</div>
          <div>✓ 七張品牌輪播</div><div>✓ PNG／ZIP 下載</div>
        </div>
        <div style="position:absolute;right:80px;bottom:55px;color:#f3aa91;font-size:20px;font-weight:800;">呆一布 AI 實驗室</div>
      </div>
    `, { duration: 5200 });
    await pause(5200);
  });

  return {
    download: 'BillionToOne-carousel.zip',
    previewVisible: await previewHeading.count(),
  };
}
