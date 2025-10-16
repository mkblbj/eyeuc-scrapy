# EyeUC 多分支支持完整指南 🎉

## 一、爬虫功能更新

### 1.1 元数据字段增强

每个资源现在包含以下元数据：

```json
{
  "mid": "31439",
  "metadata": {
    "author": "2k不一般",
    "author_url": "https://bbs.eyeuc.com/down/user/...",
    "publisher": "2k不一般", 
    "publisher_url": "https://bbs.eyeuc.com/down/user/...",
    "created_at": "2025-9-13 17:59",
    "last_updated": "2025-9-13 17:59",
    "current_version_updated": "2025-9-13 17:59",
    "views": "463",
    "downloads": "5",
    "likes": "0"
  }
}
```

### 1.2 多分支支持

每个分支包含：
- `vid` - 分支 ID
- `version_name` - 分支名称
- `is_default` - 是否默认分支
- `intro` - 分支描述（完整 HTML）
- `stats` - 分支统计信息
- `downloads` - 分支下载文件列表

```json
{
  "versions": [
    {
      "vid": "46841",
      "version_name": "1.0",
      "is_default": true,
      "intro": "<div>...</div>",
      "stats": {
        "updated_at": "2025-9-13 17:59",
        "views": "463",
        "downloads": "5"
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
  ]
}
```

## 二、直链获取脚本更新

### 2.1 基本用法

```bash
# 获取单个 mid 的所有分支
python3 fetch_direct_links.py --json output.json --mid 31439 --cookies cookies.json

# 获取特定分支
python3 fetch_direct_links.py --json output.json --mid 31439 --vid 46841 --cookies cookies.json

# 批量获取（所有 mid）
python3 fetch_direct_links.py --json output.json --cookies cookies.json
```

### 2.2 输出格式

```json
[
  {
    "mid": "31439",
    "title": "2k不一般 / 门厅侍者 / 1.0",
    "versions": [
      {
        "vid": "46841",
        "version_name": "1.0",
        "downloads": [
          {
            "fileid": "46000",
            "filename": "门厅侍者.zip",
            "size": "10.13 MB",
            "direct_url": "https://resource-file.eyeassets.com/...",
            "expires_at": "2025-10-16T16:46:16"
          }
        ]
      }
    ]
  }
]
```

## 三、完整工作流程

### 步骤 1: 爬取元数据
```bash
scrapy crawl eyeuc_mods \
  -a cookies=cookies.json \
  -a list_ids=172 \
  -s CLOSESPIDER_ITEMCOUNT=10 \
  -O output.json
```

### 步骤 2: 动态获取直链
```bash
# 获取特定 mod 的直链
python3 fetch_direct_links.py \
  --json output.json \
  --mid 31439 \
  --cookies cookies.json \
  --output direct_links.json
```

### 步骤 3: 使用直链下载
直链有效期约 15 分钟，可以直接用于下载：
```bash
wget "https://resource-file.eyeassets.com/..." -O filename.zip
```

## 四、关键特性

✅ **多分支完整支持** - 每个分支独立的 vid、描述、统计、下载
✅ **元数据丰富** - 作者、时间、查看数、下载数等
✅ **分支统计** - 每个分支独立的查看、下载、更新时间
✅ **灵活查询** - 支持按 mid、vid 精确获取
✅ **临时直链** - 按需生成，避免时效问题
✅ **HTML 内容** - intro 字段返回完整 HTML，方便前端渲染

## 五、注意事项

⚠️ **直链时效性**: 直链约 15 分钟过期，建议即时使用
⚠️ **Cookie 要求**: 必须提供有效的 cookies.json
⚠️ **并发限制**: 建议使用爬虫的节流设置避免封禁
⚠️ **数据完整性**: 优先使用爬虫输出的 JSON 作为直链脚本输入

---

🎉 **多分支支持完整实现！**
