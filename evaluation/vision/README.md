# 衣物照片识别评测

这里保存人工标注的衣物照片识别案例。照片本身放在被 `.gitignore` 保护的本地
目录中，不提交到 Git；清单只记录相对路径和用于评测的字段。

## 建立案例

复制下面的 JSON 模板为 `cases.json`，再根据照片人工填写 `category`、`colors`
和 `materials`。只填写照片中确实可以确认的字段；无法判断的字段不要加入
`expected`，避免把模型不应猜测的内容当成错误。

```json
{
  "schema_version": "1.0",
  "cases": [
    {
      "case_id": "shirt-1",
      "image_path": "../../test-assets/vision/shirt_1.jpg",
      "expected": {
        "category": "衬衫",
        "colors": ["浅蓝色"]
      }
    }
  ]
}
```

`image_path` 相对于 `cases.json` 所在目录解析。评测只比较结构化字段，不保存
照片、模型原始文本或用户信息；颜色和材质支持人工标注的短语被模型更具体描述
包含的情况，例如标注“蓝色”时可以匹配“浅蓝色”。

## 运行

首次运行只做清单和本地代码检查，不会调用模型。真正评测需要显式授权：

```powershell
python -m scripts.evaluate_wardrobe_vision `
  --manifest evaluation/vision/cases.json `
  --allow-model-call `
  --output evaluation/reports/vision-local.json
```

调用前请确认 API 已启动，并确认本次外部视觉模型调用的费用和数据范围。报告
只包含每个案例的通过状态、命中字段和失败字段。
