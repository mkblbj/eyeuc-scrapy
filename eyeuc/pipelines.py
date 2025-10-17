"""
EyeUC Pipelines

按 list_id 分文件导出的管道
"""

import json
import os
from datetime import datetime
from pathlib import Path


class PerListJsonPipeline:
    """按 list_id 分文件导出的管道
    
    功能：
    - 为每个 list_id 创建独立的输出文件
    - 支持 JSONL 和 JSON 数组两种格式
    - 自动创建输出目录
    - 文件名包含 list_id、game 和时间戳
    
    配置项：
    - PER_LIST_OUTPUT_DIR: 输出目录（默认：per_list_output）
    - PER_LIST_AS_JSONL: 是否使用 JSONL 格式（默认：True）
    """
    
    def __init__(self, output_dir='per_list_output', as_jsonl=True):
        self.output_dir = output_dir
        self.as_jsonl = as_jsonl
        self.files = {}  # {list_id: file_handle}
        self.item_counts = {}  # {list_id: count}
        self.list_games = {}  # {list_id: game_name}
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    @classmethod
    def from_crawler(cls, crawler):
        """从 Scrapy settings 加载配置"""
        return cls(
            output_dir=crawler.settings.get('PER_LIST_OUTPUT_DIR', 'per_list_output'),
            as_jsonl=crawler.settings.get('PER_LIST_AS_JSONL', True),
        )
    
    def open_spider(self, spider):
        """Spider 启动时创建输出目录"""
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        spider.logger.info(f"PerListJsonPipeline 已启动，输出目录: {self.output_path.absolute()}")
        spider.logger.info(f"输出格式: {'JSONL' if self.as_jsonl else 'JSON 数组'}")
        
        # 获取页数范围（用于文件名）
        self.start_page = getattr(spider, 'start_page', 1)
        self.end_page = getattr(spider, 'end_page', None)
    
    def close_spider(self, spider):
        """Spider 关闭时关闭所有文件并输出统计"""
        spider.logger.info("=" * 80)
        spider.logger.info("PerListJsonPipeline 统计")
        spider.logger.info("=" * 80)
        
        for list_id, file_handle in self.files.items():
            count = self.item_counts.get(list_id, 0)
            game = self.list_games.get(list_id, 'unknown')
            
            if not self.as_jsonl:
                # JSON 数组格式：写入结尾的 ]
                file_handle.write('\n]')
            
            file_handle.close()
            
            file_path = file_handle.name
            file_size = os.path.getsize(file_path)
            
            spider.logger.info(f"  list_id={list_id} ({game}): {count} items, {file_size:,} bytes")
            spider.logger.info(f"    文件: {file_path}")
        
        spider.logger.info("=" * 80)
        spider.logger.info(f"总计: {len(self.files)} 个列表, {sum(self.item_counts.values())} items")
        spider.logger.info("=" * 80)
    
    def process_item(self, item, spider):
        """处理每个 item，写入对应的文件"""
        list_id = item.get('list_id')
        
        if not list_id:
            spider.logger.warning(f"item 缺少 list_id，跳过: {item.get('detail_url', 'unknown')}")
            return item
        
        # 首次遇到该 list_id，创建文件
        if list_id not in self.files:
            self._create_file(list_id, item.get('game', 'unknown'), spider)
        
        # 写入 item
        self._write_item(list_id, item)
        
        # 更新计数
        self.item_counts[list_id] = self.item_counts.get(list_id, 0) + 1
        
        return item
    
    def _create_file(self, list_id, game, spider):
        """为指定 list_id 创建输出文件"""
        # 清理 game 名称，用于文件名
        game_slug = self._slugify(game) if game and game != 'unknown' else ''
        
        # 构造文件名（包含页数范围）
        if game_slug:
            filename = f"eyeuc_list{list_id}_{game_slug}"
        else:
            filename = f"eyeuc_list{list_id}"
        
        # 添加页数范围（如果指定了 end_page）
        if self.end_page:
            filename += f"_p{self.start_page}-{self.end_page}"
        
        # 添加时间戳
        filename += f"_{self.timestamp}"
        
        # 添加扩展名
        if self.as_jsonl:
            filename += '.jsonl'
        else:
            filename += '.json'
        
        file_path = self.output_path / filename
        
        # 打开文件
        file_handle = open(file_path, 'w', encoding='utf-8')
        
        # JSON 数组格式：写入开头的 [
        if not self.as_jsonl:
            file_handle.write('[\n')
        
        self.files[list_id] = file_handle
        self.list_games[list_id] = game
        
        spider.logger.info(f"创建输出文件: {file_path}")
    
    def _write_item(self, list_id, item):
        """将 item 写入对应的文件"""
        file_handle = self.files[list_id]
        
        if self.as_jsonl:
            # JSONL 格式：每行一个 JSON 对象
            json.dump(item, file_handle, ensure_ascii=False)
            file_handle.write('\n')
        else:
            # JSON 数组格式：对象之间用逗号分隔
            count = self.item_counts.get(list_id, 0)
            if count > 0:
                file_handle.write(',\n')
            
            json.dump(item, file_handle, ensure_ascii=False, indent=2)
        
        file_handle.flush()  # 及时刷新，避免丢失数据
    
    def _slugify(self, text):
        """将文本转换为文件名安全的 slug"""
        # 移除空格和特殊字符
        slug = text.strip().lower()
        slug = slug.replace(' ', '_')
        slug = ''.join(c for c in slug if c.isalnum() or c in ['_', '-'])
        return slug[:50]  # 限制长度

