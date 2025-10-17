#!/usr/bin/env python3
"""
合并分批抓取的 JSONL 文件

用法：
    python merge_batches.py per_list_output/eyeuc_list182_*_p*.jsonl
    或
    python merge_batches.py 182
"""

import json
import sys
import glob
from pathlib import Path
from collections import defaultdict
import re

def parse_filename(filepath):
    """从文件名中提取 list_id 和页数范围"""
    filename = Path(filepath).name
    
    # 匹配格式：eyeuc_list182_xxx_p1-5_xxx.jsonl 或 eyeuc_list182_p1-5_xxx.jsonl
    pattern = r'eyeuc_list(\d+).*?_p(\d+)-(\d+)_'
    match = re.search(pattern, filename)
    
    if match:
        list_id = int(match.group(1))
        start_page = int(match.group(2))
        end_page = int(match.group(3))
        return list_id, start_page, end_page
    
    return None, None, None

def merge_jsonl_files(files, output_file):
    """合并多个 JSONL 文件，去重（基于 mid）"""
    seen_mids = set()
    total_items = 0
    duplicate_items = 0
    
    # 按文件名中的起始页排序
    files_with_meta = []
    for f in files:
        list_id, start_page, end_page = parse_filename(f)
        if start_page:
            files_with_meta.append((f, start_page))
        else:
            files_with_meta.append((f, 0))
    
    files_with_meta.sort(key=lambda x: x[1])
    sorted_files = [f for f, _ in files_with_meta]
    
    print(f"\n📄 找到 {len(sorted_files)} 个文件:")
    for f in sorted_files:
        print(f"  - {Path(f).name}")
    
    print(f"\n🔄 合并中...")
    
    with open(output_file, 'w', encoding='utf-8') as out:
        for filepath in sorted_files:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        item = json.loads(line)
                        mid = item.get('mid')
                        
                        if mid and mid in seen_mids:
                            duplicate_items += 1
                            continue
                        
                        if mid:
                            seen_mids.add(mid)
                        
                        out.write(json.dumps(item, ensure_ascii=False) + '\n')
                        total_items += 1
                    except json.JSONDecodeError as e:
                        print(f"⚠️  解析错误: {filepath}: {e}")
    
    print(f"\n✅ 合并完成!")
    print(f"  - 总 items: {total_items}")
    print(f"  - 重复（已去除）: {duplicate_items}")
    print(f"  - 输出文件: {output_file}")
    
    return total_items

def main():
    if len(sys.argv) < 2:
        print("用法: python merge_batches.py <list_id> 或 <文件模式>")
        print("示例: python merge_batches.py 182")
        print("示例: python merge_batches.py per_list_output/eyeuc_list182_*_p*.jsonl")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    # 如果参数是数字，视为 list_id
    if arg.isdigit():
        list_id = int(arg)
        pattern = f"per_list_output/eyeuc_list{list_id}_*_p*.jsonl"
        files = glob.glob(pattern)
        
        if not files:
            print(f"❌ 未找到 list {list_id} 的批次文件 (模式: {pattern})")
            sys.exit(1)
        
        # 输出文件名
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 从第一个文件中提取 game_slug
        first_file = Path(files[0]).name
        game_match = re.search(r'eyeuc_list\d+_([a-z0-9]+)_p', first_file)
        game_slug = game_match.group(1) if game_match else 'unknown'
        
        output_file = f"per_list_output/eyeuc_list{list_id}_{game_slug}_merged_{timestamp}.jsonl"
    else:
        # 否则视为文件模式
        files = glob.glob(arg)
        
        if not files:
            print(f"❌ 未找到匹配的文件: {arg}")
            sys.exit(1)
        
        # 从文件名推断输出文件名
        list_id, _, _ = parse_filename(files[0])
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"per_list_output/eyeuc_list{list_id}_merged_{timestamp}.jsonl"
    
    merge_jsonl_files(files, output_file)

if __name__ == '__main__':
    main()

