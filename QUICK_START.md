# 🚀 快速开始 - 分批抓取 List 182

## ✅ 已完成的实现

### 1. **分批抓取功能**
- ✅ 添加了 `start_page` 和 `end_page` 参数
- ✅ 支持指定页数范围进行抓取
- ✅ 文件名自动包含批次信息（如 `_p1-5_`）
- ✅ 达到 `end_page` 时自动停止翻页

### 2. **合并脚本**
- ✅ 自动识别批次文件
- ✅ 按页数顺序合并
- ✅ 自动去重（基于 `mid`）
- ✅ 输出统计信息

### 3. **自动化脚本**
- ✅ `batch_crawl.sh` - 完整的自动化批次抓取
- ✅ 进度显示、错误处理、失败重试提示
- ✅ 自动询问是否合并

### 4. **文档**
- ✅ `BATCH_CRAWL_GUIDE.md` - 详细使用指南
- ✅ `WHY_193_OK_BUT_182_FAIL.md` - 问题分析文档

## 🎯 立即开始

### 方法 1：手动分批（适合测试）

```bash
# 第 1 批：第 1-5 页
scrapy crawl eyeuc_mods \
    -a cookies=cookies.json \
    -a list_ids=182 \
    -a start_page=1 \
    -a end_page=5

# 第 2 批：第 6-10 页
scrapy crawl eyeuc_mods \
    -a cookies=cookies.json \
    -a list_ids=182 \
    -a start_page=6 \
    -a end_page=10

# 合并结果
python merge_batches.py 182
```

### 方法 2：自动化脚本（推荐）

```bash
# 抓取 list 182 的前 20 页（测试）
./batch_crawl.sh 182 20 5

# 抓取 list 182 的全部 100 页
./batch_crawl.sh 182 100 5
```

**参数说明**：
- `182` - list_id
- `20` / `100` - 总页数
- `5` - 每批页数

### 方法 3：自定义 Shell 脚本

```bash
#!/bin/bash
# 抓取前 30 页（测试用）

for start in 1 6 11 16 21 26; do
    end=$((start + 4))
    
    echo "抓取第 $start-$end 页..."
    scrapy crawl eyeuc_mods \
        -a cookies=cookies.json \
        -a list_ids=182 \
        -a start_page=$start \
        -a end_page=$end \
        -s LOG_LEVEL=WARNING
    
    sleep 10
done

# 合并
python merge_batches.py 182
```

## 📊 预期结果

### 测试场景（前 20 页）

**输入**：
```bash
./batch_crawl.sh 182 20 5
```

**输出文件**：
```
per_list_output/
├── eyeuc_list182_nba2k25_p1-5_20251017_120000.jsonl    (120 items)
├── eyeuc_list182_nba2k25_p6-10_20251017_120400.jsonl   (120 items)
├── eyeuc_list182_nba2k25_p11-15_20251017_120800.jsonl  (120 items)
├── eyeuc_list182_nba2k25_p16-20_20251017_121200.jsonl  (120 items)
└── eyeuc_list182_nba2k25_merged_20251017_121500.jsonl  (480 items)
```

**时间**：约 15-20 分钟

### 完整场景（100 页）

**输入**：
```bash
./batch_crawl.sh 182 100 5
```

**输出**：20 个批次文件 + 1 个合并文件，共 **~2386 items**

**时间**：约 80 分钟（顺序执行）

## ⚡ 并行加速（可选）

如果你有多核 CPU 或多台机器：

```bash
# 终端 1：第 1-20 页
./batch_crawl.sh 182 20 5 &

# 终端 2：第 21-40 页
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -a start_page=21 -a end_page=40 &

# 终端 3：第 41-60 页
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -a start_page=41 -a end_page=60 &

# 等待所有完成
wait

# 合并
python merge_batches.py 182
```

**时间缩短至 ~20-30 分钟**！

## 🔍 验证结果

```python
# 查看合并后的文件
python3 << 'EOF'
import json

with open('per_list_output/eyeuc_list182_nba2k25_merged_*.jsonl', 'r') as f:
    items = [json.loads(line) for line in f if line.strip()]

print(f"总计: {len(items)} items")
print(f"去重后 mids: {len(set(item['mid'] for item in items))}")

# 检查多分支 mods
multi_version = [item for item in items if len(item.get('versions', [])) > 1]
print(f"多分支 mods: {len(multi_version)}")

# 示例
print(f"\n示例（前 3 个）:")
for item in items[:3]:
    print(f"  - {item['title'][:50]} ({len(item['versions'])} 分支)")
EOF
```

## 📝 常见问题

### Q: 为什么要分批抓取？

**A**: 一次性抓取 2386 个 mods（100 页）存在以下风险：
- 长时间运行（1+ 小时）导致网络波动、服务器异常
- 多分支 mods 的某个分支失败会导致整个 mod 被丢弃
- 中途失败需要重新开始

分批抓取每批只需 3-5 分钟，出错可以单独重跑，更加稳定可控。

### Q: 批次大小怎么选？

**A**: 
- **小批次（3-5 页）**：更稳定，适合网络不稳定或复杂列表
- **大批次（10-20 页）**：更快，适合简单列表或稳定网络

推荐 **5 页/批**，平衡了速度和稳定性。

### Q: 合并后的数量为什么比预期少？

**A**: 可能原因：
1. 某些 mods 的多分支数据不完整（但已经尽可能保留）
2. 有重复的 `mid`（合并脚本会自动去重）
3. 某些页面可能有空洞（网站数据本身的问题）

可以查看合并脚本的输出："重复（已去除）: X"

### Q: 可以中途停止吗？

**A**: 可以！按 `Ctrl+C` 停止当前批次，已完成的批次文件会保留。稍后可以从中断的地方继续。

### Q: 文件太多怎么办？

**A**: 合并后可以删除批次文件：

```bash
# 合并
python merge_batches.py 182

# 验证合并文件正确后，删除批次文件
rm per_list_output/eyeuc_list182_*_p*.jsonl
```

## 🎉 总结

**已实现的核心功能**：
1. ✅ 分批抓取（`start_page` / `end_page`）
2. ✅ 自动合并（`merge_batches.py`）
3. ✅ 自动化脚本（`batch_crawl.sh`）
4. ✅ 详细文档（`BATCH_CRAWL_GUIDE.md`）

**使用建议**：
- 对于 **小列表（< 20 页）**：直接一次性抓取
- 对于 **大列表（> 20 页）**：使用分批抓取
- 先测试小批次（如前 10 页），确认无误后再完整抓取

现在你可以：
```bash
# 立即开始测试（前 10 页，约 5 分钟）
./batch_crawl.sh 182 10 5

# 或完整抓取（100 页，约 80 分钟）
./batch_crawl.sh 182 100 5
```

祝抓取顺利！🚀

