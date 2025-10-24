# 🎯 一键爬取指南

## 🚀 超简单：smart_crawl.sh

**一条命令搞定所有！自动并行、自动合并、自动导入。**

### 基础用法

```bash
./smart_crawl.sh <list_id> <total_pages>
```

### 示例

```bash
# 自动爬取 list 182 的 100 页
./smart_crawl.sh 182 100

# 自动爬取 list 193 的 5 页
./smart_crawl.sh 193 5
```

### 特性

- ✅ **自动选择最佳并行数**
  - ≤10 页 → 1 进程
  - ≤30 页 → 2 进程
  - ≤50 页 → 3 进程
  - ≤75 页 → 4 进程
  - ≤100 页 → 5 进程 ⚡
  - ≤150 页 → 6 进程
  - ≤200 页 → 8 进程
  - >200 页 → 10 进程

- ✅ **实时进度条**
  ```
  进度: [████████████████░░░░░░░░] 60% (3/5)
  ```

- ✅ **自动合并结果**
- ✅ **自动统计数据**
- ✅ **可选自动导入数据库**

---

## 🎛️ 灵活控制：parallel_crawl.sh

**需要更多控制时使用。**

### 基础用法

```bash
./parallel_crawl.sh <list_id> <total_pages> [parallel_jobs] [batch_size] [cookies]
```

### 示例

```bash
# 默认 4 进程
./parallel_crawl.sh 182 100

# 指定 8 进程
./parallel_crawl.sh 182 100 8

# 自定义批次大小
./parallel_crawl.sh 182 100 4 10
```

### 特性

- ✅ **手动指定并行数**
- ✅ **自定义批次大小**
- ✅ **详细的任务分配信息**
- ✅ **保存 PID 方便管理**
- ⚠️ **需要手动合并结果**

---

## 📊 三种方案对比

### 方案 1：smart_crawl.sh（推荐 🌟）

```bash
./smart_crawl.sh 182 100
```

| 优点 | 缺点 |
|------|------|
| ✅ 一条命令全搞定 | ⚠️ 自动化程度高，不适合微调 |
| ✅ 自动并行 | |
| ✅ 自动合并 | |
| ✅ 实时进度条 | |
| ✅ 可选自动导入 | |

**适合：** 日常使用、快速抓取、懒人必备

---

### 方案 2：parallel_crawl.sh

```bash
./parallel_crawl.sh 182 100 4
# 完成后手动合并
python3 merge_batches.py 182
```

| 优点 | 缺点 |
|------|------|
| ✅ 可控性强 | ⚠️ 需要手动合并 |
| ✅ 自定义参数 | ⚠️ 多一步操作 |
| ✅ 适合复杂场景 | |

**适合：** 需要精细控制、大规模抓取、高级用户

---

### 方案 3：手动并行（原始方法）

```bash
# 手动开多个终端
./batch_crawl.sh 182 50 5 cookies.json 1 &
./batch_crawl.sh 182 100 5 cookies.json 51 &
wait
python3 merge_batches.py 182
```

| 优点 | 缺点 |
|------|------|
| ✅ 最大灵活性 | ❌ 太麻烦 |
| ✅ 完全可控 | ❌ 容易出错 |
| | ❌ 需要手动计算范围 |

**适合：** 特殊需求、调试、学习原理

---

## 🎯 使用建议

### 快速抓取（推荐）

```bash
# 小列表（< 10 页）
./smart_crawl.sh 193 5

# 中等列表（< 100 页）
./smart_crawl.sh 182 100

# 大列表（> 100 页）
./smart_crawl.sh 182 200
```

### 高级控制

```bash
# 需要更多并行（8 核 CPU）
./parallel_crawl.sh 182 200 8

# 减少批次大小（提高稳定性）
./parallel_crawl.sh 182 100 4 3

# 大批次（提高速度）
./parallel_crawl.sh 182 100 2 10
```

### 分批抓取（断点续抓）

```bash
# 第一次：抓前 50 页
./smart_crawl.sh 182 50

# 第二次：继续抓 51-100 页
./parallel_crawl.sh 182 100 4 5 cookies.json 51

# 合并所有
python3 merge_batches.py 182
```

---

## 🔍 监控与管理

### 查看运行中的任务

```bash
# 查看所有爬虫进程
ps aux | grep batch_crawl

# 查看日志
tail -f logs/list182_*/job0*.log

# 查看所有日志的最新状态
ls -lh logs/list182_*/
tail logs/list182_*/*.log
```

### 停止任务

```bash
# 找到 PID 文件
ls logs/list182_*/pids.txt

# 停止所有任务
kill $(cat logs/list182_TIMESTAMP/pids.txt)

# 或者直接杀掉所有
pkill -f batch_crawl
```

### 查看结果

```bash
# 查看输出文件
ls -lh per_list_output/

# 统计 items
wc -l per_list_output/eyeuc_list182_*_merged_*.jsonl

# 检查时间字段覆盖率
python3 -c "
import json
total = has_created = has_updated = 0
with open('per_list_output/eyeuc_list182_nba2k25_merged_*.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        total += 1
        if data.get('metadata', {}).get('created_at'): has_created += 1
        if data.get('metadata', {}).get('last_updated'): has_updated += 1
print(f'总计: {total}')
print(f'created_at: {has_created}/{total} ({has_created*100//total}%)')
print(f'last_updated: {has_updated}/{total} ({has_updated*100//total}%)')
"
```

---

## ⚡ 性能对比

### List 182 (100 页, ~2400 items)

| 方案 | 命令 | 耗时 | 手动操作 |
|------|------|------|---------|
| 顺序抓取 | `./batch_crawl.sh 182 100 5` | ~80 分钟 | 开 1 个终端 |
| 手动并行 | 开 4 个终端分别运行 | ~20 分钟 | 开 4 个终端 😰 |
| parallel_crawl.sh | `./parallel_crawl.sh 182 100 4` | ~20 分钟 | 开 1 个终端 ✅ |
| smart_crawl.sh | `./smart_crawl.sh 182 100` | ~20 分钟 | 开 1 个终端 🌟 |

### List 182 (200 页, ~4800 items)

| 方案 | 命令 | 耗时 | 并行数 |
|------|------|------|--------|
| smart_crawl.sh | `./smart_crawl.sh 182 200` | ~30 分钟 | 8 进程（自动） |
| parallel_crawl.sh | `./parallel_crawl.sh 182 200 8` | ~30 分钟 | 8 进程（手动） |
| 顺序抓取 | `./batch_crawl.sh 182 200 5` | ~160 分钟 | 1 进程 |

**节省时间：** 80% ⚡

---

## 🛠️ 故障排除

### 问题 1：所有任务立即完成但没有输出

**可能原因：** cookies 过期

```bash
# 检查 cookies
cat cookies.json

# 重新获取 cookies（浏览器 DevTools → Application → Cookies）
```

### 问题 2：某些任务卡住不动

**解决方案：**

```bash
# 1. 找到卡住的任务
ps aux | grep batch_crawl

# 2. 杀掉该任务
kill <PID>

# 3. 重新运行那个范围
./batch_crawl.sh 182 50 5 cookies.json 26

# 4. 重新合并
python3 merge_batches.py 182
```

### 问题 3：合并后 items 数量不对

**检查：**

```bash
# 查看所有分批文件
ls -lh per_list_output/eyeuc_list182_*_p*.jsonl

# 每个文件的 items 数
wc -l per_list_output/eyeuc_list182_*_p*.jsonl

# 合并后的总数
wc -l per_list_output/eyeuc_list182_*_merged_*.jsonl
```

**修复：** 如果某个批次文件为空或很小，重新抓取那个范围。

### 问题 4：内存/CPU 占用过高

**解决方案：**

```bash
# 减少并行数
./parallel_crawl.sh 182 100 2  # 从 4 降到 2

# 或增加批次间隔
# 修改 parallel_crawl.sh 中的 sleep 2 改为 sleep 5
```

---

## 🎓 最佳实践

### 1. 首次抓取

```bash
# 先抓 5 页测试
./smart_crawl.sh 182 5

# 检查结果
tail per_list_output/eyeuc_list182_*.jsonl

# 如果 OK，全量抓取
./smart_crawl.sh 182 100
```

### 2. 定时抓取（更新数据）

```bash
# 创建 cron 任务
crontab -e

# 每天凌晨 2 点抓取
0 2 * * * cd /root/dev/eyeuc-scrapy && ./smart_crawl.sh 182 100 >> logs/cron.log 2>&1
```

### 3. 批量抓取多个列表

```bash
#!/bin/bash
# batch_all.sh
for list_id in 182 193 172; do
    echo "抓取 list $list_id..."
    ./smart_crawl.sh $list_id 100
    sleep 60  # 列表之间间隔 1 分钟
done
```

### 4. 网络不稳定时

```bash
# 减小批次，增加并行
./parallel_crawl.sh 182 100 8 3

# 3 页一批，8 个并行 → 更快失败重试
```

---

## 📚 相关文档

- 📄 `PARALLEL_CRAWL_GUIDE.md` - 并行爬取原理详解
- 📄 `BATCH_CRAWL_GUIDE.md` - 批次爬取完整指南
- 📄 `DATABASE_IMPORT_README.md` - 数据库导入说明
- 📄 `TIME_FIX_SUMMARY.md` - 时间字段修复说明

---

## 🎉 总结

### 日常使用（推荐）

```bash
./smart_crawl.sh <list_id> <pages>
```

### 需要控制

```bash
./parallel_crawl.sh <list_id> <pages> <jobs>
```

### 特殊场景

```bash
# 手动并行 + 合并
./batch_crawl.sh ... &
./batch_crawl.sh ... &
wait
python3 merge_batches.py <list_id>
```

**从此告别手动开 5 个终端！** 🎊

