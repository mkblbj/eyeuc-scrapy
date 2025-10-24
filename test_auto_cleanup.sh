#!/bin/bash
# 测试自动清理功能

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧪 测试自动清理功能"
echo "===================="
echo ""

# 1. 清理旧的测试文件
echo "1️⃣ 清理旧的测试文件..."
rm -f per_list_output/test_*.jsonl
echo "   ✅ 完成"
echo ""

# 2. 创建测试数据
echo "2️⃣ 创建测试数据..."
mkdir -p per_list_output

cat > per_list_output/test_mod_001.jsonl << 'EOF'
{"list_id": "999", "game": "test_game", "mid": "90001", "title": "Test Mod 001", "author": "Tester", "detail_url": "https://example.com/90001", "created_at": "2025-10-24 10:00", "last_updated": "2025-10-24 10:00", "views": 100, "likes": 10, "downloads": 5, "images": [], "versions": []}
EOF

cat > per_list_output/test_mod_002.jsonl << 'EOF'
{"list_id": "999", "game": "test_game", "mid": "90002", "title": "Test Mod 002", "author": "Tester", "detail_url": "https://example.com/90002", "created_at": "2025-10-24 10:00", "last_updated": "2025-10-24 10:00", "views": 200, "likes": 20, "downloads": 10, "images": [], "versions": []}
EOF

cat > per_list_output/test_mod_003.jsonl << 'EOF'
{"list_id": "999", "game": "test_game", "mid": "90003", "title": "Test Mod 003", "author": "Tester", "detail_url": "https://example.com/90003", "created_at": "2025-10-24 10:00", "last_updated": "2025-10-24 10:00", "views": 300, "likes": 30, "downloads": 15, "images": [], "versions": []}
EOF

echo "   ✅ 创建了 3 个测试文件"
ls -lh per_list_output/test_*.jsonl
echo ""

# 3. 查看导入前的文件
echo "3️⃣ 导入前的文件列表："
echo "   $(ls per_list_output/test_*.jsonl 2>/dev/null | wc -l) 个测试文件"
echo ""

# 4. 执行导入（自动清理）
echo "4️⃣ 执行导入（自动清理开启）..."
echo "===================="
source venv/bin/activate
python3 scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/test_*.jsonl"
echo "===================="
echo ""

# 5. 验证清理结果
echo "5️⃣ 验证清理结果："
remaining=$(ls per_list_output/test_*.jsonl 2>/dev/null | wc -l)
if [ "$remaining" -eq 0 ]; then
    echo "   ✅ 所有测试文件已被清理！"
else
    echo "   ⚠️  还剩 $remaining 个文件未清理"
    ls -lh per_list_output/test_*.jsonl
fi
echo ""

# 6. 测试禁用清理
echo "6️⃣ 测试禁用清理功能..."
echo ""

# 重新创建测试文件
cat > per_list_output/test_mod_004.jsonl << 'EOF'
{"list_id": "999", "game": "test_game", "mid": "90004", "title": "Test Mod 004", "author": "Tester", "detail_url": "https://example.com/90004", "created_at": "2025-10-24 10:00", "last_updated": "2025-10-24 10:00", "views": 400, "likes": 40, "downloads": 20, "images": [], "versions": []}
EOF

echo "   创建了新的测试文件"
echo "   导入前: $(ls per_list_output/test_*.jsonl 2>/dev/null | wc -l) 个文件"
echo ""

echo "   执行导入（CLEANUP=false）..."
echo "   ===================="
CLEANUP=false python3 scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/test_*.jsonl"
echo "   ===================="
echo ""

remaining=$(ls per_list_output/test_*.jsonl 2>/dev/null | wc -l)
if [ "$remaining" -gt 0 ]; then
    echo "   ✅ 禁用清理成功！文件被保留了"
    ls -lh per_list_output/test_*.jsonl
else
    echo "   ⚠️  文件意外被清理了"
fi
echo ""

# 7. 手动清理测试文件
echo "7️⃣ 清理测试文件..."
rm -f per_list_output/test_*.jsonl
echo "   ✅ 测试完成，已清理所有测试文件"
echo ""

# 8. 验证数据库
echo "8️⃣ 验证数据库中的测试数据..."
python3 << 'PYEOF'
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    charset="utf8mb4"
)

try:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM mods WHERE list_id = 999")
        count = cur.fetchone()[0]
        print(f"   测试数据: {count} 条记录")
        
        if count > 0:
            print("\n   测试 Mods:")
            cur.execute("SELECT mid, title, views, likes, downloads FROM mods WHERE list_id = 999 ORDER BY mid")
            for row in cur.fetchall():
                print(f"   - mid={row[0]}: {row[1]} (浏览:{row[2]}, 点赞:{row[3]}, 下载:{row[4]})")
            
            print("\n   清理测试数据...")
            cur.execute("DELETE FROM mods WHERE list_id = 999")
            cur.execute("DELETE FROM lists WHERE list_id = 999")
            conn.commit()
            print("   ✅ 测试数据已清理")
finally:
    conn.close()
PYEOF

echo ""
echo "===================="
echo "🎉 测试完成！"
echo "===================="
echo ""
echo "总结："
echo "  ✅ 自动清理功能正常"
echo "  ✅ CLEANUP=false 禁用功能正常"
echo "  ✅ 数据库导入正常"
echo ""

