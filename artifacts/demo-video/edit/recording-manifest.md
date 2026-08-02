# Demo recording manifest

- Date: 2026-08-01
- App URL: `http://localhost:8502/選題`
- App process: PID 50702
- App database: `/private/tmp/daibu-workstation-redesign.db`
- Real database: `/Users/cengweiting/Developer/daibu-content-brain/daibu.db`
- Real database mtime before: `1785650884` (`Aug 1 23:08:04 2026`)
- Browser capture: 1280×720
- Target: H.264 MP4, yuv420p, 30fps, 110–135 seconds

## Environment evidence

- `lsof -p 50702` shows the Streamlit process has `/private/tmp/daibu-workstation-redesign.db` open.
- Port 8502 is listening under the same process.
- ffmpeg: 8.1.2.
- Playwright CLI: 0.1.17.

## After recording

- Real database mtime after: `1785650884` (`Aug 1 23:08:04 2026`), unchanged.
- Fresh run: Tavily＋Gemini created Warp idea 16; body is 478 characters with 3 verified sources.
- Logo guard: Warp produced an official-site candidate, but it was not confirmed or stored.
- Approved fallback: downstream carousel recording switched to the already verified BillionToOne idea 15.
- Download: seven PNG files in `BillionToOne-carousel.zip`; `unzip -t` reported no errors.
- Final video: H.264, 1280×720, yuv420p, 30fps, 115.4 seconds, 4,925,747 bytes, no audio stream.
- Final SHA-256: `385c2abcb743b887819c766e1993a97971bfc7b79b29c36fd78ec767a686073f`.
- Secret scan: clean; no Tavily or Gemini key pattern in text artifacts.
- Visual review: three edit passes; all 12 cut boundaries, title, midpoint samples, transition, captions, preview and end card passed.
- Browser console: two non-blocking 404s for multipage-relative `_stcore/health` and `_stcore/host-config`; no visible failure in the recorded workflow.
