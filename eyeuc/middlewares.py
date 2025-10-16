# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from scrapy.exceptions import IgnoreRequest
import random
import time
import logging

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class EyeucSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn't have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class EyeucDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class RandomDelayMiddleware:
    """随机延迟中间件，避免请求节律化"""
    
    def __init__(self, delay_range):
        self.delay_range = delay_range
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        # 从配置读取延迟范围，默认 0.1-0.5 秒
        delay_min = crawler.settings.getfloat('RANDOM_DELAY_MIN', 0.1)
        delay_max = crawler.settings.getfloat('RANDOM_DELAY_MAX', 0.5)
        return cls((delay_min, delay_max))
    
    def process_request(self, request, spider):
        # 随机延迟
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
        return None


class EnhancedRetryMiddleware(RetryMiddleware):
    """增强的重试中间件，带错误分类和统计"""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stats_by_reason = {}
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def process_response(self, request, response, spider):
        # 检测权限/登录问题
        if response.status in [401, 403]:
            spider.logger.warning(
                f"权限错误 [{response.status}]: {request.url}"
            )
            self._update_stats('permission_error')
        
        # 检测登录跳转
        if '登录' in response.text or 'login' in response.url.lower():
            spider.logger.warning(
                f"可能需要登录: {request.url}"
            )
            self._update_stats('login_required')
        
        return super().process_response(request, response, spider)
    
    def process_exception(self, request, exception, spider):
        # 错误分类
        exception_name = exception.__class__.__name__
        
        # 网络错误
        if 'Timeout' in exception_name or 'TimeoutError' in exception_name:
            spider.logger.warning(
                f"超时错误: {request.url} ({exception_name})"
            )
            self._update_stats('timeout_error')
        
        # DNS/连接错误
        elif 'DNS' in exception_name or 'Connection' in exception_name:
            spider.logger.warning(
                f"网络错误: {request.url} ({exception_name})"
            )
            self._update_stats('network_error')
        
        # 其他错误
        else:
            spider.logger.warning(
                f"未分类错误: {request.url} ({exception_name})"
            )
            self._update_stats('unknown_error')
        
        return super().process_exception(request, exception, spider)
    
    def _update_stats(self, reason):
        """更新错误统计"""
        self.stats_by_reason[reason] = self.stats_by_reason.get(reason, 0) + 1


class ParseErrorMonitorMiddleware:
    """解析错误监控中间件，保存失败样本"""
    
    def __init__(self, output_dir, save_samples):
        self.output_dir = output_dir
        self.save_samples = save_samples
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if self.save_samples:
            import os
            os.makedirs(self.output_dir, exist_ok=True)
    
    @classmethod
    def from_crawler(cls, crawler):
        output_dir = crawler.settings.get('PARSE_ERROR_OUTPUT_DIR', 'parse_errors')
        save_samples = crawler.settings.getbool('PARSE_ERROR_SAVE_SAMPLES', True)
        return cls(output_dir, save_samples)
    
    def process_spider_exception(self, response, exception, spider):
        """捕获解析异常"""
        self.logger.error(
            f"解析错误: {response.url}\n"
            f"异常: {exception.__class__.__name__}: {str(exception)}"
        )
        
        # 保存失败样本
        if self.save_samples:
            self._save_error_sample(response, exception, spider)
        
        return None
    
    def _save_error_sample(self, response, exception, spider):
        """保存失败的 HTML 样本"""
        import os
        from datetime import datetime
        
        # 文件名：timestamp_mid_exception.html
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mid = response.url.split('/')[-1] if '/' in response.url else 'unknown'
        exception_name = exception.__class__.__name__
        filename = f"{timestamp}_{mid}_{exception_name}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- URL: {response.url} -->\n")
                f.write(f"<!-- Exception: {exception_name}: {str(exception)} -->\n")
                f.write(f"<!-- Timestamp: {timestamp} -->\n\n")
                f.write(response.text)
            
            self.logger.info(f"失败样本已保存: {filepath}")
        except Exception as e:
            self.logger.error(f"保存失败样本时出错: {e}")


class StatsCollectorMiddleware:
    """统计收集中间件"""
    
    def __init__(self, stats):
        self.stats = stats
        self.logger = logging.getLogger(self.__class__.__name__)
        self.response_times = []
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.stats)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def process_request(self, request, spider):
        request.meta['start_time'] = time.time()
        return None
    
    def process_response(self, request, response, spider):
        # 计算响应时间
        if 'start_time' in request.meta:
            response_time = time.time() - request.meta['start_time']
            self.response_times.append(response_time)
            
            # 记录慢响应
            if response_time > 5.0:
                spider.logger.warning(
                    f"慢响应 ({response_time:.2f}s): {request.url}"
                )
        
        return response
    
    def spider_closed(self, spider):
        """Spider 关闭时输出统计"""
        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)
            max_time = max(self.response_times)
            min_time = min(self.response_times)
            
            self.logger.info("=" * 80)
            self.logger.info("响应时间统计")
            self.logger.info("=" * 80)
            self.logger.info(f"  平均响应时间: {avg_time:.3f}s")
            self.logger.info(f"  最快响应: {min_time:.3f}s")
            self.logger.info(f"  最慢响应: {max_time:.3f}s")
            self.logger.info(f"  总请求数: {len(self.response_times)}")
            self.logger.info("=" * 80)

