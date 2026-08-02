# 结构化需求分析基线

## 基线信息

- 执行日期：2026-08-02
- 模型：`deepseek-v4-flash`
- 评测案例数：18
- 最终结果：18/18，通过率 100.0%

## 分类结果

| 类别 | 通过数 | 总数 | 通过率 |
|---|---:|---:|---:|
| adjustment | 2 | 2 | 100.0% |
| incomplete | 2 | 2 | 100.0% |
| knowledge | 2 | 2 | 100.0% |
| preference_boundary | 4 | 4 | 100.0% |
| shopping | 2 | 2 | 100.0% |
| shopping_boundary | 2 | 2 | 100.0% |
| wardrobe | 2 | 2 | 100.0% |
| weather_boundary | 2 | 2 | 100.0% |

## 案例结果

| case_id | 类别 | 结果 | 不匹配字段 |
|---|---|---|---|
| knowledge-linen-care | knowledge | PASS | - |
| knowledge-color-principle | knowledge | PASS | - |
| incomplete-no-scenario | incomplete | PASS | - |
| incomplete-weather-location | incomplete | PASS | - |
| wardrobe-weekend-outfit | wardrobe | PASS | - |
| wardrobe-inventory-query | wardrobe | PASS | - |
| adjustment-more-formal | adjustment | PASS | - |
| adjustment-replace-upper | adjustment | PASS | - |
| shopping-explicit-shirt | shopping | PASS | - |
| shopping-explicit-shoes | shopping | PASS | - |
| shopping-boundary-wardrobe-only | shopping_boundary | PASS | - |
| shopping-boundary-advice-only | shopping_boundary | PASS | - |
| preference-avoid-color | preference_boundary | PASS | - |
| preference-avoid-material | preference_boundary | PASS | - |
| preference-current-style-override | preference_boundary | PASS | - |
| weather-provided-hot-commute | weather_boundary | PASS | - |
| weather-query-complete-location | weather_boundary | PASS | - |
| preference-current-positive-and-avoidance | preference_boundary | PASS | - |

## 说明

该报告只保存合成案例的聚合评分和字段差异，不包含 API Key、
请求头、真实用户数据或完整模型响应。
