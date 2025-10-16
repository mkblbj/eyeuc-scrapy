#!/usr/bin/env python3
"""
动态获取下载直链脚本（支持多分支）

用法:
  # 单个 mid（所有分支）
  python fetch_direct_links.py --mid 31047 --cookies cookies.json
  
  # 单个 mid 的特定分支
  python fetch_direct_links.py --mid 31047 --vid 46111 --cookies cookies.json
  
  # 多个 mid
  python fetch_direct_links.py --mids 31047,31439,29672 --cookies cookies.json
  
  # 从 JSON 文件读取（爬虫输出）
  python fetch_direct_links.py --json output.json --cookies cookies.json
  
  # 从 JSON 中提取特定 mid
  python fetch_direct_links.py --json output.json --mid 31047 --cookies cookies.json

输出: JSON 格式，包含实时生成的直链（按 mid 和 vid 组织）
"""

import json
import argparse
import requests
import re
from datetime import datetime
from urllib.parse import urljoin
from html import unescape


def load_cookies(cookies_file):
    """加载 cookies"""
    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies_data = json.load(f)
    
    cookies = {}
    for c in cookies_data:
        if 'eyeuc.com' in c.get('domain', ''):
            cookies[c['name']] = c['value']
    
    return cookies


def get_formhash(mid, cookies):
    """从详情页获取 formhash"""
    detail_url = f'https://bbs.eyeuc.com/down/view/{mid}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        resp = requests.get(detail_url, cookies=cookies, headers=headers, timeout=15)
        html_content = resp.text
        
        # 从 var _data 中提取 formhash
        formhash_match = re.search(r'var _data = \{.*?"formhash"\s*:\s*"([a-f0-9]+)"', html_content)
        if formhash_match:
            return formhash_match.group(1)
        
        # 备用：从 input hidden 中提取
        formhash_match = re.search(r'name="formhash"\s+value="([a-f0-9]+)"', html_content)
        if formhash_match:
            return formhash_match.group(1)
        
        return None
    except Exception as e:
        print(f"    ❌ 获取 formhash 失败: {e}")
        return None


def get_direct_link_for_file(mid, vid, fileid, formhash, cookies):
    """为单个文件获取直链（使用 buy 接口）"""
    if not formhash:
        return None, None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        
        # 构造 buy URL
        buy_url = f'https://bbs.eyeuc.com/down.php?mod=buy&mid={mid}&vid={vid}&fileid={fileid}&hash={formhash}'
        
        # 获取直链（302 重定向）
        resp = requests.get(buy_url, cookies=cookies, headers=headers, allow_redirects=False, timeout=15)
        
        if 'Location' in resp.headers:
            direct_url = resp.headers['Location']
            
            # 解析过期时间
            expires_at = None
            auth_match = re.search(r'auth_key=(\d+)-', direct_url)
            if auth_match:
                timestamp = int(auth_match.group(1))
                expires_at = datetime.fromtimestamp(timestamp).isoformat()
            
            return direct_url, expires_at
        
        return None, None
    
    except Exception as e:
        print(f"    ❌ 错误: {e}")
        return None, None


def process_version(mid, vid, version_name, downloads_meta, formhash, cookies):
    """处理单个分支，获取所有文件的直链"""
    print(f"\n  分支: {version_name} (vid={vid})")
    
    # 过滤出 internal 类型的下载
    internal_files = [dl for dl in downloads_meta if dl.get('type') == 'internal']
    
    if not internal_files:
        print(f"    ⚠️ 无内部附件")
        return {
            'vid': vid,
            'version_name': version_name,
            'downloads': [],
        }
    
    print(f"    处理 {len(internal_files)} 个附件:")
    
    # 为每个文件获取直链
    downloads = []
    for dl in internal_files:
        fileid = dl.get('fileid')
        filename = dl.get('filename', 'unknown')
        
        print(f"      {filename[:40]} ... ", end='', flush=True)
        
        direct_url, expires_at = get_direct_link_for_file(mid, vid, fileid, formhash, cookies)
        
        if direct_url:
            print(f"✅")
            downloads.append({
                'fileid': fileid,
                'filename': filename,
                'size': dl.get('size', ''),
                'direct_url': direct_url,
                'expires_at': expires_at,
            })
        else:
            print(f"❌")
            downloads.append({
                'fileid': fileid,
                'filename': filename,
                'size': dl.get('size', ''),
                'direct_url': None,
                'expires_at': None,
            })
    
    return {
        'vid': vid,
        'version_name': version_name,
        'downloads': downloads,
    }


def process_mid(mid, target_vid, item_data, cookies):
    """处理单个 mid 的所有分支（或指定分支）"""
    print(f"\n{'='*80}")
    print(f"处理 mid={mid}")
    
    versions = item_data.get('versions', [])
    if not versions:
        print("  ⚠️ 未找到分支信息")
        return {
            'mid': mid,
            'title': item_data.get('title', ''),
            'versions': [],
        }
    
    print(f"  共 {len(versions)} 个分支")
    print(f"{'='*80}")
    
    # 获取 formhash（每个 mid 只需获取一次）
    print(f"  获取 formhash ... ", end='', flush=True)
    formhash = get_formhash(mid, cookies)
    if formhash:
        print(f"✅ {formhash}")
    else:
        print(f"❌")
        return {
            'mid': mid,
            'title': item_data.get('title', ''),
            'versions': [],
        }
    
    # 如果指定了 vid，只处理该分支
    if target_vid:
        versions = [v for v in versions if v.get('vid') == target_vid]
        if not versions:
            print(f"  ❌ 未找到 vid={target_vid}")
            return {
                'mid': mid,
                'title': item_data.get('title', ''),
                'versions': [],
            }
    
    # 处理每个分支
    version_results = []
    for ver in versions:
        vid = ver.get('vid')
        version_name = ver.get('version_name', 'Unknown')
        downloads_meta = ver.get('downloads', [])
        
        result = process_version(mid, vid, version_name, downloads_meta, formhash, cookies)
        version_results.append(result)
    
    return {
        'mid': mid,
        'title': item_data.get('title', ''),
        'versions': version_results,
    }


def main():
    parser = argparse.ArgumentParser(description='动态获取 EyeUC 下载直链（支持多分支）')
    parser.add_argument('--mid', type=str, help='单个 mid')
    parser.add_argument('--vid', type=str, help='指定 vid（配合 --mid 使用）')
    parser.add_argument('--mids', type=str, help='多个 mid，逗号分隔')
    parser.add_argument('--json', type=str, help='从 JSON 文件读取（爬虫输出）')
    parser.add_argument('--cookies', type=str, required=True, help='cookies.json 文件路径')
    parser.add_argument('--output', type=str, help='输出文件路径（可选，默认输出到 stdout）')
    
    args = parser.parse_args()
    
    # 加载 cookies
    print(f"加载 cookies: {args.cookies}")
    cookies = load_cookies(args.cookies)
    print(f"✅ 已加载 {len(cookies)} 个 cookies\n")
    
    # 确定要处理的资源
    resources_to_process = {}  # {mid: {'vid': target_vid, 'item_data': {...}}}
    
    if args.json:
        # 从 JSON 文件读取（爬虫输出格式）
        with open(args.json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果指定了 --mid，只处理该 mid
        if args.mid:
            for item in data:
                if str(item.get('mid')) == args.mid:
                    resources_to_process[args.mid] = {
                        'vid': args.vid,
                        'item_data': item,
                    }
                    break
        else:
            # 处理所有 mid
            for item in data:
                mid = str(item.get('mid'))
                if mid:
                    resources_to_process[mid] = {
                        'vid': None,
                        'item_data': item,
                    }
    
    elif args.mid:
        # 单个 mid，需要先爬取数据
        print(f"⚠️  未提供 JSON 文件，将尝试在线获取 mid={args.mid} 的数据...")
        print(f"⚠️  建议使用 --json 参数传入爬虫输出的 JSON 文件\n")
        
        # 简化处理：直接使用 mid/vid
        resources_to_process[args.mid] = {
            'vid': args.vid,
            'item_data': {
                'mid': args.mid,
                'title': f'mid_{args.mid}',
                'versions': [{'vid': args.vid or 'default', 'version_name': 'Unknown', 'downloads': []}]
            }
        }
    
    elif args.mids:
        # 多个 mid
        for mid in args.mids.split(','):
            mid = mid.strip()
            resources_to_process[mid] = {
                'vid': None,
                'item_data': {
                    'mid': mid,
                    'title': f'mid_{mid}',
                    'versions': []
                }
            }
    
    if not resources_to_process:
        print("❌ 未指定任何资源")
        return
    
    print(f"待处理: {len(resources_to_process)} 个资源\n")
    
    # 处理每个 mid
    results = []
    for mid, res_info in resources_to_process.items():
        target_vid = res_info['vid']
        item_data = res_info['item_data']
        
        result = process_mid(mid, target_vid, item_data, cookies)
        results.append(result)
    
    # 输出结果
    output_json = json.dumps(results, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"\n✅ 结果已保存到: {args.output}")
    else:
        print(f"\n{'='*80}")
        print("【结果】")
        print(f"{'='*80}")
        print(output_json)


if __name__ == '__main__':
    main()

