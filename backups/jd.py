import asyncio
import json
import os
import random
import re
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path
import pandas as pd # For Excel export

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JDCommentScraper:
    def __init__(self, headless=False, user_data_dir="jd_user_data", timeout=90000, test_mode=False):
        # 基本配置
        self.headless = headless
        if user_data_dir:
            self.user_data_dir = Path(user_data_dir).absolute()
            self.user_data_dir.mkdir(exist_ok=True)
        else:
            self.user_data_dir = Path(__file__).parent / "jd_user_data"
            self.user_data_dir.mkdir(exist_ok=True)
        
        # 浏览器相关
        self.browser = None
        self.context = None
        self.page = None
        self.timeout = timeout
        
        # 数据存储
        self.captured_comments = []
        self.comment_api_pattern = re.compile(r'comment\?callback=fetchJSON_comment|club.jd.com/comment/skuProductPageComments.action|club.jd.com/comment/productPageComments.action')
        self.test_mode = test_mode
        
    async def setup(self):
        """设置Playwright浏览器实例，增强反爬措施"""
        playwright = await async_playwright().start()
        
        # 精简必要的浏览器启动参数，增加稳定性配置
        browser_args = [
            '--no-sandbox',
            '--no-zygote',
            '--single-process',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--disable-breakpad',
            '--disable-ipc-flooding-protection',
            '--window-size=1920,1080',
            '--start-maximized',
            f'--user-data-dir={str(self.user_data_dir)}'
            '--disable-popup-blocking',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=browser_args,
            timeout=self.timeout
        )
        
        # 使用持久化的用户目录
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            storage_state=str(self.user_data_dir / "storage.json") if (self.user_data_dir / "storage.json").exists() else None,
        )
        
        # 更全面的浏览器环境模拟
        await self.context.add_init_script("""
        () => {
            // 覆盖WebDriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
                configurable: true
            });
            
            // 添加媒体设备
            if (!navigator.mediaDevices) {
                navigator.mediaDevices = {};
            }
            
            // 添加语言和平台信息
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });
            
            // 添加插件信息
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return {
                        length: 5,
                        item: () => { return {}; },
                        namedItem: () => { return {}; },
                        refresh: () => {}
                    };
                },
                configurable: true
            });
            
            // 修改Canvas指纹
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, attributes) {
                const context = originalGetContext.call(this, type, attributes);
                if (type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function() {
                        return originalFillText.apply(this, arguments);
                    };
                }
                return context;
            };
        }
        """)
        
        # 设置拦截器捕获评论API响应
        await self.context.route(self.comment_api_pattern, self.intercept_comments)
        
        # 设置请求拦截，过滤部分资源加快加载
        await self.context.route("**/*.{png,jpg,jpeg,gif,svg,webp}", lambda route: route.abort() if random.random() < 0.5 else route.continue_())
        await self.context.route("**/*.{css}", lambda route: route.continue_())
        await self.context.route("**/*.{woff,woff2,ttf,otf,eot}", lambda route: route.abort() if random.random() < 0.5 else route.continue_())
        
        self.page = await self.context.new_page()
        
        # 增加页面默认超时
        self.page.set_default_timeout(self.timeout)
        
        logger.info("Playwright浏览器已初始化（增强反爬措施）")
        return self
        
    async def intercept_comments(self, route, request):
        """拦截评论API请求的响应并提取数据"""
        await route.continue_()
        try:
            response = await route.fetch()
            
            if response.ok:
                try:
                    body = await response.text()
                    
                    # 处理JSONP响应
                    if 'fetchJSON_comment' in body:
                        json_str = re.search(r'fetchJSON_comment\d*\((.*)\);', body)
                        if json_str:
                            body = json_str.group(1)
                    
                    data = json.loads(body)
                    
                    if 'comments' in data:
                        comments = data['comments']
                        logger.info(f"成功捕获 {len(comments)} 条评论")
                        
                        for comment in comments:
                            if comment.get('content'):  # 只添加有内容的评论
                                comment_data = {
                                    'content': comment.get('content', ''),
                                    'creationTime': comment.get('creationTime', ''),
                                    'nickname': comment.get('nickname', ''),
                                    'score': comment.get('score', 0),
                                    'userLevelName': comment.get('userLevelName', ''),
                                    'productColor': comment.get('productColor', ''),
                                    'productSize': comment.get('productSize', ''),
                                    'images': comment.get('images', [])
                                }
                                # 避免重复添加相同评论
                                content_exists = any(c['content'] == comment_data['content'] and 
                                                    c['nickname'] == comment_data['nickname'] 
                                                    for c in self.captured_comments)
                                if not content_exists:
                                    self.captured_comments.append(comment_data)
                except Exception as e:
                    logger.error(f"处理拦截的评论数据时出错: {e}")
        except Exception as e:
            logger.error(f"拦截评论请求失败: {e}")
    
    async def login_if_needed(self):
        """检查登录状态并在需要时引导用户登录，增加错误处理"""
        try:
            # 启用真实登录检查，移除测试模式的跳过逻辑
            # if self.test_mode:
            #     logger.info("测试模式：跳过登录检查")
            #     return
                
            await self.page.goto("https://home.jd.com/", 
                                wait_until="domcontentloaded", 
                                timeout=self.timeout)
            await asyncio.sleep(5)
            
            # 检查是否需要登录
            is_login_page = "login" in self.page.url
            need_login = False
            
            try:
                need_login = await self.page.is_visible("text=请登录", timeout=5000) or is_login_page
            except:
                # 尝试其他检测方法
                need_login = is_login_page or await self.page.is_visible("xpath=//a[contains(text(), '登录') or contains(text(), '注册')]", timeout=3000)
            
            if need_login:
                logger.info("需要登录，等待用户手动完成京东登录...")
                print("=" * 60)
                print("请在打开的浏览器中完成京东登录，需要扫码或输入验证码")
                print("登录成功后系统将自动继续")
                print("提示: 登录成功后应该能看到'欢迎登录'或个人中心页面")
                print("=" * 60)
                
                # 等待登录成功，使用更可靠的检测方法
                login_success = False
                start_time = time.time()
                logger.info("开始检测登录状态...")
                while time.time() - start_time < 300:  # 最多等待5分钟
                    await asyncio.sleep(3)
                    current_url = self.page.url
                    logger.info(f"当前URL: {current_url}")
                    
                    # 检查URL是否不再是登录页
                    if "login" not in current_url and "passport.jd.com" not in current_url:
                        logger.info("URL不再是登录页。尝试检查用户元素...")
                        try:
                            # 尝试多种选择器确认登录
                            # 1. 用户昵称
                            nickname_visible = await self.page.is_visible("xpath=//a[contains(@class, 'nickname') and string-length(normalize-space(text())) > 0]", timeout=2000)
                            # 2. "我的京东" 链接 (确保不是登录页上的)
                            my_jd_visible = await self.page.is_visible("xpath=//a[normalize-space(text())='我的京东' and not(contains(@href, 'passport.jd.com'))]", timeout=2000)
                            # 3. 另一个常见的用户区域标识
                            user_info_area = await self.page.is_visible("xpath=//div[@id='J_userApp']//div[@class='userinfo_tip']", timeout=2000) # 可能的京东首页用户区域
                            # 4. 原有的检查
                            original_check_visible = await self.page.is_visible("xpath=//a[contains(@href, 'myjd') or contains(@class, 'user')]", timeout=2000)

                            logger.info(f"用户元素可见性: nickname: {nickname_visible}, 我的京东: {my_jd_visible}, 用户区域: {user_info_area}, 原检查: {original_check_visible}")

                            if nickname_visible or my_jd_visible or user_info_area or original_check_visible:
                                login_success = True
                                logger.info("检测到用户元素，判定登录成功。")
                                break
                            else:
                                logger.info("未检测到明确的用户元素。继续等待...")
                        except Exception as e_vis:
                            logger.warning(f"检查用户元素时发生异常: {e_vis}")
                            pass # 继续循环
                    else:
                        logger.info(f"当前URL ({current_url}) 仍被识别为登录相关页面。")
                
                if login_success:
                    # 保存登录状态
                    storage = await self.context.storage_state()
                    with open(self.user_data_dir / "storage.json", "w") as f:
                        json.dump(storage, f)
                    
                    logger.info("登录成功，已保存会话状态")
                else:
                    logger.warning("等待登录超时，请确认是否成功登录")
            else:
                logger.info("用户已登录，无需额外操作")
        except Exception as e:
            logger.error(f"登录检查过程中出错: {e}")
            # 如果是超时错误，给更明确的提示
            if isinstance(e, TimeoutError):
                logger.error("页面加载超时，可能是网络问题或被京东反爬系统拦截")
    
    async def scroll_with_human_like_behavior(self):
        """模拟更逼真的人类滚动行为，包括随机暂停和鼠标移动"""
        try:
            height = await self.page.evaluate("document.body.scrollHeight")
            viewport_height = await self.page.evaluate("window.innerHeight")
            
            # 随机起始点
            start_pos = random.randint(0, viewport_height // 3)
            await self.page.evaluate(f"window.scrollTo(0, {start_pos})")
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # 分段滚动，每段随机停顿
            segments = random.randint(5, 10)
            for i in range(segments):
                # 目标位置在当前段的范围内随机选择
                current_pos = await self.page.evaluate("window.pageYOffset")
                target_pos = random.randint(
                    int(current_pos + (height - current_pos) * 0.1),
                    int(current_pos + (height - current_pos) * 0.3)
                )
                
                # 使用平滑滚动
                await self.page.evaluate(f"window.scrollTo({{top: {target_pos}, behavior: 'smooth'}})")
                
                # 随机等待时间
                await asyncio.sleep(random.uniform(0.7, 2.5))
                
                # 随机的微小上下抖动（像人类阅读时那样）
                if random.random() < 0.3:  # 30%的概率
                    jitter = random.randint(-30, 30)
                    await self.page.evaluate(f"window.scrollBy(0, {jitter})")
                    await asyncio.sleep(random.uniform(0.3, 1.0))
                
                # 随机鼠标移动
                if random.random() < 0.4:  # 40%的概率
                    x = random.randint(100, 1000)
                    y = random.randint(100, 500)
                    await self.page.mouse.move(x, y)
            
            # 最后滚动到评论区域附近
            comment_scroll_pos = int(height * 0.7)  # 大约70%的页面高度
            await self.page.evaluate(f"window.scrollTo({{top: {comment_scroll_pos}, behavior: 'smooth'}})")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            logger.error(f"执行人类滚动行为时出错: {e}")
    
    async def navigate_to_comments(self, product_url):
        """导航到产品评论区，增强错误处理和加载策略"""
        logger.info(f"访问商品页面: {product_url}")
        
        # 尝试使用不同的导航选项
        success = False
        for attempt in range(3):  # 最多尝试3次
            try:
                # 每次尝试使用不同的等待策略
                wait_options = ["domcontentloaded", "load", "networkidle"]
                wait_until = wait_options[attempt % len(wait_options)]
                
                logger.info(f"尝试第 {attempt+1} 次访问页面，等待条件: {wait_until}")
                await self.page.goto(
                    product_url,
                    timeout=self.timeout,
                    wait_until=wait_until
                )
                
                # 等待页面主要内容加载
                try:
                    await self.page.wait_for_selector("#detail, .sku-name, .product-intro", timeout=10000)
                    success = True
                    break
                except:
                    logger.warning(f"未能检测到产品详情元素，继续尝试...")
                    if attempt < 2:
                        await asyncio.sleep(5)
            
            except TimeoutError as e:
                logger.warning(f"页面加载超时 (尝试 {attempt+1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(10)  # 较长的等待时间再试
            except Exception as e:
                logger.error(f"页面导航过程中出错 (尝试 {attempt+1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
        
        if not success:
            logger.error("多次尝试后仍无法加载页面，将尝试直接获取评论API数据")
            return False
        
        # 给页面充分加载时间
        await asyncio.sleep(8)
        
        # 模拟人类浏览行为
        await self.scroll_with_human_like_behavior()
        
        # 尝试点击"商品评价"选项卡，增加更多选择器匹配可能性
        clicked_tab = False
        selectors = [
            "#detail > div.tab-main.J-detail-main > ul > li:nth-child(5)",
            "#detail > div.tab-main.J-detail-main > ul > li:nth-child(4)",
            "#detail > div.tab-main > ul > li:nth-child(4)",
            "#detail > ul.J-detail-tab.tabs > li.item:nth-child(4)",
            "//a[contains(text(), '商品评价')]",
            "//a[contains(@href, '#comment')]",
            "//div[contains(text(), '商品评价')]",
            "//li[contains(@data-anchor, 'comment')]",
            "//li[contains(@data-tab, 'comment') or contains(@data-tab, 'review')]",
            "//div[contains(@class, 'tab') and contains(text(), '评价')]",
            "#comment-tab"
        ]
        
        for selector in selectors:
            if clicked_tab:
                break
                
            try:
                logger.info(f"尝试点击选择器: {selector}")
                
                if selector.startswith("//"):
                    # XPath选择器
                    elements = await self.page.query_selector_all(f"xpath={selector}")
                    for element in elements:
                        try:
                            if await element.is_visible() and await element.is_enabled():
                                await element.click()
                                logger.info(f"成功点击评论标签: {selector}")
                                clicked_tab = True
                                await asyncio.sleep(3)
                                break
                        except:
                            continue
                else:
                    # CSS选择器
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"成功点击评论标签: {selector}")
                        clicked_tab = True
                        await asyncio.sleep(3)
            except Exception as e:
                logger.debug(f"未能使用选择器 {selector} 点击评论标签: {e}")
        
        # 如果没有成功点击标签，尝试直接滚动到评论区
        if not clicked_tab:
            logger.warning("未能点击评论标签，尝试直接滚动到评论区")
            for comment_id in ["#comment", "#J_DetailReview", "#J_ReviewsCount", ".J_RateCounter"]:
                try:
                    # 尝试查找元素
                    element = await self.page.query_selector(comment_id)
                    if element:
                        # 滚动到元素
                        await element.scroll_into_view_if_needed()
                        logger.info(f"已滚动到评论区元素: {comment_id}")
                        await asyncio.sleep(3)
                        break
                except Exception as e:
                    logger.debug(f"无法滚动到评论区元素 {comment_id}: {e}")
            
        return True
    
    async def fetch_comments_via_api(self, sku_id, max_pages=3):
        """直接通过API获取评论作为备选方案"""
        logger.info(f"尝试通过直接API请求获取商品 {sku_id} 的评论")
        api_comments = []
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
        ]
        
        # 使用会话保持Cookie一致性
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Referer': f'https://item.jd.com/{sku_id}.html',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })
        
        # 提取页面中的cookie
        if self.context:
            try:
                cookies = await self.context.cookies()
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
            except Exception as e:
                logger.error(f"提取浏览器Cookie失败: {e}")
        
        for page in range(0, max_pages):
            try:
                # 随机延迟避免请求过快
                await asyncio.sleep(random.uniform(1, 3))
                
                # 构建不同的API URL尝试几种变体
                api_urls = [
                    f"https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98&productId={sku_id}&score=0&sortType=5&page={page}&pageSize=10&isShadowSku=0&fold=1",
                    f"https://club.jd.com/comment/skuProductPageComments.action?callback=fetchJSON_comment98&productId={sku_id}&score=0&sortType=5&page={page}&pageSize=10&isShadowSku=0&fold=1"
                ]
                
                success = False
                for api_url in api_urls:
                    try:
                        response = session.get(api_url, timeout=20)
                        if response.status_code == 200:
                            # 处理JSONP响应
                            text = response.text
                            json_str = re.search(r'fetchJSON_comment\d*\((.*)\);', text)
                            if json_str:
                                data = json.loads(json_str.group(1))
                                
                                if 'comments' in data and data['comments']:
                                    comments = data['comments']
                                    logger.info(f"API成功获取第 {page+1} 页共 {len(comments)} 条评论")
                                    
                                    for comment in comments:
                                        if comment.get('content'):  # 只添加有内容的评论
                                            comment_data = {
                                                'content': comment.get('content', ''),
                                                'creationTime': comment.get('creationTime', ''),
                                                'nickname': comment.get('nickname', ''),
                                                'score': comment.get('score', 0),
                                                'userLevelName': comment.get('userLevelName', ''),
                                                'productColor': comment.get('productColor', ''),
                                                'productSize': comment.get('productSize', ''),
                                                'images': comment.get('images', [])
                                            }
                                            # 避免重复添加
                                            content_exists = any(c['content'] == comment_data['content'] and 
                                                               c['nickname'] == comment_data['nickname'] 
                                                               for c in api_comments)
                                            if not content_exists:
                                                api_comments.append(comment_data)
                                    
                                    success = True
                                    break
                                else:
                                    logger.warning(f"API页面 {page+1} 未返回有效评论数据")
                            else:
                                logger.warning("API响应格式不是预期的JSONP格式")
                        else:
                            logger.warning(f"API请求返回状态码 {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"API请求 {api_url} 失败: {e}")
                
                if not success:
                    logger.warning(f"第 {page+1} 页所有API尝试均失败")
                    
                # 如果连续两页没有新评论，退出循环
                if page >= 1 and not api_comments:
                    logger.info("连续多页无评论，结束API获取")
                    break
                    
            except Exception as e:
                logger.error(f"处理第 {page+1} 页API数据时出错: {e}")
        
        return api_comments
                
    async def load_comments(self, product_url, max_pages=3):
        """加载产品评论，全面优化并增加备选方案"""
        # 提取商品ID
        sku_id = None
        match = re.search(r'/(\d+)\.html', product_url)
        if match:
            sku_id = match.group(1)
        else:
            logger.error(f"无法从URL提取商品ID: {product_url}")
            return []
        
        logger.info(f"提取到商品ID: {sku_id}")
        
        # 测试模式下生成模拟数据
        if self.test_mode:
            logger.info("测试模式：生成模拟评论数据")
            for i in range(10):
                comment_data = {
                    'content': f"这是一条测试评论 {i+1}，用于测试爬虫功能。商品质量很好，非常满意！",
                    'creationTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'nickname': f"测试用户_{i+1}",
                    'score': random.randint(1, 5),
                    'userLevelName': f"级别{random.randint(1, 10)}",
                    'productColor': random.choice(["黑色", "白色", "蓝色", "红色"]),
                    'productSize': random.choice(["256GB", "128GB", "512GB"]),
                    'images': [],
                    'product_id': sku_id,
                    'product_name': "测试商品"
                }
                self.captured_comments.append(comment_data)
            logger.info(f"测试模式：已生成 {len(self.captured_comments)} 条模拟评论")
            return self.captured_comments
        
        # 检查并处理登录
        await self.login_if_needed()
        
        # 先尝试页面模拟法获取评论
        page_navigation_success = await self.navigate_to_comments(product_url)
        
        if page_navigation_success:
            logger.info("成功导航到评论区，现在尝试通过页面交互获取评论")
            
            # 如果已经捕获到了评论数据（通过拦截器），检查数量
            if len(self.captured_comments) > 0:
                logger.info(f"通过拦截器已捕获 {len(self.captured_comments)} 条评论")
            
            # 尝试翻页查看更多评论
            for page in range(1, max_pages + 1):
                if page > 1:  # 第一页已经在navigate_to_comments中处理
                    logger.info(f"尝试加载第 {page} 页评论")
                    
                    # 尝试点击下一页
                    next_page_clicked = False
                    for next_selector in [
                        "a.ui-pager-next:not(.ui-pager-disabled)",
                        "//a[contains(@class, 'next') and not(contains(@class, 'disabled'))]",
                        "//a[contains(text(), '下一页') and not(contains(@class, 'disabled'))]",
                        ".p-next"
                    ]:
                        try:
                            if next_selector.startswith("//"):
                                next_btn = await self.page.query_selector(f"xpath={next_selector}")
                            else:
                                next_btn = await self.page.query_selector(next_selector)
                                
                            if next_btn and await next_btn.is_visible() and await next_btn.is_enabled():
                                await next_btn.click()
                                logger.info(f"成功点击下一页按钮: {next_selector}")
                                next_page_clicked = True
                                await asyncio.sleep(random.uniform(3, 5))
                                break
                        except Exception as e:
                            logger.debug(f"点击下一页按钮 {next_selector} 失败: {e}")
                    
                    if not next_page_clicked:
                        logger.warning("未能点击到下一页按钮，可能已到末页或元素不存在")
                        break
                    
                # 直接访问评论API，尝试获取评论
                try:
                    logger.info(f"尝试直接访问评论API获取第 {page} 页")
                    # 尝试两种不同的API端点
                    for api_endpoint in [
                        f"https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98&productId={sku_id}&score=0&sortType=5&page={page-1}&pageSize=10&isShadowSku=0&fold=1",
                        f"https://club.jd.com/comment/skuProductPageComments.action?callback=fetchJSON_comment98&productId={sku_id}&score=0&sortType=5&page={page-1}&pageSize=10&isShadowSku=0&fold=1"
                    ]:
                        try:
                            await self.page.goto(api_endpoint, timeout=20000, wait_until="domcontentloaded")
                            await asyncio.sleep(random.uniform(2, 4))
                            break  # 如果成功，不再尝试第二个端点
                        except Exception as e:
                            logger.debug(f"访问 {api_endpoint} 失败: {e}")
                    
                    # 回到商品页面准备下一次加载
                    if page < max_pages:
                        try:
                            await self.page.goto(product_url, timeout=30000, wait_until="domcontentloaded")
                            await asyncio.sleep(3)
                            await self.navigate_to_comments(product_url)
                        except Exception as e:
                            logger.error(f"返回产品页面时出错: {e}")
                            break  # 如果无法返回商品页，退出循环
                except Exception as e:
                    logger.error(f"直接访问评论API时出错: {e}")
        
        # 如果页面交互方法未能获取足够评论，尝试直接API请求
        if len(self.captured_comments) < 3:  # 少于3条评论时尝试API方法
            logger.info("通过页面交互未获取到足够评论，尝试直接API请求")
            api_comments = await self.fetch_comments_via_api(sku_id, max_pages)
            
            if api_comments:
                logger.info(f"API请求成功获取 {len(api_comments)} 条评论")
                # 合并结果，避免重复
                for comment in api_comments:
                    content_exists = any(c['content'] == comment['content'] and 
                                        c['nickname'] == comment['nickname'] 
                                        for c in self.captured_comments)
                    if not content_exists:
                        self.captured_comments.append(comment)
        
        logger.info(f"总共获取到 {len(self.captured_comments)} 条评论")
        return self.captured_comments
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("浏览器已关闭")
    
    def save_comments(self, product_id):
        """保存评论数据到 JSON 和 Excel 文件"""
        if not self.captured_comments:
            logger.warning("没有评论数据可保存")
            return None, None # Return two Nones

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"jd_{product_id}_comments_{timestamp}"
        
        # Save to JSON
        json_filename = f"{base_filename}.json"
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.captured_comments, f, ensure_ascii=False, indent=4)
            logger.info(f"评论数据已保存到 {json_filename}")
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            json_filename = None

        # Save to Excel
        excel_filename = f"{base_filename}.xlsx"
        try:
            if not self.captured_comments: # 再次检查，以防JSON保存成功但列表为空
                logger.info("没有评论可用于Excel导出。")
                excel_filename = None
            else:
                df = pd.DataFrame(self.captured_comments)
                # 定义期望的列顺序，并筛选出实际存在的列
                cols_order = ['nickname', 'creationTime', 'score', 'content', 'userLevelName', 'productColor', 'productSize', 'images']
                df_cols = [col for col in cols_order if col in df.columns]
                if not df_cols: # 如果主要列都不存在，则使用所有可用列
                    df_cols = df.columns.tolist()
                df_filtered = df[df_cols]

                df_filtered.to_excel(excel_filename, index=False, engine='openpyxl')
                logger.info(f"评论数据已保存到 {excel_filename}")
        except Exception as e:
            logger.error(f"保存到Excel失败: {e}")
            excel_filename = None # Indicate failure

        return json_filename, excel_filename

async def main():
    parser = argparse.ArgumentParser(description="京东商品评论爬虫 (优化版 - Playwright)")
    parser.add_argument("-u", "--url", required=True, help="京东商品页面URL")
    parser.add_argument("-p", "--pages", type=int, default=3, help="要爬取的评论页数")
    parser.add_argument("--headless", action="store_true", help="启用无头模式")
    parser.add_argument("--timeout", type=int, default=90000, help="页面加载超时时间(毫秒)")
    parser.add_argument("--api-only", action="store_true", help="仅使用API获取评论，不进行页面交互")
    parser.add_argument("--test-mode", action="store_true", help="启用测试模式")
    args = parser.parse_args()
    
    if not args.url or not "jd.com" in args.url:
        print("请提供有效的京东商品URL，例如 https://item.jd.com/100016034372.html")
        return
    
    # 提取商品ID，用于文件命名
    product_id = "unknown"
    id_match = re.search(r'/(\d+)\.html', args.url)
    if id_match:
        product_id = id_match.group(1)
    
    try:
        scraper = await JDCommentScraper(
            headless=args.headless,
            timeout=args.timeout,
            test_mode=args.test_mode
        ).setup()
        
        if args.api_only:
            # 仅使用API模式获取评论
            logger.info("使用纯API模式获取评论...")
            comments = await scraper.fetch_comments_via_api(product_id, args.pages)
            scraper.captured_comments = comments
        else:
            # 使用完整的页面交互+API模式
            comments = await scraper.load_comments(args.url, args.pages)
        
        # 保存并显示结果
        json_saved_file, excel_saved_file = scraper.save_comments(product_id)

        if json_saved_file or excel_saved_file: # 检查是否至少有一个文件保存成功
            print("\n" + "="*60)
            
            saved_files_messages = []
            if json_saved_file:
                saved_files_messages.append(f"JSON ({json_saved_file})")
            if excel_saved_file:
                saved_files_messages.append(f"Excel ({excel_saved_file})")
            
            if saved_files_messages:
                 print(f"共获取到 {len(comments)} 条评论，已保存到 " + " 和 ".join(saved_files_messages))
            else: # Fallback, though unlikely if the outer if condition is met
                print(f"共获取到 {len(comments)} 条评论，但文件保存状态未知。")

            # 打印前3条评论作为示例
            print("\n评论示例:")
            for i, comment in enumerate(comments[:min(3, len(comments))]):
                print(f"[{i+1}] {comment.get('nickname', '匿名')} ({comment.get('creationTime', '')}) - 评分: {comment.get('score', '未知')}")
                print(f"    {comment.get('content', '')[:100]}..." + ("..." if len(comment.get('content', '')) > 100 else ""))
                print()
            print("="*60)
        else:
            print("\n未能获取到任何评论。")
            print("可能原因:")
            print("1. 该商品可能没有评论")
            print("2. 京东反爬机制阻止了访问")
            print("3. 您的网络环境可能被京东识别为爬虫")
            print("\n建议:")
            print("1. 尝试使用 --api-only 参数绕过页面交互")
            print("2. 使用 --timeout 增加超时时间，例如 --timeout 120000")
            print("3. 确保成功登录京东账号")
    except Exception as e:
        logger.error(f"脚本执行过程中发生错误: {e}", exc_info=True)
        print(f"\n程序执行过程中出现错误: {e}")
    finally:
        if 'scraper' in locals():
            await scraper.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行失败: {e}")