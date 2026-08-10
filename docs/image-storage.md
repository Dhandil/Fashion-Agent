# 衣物照片存储与 `image_url` 生命周期方案

## 1. 目标与边界

衣物照片属于用户私有数据，存储方案需要同时满足：

- 图片默认私有，不能通过公开 URL 访问；
- 应用服务不长期保存 Base64 和图片字节；
- 图片对象与用户、衣橱单品严格隔离；
- 识别草稿未经用户确认不能成为衣橱事实；
- 用户删除衣橱单品后，关联图片可以异步、可审计地清理；
- 本地开发不强制引入新的外部服务，生产环境可以替换为 S3、OSS 或其他
  S3-compatible Object Storage。

当前版本同时支持旧的 Base64 识别和本地文件卷上传流程。照片元数据写入
`wardrobe_image_assets`，原始字节保存到受保护的本地文件卷；识别结果仍然必须
经过用户确认后才能写入衣橱。

## 2. 推荐架构

```text
Browser
  │ 1. 创建上传凭证
  ▼
Fashion-Agent API ─── PostgreSQL: wardrobe_image_assets 元数据
  │ 2. 返回本地上传地址（本地版由 API 接收 PUT）
  ▼
Local Protected File Volume
  │ 3. 浏览器上传原始字节，服务端校验后原子写入
  ▼
Fashion-Agent API
  │ 4. 完成上传并发起识别
  ▼
Vision Provider → WardrobeItemDraft
  │ 5. 用户确认
  ▼
wardrobe_items.image_asset_id ─── wardrobe_image_assets
```

当前本地实现使用 `LocalWardrobeImageStorage` 和 Docker named volume，禁止公开
目录访问。生产环境可以替换为 S3、OSS 或其他 S3-compatible Provider；替换时
保持同一套资产元数据和用户隔离边界。

## 3. 数据模型

新增 `wardrobe_image_assets` 表（名称可在实现时调整）：

| 字段 | 作用 |
|---|---|
| `image_asset_id` | 应用生成的不可猜测 ID |
| `user_id` | 所属用户，所有查询必须带用户条件 |
| `object_key` | Bucket 内部路径，不向客户端暴露可推断的用户信息 |
| `content_type` | 经过文件头校验后的 `image/jpeg` 或 `image/png` |
| `byte_size` | 服务端确认的实际字节数 |
| `sha256` | 内容去重、完整性和审计校验 |
| `status` | `pending`、`uploaded`、`attached`、`deletion_pending`、`deleted` |
| `created_at` | 资产创建时间 |
| `expires_at` | 未完成上传或未确认草稿的过期时间 |
| `attached_at` | 首次关联衣橱单品的时间 |
| `deleted_at` | 逻辑删除时间 |

`wardrobe_items` 后续新增 `image_asset_id` 外键。现有 `image_url` 暂时保留：

- 写入接口继续接受它，作为迁移期的外部托管地址；
- 新上传流程不再把签名 URL 写入 `image_url`；
- 返回接口中的 `image_url` 改为按请求即时生成的短时 GET URL；
- 迁移完成后，`image_url` 变为响应模型的派生字段，而不是永久事实字段。

## 4. API 生命周期

### 4.1 创建上传凭证

新增接口建议为：

```text
POST /api/v1/wardrobe/images/uploads
```

请求包含声明的格式和文件大小。服务端只接受 JPEG/PNG、限制 5 MB，生成：

- `image_asset_id`；
- 短时本地 PUT 地址（有效期默认 10 分钟；生产 Provider 可替换为 presigned URL）；
- `object_key` 不直接暴露给 UI；
- 上传完成接口地址。

### 4.2 上传与完成确认

```text
PUT /api/v1/wardrobe/images/{image_asset_id}/content
```

前端把原始图片字节 PUT 到该地址。服务端重新校验图片文件头、大小并计算
SHA-256，成功后将资产状态改为 `uploaded`。

```text
POST /api/v1/wardrobe/images/{image_asset_id}/complete
```

完成接口会确认元数据与文件卷中的对象一致，并检查对象确实存在。校验失败时
不允许进入识别流程。

### 4.3 发起识别

识别接口新增 `image_asset_id` 输入，同时保留当前 Base64 输入作为迁移期兼容：

```text
POST /api/v1/wardrobe/recognitions
{
  "image_asset_id": "asset-...",
  "hint": "这是一件夏季衬衫"
}
```

视觉 Provider 读取私有对象并在内存中构造 Data URI；日志、Trace 和异常信息不
记录图片内容、Base64、对象存储密钥或模型原始响应。识别只返回草稿，不改变
`wardrobe_image_assets.status` 为 `attached`。

### 4.4 用户确认并写入衣橱

用户修改草稿后调用现有 `POST /api/v1/wardrobe`，请求携带 `image_asset_id`。
服务端在同一数据库事务中：

1. 校验图片资产属于当前用户且状态为 `uploaded`；
2. 创建或更新衣橱单品；
3. 将资产标记为 `attached`；
4. 提交事务。

任何一步失败都回滚数据库状态，图片对象由异步清理任务处理，不在请求内做
不可逆删除。

## 5. `image_url` 生命周期

| 阶段 | URL 行为 | 资产状态 |
|---|---|---|
| 上传前 | 不生成访问 URL | `pending` |
| 上传中 | 仅返回短时 PUT URL | `pending` |
| 上传完成 | 仅服务端确认，前端需要预览时生成短时 GET URL | `uploaded` |
| 识别草稿 | 草稿可携带短时预览 URL，但不写永久衣橱记录 | `uploaded` |
| 用户确认 | 衣橱记录保存 `image_asset_id`，每次读取时生成新 GET URL | `attached` |
| 用户删除衣橱 | 标记待删除，短期保留用于恢复和审计 | `deletion_pending` |
| 清理任务完成 | 删除对象和元数据，历史 URL 全部失效 | `deleted` |

本地版 `content_url` 是需要当前用户身份的 API 地址，不是公开文件 URL；前端
通过带 `X-User-ID` 的 API 请求访问。生产对象存储 Provider 应返回短时签名 GET
URL。前端不得缓存永久 URL；React Query 缓存中只保存当前页面需要的短时地址。

## 6. 清理与保留策略

- `pending` 超过 10 分钟：删除未完成的上传凭证和对象；
- `uploaded` 超过 24 小时仍未关联衣橱：标记并清理，避免识别草稿产生孤儿图片；
- `attached` 随衣橱单品保留；
- 用户删除单品后进入 `deletion_pending`，建议保留 7 天后物理删除；
- 用户删除账户时立即标记全部资产，后台任务优先清理对象，再清理元数据；
- 清理任务必须幂等、可重试，并记录匿名资产 ID、结果和耗时，不记录 URL 或图片。

## 7. 安全与可靠性要求

- Bucket 私有、服务端加密，生产环境使用最小权限的读写角色；
- 对象 Key 使用随机资产 ID，不使用原始文件名、用户 ID 或可推断路径；
- 上传前后都校验文件头，不能只相信浏览器声明的 MIME 类型；
- 限制尺寸、字节数和请求频率，必要时增加病毒扫描或内容安全检查；
- 服务端不抓取任意 `image_url`，避免 SSRF；迁移期外部地址只允许 HTTPS，且不
  由服务器主动下载；
- 识别失败时资产仍可重试，不自动创建衣橱单品；
- 删除、过期、确认和识别都写入匿名审计事件。

## 8. 分阶段实施

1. **已完成**：资产实体、PostgreSQL 表、本地文件卷适配器、上传/完成/读取
   接口，以及前端直传和 `image_asset_id` 识别；Base64 保留为兼容路径；
2. **下一阶段**：补充资产过期、孤儿图片和衣橱删除后的异步清理任务；
3. **生产阶段**：增加 S3-compatible Provider，并在需要时接入 MinIO；
4. **迁移阶段**：逐步停止新业务写入永久外部 `image_url`，再移除旧兼容路径。

本地实现不需要新增对象存储镜像、云 Bucket 或密钥；照片文件位于被 `.gitignore`
保护的 `data/uploads/`（宿主机开发）或 `fashion_agent_wardrobe_uploads`
（Docker）中。
