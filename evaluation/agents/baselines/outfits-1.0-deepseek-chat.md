# Outfit 生成与修正基线

## 基线信息

- 执行日期：2026-08-02
- 模型：`deepseek-v4-flash`
- 案例数：8
- 案例验证通过率：8/8 (100.0%)
- 首次通过率：5/5 (100.0%)
- 修正成功率：3/3 (100.0%)
- 来源真实性：8/8 (100.0%)
- 最终拒绝数：0

## 案例结果

| case_id | 模式 | 首次通过 | 修正 | 最终状态 | 来源真实 | 结果 |
|---|---|---|---|---|---|---|
| generation-wardrobe-weekend | generation | 是 | 未执行 | executable | 是 | PASS |
| generation-hot-commute | generation | 是 | 未执行 | executable | 是 | PASS |
| generation-product-gap | generation | 是 | 未执行 | executable | 是 | PASS |
| generation-current-avoidance | generation | 是 | 未执行 | executable | 是 | PASS |
| generation-current-preference-override | generation | 是 | 未执行 | executable | 是 | PASS |
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

第一次提示词修改后使用同一真实模型定向复测高温案例。初稿仍未通过，但唯一
一次受限修正成功。随后增加确定性衣橱候选过滤：`unavailable` 单品和高温下的
明显厚重保暖单品不再进入生成、修正模型上下文，完整原始工具事实仍供最终检查。

候选过滤后再次定向复测高温案例，初稿直接通过且没有进入修正。其余5条沿用
最近一次完整运行结果，因此当前组合验证覆盖为6/6；这不是候选过滤后再次同时
执行全部6条所得的单次快照。

随后增加当前轮明确避开颜色和材质的生成案例。系统在模型调用前排除命中避雷项
的衣橱候选，并在生成后使用完整原始工具事实进行确定性复检。该新增案例使用同一
真实模型定向执行，初稿直接通过、没有进入修正且来源真实。因此当前组合验证覆盖
为7/7；这是最近6条验证结果与新增1条定向结果的组合，不是同一次执行全部7条
所得的快照。

随后把长期 Style Profile 转换为不含用户 ID 的结构化快照，并按“当前明确要求
> 长期档案 > 历史反馈”生成唯一有效约束。新增“本轮主动选择黑色覆盖长期避免
黑色”的对称案例，使用同一真实模型定向执行后初稿直接通过、没有进入修正且来源
真实。因此当前组合验证覆盖为8/8；这是最近7条验证结果与新增1条定向结果的
组合，不是同一次执行全部8条所得的快照。

## 结论与局限

- 三条刻意预置错误的案例均在唯一一次修正内成功。
- 来源真实性达到100%，没有返回测试工具结果之外的衣橱或商品 ID。
- 当前5条生成案例均首次通过；刻意预置错误的3条 correction 案例不计入首次
  通过率分母。
- “清洗中”“未干”等原因统一映射为 `unavailable`，没有增加额外领域状态。
- 当前轮明确避雷项不会自动写入长期 Style Profile。
- 当前只有8条合成案例，不能代表全部衣橱、天气、场景和商品组合。
- 后续增加护理状态、颜色禁忌或新天气规则时必须扩充案例并重建基线。
