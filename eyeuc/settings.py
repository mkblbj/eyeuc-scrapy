# Scrapy settings for eyeuc project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "eyeuc"

SPIDER_MODULES = ["eyeuc.spiders"]
NEWSPIDER_MODULE = "eyeuc.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 12  # Stage 2: 提升到 12（在 8-16 之间）

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 0.3  # Stage 2: 降低到 0.3s（配合 AutoThrottle 动态调整）
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 6  # Stage 2: 提升到 6（在 4-8 之间）
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    # 解析错误监控（保存失败样本）
    "eyeuc.middlewares.ParseErrorMonitorMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # 随机延迟（避免节律化）
    "eyeuc.middlewares.RandomDelayMiddleware": 100,
    # 增强重试（错误分类）
    "eyeuc.middlewares.EnhancedRetryMiddleware": 550,
    # 统计收集
    "eyeuc.middlewares.StatsCollectorMiddleware": 585,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   "eyeuc.pipelines.PerListJsonPipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay (Stage 2: 0.2-0.5s)
AUTOTHROTTLE_START_DELAY = 0.3
# The maximum download delay to be set in case of high latencies (Stage 2: 3-8s)
AUTOTHROTTLE_MAX_DELAY = 6
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.5  # Stage 2: 提升到 2.5
# Enable showing throttle stats for every response received:
AUTOTHROTTLE_DEBUG = False  # 生产环境设为 False，开发时可设为 True

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3  # 重试次数
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]  # 需要重试的 HTTP 状态码

# Download timeout
DOWNLOAD_TIMEOUT = 30

# Redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 3

# Log settings
LOG_LEVEL = "INFO"
# LOG_FILE = "scrapy.log"

# Per-list output settings (for阶段1.5)
PER_LIST_OUTPUT_DIR = "per_list_output"
PER_LIST_AS_JSONL = True  # True = JSONL, False = JSON array

# Stage 2: 随机延迟中间件配置
RANDOM_DELAY_MIN = 0.1  # 最小延迟（秒）
RANDOM_DELAY_MAX = 0.4  # 最大延迟（秒）

# Stage 2: 解析错误监控配置
PARSE_ERROR_OUTPUT_DIR = "parse_errors"  # 失败样本保存目录
PARSE_ERROR_SAVE_SAMPLES = True  # 是否保存失败样本

# Images pipeline settings (for阶段3，暂时注释)
# IMAGES_STORE = "images"
# MEDIA_ALLOW_REDIRECTS = True
# IMAGES_EXPIRES = 90
# ITEM_PIPELINES = {
#     "eyeuc.pipelines.PerListImagesPipeline": 200,
#     "eyeuc.pipelines.PerListJsonPipeline": 300,
# }

# Set settings whose default value is deprecated to a future-proof value
# REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"  # 禁用新指纹算法
DUPEFILTER_CLASS = 'scrapy.dupefilters.BaseDupeFilter'  # 完全禁用去重（rely on seen_in_page）
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

