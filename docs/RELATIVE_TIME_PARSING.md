# 相对时间解析说明

## 问题背景

EyeUC 网站在列表页和详情页显示的时间字段（`created_at`、`last_updated`、`current_version_updated`）使用了两种不同的 HTML 格式：

### 格式1：相对时间（带 title 属性）
```html
<li>
  <p class="custom-tt">资源创建时间</p>
  <p class="custom-dd"><span title="2025-10-18 17:36">昨天 17:36</span></p>
</li>
```

### 格式2：绝对时间（直接文本）
```html
<li>
  <p class="custom-tt">资源创建时间</p>
  <p>2025-9-1 11:11</p>
</li>
```

如果爬虫不兼容这两种格式，会导致约 45% 的数据缺失时间字段。

## 解决方案

爬虫已实现 `_parse_relative_time()` 方法，自动将相对时间转换为绝对时间格式（`YYYY-MM-DD HH:MM`）。

### 支持的相对时间格式

| 输入格式 | 示例 | 转换结果（假设当前时间 2025-10-19 10:48） |
|---------|------|----------------------------------------|
| 昨天 HH:MM | 昨天 17:37 | 2025-10-18 17:37 |
| 前天 HH:MM | 前天 12:34 | 2025-10-17 12:34 |
| 今天 HH:MM | 今天 08:00 | 2025-10-19 08:00 |
| N 天前 | 3 天前 | 2025-10-16 10:48 |
| N 小时前 | 2 小时前 | 2025-10-19 08:48 |
| N 分钟前 | 30 分钟前 | 2025-10-19 10:18 |
| 刚刚/刚才 | 刚刚 | 2025-10-19 10:48 |
| 绝对时间 | 2025-10-18 17:37 | 2025-10-18 17:37（保持不变） |

### 转换逻辑

1. **多格式兼容**：
   - 优先尝试从 `<span title="...">` 提取绝对时间
   - 若无 `<span>`，则从 `<p>` 标签直接提取文本
2. **相对时间转换**：自动识别并转换相对时间为绝对时间
3. **智能识别**：自动判断文本是绝对时间还是相对时间
4. **兜底处理**：若无法识别格式，保留原始文本

### 代码实现

```python
def _parse_relative_time(self, time_str):
    """将相对时间转换为绝对时间字符串"""
    if not time_str:
        return None
        
    time_str = time_str.strip()
    now = datetime.now()
    
    # 如果已经是绝对时间格式，直接返回
    if re.match(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', time_str):
        return time_str
    
    # 匹配 "昨天 HH:MM"
    match = re.match(r'昨天\s+(\d{1,2}):(\d{2})', time_str)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        target_date = now - timedelta(days=1)
        result = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return result.strftime('%Y-%m-%d %H:%M')
    
    # ... 其他格式匹配 ...
```

## 数据库字段

导入数据库后，`mods` 表的时间字段均为绝对时间格式，可直接用于：

- 时间排序：`ORDER BY created_at DESC`
- 时间筛选：`WHERE created_at >= '2025-10-01'`
- 时间范围查询：`WHERE last_updated BETWEEN '2025-10-01' AND '2025-10-19'`

## 示例

### 爬取前（网站显示）
```
资源创建时间：昨天 17:37
最后更新时间：3 天前
```

### 爬取后（JSON 输出）
```json
{
  "created_at": "2025-10-18 17:37",
  "last_updated": "2025-10-16 10:48"
}
```

### 数据库记录
```sql
SELECT mid, title, created_at, last_updated 
FROM mods 
WHERE created_at >= '2025-10-18'
ORDER BY created_at DESC;

-- 结果
mid    title              created_at         last_updated
31715  Shai Gilgeous...   2025-10-18 17:37   2025-10-18 17:37
31712  2K: UNDER THE...   2025-10-18 10:11   2025-10-18 10:12
```

## 注意事项

1. **时区**：转换基于爬虫运行时的系统时间（本地时区），建议在与网站相同的时区运行爬虫
2. **精度**：
   - "昨天/前天 HH:MM" 保留小时和分钟精度
   - "N 天前" 只保留日期，时间设为当前时刻
   - "N 小时前/N 分钟前" 保留完整精度
3. **历史数据**：已爬取的相对时间数据不会自动更新，建议重新爬取或手动处理

## 日志示例

爬虫运行时会记录相对时间转换情况：

```
[eyeuc_mods] DEBUG: 转换相对时间: "昨天 17:37" -> "2025-10-18 17:37"
[eyeuc_mods] WARNING: 无法解析相对时间: "上周三"
```

---

**更新时间**：2025-10-19  
**版本**：v1.0

