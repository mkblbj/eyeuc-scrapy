# 📥 直链获取脚本使用指南

## 功能说明

`fetch_direct_links.py` 用于**动态生成**下载直链，支持：

- ✅ 单个 mod 的所有分支
- ✅ 单个 mod 的特定分支
- ✅ 批量处理多个 mod
- ✅ 从爬虫输出的 JSON 批量提取

---

## 必需参数

### 1. Cookies 文件 🍪

**必需参数**：`--cookies cookies.json`

```bash
# 导出 cookies（浏览器扩展）
1. 安装 EditThisCookie 或 Cookie Editor
2. 登录 bbs.eyeuc.com
3. 导出 cookies 为 JSON 格式
4. 保存为 cookies.json
```

**Cookies 有效期**：通常 30 天，过期需重新导出。

---

## 使用场景

### 场景 1：获取单个 mod 的所有分支直链

**最简单**，只需提供 `mid` 和 `cookies`：

```bash
python3 fetch_direct_links.py \
  --mid 31047 \
  --cookies cookies.json
```

**输出**：该 mod 的所有分支的所有附件直链（JSON 格式）

---

### 场景 2：获取单个 mod 的特定分支直链

如果只需要某个特定分支：

```bash
python3 fetch_direct_links.py \
  --mid 31047 \
  --vid 46111 \
  --cookies cookies.json
```

**参数说明**：
- `--mid 31047`：mod ID
- `--vid 46111`：版本 ID（分支 ID）
- `--cookies cookies.json`：认证文件

**如何找到 vid？**

1. **方法 1**：从爬虫输出的 JSON 查看
   ```bash
   cat per_list_output/eyeuc_list182_*.jsonl | grep -A5 '"mid": 31047'
   ```

2. **方法 2**：从详情页 URL
   ```
   https://bbs.eyeuc.com/down/view/31047?vid=46111
                                   ^^^^^      ^^^^^
                                   mid        vid
   ```

---

### 场景 3：批量获取多个 mod 的直链

用逗号分隔多个 mid：

```bash
python3 fetch_direct_links.py \
  --mids 31047,31439,29672 \
  --cookies cookies.json
```

**适用场景**：手动指定几个 mod 批量下载

---

### 场景 4：从爬虫输出的 JSON 批量提取 ⭐

**最推荐**，直接使用爬虫的 JSON 输出：

```bash
# 方法 1：从 merged JSONL（需转换）
cat per_list_output/eyeuc_list182_nba2k25_merged_*.jsonl | \
  jq -s '.' > list182_full.json

# 方法 2：直接使用（如果是 JSON 格式）
python3 fetch_direct_links.py \
  --json list182_full.json \
  --cookies cookies.json \
  --output list182_direct_links.json
```

**优势**：
- ✅ 自动包含所有 mod 的元数据（title、versions、downloads）
- ✅ 不需要手动查 mid/vid
- ✅ 批量处理，一次搞定

---

### 场景 5：从 JSON 中提取特定 mod

从 JSON 中只提取某个 mid：

```bash
python3 fetch_direct_links.py \
  --json list182_full.json \
  --mid 31047 \
  --cookies cookies.json
```

**适用场景**：已有大 JSON，只想单独测试某个 mod

---

## 参数详解

| 参数 | 必需？ | 说明 | 示例 |
|------|-------|------|------|
| `--cookies` | ✅ | Cookies 文件路径 | `cookies.json` |
| `--mid` | 可选 | 单个 mod ID | `31047` |
| `--vid` | 可选 | 指定分支 ID（配合 `--mid`） | `46111` |
| `--mids` | 可选 | 多个 mid，逗号分隔 | `31047,31439` |
| `--json` | 可选 | 从 JSON 文件读取 | `output.json` |
| `--output` | 可选 | 保存到文件 | `result.json` |

**互斥规则**：
- `--mid` 或 `--mids` 或 `--json` 三选一
- `--vid` 只能配合 `--mid` 使用

---

## 输出格式

### 标准输出（默认）

```json
[
  {
    "mid": "31047",
    "title": "Some Mod Title",
    "versions": [
      {
        "vid": "46111",
        "version_name": "v1.0",
        "downloads": [
          {
            "fileid": "12345",
            "filename": "mod_v1.0.zip",
            "size": "15 MB",
            "direct_url": "https://cdn.eyeuc.com/...?auth_key=1734567890-...",
            "expires_at": "2025-10-19T15:31:30"
          }
        ]
      }
    ]
  }
]
```

### 保存到文件

```bash
# 使用 --output 参数
python3 fetch_direct_links.py \
  --mid 31047 \
  --cookies cookies.json \
  --output result.json

# ✅ 结果已保存到: result.json
```

---

## 直链有效期 ⏰

生成的直链包含时间戳签名：

```
https://cdn.eyeuc.com/...?auth_key=1734567890-xxx-xxx
                                    ^^^^^^^^^^
                                    过期时间戳
```

**有效期**：通常 **2-24 小时**（取决于网站设置）

**过期后**：需重新调用脚本生成新直链

---

## 典型工作流

### 工作流 1：快速测试单个 mod

```bash
# 1. 找到想要的 mid（从爬虫输出或网页 URL）
# 例如：https://bbs.eyeuc.com/down/view/31047

# 2. 获取直链
python3 fetch_direct_links.py \
  --mid 31047 \
  --cookies cookies.json \
  --output mod_31047.json

# 3. 下载文件
wget -i mod_31047.json  # 需要提取 direct_url
```

---

### 工作流 2：批量处理整个列表

```bash
# 1. 爬取列表（已完成）
./smart_crawl.sh 182 100

# 2. 合并数据
python3 merge_batches.py 182
# 输出：per_list_output/eyeuc_list182_nba2k25_merged_*.jsonl

# 3. 转换为 JSON
cat per_list_output/eyeuc_list182_nba2k25_merged_*.jsonl | \
  jq -s '.' > list182_full.json

# 4. 批量生成直链
python3 fetch_direct_links.py \
  --json list182_full.json \
  --cookies cookies.json \
  --output list182_direct_links.json

# 5. 导入数据库或进一步处理
python3 scripts/import_eyeuc_jsonl_to_mysql.py list182_full.json
```

---

### 工作流 3：实时直链生成（FastAPI 集成）

**场景**：用户点击下载按钮时动态生成直链

```python
# FastAPI 后端示例
from fastapi import FastAPI
import subprocess
import json

app = FastAPI()

@app.get("/api/download/{mid}/{vid}")
async def get_download_link(mid: str, vid: str):
    # 调用脚本生成直链
    result = subprocess.run([
        'python3', 'fetch_direct_links.py',
        '--mid', mid,
        '--vid', vid,
        '--cookies', 'cookies.json'
    ], capture_output=True, text=True)
    
    data = json.loads(result.stdout)
    return {
        'direct_url': data[0]['versions'][0]['downloads'][0]['direct_url'],
        'expires_at': data[0]['versions'][0]['downloads'][0]['expires_at']
    }
```

**前端调用**：

```javascript
// React 示例
const handleDownload = async (mid, vid) => {
  const res = await fetch(`/api/download/${mid}/${vid}`);
  const { direct_url } = await res.json();
  window.open(direct_url, '_blank');
};
```

---

## 常见问题

### Q1: 提示 "❌ 获取 formhash 失败"

**原因**：Cookies 过期或无效

**解决**：
```bash
# 重新导出 cookies.json
1. 打开浏览器，登录 bbs.eyeuc.com
2. 使用 Cookie Editor 导出
3. 覆盖旧的 cookies.json
```

---

### Q2: 提示 "⚠️ 无内部附件"

**原因**：该分支只有外部链接（如网盘、论坛跳转），没有直接下载的附件

**说明**：正常现象，脚本只处理 `type: internal` 的下载

---

### Q3: 如何找到 mid/vid？

**方法 1**：从爬虫输出的 JSONL

```bash
# 查看 mid 列表
cat per_list_output/eyeuc_*.jsonl | jq '.mid'

# 查看某个 mid 的所有 vid
cat per_list_output/eyeuc_*.jsonl | \
  jq 'select(.mid == 31047) | .versions[].vid'
```

**方法 2**：从详情页 URL

```
https://bbs.eyeuc.com/down/view/31047?vid=46111
                              ^^^^^      ^^^^^
```

**方法 3**：从数据库（如果已导入）

```sql
-- 查找 mod
SELECT id, mid, title FROM mods WHERE title LIKE '%关键词%';

-- 查找版本
SELECT id, vid, version_name FROM versions WHERE mod_id = 123;
```

---

### Q4: 直链失效了怎么办？

**直链有效期**：2-24 小时

**解决**：重新运行脚本生成新直链

```bash
# 重新生成
python3 fetch_direct_links.py \
  --mid 31047 \
  --vid 46111 \
  --cookies cookies.json
```

---

### Q5: 能否批量下载？

**可以**，结合 `jq` 和 `wget`：

```bash
# 1. 生成直链
python3 fetch_direct_links.py \
  --mid 31047 \
  --cookies cookies.json \
  --output links.json

# 2. 提取所有 direct_url
jq -r '.[].versions[].downloads[].direct_url' links.json > urls.txt

# 3. 批量下载
wget -i urls.txt -P downloads/
```

---

## 性能和限制

### 速度

- **单个 mid**：~3-5 秒（取决于分支数和附件数）
- **100 个 mid**：~5-8 分钟
- **瓶颈**：每个附件需要一次 HTTP 请求

### 限制

- ⚠️ **频率限制**：建议每秒 ≤ 5 个请求
- ⚠️ **Cookies 有效期**：~30 天
- ⚠️ **直链有效期**：2-24 小时

### 优化建议

1. **批量处理**：使用 `--json` 而非多次 `--mid`
2. **缓存直链**：存入数据库，有效期内复用
3. **并发控制**：避免同时生成大量直链

---

## 与数据库集成

### 方案 1：预生成直链存入数据库

```bash
# 1. 生成直链
python3 fetch_direct_links.py \
  --json list182_full.json \
  --cookies cookies.json \
  --output list182_direct_links.json

# 2. 更新数据库（需自行实现）
python3 scripts/update_direct_links.py list182_direct_links.json
```

**优点**：响应快  
**缺点**：需定期更新（直链会过期）

---

### 方案 2：实时生成（推荐）

```python
# FastAPI 后端
@app.get("/api/download/{mid}/{vid}")
async def get_download_link(mid: str, vid: str):
    # 实时调用脚本
    result = subprocess.run([...])
    return json.loads(result.stdout)
```

**优点**：直链始终有效  
**缺点**：每次请求需 3-5 秒

---

### 方案 3：混合模式（最优）

```python
# 伪代码
def get_direct_link(mid, vid):
    # 1. 检查数据库缓存
    cached = db.query("SELECT direct_url, expires_at WHERE ...")
    if cached and cached.expires_at > now():
        return cached.direct_url
    
    # 2. 缓存失效，重新生成
    new_link = fetch_direct_links(mid, vid)
    db.update("UPDATE downloads SET direct_url=...")
    return new_link
```

**优点**：快速 + 始终有效  
**缺点**：实现稍复杂

---

## 快速参考

```bash
# 单个 mod 所有分支
python3 fetch_direct_links.py --mid 31047 --cookies cookies.json

# 单个 mod 特定分支
python3 fetch_direct_links.py --mid 31047 --vid 46111 --cookies cookies.json

# 多个 mod
python3 fetch_direct_links.py --mids 31047,31439 --cookies cookies.json

# 从 JSON 批量
python3 fetch_direct_links.py --json list182.json --cookies cookies.json -o out.json

# 从 JSON 提取单个
python3 fetch_direct_links.py --json list182.json --mid 31047 --cookies cookies.json
```

---

## 总结

### 核心流程

```
1. 准备 cookies.json（浏览器导出）
2. 确定 mid（从爬虫输出或网页 URL）
3. 运行脚本生成直链
4. 使用直链下载或集成到应用
```

### 推荐用法

- **单次测试**：`--mid` + `--cookies`
- **批量处理**：`--json` + `--cookies`（从爬虫输出）
- **应用集成**：实时调用或缓存混合

需要我帮你测试一下脚本吗？或者有什么特定的使用场景需要优化？🚀

