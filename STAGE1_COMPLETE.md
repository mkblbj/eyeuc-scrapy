# Stage 1 (MVP) 完成总结 🎉

## 概述

EyeUC 多列表爬虫的 Stage 1 (MVP) 已全部完成并测试通过！

## 完成的功能

### ✅ 1.1 项目准备
- 虚拟环境和依赖管理
- Cookie 验证
- 基础限速与重试配置

### ✅ 1.2 Spider 多入口
- 支持 `cookies`, `list_ids`, `list_range`, `use_pw`, `direct_dl` 参数
- 多 list 并发抓取
- cookiejar 隔离

### ✅ 1.3 列表解析与翻页
- 游戏名称自动识别
- 详情链接提取与去重
- 自动翻页（动态检测最大页数）

### ✅ 1.4 详情解析
- 完整字段提取（title, cover_image, images, intro, metadata）
- 多分支支持（versions 数组）
- 元数据（作者、时间、统计）
- 分支统计（每个分支独立的查看/下载/更新时间）
- HTML 内容（支持 Markdown 和纯文本）

### ✅ 1.4.x 下载直链（两阶段分离）
- **阶段1：爬虫** - 提取元数据（mid/vid/fileid/filename/size）
- **阶段2：动态脚本** - `fetch_direct_links.py` 按需生成直链

### ✅ 1.5 按 list 分文件导出
- `PerListJsonPipeline` 管道
- 自动为每个 list_id 创建独立文件
- 支持 JSONL 和 JSON 数组格式
- 智能文件命名（含 game 和时间戳）

## 数据结构

### 爬虫输出格式

```json
{
  "mid": "31439",
  "list_id": 172,
  "game": "NBA2K24",
  "title": "2k不一般 / 门厅侍者 / 1.0",
  "cover_image": "https://a0.eyeassets.com/...",
  "images": ["https://..."],
  "intro": "<div>...</div>",
  "metadata": {
    "author": "2k不一般",
    "publisher": "2k不一般",
    "created_at": "2025-9-13 17:59",
    "views": "473",
    "downloads": "11",
    "likes": "0"
  },
  "versions": [
    {
      "vid": "46841",
      "version_name": "1.0",
      "is_default": true,
      "intro": "<div>...</div>",
      "stats": {
        "updated_at": "2025-9-13 17:59",
        "views": "474",
        "downloads": "11"
      },
      "downloads": [
        {
          "type": "internal",
          "mid": "31439",
          "vid": "46841",
          "fileid": "46000",
          "filename": "门厅侍者.zip",
          "size": "10.13 MB"
        }
      ]
    }
  ],
  "detail_url": "https://bbs.eyeuc.com/down/view/31439",
  "list_url": "https://bbs.eyeuc.com/down/list/172"
}
```

## 使用指南

### 基本用法

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 单个列表（JSONL 格式，分文件）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172

# 3. 多个列表（分文件）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172,182

# 4. 分文件 + 合并导出
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172,182 -O merged.json

# 5. JSON 数组格式
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172 \
  -s PER_LIST_AS_JSONL=False

# 6. 限制抓取数量（测试用）
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172 \
  -s CLOSESPIDER_ITEMCOUNT=10
```

### 获取直链

```bash
# 从爬虫输出获取直链（所有 mid）
python3 fetch_direct_links.py --json per_list_output/eyeuc_list172_*.jsonl \
  --cookies cookies.json

# 获取特定 mid 的直链
python3 fetch_direct_links.py --json per_list_output/eyeuc_list172_*.jsonl \
  --mid 31439 --cookies cookies.json

# 获取特定分支的直链
python3 fetch_direct_links.py --json per_list_output/eyeuc_list172_*.jsonl \
  --mid 31439 --vid 46841 --cookies cookies.json
```

## 输出文件

### 分文件输出

```
per_list_output/
├── eyeuc_list172_nba2k24_20251016_173408.jsonl  (8 items, 15 KB)
├── eyeuc_list182_nba2k25_20251016_173408.jsonl  (7 items, 9 KB)
└── ...
```

### 文件命名规则

`eyeuc_list{list_id}_{game}_{timestamp}.{jsonl|json}`

- `list_id`: 列表 ID
- `game`: 游戏名称（自动识别，如 nba2k24）
- `timestamp`: YYYYmmdd_HHMMSS
- `jsonl/json`: 格式（JSONL 或 JSON 数组）

## 配置项

### settings.py

```python
# Pipeline 配置
ITEM_PIPELINES = {
   "eyeuc.pipelines.PerListJsonPipeline": 300,
}

# 分文件导出配置
PER_LIST_OUTPUT_DIR = "per_list_output"
PER_LIST_AS_JSONL = True  # True=JSONL, False=JSON数组

# 并发与限速
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 0.5
AUTOTHROTTLE_ENABLED = True

# 重试配置
RETRY_ENABLED = True
RETRY_TIMES = 3
```

## 性能参数

- **并发请求**: 8 个
- **下载延迟**: 0.5 秒
- **AutoThrottle**: 启用（0.5s - 8s）
- **重试次数**: 3 次
- **超时时间**: 30 秒

## 统计示例

```
PerListJsonPipeline 统计
================================================================================
  list_id=172 (NBA2K24): 8 items, 15,572 bytes
    文件: per_list_output/eyeuc_list172_nba2k24_20251016_173408.jsonl
  list_id=182 (NBA2K25): 7 items, 9,406 bytes
    文件: per_list_output/eyeuc_list182_nba2k25_20251016_173408.jsonl
================================================================================
总计: 2 个列表, 15 items
================================================================================
```

## 关键特性

✅ **多列表并发** - 同时抓取多个列表，自动管理 cookies
✅ **分文件导出** - 每个列表独立文件，便于管理
✅ **多分支支持** - 完整支持 mod 的多个版本/分支
✅ **元数据丰富** - 作者、时间、统计等完整信息
✅ **HTML 内容** - 保留完整格式，便于前端渲染
✅ **直链分离** - 爬虫抓元数据，直链按需生成
✅ **格式灵活** - 支持 JSONL 和 JSON 数组
✅ **统计详细** - 自动输出抓取统计信息

## 下一步

Stage 1 (MVP) 已完成！可以考虑：

1. **Stage 2**: 稳健性与可维护性
   - 错误分类与监控
   - 选择器兜底
   - 断点续跑验证

2. **Stage 3**: 图片落地（可选）
   - ImagesPipeline 实现
   - 本地/云存储

3. **生产部署**
   - 定时任务
   - 监控告警
   - 数据入库

---

🎉 **Stage 1 (MVP) 完成并测试通过！**
