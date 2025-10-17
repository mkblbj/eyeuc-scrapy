#!/usr/bin/env python3
"""
数据库验证脚本

用法:
  python scripts/verify_database.py
  
自动加载 .env 文件。
"""

import os
import sys
import pymysql

try:
    from dotenv import load_dotenv
    # 自动加载 .env 文件
    load_dotenv()
except ImportError:
    # 如果没有安装 python-dotenv，仍然可以通过手动 export 环境变量运行
    pass

def get_conn():
    """创建数据库连接"""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "eyeuc"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

def main():
    # 检查环境变量
    required_env = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing = [e for e in required_env if not os.getenv(e)]
    
    if missing:
        print(f"❌ 缺少环境变量: {', '.join(missing)}")
        print("\n请检查 .env 文件是否存在，或手动设置环境变量:")
        print("  export MYSQL_HOST=your_host")
        print("  export MYSQL_USER=your_user")
        print("  export MYSQL_PASSWORD=your_password")
        print("  export MYSQL_DATABASE=your_database")
        sys.exit(1)
    
    print("=" * 80)
    print("📊 数据库验证")
    print("=" * 80)
    print(f"🔌 连接: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DATABASE')}")
    print("=" * 80)
    
    conn = get_conn()
    
    with conn.cursor() as cur:
        # 统计各表数据量
        print("\n【数据统计】")
        for table in ['lists', 'mods', 'images', 'versions', 'downloads']:
            cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            count = cur.fetchone()['cnt']
            print(f"  {table:15s}: {count:6d} 条")
        
        # 按列表统计
        print("\n【按列表统计】")
        cur.execute("""
            SELECT l.list_id, l.game, COUNT(m.mid) as mod_count
            FROM lists l
            LEFT JOIN mods m ON l.list_id = m.list_id
            GROUP BY l.list_id
            ORDER BY mod_count DESC
        """)
        for row in cur.fetchall():
            print(f"  list_{row['list_id']:3d} ({row['game']:20s}): {row['mod_count']:4d} mods")
        
        # 下载类型分布
        print("\n【下载类型分布】")
        cur.execute("""
            SELECT type, COUNT(*) as cnt
            FROM downloads
            GROUP BY type
            ORDER BY cnt DESC
        """)
        for row in cur.fetchall():
            print(f"  {row['type']:20s}: {row['cnt']:5d} 条")
        
        # 多分支资源
        print("\n【多分支资源 TOP 10】")
        cur.execute("""
            SELECT m.mid, m.title, COUNT(v.id) as version_count
            FROM mods m
            LEFT JOIN versions v ON m.mid = v.mod_id
            GROUP BY m.mid
            HAVING version_count > 1
            ORDER BY version_count DESC
            LIMIT 10
        """)
        for row in cur.fetchall():
            print(f"  mid={row['mid']:5d}: {row['title'][:50]:50s} ({row['version_count']} 分支)")
        
        # 热门资源
        print("\n【热门资源 TOP 10】")
        cur.execute("""
            SELECT mid, title, author, views, downloads, likes
            FROM mods
            ORDER BY downloads DESC
            LIMIT 10
        """)
        for row in cur.fetchall():
            print(f"  {row['title'][:40]:40s} | 下载:{row['downloads']:5d} 浏览:{row['views']:6d} 赞:{row['likes']:3d}")
        
        # 数据完整性检查
        print("\n【数据完整性检查】")
        
        # 无版本的 mods
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM mods m
            LEFT JOIN versions v ON m.mid = v.mod_id
            WHERE v.id IS NULL
        """)
        no_versions = cur.fetchone()['cnt']
        print(f"  无版本的 mods: {no_versions} 条 {'✅' if no_versions == 0 else '⚠️'}")
        
        # 无下载的版本
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM versions v
            LEFT JOIN downloads d ON v.id = d.version_id
            WHERE d.id IS NULL
        """)
        no_downloads = cur.fetchone()['cnt']
        print(f"  无下载的版本: {no_downloads} 条 {'✅' if no_downloads < 10 else '⚠️'}")
        
        # 无图片的 mods
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM mods m
            LEFT JOIN images i ON m.mid = i.mod_id
            WHERE i.id IS NULL
        """)
        no_images = cur.fetchone()['cnt']
        print(f"  无图片的 mods: {no_images} 条")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 验证完成")
    print("=" * 80)

if __name__ == "__main__":
    main()

