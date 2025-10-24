# 🎨 前端显示版本说明指南

## 当前数据格式

### 示例数据

```json
{
  "versions": [
    {
      "version_name": "V25.10.22",
      "intro": "<font color=\"Red\"><strong>名单bug反馈<a href=\"https://wj.qq.com/s2/24068575/02g7/\" target=\"_blank\">https://wj.qq.com/s2/24068575/02g7/</a></strong></font><br /><br />游戏过程中如遇异常，请删除原Mods文件夹和存档目录CustomShoeDatabase文件，验证游戏文件完整性后，重新安装新版本补丁文件即可。<br /><br /><strong><font color=\"Red\">V25.10.22 各队揭幕战阵容/color]</strong><br />线上搜索名单名：现役 DEST 25-26，库里纪元\"DEST CURRY ERA\"，ALLTIME名单&quot;DEST ALLTIME&quot;，复古优化现役纪元搜索\"DEST RETRO\"或用户名DEST2K"
    }
  ]
}
```

### 数据特点

- ✅ 已移除 `\r\n` (Windows 换行符)
- ✅ 已清理 `<script>` 标签
- ✅ 保留所有 HTML 格式标签（`<font>`, `<strong>`, `<br>`, `<a>` 等）
- ⚠️ 包含转义的引号（`\"` 和 `&quot;`）- 这是 JSON 标准格式，前端解析后会自动还原

---

## React 前端显示方案

### 方案 1：直接渲染（简单）

```jsx
import React from 'react';

function VersionIntro({ intro }) {
  return (
    <div 
      className="version-intro"
      dangerouslySetInnerHTML={{ __html: intro }}
    />
  );
}

export default VersionIntro;
```

**优点**：
- ✅ 简单直接
- ✅ 保留所有原始格式

**缺点**：
- ⚠️ 安全风险（虽然已清理 `<script>`，但仍需注意）

---

### 方案 2：使用 DOMPurify（推荐） ⭐

```jsx
import React from 'react';
import DOMPurify from 'dompurify';

function VersionIntro({ intro }) {
  // 配置 DOMPurify
  const config = {
    ALLOWED_TAGS: ['font', 'strong', 'br', 'a', 'em', 'b', 'i', 'u', 'p', 'div', 'span'],
    ALLOWED_ATTR: ['color', 'href', 'target', 'class', 'style'],
  };
  
  const sanitized = DOMPurify.sanitize(intro, config);
  
  return (
    <div 
      className="version-intro"
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  );
}

export default VersionIntro;
```

**安装依赖**：
```bash
npm install dompurify
# 或
yarn add dompurify
```

**优点**：
- ✅ 安全：自动过滤危险标签和属性
- ✅ 灵活：可自定义允许的标签
- ✅ 保留格式

---

### 方案 3：自定义样式（最佳实践） 🎯

```jsx
import React from 'react';
import DOMPurify from 'dompurify';
import './VersionIntro.css';

function VersionIntro({ intro }) {
  const config = {
    ALLOWED_TAGS: ['font', 'strong', 'br', 'a', 'em', 'b', 'i', 'u', 'p', 'div', 'span'],
    ALLOWED_ATTR: ['color', 'href', 'target'],
  };
  
  const sanitized = DOMPurify.sanitize(intro, config);
  
  return (
    <div 
      className="version-intro"
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  );
}

export default VersionIntro;
```

**CSS 样式**：
```css
/* VersionIntro.css */
.version-intro {
  line-height: 1.6;
  color: #333;
  font-size: 14px;
}

.version-intro a {
  color: #1890ff;
  text-decoration: none;
}

.version-intro a:hover {
  text-decoration: underline;
}

.version-intro strong {
  font-weight: 600;
}

/* 处理原始 HTML 中的 font color 标签 */
.version-intro font[color="Red"] {
  color: #ff4d4f !important;
}

/* 换行标签 */
.version-intro br {
  line-height: 1.8;
}
```

---

## Vue.js 前端显示方案

### 方案 1：使用 v-html

```vue
<template>
  <div class="version-intro" v-html="sanitizedIntro"></div>
</template>

<script>
import DOMPurify from 'dompurify';

export default {
  name: 'VersionIntro',
  props: {
    intro: {
      type: String,
      default: ''
    }
  },
  computed: {
    sanitizedIntro() {
      const config = {
        ALLOWED_TAGS: ['font', 'strong', 'br', 'a', 'em', 'b', 'i', 'u', 'p', 'div', 'span'],
        ALLOWED_ATTR: ['color', 'href', 'target'],
      };
      return DOMPurify.sanitize(this.intro, config);
    }
  }
}
</script>

<style scoped>
.version-intro {
  line-height: 1.6;
  color: #333;
}

.version-intro a {
  color: #1890ff;
  text-decoration: none;
}

.version-intro a:hover {
  text-decoration: underline;
}
</style>
```

---

## FastAPI 后端 API 示例

```python
from fastapi import FastAPI, HTTPException
from typing import List, Optional
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

def get_db():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.get("/api/mods/{mid}/versions")
async def get_mod_versions(mid: int):
    """获取 mod 的所有版本信息"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 查询版本信息
            cur.execute("""
                SELECT 
                    v.id,
                    v.vid,
                    v.version_name,
                    v.is_default,
                    v.intro,
                    v.updated_at,
                    v.views,
                    v.downloads
                FROM versions v
                WHERE v.mod_id = %s
                ORDER BY v.is_default DESC, v.updated_at DESC
            """, (mid,))
            versions = cur.fetchall()
            
            # 查询每个版本的下载链接
            for ver in versions:
                cur.execute("""
                    SELECT 
                        type,
                        fileid,
                        filename,
                        size,
                        url,
                        note
                    FROM downloads
                    WHERE version_id = %s
                """, (ver['id'],))
                ver['downloads'] = cur.fetchall()
            
            return {
                "success": True,
                "data": versions
            }
    finally:
        conn.close()
```

**前端调用**：
```jsx
import React, { useState, useEffect } from 'react';
import VersionIntro from './VersionIntro';

function ModDetail({ mid }) {
  const [versions, setVersions] = useState([]);
  
  useEffect(() => {
    fetch(`/api/mods/${mid}/versions`)
      .then(res => res.json())
      .then(data => setVersions(data.data));
  }, [mid]);
  
  return (
    <div>
      {versions.map(ver => (
        <div key={ver.id} className="version-card">
          <h3>{ver.version_name}</h3>
          <VersionIntro intro={ver.intro} />
          {/* ... 显示下载链接等 ... */}
        </div>
      ))}
    </div>
  );
}
```

---

## 常见问题处理

### Q1: 转义引号显示问题

**问题**：JSON 中的 `\"` 在前端显示为 `"`

**解决**：这是正常的。JSON 解析时会自动将 `\"` 转换为 `"`

```javascript
// JSON 字符串
const jsonStr = '{"intro": "DEST \\"ALLTIME\\""}'

// 解析后
const obj = JSON.parse(jsonStr);
console.log(obj.intro);  // 输出: DEST "ALLTIME"
```

### Q2: `&quot;` 显示为引号

**问题**：HTML 实体 `&quot;` 应该显示为 `"`

**解决**：浏览器会自动将 HTML 实体转换。如果没有，可以手动转换：

```javascript
function decodeHtmlEntities(str) {
  const textarea = document.createElement('textarea');
  textarea.innerHTML = str;
  return textarea.value;
}

// 或使用现代浏览器 API
const parser = new DOMParser();
const decoded = parser.parseFromString(str, 'text/html').documentElement.textContent;
```

### Q3: `<br />` 换行不生效

**问题**：HTML 中的 `<br />` 没有显示换行

**解决**：确保使用 `dangerouslySetInnerHTML` 或 `v-html`，而不是直接显示文本：

```jsx
// ❌ 错误：这样会显示原始 HTML 标签
<div>{intro}</div>

// ✅ 正确：这样会渲染 HTML
<div dangerouslySetInnerHTML={{ __html: intro }} />
```

---

## 安全性最佳实践

### 1. 使用 Content Security Policy (CSP)

在 HTML 的 `<head>` 中添加：

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'unsafe-inline'; 
               style-src 'self' 'unsafe-inline';">
```

### 2. 过滤危险属性

```javascript
import DOMPurify from 'dompurify';

// 移除所有事件处理器
DOMPurify.addHook('afterSanitizeAttributes', function (node) {
  // 移除所有以 on 开头的属性（onclick, onerror 等）
  if (node.tagName) {
    Array.from(node.attributes).forEach(attr => {
      if (attr.name.startsWith('on')) {
        node.removeAttribute(attr.name);
      }
    });
  }
});
```

### 3. 限制外部链接

```javascript
const config = {
  ALLOWED_TAGS: ['font', 'strong', 'br', 'a'],
  ALLOWED_ATTR: ['color', 'href', 'target'],
  ALLOW_UNKNOWN_PROTOCOLS: false,
  // 只允许 http(s) 链接
  ALLOWED_URI_REGEXP: /^(?:https?:)/i
};
```

---

## 完整示例：React + Ant Design

```jsx
import React from 'react';
import { Card, Divider, Tag } from 'antd';
import { DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import DOMPurify from 'dompurify';
import './ModVersionCard.css';

function ModVersionCard({ version }) {
  const sanitizeConfig = {
    ALLOWED_TAGS: ['font', 'strong', 'br', 'a', 'em', 'b', 'i', 'u', 'p', 'div'],
    ALLOWED_ATTR: ['color', 'href', 'target'],
  };
  
  const sanitizedIntro = DOMPurify.sanitize(version.intro || '', sanitizeConfig);
  
  return (
    <Card
      title={
        <div className="version-header">
          <span className="version-name">{version.version_name}</span>
          {version.is_default && <Tag color="blue">默认分支</Tag>}
        </div>
      }
      extra={
        <div className="version-stats">
          <span><EyeOutlined /> {version.views}</span>
          <Divider type="vertical" />
          <span><DownloadOutlined /> {version.downloads}</span>
        </div>
      }
    >
      {sanitizedIntro && (
        <div 
          className="version-intro"
          dangerouslySetInnerHTML={{ __html: sanitizedIntro }}
        />
      )}
      
      {version.downloads && version.downloads.length > 0 && (
        <>
          <Divider />
          <div className="download-list">
            {version.downloads.map((dl, idx) => (
              <div key={idx} className="download-item">
                {dl.filename || dl.note}
                {dl.size && <span className="file-size">{dl.size}</span>}
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

export default ModVersionCard;
```

---

## 总结

### ✅ 可以直接显示

当前的 HTML 格式**完全可以在前端显示**，只需：

1. **React**: 使用 `dangerouslySetInnerHTML`
2. **Vue**: 使用 `v-html`
3. **安全性**: 建议使用 DOMPurify 过滤

### 📝 数据质量

- ✅ 已移除 `\r\n`
- ✅ 已清理 `<script>`
- ✅ 保留完整 HTML 格式
- ✅ JSON 转义符（`\"`）会被自动处理

### 🎨 显示效果

使用推荐的方案后，前端会完美显示：
- 🔴 红色字体
- 🔗 可点击链接
- 💪 加粗文字
- 📄 正确的换行

**无需额外处理，直接使用即可！** 🚀

