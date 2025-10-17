# 📚 分批抓取使用指南

## 🎯 为什么需要分批抓取？

对于大型列表（如 list 182，有 2386 个 mods，100 页），一次性抓取存在以下问题：

1. **长时间运行（1+ 小时）**：网络波动、服务器异常的风险增加
2. **多分支 mods 的处理**：某些分支请求失败会导致整个 mod 被丢弃
3. **难以恢复**：如果中途失败，需要重新开始
4. **资源占用**：长时间占用内存和网络资源

**分批抓取的优势**：
- ✅ 每批只需 3-5 分钟
- ✅ 出错可以单独重跑某一批
- ✅ 可以并行运行多批（不同机器/进程）
- ✅ 更容易监控进度

## 📖 使用方法

### 1. 基本用法

```bash
# 抓取 list 182 的第 1-5 页
scrapy crawl eyeuc_mods \
    -a cookies=cookies.json \
    -a list_ids=182 \
    -a start_page=1 \
    -a end_page=5

# 抓取 list 182 的第 6-10 页
scrapy crawl eyeuc_mods \
    -a cookies=cookies.json \
    -a list_ids=182 \
    -a start_page=6 \
    -a end_page=10
```

### 2. 批量抓取脚本

创建一个 shell 脚本 `batch_crawl_182.sh`：

```bash
#!/bin/bash
# 分批抓取 list 182（共 100 页，每批 5 页）

LIST_ID=182
BATCH_SIZE=5
TOTAL_PAGES=100

for start in $(seq 1 $BATCH_SIZE $TOTAL_PAGES); do
    end=$((start + BATCH_SIZE - 1))
    
    echo "========================================"
    echo "抓取第 $start-$end 页 (批次 $((start / BATCH_SIZE + 1))/20)"
    echo "========================================"
    
    scrapy crawl eyeuc_mods \
        -a cookies=cookies.json \
        -a list_ids=$LIST_ID \
        -a start_page=$start \
        -a end_page=$end
    
    # 检查退出状态
    if [ $? -ne 0 ]; then
        echo "❌ 批次 $start-$end 失败，停止抓取"
        exit 1
    fi
    
    echo "✅ 批次 $start-$end 完成"
    echo ""
    
    # 可选：批次之间休息 10 秒
    sleep 10
done

echo "🎉 所有批次完成！"
```

运行：

```bash
chmod +x batch_crawl_182.sh
./batch_crawl_182.sh
```

### 3. 合并结果

抓取完所有批次后，使用 `merge_batches.py` 合并：

```bash
# 方法 1：指定 list_id（推荐）
python merge_batches.py 182

# 方法 2：指定文件模式
python merge_batches.py "per_list_output/eyeuc_list182_*_p*.jsonl"
```

**输出**：
```
📄 找到 20 个文件:
  - eyeuc_list182_nba2k25_p1-5_20251017_114845.jsonl
  - eyeuc_list182_nba2k25_p6-10_20251017_115256.jsonl
  ...
  - eyeuc_list182_nba2k25_p96-100_20251017_123456.jsonl

🔄 合并中...

✅ 合并完成!
  - 总 items: 2386
  - 重复（已去除）: 15
  - 输出文件: per_list_output/eyeuc_list182_nba2k25_merged_20251017_124500.jsonl
```

## 🔧 高级用法

### 并行抓取（多进程）

如果你有多核 CPU 或多台机器，可以并行运行多批：

```bash
# 终端 1：抓取第 1-10 页
scrapy crawl eyeuc_mods -a list_ids=182 -a start_page=1 -a end_page=10 &

# 终端 2：抓取第 11-20 页
scrapy crawl eyeuc_mods -a list_ids=182 -a start_page=11 -a end_page=20 &

# 终端 3：抓取第 21-30 页
scrapy crawl eyeuc_mods -a list_ids=182 -a start_page=21 -a end_page=30 &

# 等待所有进程完成
wait

# 合并
python merge_batches.py 182
```

### 只重跑失败的批次

如果某一批次失败（如第 46-50 页），只需重跑那一批：

```bash
scrapy crawl eyeuc_mods \
    -a cookies=cookies.json \
    -a list_ids=182 \
    -a start_page=46 \
    -a end_page=50
```

### 自定义批次大小

根据列表的复杂度调整批次大小：

- **简单列表**（少量多分支 mods）：10-20 页/批
- **中等列表**：5-10 页/批
- **复杂列表**（大量多分支 mods）：3-5 页/批

## 📊 输出文件

### 批次文件

每个批次的输出文件名包含页数范围：

```
eyeuc_list182_nba2k25_p1-5_20251017_114845.jsonl
eyeuc_list182_nba2k25_p6-10_20251017_115256.jsonl
eyeuc_list182_nba2k25_p11-15_20251017_120130.jsonl
...
```

### 合并文件

合并后的文件名包含 `merged` 标识：

```
eyeuc_list182_nba2k25_merged_20251017_124500.jsonl
```

## ⚠️ 注意事项

1. **保持 cookies 有效**：长时间抓取时，cookies 可能过期，建议每批更新 cookies
2. **网络稳定性**：如果网络不稳定，减小批次大小（如 3 页/批）
3. **去重**：合并脚本会自动去重（基于 `mid`），所以重跑批次不会产生重复数据
4. **文件命名**：确保每批的文件名中包含 `_p{start}-{end}_` 格式，否则合并脚本无法识别

## 🚀 完整示例

### 抓取 list 182（2386 个 mods，100 页）

```bash
# 1. 创建批次脚本
cat > batch_crawl.sh << 'EOF'
#!/bin/bash
for start in {1..100..5}; do
    end=$((start + 4))
    echo "抓取第 $start-$end 页..."
    scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -a start_page=$start -a end_page=$end
    sleep 10
done
EOF

# 2. 运行
chmod +x batch_crawl.sh
./batch_crawl.sh

# 3. 合并
python merge_batches.py 182

# 4. 验证
python -c "
import json
with open('per_list_output/eyeuc_list182_nba2k25_merged_*.jsonl', 'r') as f:
    count = sum(1 for line in f if line.strip())
    print(f'总计: {count} 个 items')
"
```

## 📈 预估时间

根据测试，每批（5 页，~120 个 mods）需要约 **3-4 分钟**。

对于 list 182（100 页，20 批）：
- **顺序抓取**：20 批 × 4 分钟 = **80 分钟**
- **并行抓取（4 进程）**：20 分钟
- **合并时间**：< 1 分钟

## 🎯 最佳实践

1. **先测试小批次**：先抓 1-5 页，确认没问题再大批量抓取
2. **设置日志级别**：`-s LOG_LEVEL=WARNING` 减少日志输出
3. **监控进度**：使用 `tail -f` 实时查看日志
4. **备份 cookies**：定期更新 `cookies.json`，避免过期
5. **分时段抓取**：避开网站高峰期（如晚上抓取）

## 🐛 常见问题

### Q: 合并时提示"未找到批次文件"？

A: 检查文件名格式是否正确，必须包含 `_p{start}-{end}_` 模式。

### Q: 合并后的总数少于预期？

A: 可能有重复的 `mid`，合并脚本会自动去重。检查日志中的"重复（已去除）"数量。

### Q: 某一批次抓取失败怎么办？

A: 只需重跑那一批，合并时会自动去重：

```bash
scrapy crawl eyeuc_mods -a list_ids=182 -a start_page=46 -a end_page=50
```

### Q: 可以改变批次大小吗？

A: 可以！调整 `start_page` 和 `end_page` 的间隔即可：

```bash
# 10 页/批
-a start_page=1 -a end_page=10

# 3 页/批
-a start_page=1 -a end_page=3
```

## 🎉 总结

分批抓取是处理大型列表的**最佳实践**，具有以下优势：

- ✅ **稳定性高**：单批失败不影响其他批次
- ✅ **易于恢复**：可以单独重跑失败的批次
- ✅ **进度可控**：清晰看到每批的进度
- ✅ **并行化**：可以多进程/多机器并行抓取

建议对于 **超过 20 页** 的列表，都使用分批抓取！

