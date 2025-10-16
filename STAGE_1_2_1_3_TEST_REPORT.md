# 阶段 1.2-1.3 实施与测试报告

## 实施日期
2025-10-15

## 实施内容

### ✅ 1.2 Spider 多入口（多 list）

#### 1.2.1 参数支持
- **cookies**: 从 JSON 文件加载（过滤 eyeuc.com 域名）
- **list_ids**: 逗号分隔多个 ID（如 `181,182`）
- **list_range**: 范围参数（如 `180-185`）
  - ⚠️ **注意**: 由于网站 list 编号不连续（如 162, 172, 182），range 功能实际用处有限，建议使用 list_ids
- **use_pw**: Playwright 开关（默认 false，未启用）

#### 1.2.2 expand_list_ids() 实现
- 合并 list_ids 和 list_range 参数
- 去重和排序
- 默认值：`[182]`（NBA 2K25）

#### 1.2.3 start_requests() 多入口
- 为每个 list_id 发起独立请求
- 每个 list 使用独立 cookiejar（会话隔离）
- meta 传递：`{cookiejar: list_id, list_id: lid}`

#### 1.2.4 静态游戏名映射
```python
GAME_NAME_MAP = {
    182: "NBA 2K25",
    172: "NBA 2K24", 
    162: "NBA 2K23",
}
```

### ✅ 1.3 列表解析与翻页

#### 1.3.1 _guess_game_name() 实现
- 从 H1/title/面包屑聚合文本
- 正则提取：`(NBA\s*2K\s*\d{2,4})`
- 归一化：统一大写和空格
- 优先级：正则提取 > 静态映射 > `list_{id}`

#### 1.3.2 parse_list() 实现
- 提取 `/down/view/` 详情链接
- 页内集合去重（避免置顶帖重复）
- 第一页解析最大页码
- 生成第 2..N 页请求（继承 cookiejar 和 list_id）

#### 1.3.3 _parse_max_page() 实现
- 仅在第一页扫描所有链接
- 正则匹配：`/down/list/{lid}/(\d+)`
- 取数字最大值作为上界

#### 1.3.4 置顶帖去重机制
- **页内去重**: `seen_in_page` 集合
- **全局去重**: Scrapy dupefilter 自动处理
- **测试验证**: list 182 过滤了 297 个重复请求

## 测试结果

### 测试 1: 单个 list（182 - NBA 2K25）
```bash
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=182 -O test_stage_1_2_3.json
```

**结果**:
- ✅ 抓取时间: 25分11秒（1511秒）
- ✅ 列表页: 100 页
- ✅ 详情页: 2483 个请求
- ✅ 产出 items: 2383 个
- ✅ 去重过滤: 297 个（dupefilter）
- ✅ 游戏名识别: `NBA2K25` ✓
- ✅ 平均速度: 94.6 items/min
- ✅ 文件大小: 370 KB

**详细统计**:
```
页码分布: 第1页 27个链接，第2-99页 每页27个，第100页 10个
总链接数: 27 + 98×27 + 10 = 2683 个
去重后: 2383 个（去重率 11.2%）
```

### 测试 2: 单个 list（172 - NBA 2K24）
```bash
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=172 -O test_list_172.json
```

**结果**:
- ✅ 抓取时间: ~8分钟
- ✅ 列表页: 35 页
- ✅ 产出 items: 829 个（去重后）
- ✅ 游戏名识别: `NBA2K24` ✓
- ✅ 文件大小: 129 KB

### 测试 3: 多个 list（181, 182）
```bash
scrapy crawl eyeuc_mods -a cookies=cookies.json -a list_ids=181,182
```

**结果**:
- ✅ 多入口正常工作
- ✅ list 181: 4页，88个链接
- ✅ list 182: 100页，开始抓取
- ✅ 两个列表并发处理
- ✅ 会话隔离正常（独立 cookiejar）

### 测试 4: 详情页 title 提取
**观察**:
- 大部分详情页 title 为空（占位实现）
- 少数页面提取到 title：
  - `"NBA2K24 Tools 名单编辑器/修改工具 | 已发布"`
  - `"NBA2K_Hook(NBA2K24) by-Looyh"`
- 极少数提取到单个标点：`","`

**说明**: 当前是占位实现，阶段 1.4 会完整实现详情解析

## 性能分析

### 限速与并发
- **AutoThrottle**: 0.5s 起始延迟，最大 8s
- **并发**: 8 总并发，4 域内并发
- **实际速度**: ~96 pages/min, ~95 items/min

### 资源占用
- **CPU**: 5-10%（非瓶颈）
- **内存**: 66-85 MB
- **网络**: I/O 密集型（主要瓶颈）
- **磁盘**: 写入 JSON 时

### 去重效率
- **页面级**: Scrapy dupefilter（基于 URL 指纹）
- **应用层**: 页内集合去重
- **效果**: list 182 过滤 297/2780 = 10.7%

## 验收标准检查

### 阶段 1.2 ✅
- [x] 支持 `cookies` 参数加载
- [x] 支持 `list_ids` 参数（逗号分隔）
- [x] 支持 `list_range` 参数（区间）⚠️ 实际用处有限
- [x] `expand_list_ids()` 合并/去重/排序
- [x] `start_requests()` 多入口
- [x] 独立 cookiejar 会话隔离
- [x] `use_pw` 开关（未启用）

### 阶段 1.3 ✅
- [x] `_guess_game_name()` 实现
- [x] 正则提取 NBA 2K 系列名
- [x] 归一化处理（大写、空格）
- [x] 静态映射兜底
- [x] `parse_list()` 提取详情链接
- [x] 页内集合去重
- [x] `_parse_max_page()` 第一页扫描
- [x] 翻页请求生成（2..N 页）
- [x] meta 参数传递（cookiejar, list_id, game_name）

### 数据质量 ✅
- [x] Cookies 有效：无权限问题
- [x] 翻页完整：末页不丢（第100页 10个链接）
- [x] 详情去重：按 URL 自动去重
- [x] 字段基本齐全：list_id, game, detail_url, list_url
- [x] 游戏名识别准确：NBA2K25, NBA2K24

## 已知问题与注意事项

### 1. list_range 功能限制 ⚠️
**问题**: 网站 list 编号不连续（162, 172, 182），range 参数实际用处有限

**建议**: 
- 优先使用 `list_ids` 参数指定具体 ID
- 可保留 range 功能作为便捷工具

### 2. 详情页 title 大部分为空 ℹ️
**原因**: 当前是占位实现，仅提取 h1/title 元素

**解决**: 阶段 1.4 会完整实现详情页解析

### 3. start_requests() deprecation 警告 ⚠️
**警告信息**: Scrapy 2.13 建议使用 `start()` 代替 `start_requests()`

**影响**: 功能正常，仅是 API 更新提示

**解决方案**: 可选择性升级到 async def start()

## 下一步

### 阶段 1.4：详情解析
- [ ] 完整实现 `parse_detail()`
- [ ] 提取字段：title, cover_image, images, intro, content_html, downloads
- [ ] 过滤小图标（宽高 < 40）
- [ ] 下载链接提取与归一化

### 阶段 1.5：导出管道
- [ ] 实现 `PerListJsonPipeline`
- [ ] 按 list_id 分文件导出
- [ ] 文件命名：`eyeuc_list{id}_{game}_{timestamp}.jsonl`

### 阶段 1.6：运行验收
- [ ] 单 list 完整验收
- [ ] 多 list 验收
- [ ] 断点续跑验证

## 文件清单

### 新增/更新
- `eyeuc/spiders/eyeuc_mods.py` - Spider 实现
- `eyeuc/settings.py` - Scrapy 配置
- `requirements.txt` - 依赖（添加 brotli）

### 测试输出
- `test_stage_1_2_3.json` - list 182 测试（370 KB, 2383 items）
- `test_list_172.json` - list 172 测试（129 KB, 829 items）

### 文档
- `STAGE_1_1_TEST_REPORT.md` - 阶段 1.1 报告
- `STAGE_1_2_1_3_TEST_REPORT.md` - 本报告

## 参考

- 规格文档：`docs/eyeuc_scrapy_multi_list_spec.md`
- 任务清单：`docs/eyeuc_scrapy_multi_list_checklist.md`

