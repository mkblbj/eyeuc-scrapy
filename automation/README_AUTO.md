# ⏱️ 自动化抓取与导入指南

## 目标

- 每 6 小时自动抓取列表 `182` 与 `192`
- 抓取完成后自动合并并导入 MySQL
- 全程记录日志，可回溯与排查

---

## 1. 准备工作

### 1.1 环境变量

请确保 `.env` 正确配置数据库连接信息：

```
MYSQL_HOST=
MYSQL_PORT=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
MYSQL_SSL=false
```

### 1.2 Cookies

更新 `cookies.json`（位于项目根目录）：

```
/root/dev/eyeuc-scrapy/cookies.json
```

建议每月重新导出一次，避免过期。

### 1.3 虚拟环境

确保虚拟环境存在并已安装依赖：

```bash
cd /root/dev/eyeuc-scrapy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 2. 自动化脚本

主脚本：`automation/run_scheduled_crawls.sh`

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_ROOT="$PROJECT_DIR/logs/scheduled"
mkdir -p "$LOG_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_LOG="$LOG_ROOT/run_${TIMESTAMP}.log"
exec > >(tee -a "$RUN_LOG") 2>&1

source "$PROJECT_DIR/venv/bin/activate"
export COOKIES="$PROJECT_DIR/cookies.json"
export AUTO_MODE=1
export BATCH_LIMIT=25

function run_list() {
  local list_id=$1
  local pages=$2
  echo "=== Running smart_crawl for list ${list_id} (${pages} pages) ==="
  LOG_DIR="$LOG_ROOT/list${list_id}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  env LOG_DIR_OVERRIDE="$LOG_DIR" bash "$PROJECT_DIR/smart_crawl.sh" "$list_id" "$pages"
  python3 "$PROJECT_DIR/scripts/import_eyeuc_jsonl_to_mysql.py" "$(ls -t "$PROJECT_DIR"/per_list_output/eyeuc_list${list_id}_*_merged_*.jsonl | head -1)"
}

run_list 182 100
run_list 192 50

python3 "$PROJECT_DIR/scripts/verify_database.py"

deactivate
```

### 功能说明
- 自动激活虚拟环境
- 设置 `AUTO_MODE=1`（非交互模式，自动导入 DB）
- 设置 `BATCH_LIMIT=25`，保证长列表分批稳定抓取
- 将日志输出到 `logs/scheduled/`
- 每个列表抓取完成后立即导入 MySQL
- 最后运行数据库验证脚本

---

## 3. 日志管理

所有运行日志存放在：
```
/root/dev/eyeuc-scrapy/logs/scheduled/
```

单次运行示例：
```
logs/scheduled/
├── run_20251019_150000.log        # 总日志
├── list182_20251019_150000/       # smart_crawl 日志
│   ├── job0_p1-25.log
│   ├── job1_p26-50.log
│   └── ...
└── list192_20251019_150000/
    ├── job0_p1-25.log
    └── ...
```

### 3.1 日志轮转

提供默认的 logrotate 配置：
```
automation/logrotate/scheduled_logs
```
内容：
```
/root/dev/eyeuc-scrapy/logs/scheduled/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    sharedscripts
}
```

配置方法：
```bash
sudo ln -s /root/dev/eyeuc-scrapy/automation/logrotate/scheduled_logs /etc/logrotate.d/eyeuc_scheduled
```

---

## 4. Cron 定时任务

### 4.1 编辑 crontab

```bash
crontab -e
```

添加：
```
0 */6 * * * /root/dev/eyeuc-scrapy/automation/run_scheduled_crawls.sh >> /root/dev/eyeuc-scrapy/logs/scheduled/cron.log 2>&1
```

### 4.2 生效与验证

- 保存后自动生效，可用 `crontab -l` 查看
- 等待下一次触发，检查 `logs/scheduled/cron.log`
- 如需立即测试，可手动运行主脚本：
```bash
/root/dev/eyeuc-scrapy/automation/run_scheduled_crawls.sh
```

---

## 5. 故障排查

1. **脚本未运行**：查看 `cron.log` 中的错误信息
2. **抓取失败**：进入对应 `logs/scheduled/list*/job*.log` 排查
3. **数据库导入失败**：检查 `.env` 与 MySQL 连接
4. **Cookies 过期**：重新导出 `cookies.json`
5. **直链失效**：运行 `fetch_direct_links.py` 重新生成

---

## 6. 最佳实践

- ✅ 每月刷新 cookies
- ✅ 定期使用 `verify_database.py` 检查数据完整性
- ✅ 关注 `logs/scheduled/run_*.log` 及时发现异常
- ✅ 若服务器高负载，可调低 `BATCH_LIMIT` 或并行数
- ✅ 使用 `SMART_PARALLEL_STRATEGY.md` 了解并行策略

---

## 7. 手动恢复

若自动任务失败，可手动执行以下命令：

```bash
cd /root/dev/eyeuc-scrapy
source venv/bin/activate

export AUTO_MODE=1
export BATCH_LIMIT=25
bash smart_crawl.sh 182 100
bash smart_crawl.sh 192 50

python3 scripts/import_eyeuc_jsonl_to_mysql.py per_list_output/eyeuc_list182_*.jsonl
python3 scripts/import_eyeuc_jsonl_to_mysql.py per_list_output/eyeuc_list192_*.jsonl

python3 scripts/verify_database.py
```

---

## 8. 常见 FAQ

**Q: 为什么每次要导入数据库？**
A: 导入脚本使用 `INSERT ... ON DUPLICATE KEY UPDATE`，可安全更新数据，确保增量同步。

**Q: 若只想抓取不要导入？**
A: 将脚本中 `python3 scripts/import_eyeuc_jsonl_to_mysql.py` 行注释即可。

**Q: `AUTO_MODE` 有什么作用？**
A: 自动跳过交互提示，适合 cron 使用。

**Q: 如何调整并行策略？**
A: 通读 `SMART_PARALLEL_STRATEGY.md`，可调整 `parallel_jobs` 或 `BATCH_LIMIT`。

---

需要我帮你直接配置 cron 吗？或先手动测试一遍？🚀
