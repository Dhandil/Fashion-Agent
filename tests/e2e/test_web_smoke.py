"""Web 端到端冒烟测试。

覆盖最基础的用户路径:首页加载、衣橱/穿搭/档案等主导航可点击、聊天可发送。
更复杂的业务流(衣橱新增、Outfit 保存、识别上传)依赖真实模型与业务数据,
按需在此目录继续补充。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


def test_home_page_loads(page) -> None:
    """首页可加载,页面有内容且存在应用标题。"""
    assert page.title() == "Fashion-Agent"
    # 首屏应渲染欢迎文案
    page.get_by_text("穿搭方案").first.wait_for(timeout=10000)
    body_text = page.locator("body").inner_text()
    assert "穿搭" in body_text


def test_navigation_links_available(page) -> None:
    """主导航(衣橱/穿搭/档案)可见并可点击。"""
    for label in ("衣橱", "穿搭", "档案"):
        link = page.get_by_role("link", name=label).first
        link.wait_for(timeout=10000)
        link.click()
        # 点击后停留/跳转不报错即可
        page.wait_for_timeout(300)


def test_quick_prompt_clickable(page) -> None:
    """欢迎页快捷提示可点击(触发发送;无后端时页面不应崩溃)。"""
    prompt = page.get_by_role("button", name="从衣橱帮我搭配").first
    prompt.wait_for(timeout=10000)
    prompt.click()
    # 等待发送动作落定:有后端则进入会话,无后端则展示错误提示,均不应白屏
    page.wait_for_timeout(1500)
    body_text = page.locator("body").inner_text()
    assert "穿搭" in body_text or "衣橱" in body_text
