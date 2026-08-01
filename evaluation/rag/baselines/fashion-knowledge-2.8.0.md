# Fashion Knowledge 2.8.0 检索基线

## 基线信息

- 执行日期：2026-08-01
- 知识发布：`fashion-knowledge-2.8.0`
- Embedding：`BAAI/bge-small-zh-v1.5`
- Chroma Collection：`fashion_knowledge`
- 向量候选数：24
- 最终返回数：3
- 评测问题数：8
- 最终结果：8/8，通过率 100%

## 问题结果

| case_id | 类别 | knowledge_rank | section_rank | 结果 |
|---|---|---:|---:|---|
| material-linen-hot-commute | 面料 | 1 | 3 | PASS |
| material-wool-care | 面料 | 1 | 1 | PASS |
| occasion-interview-dress-code | 场景 | 1 | 1 | PASS |
| occasion-commute-walking | 场景 | 1 | 2 | PASS |
| weather-rain-protection-terms | 天气 | 1 | 2 | PASS |
| weather-wind-outer-layer | 天气 | 1 | 3 | PASS |
| care-unclear-label | 护理 | 1 | 1 | PASS |
| care-washing-drying | 护理 | 1 | 1 | PASS |

## 本轮发现和修正

首次评测为 5/8。诊断显示旧重排器把标签、标题和正文命中作为字典序绝对优先，
远处候选可能因为命中一个通用标签而覆盖强向量结果。羊毛护理的正确向量第一名
`S04` 被推到第四，风天问题中较远的气温章节则被推到前两名。

修正后的重排策略：

1. 使用原始向量排名作为排序主干；
2. 标签、标题和正文词面命中只提供有上限的加分；
3. 允许相邻的明确元数据命中纠正排序；
4. 禁止较远候选仅凭通用词面命中跃升到首位。

第二次评测仍为 5/8，但失败项已经变化。人工阅读实际命中章节后确认：护理标签
`S07`、洗涤 `S01`、降雨 `S11` 等章节正文能够直接支持对应问题，原评测白名单
过窄。因此只把经过正文核对的相关章节加入允许集合，最终得到 8/8。

## 局限

- 当前只有 8 条问题，不能代表全部服装知识和真实用户表达。
- 该基线依赖本地 Embedding 模型与正式 Chroma 数据，不作为默认离线单元测试。
- Hugging Face 未认证访问会产生速率提示，但本次模型成功从本地缓存加载。
- 后续知识版本、Embedding、切分参数或重排权重变化时必须重新建立基线。
- 100% 只表示当前小规模问题集通过，不表示 RAG 已不存在召回质量问题。
