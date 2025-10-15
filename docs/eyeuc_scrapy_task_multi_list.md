# EyeUC 多列表（多游戏）模组采集任务 · Scrapy 方案（按 list 单独出 JSON）

> 在原有“只抓 `/down/list/182`”的基础上，扩展为：**支持多个 list（游戏）一起抓**，并**为每个 list 单独导出 1 个或一批 JSON/JSONL 文件**。例如：`181 → NBA2K25`，`182 → NBA2K24`。

---

## 1) 目标与产物

- **输入**：一个或多个 `list_id`（如 `181,182,183`），或一个范围（如 `180-185`）。  
- **抓取范围**：每个 `list_id` 下 **所有分页与详情页**。  
- **数据字段（每个模组）**
  - `list_id`：列表/游戏 ID（如 181）
  - `game`：游戏名称（从列表页标题/面包屑解析；若解析不到，则 `list_{id}`）
  - `title`：标题
  - `cover_image`：封面图链接
  - `images`：内部图片链接数组
  - `intro`：简介（纯文本）
  - `content_html`：正文 HTML（保留格式）
  - `downloads`：下载链接（数组，站内/外链）
  - `detail_url`、`list_url`：溯源
- **产物**：**每个 list 单独 1 个或多个 JSON 文件**（默认 JSONL 更稳；也支持 JSON 数组）。文件名带 `list_id / game / 时间戳`。同时可选导出**合并总文件**。

---

## 2) 技术路径（增量改造点）

在原 Scrapy 方案基础上，新增：

1. **Spider 支持多 list**  
   - 通过参数 `list_ids=181,182` 或 `list_range=180-185` 指定。  
   - `start_requests()` 为每个 `list_id` 发起起始列表页请求，并将 `list_id` 通过 `meta` 传递全流程。

2. **解析 game 名称**  
   - 在**列表页**解析页面标题/面包屑作为 `game`（如 “NBA 2K25 模组资源”→ 归一化为 `NBA 2K25`）。  
   - 解析不到则回退为 `f"list_{list_id}"`。

3. **按 list 分文件导出**  
   - 新增 **`PerListJsonPipeline`**：在 `pipelines.py` 中**按 `list_id` 打开独立文件**，逐条写入（JSONL）或写入 JSON 数组。  
   - 文件命名：`eyeuc_list{list_id}_{game?}_{timestamp}.jsonl`（或 `.json`）。  
   - 同时保留 Scrapy 自带 **FEEDS 总导出**（可选），方便一次性得到 “全量合并” 文件。

---

## 3) 代码改造

### 3.1 items.py（新增 `list_id`、`game`）
```python
# eyeuc/items.py
import scrapy

class ModItem(scrapy.Item):
    list_id = scrapy.Field()
    game = scrapy.Field()
    list_url = scrapy.Field()
    detail_url = scrapy.Field()
    title = scrapy.Field()
    cover_image = scrapy.Field()
    images = scrapy.Field()
    intro = scrapy.Field()
    content_html = scrapy.Field()
    downloads = scrapy.Field()
```

### 3.2 pipelines.py（新增按 list 分文件导出）
```python
# eyeuc/pipelines.py
import os, json, datetime
from scrapy import Item

class PerListJsonPipeline:
    def __init__(self, output_dir='per_list_output', as_jsonl=True):
        self.output_dir = output_dir
        self.as_jsonl = as_jsonl
        self.files = {}        # list_id -> file handle
        self.first_written = {}# for JSON array mode

    @classmethod
    def from_crawler(cls, crawler):
        out = crawler.settings.get('PER_LIST_OUTPUT_DIR', 'per_list_output')
        as_jsonl = crawler.settings.getbool('PER_LIST_AS_JSONL', True)
        os.makedirs(out, exist_ok=True)
        return cls(output_dir=out, as_jsonl=as_jsonl)

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        for lid, fh in self.files.items():
            if not self.as_jsonl:
                fh.write('\n]\n')
            fh.close()

    def _safe_name(self, s):
        if not s:
            return ''
        s = s.strip().replace(' ', '_').replace('/', '_').replace('\\', '_')
        return s[:40]

    def _ensure_handle(self, list_id, game_name):
        if list_id in self.files:
            return self.files[list_id]
        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        g = self._safe_name(game_name)
        base = f"eyeuc_list{list_id}{('_'+g) if g else ''}_{stamp}"
        ext = 'jsonl' if self.as_jsonl else 'json'
        path = os.path.join(self.output_dir, f"{base}.{ext}")
        fh = open(path, 'w', encoding='utf-8')
        if not self.as_jsonl:
            fh.write('[\n')
            self.first_written[list_id] = False
        self.files[list_id] = fh
        return fh

    def process_item(self, item, spider):
        data = dict(item) if isinstance(item, Item) else item
        list_id = data.get('list_id')
        game = data.get('game')
        fh = self._ensure_handle(list_id, game)
        if self.as_jsonl:
            fh.write(json.dumps(data, ensure_ascii=False) + '\n')
        else:
            if self.first_written[list_id]:
                fh.write(',\n')
            fh.write(json.dumps(data, ensure_ascii=False, indent=2))
            self.first_written[list_id] = True
        return item
```

### 3.3 settings.py（启用管道 & 参数）
```python
# eyeuc/settings.py（新增/修改）
ITEM_PIPELINES = {
    "eyeuc.pipelines.PerListJsonPipeline": 300,
}

# 输出目录与格式（默认 JSONL 更稳，不用担心数组末尾逗号）
PER_LIST_OUTPUT_DIR = "per_list_output"
PER_LIST_AS_JSONL = True

# 其余 Scrapy 基础设置沿用之前（AutoThrottle、FEEDS 总导出可选开启）
```

### 3.4 spiders/eyeuc_mods.py（支持多 list）
```python
# 仅展示与多 list 相关的关键改动：
import json, re
import scrapy
from urllib.parse import urljoin
from pathlib import Path
from ..items import ModItem

BASE = "https://bbs.eyeuc.com"

def expand_list_ids(list_ids: str, list_range: str):
    """
    将 '181,182' 与 '180-185' 合并解析为去重有序的 int 列表。
    """
    ids = set()
    if list_ids:
        for x in list_ids.split(','):
            x = x.strip()
            if x.isdigit():
                ids.add(int(x))
    if list_range and '-' in list_range:
        s, e = list_range.split('-', 1)
        if s.strip().isdigit() and e.strip().isdigit():
            for i in range(int(s), int(e) + 1):
                ids.add(i)
    return sorted(ids) if ids else [182]  # 默认 182

class EyeucModsSpider(scrapy.Spider):
    name = "eyeuc_mods"

    def __init__(self, cookies="cookies.json", list_ids="", list_range="", use_pw="false", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookies_file = cookies
        self.use_playwright = str(use_pw).lower() in ("1", "true", "yes")
        self.target_lists = expand_list_ids(list_ids, list_range)
        self.list_game_name = {}  # list_id -> game

    # ...（省略 _load_cookie_dict 与登录失效检测等）

    def start_requests(self):
        cookie_dict = self._load_cookie_dict()
        for lid in self.target_lists:
            list_url = f"{BASE}/down/list/{lid}"
            meta = {"cookiejar": lid, "list_id": lid}
            if self.use_playwright:
                meta["playwright"] = False
            yield scrapy.Request(list_url, callback=self.parse_list,
                                 cookies=cookie_dict, meta=meta, dont_filter=True)

    def _guess_game_name(self, response):
        # 尝试从 H1 / 标题 / 面包屑推断
        text = " ".join([
            response.css("h1::text").get(default=""),
            "".join(response.css("title::text").getall() or []),
            " ".join(response.css(".crumb *::text, .breadcrumb *::text").getall())
        ]).strip()
        # 简单归一化，提取 'NBA 2Kxx'
        m = re.search(r"(NBA\s*2K\s*\d{2,4})", text, re.I)
        if m:
            return m.group(1).upper().replace("  ", " ")
        return ""

    def parse_list(self, response):
        lid = response.meta["list_id"]
        # 解析并缓存 game 名称
        if lid not in self.list_game_name:
            g = self._guess_game_name(response) or f"list_{lid}"
            self.list_game_name[lid] = g

        # 抽取详情链接
        seen = set()
        for a in response.css("a[href*='/down/view/']"):
            href = a.attrib.get("href", "")
            url = response.urljoin(href)
            if url in seen:
                continue
            seen.add(url)
            title = a.attrib.get("title") or a.css("::text").get(default="").strip()
            meta = {"cookiejar": lid, "list_id": lid, "game": self.list_game_name[lid]}
            if self.use_playwright:
                meta["playwright"] = False
            yield scrapy.Request(url, callback=self.parse_detail, meta=meta,
                                 cb_kwargs={"list_url": response.url, "fallback_title": title})

        # 分页：探测最大页码并翻页
        import re as _re
        if _re.fullmatch(rf"{BASE}/down/list/{lid}/?", response.url.rstrip("/") ):
            max_page = 1
            for a in response.css("a[href]::attr(href)").getall():
                m = _re.search(rf"/down/list/{lid}/(\d+)", a)
                if m:
                    max_page = max(max_page, int(m.group(1)))
            for p in range(2, max_page + 1):
                url = f"{BASE}/down/list/{lid}/{p}"
                meta = {"cookiejar": lid, "list_id": lid}
                if self.use_playwright:
                    meta["playwright"] = False
                yield scrapy.Request(url, callback=self.parse_list, meta=meta)

    def parse_detail(self, response, list_url, fallback_title):
        lid = response.meta["list_id"]
        game = response.meta.get("game") or self.list_game_name.get(lid) or f"list_{lid}"
        # ——以下与原解析逻辑一致，略——
        # 标题、正文容器、图片、简介、content_html、downloads ...
        # 最终产出：
        yield ModItem(
            list_id=lid,
            game=game,
            list_url=list_url,
            detail_url=response.url,
            title=title,
            cover_image=cover,
            images=inner_images,
            intro=intro,
            content_html=content_html,
            downloads=downloads,
        )
```

---

## 4) 运行示例

### 单个 list（例如 182 → 2K24）
```bash
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -O all_182.json
# per_list_output/ 目录会生成 eyeuc_list182_<game>_<ts>.jsonl
```

### 多个 list（逗号分隔）
```bash
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=181,182,183 -O all_181_182_183.json
```

### 范围（区间）
```bash
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_range=180-185
```

> 建议：保留 `-O` 合并总文件用于全局检索/统计；按游戏消费用 `per_list_output/` 下各自 JSONL。

---

## 5) 其他建议

- **ID → 游戏名映射**：如想更“可控”，可在 settings 里放一个静态映射表 `{181: "NBA 2K25", 182: "NBA 2K24"}`，解析不到时再回退正则推断。  
- **异常隔离**：多 list 并行抓时，用不同 `cookiejar` 有助排障。  
- **增量与重复**：以 `detail_url` 作为指纹键；后续可做增量抓取，仅采集新增/近期更新。

---

**完成。** 这份文档说明了如何一次抓取多个游戏列表，并按 list 自动分文件输出，与你的“一个 list 一个/一批 JSON 文件”的目标一致。
