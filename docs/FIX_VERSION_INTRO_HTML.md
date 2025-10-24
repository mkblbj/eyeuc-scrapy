# 🔧 修复版本说明提取（保留 HTML 格式）

**日期**: 2025-10-22  
**问题**: 版本说明被错误地提取为纯文本，丢失了 HTML 格式

---

## 问题描述

### 案例

**资源**: mid=31350 (DEST 2K26名单)  
**网页显示**: 包含丰富的 HTML 格式（`<font>`, `<strong>`, `<br>`, `<a>` 等标签）  
**旧版爬虫**: 提取纯文本，丢失所有格式和链接 ❌  
**需求**: 保留原始 HTML 格式，便于前端渲染 ✅

### 实际 HTML 结构

```html
<div class="veritem-content">
  <font color="Red">
    <strong>名单bug反馈
      <a href="https://wj.qq.com/s2/24068575/02g7/" target="_blank">
        https://wj.qq.com/s2/24068575/02g7/
      </a>
    </strong>
  </font><br />
  <br />
  游戏过程中如遇异常，请删除原Mods文件夹和存档目录CustomShoeDatabase文件，
  验证游戏文件完整性后，重新安装新版本补丁文件即可。<br />
  <br />
  <strong><font color="Red">V25.10.22 各队揭幕战阵容</font></strong><br />
  线上搜索名单名：现役 DEST 25-26，库里纪元"DEST CURRY ERA"，
  ALLTIME名单&quot;DEST ALLTIME&quot;，复古优化现役纪元搜索"DEST RETRO"或用户名DEST2K
</div>
```

---

## 根本原因

### 用户的错误修改

用户试图修复某个问题时，将 HTML 提取改为了纯文本提取：

```python
# 用户的修改（有问题）
else:
    # 如果没有 markdown-body，提取纯文本
    plain_texts = selector.css('*::text').getall()
    if plain_texts:
        full_intro = ' '.join([t.strip() for t in plain_texts if t.strip()])
        if full_intro:
            version_intro = full_intro
```

**问题**:
- ❌ 丢失所有 HTML 标签
- ❌ 丢失链接 `<a href="...">`
- ❌ 丢失格式 `<font color="Red">`, `<strong>`
- ❌ 丢失换行 `<br />`

---

## 修复方案

### 1. 保留原始 HTML

对于非 `markdown-body` 的内容，直接使用 `content_area` 原始 HTML：

```python
# 修复后的代码
else:
    # 如果没有 markdown-body，保留原始 HTML 内容
    # 清理 script 标签
    cleaned_html = re.sub(r'<script[^>]*>.*?</script>', '', content_area, flags=re.DOTALL | re.IGNORECASE)
    if cleaned_html.strip():
        version_intro = cleaned_html.strip()
```

**优势**:
- ✅ 保留所有 HTML 标签
- ✅ 保留链接和格式
- ✅ 只清理危险的 `<script>` 标签
- ✅ 便于前端渲染

---

### 2. 修复正则表达式

用户还修改了正则，添加了额外的 `</div>`，导致某些页面匹配失败：

```python
# 用户修改（太严格）
veritem_content_match = re.search(
    r'<div class="veritem-content">(.*?)</div>\s*</div>\s*<div class="veritem-footer">', 
    html_content, re.DOTALL
)
```

**问题**: 并非所有页面都有两个连续的 `</div>`

**修复**: 使用可选的 `(?:...)?` 使正则更灵活

```python
# 修复后（灵活匹配）
veritem_content_match = re.search(
    r'<div class="veritem-content">(.*?)</div>(?:\s*</div>)?\s*<div class="veritem-footer">', 
    html_content, re.DOTALL
)
```

---

## 代码对比

### 修改前（有问题）

```python
# eyeuc/spiders/eyeuc_mods.py:909-929

veritem_content_match = re.search(
    r'<div class="veritem-content">(.*?)</div>\s*</div>\s*<div class="veritem-footer">', 
    html_content, re.DOTALL
)
if veritem_content_match:
    content_area = veritem_content_match.group(1)
    selector = scrapy.Selector(text=content_area)
    
    markdown_body = selector.css('div.markdown-body')
    if markdown_body:
        html_intro = markdown_body.get()
        if html_intro:
            html_intro = re.sub(r'<script[^>]*>.*?</script>', '', html_intro, flags=re.DOTALL | re.IGNORECASE)
            version_intro = html_intro.strip()
    else:
        # ❌ 提取纯文本
        plain_texts = selector.css('*::text').getall()
        if plain_texts:
            full_intro = ' '.join([t.strip() for t in plain_texts if t.strip()])
            if full_intro:
                version_intro = full_intro
```

### 修改后（已修复）

```python
# eyeuc/spiders/eyeuc_mods.py:909-928

veritem_content_match = re.search(
    r'<div class="veritem-content">(.*?)</div>(?:\s*</div>)?\s*<div class="veritem-footer">', 
    html_content, re.DOTALL
)
if veritem_content_match:
    content_area = veritem_content_match.group(1).strip()
    selector = scrapy.Selector(text=content_area)
    
    markdown_body = selector.css('div.markdown-body')
    if markdown_body:
        html_intro = markdown_body.get()
        if html_intro:
            html_intro = re.sub(r'<script[^>]*>.*?</script>', '', html_intro, flags=re.DOTALL | re.IGNORECASE)
            version_intro = html_intro.strip()
    else:
        # ✅ 保留原始 HTML
        cleaned_html = re.sub(r'<script[^>]*>.*?</script>', '', content_area, flags=re.DOTALL | re.IGNORECASE)
        if cleaned_html.strip():
            version_intro = cleaned_html.strip()
```

---

## 测试验证

### 测试命令

```bash
cd /root/dev/eyeuc-scrapy
source venv/bin/activate
scrapy crawl eyeuc_mods \
  -a cookies=cookies.json \
  -a list_ids=193 \
  -a start_page=1 \
  -a end_page=1 \
  -s LOG_LEVEL=ERROR \
  -o /tmp/test_version_intro.jsonl
```

### 验证结果

```bash
python3 << 'EOF'
import json

with open('/tmp/test_version_intro.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        if data.get('mid') == '31350':
            intro = data['versions'][0].get('intro', '')
            print("版本说明（前 500 字符）：")
            print(intro[:500])
            break
EOF
```

**输出**:
```html
<font color="Red"><strong>名单bug反馈<a href="https://wj.qq.com/s2/24068575/02g7/" target="_blank">https://wj.qq.com/s2/24068575/02g7/</a></strong></font><br />
<br />
游戏过程中如遇异常，请删除原Mods文件夹和存档目录CustomShoeDatabase文件，验证游戏文件完整性后，重新安装新版本补丁文件即可。<br />
<br />
<strong><font color="Red">V25.10.22 各队揭幕战阵容/color]</strong><br />
线上搜索名单名：现役 DEST 25-26，库里纪元"DEST CURRY ERA"，ALLTIME名单&quot;DEST ALLTIME&quot;，复古优化现役纪元搜索"DEST RETRO"或用户名DEST2K
```

✅ **完整保留 HTML 格式！**

---

## 影响范围

### 受影响的内容类型

| 类型 | 处理方式 | 影响 |
|------|---------|------|
| Markdown 格式 | 提取 `div.markdown-body` 的 HTML | ✅ 无变化 |
| 原始 HTML 格式 | 保留 `content_area` 原始 HTML | ✅ 修复（之前丢失格式）|
| 空版本说明 | 保持为空 | ✅ 无影响 |

### 兼容性

- ✅ 向后兼容：Markdown 格式的处理逻辑未改变
- ✅ 向前兼容：新数据保留完整 HTML
- ✅ 数据库兼容：`versions.intro` 字段已支持存储长文本

---

## 前端渲染建议

### React 示例

```jsx
// 使用 dangerouslySetInnerHTML 渲染 HTML
function VersionIntro({ intro }) {
  return (
    <div 
      className="version-intro"
      dangerouslySetInnerHTML={{ __html: intro }}
    />
  );
}
```

### 安全性

由于爬虫已清理 `<script>` 标签，HTML 内容相对安全，但建议：

1. ✅ 使用 CSP (Content Security Policy)
2. ✅ 过滤危险属性（如 `onerror`, `onclick`）
3. ✅ 使用 DOMPurify 库进一步清理

```jsx
import DOMPurify from 'dompurify';

function VersionIntro({ intro }) {
  const sanitized = DOMPurify.sanitize(intro);
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
```

---

## 数据库更新

如果需要更新已导入的数据：

```bash
# 重新爬取受影响的资源
scrapy crawl eyeuc_mods \
  -a cookies=cookies.json \
  -a list_ids=193 \
  -a start_page=1 \
  -a end_page=50 \
  -o /tmp/update_version_intro.jsonl

# 导入更新（ON DUPLICATE KEY UPDATE）
python3 scripts/import_eyeuc_jsonl_to_mysql.py /tmp/update_version_intro.jsonl
```

---

## 相关文件

| 文件 | 修改内容 |
|------|---------|
| `eyeuc/spiders/eyeuc_mods.py:909-928` | 修复版本说明提取逻辑 |
| `docs/FIX_VERSION_INTRO_HTML.md` | 本文档 |

---

## 最佳实践

### 1. 内容提取原则

- ✅ **优先保留原格式**：HTML 内容保留 HTML，Markdown 保留 Markdown
- ✅ **清理危险内容**：移除 `<script>`, `<iframe>` 等危险标签
- ✅ **避免过度处理**：不要将 HTML 转换为纯文本（除非明确需要）

### 2. 正则表达式设计

- ✅ 使用非贪婪匹配 `.*?`
- ✅ 使用可选组 `(?:...)?` 提高灵活性
- ✅ 使用 `re.DOTALL` 支持多行匹配

### 3. 数据验证

定期检查版本说明质量：

```sql
-- 查找可能有问题的版本说明
SELECT 
  v.mod_id, 
  m.title,
  LENGTH(v.intro) as intro_length,
  v.intro
FROM versions v
JOIN mods m ON v.mod_id = m.mid
WHERE 
  LENGTH(v.intro) > 0 
  AND v.intro NOT LIKE '%<%'  -- 没有 HTML 标签
LIMIT 20;
```

如果大量记录没有 HTML 标签但应该有，说明提取逻辑有问题。

---

## 总结

### 问题
- 用户修改导致版本说明被提取为纯文本，丢失所有 HTML 格式

### 解决
- 恢复保留原始 HTML 的逻辑
- 修复正则表达式，使其更灵活地匹配不同的 HTML 结构

### 效果
- ✅ 完整保留 HTML 格式（标签、链接、颜色、换行）
- ✅ 向后兼容 Markdown 格式
- ✅ 便于前端渲染

---

**修复日期**: 2025-10-22  
**修复人**: AI Assistant  
**状态**: ✅ 已完成并测试通过

