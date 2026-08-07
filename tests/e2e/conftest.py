"""端到端测试共享夹具。

e2e 测试需要:
1. 已安装 playwright 包与 Chromium 浏览器(见 pyproject [project.optional-dependencies].e2e)
2. 前端服务正在运行(默认 http://127.0.0.1:5173,可通过 E2E_BASE_URL 覆盖)

运行方式:
    python -m pytest tests/e2e -m e2e

默认质量门(pytest 不带 -m e2e)会自动跳过本目录用例。
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("playwright.sync_api", reason="需要安装 playwright 包才能运行 e2e 测试")

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:5173")


@pytest.fixture(scope="session")
def base_url() -> str:
    """被测前端地址,可用 E2E_BASE_URL 环境变量覆盖(如 Docker 部署 http://127.0.0.1:8080)。"""
    return E2E_BASE_URL


@pytest.fixture(scope="session")
def browser():
    """无头 Chromium 实例,会话级复用。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, base_url: str):
    """每个用例一个页面,打开首页并等待首屏。"""
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(base_url, wait_until="domcontentloaded")
    yield page
    page.close()


def pytest_collection_modifyitems(config, items) -> None:
    """自动为 tests/e2e 下的用例打上 e2e marker,默认质量门通过 -m 'not e2e' 排除。"""
    prefix = os.path.join("tests", "e2e")
    for item in items:
        if item.path.as_posix().startswith(prefix):
            item.add_marker(pytest.mark.e2e)
