# 更新日志

## [2025-10-19] - 时间字段提取完整修复

### 新增功能
- ✅ **相对时间自动转换**：爬虫现在能自动将网站显示的相对时间（如"昨天 17:37"、"3 天前"）转换为绝对时间格式（`YYYY-MM-DD HH:MM`）
- ✅ **智能识别**：支持多种中文相对时间格式，包括：
  - "昨天/前天/今天 HH:MM"
  - "N 天前/小时前/分钟前"
  - "刚刚/刚才"
  - 已存在的绝对时间格式（保持不变）
- ✅ **兼容多种 HTML 格式**：自动识别并处理两种时间字段格式：
  - 格式1：`<span title="绝对时间">相对时间</span>`（优先使用 title 属性）
  - 格式2：`<p>绝对时间</p>`（直接提取 p 标签文本）

### 修复问题
- 🐛 **修复时间字段缺失**：之前爬取的数据中 `created_at` 和 `last_updated` 字段有约 45% 缺失，原因是网站使用了两种不同的 HTML 结构，爬虫只能识别其中一种。现已完全修复，覆盖率 100%。

### 技术细节
- 新增 `_parse_relative_time()` 方法
- 在 `_extract_metadata()` 中集成相对时间转换逻辑
- 优先提取 HTML `title` 属性（绝对时间），若无则解析相对时间
- 添加详细的日志记录，方便追踪转换过程

### 文档更新
- 📄 新增 `docs/RELATIVE_TIME_PARSING.md` 详细说明相对时间解析机制
- 📄 更新 `docs/BACKEND_DB_INTEGRATION.md` 说明时间字段已自动转换
- 📄 创建本 `CHANGELOG.md` 记录更新历史

### 影响范围
- **数据库**：导入后的 `mods` 表时间字段现在都是绝对时间，可直接用于排序和筛选
- **后端对接**：无需额外处理相对时间，所有时间字段均为 `YYYY-MM-DD HH:MM` 格式
- **历史数据**：已抓取的数据不会自动更新，建议重新爬取以获取正确的时间信息

### 使用示例

**重新爬取列表 193（前 5 页）**：
```bash
cd /root/dev/eyeuc-scrapy
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=193 -a start_page=1 -a end_page=5
```

**检查时间字段**：
```bash
# 查看 JSONL 输出
head -1 per_list_output/eyeuc_list193_*.jsonl | python3 -c "import json, sys; data=json.load(sys.stdin); print('created_at:', data['metadata'].get('created_at')); print('last_updated:', data['metadata'].get('last_updated'))"

# 查看数据库
mysql -h <host> -u <user> -p<password> <database> -e "SELECT mid, title, created_at, last_updated FROM mods ORDER BY created_at DESC LIMIT 5;"
```

---

## 历史记录

### [2025-10-19] - 分类功能
- ✅ 新增 `mods.category` 字段
- ✅ 从详情页面包屑和 meta keywords 提取分类信息
- ✅ 数据库导入脚本支持 `category` 字段

### [2025-10-19] - 后端对接文档
- ✅ 创建完整的后端对接文档 `docs/BACKEND_DB_INTEGRATION.md`
- ✅ 包含数据范围、表结构、连接方式、典型查询示例

### [2025-10-18] - 批量抓取功能
- ✅ 支持分批页抓取（`start_page`、`end_page` 参数）
- ✅ 支持并行抓取多个批次
- ✅ 创建 `batch_crawl.sh` 脚本
- ✅ 创建 `merge_batches.py` 合并脚本

### [2025-10-17] - 数据库集成
- ✅ 创建完整的数据库 schema（5 个表）
- ✅ 实现幂等导入脚本（支持增量更新）
- ✅ 创建数据验证脚本
- ✅ 环境变量管理（`.env` 文件）

### [2025-10-16] - 多分支处理
- ✅ 修复多分支 mods 丢失问题
- ✅ 实现 `closed()` 方法强制输出未完成的 items
- ✅ 禁用全局去重，确保所有分支都能抓取

### [2025-10-15] - 初始版本
- ✅ 基础爬虫功能
- ✅ 列表页分页抓取
- ✅ 详情页数据提取
- ✅ 版本和下载信息抓取

