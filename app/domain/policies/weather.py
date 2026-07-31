"""把天气事实转换为可执行的穿搭约束。"""

from app.domain.entities.weather import WeatherContext


def build_weather_outfit_guidance(
    weather: WeatherContext,
) -> tuple[str, ...]:
    """根据已提供天气字段生成确定性穿搭约束。

    这里只使用真实存在的字段，不推测缺失天气。返回元组便于调用方
    安全复用，也便于单元测试逐条验证规则。
    """

    guidance: list[str] = []
    effective_heat = _maximum_known_temperature(
        weather.temperature_max_c,
        weather.feels_like_c,
    )

    if effective_heat is not None and effective_heat >= 30:
        guidance.append(
            "高温或体感炎热：优先轻薄、透气、吸湿的单品，减少不必要的厚重层次。",
        )

    if weather.temperature_min_c is not None and weather.temperature_min_c <= 10:
        guidance.append(
            "低温：使用可保暖的内层和外层，避免只推荐单薄单品。",
        )

    if (
        weather.temperature_min_c is not None
        and weather.temperature_max_c is not None
        and (weather.temperature_max_c - weather.temperature_min_c) >= 8
    ):
        guidance.append(
            "昼夜温差较大：提供方便穿脱的分层搭配。",
        )

    condition = (weather.condition or "").lower()
    has_precipitation_condition = any(
        keyword in condition
        for keyword in (
            "雨",
            "雪",
            "drizzle",
            "rain",
            "snow",
        )
    )
    has_high_precipitation_probability = (
        weather.precipitation_probability is not None and weather.precipitation_probability >= 50
    )
    if has_precipitation_condition or has_high_precipitation_probability:
        guidance.append(
            "存在明显降水风险：考虑防水外层、防滑耐水鞋履或雨具，避免只给出怕水且难护理的方案。",
        )

    if weather.wind_speed_kph is not None and weather.wind_speed_kph >= 30:
        guidance.append(
            "风力较强：优先防风且便于固定的外层，避免容易被风吹动的宽大或松散单品。",
        )

    if (
        weather.humidity_percent is not None
        and weather.humidity_percent >= 75
        and effective_heat is not None
        and effective_heat >= 26
    ):
        guidance.append(
            "高温高湿：优先快干、透气和不易贴肤的材质。",
        )

    return tuple(guidance)


def _maximum_known_temperature(
    *temperatures: float | None,
) -> float | None:
    """取得已知温度中的最大值；全部缺失时返回 None。"""

    known_temperatures = tuple(
        temperature for temperature in temperatures if temperature is not None
    )
    if not known_temperatures:
        return None
    return max(known_temperatures)
