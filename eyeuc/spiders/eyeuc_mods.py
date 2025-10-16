import scrapy
import json
import re
from urllib.parse import urljoin, urlparse


class EyeucModsSpider(scrapy.Spider):
    """EyeUC 多列表采集 Spider - 阶段 1.2-1.3"""
    
    name = "eyeuc_mods"
    allowed_domains = ["eyeuc.com"]
    
    # 静态游戏名映射（兜底）
    GAME_NAME_MAP = {
        182: "NBA 2K25",
        172: "NBA 2K24",
        162: "NBA 2K23",
        # 可继续扩展
    }
    
    def __init__(self, cookies=None, list_ids=None, list_range=None, use_pw=None, 
                 direct_dl=None, prefer_versions=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 参数解析
        self.cookies_file = cookies
        self.cookies_dict = {}
        self.formhash = None  # 用于 buy 接口
        self.list_ids_param = list_ids
        self.list_range_param = list_range
        self.use_pw = use_pw and use_pw.lower() in ('true', '1', 'yes')
        self.direct_dl = direct_dl and direct_dl.lower() in ('true', '1', 'yes')  # 默认 false（只抓元数据）
        self.prefer_versions = prefer_versions and prefer_versions.lower() in ('true', '1', 'yes')
        
        # 加载 cookies
        if self.cookies_file:
            self._load_cookies()
        
        # 解析 list_ids
        self.target_list_ids = self.expand_list_ids(self.list_ids_param, self.list_range_param)
        self.logger.info(f"目标列表 IDs: {self.target_list_ids}")
        self.logger.info(f"直链提取: {'启用' if self.direct_dl else '禁用'}")
        
        # 用于页内去重
        self.seen_urls_per_page = set()
    
    def _load_cookies(self):
        """从 JSON 文件加载 cookies"""
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies_list = json.load(f)
            
            # 转换为 {name: value} 字典，过滤域名
            for cookie in cookies_list:
                domain = cookie.get('domain', '')
                if 'eyeuc.com' in domain:
                    self.cookies_dict[cookie['name']] = cookie['value']
            
            self.logger.info(f"已加载 {len(self.cookies_dict)} 个 cookies")
        except Exception as e:
            self.logger.error(f"加载 cookies 失败: {e}")
    
    def expand_list_ids(self, list_ids, list_range):
        """
        合并 list_ids 和 list_range，去重排序
        - list_ids: "181,182,183"
        - list_range: "180-185"
        - 返回: [180, 181, 182, 183, 184, 185]
        """
        result = set()
        
        # 解析 list_ids
        if list_ids:
            for item in list_ids.split(','):
                item = item.strip()
                if item.isdigit():
                    result.add(int(item))
        
        # 解析 list_range
        if list_range:
            match = re.match(r'^(\d+)-(\d+)$', list_range.strip())
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                result.update(range(start, end + 1))
            else:
                self.logger.warning(f"list_range 格式错误: {list_range}")
        
        # 默认值
        if not result:
            result.add(182)
            self.logger.info("未指定 list_ids 或 list_range，使用默认值 [182]")
        
        return sorted(result)
    
    def start_requests(self):
        """为每个 list_id 发起起始请求"""
        for list_id in self.target_list_ids:
            url = f"https://bbs.eyeuc.com/down/list/{list_id}"
            
            # 每个 list_id 使用独立的 cookiejar
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                cookies=self.cookies_dict if self.cookies_dict else None,
                meta={
                    'cookiejar': list_id,  # 会话隔离
                    'list_id': list_id,
                    'page': 1,
                },
                dont_filter=True,
            )
    
    def parse_list(self, response):
        """解析列表页，提取详情链接和翻页"""
        list_id = response.meta['list_id']
        page = response.meta.get('page', 1)
        
        self.logger.info(f"正在解析列表 {list_id} 第 {page} 页: {response.url}")
        
        # 第一页：解析游戏名和最大页码
        if page == 1:
            game_name = self._guess_game_name(response, list_id)
            response.meta['game_name'] = game_name
            self.logger.info(f"列表 {list_id} 游戏名: {game_name}")
            
            # 解析最大页码
            max_page = self._parse_max_page(response, list_id)
            response.meta['max_page'] = max_page
            self.logger.info(f"列表 {list_id} 最大页码: {max_page}")
        else:
            # 后续页面继承 game_name 和 max_page
            game_name = response.meta.get('game_name', f'list_{list_id}')
            max_page = response.meta.get('max_page', 1)
        
        # 提取详情链接和封面图（页内去重）
        # 封面图在列表页，结构：.modlist ul li
        items = response.css('.modlist ul li')  # 每个资源卡片
        
        seen_in_page = set()
        for item in items:
            # 提取详情链接
            detail_link = item.css('a[href*="/down/view/"]::attr(href)').get()
            if not detail_link:
                continue
            
            full_url = urljoin(response.url, detail_link)
            if full_url in seen_in_page:
                continue
            seen_in_page.add(full_url)
            
            # 提取封面图：从 .modpic img 的 data-original 属性
            cover_image = ''
            img_url = item.css('.modpic img::attr(data-original)').get()
            if img_url and not img_url.startswith('data:image'):
                # 去掉缩略图后缀 /fw_285
                img_url = re.sub(r'/f[wh]_\d+$', '', img_url)
                cover_image = urljoin(response.url, img_url)
            
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_detail,
                cookies=self.cookies_dict if self.cookies_dict else None,
                meta={
                    'cookiejar': list_id,
                    'list_id': list_id,
                    'game_name': game_name,
                    'list_url': response.url,
                    'cover_image': cover_image,  # 传递封面图
                },
            )
        
        self.logger.info(f"列表 {list_id} 第 {page} 页找到 {len(seen_in_page)} 个详情链接")
        
        # 翻页：仅在第一页时生成后续页面请求
        if page == 1 and max_page > 1:
            for next_page in range(2, max_page + 1):
                next_url = f"https://bbs.eyeuc.com/down/list/{list_id}/{next_page}"
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_list,
                    cookies=self.cookies_dict if self.cookies_dict else None,
                    meta={
                        'cookiejar': list_id,
                        'list_id': list_id,
                        'page': next_page,
                        'game_name': game_name,
                        'max_page': max_page,
                    },
                    dont_filter=True,
                )
    
    def _guess_game_name(self, response, list_id):
        """
        从 H1/title/面包屑聚合文本，用正则归一化游戏名
        优先级：正则提取 > 静态映射 > list_{id}
        """
        # 聚合文本信号
        texts = []
        
        # H1
        h1_text = response.css('h1::text').get()
        if h1_text:
            texts.append(h1_text.strip())
        
        # Title
        title_text = response.css('title::text').get()
        if title_text:
            texts.append(title_text.strip())
        
        # 面包屑
        breadcrumb_texts = response.css('.crumb *::text, .breadcrumb *::text').getall()
        texts.extend([t.strip() for t in breadcrumb_texts if t.strip()])
        
        # 正则提取 NBA 2K 系列
        pattern = r'(NBA\s*2K\s*\d{2,4})'
        for text in texts:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 归一化：统一大写和空格
                game = match.group(1).upper()
                game = re.sub(r'\s+', ' ', game)  # 多个空格变一个
                return game
        
        # 回退到静态映射
        if list_id in self.GAME_NAME_MAP:
            return self.GAME_NAME_MAP[list_id]
        
        # 最终兜底
        return f'list_{list_id}'
    
    def _parse_max_page(self, response, list_id):
        r"""
        仅在第一页扫描 /down/list/{lid}/(\d+) 取最大页码
        """
        max_page = 1
        
        # 提取所有链接
        all_links = response.css('a::attr(href)').getall()
        
        # 正则匹配分页链接
        pattern = rf'/down/list/{list_id}/(\d+)'
        for link in all_links:
            match = re.search(pattern, link)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)
        
        return max_page
    
    def parse_detail(self, response):
        """解析详情页 - 阶段 1.4 完整实现 + 1.4.x 直链提取"""
        list_id = response.meta['list_id']
        game_name = response.meta['game_name']
        list_url = response.meta['list_url']
        cover_image = response.meta.get('cover_image', '')  # 从列表页传递过来
        
        # 1. 标题：从 H1 提取
        title = self._extract_title(response)
        
        # 2. 正文图片：去掉缩略图后缀获取大图
        images = self._extract_images(response)
        
        # 3. 简介：从资源简介区提取（Markdown 格式返回 HTML，纯文本格式返回文本）
        intro = self._extract_intro(response)
        
        # 4. 提取元数据（作者、发布者、时间、统计等）
        metadata = self._extract_metadata(response)
        
        # 5. 提取 mid/vid 和 formhash（用于直链提取）
        mid, vid, formhash = self._extract_resource_ids(response)
        
        # 6. 获取所有分支版本
        if mid:
            # 请求 toversion 获取所有分支
            version_url = f'https://bbs.eyeuc.com/down.php?mod=view&mid={mid}&show=toversion'
            
            yield scrapy.Request(
                url=version_url,
                callback=self.parse_versions,
                cookies=self.cookies_dict if self.cookies_dict else None,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                meta={
                    'cookiejar': list_id,
                    'list_id': list_id,
                    'game': game_name,
                    'title': title,
                    'cover_image': cover_image,
                    'images': images,
                    'intro': intro,
                    'metadata': metadata,  # 元数据（作者、时间、统计等）
                    'detail_url': response.url,
                    'list_url': list_url,
                    'mid': mid,
                    'default_vid': vid,  # 默认分支的 vid
                    'formhash': formhash,
                    'versions_data': [],  # 用于收集所有分支数据
                },
                dont_filter=True,
            )
        else:
            # 无法获取 mid：使用旧方法兜底
            downloads = self._extract_downloads(response)
            
            # 返回完整字段
            yield {
                'list_id': list_id,
                'game': game_name,
                'title': title,
                'cover_image': cover_image,
                'images': images,
                'intro': intro,
                'metadata': metadata,
                'downloads': downloads,
                'detail_url': response.url,
                'list_url': list_url,
            }
    
    def _extract_title(self, response):
        """提取标题：H1 优先"""
        # H1 通常格式：作者 / 标题 / 版本
        h1_text = response.css('h1#title ::text').getall()
        if h1_text:
            # 合并所有文本，去除多余空白
            title = ''.join(h1_text).strip()
            return title
        
        # 兜底：从 title 标签提取
        page_title = response.css('title::text').get(default='')
        if page_title:
            # 移除后缀 " - EYE资源中心"
            title = page_title.replace(' - EYE资源中心', '').strip()
            return title
        
        return ''
    
    def _extract_images(self, response):
        """提取正文图片：去掉缩略图后缀获取大图"""
        images = []
        seen = set()
        
        # 从多个可能的区域提取图片
        img_selectors = [
            '#imglist img::attr(data-original)',
            '#imglist img::attr(src)',
            '.view-message img::attr(src)',
            '.view-message img::attr(data-original)',
        ]
        
        for selector in img_selectors:
            img_urls = response.css(selector).getall()
            for img_url in img_urls:
                if not img_url or img_url.endswith('loading_blue.gif'):
                    continue
                
                # 过滤小图标
                if self._is_small_icon(img_url):
                    continue
                
                # 转换为绝对 URL
                abs_url = urljoin(response.url, img_url)
                
                # 去掉缩略图后缀，获取大图
                # 例如：/fh_140 → 原图
                abs_url = re.sub(r'/f[wh]_\d+$', '', abs_url)
                
                # 去重
                if abs_url not in seen:
                    seen.add(abs_url)
                    images.append(abs_url)
        
        return images
    
    def _is_small_icon(self, img_url):
        """判断是否是小图标/表情（简单检查）"""
        # 通过 URL 特征判断
        small_patterns = [
            '/smilies/',
            '/icon/',
            '/static/image/smiley/',
            'emoji',
            'loading',
        ]
        
        img_lower = img_url.lower()
        return any(pattern in img_lower for pattern in small_patterns)
    
    def _extract_intro(self, response):
        """提取简介：资源简介区（统一返回 HTML 格式，保留结构）
        
        Returns:
            str: 返回 HTML 字符串（Markdown 或普通 HTML，保留换行、链接等结构）
        """
        # 检查是否有 markdown-body（Markdown 格式）
        markdown_body = response.css('.view-message .markdown-body')
        if markdown_body:
            # Markdown 格式：返回 markdown-body 的完整 HTML
            html_content = markdown_body.get()
            if html_content:
                # 清理 script 标签
                html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                return html_content.strip()
        
        # 纯文本格式：返回整个 view-message 的 HTML（保留 <br>、<a> 等标签）
        view_message = response.css('.view-message').get()
        if view_message:
            # 清理 script 标签和多余空白
            view_message = re.sub(r'<script[^>]*>.*?</script>', '', view_message, flags=re.DOTALL | re.IGNORECASE)
            # 去掉外层 div 的多余换行和空格
            view_message = re.sub(r'>\s+', '>', view_message)
            view_message = re.sub(r'\s+<', '<', view_message)
            return view_message.strip()
        
        return ''
    
    def _extract_metadata(self, response):
        """提取资源元数据（作者、发布者、时间、统计等）"""
        metadata = {}
        
        # 1. 提取统计数据（查看、下载、喜欢）
        stats = response.css('.top-right-info span')
        for stat in stats:
            icon_text = stat.css('a::text').get()
            count = stat.css('em::text').get()
            
            if icon_text and count:
                icon_text = icon_text.strip()
                if '查看' in icon_text:
                    metadata['views'] = count
                elif '下载' in icon_text:
                    metadata['downloads'] = count
                elif '喜欢' in icon_text:
                    metadata['likes'] = count
        
        # 2. 提取详细信息（时间、作者等）
        info_items = response.css('.uploadinfo ul li')
        for item in info_items:
            label = item.css('p.custom-tt::text').get()
            if label:
                label = label.strip()
                
                if '当前版本最后更新' in label:
                    # 可能有相对时间（如"6 天前"）或绝对时间
                    time_span = item.css('span::attr(title)').get()  # 绝对时间
                    time_relative = item.css('span::text').get()      # 相对时间
                    metadata['current_version_updated'] = time_span if time_span else time_relative
                    
                elif '最后更新时间' in label:
                    time_span = item.css('span::attr(title)').get()
                    time_relative = item.css('span::text').get()
                    metadata['last_updated'] = time_span if time_span else time_relative
                    
                elif '资源创建时间' in label:
                    # 优先获取绝对时间（title 属性），否则获取相对时间
                    time_span = item.css('span::attr(title)').get()
                    time_relative = item.css('span::text').get()
                    if time_span:
                        metadata['created_at'] = time_span
                    elif time_relative:
                        metadata['created_at'] = time_relative.strip()
                        
                elif '资源作者' in label:
                    author_name = item.css('a::text').get()
                    author_link = item.css('a::attr(href)').get()
                    if author_name:
                        metadata['author'] = author_name.strip()
                    if author_link:
                        metadata['author_url'] = response.urljoin(author_link)
                        
                elif '资源发布者' in label:
                    publisher_name = item.css('a::text').get()
                    publisher_link = item.css('a::attr(href)').get()
                    if publisher_name:
                        metadata['publisher'] = publisher_name.strip()
                    if publisher_link:
                        metadata['publisher_url'] = response.urljoin(publisher_link)
        
        return metadata
    
    
    def _extract_resource_ids(self, response):
        """提取 mid/vid/formhash（用于直链提取）"""
        mid = vid = formhash = None
        
        # 从 JS 变量中提取：var _data = {"mid": "31047", "vid": "46111", "formhash": "98e0550f",...}
        script_text = response.css('script:contains("var _data")::text').get()
        if script_text:
            mid_match = re.search(r'"mid":\s*"(\d+)"', script_text)
            vid_match = re.search(r'"vid":\s*"(\d+)"', script_text)
            hash_match = re.search(r'"formhash":\s*"([a-f0-9]+)"', script_text)
            
            if mid_match:
                mid = mid_match.group(1)
            if vid_match:
                vid = vid_match.group(1)
            if hash_match:
                formhash = hash_match.group(1)
        
        return mid, vid, formhash
    
    def _extract_downloads(self, response):
        """提取下载链接：从 JS 变量和正文中提取（旧方法，兜底用）"""
        downloads = []
        seen = set()
        
        # 1. 从页面 JS 变量中提取资源 ID，构造下载页面 URL
        mid, vid, _ = self._extract_resource_ids(response)
        
        if mid and vid:
            # 构造下载页面 URL
            download_page_url = f"https://bbs.eyeuc.com/down/view/{mid}/{vid}"
            downloads.append({
                'type': 'page',
                'url': download_page_url,
                'version': '',
                'filename': '',
            })
            seen.add(download_page_url)
        
        # 2. 从正文中提取外链
        content_links = response.css('.view-message a::attr(href)').getall()
        
        # 下载链接白名单
        download_patterns = [
            'pan.baidu.com',
            'mega.nz',
            'mediafire.com',
            'onedrive',
            '1drv.ms',
            'github.com',
            'attachment.php',
            'down.php?',
            'download',
        ]
        
        for link in content_links:
            if not link:
                continue
            
            # 转换为绝对 URL
            abs_link = urljoin(response.url, link)
            
            # 检查是否匹配下载模式
            link_lower = abs_link.lower()
            if any(pattern in link_lower for pattern in download_patterns):
                if abs_link not in seen:
                    seen.add(abs_link)
                    downloads.append({
                        'type': 'external',
                        'url': abs_link,
                        'version': '',
                        'filename': '',
                    })
        
        return downloads
    
    def parse_versions(self, response):
        """解析所有分支版本列表"""
        meta = response.meta
        mid = meta['mid']
        default_vid = meta['default_vid']
        
        html_content = response.text
        
        # 提取 CDATA
        cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', html_content, re.DOTALL)
        if cdata_match:
            html_content = cdata_match.group(1)
        
        # 提取所有版本信息
        selector = scrapy.Selector(text=html_content)
        verlist_items = selector.css('div.verlist')
        
        versions = []
        for item in verlist_items:
            h4 = item.css('h4')
            if h4:
                a_tag = h4.css('a')
                if a_tag:
                    href = a_tag.css('::attr(href)').get()
                    version_text = a_tag.css('::text').get()
                    
                    if version_text and href:
                        version_name = version_text.strip()
                        is_default = '默认分支' in a_tag.get()
                        
                        # 提取 vid
                        vid_match = re.search(r'/down/view/\d+/(\d+)', href)
                        
                        # 提取分支描述（在同一个 verlist 项中的 verlist-note）
                        note_div = item.css('div.verlist-note::text').get()
                        version_intro = note_div.strip() if note_div else ''
                        
                        # 提取分支统计信息（时间、查看数、下载数）
                        version_stats = {}
                        info_items = item.css('div.verlist-info em')
                        for info_em in info_items:
                            # 检查图标类型
                            icon = info_em.css('i.iconfont::text').get()
                            if icon:
                                # &#xe67d; = 时间图标
                                # &#xe636; = 查看图标  
                                # &#xe893; = 下载图标
                                if '&#xe67d;' in icon or '\ue67d' in icon:
                                    # 时间：优先获取绝对时间（title），否则获取相对时间
                                    time_absolute = info_em.css('span::attr(title)').get()
                                    time_relative = info_em.css('span::text').get()
                                    time_text = info_em.css('::text').getall()  # 没有span的情况
                                    if time_absolute:
                                        version_stats['updated_at'] = time_absolute
                                    elif time_relative:
                                        version_stats['updated_at'] = time_relative.strip()
                                    elif time_text:
                                        # 去掉图标字符
                                        version_stats['updated_at'] = ''.join([t.strip() for t in time_text if t.strip() and '\ue67d' not in t])
                                        
                                elif '&#xe636;' in icon or '\ue636' in icon:
                                    # 查看数
                                    views = info_em.css('span::text').get()
                                    if views:
                                        version_stats['views'] = views.strip()
                                        
                                elif '&#xe893;' in icon or '\ue893' in icon:
                                    # 下载数
                                    downloads = info_em.css('span::text').get()
                                    if downloads:
                                        version_stats['downloads'] = downloads.strip()
                        
                        if vid_match:
                            vid = vid_match.group(1)
                            versions.append({
                                'vid': vid,
                                'name': version_name,
                                'is_default': is_default,
                                'intro': version_intro,  # 直接从版本列表获取描述
                                'stats': version_stats,  # 分支统计信息
                            })
        
        if not versions:
            # 没有找到分支，使用默认 vid
            self.logger.warning(f"未找到分支列表（mid={mid}），使用默认 vid={default_vid}")
            versions = [{'vid': default_vid, 'name': 'Default', 'is_default': True}]
        
        self.logger.info(f"找到 {len(versions)} 个分支（mid={mid}）")
        
        # 为每个分支发起请求获取下载文件
        meta['total_versions'] = len(versions)
        meta['current_version_index'] = 0
        
        for idx, ver in enumerate(versions):
            vid = ver['vid']
            vname = ver['name']
            version_intro = ver.get('intro', '')
            version_stats = ver.get('stats', {})
            
            # 直接请求下载文件列表（不需要再请求 message 接口）
            ajax_url = f'https://bbs.eyeuc.com/down.php?mod=view&mid={mid}&vid={vid}&show=todownload'
            
            yield scrapy.Request(
                url=ajax_url,
                callback=self.parse_download_ajax,
                cookies=self.cookies_dict if self.cookies_dict else None,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                meta={
                    **meta,
                    'version_vid': vid,
                    'version_name': vname,
                    'version_is_default': ver['is_default'],
                    'version_intro': version_intro,  # 已经从版本列表中提取
                    'version_stats': version_stats,  # 分支统计信息
                    'version_index': idx,
                },
                dont_filter=True,
            )
    
    def parse_download_ajax(self, response):
        """解析 AJAX 下载接口，提取文件列表元数据（mid/vid/fileid/filename/size）"""
        # 从 meta 恢复数据
        meta = response.meta
        list_id = meta['list_id']
        game = meta['game']
        title = meta['title']
        cover_image = meta['cover_image']
        images = meta['images']
        intro = meta.get('intro', '')
        metadata = meta.get('metadata', {})
        detail_url = meta['detail_url']
        list_url = meta['list_url']
        mid = meta['mid']
        
        # 多分支模式的字段
        vid = meta.get('version_vid')  # 当前分支的 vid
        version_name = meta.get('version_name', '')
        version_intro = meta.get('version_intro', '')
        version_stats = meta.get('version_stats', {})
        version_is_default = meta.get('version_is_default', False)
        version_index = meta.get('version_index', 0)
        total_versions = meta.get('total_versions', 1)
        
        formhash = meta.get('formhash')
        
        # 解析返回的 AJAX HTML 片段
        html_content = response.text
        
        # 提取 CDATA 内容
        cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', html_content, re.DOTALL)
        if cdata_match:
            html_content = cdata_match.group(1)
        
        # 提取完整的分支描述（从 veritem-content 中，支持 Markdown HTML 和纯文本）
        veritem_content_match = re.search(r'<div class="veritem-content">(.*?)</div>\s*</div>\s*<div class="veritem-footer">', html_content, re.DOTALL)
        if veritem_content_match:
            content_area = veritem_content_match.group(1)
            selector = scrapy.Selector(text=content_area)
            
            # 优先尝试 Markdown 格式（返回 HTML）
            markdown_body = selector.css('div.markdown-body')
            if markdown_body:
                html_intro = markdown_body.get()
                if html_intro:
                    # 清理 script 标签
                    html_intro = re.sub(r'<script[^>]*>.*?</script>', '', html_intro, flags=re.DOTALL | re.IGNORECASE)
                    version_intro = html_intro.strip()
            else:
                # 如果没有 markdown-body，提取纯文本
                plain_texts = selector.css('*::text').getall()
                if plain_texts:
                    full_intro = ' '.join([t.strip() for t in plain_texts if t.strip()])
                    if full_intro:
                        version_intro = full_intro
        
        # 提取版本名（在 veritem-name 中，格式：<span>V1.1</span> 或 <span>现役/复古</span>）
        version = ''
        version_span = re.search(r'<div class="veritem-name">.*?<span>([^<]+)</span>', html_content, re.DOTALL)
        if version_span:
            version = version_span.group(1).strip()
        
        # 检查是否为"暂无文件"
        if '暂无文件' in html_content or '当前分支版本暂无文件' in html_content:
            self.logger.warning(f"资源暂无文件（mid={mid}, vid={vid}）")
            downloads = [{
                'type': 'empty',
                'mid': mid,
                'vid': vid,
                'version': version,
                'note': '当前版本暂无文件',
            }]
        else:
            # 解析文件列表
            file_pattern = r'showprotocol\([\'"]([^\'"]+)[\'"]'
            file_matches = re.findall(file_pattern, html_content)
            
            # 提取文件名（从 <em class="bupload"> 中）
            filename_pattern = r'<em[^>]*class="bupload"[^>]*>.*?([a-zA-Z0-9_\-\.]+\.(iff|rar|zip|7z|png|jpg))</em>'
            filename_matches = re.findall(filename_pattern, html_content, re.IGNORECASE)
            
            # 如果没有找到带扩展名的文件名，尝试提取纯文本文件名
            if not filename_matches:
                text_filename_pattern = r'<em[^>]*class="bupload"[^>]*>.*?&nbsp;([^<]+)</em>'
                text_matches = re.findall(text_filename_pattern, html_content)
                if text_matches:
                    filename_matches = [(match, '') for match in text_matches]
            
            # 检查是否有需要登录的外链/重定向链接（onclick 包含 showWindow('login')）
            login_required_count = html_content.count("showWindow('login'")
            download_item_count = html_content.count('veritem-download-item')
            
            # 如果所有下载项都需要登录（没有真实的 showprotocol）
            if download_item_count > 0 and login_required_count >= download_item_count and not file_matches:
                self.logger.info(f"资源包含外链/重定向（mid={mid}, vid={vid}, items={download_item_count}）")
                # 提取外链名称（如 "MediaFire", "百度云", "虚拟爵士试用" 等）
                external_link_pattern = r'<em[^>]*class="bupload"[^>]*>.*?&nbsp;([^<]+)</em>'
                external_names = re.findall(external_link_pattern, html_content)
                
                downloads = []
                for name in external_names:
                    name_clean = name.strip()
                    # 判断是论坛链接还是外部网盘
                    if any(kw in name_clean.lower() for kw in ['试用', '链接', '地址', '下载']):
                        link_type = 'forum_redirect'
                        note = '跳转到论坛帖子（需登录查看）'
                    elif any(kw in name_clean.lower() for kw in ['baidu', '百度', 'mediafire', 'mega', 'onedrive', '网盘']):
                        link_type = 'external'
                        note = f'外部网盘（{name_clean}）'
                    else:
                        link_type = 'external'
                        note = '外部链接或网盘'
                    
                    downloads.append({
                        'type': link_type,
                        'mid': mid,
                        'vid': vid,
                        'name': name_clean,
                        'version': version,
                        'note': note,
                    })
                
                # 返回 item
                yield {
                    'mid': mid,
                    'list_id': list_id,
                    'game': game,
                    'title': title,
                    'cover_image': cover_image,
                    'images': images,
                    'intro': intro,
                    'downloads': downloads,
                    'detail_url': detail_url,
                    'list_url': list_url,
                }
                return
            
            # 提取文件大小
            size_pattern = r'<span>(\d+\.?\d*\s*(?:KB|MB|GB))</span>'
            size_matches = re.findall(size_pattern, html_content, re.IGNORECASE)
            
            downloads = []
            
            if file_matches:
                self.logger.info(f"找到 {len(file_matches)} 个下载文件（mid={mid}, vid={vid}, version={version}）")
                
                for idx, buy_url in enumerate(file_matches):
                    # 提取 fileid
                    fileid_match = re.search(r'fileid=(\d+)', buy_url)
                    
                    if fileid_match:
                        # 站内附件：有 fileid
                        fileid = fileid_match.group(1)
                        filename = filename_matches[idx][0] if idx < len(filename_matches) else f'file_{fileid}'
                        size = size_matches[idx] if idx < len(size_matches) else ''
                        
                        downloads.append({
                            'type': 'internal',
                            'mid': mid,
                            'vid': vid,
                            'fileid': fileid,
                            'filename': filename,
                            'size': size,
                            'version': version,
                        })
                    else:
                        # 外部链接：没有 fileid，提取链接名称
                        link_name = filename_matches[idx][0] if idx < len(filename_matches) else '外部链接'
                        
                        # 判断链接类型
                        link_name_lower = link_name.lower()
                        if any(kw in link_name_lower for kw in ['baidu', '百度', 'mediafire', 'mega', 'onedrive', '网盘']):
                            link_type = 'external'
                            note = f'外部网盘（{link_name}）'
                        elif any(kw in buy_url for kw in ['/t/', '/thread-']):
                            link_type = 'forum_redirect'
                            note = f'论坛帖子（{link_name}）'
                        else:
                            link_type = 'external'
                            note = f'外部链接（{link_name}）'
                        
                        downloads.append({
                            'type': link_type,
                            'name': link_name,
                            'url': urljoin('https://bbs.eyeuc.com', buy_url) if buy_url.startswith('/') else buy_url,
                            'version': version,
                            'note': note,
                        })
            else:
                # 检查是否有外链（iframe 或纯链接）
                external_link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?(?:外链|网盘|下载)</a>'
                external_matches = re.findall(external_link_pattern, html_content, re.IGNORECASE)
                
                if external_matches:
                    self.logger.info(f"找到外链资源（mid={mid}, vid={vid}）")
                    for ext_url in external_matches:
                        if not ext_url.startswith('javascript:'):
                            downloads.append({
                                'type': 'external',
                                'url': urljoin('https://bbs.eyeuc.com', ext_url),
                                'version': version,
                            })
                else:
                    # 真正的空资源或需要特殊权限
                    self.logger.warning(f"AJAX 返回无文件列表（mid={mid}, vid={vid}）")
                    downloads.append({
                        'type': 'unknown',
                        'mid': mid,
                        'vid': vid,
                        'version': version,
                        'note': '未找到下载链接',
                    })
        
        # 创建当前分支的数据
        version_data = {
            'vid': vid,
            'version_name': version_name,
            'is_default': version_is_default,
            'intro': version_intro,
            'stats': version_stats,  # 分支统计信息（时间、查看、下载）
            'downloads': downloads,
        }
        
        # 收集到 versions_data
        versions_data = meta.get('versions_data', [])
        versions_data.append(version_data)
        
        self.logger.info(f"已处理分支 {version_index + 1}/{total_versions}: {version_name} (mid={mid}, vid={vid})")
        
        # 检查是否所有分支都处理完毕
        if len(versions_data) >= total_versions:
            # 所有分支处理完毕，返回完整 item
            self.logger.info(f"所有分支处理完毕（mid={mid}），共 {len(versions_data)} 个分支")
            
            yield {
                'mid': mid,
                'list_id': list_id,
                'game': game,
                'title': title,
                'cover_image': cover_image,
                'images': images,
                'intro': intro,  # 资源主描述（Markdown HTML 或纯文本）
                'metadata': metadata,  # 元数据（作者、时间、统计等）
                'versions': versions_data,  # 所有分支数据
                'detail_url': detail_url,
                'list_url': list_url,
            }
        else:
            # 还有分支未处理，更新 meta 中的 versions_data
            meta['versions_data'] = versions_data
    
