# 🚀 并行抓取指南

## ✅ 新功能：起始页参数

`batch_crawl.sh` 现在支持指定起始页，可以并行抓取不同页数范围！

### 📝 新的命令格式

```bash
./batch_crawl.sh <list_id> <end_page> [batch_size] [cookies] [start_page]
```

**参数说明：**
- `list_id` - 列表 ID（必需）
- `end_page` - 结束页（必需）
- `batch_size` - 批次大小，默认 5
- `cookies` - cookies 文件，默认 `cookies.json`
- `start_page` - **起始页，默认 1** ⭐

### 🎯 使用示例

#### 1. 顺序抓取（默认）

```bash
# 抓取第 1-100 页
./batch_crawl.sh 182 100 5

# 等价于
./batch_crawl.sh 182 100 5 cookies.json 1
```

#### 2. 抓取指定范围

```bash
# 只抓取第 26-50 页
./batch_crawl.sh 182 50 5 cookies.json 26

# 只抓取第 51-75 页
./batch_crawl.sh 182 75 5 cookies.json 51
```

#### 3. 并行抓取（推荐 🔥）

**方法 1：手动并行（适合测试）**

```bash
# 终端 1: 第 1-20 页
./batch_crawl.sh 182 25 5 cookies.json 1 &

./batch_crawl.sh 182 50 5 cookies.json 26 &

./batch_crawl.sh 182 75 5 cookies.json 51 &

./batch_crawl.sh 182 100 5 cookies.json 76 &







# 终端 2: 第 51-100 页
./batch_crawl.sh 182 100 5 cookies.json 51 &

# 等待完成
wait

# 合并
python3 merge_batches.py 182
```

**方法 2：使用提供的示例脚本**

```bash
# 4 进程并行抓取（25 页/进程）
./parallel_crawl_example.sh
```

**方法 3：自定义并行脚本（最灵活）**

```bash
#!/bin/bash
# 2 进程并行抓取 list 182

LIST_ID=182

# 进程 1: 第 1-50 页
./batch_crawl.sh $LIST_ID 50 5 cookies.json 1 > logs/part1.log 2>&1 &
PID1=$!

# 进程 2: 第 51-100 页
./batch_crawl.sh $LIST_ID 100 5 cookies.json 51 > logs/part2.log 2>&1 &
PID2=$!

echo "任务已启动："
echo "  - 进程 1 (PID: $PID1): 第 1-50 页"
echo "  - 进程 2 (PID: $PID2): 第 51-100 页"

# 等待完成
wait $PID1 $PID2

# 合并
python3 merge_batches.py $LIST_ID
```

## 📊 并行策略建议

### 根据总页数选择并行数

| 总页数 | 建议进程数 | 每进程页数 | 预计总时间 |
|--------|-----------|-----------|-----------|
| 20 页  | 1         | 20        | ~8 分钟   |
| 50 页  | 2         | 25        | ~10 分钟  |
| 100 页 | 2-4       | 25-50     | ~20-30 分钟 |
| 200 页 | 4-8       | 25-50     | ~40-60 分钟 |

### CPU 核心数建议

```bash
# 查看 CPU 核心数
nproc

# 建议并行进程数 = CPU 核心数 / 2
# 例如 8 核 CPU → 4 个并行进程
```

## 🎯 完整示例：List 182 (100 页)

### 方案 A：2 进程并行（简单）

```bash
# 创建日志目录
mkdir -p logs

# 进程 1
./batch_crawl.sh 182 50 5 cookies.json 1 > logs/p1-50.log 2>&1 &

# 进程 2
./batch_crawl.sh 182 100 5 cookies.json 51 > logs/p51-100.log 2>&1 &

# 监控进度
tail -f logs/p1-50.log

# 等待完成
wait

# 合并
python3 merge_batches.py 182
```

**预计时间：** ~25-30 分钟（相比顺序 80 分钟，节省 60%）

### 方案 B：4 进程并行（推荐）

```bash
mkdir -p logs

# 4 个进程同时运行
./batch_crawl.sh 182 25 5 cookies.json 1 > logs/p1-25.log 2>&1 &
./batch_crawl.sh 182 50 5 cookies.json 26 > logs/p26-50.log 2>&1 &
./batch_crawl.sh 182 75 5 cookies.json 51 > logs/p51-75.log 2>&1 &
./batch_crawl.sh 182 100 5 cookies.json 76 > logs/p76-100.log 2>&1 &

# 等待完成
wait

# 合并
python3 merge_batches.py 182
```

**预计时间：** ~15-20 分钟（相比顺序 80 分钟，节省 75%）

### 方案 C：使用提供的脚本（最简单）

```bash
# 一键并行抓取（4 进程）
./parallel_crawl_example.sh
```

## 🔍 监控并行任务

### 查看所有运行中的任务

```bash
ps aux | grep batch_crawl
```

### 实时查看单个任务日志

```bash
tail -f logs/p1-50.log
```

### 同时查看多个任务（使用 tmux）

```bash
# 安装 tmux（如果未安装）
sudo apt-get install tmux

# 启动 tmux
tmux

# 分割窗口
Ctrl+B 然后按 "    # 水平分割
Ctrl+B 然后按 %    # 垂直分割

# 在不同窗口查看不同日志
tail -f logs/p1-25.log
tail -f logs/p26-50.log
# ...
```

### 查看所有任务的最新进度

```bash
# 一次性查看所有日志的最后 10 行
for log in logs/*.log; do
    echo "=== $log ==="
    tail -10 "$log"
    echo ""
done
```

## ⚠️ 注意事项

### 1. 不要并行太多

- **建议最多 4-8 个进程**
- 过多进程会：
  - 占用过多网络带宽
  - 可能被服务器限流
  - 增加系统负载

### 2. 确保页数范围不重叠

```bash
# ❌ 错误：范围重叠
./batch_crawl.sh 182 50 5 cookies.json 1 &   # 第 1-50 页
./batch_crawl.sh 182 75 5 cookies.json 40 &  # 第 40-75 页（重叠！）

# ✅ 正确：范围不重叠
./batch_crawl.sh 182 50 5 cookies.json 1 &   # 第 1-50 页
./batch_crawl.sh 182 100 5 cookies.json 51 & # 第 51-100 页
```

### 3. 合并会自动去重

即使有重叠，`merge_batches.py` 也会自动去重（基于 `mid`），所以不用太担心。

### 4. 失败重跑

如果某个进程失败，只需重跑那个范围：

```bash
# 假设第 51-75 页失败了
./batch_crawl.sh 182 75 5 cookies.json 51

# 然后重新合并
python3 merge_batches.py 182
```

## 📈 性能对比

### List 182 (100 页，~2386 items)

| 方案 | 进程数 | 预计时间 | 相比顺序 | 资源占用 |
|------|-------|---------|---------|---------|
| 顺序抓取 | 1 | 80 分钟 | - | 低 |
| 2 进程并行 | 2 | 25-30 分钟 | ⬇️ 60% | 中 |
| 4 进程并行 | 4 | 15-20 分钟 | ⬇️ 75% | 中高 |
| 8 进程并行 | 8 | 10-15 分钟 | ⬇️ 80% | 高 |

**推荐：4 进程并行** - 平衡了速度和资源占用

## 🎓 高级技巧

### 1. 动态调整批次大小

不同范围使用不同批次大小：

```bash
# 前面部分（可能更复杂）：小批次
./batch_crawl.sh 182 50 3 cookies.json 1 &

# 后面部分（可能更简单）：大批次
./batch_crawl.sh 182 100 10 cookies.json 51 &
```

### 2. 错峰抓取

```bash
# 立即开始前 50 页
./batch_crawl.sh 182 50 5 cookies.json 1 &

# 等 10 分钟后再开始后 50 页
(sleep 600 && ./batch_crawl.sh 182 100 5 cookies.json 51) &
```

### 3. 使用 GNU Parallel（高级）

```bash
# 安装 GNU Parallel
sudo apt-get install parallel

# 创建任务列表
cat > tasks.txt << EOF
./batch_crawl.sh 182 25 5 cookies.json 1
./batch_crawl.sh 182 50 5 cookies.json 26
./batch_crawl.sh 182 75 5 cookies.json 51
./batch_crawl.sh 182 100 5 cookies.json 76
EOF

# 并行执行（最多 4 个同时）
parallel -j 4 < tasks.txt

# 合并
python3 merge_batches.py 182
```

## 📝 检查清单

抓取前：
- [ ] 确认 cookies.json 文件存在且有效
- [ ] 确认有足够的磁盘空间（~100MB per 100 pages）
- [ ] 创建 logs 目录：`mkdir -p logs`
- [ ] 规划好页数范围（不重叠）

抓取中：
- [ ] 监控日志文件：`tail -f logs/*.log`
- [ ] 检查系统资源：`htop` 或 `top`
- [ ] 必要时调整并行数

抓取后：
- [ ] 检查所有进程是否完成：`ps aux | grep batch_crawl`
- [ ] 合并结果：`python3 merge_batches.py <list_id>`
- [ ] 验证 item 数量
- [ ] 清理临时文件（可选）

## 🎉 总结

**顺序抓取：**
```bash
./batch_crawl.sh 182 100 5
```
- ✅ 简单
- ❌ 慢（80 分钟）

**并行抓取：**
```bash
./batch_crawl.sh 182 50 5 cookies.json 1 &
./batch_crawl.sh 182 100 5 cookies.json 51 &
wait
python3 merge_batches.py 182
```
- ✅ 快（25 分钟）
- ✅ 灵活
- ⚠️ 需要多一点配置

**一键并行：**
```bash
./parallel_crawl_example.sh
```
- ✅ 最简单
- ✅ 最快（15-20 分钟）
- ⚠️ 固定 4 进程

选择适合你的方案，开始高效抓取！🚀

