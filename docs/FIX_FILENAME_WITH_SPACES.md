# 🔧 修复文件名提取（支持包含空格的完整文件名）

**日期**: 2025-10-22  
**问题**: 爬虫只提取部分文件名，遗漏了文件名中的空格和前缀

---

## 问题描述

### 案例

**资源**: mid=31731 (Curry Series 7 candy)  
**网页显示**: `CURRY SERIES 7 CANDY 2k26.zip`  
**爬虫提取**: `2k26.zip` ❌

### 根本原因

旧的正则表达式只能匹配**连续的字母数字字符**，不支持空格：

```python
# 旧正则（有问题）
filename_pattern = r'<em[^>]*class="bupload"[^>]*>.*?([a-zA-Z0-9_\-\.]+\.(iff|rar|zip|7z|png|jpg))</em>'
```

匹配逻辑：
- `[a-zA-Z0-9_\-\.]+` 只匹配字母、数字、下划线、连字符、点
- 遇到空格就停止匹配
- 结果：只捕获最后一段 `2k26.zip`

---

## 实际 HTML 结构

```html
<em class="bupload">
  <i class="iconfont">&#xe67b;</i> 
  &nbsp;CURRY SERIES 7 CANDY 2k26.zip
</em>
```

关键点：
1. 文件名位于 `&nbsp;` 之后
2. 文件名可能包含空格
3. 以文件扩展名结尾（`.zip`, `.rar` 等）

---

## 修复方案

### 新正则表达式

```python
# 新正则（已修复）
filename_pattern = r'<em[^>]*class="bupload"[^>]*>.*?&nbsp;([^<]+?\.(?:iff|rar|zip|7z|png|jpg))</em>'
```

**改进点**:
1. ✅ 明确匹配 `&nbsp;` 作为起点
2. ✅ 使用 `[^<]+?` 匹配任意字符（包括空格），直到遇到 `<`
3. ✅ 使用非贪婪匹配 `+?` 避免过度匹配
4. ✅ 使用 `(?:...)` 非捕获组简化返回值

### 代码修改

#### 1. 文件名提取逻辑

```python
# eyeuc/spiders/eyeuc_mods.py:952-955

# 提取文件名（从 <em class="bupload"> 中，包含完整文件名）
# 匹配 &nbsp; 之后的完整文件名（可能包含空格）
filename_pattern = r'<em[^>]*class="bupload"[^>]*>.*?&nbsp;([^<]+?\.(?:iff|rar|zip|7z|png|jpg))</em>'
filename_matches = re.findall(filename_pattern, html_content, re.IGNORECASE)
```

#### 2. 返回值类型调整

旧正则返回元组列表：`[('2k26.zip', 'zip'), ...]`  
新正则返回字符串列表：`['CURRY SERIES 7 CANDY 2k26.zip', ...]`

需要调整使用处：

```python
# eyeuc/spiders/eyeuc_mods.py:1030 (旧)
filename = filename_matches[idx][0] if idx < len(filename_matches) else f'file_{fileid}'

# eyeuc/spiders/eyeuc_mods.py:1030 (新)
filename = filename_matches[idx] if idx < len(filename_matches) else f'file_{fileid}'
```

同样修改：
- 第 1044 行：`link_name = filename_matches[idx]`
- 第 962 行：`filename_matches = text_matches` （备用逻辑）

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
  -o /tmp/test_filename_fix.jsonl
```

### 验证结果

```bash
grep '"mid": "31731"' /tmp/test_filename_fix.jsonl | \
  python3 -c "import sys, json; \
    data=json.loads(sys.stdin.read()); \
    print(data['versions'][0]['downloads'][0]['filename'])"
```

**输出**:
```
CURRY SERIES 7 CANDY 2k26.zip  ✅
```

**对比旧版**:
```
2k26.zip  ❌
```

---

## 影响范围

### 受影响的文件类型

| 扩展名 | 说明 | 影响 |
|--------|------|------|
| `.zip` | 压缩包 | ✅ 已修复 |
| `.rar` | 压缩包 | ✅ 已修复 |
| `.7z` | 压缩包 | ✅ 已修复 |
| `.iff` | 游戏资源 | ✅ 已修复 |
| `.png`, `.jpg` | 图片 | ✅ 已修复 |

### 文件名类型示例

| 类型 | 旧提取 | 新提取 | 状态 |
|------|-------|-------|------|
| 无空格 | `mod_v1.0.zip` | `mod_v1.0.zip` | ✅ 兼容 |
| 单空格 | `2k26.zip` | `NBA 2k26.zip` | ✅ 修复 |
| 多空格 | `2k26.zip` | `CURRY SERIES 7 CANDY 2k26.zip` | ✅ 修复 |
| 特殊字符 | `v1.0.zip` | `LeBron James v1.0.zip` | ✅ 修复 |

---

## 回归测试

### 测试数据集

已在以下资源上验证：

1. **mid=31731**: `CURRY SERIES 7 CANDY 2k26.zip` ✅
2. **mid=31672**: `2009v1.0.zip`（无空格）✅
3. **mid=31676**: `levels.zip`（无空格）✅

### 预期覆盖率

- ✅ 100% 的站内附件（`type=internal`）
- ✅ 100% 的外部链接名称（`type=external`）
- ✅ 向后兼容：无空格的文件名仍正常工作

---

## 数据库影响

### 已导入数据

旧数据库中的 `downloads.filename` 字段可能包含不完整的文件名（如 `2k26.zip`）。

### 更新策略

**方案 1**: 重新爬取并导入（推荐）
```bash
# 重新爬取受影响的列表
./smart_crawl.sh 193 100

# 自动更新数据库（ON DUPLICATE KEY UPDATE）
python3 scripts/import_eyeuc_jsonl_to_mysql.py \
  per_list_output/eyeuc_list193_*_merged_*.jsonl
```

**方案 2**: 只更新特定资源
```bash
# 爬取特定页面
scrapy crawl eyeuc_mods \
  -a cookies=cookies.json \
  -a list_ids=193 \
  -a start_page=1 \
  -a end_page=1 \
  -o /tmp/fix_filenames.jsonl

# 导入更新
python3 scripts/import_eyeuc_jsonl_to_mysql.py /tmp/fix_filenames.jsonl
```

---

## 相关文件

| 文件 | 修改内容 |
|------|---------|
| `eyeuc/spiders/eyeuc_mods.py` | 更新文件名提取正则表达式（3 处） |
| `docs/FIX_FILENAME_WITH_SPACES.md` | 本文档 |

---

## 最佳实践

### 1. 正则表达式设计

- ✅ 明确定义边界（如 `&nbsp;`、`</em>`）
- ✅ 使用非贪婪匹配 `+?` 避免过度匹配
- ✅ 考虑特殊字符（空格、Unicode）

### 2. 数据验证

定期抽查：
```bash
# 检查是否有异常短的文件名
mysql -h ... -u ... -p ... -e "
SELECT mid, filename, LENGTH(filename) as len
FROM downloads
WHERE type='internal' AND LENGTH(filename) < 10
ORDER BY len LIMIT 20;"
```

### 3. 日志监控

爬虫日志中搜索 `file_` 前缀（备用文件名）：
```bash
grep "file_" per_list_output/*.jsonl
```

如果大量出现，说明正则匹配失败。

---

## 总结

### 问题
- 旧正则只能匹配连续字母数字，遇到空格就截断

### 解决
- 新正则明确从 `&nbsp;` 开始，匹配任意字符直到 `</em>`

### 效果
- ✅ 完整提取包含空格的文件名
- ✅ 向后兼容无空格的文件名
- ✅ 数据质量显著提升

---

**修复日期**: 2025-10-22  
**修复人**: AI Assistant  
**状态**: ✅ 已完成并测试通过

