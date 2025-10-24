# 📦 EyeUC 数据库导入指南

## ✅ 已完成的实施

### 2.5.1 表结构（schema.sql）
- ✅ 5 张表：`lists`, `mods`, `images`, `versions`, `downloads`
- ✅ 主键与唯一约束
- ✅ 索引优化（list_id, author, title 全文索引）
- ✅ 字符集 utf8mb4
- ✅ 支持 5 种下载类型：`internal`, `external`, `forum_redirect`, `empty`, `unknown`

### 2.5.2 导入脚本（scripts/import_eyeuc_jsonl_to_mysql.py）
- ✅ 支持 JSONL 和 JSON 数组
- ✅ 支持目录 glob 批量导入
- ✅ 幂等导入（ON DUPLICATE KEY UPDATE）
- ✅ 批量提交（每 200 条）
- ✅ 环境变量配置
- ✅ 自动类型推断（type 字段）
- ✅ 导入成功后自动清理源文件（默认开启）
- ✅ 全量替换模式：删除所有旧数据后导入（可选）

### 2.5.3 验证脚本（scripts/verify_database.py）
- ✅ 数据统计
- ✅ 按列表统计
- ✅ 下载类型分布
- ✅ 多分支资源排行
- ✅ 热门资源排行
- ✅ 数据完整性检查

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pymysql
```

### 2. 配置环境变量 ⚠️

**重要：** 
- 数据库连接信息仅存储在 `.env` 文件中
- `.env` 已在 `.gitignore` 中，不会被提交到 git
- 使用 `.env.example` 作为模板

**方法 1：复制模板并编辑**

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件，填入真实的连接信息
nano .env  # 或使用其他编辑器

# 加载环境变量
source .env
```

**方法 2：直接创建**

```bash
cat > .env << 'EOF'
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name
MYSQL_SSL=false
EOF

# 加载环境变量
source .env
```

或直接设置环境变量：

```bash
export MYSQL_HOST=your_mysql_host
export MYSQL_PORT=3306
export MYSQL_USER=your_mysql_user
export MYSQL_PASSWORD=your_mysql_password
export MYSQL_DATABASE=your_database_name
export MYSQL_SSL=false
```

### 3. 导入数据

#### 3.1 增量导入（默认） 📥

**行为**：更新已存在的记录，添加新记录，保留旧记录

```bash
# 导入单个列表（增量 + 自动清理）
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/eyeuc_list193_*_merged_*.jsonl"

# 导入所有合并文件（增量 + 自动清理）
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/eyeuc_list*_merged_*.jsonl"

# 如果需要保留源文件（禁用自动清理）
CLEANUP=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

**适用场景**：
- ✅ 部分数据更新
- ✅ 增量爬取
- ✅ 不希望删除任何旧数据

---

#### 3.2 全量替换（推荐用于定时任务） 🔄

**行为**：删除所有旧数据，导入全新数据（事务保护）

```bash
# 全量替换模式
FULL_REPLACE=true python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 全量替换 + 禁用清理（用于调试）
FULL_REPLACE=true CLEANUP=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

**适用场景**：
- ✅ 定时全量爬取
- ✅ 需要数据库与爬取结果完全同步
- ✅ 需要清理已删除的资源
- ✅ 保持数据库实时最新

**安全机制**：
- ✅ 事务保护：失败自动回滚
- ✅ 使用 `TRUNCATE TABLE` 快速删除
- ✅ 详细日志记录

**详细文档**：参见 `docs/FULL_REPLACE_GUIDE.md`

---

**清理行为说明：**
- ✅ 导入成功后自动删除已导入的 `.jsonl` 文件
- ✅ 如果目录为空，自动删除目录
- ✅ 防止 `per_list_output` 文件夹变得过大
- ✅ 可通过 `CLEANUP=false` 环境变量禁用

### 4. 验证数据

```bash
python scripts/verify_database.py
```

## 📊 数据结构

### lists（游戏/列表）
```sql
list_id | game    | slug | created_at | updated_at
--------|---------|------|------------|------------
193     | NBA2K26 | NULL | 2025-...   | 2025-...
```

### mods（资源）
```sql
mid    | list_id | title        | author | views | downloads | likes | ...
-------|---------|--------------|--------|-------|-----------|-------|----
31350  | 193     | DEST 2K26... | DEST2K | 16082 | 3398      | 14    | ...
```

### versions（分支）
```sql
id  | mod_id | vid   | version_name | is_default | ...
----|--------|-------|--------------|------------|----
1   | 31350  | 46648 | V25.10.16    | 1          | ...
```

### downloads（附件）
```sql
id | mod_id | version_id | type     | fileid | filename    | size    | url | ...
---|--------|------------|----------|--------|-------------|---------|-----|----
1  | 31350  | 1          | external | NULL   | NULL        | NULL    | ... | ...
```

### images（图片）
```sql
id | mod_id | url                              | idx
---|--------|----------------------------------|----
1  | 31350  | https://a0.eyeassets.com/...     | 0
```

## 🔧 后端对接（直链生成）

### 方法 1：使用现有脚本逻辑

将 `fetch_direct_links.py` 中的 `get_direct_link_for_file` 函数集成到 FastAPI：

```python
# backend/utils/eyeuc_direct_link.py
import requests
import re
from datetime import datetime

def get_formhash(mid: int, cookies: dict) -> str:
    """从详情页获取 formhash"""
    url = f'https://bbs.eyeuc.com/down/view/{mid}'
    resp = requests.get(url, cookies=cookies, timeout=15)
    
    # 从 var _data 中提取
    match = re.search(r'var _data = \{.*?"formhash"\s*:\s*"([a-f0-9]+)"', resp.text)
    if match:
        return match.group(1)
    
    # 从 input hidden 中提取
    match = re.search(r'name="formhash"\s+value="([a-f0-9]+)"', resp.text)
    return match.group(1) if match else None

def get_direct_link(mid: int, vid: int, fileid: int, formhash: str, cookies: dict) -> tuple:
    """获取直链（buy 接口）"""
    url = f'https://bbs.eyeuc.com/down.php?mod=buy&mid={mid}&vid={vid}&fileid={fileid}&hash={formhash}'
    
    resp = requests.get(url, cookies=cookies, allow_redirects=False, timeout=15)
    
    if 'Location' in resp.headers:
        direct_url = resp.headers['Location']
        
        # 解析过期时间
        auth_match = re.search(r'auth_key=(\d+)-', direct_url)
        expires_at = None
        if auth_match:
            timestamp = int(auth_match.group(1))
            expires_at = datetime.fromtimestamp(timestamp).isoformat()
        
        return direct_url, expires_at
    
    return None, None
```

### 方法 2：FastAPI 路由示例

```python
# backend/api/downloads.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx

router = APIRouter()

@router.get("/downloads/{mid}/{vid}/{fileid}")
async def get_download(mid: int, vid: int, fileid: int):
    """生成直链并重定向"""
    # 1. 从数据库查询 download 信息
    download = await db.query(
        "SELECT * FROM downloads WHERE mod_id=%s AND fileid=%s",
        (mid, fileid)
    )
    
    if not download:
        raise HTTPException(404, "附件不存在")
    
    # 2. 根据类型处理
    if download['type'] == 'external':
        # 外链直接跳转
        return RedirectResponse(download['url'])
    
    elif download['type'] == 'internal':
        # 站内附件生成直链
        from utils.eyeuc_direct_link import get_formhash, get_direct_link
        
        # 使用用户的 cookies（从 session 或 request header 获取）
        cookies = get_user_cookies()
        
        formhash = get_formhash(mid, cookies)
        direct_url, expires_at = get_direct_link(mid, vid, fileid, formhash, cookies)
        
        if direct_url:
            return RedirectResponse(direct_url)
        else:
            raise HTTPException(500, "直链生成失败")
    
    elif download['type'] == 'forum_redirect':
        # 论坛跳转
        return RedirectResponse(download['url'])
    
    else:
        raise HTTPException(400, f"不支持的类型: {download['type']}")
```

### 方法 3：代理下载（推荐）

```python
@router.get("/downloads/{mid}/{vid}/{fileid}/proxy")
async def proxy_download(mid: int, vid: int, fileid: int):
    """代理下载（避免暴露直链）"""
    # ... 生成直链 ...
    
    # 代理文件流
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', direct_url) as resp:
            headers = {
                'Content-Type': resp.headers.get('Content-Type'),
                'Content-Disposition': resp.headers.get('Content-Disposition'),
            }
            
            return StreamingResponse(
                resp.aiter_bytes(),
                headers=headers
            )
```

## 📈 数据统计（List 193 测试结果）

```
✅ 导入成功
- 总 items: 98
- 用时: 0.76s
- 速度: 128.2 items/s

数据统计:
- lists: 1 条
- mods: 98 条
- images: 500 条
- versions: 149 条
- downloads: 188 条

下载类型分布:
- internal: 108 条（站内附件，需要直链生成）
- external: 52 条（外部网盘，直接跳转）
- forum_redirect: 21 条（论坛跳转）
- unknown: 4 条
- empty: 3 条

数据完整性:
- 无版本的 mods: 0 条 ✅
- 无下载的版本: 0 条 ✅
- 无图片的 mods: 4 条
```

## 🔍 常用查询

### 1. 列表页数据（分页）

```sql
SELECT 
    m.mid, m.title, m.author, m.cover_image,
    m.views, m.downloads, m.likes, m.created_at
FROM mods m
WHERE m.list_id = 193
ORDER BY m.downloads DESC
LIMIT 20 OFFSET 0;
```

### 2. 详情页数据

```sql
-- 主信息
SELECT * FROM mods WHERE mid = 31350;

-- 图片
SELECT url FROM images WHERE mod_id = 31350 ORDER BY idx;

-- 版本
SELECT * FROM versions WHERE mod_id = 31350;

-- 下载（带版本信息）
SELECT 
    d.*, 
    v.version_name, v.is_default
FROM downloads d
LEFT JOIN versions v ON d.version_id = v.id
WHERE d.mod_id = 31350;
```

### 3. 搜索

```sql
-- 全文搜索（标题）
SELECT mid, title, author, downloads
FROM mods
WHERE MATCH(title) AGAINST('科比' IN NATURAL LANGUAGE MODE)
ORDER BY downloads DESC
LIMIT 20;

-- 作者搜索
SELECT mid, title, downloads
FROM mods
WHERE author LIKE '%DEST%'
ORDER BY downloads DESC;
```

### 4. 统计

```sql
-- 按游戏统计
SELECT l.game, COUNT(m.mid) as mod_count
FROM lists l
LEFT JOIN mods m ON l.list_id = m.list_id
GROUP BY l.list_id;

-- 热门作者
SELECT author, COUNT(*) as mod_count, SUM(downloads) as total_downloads
FROM mods
WHERE author IS NOT NULL
GROUP BY author
ORDER BY total_downloads DESC
LIMIT 20;
```

## ⚠️ 注意事项

### 1. 直链时效性
- `internal` 类型的直链带时效和鉴权
- 建议代理下载或实时生成
- 不要缓存直链 URL

### 2. 用户 Cookies
- 直链生成需要用户的 cookies
- 建议让用户在前端登录 EyeUC 并提取 cookies
- 或使用服务端统一 cookies（注意限流）

### 3. 数据更新
- 定期重新抓取更新数据
- 使用幂等导入（ON DUPLICATE KEY UPDATE）
- 注意 `updated_ts` 字段可用于增量同步

### 4. 性能优化
- 已建立必要索引（list_id, author, title）
- 大表查询注意分页
- 考虑使用 Redis 缓存热门数据

## 📝 下一步

1. ✅ 表结构和导入脚本已完成
2. ✅ List 193 测试通过
3. ⏳ 你方实施：
   - FastAPI 路由（列表、详情、下载）
   - React 前端对接
   - 直链生成集成
4. ⏳ 完整数据导入：
   - List 182（~2386 mods）
   - 其他列表

## 🎓 参考文档

- `docs/eyeuc_scrapy_multi_list_checklist.md` - 完整清单（2.5 节）
- `fetch_direct_links.py` - 直链生成脚本（可复用核心逻辑）
- `schema.sql` - 完整表结构
- `scripts/import_eyeuc_jsonl_to_mysql.py` - 导入脚本
- `scripts/verify_database.py` - 验证脚本

---

✨ 数据已就绪，祝开发顺利！

