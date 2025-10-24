# 🎮 EyeUC 游戏 Mods 爬虫

自动爬取 EyeUC 网站游戏 Mods 数据，并导入 MySQL 数据库。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

编辑 `.env` 文件（已配置好）：

```bash
MYSQL_HOST=162.43.7.144
MYSQL_PORT=3306
MYSQL_USER=eyeuc
MYSQL_PASSWORD=Djy4QzH3BTTDeEPC
MYSQL_DATABASE=eyeuc
MYSQL_SSL=false

# 全量替换模式：每次导入前删除所有旧数据
FULL_REPLACE=true

# 自动清理源文件
CLEANUP=true
```

### 3. 运行定时任务

```bash
# 这是唯一需要执行的脚本
./automation/run_scheduled_crawls.sh
```

**功能**：
- ✅ 爬取 list 182, 193, 172, 93
- ✅ 全量替换导入数据库（删除旧数据，保持最新）
- ✅ 自动清理源文件（节省磁盘空间）
- ✅ 验证数据完整性
- ✅ 记录详细日志 (`logs/scheduled/`)

---

## 📊 数据库结构

```
lists (游戏列表)
  ├─ mods (资源)
  │   ├─ images (图片)
  │   └─ versions (分支)
  │       └─ downloads (附件)
```

---

## 🔧 高级用法

### 手动爬取单个列表

```bash
# 爬取 list 193，前 50 页
bash smart_crawl.sh 193 50
```

### 手动导入数据库

```bash
# 全量替换导入（默认）
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 增量导入（不删除旧数据）
FULL_REPLACE=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 禁用自动清理（保留源文件）
CLEANUP=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

### 验证数据

```bash
python scripts/verify_database.py
```

---

## 📚 核心文档

### 必读
- **QUICK_START_FULL_REPLACE.md** - 全量替换快速上手
- **DATABASE_IMPORT_README.md** - 数据库导入完整手册

### 参考
- **docs/FULL_REPLACE_GUIDE.md** - 全量替换详细说明
- **SMART_CRAWL_README.md** - 智能爬取说明
- **docs/AUTO_CLEANUP_GUIDE.md** - 自动清理功能
- **DIRECT_LINKS_GUIDE.md** - 直链获取脚本
- **docs/FRONTEND_VERSION_INTRO_DISPLAY.md** - 前端显示指南

---

## 🎯 核心特性

### ✅ 智能爬取
- 自动分配并行任务
- 实时监控进度
- 自动合并结果

### ✅ 全量替换
- 每次导入前删除所有旧数据
- 确保数据库与网站完全同步
- 事务保护，失败自动回滚

### ✅ 自动清理
- 导入成功后自动删除源文件
- 防止磁盘空间累积
- 每月节省 13 GB

### ✅ 数据完整性
- 幂等导入（可重复运行）
- 外键约束
- 唯一索引防止重复

---

## 📁 项目结构

```
eyeuc-scrapy/
├── eyeuc/
│   └── spiders/
│       └── eyeuc_mods.py          # 核心爬虫
├── scripts/
│   ├── import_eyeuc_jsonl_to_mysql.py  # 数据导入
│   ├── verify_database.py              # 数据验证
│   └── fetch_direct_links.py           # 直链获取
├── automation/
│   └── run_scheduled_crawls.sh    # 定时任务（唯一需要执行的）
├── smart_crawl.sh                 # 智能爬取脚本
├── batch_crawl.sh                 # 批量爬取脚本
├── schema.sql                     # 数据库结构
├── .env                           # 配置文件
└── logs/                          # 日志目录
```

---

## 🔧 定时任务设置

使用 cron 定期运行：

```bash
# 编辑 crontab
crontab -e

# 每 6 小时运行一次（0点、6点、12点、18点）
0 */6 * * * cd /root/dev/eyeuc-scrapy && ./automation/run_scheduled_crawls.sh
```

---

## 🐛 故障排查

### 日志位置
```bash
# 定时任务日志
logs/scheduled/run_*.log

# 爬取日志
logs/list*_*/batch_*_*.log
```

### 常见问题

**Q: 数据库连接失败？**
```bash
# 检查 .env 配置
cat .env

# 测试数据库连接
python scripts/verify_database.py
```

**Q: 爬取失败？**
```bash
# 检查 cookies 是否有效
ls -lh cookies.json

# 查看详细日志
tail -f logs/scheduled/run_*.log
```

**Q: 磁盘空间不足？**
```bash
# 检查配置
grep CLEANUP .env  # 应该是 true

# 手动清理
rm -rf per_list_output/*.jsonl
```

---

## 📊 监控

### 检查最近运行状态

```bash
# 查看最新日志
tail -100 logs/scheduled/run_$(ls -t logs/scheduled/ | head -1)

# 统计数据
python scripts/verify_database.py
```

### 数据库统计

```sql
-- 总资源数
SELECT COUNT(*) FROM mods;

-- 按列表统计
SELECT list_id, game, COUNT(*) FROM mods GROUP BY list_id, game;

-- 最新更新时间
SELECT MAX(last_updated) FROM mods;
```

---

## 🎉 总结

### 一键运行
```bash
./automation/run_scheduled_crawls.sh
```

### 核心特性
- ✅ 全量替换：数据库始终最新
- ✅ 自动清理：节省磁盘空间
- ✅ 智能爬取：并行处理，快速高效
- ✅ 完整日志：方便监控和排查

**简单、高效、可靠！** 🚀

---

## 📝 更新日志

### v2.1.0 (2025-10-24)
- ✅ 新增全量替换模式
- ✅ 新增自动清理功能
- ✅ 优化版本说明提取
- ✅ 修复文件名提取问题

### v2.0.0 (2025-10-22)
- ✅ 支持多列表爬取
- ✅ 智能并行爬取
- ✅ MySQL 数据库集成

---

## 📧 联系

如有问题，请查看详细文档或日志文件 📚
