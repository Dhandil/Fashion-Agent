# 结构化需求分析基线

## 基线信息

- 执行日期：2026-08-02
- 模型：`deepseek-v4-flash`
- 评测案例数：15
- 最终验证结果：15/15，通过率 100.0%

## 分类结果

| 类别 | 通过数 | 总数 | 通过率 |
|---|---:|---:|---:|
| adjustment | 2 | 2 | 100.0% |
| incomplete | 2 | 2 | 100.0% |
| knowledge | 2 | 2 | 100.0% |
| shopping | 2 | 2 | 100.0% |
| shopping_boundary | 2 | 2 | 100.0% |
| wardrobe | 2 | 2 | 100.0% |
| preference_boundary | 3 | 3 | 100.0% |

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

## 说明

该报告只保存合成案例的聚合评分和字段差异，不包含 API Key、
请求头、真实用户数据或完整模型响应。

## 验证过程

首次完整评测为 10/12。诊断后完成两项修正：

1. 对全新完整穿搭缺少使用场景的情况增加确定性最小追问；
2. 将“调整上一套穿搭需要重新确认衣橱可用性”写回案例预期。

第二次完整评测为 11/12，唯一失败是模型把“周末”表达判定为仍缺少场景。
随后增加对称归一化：当原文已有明确使用情境，且模型唯一缺失字段是
`scenario` 时恢复为充分；地点、天气等其他缺口不会被放行。

修改后对唯一失败案例 `shopping-boundary-wardrobe-only` 使用同一真实模型进行
定向复测并通过。其余 11 条沿用最近一次完整评测结果，因此最终验证覆盖为
12/12；这不是最后一次同时执行 12 条所得的单次快照。

随后增加 3 条当前轮偏好边界案例，覆盖明确避免颜色、明确避免材质，以及当前轮
避免风格覆盖同轮正向风格表达。三条案例使用同一真实模型定向执行并全部通过。
因此当前组合验证覆盖为 15/15；这是最近一次 12 条验证结果与新增 3 条定向结果
的组合，不是同一次执行全部 15 条所得的快照。

## 局限

- 当前只有 15 条合成案例，100% 不代表需求理解不存在其他错误。
- 模型输出存在波动，确定性权限和充分度规则仍需保留。
- 新增意图、路由字段或产品边界后必须扩充案例并重新建立基线。
