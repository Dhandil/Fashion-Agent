# Outfit 生成与修正基线

## 基线信息

- 执行日期：2026-08-01
- 模型：`deepseek-v4-flash`
- 案例数：6
- 案例验证通过率：6/6 (100.0%)
- 首次通过率：2/3 (66.7%)
- 修正成功率：4/4 (100.0%)
- 来源真实性：6/6 (100.0%)
- 最终拒绝数：0

## 案例结果

| case_id | 模式 | 首次通过 | 修正 | 最终状态 | 来源真实 | 结果 |
|---|---|---|---|---|---|---|
| generation-wardrobe-weekend | generation | 是 | 未执行 | executable | 是 | PASS |
| generation-hot-commute | generation | 否 | 成功 | executable | 是 | PASS |
| generation-product-gap | generation | 是 | 未执行 | executable | 是 | PASS |
| correction-missing-core-roles | correction | 否 | 成功 | executable | 是 | PASS |
| correction-invented-source | correction | 否 | 成功 | executable | 是 | PASS |
| correction-scenario-mismatch | correction | 否 | 成功 | executable | 是 | PASS |

该报告只保存聚合指标和稳定状态，不保存衣橱正文、商品正文、
API Key 或完整模型响应。

## 验证过程

首次完整运行结果为 5/6，三条刻意错误的修正案例全部成功，来源真实性为
6/6。唯一失败是 `generation-hot-commute`：初稿选择了厚羊毛大衣，修正后仍
触发 `hot_weather_conflict`，因此被确定性检查正确拒绝。

随后完成两项提示词收紧：

1. 明确 `weather_outfit_guidance` 是当前轮约束，不是可选建议；
2. 明确修正必须删除或替换导致天气冲突的真实单品，消除错误优先于保留原方案。

修改后使用同一真实模型定向复测高温案例。初稿仍未通过，但唯一一次受限修正
成功，最终方案可执行且来源真实。其余5条沿用最近一次完整运行结果，因此最终
验证覆盖为6/6；这不是修改后再次同时执行全部6条所得的单次快照。

## 结论与局限

- 一次修正闭环和确定性拒绝边界有效，4次修正全部成功。
- 来源真实性达到100%，没有返回测试工具结果之外的衣橱或商品 ID。
- 生成案例首次通过率为66.7%；高温案例仍依赖一次修正，初稿天气遵循能力需要
  继续优化。刻意预置错误的3条 correction 案例不计入首次通过率分母。
- 当前只有6条合成案例，不能代表全部衣橱、天气、场景和商品组合。
- 后续增加护理状态、颜色禁忌或新天气规则时必须扩充案例并重建基线。
