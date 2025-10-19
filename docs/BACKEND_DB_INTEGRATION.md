## EyeUC 数据库对接指南（FastAPI/React）

这份文档面向后端/全栈同学，说明我们已抓取的数据范围、数据库表字段、连接方式、导入与更新流程、典型查询与接口示例，便于直接对接现有后端使用。🙂

---

### TL;DR
- 已抓取实体：`lists`（游戏/集合）、`mods`（资源）、`images`（图集）、`versions`（分支）、`downloads`（附件）
- 导入方式：增量、幂等（`INSERT ... ON DUPLICATE KEY UPDATE`），可重复执行，不会产生重复数据
- 连接方式：通过环境变量（.env）读取；脚本支持自动加载 `.env`
- 直接可用查询：列表/分页/筛选、详情聚合、下载元数据；下方有 SQL 示例

---

## 1. 数据来源与采集范围

- 站点资源页面：列表页（含分页）、详情页（含分支版本与附件）
- 去重策略：完全禁用 Scrapy 全局指纹去重，确保多分支/多 AJAX 请求不被过滤
- 批量策略：支持分批页抓取与合并（按 list_id 与页码范围输出），便于并行/失败重启
- 文件输出：`per_list_output/eyeuc_list{list_id}[_game]_p{start}-{end}_{ts}.jsonl`

单条资源（mod）JSON 结构（示例：字段会按实际页面有增减）：

```json
{
  "mid": 31650,
  "list_id": 193,
  "game": "NBA2K26",
  "category": "照片",
  "title": "示例标题 / v1.0",
  "cover_image": "https://.../cover.png",
  "images": ["https://.../1.png", "https://.../2.png"],
  "intro": "<p>资源简介 HTML</p>",
  "metadata": {
    "author": "作者名",
    "author_url": "https://...",
    "publisher": "发布者",
    "publisher_url": "https://...",
    "views": 1234,
    "downloads": 567,
    "likes": 8,
    "created_at": "2025-10-16 12:34:56",
    "last_updated": "2025-10-17 18:22:00"
  },
  "versions": [
    {
      "vid": 47196,
      "version": "v1.0",
      "intro": "版本说明...",
      "stats": { "updated_at": "2025-10-17 18:22:00", "views": 321, "downloads": 45 },
      "downloads": [
        { "type": "internal", "fileid": 12345, "filename": "mod.7z", "size": "21.3MB" },
        { "type": "external", "url": "https://pan.baidu.com/...", "note": "百度网盘" }
      ]
    }
  ],
  "detail_url": "https://bbs.eyeuc.com/down/view/31650",
  "list_url": "https://bbs.eyeuc.com/down/list/193/1"
}
```

---

## 2. 数据库表结构概览（MySQL）

关系图（简述）：
- `lists (1) ──< mods (N)`
- `mods (1) ──< images (N)`
- `mods (1) ──< versions (N)`
- `versions (1) ──< downloads (N)`，同时 `downloads.mod_id` 亦外键到 `mods`

所有表均使用 `utf8mb4` + `utf8mb4_unicode_ci`。

### 2.1 lists（游戏/集合）
- 主键：`list_id`
- 字段：
  - `game`：游戏名称（如 NBA2K26）
  - `slug`：URL 友好名（预留，目前为空，可由后端根据 `game` 生成，如 `nba-2k26`）

### 2.2 mods（资源）
- 主键：`mid`；外键：`list_id → lists.list_id`
- 关键字段：
  - `list_id`：所属列表
  - `category`：分类（如：工具/名单&人补/面补&身形/照片/球衣/球场/球鞋/画质/其他）
  - `title`、`intro_html`、`cover_image`
  - 作者/发布者：`author`、`author_url`、`publisher`、`publisher_url`
  - 统计：`views`、`downloads`、`likes`
  - 时间：`created_at`、`last_updated`（已自动转换相对时间为绝对时间，如"昨天 17:37" → "2025-10-18 17:37"）
  - 链接：`detail_url`、`list_url`
  - `raw_json`：原始 JSON 备份（LONGBLOB）
  - 系统：`created_ts`、`updated_ts`
- 索引：`idx_list_id`、`idx_category`、`idx_author`、`idx_created_at`、`fidx_title(FTS)`

### 2.3 images（图集）
- 唯一键：`(mod_id, url(191))`
- 字段：`mod_id`、`url`、`idx`

### 2.4 versions（分支）
- 唯一键：`(mod_id, vid)`
- 字段：`mod_id`、`vid`、`version_name`、`is_default`、`intro`、`updated_at`、`views`、`downloads`

### 2.5 downloads（附件）
- 唯一键：`(mod_id, version_id, fileid, url(191))`
- 字段：
  - `type`：`internal | external | forum_redirect | empty | unknown`
  - internal：`fileid`、`filename`、`size`
  - external/redirect：`url`、`note`
  - `version_label`：版本标签（与 `versions.version_name` 可不同步）

---

## 3. 连接与配置

与现有数据库一致

---


## 5. 典型 SQL 查询（可直接用于后端 API）

### 5.1 列表 API（分页 + 条件）

按列表/分类筛选，带一张封面（优先 `mods.cover_image`，否则取 `images.idx=0` 的第一张）：

```sql
-- :list_id, :category, :keyword, :page, :size
SELECT 
  m.mid, m.list_id, m.category, m.title, m.views, m.downloads, m.likes,
  COALESCE(m.cover_image, (
    SELECT i.url FROM images i WHERE i.mod_id = m.mid ORDER BY i.idx ASC LIMIT 1
  )) AS cover
FROM mods m
WHERE m.list_id = :list_id
  AND (:category IS NULL OR m.category = :category)
  AND (:keyword IS NULL OR MATCH(m.title) AGAINST(:keyword IN NATURAL LANGUAGE MODE))
ORDER BY COALESCE(m.last_updated, m.created_at) DESC
LIMIT :size OFFSET (:page - 1) * :size;
```

### 5.2 详情 API（基础信息 + 图集 + 版本 + 附件）

建议分 3~4 次查询聚合（更清晰、便于缓存）：

```sql
-- 基础信息
SELECT * FROM mods WHERE mid = :mid;

-- 图集
SELECT url, idx FROM images WHERE mod_id = :mid ORDER BY idx ASC;

-- 版本
SELECT id AS version_id, vid, version_name, is_default, intro, updated_at, views, downloads
FROM versions WHERE mod_id = :mid ORDER BY (is_default DESC), updated_at DESC, id DESC;

-- 附件（按版本）
SELECT id, version_id, type, fileid, filename, size, url, note, version_label
FROM downloads WHERE mod_id = :mid ORDER BY version_id ASC, id ASC;
```

### 5.3 分类聚合 / 统计

```sql
-- 按分类计数
SELECT category, COUNT(*) AS cnt FROM mods WHERE list_id = :list_id GROUP BY category ORDER BY cnt DESC;

-- 最新/热门（示例：按下载量）
SELECT mid, title, downloads FROM mods WHERE list_id = :list_id ORDER BY downloads DESC LIMIT 20;
```

### 5.4 全文检索（标题）

```sql
SELECT mid, title FROM mods
WHERE MATCH(title) AGAINST(:keyword IN NATURAL LANGUAGE MODE)
ORDER BY (downloads + views) DESC
LIMIT 50;
```

---

## 6. 下载直链对接建议（后端实现）

目标：前端点击附件 → 后端根据 `downloads` 元数据判断：
- `type='external'|'forum_redirect'`：直接 302 跳转到 `url`
- `type='internal'`：调用直链生成逻辑（可复用 `fetch_direct_links.py` 的内部流程），以用户 Cookie 拉取直链，再以流方式代理给前端

伪代码（FastAPI 思路）：

```python
@app.get('/downloads/{mid}/{version_id}/{download_id}')
def proxy_download(mid: int, version_id: int, download_id: int):
    dl = get_download(mid, version_id, download_id)
    if dl.type in ('external', 'forum_redirect'):
        return RedirectResponse(url=dl.url)
    # internal：按站点流程生成直链，然后 StreamingResponse 代理
    # 需要用户会话 Cookie；注意限速与错误兜底
```

注意：直链存在时效/鉴权，必须使用用户 Cookie 调用；务必做好限流与失败重试。

---

## 7. 关键约束与幂等策略

- `mods.mid` 为主键；重复导入时使用 `ON DUPLICATE KEY UPDATE` 更新字段
- `versions` 唯一键 `(mod_id, vid)`；`downloads` 唯一键 `(mod_id, version_id, fileid, url(191))`；`images` 唯一键 `(mod_id, url(191))`
- 文本 URL 采用 `(191)` 前缀作为唯一索引，兼顾 MySQL 限制与防重
- `downloads.type` 枚举：`internal/external/forum_redirect/empty/unknown`
- `category` 来源于详情页 `<meta keywords>`/`<title>` 解析，极少数页面可能缺失（可为空）

---

## 8. 性能与索引建议

- 常用筛选：`idx_list_id`、`idx_category`、`idx_created_at`
- 文本检索：`FULLTEXT(title)`（ngram 分词已启用）
- 分页：`LIMIT + OFFSET`；高并发建议 keyset pagination（基于索引字段）

---

如果你需要我直接给出 FastAPI 的 3 个接口骨架（列表、详情、下载直链代理），我可以在此文档基础上继续补齐代码示例。🚀


