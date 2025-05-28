import asyncio
import json
import re
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime
import random
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JDCommentScraper:
    def __init__(self, headless=False, user_data_dir="jd_user_data", timeout=90000, test_mode=False):
        # 基本配置
        self.headless = headless
        self.user_data_dir = Path(user_data_dir).absolute()
        self.user_data_dir.mkdir(exist_ok=True)

        # 浏览器相关
        self.browser = None
        self.context = None
        self.page = None
        self.timeout = timeout
        
        # 数据存储
        self.captured_comments = []
        # 更新京东评论API的匹配模式，增加更多可能的模式
        self.comment_api_pattern = re.compile(r'(comment\?callback=fetchJSON_comment|club\.jd\.com/comment/skuProductPageComments\.action|club\.jd\.com/comment/productPageComments\.action|getCommentListWithCard|productapi\.yiyaojd\.com|pop/commentServer)')
        self.test_mode = test_mode
        
        # 记录API请求信息
        self.api_requests = []

    async def setup(self):
        """设置Playwright浏览器实例，修复版本"""
        try:
            playwright = await async_playwright().start()
            
            # 精简浏览器启动参数，移除--user-data-dir
            browser_args = [
                '--no-sandbox',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-breakpad',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
            
            # 使用persistent_context方式启动浏览器
            self.context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                args=browser_args,
                viewport={"width": 1920, "height": 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
                timeout=self.timeout
            )
            
            # 减少JavaScript注入
            await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            """)
            
            # 设置路由处理
            await self.context.route(self.comment_api_pattern, self.intercept_comments)
            
            # 创建新页面
            self.page = await self.context.new_page()
            self.page.set_default_timeout(self.timeout)
            
            # 设置browser属性为None
            self.browser = None
            
            return self
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            logger.error(traceback.format_exc())
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass
            raise e

    async def intercept_comments(self, route, request):
        """拦截评论请求并处理响应"""
        try:
            # 记录拦截到的URL
            url = request.url
            logger.info(f"拦截到评论请求: {url}")
            self.api_requests.append(url)
            
            # 记录请求头部信息用于调试
            headers = request.headers
            logger.info(f"请求头部: {headers}")
            
            # 继续请求
            await route.continue_()
            
            # 等待响应
            response = await request.response()
            
            if not response:
                logger.warning(f"未获取到响应: {url}")
                return
                
            if response.ok:
                logger.info(f"成功获取响应: {url}, 状态码: {response.status}")
                try:
                    body = await response.text()
                    logger.info(f"响应大小: {len(body)} 字节")
                    
                    # 保存第一部分响应用于调试
                    debug_body = body[:500] + ("..." if len(body) > 500 else "")
                    logger.info(f"响应内容片段: {debug_body}")
                    
                    # 处理JSONP响应
                    if 'fetchJSON_comment' in body:
                        logger.info("检测到JSONP响应，提取JSON数据")
                        json_str = re.search(r'fetchJSON_comment\d*\((.*)\);', body)
                        if json_str:
                            body = json_str.group(1)
                            logger.info("JSONP提取成功")
                        else:
                            logger.warning("JSONP格式提取失败")
                    
                    # 尝试解析JSON
                    try:
                        data = json.loads(body)
                        logger.info(f"JSON解析成功，数据结构: {list(data.keys())}")
                        
                        # 尝试多种可能的评论字段
                        comment_fields = ['comments', 'data', 'commentList', 'list']
                        comments = None
                        
                        for field in comment_fields:
                            if field in data:
                                if isinstance(data[field], list):
                                    comments = data[field]
                                    logger.info(f"从字段 '{field}' 找到评论列表，包含 {len(comments)} 条评论")
                                    break
                                elif isinstance(data[field], dict) and 'comments' in data[field]:
                                    comments = data[field]['comments']
                                    logger.info(f"从嵌套字段 '{field}.comments' 找到评论列表，包含 {len(comments)} 条评论")
                                    break
                        
                        if not comments and 'commentInfoList' in data:
                            comments = data['commentInfoList']
                            logger.info(f"从字段 'commentInfoList' 找到评论列表，包含 {len(comments)} 条评论")
                        
                        if comments:
                            logger.info(f"成功捕获 {len(comments)} 条评论")
                            
                            for comment in comments:
                                # 尝试多种可能的内容字段
                                content = None
                                for content_field in ['content', 'commentData', 'commentContent', 'comment']:
                                    if content_field in comment and comment[content_field]:
                                        content = comment[content_field]
                                        break
                                
                                if content:  # 只添加有内容的评论
                                    comment_data = {
                                        'content': content,
                                        'creationTime': comment.get('creationTime', comment.get('commentTime', comment.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))),
                                        'nickname': comment.get('nickname', comment.get('userName', comment.get('userNickName', '匿名用户'))),
                                        'score': comment.get('score', comment.get('starCount', comment.get('star', 5))),
                                        'userLevelName': comment.get('userLevelName', comment.get('userLevel', '')),
                                        'productColor': comment.get('productColor', comment.get('color', '')),
                                        'productSize': comment.get('productSize', comment.get('size', '')),
                                        'images': comment.get('images', comment.get('pics', []))
                                    }
                                    
                                    logger.info(f"处理评论: {comment_data['nickname']} - {comment_data['content'][:30]}...")
                                    
                                    # 避免重复添加相同评论
                                    content_exists = any(c['content'] == comment_data['content'] and 
                                                       c['nickname'] == comment_data['nickname'] 
                                                       for c in self.captured_comments)
                                    if not content_exists:
                                        self.captured_comments.append(comment_data)
                                        logger.info(f"添加新评论: {comment_data['nickname']} - {comment_data['content'][:30]}...")
                                    else:
                                        logger.info("评论已存在，跳过")
                        else:
                            logger.warning(f"未在响应中找到评论数据，响应键: {list(data.keys())}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")
                        logger.error(f"响应内容片段: {body[:200]}...")
                except Exception as e:
                    logger.error(f"处理评论数据时出错: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"请求失败，状态码: {response.status}, URL: {url}")
        except Exception as e:
            logger.error(f"拦截评论请求失败: {e}")
            logger.error(traceback.format_exc())

    async def load_comments(self, product_url, max_pages=3):
        """加载商品评论"""
        if self.test_mode:
            logger.info("测试模式：生成模拟评论数据")
            for i in range(10):
                comment_data = {
                    'content': f"这是一条测试评论 {i+1}，测试商品质量很好！",
                    'creationTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'nickname': f"测试用户_{i+1}",
                    'score': random.randint(1, 5),
                    'userLevelName': "普通会员",
                    'productColor': "默认",
                    'productSize': "默认",
                    'images': []
                }
                self.captured_comments.append(comment_data)
            return self.captured_comments

        logger.info(f"开始加载商品页面: {product_url}")
        
        # 提取商品ID
        sku_id = re.search(r'/(\d+)\.html', product_url)
        if not sku_id:
            logger.error(f"无法从URL中提取商品ID: {product_url}")
            return []
            
        product_id = sku_id.group(1)
        logger.info(f"提取到商品ID: {product_id}")
        
        # 重试机制
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 确保页面处于活动状态
                if not self.page or self.page.is_closed():
                    # 如果页面已关闭，创建新页面
                    logger.info("页面已关闭，创建新页面")
                    self.page = await self.context.new_page()
                    self.page.set_default_timeout(self.timeout)
                
                # 设置更长的超时时间
                timeout_option = {"timeout": self.timeout, "wait_until": "domcontentloaded"}
                
                # 首先访问原始商品页面
                logger.info(f"访问商品页面: {product_url}")
                await self.page.goto(product_url, **timeout_option)
                
                # 等待页面加载
                logger.info("等待页面完全加载")
                await asyncio.sleep(5)
                
                # 记录页面标题，用于确认是否正确加载
                title = await self.page.title()
                logger.info(f"页面标题: {title}")
                
                # 模拟人类滚动行为
                logger.info("模拟滚动行为")
                for i in range(5):
                    await self.page.evaluate(f"window.scrollTo(0, {(i+1) * 800})")
                    await asyncio.sleep(1)
                
                # 构建并直接访问多个评论API URL
                comment_api_urls = [
                    f"https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98&productId={product_id}&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0",
                    f"https://club.jd.com/comment/skuProductPageComments.action?callback=fetchJSON_comment98&productId={product_id}&score=0&sortType=5&page=0&pageSize=10",
                    f"https://api.m.jd.com/api?functionId=getCommentListWithCard&body=%7B%22productId%22:%22{product_id}%22,%22score%22:0,%22sortType%22:5,%22page%22:0,%22pageSize%22:10%7D"
                ]
                
                # 逐个尝试访问评论API
                for api_url in comment_api_urls:
                    logger.info(f"尝试访问评论API: {api_url}")
                    try:
                        await self.page.goto(api_url, timeout=30000)
                        await asyncio.sleep(3)
                        
                        # 如果已经捕获到评论，则跳出循环
                        if len(self.captured_comments) > 0:
                            logger.info(f"已成功捕获 {len(self.captured_comments)} 条评论，停止尝试其他API")
                            break
                    except Exception as e:
                        logger.warning(f"访问评论API出错: {e}")
                
                # 如果直接访问API未成功，尝试使用XHR请求
                if len(self.captured_comments) == 0:
                    logger.info("尝试使用页面内XHR请求获取评论")
                    
                    # 回到商品页面
                    await self.page.goto(product_url, **timeout_option)
                    await asyncio.sleep(3)
                    
                    # 模拟点击评论标签触发XHR请求
                    comment_selectors = [
                        "#detail > div.tab-main > ul > li:nth-child(4)",
                        "//a[contains(text(), '商品评价')]",
                        "#comment",
                        ".tab-main li:nth-child(4)",
                        "a.anchor[name='comment']",
                        "//li[contains(@class, 'comment')]",
                        "//li[contains(@class, 'curr')]/following-sibling::li"
                    ]
                    
                    for selector in comment_selectors:
                        try:
                            logger.info(f"尝试点击评论选择器: {selector}")
                            try:
                                if selector.startswith("//"):
                                    element = await self.page.wait_for_selector(f"xpath={selector}", 
                                                                            state="visible", 
                                                                            timeout=5000)
                                else:
                                    element = await self.page.wait_for_selector(selector, 
                                                                            state="visible", 
                                                                            timeout=5000)
                                
                                if element:
                                    # 先滚动到元素位置
                                    await element.scroll_into_view_if_needed()
                                    await asyncio.sleep(1)
                                    
                                    # 点击元素
                                    await element.click()
                                    logger.info(f"成功点击评论选择器: {selector}")
                                    await asyncio.sleep(5)
                                    
                                    # 再次滚动页面
                                    await self.page.evaluate("window.scrollBy(0, 500)")
                                    await asyncio.sleep(2)
                                    
                                    # 如果已经捕获到评论，则跳出循环
                                    if len(self.captured_comments) > 0:
                                        logger.info(f"点击后成功捕获 {len(self.captured_comments)} 条评论")
                                        break
                            except Exception as e:
                                logger.warning(f"点击选择器 {selector} 失败: {e}")
                        except Exception as e:
                            logger.warning(f"处理选择器 {selector} 时出错: {e}")
                
                # 最后检查是否获取到评论
                if len(self.captured_comments) > 0:
                    logger.info(f"成功获取 {len(self.captured_comments)} 条评论")
                    return self.captured_comments
                else:
                    logger.warning("尝试所有方法后仍未获取到评论，重试中...")
                    retry_count += 1
                    await asyncio.sleep(2)
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"加载评论时出错: {e}")
                logger.error(traceback.format_exc())
                
                if retry_count < max_retries:
                    logger.info(f"重试第 {retry_count} 次 (共{max_retries}次)")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"已重试 {max_retries} 次，仍然失败")
                    # 记录失败原因和已发出的请求
                    logger.info(f"失败分析 - 已发出的API请求: {len(self.api_requests)}")
                    for i, req in enumerate(self.api_requests):
                        logger.info(f"请求 {i+1}: {req}")
                    return []
        
        return self.captured_comments

    async def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                try:
                    await self.page.close()
                except:
                    pass
                self.page = None
                
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass
                self.context = None
                
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
                self.browser = None
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")
            logger.error(traceback.format_exc())