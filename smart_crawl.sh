#!/bin/bash
# 超智能一键爬虫脚本 - 自动监控、自动合并、自动导入
# 用法: ./smart_crawl.sh <list_id> <total_pages> [parallel_jobs]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 默认参数
LIST_ID=${1}
TOTAL_PAGES=${2}
PARALLEL_JOBS=${3:-0}  # 0 表示自动检测
BATCH_SIZE=5
COOKIES=${COOKIES:-"cookies.json"}
AUTO_MODE=${AUTO_MODE:-0}
BATCH_LIMIT=${BATCH_LIMIT:-0}  # 自动模式下每个任务的最大页数，为 0 表示不限制

# 检测是否是交互式终端
IS_TTY=0
if [ -t 0 ]; then
    IS_TTY=1
fi

# 参数验证
if [ -z "$LIST_ID" ] || [ -z "$TOTAL_PAGES" ]; then
    echo -e "${RED}用法: $0 <list_id> <total_pages> [parallel_jobs]${NC}"
    echo ""
    echo "参数说明:"
    echo "  list_id       - 列表 ID (必需)"
    echo "  total_pages   - 总页数 (必需)"
    echo "  parallel_jobs - 并行任务数 (默认: 自动)"
    echo ""
    echo "示例:"
    echo "  $0 182 100        # 自动并行抓取 100 页"
    echo "  $0 182 100 4      # 4 进程并行抓取"
    echo "  $0 193 5          # 单进程抓取 5 页（自动判断）"
    exit 1
fi

# 自动检测最佳并行数
if [ $PARALLEL_JOBS -eq 0 ]; then
    if [ $TOTAL_PAGES -le 10 ]; then
        PARALLEL_JOBS=1
    elif [ $TOTAL_PAGES -le 30 ]; then
        PARALLEL_JOBS=2
    elif [ $TOTAL_PAGES -le 50 ]; then
        PARALLEL_JOBS=3
    elif [ $TOTAL_PAGES -le 75 ]; then
        PARALLEL_JOBS=4
    elif [ $TOTAL_PAGES -le 100 ]; then
        PARALLEL_JOBS=5
    elif [ $TOTAL_PAGES -le 150 ]; then
        PARALLEL_JOBS=6
    elif [ $TOTAL_PAGES -le 200 ]; then
        PARALLEL_JOBS=8
    else
        PARALLEL_JOBS=10
    fi
    echo -e "${CYAN}🤖 自动选择 ${PARALLEL_JOBS} 个并行任务${NC}"
fi

# 检查 cookies 文件
if [ ! -f "$COOKIES" ]; then
    echo -e "${RED}❌ 找不到 cookies 文件: $COOKIES${NC}"
    exit 1
fi

# 创建日志目录
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR=${LOG_DIR_OVERRIDE:-"logs/list${LIST_ID}_${TIMESTAMP}"}
mkdir -p "$LOG_DIR"

# 显示欢迎界面
if [ $AUTO_MODE -eq 0 ] && [ $IS_TTY -eq 1 ]; then
    clear
fi

echo -e "${MAGENTA}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🚀 EyeUC 超级智能爬虫 v2.0                            ║
║        Smart Crawler with Auto Everything                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${GREEN}📋 任务配置${NC}"
echo -e "  列表 ID:      ${YELLOW}${LIST_ID}${NC}"
echo -e "  总页数:       ${YELLOW}${TOTAL_PAGES}${NC}"
echo -e "  并行任务数:   ${YELLOW}${PARALLEL_JOBS}${NC}"
echo -e "  批次大小:     ${YELLOW}${BATCH_SIZE}${NC}"
if [ $AUTO_MODE -eq 1 ] && [ $BATCH_LIMIT -gt 0 ]; then
    echo -e "  自动分批上限: ${YELLOW}${BATCH_LIMIT}${NC}"
fi
echo ""

# 计算预计时间
PAGES_PER_JOB=$(( (TOTAL_PAGES + PARALLEL_JOBS - 1) / PARALLEL_JOBS ))
EST_TIME_MIN=$(( PAGES_PER_JOB * BATCH_SIZE * 2 / 60 ))  # 假设每页 2 秒
EST_TIME_MIN=$(( EST_TIME_MIN > 0 ? EST_TIME_MIN : 1 ))

echo -e "${CYAN}⏱️  预计用时: ${YELLOW}~${EST_TIME_MIN} 分钟${NC}"
if [ $AUTO_MODE -eq 1 ] && [ $BATCH_LIMIT -gt 0 ] && [ $((PARALLEL_JOBS * BATCH_LIMIT)) -lt $TOTAL_PAGES ]; then
    echo -e "  ${YELLOW}提示: 并行数不足以覆盖全部页面，自动按 ${BATCH_LIMIT} 页分批处理${NC}"
fi
echo ""
if [ $AUTO_MODE -eq 0 ] && [ $IS_TTY -eq 1 ]; then
    echo -e "${BLUE}按 Enter 开始，或 Ctrl+C 取消...${NC}"
    read
else
    echo -e "${BLUE}自动模式: 将在 3 秒后开始任务...${NC}"
    sleep 3
fi

# 启动所有任务
echo ""
echo -e "${GREEN}🚀 启动爬虫任务...${NC}"
echo ""

PIDS=()
START_TIME=$(date +%s)

for (( i=0; i<$PARALLEL_JOBS; i++ )); do
    START_PAGE=$(( i * PAGES_PER_JOB + 1 ))
    END_PAGE=$(( (i + 1) * PAGES_PER_JOB ))
    
    if [ $END_PAGE -gt $TOTAL_PAGES ]; then
        END_PAGE=$TOTAL_PAGES
    fi
    
    if [ $START_PAGE -gt $TOTAL_PAGES ]; then
        break
    fi
    
        if [ $AUTO_MODE -eq 1 ] && [ $BATCH_LIMIT -gt 0 ]; then
        echo -e "${BLUE}[任务 $((i+1))/${PARALLEL_JOBS}]${NC} 页面 ${YELLOW}${START_PAGE}-${END_PAGE}${NC} "
        echo -e "  ${YELLOW}自动分批，每批 ${BATCH_LIMIT} 页${NC}"
        
        for (( batch_start=$START_PAGE; batch_start<=$END_PAGE; batch_start+=BATCH_LIMIT )); do
            batch_end=$((batch_start + BATCH_LIMIT - 1))
            if [ $batch_end -gt $END_PAGE ]; then
                batch_end=$END_PAGE
            fi
            LOG_FILE="${LOG_DIR}/job${i}_p${batch_start}-${batch_end}.log"
            echo -e "    ${CYAN}批次: ${batch_start}-${batch_end}${NC}"
            
            ./batch_crawl.sh "$LIST_ID" "$batch_end" "$BATCH_SIZE" "$COOKIES" "$batch_start" > "$LOG_FILE" 2>&1 &
            PID=$!
            PIDS+=($PID)
            sleep 1
        done
    else
LOG_FILE="${LOG_DIR}/job${i}_p${START_PAGE}-${END_PAGE}.log"
        echo -e "${BLUE}[任务 $((i+1))/${PARALLEL_JOBS}]${NC} 页面 ${YELLOW}${START_PAGE}-${END_PAGE}${NC}"
        
        ./batch_crawl.sh "$LIST_ID" "$END_PAGE" "$BATCH_SIZE" "$COOKIES" "$START_PAGE" > "$LOG_FILE" 2>&1 &
        PID=$!
        PIDS+=($PID)
        
        sleep 1
    fi
done

# 保存 PID
PID_FILE="${LOG_DIR}/pids.txt"
printf "%s\n" "${PIDS[@]}" > "$PID_FILE"

echo ""
echo -e "${GREEN}✅ ${#PIDS[@]} 个任务已启动${NC}"
echo ""

# 监控进度
echo -e "${CYAN}📊 实时监控中...${NC}"
echo ""

# 监控函数
monitor_progress() {
    local completed=0
    local total=${#PIDS[@]}
    
    while [ $completed -lt $total ]; do
        completed=0
        for PID in "${PIDS[@]}"; do
            if ! kill -0 $PID 2>/dev/null; then
                completed=$((completed + 1))
            fi
        done
        
        # 显示进度条
        local percent=$((completed * 100 / total))
        local filled=$((completed * 40 / total))
        local empty=$((40 - filled))
        
        printf "\r${CYAN}进度: [${GREEN}"
        printf "%${filled}s" | tr ' ' '█'
        printf "${NC}%${empty}s" | tr ' ' '░'
        printf "${CYAN}] ${YELLOW}%d%%${NC} (${GREEN}%d${NC}/${total})" $percent $completed
        
        sleep 5
    done
    
    echo ""
}

# 后台监控
monitor_progress

# 等待所有任务完成
echo ""
echo -e "${BLUE}⏳ 等待任务完全结束...${NC}"
COMPLETED=0
FAILED=0

for PID in "${PIDS[@]}"; do
    if wait $PID; then
        COMPLETED=$((COMPLETED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done

END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED_TIME / 60))
ELAPSED_SEC=$((ELAPSED_TIME % 60))

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    爬取完成                                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "  成功任务: ${GREEN}${COMPLETED}${NC}"
echo -e "  失败任务: ${RED}${FAILED}${NC}"
echo -e "  用时:     ${YELLOW}${ELAPSED_MIN} 分 ${ELAPSED_SEC} 秒${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}⚠️  有任务失败，请检查日志${NC}"
    exit 1
fi

# 自动合并
echo -e "${GREEN}📦 自动合并结果...${NC}"
python3 merge_batches.py "$LIST_ID"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 合并成功${NC}"
    
    # 统计数据
    MERGED_FILE=$(ls -t per_list_output/eyeuc_list${LIST_ID}_*_merged_*.jsonl 2>/dev/null | head -1)
    if [ -n "$MERGED_FILE" ]; then
        ITEM_COUNT=$(wc -l < "$MERGED_FILE")
        echo -e "${CYAN}📊 抓取统计${NC}"
        echo -e "  总 items: ${YELLOW}${ITEM_COUNT}${NC}"
        echo -e "  文件:     ${YELLOW}${MERGED_FILE}${NC}"
        echo ""
        
        if [ $AUTO_MODE -eq 1 ]; then
            IMPORT_DB="y"
            echo -e "${BLUE}自动模式: 默认导入数据库${NC}"
        elif [ $IS_TTY -eq 1 ]; then
            echo -e "${BLUE}是否导入数据库? [y/N]${NC}"
            read -t 10 -n 1 IMPORT_DB || IMPORT_DB="n"
            echo ""
        else
            IMPORT_DB="n"
            echo -e "${YELLOW}⏭️  非交互模式且未启用自动导入，默认跳过数据库导入${NC}"
        fi

        if [[ "$IMPORT_DB" =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}💾 导入数据库...${NC}"
            python3 scripts/import_eyeuc_jsonl_to_mysql.py "$MERGED_FILE"
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ 数据库导入成功${NC}"
            else
                echo -e "${RED}❌ 数据库导入失败${NC}"
            fi
        else
            echo -e "${YELLOW}⏭️  跳过数据库导入${NC}"
            echo -e "   手动导入: ${CYAN}python3 scripts/import_eyeuc_jsonl_to_mysql.py \"${MERGED_FILE}\"${NC}"
        fi
    fi
else
    echo -e "${RED}❌ 合并失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🎉 全部完成！                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📁 日志目录: ${YELLOW}${LOG_DIR}${NC}"
echo ""

