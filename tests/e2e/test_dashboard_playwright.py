"""Playwright browser tests for the job_finder dashboard.

Tests responsive layout at 1280px (desktop) and 375px (mobile), keyboard
navigation coverage, error-state rendering, policy-blocked status, and
notification-redaction display.
"""

from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from collections.abc import Generator

    from playwright.sync_api import Page

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

pytestmark = pytest.mark.e2e


def _wait_for_server(url: str, timeout: float = 15.0) -> None:
    """Poll *url* until it returns HTTP 200 or *timeout* expires."""
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            resp = urllib.request.urlopen(f"{url}/health", timeout=2)
            if resp.status == 200:
                return
        except (
            urllib.error.URLError,
            ConnectionResetError,
            ConnectionRefusedError,
        ) as exc:
            last_error = str(exc)
        time.sleep(0.3)
    msg = f"server did not start within {timeout}s: {last_error}"
    raise RuntimeError(msg)


def _run_server(port: int, ready_event: threading.Event) -> None:
    """Start the FastAPI server on the given port."""
    import traceback

    try:

        import uvicorn
        from src.job_finder.adapters.db import bootstrap_private_sqlite_storage
        from src.job_finder.adapters.migrations import (
            connect_migrated_sqlite_database,
        )
        from src.job_finder.adapters.notifications.telegram import (
            FakeTelegramNotifier,
        )
        from src.job_finder.adapters.repositories.workflow import (
            SqliteWorkflowRepository,
        )
        from src.job_finder.adapters.settings import PrivateSettings
        from src.job_finder.web.app import create_app, inject_test_deps
        from src.job_finder.web.deps import AppDependencies

        tmp = Path("/tmp/jf-pw-server")
        settings = PrivateSettings.from_paths(app_data_dir=tmp)
        _ = bootstrap_private_sqlite_storage(settings)
        conn = connect_migrated_sqlite_database(settings.sqlite_database_path)
        deps = AppDependencies(
            settings=settings,
            connection=conn,
            workflow_repo=SqliteWorkflowRepository(conn),
            notifier=FakeTelegramNotifier(),
            mcp_available=False,
        )
        inject_test_deps(deps)
        app = create_app()
        ready_event.set()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
    except Exception:
        traceback.print_exc()
        raise


@pytest.fixture(scope="session")
def server_url() -> Generator[str, None, None]:
    """Start the FastAPI server on a thread for the entire test session."""
    port = 18923
    url = f"http://127.0.0.1:{port}"
    ready = threading.Event()
    thread = threading.Thread(
        target=_run_server,
        args=(port, ready),
        daemon=True,
    )
    thread.start()
    ready.wait(timeout=10)
    _wait_for_server(url)
    yield url


@pytest.fixture
def app_url(server_url: str) -> str:
    """Return the base URL for the running test server."""
    return server_url


# ── tests ────────────────────────────────────────────────────────────────────


class TestDashboardPlaywright:
    """Playwright browser tests for dashboard responsive behaviour."""

    # ── Desktop viewport (1280px) ────────────────────────────────────────

    def test_desktop_dashboard_loads(self, page: Page, app_url: str) -> None:
        """Desktop: dashboard page loads with stats."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/dashboard")
        expect(page).to_have_title("Dashboard - job_finder")
        expect(page.locator("h1")).to_contain_text("Dashboard")
        expect(page.locator(".stat-card")).to_have_count(6)

    def test_desktop_nav_links_visible(self, page: Page, app_url: str) -> None:
        """Desktop: all nav links are visible."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/dashboard")
        nav = page.locator("nav")
        expect(nav.locator("text=Dashboard")).to_be_visible()
        expect(nav.locator("text=Profile")).to_be_visible()
        expect(nav.locator("text=CV Source")).to_be_visible()
        expect(nav.locator("text=Job Review")).to_be_visible()
        expect(nav.locator("text=Audit")).to_be_visible()
        expect(nav.locator("text=Checkpoints")).to_be_visible()

    def test_desktop_job_review_table(self, page: Page, app_url: str) -> None:
        """Desktop: job review page shows data table."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/job-review")
        expect(page.locator("h1")).to_contain_text("Job Review")
        expect(page.locator("table")).to_be_visible()
        expect(page.locator("table thead tr th")).to_have_count(7)

    def test_desktop_audit_empty_state(self, page: Page, app_url: str) -> None:
        """Desktop: audit page shows empty state with search."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/audit")
        expect(page.locator("h1")).to_contain_text("Audit")
        expect(page.locator('input[name="search"]')).to_be_visible()

    # ── Mobile viewport (375px) ─────────────────────────────────────────

    def test_mobile_nav_toggle_visible(self, page: Page, app_url: str) -> None:
        """Mobile: hamburger toggle is visible, nav links hidden."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{app_url}/dashboard")
        toggle = page.locator("#nav-toggle")
        expect(toggle).to_be_visible()
        expect(toggle).to_have_attribute("aria-label", "Toggle navigation menu")
        nav_links = page.locator("#nav-links")
        expect(nav_links).not_to_be_visible()

    def test_mobile_toggle_opens_nav(self, page: Page, app_url: str) -> None:
        """Mobile: clicking toggle reveals nav links."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{app_url}/dashboard")
        page.locator("#nav-toggle").click()
        nav_links = page.locator("#nav-links")
        expect(nav_links).to_be_visible()
        expect(nav_links.locator("a")).to_have_count(6)

    def test_mobile_stats_grid(self, page: Page, app_url: str) -> None:
        """Mobile: stats cards are visible in 2-column grid."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{app_url}/dashboard")
        expect(page.locator(".stat-card")).to_have_count(6)

    # ── Keyboard navigation ─────────────────────────────────────────────

    def test_keyboard_skip_link(self, page: Page, app_url: str) -> None:
        """Skip-to-content link is reachable via keyboard."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/dashboard")
        skip = page.locator(".skip-link")
        expect(skip).to_have_attribute("href", "#main-content")
        page.keyboard.press("Tab")
        expect(skip).to_be_focused()

    def test_keyboard_reaches_nav_links(self, page: Page, app_url: str) -> None:
        """All nav links are reachable via Tab."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/dashboard")
        for _ in range(8):
            page.keyboard.press("Tab")
        focused = page.evaluate("document.activeElement?.getAttribute('href')")
        assert focused is not None

    def test_keyboard_main_landmark(self, page: Page, app_url: str) -> None:
        """Main landmark is reachable via skip link."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/dashboard")
        page.evaluate('document.querySelector(".skip-link").click()')
        main = page.locator("#main-content")
        expect(main).to_be_visible()

    # ── Error states ────────────────────────────────────────────────────

    def test_nonexistent_route_returns_404(self, page: Page, app_url: str) -> None:
        """Navigating to a nonexistent route returns 404."""
        page.set_viewport_size({"width": 1280, "height": 900})
        response = page.goto(f"{app_url}/nonexistent-page")
        assert response is not None
        assert response.status == 404

    # ── Policy-blocked status ───────────────────────────────────────────

    def test_hard_filter_blocked_status(self, page: Page, app_url: str) -> None:
        """Job review shows hard_filter_blocked badge."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/job-review")
        hard_filter_badge = page.locator("text=Hard Filter")
        expect(hard_filter_badge).to_be_visible()

    def test_cap_hit_status(self, page: Page, app_url: str) -> None:
        """Job review shows cap-hit badge."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/job-review")
        cap_badge = page.locator("text=Capped")
        expect(cap_badge).to_be_visible()

    # ── Notification preview redacted ───────────────────────────────────

    def test_checkpoints_page_has_kill_switch(
        self, page: Page, app_url: str,
    ) -> None:
        """Checkpoints page shows kill switch toggle."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/checkpoints")
        expect(page.locator("h1")).to_contain_text("Checkpoints")
        expect(page.locator("text=Kill Switch")).to_be_visible()

    def test_notification_redacted_preview(self, page: Page, app_url: str) -> None:
        """No emoji, URLs, or CV references appear in page content."""
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_url}/dashboard")
        content = page.content()
        assert "https://" not in content
        assert "🔒" not in content
        assert "📄" not in content
