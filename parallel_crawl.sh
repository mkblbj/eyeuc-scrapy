#!/bin/bash
# 智能并行爬虫脚本
# 用法: ./parallel_crawl.sh <list_id> <total_pages> [parallel_jobs] [batch_size] [cookies]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认参数
LIST_ID=${1}
TOTAL_PAGES=${2}
PARALLEL_JOBS=${3:-4}  # 默认 4 个并行任务
BATCH_SIZE=${4:-5}     # 默认每批 5 页
COOKIES=${5:-cookies.json}

# 参数验证
if [ -z "$LIST_ID" ] || [ -z "$TOTAL_PAGES" ]; then
    echo -e "${RED}用法: $0 <list_id> <total_pages> [parallel_jobs] [batch_size] [cookies]${NC}"
    echo ""
    echo "参数说明:"
    echo "  list_id       - 列表 ID (必需)"
    echo "  total_pages   - 总页数 (必需)"
    echo "  parallel_jobs - 并行任务数 (默认: 4)"
    echo "  batch_size    - 每批页数 (默认: 5)"
    echo "  cookies       - cookies 文件 (默认: cookies.json)"
    echo ""
    echo "示例:"
    echo "  $0 182 100              # 4 进程并行抓取 100 页"
    echo "  $0 182 100 8            # 8 进程并行抓取 100 页"
    echo "  $0 182 100 4 10         # 4 进程，每批 10 页"
    exit 1
fi

# 检查 cookies 文件
if [ ! -f "$COOKIES" ]; then
    echo -e "${RED}❌ 找不到 cookies 文件: $COOKIES${NC}"
    exit 1
fi

# 创建日志目录
LOG_DIR="logs/list${LIST_ID}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          智能并行爬虫 - EyeUC Scrapy                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📋 任务配置${NC}"
echo -e "  列表 ID:      ${YELLOW}${LIST_ID}${NC}"
echo -e "  总页数:       ${YELLOW}${TOTAL_PAGES}${NC}"
echo -e "  并行任务数:   ${YELLOW}${PARALLEL_JOBS}${NC}"
echo -e "  批次大小:     ${YELLOW}${BATCH_SIZE}${NC}"
echo -e "  Cookies 文件: ${YELLOW}${COOKIES}${NC}"
echo -e "  日志目录:     ${YELLOW}${LOG_DIR}${NC}"
echo ""

# 计算每个任务的页数范围
PAGES_PER_JOB=$(( (TOTAL_PAGES + PARALLEL_JOBS - 1) / PARALLEL_JOBS ))

echo -e "${GREEN}📊 任务分配${NC}"
echo -e "  每任务约 ${YELLOW}${PAGES_PER_JOB}${NC} 页"
echo ""

# 启动所有任务
PIDS=()
for (( i=0; i<$PARALLEL_JOBS; i++ )); do
    START_PAGE=$(( i * PAGES_PER_JOB + 1 ))
    END_PAGE=$(( (i + 1) * PAGES_PER_JOB ))
    
    # 最后一个任务处理到总页数
    if [ $END_PAGE -gt $TOTAL_PAGES ]; then
        END_PAGE=$TOTAL_PAGES
    fi
    
    # 如果起始页超过总页数，跳过
    if [ $START_PAGE -gt $TOTAL_PAGES ]; then
        break
    fi
    
    LOG_FILE="${LOG_DIR}/job${i}_p${START_PAGE}-${END_PAGE}.log"
    
    echo -e "${BLUE}[任务 $((i+1))]${NC} 页面 ${YELLOW}${START_PAGE}-${END_PAGE}${NC} → ${LOG_FILE}"
    
    # 后台运行
    ./batch_crawl.sh "$LIST_ID" "$END_PAGE" "$BATCH_SIZE" "$COOKIES" "$START_PAGE" > "$LOG_FILE" 2>&1 &
    PID=$!
    PIDS+=($PID)
    
    # 避免同时启动过多任务，间隔 2 秒
    sleep 2
done

echo ""
echo -e "${GREEN}✅ 所有任务已启动！${NC}"
echo ""
echo -e "${BLUE}🔍 监控命令${NC}"
echo -e "  查看所有日志:     ${YELLOW}tail -f ${LOG_DIR}/*.log${NC}"
echo -e "  查看单个日志:     ${YELLOW}tail -f ${LOG_DIR}/job0_*.log${NC}"
echo -e "  查看任务进程:     ${YELLOW}ps aux | grep batch_crawl${NC}"
echo ""

# 写入 PID 文件
PID_FILE="${LOG_DIR}/pids.txt"
printf "%s\n" "${PIDS[@]}" > "$PID_FILE"
echo -e "${BLUE}📝 进程 ID 已保存到: ${YELLOW}${PID_FILE}${NC}"
echo ""

# 提示如何停止
echo -e "${YELLOW}⚠️  停止所有任务: ${NC}kill \$(cat ${PID_FILE})"
echo ""

# 等待所有任务完成
echo -e "${BLUE}⏳ 等待所有任务完成...${NC}"
echo -e "   (可以 Ctrl+C 退出监控，任务会继续在后台运行)"
echo ""

COMPLETED=0
FAILED=0

for PID in "${PIDS[@]}"; do
    if wait $PID; then
        COMPLETED=$((COMPLETED + 1))
        echo -e "${GREEN}✓${NC} 任务 PID $PID 完成"
    else
        FAILED=$((FAILED + 1))
        echo -e "${RED}✗${NC} 任务 PID $PID 失败"
    fi
done

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    任务完成统计                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "  成功: ${GREEN}${COMPLETED}${NC}"
echo -e "  失败: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有任务成功完成！${NC}"
    echo ""
    echo -e "${BLUE}📦 下一步: 合并结果${NC}"
    echo -e "  ${YELLOW}python3 merge_batches.py ${LIST_ID}${NC}"
    echo ""
else
    echo -e "${RED}⚠️  有任务失败，请检查日志：${NC}"
    echo -e "  ${YELLOW}ls -lh ${LOG_DIR}/${NC}"
    echo ""
    exit 1
fi







