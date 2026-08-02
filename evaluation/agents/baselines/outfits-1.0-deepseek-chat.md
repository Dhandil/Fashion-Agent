# Outfit 生成与修正基线

## 基线信息

- 执行日期：2026-08-02
- 模型：`deepseek-v4-flash`
- 案例数：14
- 案例通过率：14/14 (100.0%)
- 首次通过率：5/5 (100.0%)
- 修正成功率：4/4 (100.0%)
- 来源真实性：14/14 (100.0%)
- 最终拒绝数：5

## 案例结果

| case_id | 模式 | 首次通过 | 缺口 | 修正 | 最终状态 | 来源真实 | 结果 |
|---|---|---|---|---|---|---|---|
| generation-wardrobe-weekend | generation | 是 | 否 | 未执行 | executable | 是 | PASS |
| generation-hot-commute | generation | 是 | 否 | 未执行 | executable | 是 | PASS |
| generation-product-gap | generation | 是 | 否 | 未执行 | executable | 是 | PASS |
| generation-current-avoidance | generation | 是 | 否 | 未执行 | executable | 是 | PASS |
| generation-current-preference-override | generation | 是 | 否 | 未执行 | executable | 是 | PASS |
| generation-wardrobe-gap-no-shopping | generation | 否 | 是 | 未执行 | rejected | 是 | PASS |
| generation-wardrobe-gap-shopping-allowed | generation | 否 | 是 | 未执行 | rejected | 是 | PASS |
| generation-avoidance-removes-all | generation | 否 | 是 | 未执行 | rejected | 是 | PASS |
| correction-missing-core-roles | correction | 否 | 否 | 成功 | executable | 是 | PASS |
| correction-invented-source | correction | 否 | 否 | 成功 | executable | 是 | PASS |
| correction-scenario-mismatch | correction | 否 | 否 | 成功 | executable | 是 | PASS |
| generation-unavailable-laundry-gap | generation | 否 | 是 | 未执行 | rejected | 是 | PASS |
| generation-high-heat-removes-only-upper | generation | 否 | 是 | 未执行 | rejected | 是 | PASS |
| correction-hot-weather-conflict | correction | 否 | 否 | 成功 | executable | 是 | PASS |

该报告只保存聚合指标和稳定状态，不保存衣橱正文、商品正文、
API Key 或完整模型响应。
