from flask import Flask, request, jsonify
import asyncio
import json
import re
import traceback
import logging
from jd import JDCommentScraper
import mysql.connector
from flask_socketio import SocketIO
import threading
from datetime import datetime
import random
from flask_cors import CORS
from pathlib import Path
from playwright.async_api import async_playwright

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('jd_crawler')

app = Flask(__name__)
# 启用CORS跨域资源共享
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SECRET_KEY'] = 'jd_crawler_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

# 数据库配置
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "12345678",
    "database": "SEP"
}

class WebSocketJDScraper(JDCommentScraper):
    def __init__(self, product_id, product_name, headless=True, test_mode=True):
        # 确保每个爬虫实例使用独立的用户数据目录
        user_data_dir = Path(__file__).parent / "jd_user_data" / f"profile_{product_id}"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 调用父类初始化
        super().__init__(headless=headless, test_mode=test_mode, user_data_dir=str(user_data_dir))
        
        # 设置实例变量
        self.product_id = product_id
        self.product_name = product_name
        self.total_comments_count = 0
        self.browser_launch_attempts = 0
        self.max_launch_attempts = 3
    
    async def setup(self):
        """设置Playwright浏览器实例"""
        try:
            playwright = await async_playwright().start()
            
            # 精简浏览器启动参数，增加稳定性
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
            ]
            
            # 重试机制
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    # 使用chromium内核
                    self.browser = await playwright.chromium.launch(
                        headless=self.headless,
                        args=browser_args,
                        timeout=self.timeout,
                        handle_sigint=False,
                        handle_sigterm=False,
                        handle_sighup=False
                    )
                    
                    # 创建新的上下文
                    self.context = await self.browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
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
                    
                    return self
                    
                except Exception as e:
                    last_error = e
                    retry_count += 1
                    logger.warning(f"浏览器启动失败，第 {retry_count} 次重试...")
                    if self.browser:
                        try:
                            await self.browser.close()
                        except:
                            pass
                    await asyncio.sleep(2)
            
            raise Exception(f"浏览器启动失败，已重试 {max_retries} 次: {last_error}")
            
        except Exception as e:
            logger.error(f"浏览器设置失败: {e}")
            logger.error(traceback.format_exc())
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
            raise
    
    async def close(self):
        """安全关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")

def run_crawler(product_url, product_id, product_name):
    """后台执行爬虫任务"""
    always_test_mode = False
    
    async def run():
        scraper = None
        try:
            logger.info(f"开始爬取商品: {product_id} - {product_name}")
            socketio.emit('progress', {'status': 'starting', 'product_id': product_id})
            
            try:
                # 创建爬虫实例
                scraper = WebSocketJDScraper(product_id, product_name, headless=True, test_mode=always_test_mode)
                # 初始化浏览器
                await scraper.setup()
                
                # 爬取评论
                await scraper.load_comments(product_url)
                
                logger.info(f"商品 {product_id} 爬取完成，共获取 {len(scraper.captured_comments)} 条评论")
                socketio.emit('progress', {
                    'status': 'completed',
                    'count': len(scraper.captured_comments),
                    'product_id': product_id
                })
                
            except Exception as e:
                logger.error(f"爬虫执行失败: {e}")
                logger.error(traceback.format_exc())
                socketio.emit('error', {'message': f'爬虫执行失败: {str(e)}'})
            
        finally:
            # 确保浏览器被关闭
            if scraper:
                try:
                    await scraper.close()
                except Exception as e:
                    logger.error(f"关闭浏览器失败: {e}")
    
    # 在新的事件循环中运行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    except Exception as e:
        logger.error(f"爬虫任务执行错误: {e}")
        logger.error(traceback.format_exc())
        socketio.emit('error', {'message': f'爬虫任务执行错误: {str(e)}'})
    finally:
        loop.close()

@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    """启动爬虫的API端点"""
    try:
        data = request.json
        logger.info(f"收到爬取请求: {data}")
        
        # 检查必要参数
        product_url = data.get('url')
        product_id = data.get('product_id')
        product_name = data.get('product_name', '')
        
        if not product_url or not product_id:
            logger.warning("请求缺少必要参数")
            return jsonify({'success': False, 'message': '缺少商品URL或ID'}), 400
        
        # 检查数据库连接
        if not check_database_connection():
            return jsonify({'success': False, 'message': '数据库连接失败，请检查配置'}), 500
        
        # 启动爬虫线程
        thread = threading.Thread(target=run_crawler, args=(product_url, product_id, product_name))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': '爬虫已启动'})
    
    except Exception as e:
        logger.error(f"启动爬虫失败: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'启动爬虫失败: {str(e)}'}), 500

@socketio.on('connect')
def handle_connect():
    logger.info(f"客户端已连接: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"客户端已断开连接: {request.sid}")

@app.route('/')
def index():
    return jsonify({"status": "服务正常运行", "version": "1.0"})

if __name__ == '__main__':
    # 启动前检查数据库连接
    if check_database_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接失败，服务可能无法正常工作")
    
    # 启动服务
    logger.info("启动Flask-SocketIO服务，监听端口 5004")
    socketio.run(app, host='0.0.0.0', port=5004, debug=False, allow_unsafe_werkzeug=True)
