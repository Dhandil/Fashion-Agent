# Agent 需求分析评测

`requirement_cases.json` 保存不含真实用户数据的合成案例，用于评测需求分析节点的
结构化输出和确定性权限收紧结果。

当前覆盖六类边界：

- 通用知识问答
- 信息不足与最小追问
- 衣橱查询和衣橱优先穿搭
- 对既有 Outfit 的局部调整
- 用户明确授权的商品查询
- 明确不购物时的权限边界

`outfit_cases.json` 进一步评测结构化 Outfit，分为：

- `generation`：根据受控衣橱、商品和天气事实生成初稿
- `correction`：对刻意包含完整性、来源或场景错误的初稿执行一次受限修正

它统计首次通过率、修正成功率、来源真实性和最终拒绝数。评测直接调用生成与
修正节点，不经过聊天工具选择，因此指标反映结构化 Outfit 本身的质量。

## 运行方式

在项目根目录执行：

```powershell
python -m scripts.evaluate_requirements
```

Outfit 评测运行方式：

```powershell
python -m scripts.evaluate_outfits
```

保存 Outfit 基线：

```powershell
python -m scripts.evaluate_outfits `
    --output evaluation/agents/baselines/outfits-current.md
```

需要保存可比较的 Markdown 基线时执行：

```powershell
python -m scripts.evaluate_requirements `
    --output evaluation/agents/baselines/requirements-current.md
```

只复测指定失败案例时，可以使用：

```powershell
python -m scripts.evaluate_requirements `
    --case-id shopping-boundary-wardrobe-only
```

该命令会调用当前配置的真实聊天模型，因此会产生外部 API 请求和少量费用。运行前
需要确认 `.env` 中模型配置有效，并按项目权限规则获得联网许可。单元测试只使用假
分析结果验证加载、评分和聚合逻辑，不会访问网络。

## 判定规则

每条案例比较以下路由关键字段：

- `intent`
- `is_sufficient`
- `needs_wardrobe`
- `needs_weather`
- `shopping_intent`
- 必须包含的 `missing_fields`

只有全部关键字段符合预期才算通过。报告同时输出每个类别的通过率，便于区分模型
理解偏差和购物权限边界回归。
