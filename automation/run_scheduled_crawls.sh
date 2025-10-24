#!/bin/bash
# 自动定时爬取并导入数据库

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
run_list 193 50
run_list 172 35
run_list 93 31

python3 "$PROJECT_DIR/scripts/verify_database.py"

deactivate
