"""End-to-end fixtures: one logged-in headless Chromium for the session, against a running stack.

The stack (etlui, etlhub API, Celery worker, Redis, DHIS2) is started outside the tests: locally by hand, in CI by
.github/workflows/e2e-playwright.yml. Environment:
- DHIS2_TEST_URL, DHIS2_TEST_USERNAME, DHIS2_TEST_PASSWORD: the DHIS2 account to log in with (all skipped without);
- E2E_UI_URL (default http://localhost:5173), E2E_API_URL (default http://localhost:8111);
- E2E_RELAUNCH_IMPORTS=1: relaunch the imports even when carried over from another pass of the month (etlhub does
  not compare the Pivot source, PIVOT_URL, when it carries an import over).
"""
import hashlib
import os
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]  # the stack's data_dir: ./input, ./output (production), test/ (test mode)
ARTIFACTS = Path(__file__).parent / "artifacts"  # screenshots, uploaded by the workflow
UI = os.getenv("E2E_UI_URL", "http://localhost:5173").rstrip("/")
API = os.getenv("E2E_API_URL", "http://localhost:8111").rstrip("/")
DHIS2 = os.getenv("DHIS2_TEST_URL", "").rstrip("/")
USERNAME, PASSWORD = os.getenv("DHIS2_TEST_USERNAME", ""), os.getenv("DHIS2_TEST_PASSWORD", "")
RELAUNCH_IMPORTS = os.getenv("E2E_RELAUNCH_IMPORTS") == "1"
JOB_LIMIT_S = 1800  # how long a test waits for one job (the jobs themselves have no timeout, by decision)


class Stack:
    """The browser page, and etlhub called with its session cookie, as etlui does."""

    def __init__(self, page: Page):
        self.page = page

    def get(self, path: str) -> tuple[int, object]:
        return self._answer(self.page.context.request.get(f"{API}{path}"))

    def send(self, method: str, path: str, **kwargs) -> tuple[int, object]:
        # etlhub refuses a POST, PUT or DELETE whose Origin is not etlui's.
        response = self.page.context.request.fetch(f"{API}{path}", method=method, headers={"Origin": UI}, **kwargs)
        return self._answer(response)

    @staticmethod
    def _answer(response) -> tuple[int, object]:
        json_body = "json" in response.headers.get("content-type", "")
        return response.status, response.json() if json_body else response.text()

    def state(self) -> dict:
        return self.get("/pipeline/checkpoints")[1]

    def item(self, name: str) -> dict:
        return next(i for step in self.state()["steps"] for i in step["items"] if i["item"] == name)

    def launch(self, task: str, confirm: bool = False) -> str:
        """Launches a job as etlui does and returns its job_id (202), or fails the test with etlhub's answer.
        No dry_run: etlhub takes the mode's (DRYRUN = TEST MODE)."""
        params = {"confirm": "true"} if confirm else {}
        path, body = ("/forecast/", {"data": {}}) if task == "forecast" else (f"/{task}", {})
        status, answer = self.send("POST", path, params=params, **body)
        assert status == 202, f"{task}: {status} {answer}"
        return answer["job_id"]

    def wait(self, job_id: str) -> dict:
        """The job's end ({status, message, logs}), read where etlui reads it."""
        start = time.monotonic()
        while time.monotonic() - start < JOB_LIMIT_S:
            status, body = self.get(f"/api/tracking/etl-logs/{job_id}")
            if status == 200 and body.get("status") in ("success", "error"):
                return body
            time.sleep(3)
        pytest.fail(f"{job_id} still running after {JOB_LIMIT_S} s")

    def run_job(self, task: str, confirm: bool = False) -> dict:
        job_id = self.launch(task, confirm)
        end = self.wait(job_id)
        assert end["status"] == "success", f"{task} ({job_id}): {end.get('message')}"
        return {**end, "job_id": job_id}

    def shot(self, name: str) -> None:
        ARTIFACTS.mkdir(exist_ok=True)
        self.page.screenshot(path=str(ARTIFACTS / f"{name}.png"), full_page=True)


def login(page: Page) -> None:
    page.goto(f"{UI}/login")
    page.locator('input[type="url"]').fill(DHIS2)
    page.locator('input[type="text"]').fill(USERNAME)
    page.locator('input[type="password"]').fill(PASSWORD)
    page.locator('button[type="submit"]').click()
    page.wait_for_url(lambda url: "/login" not in url, timeout=30000)


@pytest.fixture(scope="session")
def stack():
    """One login for the whole run: a login revokes the DHIS2 token of the previous one, so every session but the
    last is invalid. Logs out at the end, which revokes the token this login created."""
    if not (DHIS2 and USERNAME and PASSWORD):
        pytest.skip("DHIS2_TEST_URL, DHIS2_TEST_USERNAME and DHIS2_TEST_PASSWORD not set")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1400, "height": 1000}).new_page()
        login(page)
        stack = Stack(page)
        try:
            yield stack
        finally:
            stack.shot("last")
            stack.send("POST", "/auth/logout")
            browser.close()


def production_files() -> dict[str, str]:
    """sha256 of every file under ./input and ./output: the production working folders."""
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ("input", "output") for p in sorted((ROOT / folder).rglob("*")) if p.is_file()}


# The tests of a module marked `incremental` are the steps of one scenario: after a failure, the next steps are
# reported xfail ("previous step failed") instead of failing for the same cause. An xfail does not stop the scenario.
def pytest_configure(config):
    config.addinivalue_line("markers", "incremental: the module's tests are the ordered steps of one scenario")


def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords and call.excinfo is not None and not call.excinfo.errisinstance(
            (pytest.xfail.Exception, pytest.skip.Exception)):
        item.parent._failed_step = item.name


def pytest_runtest_setup(item):
    failed = getattr(item.parent, "_failed_step", None)
    if "incremental" in item.keywords and failed:
        pytest.xfail(f"previous step failed: {failed}")
