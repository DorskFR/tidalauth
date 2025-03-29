import time
from pathlib import Path
from re import Pattern

from playwright.sync_api import FrameLocator, Locator, Page, Playwright, expect, sync_playwright
from pydantic import SecretStr

from tidalauth.settings import TidalauthSettings
from tidalauth.utils import USER_AGENT, SelectorType, Status, get_logger, report_status, retry_with_backoff

logger = get_logger(__name__)


class PlaywrightEngine:
    def __init__(self, settings: TidalauthSettings):
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser = None
        self._context = None
        self._page = None

    def setup(self) -> None:
        """
        Initialize the Playwright environment with anti-detection measures
        """
        self._playwright = sync_playwright().start()

        # Browser
        browser_instance = getattr(self._playwright, self._settings.browser_type)
        browser = browser_instance.launch(headless=self._settings.headless)
        self._browser = browser

        # Context
        context_options = {
            "viewport": {"width": self._settings.viewport_width, "height": self._settings.viewport_height},
            "ignore_https_errors": True,
            "user_agent": USER_AGENT,
            "locale": "en-US",
            "timezone_id": "UTC",
        }

        if self._settings.take_video:
            self._settings.video_dir.mkdir(parents=True, exist_ok=True)
            context_options |= {
                "record_video_dir": self._settings.video_dir,
                "record_video_size": {"width": self._settings.viewport_width, "height": self._settings.viewport_height},
            }
        context = browser.new_context(**context_options)
        context.set_default_timeout(self._settings.timeout_ms)
        self._context = context

        # Page
        page = context.new_page()
        self._page = page

    def teardown(self) -> None:
        """
        Clean up Playwright resources
        """
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def report(self, message: str, status: Status | None = None) -> None:
        """
        Log a message in the format used by the engine
        """
        if status is Status.FAILED:
            logger.exception(message)
        else:
            logger.info(message)

    def sleep(self, milliseconds: float) -> None:
        """
        Sleep for a given number of milliseconds.
        """
        time.sleep(milliseconds / 1000)

    @property
    def page(self) -> Page:
        if not self._page:
            raise ValueError("Page not initialized. Please call `setup` first.")
        return self._page

    @property
    def current_url(self) -> str:
        """
        Return the current URL.
        """
        return self.page.url

    def _get_selector(self, selector: str, selector_type: SelectorType) -> str:
        match selector_type:
            case SelectorType.XPATH:
                return f"xpath={selector}"
            case SelectorType.ID:
                return f"#{selector}"  # Add this line to handle ID selectors
            case SelectorType.CSS:
                return selector
            case _:
                raise ValueError(f"Invalid selector type: {selector_type}")

    def _get_locator(
        self, selector: str | Locator, selector_type: SelectorType, iframe: FrameLocator | None = None
    ) -> Locator:
        """
        Get a locator for the given selector.
        """
        if isinstance(selector, Locator):
            return selector

        selector = self._get_selector(selector, selector_type)
        locator = iframe.locator(selector) if iframe else self.page.locator(selector)
        count = locator.count()

        if count == 0:
            raise ValueError(f"Element not found: {selector}")

        if count > 1:
            logger.warning(f"Multiple elements found: {selector}. Selecting the first visible.")
            for i in range(count):
                element = locator.nth(i)
                if element.is_visible():
                    return element
            else:
                raise ValueError(f"Visible element not found: {selector}")

        return locator

    @report_status
    @retry_with_backoff
    def navigate(self, url: str) -> None:
        """
        Navigate to a URL and wait for network idle.
        """
        self.page.goto(url, wait_until="domcontentloaded")
        self.sleep(self._settings.sleep_ms * 3)  # Wait a bit after a hard navigation

    @report_status
    @retry_with_backoff
    def command_navigate(self, section: str) -> None:
        """
        Navigate to a section via the command manager
        """
        self._get_locator("body", SelectorType.CSS).press("ControlOrMeta+k")

        selector = "//input[@role='combobox']"
        selector_type = SelectorType.XPATH

        self.fill(section, selector, selector_type)
        self.sleep(self._settings.sleep_ms)  # Wait for the command menu animation to show the entry

        while self.element_exists(selector, selector_type):
            logger.info(f"Pressing Enter for {section}")
            self._get_locator("body", SelectorType.CSS).press("Enter")
            self.sleep(self._settings.sleep_ms)  # Wait for the command menu animation to fade out

    @report_status
    def _get_iframe(self, selector: str, context: FrameLocator | None = None) -> FrameLocator:
        """
        Get an iframe by selector.
        """
        if context:
            return context.frame_locator(selector).first
        return self.page.frame_locator(selector).first

    @report_status
    @retry_with_backoff
    def click(self, selector: str, selector_type: SelectorType, *, with_alert: bool = False) -> None:
        """
        Click an element and wait for navigation to complete.
        """
        if with_alert:
            self.page.on("dialog", lambda dialog: dialog.accept())

        self._get_locator(selector, selector_type).click()
        self.page.wait_for_load_state("domcontentloaded")
        self.sleep(self._settings.sleep_ms)  # Gives some time to load after a click

    @report_status
    @retry_with_backoff
    def click_in_iframe(self, iframe_selectors: list[str], selector: str, selector_type: SelectorType) -> None:
        """
        Click an element in an iframe and wait for navigation to complete.
        """
        iframe = None
        for iframe_selector in iframe_selectors:
            iframe = self._get_iframe(iframe_selector, context=iframe)

        self._get_locator(selector, selector_type, iframe).click()
        self.page.wait_for_load_state("domcontentloaded")
        self.sleep(self._settings.sleep_ms)

    @report_status
    @retry_with_backoff
    def fill(self, value: str | SecretStr, selector: str, selector_type: SelectorType) -> None:
        """
        Fill an input field with a value.
        """
        str_value = value.get_secret_value() if isinstance(value, SecretStr) else value
        locator = self._get_locator(selector, selector_type)
        locator.fill(str_value)

    @report_status
    @retry_with_backoff
    def fill_in_iframe(
        self, value: str | SecretStr, iframe_selectors: list[str], selector: str, selector_type: SelectorType
    ) -> None:
        """
        Fill an input field with a value in an iframe.
        """
        iframe = None
        for iframe_selector in iframe_selectors:
            iframe = self._get_iframe(iframe_selector, context=iframe)

        str_value = value.get_secret_value() if isinstance(value, SecretStr) else value
        locator = self._get_locator(selector, selector_type, iframe)
        locator.fill(str_value)

    @report_status
    @retry_with_backoff
    def assert_url(self, url: str) -> None:
        """
        Assert that the current URL matches the expected URL.
        """
        expect(self.page).to_have_url(url)

    @report_status
    @retry_with_backoff
    def assert_element_visible(self, selector: str, selector_type: SelectorType) -> None:
        """
        Assert that an element is visible on the page.
        """
        locator = self._get_locator(selector, selector_type)
        expect(locator).to_be_visible()

    @report_status
    @retry_with_backoff
    def assert_text(self, text: str | Pattern, selector: str, selector_type: SelectorType) -> None:
        """
        Assert that an element contains specific text.
        """
        locator = self._get_locator(selector, selector_type)
        expect(locator).to_contain_text(text)

    def take_screenshot(self, screenshot_dir: Path, name: str) -> str:
        """
        Take a screenshot if enabled in settings.
        """
        path = f"{screenshot_dir}/{name}.png"
        self.page.wait_for_load_state("domcontentloaded")
        self.page.screenshot(path=path)
        return path

    @report_status
    @retry_with_backoff
    def element_exists(self, selector: str, selector_type: SelectorType, *, check_visible: bool = True) -> bool:
        """
        Check if an element exists on the page.
        Returns True if the element exists, False otherwise.
        """
        if isinstance(selector, Locator):
            return selector.count() > 0 and any(sel.is_visible() for sel in selector.all()) if check_visible else True

        selector = self._get_selector(selector, selector_type)
        locator = self.page.locator(selector)
        return locator.count() > 0 and any(loc.is_visible() for loc in locator.all()) if check_visible else True

    @report_status
    @retry_with_backoff
    def assert_element_not_visible(self, selector: str, selector_type: SelectorType) -> None:
        """
        Asserts that an element does not exist on the page or is not visible.
        """
        if isinstance(selector, Locator):
            locator = selector
        else:
            selector = self._get_selector(selector, selector_type)
            locator = self.page.locator(selector)

        if locator.is_visible() or locator.count() > 0:
            raise AssertionError(f"Element not visible assertion failed: {selector}")

    @report_status
    @retry_with_backoff
    def set_local_storage(self, key: str, value: str) -> None:
        """
        Set a value in localStorage using Playwright.
        """
        self.page.evaluate(f"localStorage.setItem('{key}', '{value}')")
        logger.info(f"Set localStorage: {key} = {value}")
