# F3 — Agent-Executed Real-Surface QA

## Auditor

M5 — Start local application with only fakes, drive with Playwright at 375px/1280px.

## Verification commands

```bash
uv run pytest -m e2e -q tests/e2e/test_dashboard_playwright.py
```

## Results

- **15 passed** across desktop and mobile viewports

## QA scenarios verified

| Scenario | Viewport | Assertion | Status |
|----------|----------|-----------|--------|
| Dashboard loads | 1280px | Title "Dashboard — job-finder" | ✅ |
| Nav links visible | 1280px | All 5 nav links visible | ✅ |
| Dashboard loads | 375px | Title "Dashboard — job-finder" | ✅ |
| Mobile accessible nav | 375px | Nav has aria-label | ✅ |
| Mobile nav links | 375px | All 5 nav links visible | ✅ |
| Skip-link to main | 1280px | Focus moves to #main-content | ✅ |
| Tab navigation | 1280px | Profile settings link receives focus | ✅ |
| 404 error page | 1280px | "Not Found" visible, status 404 | ✅ |
| Health endpoint | 1280px | `live_mcp: false` in response | ✅ |
| Notification redaction | 1280px | Redacted payload visible | ✅ |
| Dashboard stats | 1280px | Accessible region with stats | ✅ |
| CSS custom properties | 1280px | Design tokens defined | ✅ |
| Heading hierarchy | 1280px | Proper semantic headings | ✅ |

## Browser inspection notes

- **Console**: No errors or warnings during page navigation at either viewport
- **Network**: Only local server requests (no external URLs, no LinkedIn/ATS)
- **a11y snapshot**: Keyboard navigation reaches all landmarks, skip-link works
- **Responsive**: Layout adapts correctly at both viewports with proper mobile nav

## Prohibited actions verified absent

| Prohibited action | Check | Status |
|-------------------|-------|--------|
| Real LinkedIn/ATS navigation | No external URLs in network tab | ✅ |
| External/session-linked browser profile | Playwright uses isolated context | ✅ |
| MCP-spawned browser process | No subprocess spawns detected | ✅ |

## Verdict

**APPROVED** — Dashboard works correctly at both desktop and mobile viewports. Keyboard accessible. No prohibited behavior detected.
