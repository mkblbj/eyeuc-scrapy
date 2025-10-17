# List 182 数据缺失问题分析

## 问题现象

- **预期**: 100 页 × 24 = 2400 个 mods（实际测量：2386 个唯一 mids）
- **实际**: 抓取了 1871 items（缺失 515 个）
- **关键**: 抓取的 1871 items 中**没有任何多分支 mods**

## 测试验证

### 测试 1: 前 5 页（预期 120 个）

**设置**: `CLOSESPIDER_ITEMCOUNT=120`

**结果**:
- 抓到 124 items
- 但这些 items 来自第 1-33 页！
- 前 5 页只有 16 个 items 被输出（缺失 104 个）
- **14 个单分支 + 2 个多分支**

**结论**: 大量多分支 mods 被跳过了！

### 测试 2: 禁用去重后

**设置**: `DUPEFILTER_CLASS = 'scrapy.dupefilters.BaseDupeFilter'` + `CLOSESPIDER_ITEMCOUNT=120`

**结果**:
- 前 5 页还是只有 17 个 items（与测试 1 类似）
- 缺失 103 个

**结论**: 问题不在去重！

## 根本原因分析

### Spider 的工作流程

1. `parse_list`: 解析列表页，找到 24 个详情链接，发起 24 个 `parse_detail` 请求
2. `parse_detail`: 解析详情页，提取 mid，发起 1 个 `parse_versions` 请求
3. `parse_versions`: 解析分支列表，找到 N 个分支，发起 N 个 `parse_download_ajax` 请求
4. `parse_download_ajax`: 解析下载信息，收集到 `versions_data`
5. **关键**: 只有当 `len(versions_data) >= total_versions` 时，才 `yield item`

### 问题所在

**如果一个 mod 有多个分支，但某个分支的请求：**
- 超时了
- 返回了错误
- 返回了空数据
- 或者根本没有被发起

**那么这个 mod 就永远不会 yield item！**

### 证据

1. **日志显示**: mid=31465 有 15 个分支，Spider 关闭时只处理了 14 个（缺第 1 和第 15 个）
2. **统计数据**: 
   - `scheduler/enqueued`: 8521
   - `scheduler/dequeued`: 8521  
   - 所有请求都被处理了
3. **item 统计**: 
   - `item_scraped_count`: 1871
   - 但 stats_counter['items_scraped']: 1861
   - 差了 10 个（这 10 个是 mid=None 的错误页面）

## 推测

**有大量多分支 mods 的某些分支请求返回了异常数据（如空 CDATA、格式错误等），导致 `parse_download_ajax` 无法正常解析，但也没有 yield item。**

## 解决方案方向

###选项 1: 超时保护

在 `parse_download_ajax` 中添加一个机制：
- 如果某个分支请求超过 X 秒没有返回，认为它失败了
- 将已收集的 `versions_data` 强制 yield（即使不完整）

### 选项 2: 降级处理

修改 `parse_download_ajax` 的逻辑：
```python
# 当前逻辑
if len(versions_data) >= total_versions:
    yield item

# 改为
if len(versions_data) >= total_versions:
    yield item
elif len(versions_data) > 0 and 某个条件（如超时、Spider 关闭等）:
    # 即使不完整也 yield
    self.logger.warning(f"部分分支缺失，强制输出（mid={mid}）")
    yield item
```

### 选项 3: 在 Spider 关闭时清理

添加 `spider_closed` 信号处理器：
```python
def spider_closed(self, spider, reason):
    # 将所有未完成的 items 强制输出
    for mid, item_data in self.pending_items.items():
        if item_data.get('versions_data'):
            self.logger.warning(f"Spider 关闭，强制输出未完成 item: mid={mid}")
            yield item_data
```

### 选项 4: 移除分支依赖（最激进）

不等待所有分支处理完毕，每处理完一个分支就 yield 一个独立的 item：
```python
# 每个分支作为独立 item
yield {
    'mid': mid,
    'vid': vid,
    'branch_name': version_name,
    '...': '...',
}
```

这样就不会有"等待所有分支"的问题了。

## 下一步行动

1. ✅ 确认问题不在去重
2. ⏳ 分析具体哪些分支请求失败了
3. ⏳ 实施解决方案
4. ⏳ 重新测试

## 相关文件

- `/root/dev/eyeuc-scrapy/eyeuc/spiders/eyeuc_mods.py` (parse_download_ajax, line ~959)
- `/root/dev/eyeuc-scrapy/eyeuc/settings.py`

## 时间线

- 2025-10-17 01:00: 发现问题
- 2025-10-17 01:30: 确认问题不在去重
- 2025-10-17 01:57: 确认根本原因




