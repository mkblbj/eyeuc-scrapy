#!/bin/bash
# EyeUC 分批抓取脚本
# 用法: ./batch_crawl.sh <list_id> <end_page> [batch_size] [cookies] [start_page]

# 注意：不使用 set -e，因为 scrapy 即使成功也可能返回非零退出码

# 激活虚拟环境（如果存在）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# 参数
LIST_ID=${1:-182}
END_PAGE=${2:-100}
BATCH_SIZE=${3:-5}
COOKIES=${4:-cookies.json}
START_PAGE=${5:-1}  # 新增：起始页参数，默认为 1

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查参数
if [ -z "$LIST_ID" ] || [ -z "$END_PAGE" ]; then
    echo -e "${RED}用法: $0 <list_id> <end_page> [batch_size] [cookies] [start_page]${NC}"
    echo ""
    echo "示例:"
    echo "  $0 182 100 5 cookies.json 1      # 抓取第 1-100 页"
    echo "  $0 182 50 5 cookies.json 1       # 抓取第 1-50 页"
    echo "  $0 182 100 5 cookies.json 51     # 抓取第 51-100 页（并行）"
    exit 1
fi

# 检查 cookies 文件
if [ ! -f "$COOKIES" ]; then
    echo -e "${RED}❌ 找不到 cookies 文件: $COOKIES${NC}"
    exit 1
fi

# 计算实际抓取的页数范围和批次数
TOTAL_PAGES=$(( END_PAGE - START_PAGE + 1 ))
NUM_BATCHES=$(( (TOTAL_PAGES + BATCH_SIZE - 1) / BATCH_SIZE ))

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EyeUC 分批抓取${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  列表 ID: ${GREEN}$LIST_ID${NC}"
echo -e "  页数范围: ${GREEN}$START_PAGE - $END_PAGE${NC} (共 $TOTAL_PAGES 页)"
echo -e "  批次大小: ${GREEN}$BATCH_SIZE${NC} 页/批"
echo -e "  批次总数: ${GREEN}$NUM_BATCHES${NC}"
echo -e "  Cookies: ${GREEN}$COOKIES${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 确认（交互模式才需要，后台运行自动开始）
if [ -t 0 ]; then
    read -p "确认开始抓取？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}已取消${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✅ 后台模式，自动开始...${NC}"
    echo ""
fi

# 记录开始时间
START_TIME=$(date +%s)
FAILED_BATCHES=()

# 循环抓取每个批次
for (( batch=1; batch<=NUM_BATCHES; batch++ )); do
    start=$(( START_PAGE + (batch - 1) * BATCH_SIZE ))
    end=$(( start + BATCH_SIZE - 1 ))
    
    # 最后一批可能不足 BATCH_SIZE 或超出 END_PAGE
    if [ $end -gt $END_PAGE ]; then
        end=$END_PAGE
    fi
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}批次 $batch/$NUM_BATCHES: 第 $start-$end 页${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # 执行抓取
    if scrapy crawl eyeuc_mods \
        -a cookies=$COOKIES \
        -a list_ids=$LIST_ID \
        -a start_page=$start \
        -a end_page=$end \
        -s LOG_LEVEL=WARNING 2>&1 | tee "/tmp/batch_${LIST_ID}_${start}-${end}.log"; then
        
        echo -e "${GREEN}✅ 批次 $batch/$NUM_BATCHES 完成（第 $start-$end 页）${NC}"
    else
        echo -e "${RED}❌ 批次 $batch/$NUM_BATCHES 失败（第 $start-$end 页）${NC}"
        FAILED_BATCHES+=("$start-$end")
        
        # 后台运行时自动继续，交互模式才询问
        if [ -t 0 ]; then
            # 交互模式：询问是否继续
            read -p "继续下一批次？(Y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                echo -e "${YELLOW}已停止${NC}"
                break
            fi
        else
            # 后台模式：自动继续
            echo -e "${YELLOW}自动继续下一批次...${NC}"
        fi
    fi
    
    echo ""
    
    # 批次之间休息（避免过于频繁）
    if [ $batch -lt $NUM_BATCHES ]; then
        echo -e "${YELLOW}休息 10 秒...${NC}"
        sleep 10
    fi
done

# 计算总用时
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}抓取完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  总用时: ${GREEN}${MINUTES} 分 ${SECONDS} 秒${NC}"

if [ ${#FAILED_BATCHES[@]} -eq 0 ]; then
    echo -e "  状态: ${GREEN}✅ 所有批次成功${NC}"
else
    echo -e "  状态: ${RED}❌ ${#FAILED_BATCHES[@]} 个批次失败${NC}"
    echo -e "  失败批次: ${RED}${FAILED_BATCHES[*]}${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo ""

# 询问是否合并
if [ ${#FAILED_BATCHES[@]} -eq 0 ]; then
    REPLY="Y"
    if [ -t 0 ]; then
        read -p "现在合并结果文件？(Y/n) " -n 1 -r
        echo
    else
        echo -e "${GREEN}✅ 非交互模式，自动合并结果...${NC}"
    fi

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}正在合并...${NC}"
        if python3 merge_batches.py $LIST_ID; then
            echo -e "${GREEN}✅ 合并完成${NC}"

            MERGED_FILE=$(ls -t per_list_output/eyeuc_list${LIST_ID}_*_merged_*.jsonl 2>/dev/null | head -1)
            if [ -n "$MERGED_FILE" ]; then
                echo -e "${BLUE}正在导入数据库: ${YELLOW}${MERGED_FILE}${NC}"
                if python3 scripts/import_eyeuc_jsonl_to_mysql.py "$MERGED_FILE"; then
                    echo -e "${GREEN}✅ 数据库导入完成${NC}"
                else
                    echo -e "${RED}❌ 数据库导入失败${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️  未找到合并后的文件，跳过数据库导入${NC}"
            fi
        else
            echo -e "${RED}❌ 合并失败，已跳过数据库导入${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  有批次失败，建议先重跑失败的批次再合并${NC}"
    echo ""
    echo "重跑命令："
    for batch in "${FAILED_BATCHES[@]}"; do
        IFS='-' read -ra PAGES <<< "$batch"
        start=${PAGES[0]}
        end=${PAGES[1]}
        echo "  scrapy crawl eyeuc_mods -a cookies=$COOKIES -a list_ids=$LIST_ID -a start_page=$start -a end_page=$end"
    done
fi

echo ""
echo -e "${GREEN}🎉 完成！${NC}"

