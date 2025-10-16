## EyeUC 多列表采集 · 实施清单（Notepad）

— 目标站点：[https://bbs.eyeuc.com/down/list](https://bbs.eyeuc.com/down/list) —

本清单用于基于 v2 规格文档（`eyeuc_scrapy_multi_list_spec.md`）落地开发与验收，默认只讨论方案与任务，不包含实施代码。✅

---

### 图例

- ⏸️ 待开始  · ⏳ 进行中  · ✅ 已完成  · ❌ 已跳过  · 🔍 待审阅  · ⚠️ 风险关注

---

## 阶段 1（MVP）：多列表抓取 + 按 list 分文件导出

### 1.1 项目准备与依赖
- [x] 创建虚拟环境并安装依赖（`scrapy>=2.10`，可选：`scrapy-playwright`）✅
- [x] 校验 `cookies.json` 登录有效性（人工在浏览器访问 `down/list/182`）✅
- [x] 设置基础限速与重试（AutoThrottle、RETRY）✅

### 1.2 Spider 多入口（多 list）
- [x] 新/改 `spiders/eyeuc_mods.py` 支持参数：`cookies`、`list_ids`、`list_range`、`use_pw` ✅
- [x] 实现 `expand_list_ids(list_ids, list_range)`：合并/去重/排序，空参数默认 `[182]` ✅
- [x] `start_requests()`：为每个 `list_id` 发起起始请求；`meta={cookiejar:list_id, list_id:lid}` ✅
- [x] `use_pw` 为开关，不默认启用 Playwright（仅必要时）✅
- ⚠️ 注意：list_range 因站点编号不连续，实际用处有限，建议使用 list_ids

### 1.3 列表解析与翻页
- [x] `_guess_game_name()`：从 H1/title/面包屑聚合文本，用 `(NBA\s*2K\s*\d{2,4})` 归一化 ✅
- [x] `parse_list()`：抽取 `/down/view/` 详情链接，页内 `seen` 集合去重 ✅
- [x] 仅在第一页扫描 `/down/list/{lid}/(\d+)` 取最大页 `max_page` ✅
- [x] 生成第 2..N 页请求（同 `cookiejar` & `list_id`）✅

### 1.4 详情解析
- [x] 字段：`list_id`、`game`、`title`、`cover_image`、`images`、`intro`、`content_html`、`downloads`、`detail_url`、`list_url` ✅
- [x] `title`：`h1/.title` 优先，兜底主标题区 ✅
- [x] `cover_image`：从列表页提取（去缩略图后缀） ✅
- [x] `images`：正文 `<img>` 绝对 URL，去缩略图后缀获取大图 ✅
- [x] `downloads`：提取元数据（mid/vid/fileid/filename/size），不获取直链（避免时效性） ✅
- [x] 所有字段缺失使用空值（不跳过 item） ✅

#### 1.4.x 下载直链获取（优化方案：两阶段分离）✅
- [x] **设计理念**：爬虫只抓元数据，直链按需动态生成（避免时效性问题） ✅
- [x] **阶段 1：爬虫**（默认模式，`direct_dl=false`） ✅
  - [x] 解析 `_data` 变量取 `mid/vid/formhash` ✅
  - [x] 请求 AJAX：`down.php?mod=view&mid={mid}&vid={vid}&show=todownload` ✅
  - [x] 提取元数据：`type, mid, vid, fileid, filename, size, version` ✅
  - [x] 输出格式：`downloads: [{type: 'internal', mid, vid, fileid, filename, size, version}]` ✅
  - [x] 类型判断：有文件 → `internal`；无文件 → `redirect`；外链 → `external` ✅

- [x] **阶段 2：动态获取脚本**（`fetch_direct_links.py`） ✅
  - [x] 用法：`--mid 31047` 或 `--json output.json` 或 `--mids 31047,31439` ✅
  - [x] 用户提供自己的 `cookies.json`（按需获取，分布式下载） ✅
  - [x] 实时生成直链：请求 `down.php?mod=buy&mid={mid}&vid={vid}&fileid={fileid}&hash={formhash}` ✅
  - [x] 捕获 302 重定向，提取 `resource-file.eyeassets.com` 直链 ✅
  - [x] 解析过期时间：从 `auth_key` 时间戳提取 `expires_at` ✅
  - [x] 输出格式：JSON，包含 `{mid: {downloads: [{fileid, filename, size, direct_url, expires_at}]}}` ✅

- [x] **验收** ✅
  - [x] 爬虫输出包含完整元数据（mid/vid/fileid/filename/size） ✅
  - [x] 动态脚本成功生成直链（测试 mid=31047） ✅
  - [x] 批量处理：从 JSON 读取多个 mid 并获取直链 ✅

### 1.5 导出：按 list 分文件 + 合并文件
- [x] 实现 `PerListJsonPipeline`（JSONL 默认；可切换 JSON 数组） ✅
- [x] 文件命名：`eyeuc_list{list_id}_{game?}_{YYYYmmdd_HHMMSS}.jsonl` ✅
- [x] `settings.py`： ✅
  - [x] `ITEM_PIPELINES = {"eyeuc.pipelines.PerListJsonPipeline": 300}` ✅
  - [x] `PER_LIST_OUTPUT_DIR = "per_list_output"`，`PER_LIST_AS_JSONL = True` ✅
- [x] FEEDS `-O` 合并导出保留（可选） ✅

### 1.6 运行与验收
- [x] 单 list 验证：`scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172` ✅
- [x] 多 list 验证：`scrapy crawl eyeuc_mods -a list_ids=172,93 -O test_all_172_93.json` ✅
- [ ] 区间验证：`scrapy crawl eyeuc_mods -a list_range=180-185` (跳过，编号不连续)
- [ ] 断点续跑：`-s JOBDIR=.job/eyeuc_multi` (Stage 2)

验收标准（MVP）：
- [x] cookies 有效：列表页无"登录/权限不足"提示 ✅
- [x] 翻页完整：末页不丢；`max_page` 与 UI 一致 ✅
- [x] 详情去重：按 `detail_url` 计数无重复 ✅
- [x] 每个 `list_id` 产出 1 份 JSONL，字段齐全 ✅
- [x] 合并文件存在，记录数 ≈ 各 JSONL 总和 ✅

---

## 阶段 2：稳健性与可维护性

### 2.1 并发与风控
- [x] AutoThrottle：初始/最小延迟 0.3s，最大 6s ✅
- [x] 并发：`CONCURRENT_REQUESTS=12`，域内 `6` ✅
- [x] 随机延迟中间件（避免节律化，0.1-0.4s）✅

### 2.2 选择器与兜底
- [x] 关键块采用选择器兜底方法 `_extract_with_fallback` ✅
- [x] DOM 改版监控：失败样本落盘（`ParseErrorMonitorMiddleware`）✅

### 2.3 错误与重试
- [x] 分类记录网络/解析/权限错误（`EnhancedRetryMiddleware`）✅
- [x] 关键指标日志：抓取量、失败率、重试率、平均响应时延 ✅

### 2.4 可重入与指纹
- [x] `JOBDIR` 可重入验证（测试通过）✅
- [x] 指纹键：`detail_url`（Scrapy 默认）✅

验收标准（阶段 2）：
- [x] 长跑稳定无崩溃，成功率 100% ✅
- [x] 选择器兜底机制就绪 ✅
- [x] 关键日志指标可用，便于回归 ✅

---

2. 生产部署
     - 定时任务
     - 监控告警
     - 数据入库

## 阶段 3（可选增强）：图片落地（ImagesPipeline）

### 3.1 管道实现
- [ ] 新建 `PerListImagesPipeline` 继承 `ImagesPipeline`
- [ ] `get_media_requests` 从 `item['images']` 读取 URL（无需 `image_urls`）
- [ ] `file_path` 组织：`IMAGES_STORE/eyeuc/list{list_id}/{game_slug}/{sha1[:2]}/{sha1}.ext`
- [ ] `item_completed` 写回 `image_paths`、`cover_image_local`（可选）

### 3.2 配置与并发
- [ ] `IMAGES_STORE = "images"`（或 S3/OSS）
- [ ] `MEDIA_ALLOW_REDIRECTS=True`，`DOWNLOAD_TIMEOUT=30`
- [ ] 降低域内并发（图片下载与页面抓取共享并发）
- [ ] `ITEM_PIPELINES` 顺序：建议图片管道在 JSON 写入之前

验收标准（阶段 3）：
- [ ] 181/182 样本 `image_paths` 数量 ≈ `images` 数量
- [ ] 磁盘路径符合 `list_id/game_slug` 组织
- [ ] JSON 同时包含远程 URL 与本地路径；失败率 < 3%

---

## 快速命令（演示）

```bash
# 单个 list（例如 182 → 2K24）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -O all_182.json

# 多个 list（逗号分隔）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=181,182,183 -O all_181_182_183.json

# 范围（区间）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_range=180-185

# 断点续跑
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=181,182 -s JOBDIR=.job/eyeuc_multi
```

---

## 风险与对策
- ⚠️ Cookie 过期/掉线：检测 302/登录提示 → 提示更新 cookies 或临时 `use_pw=true`
- ⚠️ DOM 改版：双路选择器 + HTML 快照落盘，快速修复
- ⚠️ 反爬收紧：降并发/增延迟/启用 AutoThrottle；必要时限到 1–2 rps
- ⚠️ 外链不可达：仅记录链接不下载，避免重试风暴

---

## 里程碑检查

### MVP 完成
- [x] 多入口抓取与翻页完整 ✅
- [x] 字段齐全与去重通过 ✅
- [x] 按 list JSONL 产出 + 合并文件可用 ✅

### 稳健性完成
- [x] 限速/并发策略固化 ✅
- [x] 选择器兜底与日志指标就绪 ✅

### 图片落地（可选）
- [ ] 图片管道启用并通过样本验收

---

## 角色与计划（可填写）
- Owner：
- 审阅人：
- 计划起止：
- 目标版本：

---

## 参考
- EyeUC 资源列表导航页：[https://bbs.eyeuc.com/down/list](https://bbs.eyeuc.com/down/list)
- 规格文档：`docs/eyeuc_scrapy_multi_list_spec.md`


