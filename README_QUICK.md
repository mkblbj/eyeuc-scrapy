# 🚀 快速开始

## 一行命令搞定

```bash
./smart_crawl.sh 182 100
```

就这么简单！✨

---

## 详细说明

### 📦 准备工作

1. **确保 cookies.json 存在且有效**
   ```bash
   ls -lh cookies.json
   ```

2. **给脚本执行权限**（只需一次）
   ```bash
   chmod +x *.sh
   ```

### 🎯 三种使用方式

#### 1. 智能模式（推荐 ⭐）

**自动一切：并行、合并、统计**

```bash
./smart_crawl.sh <list_id> <pages>
```

示例：
```bash
./smart_crawl.sh 182 100    # 爬 100 页，自动选 4 进程
./smart_crawl.sh 193 5      # 爬 5 页，自动选 1 进程
```

特点：
- ✅ 自动选择最佳并行数
- ✅ 实时进度条
- ✅ 自动合并结果
- ✅ 询问是否导入数据库

---

#### 2. 灵活模式

**手动控制并行数和批次大小**

```bash
./parallel_crawl.sh <list_id> <pages> [jobs] [batch_size]
```

示例：
```bash
./parallel_crawl.sh 182 100 4      # 4 进程
./parallel_crawl.sh 182 100 8 10   # 8 进程，每批 10 页
```

特点：
- ✅ 精细控制
- ⚠️ 需要手动合并：`python3 merge_batches.py 182`

---

#### 3. 单进程模式

**简单场景，无需并行**

```bash
./batch_crawl.sh <list_id> <pages> [batch_size] [cookies] [start_page]
```

示例：
```bash
./batch_crawl.sh 193 5                   # 爬 1-5 页
./batch_crawl.sh 182 50 5 cookies.json 1  # 爬 1-50 页
```

---

### 📊 实际使用示例

#### 小列表（<10 页）
```bash
./smart_crawl.sh 193 5
# 耗时：~2 分钟
```

#### 中等列表（~100 页）
```bash
./smart_crawl.sh 182 100
# 耗时：~15 分钟（5 进程并行）⚡
```

#### 大列表（>100 页）
```bash
./smart_crawl.sh 182 200
# 耗时：~40 分钟（8 进程并行）
```

---

### 🔍 查看结果

```bash
# 列出所有输出文件
ls -lh per_list_output/

# 查看合并后的文件
ls -lh per_list_output/*_merged_*.jsonl

# 统计 items 数量
wc -l per_list_output/eyeuc_list182_*_merged_*.jsonl
```

---

### 💾 导入数据库

```bash
# 单个文件
python3 scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/eyeuc_list182_*_merged_*.jsonl"

# 所有合并文件
python3 scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*_merged_*.jsonl"

# 验证
python3 scripts/verify_database.py
```

---

### ⚠️ 常见问题

#### Q: 提示 "可能需要登录"
**A:** cookies 过期了，需要重新获取
```bash
# 1. 浏览器登录 bbs.eyeuc.com
# 2. F12 → Application → Cookies
# 3. 复制所有 cookies 到 cookies.json
```

#### Q: 任务显示失败但文件都有
**A:** 这是正常的！Scrapy 有时会返回非零退出码。检查：
```bash
# 看看是否有输出文件
ls -lh per_list_output/eyeuc_list182_*_p*.jsonl

# 如果有文件，手动合并
python3 merge_batches.py 182
```

#### Q: 如何停止正在运行的任务
**A:** 
```bash
# 方法1：Ctrl+C（前台运行时）

# 方法2：找到并杀掉进程
ps aux | grep batch_crawl
kill <PID>

# 方法3：杀掉所有
pkill -f batch_crawl
```

#### Q: 想重新爬某几页
**A:**
```bash
# 只爬 26-50 页
./batch_crawl.sh 182 50 5 cookies.json 26

# 然后重新合并
python3 merge_batches.py 182
```

---

### 📈 性能参考

| 列表 | 页数 | 模式 | 耗时 | 命令 |
|------|------|------|------|------|
| 193 | 5 | 智能 | ~2 分钟 | `./smart_crawl.sh 193 5` |
| 182 | 100 | 智能(5进程) | ~15 分钟 ⚡ | `./smart_crawl.sh 182 100` |
| 182 | 100 | 灵活(8进程) | ~12 分钟 | `./parallel_crawl.sh 182 100 8` |
| 182 | 200 | 智能(8进程) | ~30 分钟 | `./smart_crawl.sh 182 200` |

---

### 📚 更多文档

- 📄 `ONE_COMMAND_CRAWL.md` - 完整的一键爬取指南
- 📄 `PARALLEL_CRAWL_GUIDE.md` - 并行爬取详解
- 📄 `BATCH_CRAWL_GUIDE.md` - 批次爬取说明
- 📄 `DATABASE_IMPORT_README.md` - 数据库导入详解
- 📄 `docs/BACKEND_DB_INTEGRATION.md` - 后端对接文档
- 📄 `TIME_FIX_SUMMARY.md` - 时间字段修复说明

---

## 🎉 开始使用

```bash
# 最简单的方式
./smart_crawl.sh 182 100

# 就这样！坐下来喝杯咖啡 ☕
```

**从此告别手动开 5 个终端的烦恼！** 🎊

