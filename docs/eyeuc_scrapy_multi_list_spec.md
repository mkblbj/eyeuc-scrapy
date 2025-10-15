## EyeUC 多列表（多游戏）采集方案 v2（仅方案，不实施） ✅

— 目标站点：[`https://bbs.eyeuc.com/down/list`](https://bbs.eyeuc.com/down/list) —

本方案在现有“单 list 采集”基础上，扩展支持一次性抓取多个 `list_id`，并按 `list_id/game` 维度分别产出独立 JSON/JSONL 文件；保留一次性合并导出便于检索与统计。默认纯 Scrapy 抓取；如遇登录态失效或少量动态渲染，再开关式启用 Playwright。🎯

---

## 1) 目标与产物

- 输入：一个或多个 `list_id`（如 `181,182,183`），或一个范围（如 `180-185`）。
- 站点入口：[`/down/list`](https://bbs.eyeuc.com/down/list) 分类导航页；实际抓取入口：`/down/list/{list_id}` 及分页 `.../{page}`；详情页：`/down/view/{post_id}`。
- 抓取范围：每个 `list_id` 下所有分页与详情页。
- 数据字段（每个模组）
  - `list_id`：列表/游戏 ID（如 181）
  - `game`：游戏名称（列表页标题/面包屑解析；解析不到回退 `list_{id}`）
  - `title`：标题
  - `cover_image`：封面图链接
  - `images`：正文图片链接数组（过滤表情/小图标）
  - `intro`：简介（纯文本）
  - `content_html`：正文 HTML（保留格式，适度清洗噪声）
  - `downloads`：下载链接数组（站内附件与外链）
  - `detail_url`、`list_url`：溯源
- 产物：每个 `list_id` 单独 1 份或多份 JSON 文件（默认 JSONL 更稳；也支持 JSON 数组）。文件名包含 `list_id/game/时间戳`。可选同时导出“合并总文件”。📦

---

## 2) 总体方案（架构与职责）

- 单 Spider，多入口：
  - 通过 `list_ids=181,182` 或 `list_range=180-185` 指定抓取范围；函数 `expand_list_ids()` 统一解析、去重、排序。
  - `start_requests()` 为每个 `list_id` 发起起始请求，并以 `meta={cookiejar: list_id, list_id: lid}` 贯穿全流程。
- 会话隔离：
  - 每个 `list_id` 绑定独立 `cookiejar`，避免一个列表异常污染其它列表；便于排障。
- 解析策略：
  - `game` 名优先从 H1/title/面包屑提取（正则归一化 `NBA 2Kxx`），解析不到则回退 `settings` 静态映射，再兜底 `list_{id}`。
  - 列表页抽取 `/down/view/` 详情链接，页内集合去重；第一页解析最大页码后顺序翻页。
  - 详情页抽取标题、封面、正文图片、简介、正文 HTML、下载链接；字段缺失返回空值，保持结构一致。
- 导出策略：
  - 自定义 `PerListJsonPipeline` 按 `list_id/game` 动态分流写入 JSONL（或 JSON 数组）。
  - 保留 Scrapy FEEDS 合并导出（`-O`）用于全量检索/统计。
- 可重入/增量：
  - 以 `detail_url` 为指纹键；结合 `-s JOBDIR=...` 支持断点续跑；后续可引入 `scrapy-deltafetch` 做增量仅抓新帖。🧭

---

## 3) 参数与运行形态（设计）

- Spider 参数：
  - `cookies=cookies.json`：从 JSON 读取并转 `{name: value}` 字典；过滤域名 `.eyeuc.com`/`bbs.eyeuc.com`。
  - `list_ids`：逗号分隔多个 ID（如 `181,182`）。
  - `list_range`：闭区间范围（如 `180-185`）。
  - `use_pw`：`true/false`；默认 `false`。仅在需要 JS 渲染或登录验证流程时启用。
- 设置项（建议默认）：
  - `ITEM_PIPELINES["eyeuc.pipelines.PerListJsonPipeline"] = 300`
  - `PER_LIST_OUTPUT_DIR = "per_list_output"`
  - `PER_LIST_AS_JSONL = True`
  - `ROBOTSTXT_OBEY = False`（站点非标准 robots，按合规策略执行）
  - `RETRY_ENABLED = True`，`RETRY_TIMES = 2~3`
  - `AUTOTHROTTLE_ENABLED = True`，初始/最小延迟 0.2–0.5s，最大延迟 3–8s
  - `CONCURRENT_REQUESTS = 8~16`，`CONCURRENT_REQUESTS_PER_DOMAIN = 4~8`
  - 随机延迟（如中间件）避免节律化请求
- 运行形态：
  - 合并导出：`-O all_{ids_or_range}.json`
  - 断点续跑：`-s JOBDIR=.job/eyeuc_multi`
  - 精准限速：必要时降到 1–2 rps 以越过风控。⚙️

---

## 4) 解析与选择器策略（抗脆弱）

- 列表页：
  - 详情链接：`a[href*='/down/view/']`
  - 翻页：在第 1 页扫描所有链接中匹配 `/down/list/{lid}/(\d+)` 的最大页码；仅使用数字最大值作为上界，忽略“上一页/尾页”等文本按钮。
  - 页内重复：多入口（标题/封面/按钮）导致重复，先做本页集合去重，再交由全局 dupefilter 兜底。
- `game` 名解析：
  - 聚合文本信号：`h1::text`、`<title>`、面包屑 `.crumb/.breadcrumb *::text`；正则提取 `(NBA\s*2K\s*\d{2,4})`，统一大写与空格。
  - 解析失败时查 `settings` 静态映射 `{181:"NBA 2K25", 182:"NBA 2K24"}`；仍失败兜底 `list_{id}`。
- 详情页：
  - 标题：`h1/.title` 优先，回退页面主标题区块。
  - 封面：列表卡片或详情顶部大图优先；不足则取正文第一张图片。
  - 图片：正文 `<img>` 的绝对 URL（补全基准域名），过滤表情/像素小图（例如宽/高 < 40）。
  - 简介：正文首段纯文本或摘要区块；若无则空串。
  - 正文 HTML：保留结构与链接，去除签名/站点脚注等明显噪声（选择器黑名单）。
  - 下载链接：
    - 站内：附件/按钮区，包含 `attachment.php?aid=` 等特征；
    - 外链：正文 `<a>` 中 `href` 以 `http/https` 开头；
    - 统一补全/归一化，去重，并可维护轻量白名单（如 `pan.baidu`, `mega`, `mediafire`, `onedrive`, `github`）。🔗

---

## 5) Cookies 与登录有效性

- `cookies.json` 直接读取，转 `{name: value}`；忽略 `httpOnly/secure/expirationDate` 等无直接影响字段。
- 失效检测：
  - HTTP 302 跳转到登录页/`member.php`/`login` 相关；
  - DOM 包含“登录/注册/权限不足”等关键字；
  - 若失效：
    - 记录失败 `list_id`，建议更新 cookies；
    - 或短期开启 `use_pw=true` 过登录页（仅在必要时）。
- 多 `cookiejar` 的收益：一处会话问题不影响其它 `list_id`，定位成本低。🍪

---

## 6) 并发与风控策略

- 优先启用 AutoThrottle，配合轻度随机延迟；
- 并发建议：8–16（域内 4–8）；遇风控收紧立刻降到 1–2 rps；
- 指纹/UA：可使用旋转 UA，必要时接入轻量代理；
- 遇验证码或异常跳转：记录 HTML 快照，待人工校准选择器或策略。🛡️

---

## 7) 导出策略（按 list 分文件）

- `PerListJsonPipeline`：
  - 以 `list_id`（与解析到的 `game`）为 key 动态打开文件句柄；
  - 默认 JSONL：逐行写入，稳定避免逗号/格式问题；
  - 可选 JSON 数组模式：open 时写入 `[`，close 时补 `]`，中间通过首条标记控制逗号；
  - 文件名：`eyeuc_list{list_id}_{game?}_{YYYYmmdd_HHMMSS}.jsonl`（或 `.json`）。
- FEEDS 合并导出：
  - 保留 `-O` 输出全量合并文件，便于 BI/检索。
- 数据一致性：
  - 字段齐全（即便为空），便于下游结构化处理；
  - `detail_url` 全局唯一（用于去重/增量）。📁

---

## 8) 错误处理、重试与可重入

- 网络/5xx：启用 `RETRY_ENABLED` 与轻度指数退避；
- DOM 解析失败：
  - 选择器双路（CSS + XPath）与轻度正则兜底；
  - 将异常样本（URL + HTML 片段）落盘便于回归；
- 可重入：
  - `-s JOBDIR=.job/eyeuc_multi` 支持断点续跑；
  - dupefilter 持久化（可选）以降低重复抓取。🧯

---

## 9) 可选增强：图片落地（不在 MVP 默认启用）

目标：将封面与正文图片下载到本地/对象存储，JSON 仍保留远程 URL，同时回写本地相对路径，便于离线浏览或交付。🖼️

- 方案选型：
  - 首选 Scrapy `ImagesPipeline`，稳定；按需子类化实现定制路径与字段回写。
- 字段与回写：
  - 输入：沿用 `item['images']` 作为下载源（无需增加 `image_urls`）。
  - 输出：新增 `image_paths`（本地相对路径数组），以及 `cover_image_local`（可选）。
- 存储结构：
  - `IMAGES_STORE/eyeuc/list{list_id}/{game_slug}/{sha1[:2]}/{sha1}.ext`
  - `game_slug` 由 `game` 归一化（空格/斜杠替换为 `_`，长度裁剪）。
- 去重与重试：
  - 依赖 `ImagesPipeline` 内置的基于内容 `sha1` 去重与重试；
  - 允许跨 item 复用已下载图片。
- 并发与限速：
  - 图片下载与页面抓取共享并发，建议下调 `CONCURRENT_REQUESTS_PER_DOMAIN`，并启用 AutoThrottle。
- 产出关系：
  - JSON 同时保留远程 URL 与本地相对路径；失败记录比率目标 < 3%。
- 配置开关（建议在阶段 3 启用）：
  - `ITEM_PIPELINES` 中在 `PerListJsonPipeline` 之前执行图片管道（先拿到本地路径再写 JSON），或之后执行（弱依赖）。

验收标准（图片落地）：
- 抓取 181/182 样本，`image_paths` 数量与 `images` 基本一致；
- 实际磁盘路径满足 `list_id/game` 组织与命名规范；
- JSON 同时包含远程与本地路径字段；失败率低于 3%。✅

---

## 10) 命令示例（演示用）

```bash
# 单个 list（例如 182 → 2K24）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -O all_182.json
# per_list_output/ 目录会生成 eyeuc_list182_<game>_<ts>.jsonl

# 多个 list（逗号分隔）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=181,182,183 -O all_181_182_183.json

# 范围（区间）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_range=180-185

# 断点续跑
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=181,182 -s JOBDIR=.job/eyeuc_multi
```

---

## 11) 验收清单（MVP）

- cookies 有效：列表页无“登录/权限不足”；
- 翻页完整：最大页与 UI 一致，末页不丢；
- 详情无重复：以 `detail_url` 计数去重后为 1；
- 导出文件：每个 `list_id` 生成 1 份 JSONL，字段齐全；
- 合并总文件存在，记录数 ≈ 各 JSONL 总和；
- 日志无高频异常与超时重试。🧪

---

## 12) 阶段性任务（里程碑）

阶段 1（MVP）：多列表抓取 + 按 list 分文件导出
- 解析 `list_ids/list_range` 并多入口启动；
- 列表翻页完整与页内去重；
- 详情解析字段完整（标题/封面/图片/简介/content_html/downloads/source URLs）；
- `PerListJsonPipeline` 按 `list_id/game` 动态分流到 JSONL；
- 支持 `-O` 合并导出；断点续跑 `JOBDIR` 验证；
- cookies 登录有效性检测与失败提示。

阶段 2：稳健性与可维护性
- 限速与并发策略固化（AutoThrottle、随机延迟）；
- 选择器双路（CSS+XPath）与正则兜底；
- 错误分类与重试策略明确（网络/解析/权限）；
- 结构快照（开关）与关键日志（抓取量、失败率、重试率）。

阶段 3（可选增强）：图片落地
- 启用/实现图片 Pipeline（本地/对象存储）；
- `image_paths` 与 `cover_image_local` 字段写回；
- 存储目录与清理策略落地；
- 回归样本与吞吐评估。

Post-MVP backlog（记录，择机）
- ID→游戏名静态映射增强与手动纠偏；
- 增量抓（deltafetch/指纹库）；
- 正文进一步清洗与噪声块剔除；
- 下载链接白/黑名单与归一化策略；
- 远端存储适配（S3/OSS）；
- 基于 `detail_url` 的去重统计与质量报表。🗺️

---

## 参考链接

- EyeUC 资源列表导航页：[https://bbs.eyeuc.com/down/list](https://bbs.eyeuc.com/down/list)


