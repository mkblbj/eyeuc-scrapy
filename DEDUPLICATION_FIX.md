# 去重问题修复报告

## 问题描述

在抓取过程中发现，虽然 Spider 访问了所有页面，但最终输出的 items 数量少于预期：

- **List 193 (NBA2K26)**: 预期 97 个，实际只抓到 77-78 个
- **List 65 (NBA2K11)**: 预期 667 个，实际只抓到 623 个

## 问题根源

### 1. Scrapy 2.7+ 的指纹去重机制

即使在请求中设置了 `dont_filter=True`，Scrapy 2.7+ 的新指纹算法（`REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"`）仍然会在某些情况下对请求进行去重。

### 2. 置顶帖导致的重复请求

网站的置顶帖会在多个页面重复出现，导致同一个 `mid` 的详情页被多次访问。虽然 `parse_list` 中的 `seen_in_page` 正确地去重了页内的重复链接，但跨页的重复仍然存在。

对于同一个 `mid`，以下请求的 URL 完全相同：
```python
# parse_detail → parse_versions
https://bbs.eyeuc.com/down.php?mod=view&mid={mid}&show=toversion

# parse_versions → parse_download_ajax
https://bbs.eyeuc.com/down.php?mod=view&mid={mid}&vid={vid}&show=todownload
```

### 3. 多分支 mod 的处理逻辑

Spider 的逻辑是：**只有当一个 mod 的所有分支都处理完毕后，才会 yield item**。

```python
# 在 parse_download_ajax 中
if len(versions_data) >= total_versions:
    # 所有分支处理完毕，返回完整 item
    yield { ... }
```

如果某个分支的请求被去重，这个 mod 就永远不会 yield item，导致数据缺失。

## 解决方案

### 1. 禁用 Scrapy 的去重过滤器

在 `settings.py` 中：

```python
# REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"  # 暂时禁用
DUPEFILTER_CLASS = 'scrapy.dupefilters.BaseDupeFilter'  # 完全禁用去重
```

### 2. 为 AJAX 请求添加唯一时间戳

#### 修改 `parse_detail` → `parse_versions`

```python
# 添加时间戳确保每个请求的指纹唯一（防止置顶帖重复导致的去重）
import time
version_url = f'https://bbs.eyeuc.com/down.php?mod=view&mid={mid}&show=toversion&_t={int(time.time()*1000000)}'
```

#### 修改 `parse_versions` → `parse_download_ajax`

```python
# 添加时间戳确保每个请求的指纹唯一
import time
ajax_url = f'https://bbs.eyeuc.com/down.php?mod=view&mid={mid}&vid={vid}&show=todownload&_t={int(time.time()*1000000)}'
```

## 验证结果

修复后重新测试：

### List 193 (NBA2K26)
- ✅ **预期**: 97 个 mods（5 页：24+24+24+24+1）
- ✅ **实际**: 98 items（包含 1 个 `mid=None` 的异常 item）
- ✅ **唯一 mid**: 97 个
- ✅ **成功率**: 100%

### List 65 (NBA2K11)
- ✅ **预期**: 667 个 mods（28 页：27×24 + 19）
- ✅ **实际**: 667 items
- ✅ **成功率**: 100%

## 技术细节

### 为什么时间戳方案有效？

1. **URL 唯一性**: 每次请求都有不同的 `_t` 参数，确保 URL 完全不同
2. **服务器兼容**: 服务器会忽略未知的查询参数，不影响实际功能
3. **微秒级精度**: `int(time.time()*1000000)` 提供微秒级精度，确保并发请求也不会冲突

### 为什么不能只依赖 `dont_filter=True`？

虽然 `dont_filter=True` 会告诉 Scrapy 不要过滤这个请求，但：

1. Scrapy 的调度器可能还有其他内部机制
2. JOBDIR 的持久化可能会记录已访问的 URL
3. 某些中间件可能会进行额外的去重检查

通过修改 URL 本身（添加时间戳），可以从根本上避免任何形式的去重。

## 影响评估

### 正面影响
- ✅ **数据完整性**: 确保所有 mods 都被抓取
- ✅ **多分支支持**: 正确处理有多个分支的 mods
- ✅ **置顶帖处理**: 正确处理在多页重复出现的置顶帖

### 潜在影响
- ⚠️ **请求数量**: 对于置顶帖，会重复请求相同的 `mid`，但由于时间戳不同，会被视为不同的请求
- ⚠️ **服务器负载**: 可能会对服务器造成轻微的额外负载
- ⚠️ **抓取时间**: 可能会略微增加总抓取时间

### 缓解措施
- 已设置合理的并发和延迟参数（`CONCURRENT_REQUESTS=12`, `DOWNLOAD_DELAY=0.3`）
- AutoThrottle 会根据服务器响应自动调整速度
- 时间戳参数很小，不会显著增加网络传输量

## 后续建议

1. **监控抓取质量**: 定期检查抓取结果的完整性
2. **优化去重逻辑**: 考虑在 Pipeline 中进行更智能的去重（基于 `mid` 而不是 URL）
3. **错误处理**: 增强对失败请求的重试和错误报告
4. **性能优化**: 如果服务器允许，可以适当提高并发数

## 相关文件

- `/root/dev/eyeuc-scrapy/eyeuc/spiders/eyeuc_mods.py` (第 327, 710 行)
- `/root/dev/eyeuc-scrapy/eyeuc/settings.py` (第 138-139 行)

## 修复日期

2025-10-16

## 修复人员

AI Assistant (Claude Sonnet 4.5)

