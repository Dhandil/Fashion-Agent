"""天气穿搭决策规则测试。"""

from app.domain.entities.weather import WeatherContext
from app.domain.policies.weather import (
    build_weather_outfit_guidance,
)


def test_weather_guidance_combines_relevant_risks() -> None:
    """验证高温、高湿、降雨、大风和温差分别产生明确约束。"""

    weather = WeatherContext(
        location="上海",
        target_date="2026-08-01",
        condition="阵雨",
        temperature_min_c=24,
        temperature_max_c=34,
        feels_like_c=38,
        precipitation_probability=70,
        humidity_percent=82,
        wind_speed_kph=35,
        source="api",
    )

    guidance = build_weather_outfit_guidance(
        weather,
    )
    combined_guidance = "\n".join(guidance)

    assert "高温或体感炎热" in combined_guidance
    assert "昼夜温差较大" in combined_guidance
    assert "明显降水风险" in combined_guidance
    assert "风力较强" in combined_guidance
    assert "高温高湿" in combined_guidance


def test_weather_guidance_uses_only_available_facts() -> None:
    """验证温和天气且字段有限时不会补造额外风险。"""

    weather = WeatherContext(
        location="昆明",
        target_date="2026-08-01",
        temperature_max_c=24,
        source="user_provided",
    )

    assert (
        build_weather_outfit_guidance(
            weather,
        )
        == ()
    )


def test_weather_guidance_adds_cold_layering() -> None:
    """验证低温会要求保暖分层。"""

    weather = WeatherContext(
        location="哈尔滨",
        target_date="2026-12-01",
        temperature_min_c=-12,
        temperature_max_c=-4,
        source="api",
    )

    guidance = build_weather_outfit_guidance(
        weather,
    )

    assert any("低温" in item for item in guidance)
