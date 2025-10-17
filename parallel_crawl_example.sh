#!/bin/bash
# 并行抓取 list 182 的示例脚本
# 将 100 页分成 4 个任务并行执行

LIST_ID=182
COOKIES=cookies.json

echo "🚀 开始并行抓取 list $LIST_ID (4 个进程)"
echo ""

# 任务 1: 第 1-25 页
echo "启动任务 1: 第 1-25 页..."
./batch_crawl.sh $LIST_ID 25 5 $COOKIES 1 > logs/batch_1-25.log 2>&1 &
PID1=$!

# 任务 2: 第 26-50 页
echo "启动任务 2: 第 26-50 页..."
./batch_crawl.sh $LIST_ID 50 5 $COOKIES 26 > logs/batch_26-50.log 2>&1 &
PID2=$!

# 任务 3: 第 51-75 页
echo "启动任务 3: 第 51-75 页..."
./batch_crawl.sh $LIST_ID 75 5 $COOKIES 51 > logs/batch_51-75.log 2>&1 &
PID3=$!

# 任务 4: 第 76-100 页
echo "启动任务 4: 第 76-100 页..."
./batch_crawl.sh $LIST_ID 100 5 $COOKIES 76 > logs/batch_76-100.log 2>&1 &
PID4=$!

echo ""
echo "所有任务已启动！"
echo "  - 任务 1 (PID: $PID1): 第 1-25 页"
echo "  - 任务 2 (PID: $PID2): 第 26-50 页"
echo "  - 任务 3 (PID: $PID3): 第 51-75 页"
echo "  - 任务 4 (PID: $PID4): 第 76-100 页"
echo ""
echo "日志文件:"
echo "  - logs/batch_1-25.log"
echo "  - logs/batch_26-50.log"
echo "  - logs/batch_51-75.log"
echo "  - logs/batch_76-100.log"
echo ""
echo "实时查看进度: tail -f logs/batch_1-25.log"
echo ""

# 等待所有任务完成
echo "等待所有任务完成..."
wait $PID1 $PID2 $PID3 $PID4

echo ""
echo "✅ 所有任务完成！"
echo ""
echo "现在合并结果："
python3 merge_batches.py $LIST_ID

echo ""
echo "🎉 完成！"

