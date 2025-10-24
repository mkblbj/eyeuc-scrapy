#!/usr/bin/env python3
"""
EyeUC JSONL → MySQL 导入脚本

功能：
- 支持 JSONL 和 JSON 数组格式
- 支持目录 glob 批量导入
- 幂等导入（ON DUPLICATE KEY UPDATE）
- 批量提交（每 200 条）
- 导入成功后自动清理源文件（可选）
- 全量替换模式：删除所有旧数据后导入（可选）

用法：
  # 增量导入（默认）- 更新已有数据，添加新数据
  python scripts/import_eyeuc_jsonl_to_mysql.py per_list_output/eyeuc_list193_merged_*.jsonl
  
  # 全量替换 - 删除所有旧数据，导入新数据（推荐用于定时任务）
  FULL_REPLACE=true python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
  
  # 全量替换 + 禁用清理（用于调试）
  FULL_REPLACE=true CLEANUP=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

环境变量：
  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE - 数据库连接
  CLEANUP=true/false - 导入成功后自动清理源文件（默认 true）
  FULL_REPLACE=true/false - 全量替换模式（默认 false）
"""

import os
import sys
import glob
import json
import time
from datetime import datetime
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("❌ 缺少依赖：pip install pymysql python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    # 自动加载 .env 文件
    load_dotenv()
except ImportError:
    # 如果没有安装 python-dotenv，仍然可以通过手动 export 环境变量运行
    pass


def get_conn():
    """创建数据库连接"""
    ssl_disabled = os.getenv("MYSQL_SSL", "false").lower() in ("false", "0", "no")
    
    conn_params = {
        'host': os.getenv("MYSQL_HOST", "localhost"),
        'port': int(os.getenv("MYSQL_PORT", "3306")),
        'user': os.getenv("MYSQL_USER", "root"),
        'password': os.getenv("MYSQL_PASSWORD", ""),
        'database': os.getenv("MYSQL_DATABASE", "eyeuc"),
        'charset': "utf8mb4",
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
    }
    
    # SSL 配置
    if not ssl_disabled:
        conn_params['ssl'] = {'ssl': {}}
    
    return pymysql.connect(**conn_params)


def ensure_schema(conn):
    """确保表结构存在"""
    schema_file = Path(__file__).parent.parent / "schema.sql"
    
    if not schema_file.exists():
        print(f"⚠️  未找到 schema.sql: {schema_file}")
        return
    
    print(f"📋 执行表结构: {schema_file}")
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割并执行每条 SQL
    statements = []
    current = []
    
    for line in sql_content.split('\n'):
        line = line.strip()
        
        # 跳过注释
        if line.startswith('--') or not line:
            continue
        
        current.append(line)
        
        # 遇到分号，执行一条 SQL
        if line.endswith(';'):
            statements.append(' '.join(current))
            current = []
    
    with conn.cursor() as cur:
        for stmt in statements:
            if stmt.strip():
                try:
                    cur.execute(stmt)
                except Exception as e:
                    print(f"⚠️  SQL 执行警告: {e}")
    
    conn.commit()
    print("✅ 表结构就绪\n")


def parse_int(v):
    """安全解析整数"""
    if v is None:
        return None
    try:
        # 移除逗号和空格
        return int(str(v).replace(",", "").strip())
    except:
        return None


def parse_dt(v):
    """安全解析日期时间"""
    if not v:
        return None
    
    # 尝试多种格式
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S.%f",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(v.strip(), fmt)
        except:
            pass
    
    return None


def upsert_list(conn, list_id, game):
    """插入或更新列表"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO lists (list_id, game, slug)
            VALUES (%s, %s, NULL)
            ON DUPLICATE KEY UPDATE 
                game=VALUES(game),
                updated_at=CURRENT_TIMESTAMP
        """, (list_id, game))


def upsert_mod(conn, item):
    """插入或更新资源主表"""
    md = item.get("metadata", {})
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO mods
            (mid, list_id, category, title, intro_html, cover_image, 
             author, author_url, publisher, publisher_url,
             views, downloads, likes, 
             created_at, last_updated, 
             detail_url, list_url, raw_json)
            VALUES
            (%s, %s, %s, %s, %s, %s, 
             %s, %s, %s, %s, 
             %s, %s, %s, 
             %s, %s, 
             %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                category=VALUES(category),
                title=VALUES(title), 
                intro_html=VALUES(intro_html), 
                cover_image=VALUES(cover_image),
                author=VALUES(author), 
                author_url=VALUES(author_url),
                publisher=VALUES(publisher), 
                publisher_url=VALUES(publisher_url),
                views=VALUES(views), 
                downloads=VALUES(downloads), 
                likes=VALUES(likes),
                created_at=VALUES(created_at), 
                last_updated=VALUES(last_updated),
                detail_url=VALUES(detail_url), 
                list_url=VALUES(list_url),
                raw_json=VALUES(raw_json)
        """, (
            parse_int(item["mid"]), 
            parse_int(item["list_id"]), 
            item.get("category"),  # 分类
            item.get("title"),
            item.get("intro"), 
            item.get("cover_image"),
            md.get("author"), 
            md.get("author_url"),
            md.get("publisher"), 
            md.get("publisher_url"),
            parse_int(md.get("views")), 
            parse_int(md.get("downloads")), 
            parse_int(md.get("likes")),
            parse_dt(md.get("created_at")), 
            parse_dt(md.get("last_updated") or md.get("current_version_updated")),
            item.get("detail_url"), 
            item.get("list_url"),
            json.dumps(item, ensure_ascii=False).encode('utf-8'),
        ))


def upsert_images(conn, mod_id, images):
    """插入或更新图片"""
    if not images:
        return
    
    with conn.cursor() as cur:
        for idx, url in enumerate(images):
            if not url:
                continue
            
            cur.execute("""
                INSERT INTO images (mod_id, url, idx)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE idx=VALUES(idx)
            """, (mod_id, url, idx))


def upsert_versions_and_downloads(conn, mod_id, versions):
    """插入或更新版本和下载"""
    if not versions:
        return
    
    with conn.cursor() as cur:
        for ver in versions:
            vid = parse_int(ver.get("vid"))
            
            # 插入版本
            cur.execute("""
                INSERT INTO versions
                (mod_id, vid, version_name, is_default, intro, 
                 updated_at, views, downloads)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    version_name=VALUES(version_name),
                    is_default=VALUES(is_default),
                    intro=VALUES(intro),
                    updated_at=VALUES(updated_at),
                    views=VALUES(views),
                    downloads=VALUES(downloads)
            """, (
                mod_id, 
                vid, 
                ver.get("version_name"),
                1 if ver.get("is_default") else 0,
                ver.get("intro"),
                parse_dt((ver.get("stats") or {}).get("updated_at")),
                parse_int((ver.get("stats") or {}).get("views")),
                parse_int((ver.get("stats") or {}).get("downloads")),
            ))
            
            # 获取 version_id
            cur.execute("""
                SELECT id FROM versions 
                WHERE mod_id=%s AND (vid <=> %s OR (vid IS NULL AND %s IS NULL))
                ORDER BY id DESC LIMIT 1
            """, (mod_id, vid, vid))
            
            ver_row = cur.fetchone()
            version_id = ver_row["id"] if ver_row else None
            
            # 插入下载
            for dl in ver.get("downloads", []):
                # 判断类型：有 fileid 的是 internal，否则是 external
                dl_type = dl.get("type")
                if not dl_type:
                    dl_type = "internal" if dl.get("fileid") else "external"
                
                # 处理外链的 name 字段
                note = dl.get("note") or dl.get("name")
                
                cur.execute("""
                    INSERT INTO downloads
                    (mod_id, version_id, type, 
                     fileid, filename, size, 
                     url, note, version_label)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        filename=VALUES(filename), 
                        size=VALUES(size), 
                        note=VALUES(note), 
                        version_label=VALUES(version_label)
                """, (
                    mod_id, 
                    version_id, 
                    dl_type,
                    parse_int(dl.get("fileid")), 
                    dl.get("filename"), 
                    dl.get("size"),
                    dl.get("url"), 
                    note, 
                    dl.get("version"),
                ))


def iter_items_from_file(path):
    """从文件中迭代 items（支持 JSONL 和 JSON 数组）"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            return
        
        # 判断格式
        if content.startswith('['):
            # JSON 数组
            data = json.loads(content)
            for item in data:
                yield item
        else:
            # JSONL
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    yield json.loads(line)
    
    except Exception as e:
        print(f"  ❌ 读取文件失败: {e}")


def cleanup_imported_files(files):
    """清理已成功导入的文件
    
    Args:
        files: 文件路径列表
    """
    if not files:
        return
    
    print("🧹 清理已导入的文件...")
    
    # 获取所有涉及的目录（用于后续检查是否清空）
    dirs_to_check = set()
    for file_path in files:
        try:
            file_obj = Path(file_path)
            if file_obj.exists():
                os.remove(file_path)
                print(f"  ✅ 删除: {file_obj.name}")
                dirs_to_check.add(file_obj.parent)
        except Exception as e:
            print(f"  ⚠️  删除失败 {Path(file_path).name}: {e}")
    
    # 检查目录是否为空，如果为空则删除
    for dir_path in dirs_to_check:
        try:
            if dir_path.exists() and dir_path.is_dir():
                remaining = list(dir_path.glob('*'))
                if not remaining:
                    print(f"  📁 目录已空，删除: {dir_path.name}")
                    dir_path.rmdir()
                else:
                    print(f"  📁 目录保留（还有 {len(remaining)} 个文件）: {dir_path.name}")
        except Exception as e:
            print(f"  ⚠️  检查目录失败 {dir_path}: {e}")
    
    print("✨ 清理完成\n")


def import_files(glob_pattern, batch_size=200, auto_cleanup=True, full_replace=False):
    """导入文件
    
    Args:
        glob_pattern: 文件匹配模式
        batch_size: 批量提交大小
        auto_cleanup: 导入成功后自动清理源文件（默认 True）
        full_replace: 导入前先删除所有旧数据（默认 False）
    """
    # 展开 glob
    files = sorted(glob.glob(glob_pattern))
    
    if not files:
        print(f"❌ 未找到匹配的文件: {glob_pattern}")
        return False
    
    print(f"📁 找到 {len(files)} 个文件:")
    for f in files:
        print(f"  - {Path(f).name}")
    print()
    
    # 连接数据库
    print("🔌 连接数据库...")
    conn = get_conn()
    print(f"✅ 已连接: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}\n")
    
    # 确保表结构
    ensure_schema(conn)
    
    # 全量替换：删除所有旧数据
    if full_replace:
        print("🗑️  全量替换模式：删除所有旧数据...")
        try:
            with conn.cursor() as cur:
                # 禁用外键检查，加快删除速度
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                
                # 清空所有表（按顺序）
                tables = ['downloads', 'versions', 'images', 'mods', 'lists']
                for table in tables:
                    cur.execute(f"TRUNCATE TABLE {table}")
                    print(f"  ✅ 清空表: {table}")
                
                # 恢复外键检查
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
            
            conn.commit()
            print("✅ 所有旧数据已删除\n")
        except Exception as e:
            print(f"❌ 删除旧数据失败: {e}")
            conn.rollback()
            raise
    
    # 导入数据
    total_items = 0
    batch_count = 0
    start_time = time.time()
    import_success = False
    
    try:
        for file_path in files:
            print(f"📄 处理: {Path(file_path).name}")
            
            file_items = 0
            for item in iter_items_from_file(file_path):
                try:
                    list_id = parse_int(item.get("list_id"))
                    game = item.get("game") or f"list_{list_id}"
                    mid = parse_int(item.get("mid"))
                    
                    if not list_id or not mid:
                        print(f"  ⚠️  跳过无效 item: list_id={list_id}, mid={mid}")
                        continue
                    
                    # 插入数据
                    upsert_list(conn, list_id, game)
                    upsert_mod(conn, item)
                    upsert_images(conn, mid, item.get("images"))
                    upsert_versions_and_downloads(conn, mid, item.get("versions"))
                    
                    total_items += 1
                    file_items += 1
                    batch_count += 1
                    
                    # 批量提交
                    if batch_count >= batch_size:
                        conn.commit()
                        print(f"  💾 已提交 {total_items} items")
                        batch_count = 0
                
                except Exception as e:
                    print(f"  ❌ 处理 item 失败: {e}")
                    conn.rollback()
            
            print(f"  ✅ 完成: {file_items} items\n")
        
        # 最后提交
        conn.commit()
        import_success = True
        
        elapsed = time.time() - start_time
        print(f"{'='*80}")
        print(f"🎉 导入完成!")
        print(f"{'='*80}")
        print(f"  总 items: {total_items}")
        print(f"  总文件: {len(files)}")
        print(f"  用时: {elapsed:.2f}s")
        print(f"  速度: {total_items/elapsed:.1f} items/s")
        print(f"{'='*80}\n")
        
        # 自动清理源文件
        if import_success and auto_cleanup:
            cleanup_imported_files(files)
        
        return True
    
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n❌ 缺少参数")
        print("\n用法: python scripts/import_eyeuc_jsonl_to_mysql.py <glob_pattern>")
        print('\n示例: python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/eyeuc_list193_*.jsonl"')
        sys.exit(1)
    
    glob_pattern = sys.argv[1]
    
    # 检查环境变量
    required_env = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing = [e for e in required_env if not os.getenv(e)]
    
    if missing:
        print(f"❌ 缺少环境变量: {', '.join(missing)}")
        print("\n请设置环境变量或创建 .env 文件:")
        print("  export MYSQL_HOST=your_host")
        print("  export MYSQL_PORT=3306")
        print("  export MYSQL_USER=your_user")
        print("  export MYSQL_PASSWORD=your_password")
        print("  export MYSQL_DATABASE=your_database")
        print("  export MYSQL_SSL=false")
        print("  export CLEANUP=true  # 自动清理源文件（默认）")
        print("\n或使用: source .env")
        sys.exit(1)
    
    # 读取 CLEANUP 环境变量（默认 true）
    auto_cleanup = os.getenv('CLEANUP', 'true').lower() not in ('false', '0', 'no')
    
    # 读取 FULL_REPLACE 环境变量（默认 false）
    full_replace = os.getenv('FULL_REPLACE', 'false').lower() in ('true', '1', 'yes')
    
    # 显示模式提示
    if full_replace:
        print("⚠️  " + "=" * 76)
        print("⚠️  全量替换模式：将删除所有旧数据，然后导入新数据")
        print("⚠️  " + "=" * 76)
        print()
    
    import_files(glob_pattern, auto_cleanup=auto_cleanup, full_replace=full_replace)


if __name__ == "__main__":
    main()

