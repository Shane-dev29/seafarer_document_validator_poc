"""
core/page_recorder.py
---------------------
A thin wrapper around a Playwright Page object that automatically
captures a screenshot after every key action and pushes it to the
ScreencastBroadcaster for live streaming to the Web UI.

Usage in any verifier script:

    from core.page_recorder import PageRecorder
    from core.screencast import screencast_broadcaster

    recorder = PageRecorder(page, screencast_broadcaster)
    recorder.goto("https://portal.example.com")
    recorder.fill("#cert_no", "ABC123", label="Filling CoC number...")
    recorder.click("#search_btn", label="Clicking Search...")
    recorder.wait_for_selector(".result", label="Waiting for results...")
"""

import base64
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, Locator
    from core.screencast import ScreencastBroadcaster


class PageRecorder:
    """
    Wraps a Playwright Page and auto-captures screenshots after each
    interaction, streaming them via ScreencastBroadcaster.
    """

    def __init__(self, page: "Page", broadcaster: "ScreencastBroadcaster"):
        self._page = page
        self._broadcaster = broadcaster
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _snap(self, label: str = "") -> None:
        """Take a screenshot and push to broadcaster."""
        try:
            png_bytes: bytes = self._page.screenshot(full_page=False, timeout=5000)
            self._broadcaster.push_frame(png_bytes, label=label)
            self._frame_count += 1
        except Exception as e:
            # Never let screenshotting block the verifier
            print(f"[PageRecorder] Screenshot skipped: {e}")

    # ------------------------------------------------------------------
    # Wrapped Playwright actions
    # ------------------------------------------------------------------

    def goto(self, url: str, label: str = "", **kwargs) -> None:
        label = label or f"Navigating to {url[:60]}..."
        self._broadcaster.set_label(label)
        self._page.goto(url, **kwargs)
        self._snap(label)

    def fill(self, selector: str, value: str, label: str = "", **kwargs) -> None:
        label = label or f"Filling {selector}..."
        self._broadcaster.set_label(label)
        self._page.fill(selector, value, **kwargs)
        self._snap(label)

    def type(self, selector: str, text: str, label: str = "", **kwargs) -> None:
        label = label or f"Typing in {selector}..."
        self._broadcaster.set_label(label)
        self._page.type(selector, text, **kwargs)
        self._snap(label)

    def click(self, selector: str, label: str = "", **kwargs) -> None:
        label = label or f"Clicking {selector}..."
        self._broadcaster.set_label(label)
        self._page.click(selector, **kwargs)
        time.sleep(0.3)   # brief pause so result renders before snap
        self._snap(label)

    def select_option(self, selector: str, value: str, label: str = "", **kwargs) -> None:
        label = label or f"Selecting option '{value}'..."
        self._broadcaster.set_label(label)
        self._page.select_option(selector, value, **kwargs)
        self._snap(label)

    def wait_for_selector(self, selector: str, label: str = "", **kwargs) -> None:
        label = label or f"Waiting for {selector}..."
        self._broadcaster.set_label(label)
        self._page.wait_for_selector(selector, **kwargs)
        self._snap(label)

    def wait_for_load_state(self, state: str = "networkidle", label: str = "", **kwargs) -> None:
        label = label or f"Loading page ({state})..."
        self._broadcaster.set_label(label)
        self._page.wait_for_load_state(state, **kwargs)
        self._snap(label)

    def screenshot(self, *args, **kwargs) -> bytes:
        """Take an explicit screenshot (also captures to broadcaster)."""
        label = kwargs.pop("label", "Capturing final result...")
        self._broadcaster.set_label(label)
        kwargs.setdefault("full_page", False)
        png_bytes = self._page.screenshot(*args, **kwargs)
        self._broadcaster.push_frame(png_bytes, label=label)
        self._frame_count += 1
        return png_bytes

    def set_input_files(self, selector: str, files, label: str = "", **kwargs) -> None:
        label = label or "Attaching document file..."
        self._broadcaster.set_label(label)
        self._page.set_input_files(selector, files, **kwargs)
        self._snap(label)

    def snap(self, label: str) -> None:
        """Manually push a labelled snapshot at any point in a verifier."""
        self._snap(label)

    # ------------------------------------------------------------------
    # Pass-through for everything else
    # ------------------------------------------------------------------

    def __getattr__(self, name):
        """Delegate any unrecognised attributes to the underlying page."""
        return getattr(self._page, name)

    @property
    def page(self) -> "Page":
        """Access the raw Playwright page if needed."""
        return self._page
