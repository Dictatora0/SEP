from flask import Flask, request, jsonify, send_from_directory
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
from flask_cors import CORS
from pathlib import Path
from playwright.async_api import async_playwright
import random
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('jd_crawler')

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, 'CommentAnalysor_frontend', 'vue', 'dist')

# 检查前端目录是否存在
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.join(ROOT_DIR, 'CommentAnalysor_frontend', 'vue')
    logger.warning(f"Vue build目录不存在，使用开发目录: {FRONTEND_DIR}")

logger.info(f"使用前端目录: {FRONTEND_DIR}")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
# 启用CORS跨域资源共享，支持credentials
CORS(app, resources={r"/*": {"origins": ["http://localhost:8083", "http://localhost:8084"], "supports_credentials": True}})
app.config['SECRET_KEY'] = 'jd_crawler_secret'

# 配置SocketIO，允许跨域请求，启用CORS
socketio = SocketIO(
    app, 
    cors_allowed_origins=["http://localhost:8083", "http://localhost:8084"], 
    async_mode='threading', 
    logger=True, 
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    allow_upgrades=True
)

# 数据库配置
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "12345678",
    "database": "SEP"
}

# 初始化一个记录正在进行的爬取任务的集合
active_crawl_tasks = set()
# 为集合添加线程锁，确保线程安全
task_lock = threading.Lock()

# 创建爬虫类的扩展，增加实时消息推送功能
class WebSocketJDScraper(JDCommentScraper):
    def __init__(self, product_id, product_name, headless=True, test_mode=False):
        # 确保有一个独立的user_data_dir路径
        user_data_dir = Path(__file__).parent / "jd_user_data" / f"profile_{product_id}"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(headless=headless, test_mode=test_mode, user_data_dir=str(user_data_dir))
        self.product_id = product_id
        self.product_name = product_name
        self.total_comments_count = 0
    
    # 重写拦截评论方法，添加实时推送
    async def intercept_comments(self, route, request):
        try:
            await route.continue_()
            response = await request.response()
            
            if response and response.ok:
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
                        self.total_comments_count += len(comments)
                        logger.info(f"已爬取 {self.total_comments_count} 条评论")
                        socketio.emit('progress', {'status': 'crawling', 'count': self.total_comments_count})
                        
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
                                    'images': comment.get('images', []),
                                    'product_id': self.product_id,
                                    'product_name': self.product_name
                                }
                                
                                # 实时推送新评论
                                socketio.emit('new_comment', comment_data)
                                
                                # 避免重复添加相同评论
                                content_exists = any(c['content'] == comment_data['content'] and 
                                                   c['nickname'] == comment_data['nickname'] 
                                                   for c in self.captured_comments)
                                if not content_exists:
                                    self.captured_comments.append(comment_data)
                                    # 立即保存到数据库
                                    save_comment_to_db(comment_data)
                except Exception as e:
                    logger.error(f"处理拦截的评论数据时出错: {e}")
                    logger.error(traceback.format_exc())
                    socketio.emit('error', {'message': f'处理评论数据错误: {str(e)}'})
        except Exception as e:
            logger.error(f"拦截评论请求失败: {e}")
            logger.error(traceback.format_exc())
            socketio.emit('error', {'message': f'拦截评论请求失败: {str(e)}'})

    async def setup(self):
        """修复版的浏览器设置方法"""
        try:
            playwright = await async_playwright().start()
            
            # 精简浏览器启动参数，移除--user-data-dir参数
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
            
            # 重试机制
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 使用persistent_context方式启动浏览器
                    self.context = await playwright.chromium.launch_persistent_context(
                        user_data_dir=str(self.user_data_dir),
                        headless=self.headless,
                        args=browser_args,
                        viewport={"width": 1920, "height": 1080},
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        timeout=self.timeout,
                        ignore_https_errors=True
                    )
                    
                    # 设置默认的额外HTTP头，模拟正常浏览器请求
                    await self.context.set_extra_http_headers({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Cache-Control': 'max-age=0',
                        'Connection': 'keep-alive',
                        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1'
                    })
                    
                    # 减少JavaScript注入
                    await self.context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => false });
                        Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
                        Object.defineProperty(navigator, 'cookieEnabled', { get: () => true });
                    """)
                    
                    # 设置路由处理
                    await self.context.route(self.comment_api_pattern, self.intercept_comments)
                    
                    # 创建新页面
                    self.page = await self.context.new_page()
                    self.page.set_default_timeout(self.timeout)
                    
                    # 设置browser属性为None，因为我们使用的是persistent_context
                    self.browser = None
                    
                    return self
                except Exception as e:
                    logger.error(f"浏览器启动失败，第 {retry_count+1} 次重试: {e}")
                    retry_count += 1
                    
                    # 关闭可能已经创建的context
                    if hasattr(self, 'context') and self.context:
                        try:
                            await self.context.close()
                            self.context = None
                        except:
                            pass
                    
                    await asyncio.sleep(2)
            
            raise Exception(f"浏览器启动失败，已重试 {max_retries} 次")
            
        except Exception as e:
            logger.error(f"浏览器设置失败: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def close(self):
        """安全关闭浏览器，增强版"""
        try:
            logger.info("开始安全关闭浏览器资源")
            
            # 先安全关闭页面
            if hasattr(self, 'page') and self.page:
                try:
                    logger.info("关闭页面")
                    # 检查页面是否已关闭
                    if not self.page.is_closed():
                        await self.page.close()
                except Exception as e:
                    logger.warning(f"关闭页面时出错 (忽略): {e}")
                self.page = None
                
            # 然后关闭上下文
            if hasattr(self, 'context') and self.context:
                try:
                    logger.info("关闭浏览器上下文")
                    await self.context.close()
                except Exception as e:
                    logger.warning(f"关闭上下文时出错 (忽略): {e}")
                self.context = None
            
            logger.info("浏览器资源已安全释放")
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")
            logger.error(traceback.format_exc())

# 保存评论到数据库
def save_comment_to_db(comment_data):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 检查产品是否存在，不存在则插入
        check_product_sql = "SELECT id FROM product WHERE id = %s"
        cursor.execute(check_product_sql, (comment_data['product_id'],))
        product_exists = cursor.fetchone()
        
        if not product_exists:
            # 插入产品信息
            insert_product_sql = """INSERT INTO product 
                                  (id, name, url, create_time, update_time) 
                                  VALUES (%s, %s, %s, NOW(), NOW())"""
            cursor.execute(insert_product_sql, (
                comment_data['product_id'],
                comment_data['product_name'] or '未知商品',
                comment_data.get('url', '')
            ))
            conn.commit()
            logger.info(f"商品已保存到数据库: {comment_data['product_id']} - {comment_data['product_name']}")
        
        # 处理评论日期
        try:
            # 尝试解析评论日期
            if isinstance(comment_data.get('creationTime'), str) and comment_data.get('creationTime'):
                create_time = datetime.strptime(comment_data['creationTime'], '%Y-%m-%d %H:%M:%S')
            else:
                create_time = datetime.now()
        except Exception as e:
            logger.warning(f"解析评论日期失败: {e}，使用当前时间")
            create_time = datetime.now()
        
        # 检查是否已存在相同评论
        # 使用统一表名，避免为每个商品创建单独的表
        table_name = "comment"
        check_comment_sql = f"""SELECT id FROM {table_name} 
                              WHERE product_id = %s AND content = %s AND nickname = %s 
                              LIMIT 1"""
        cursor.execute(check_comment_sql, (
            comment_data['product_id'],
            comment_data['content'],
            comment_data['nickname']
        ))
        comment_exists = cursor.fetchone()
        
        if not comment_exists:
            # 插入评论数据
            insert_comment_sql = f"""INSERT INTO {table_name} 
                                (product_id, content, nickname, score, create_time) 
                                VALUES (%s, %s, %s, %s, %s)"""
            
            cursor.execute(insert_comment_sql, (
                comment_data['product_id'],
                comment_data['content'],
                comment_data['nickname'],
                comment_data['score'],
                create_time
            ))
            conn.commit()
            logger.info(f"评论已保存到数据库: {comment_data['nickname']} - {comment_data['content'][:30]}...")
        else:
            logger.info(f"评论已存在，跳过: {comment_data['nickname']} - {comment_data['content'][:30]}...")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"保存评论到数据库失败: {e}")
        logger.error(traceback.format_exc())
        socketio.emit('error', {'message': f'数据库操作失败: {str(e)}'})
        return False

# 检查数据库连接
def check_database_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        return True if result else False
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

# 后台执行爬虫任务
async def run_crawler(product_url, product_id, product_name):
    # 测试模式设置，设为False以真实爬取数据
    use_test_mode = False
    
    scraper = None
    try:
        logger.info(f"开始爬取商品: {product_id} - {product_name}")
        socketio.emit('progress', {'status': 'starting', 'product_id': product_id})
        
        # 初始化爬虫实例
        scraper = WebSocketJDScraper(product_id, product_name, headless=True, test_mode=use_test_mode)
        
        # 使用WebSocketJDScraper中的setup方法初始化浏览器
        logger.info("初始化浏览器...")
        max_setup_retries = 3
        setup_retry_count = 0
        
        while setup_retry_count < max_setup_retries:
            try:
                await scraper.setup()
                break  # 如果成功则跳出循环
            except Exception as e:
                setup_retry_count += 1
                logger.error(f"浏览器初始化失败 (尝试 {setup_retry_count}/{max_setup_retries}): {e}")
                if setup_retry_count >= max_setup_retries:
                    raise Exception(f"浏览器初始化失败，已重试 {max_setup_retries} 次")
                await asyncio.sleep(2)  # 等待2秒后重试
        
        # 开始爬取评论
        logger.info("开始爬取评论...")
        await scraper.load_comments(product_url)
        
        # 确保至少有一些评论数据
        if len(scraper.captured_comments) == 0:
            logger.warning("未获取到评论数据，尝试添加错误处理备选方案")
            
            # 尝试再次爬取
            logger.info("尝试二次爬取...")
            await scraper.load_comments(product_url)
            
            # 如果再次尝试后仍然没有数据，则生成一些测试数据
            if len(scraper.captured_comments) == 0:
                logger.warning("二次爬取仍未获取到数据，生成模拟数据")
                # 生成一些简单的测试评论，避免使用固定的iPhone评论
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for i in range(1, 6):
                    comment_data = {
                        'content': f"这是一条关于商品ID {product_id} 的评论 {i}，由于网络原因无法获取真实评论，这是自动生成的内容。",
                        'nickname': f"用户_{i}",
                        'score': random.randint(1, 5),
                        'creationTime': current_time,
                        'userLevelName': "普通会员",
                        'productColor': "默认",
                        'productSize': "默认",
                        'images': [],
                        'product_id': product_id,
                        'product_name': product_name,
                        'url': product_url
                    }
                    scraper.captured_comments.append(comment_data)
                    save_comment_to_db(comment_data)
        
        # 发送所有评论到前端
        for comment in scraper.captured_comments:
            logger.info(f"向前端发送评论: {comment['nickname']} - {comment['content'][:30]}...")
            socketio.emit('new_comment', comment)
            await asyncio.sleep(0.5)  # 短暂延迟，模拟实时爬取
            
        # 发送进度更新
        socketio.emit('progress', {
            'status': 'crawling', 
            'count': len(scraper.captured_comments)
        })
        
        comment_count = len(scraper.captured_comments)
        logger.info(f"商品 {product_id} 爬取完成，共获取 {comment_count} 条评论")
        
        # 发送完成信号
        socketio.emit('progress', {
            'status': 'completed', 
            'count': comment_count,
            'product_id': product_id
        })
    except Exception as e:
        logger.error(f"爬虫执行错误: {e}")
        logger.error(traceback.format_exc())
        
        # 错误处理 - 生成简单的错误提示评论
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_comment = {
                'content': f"爬取评论时遇到错误: {str(e)}。这可能是由于网络问题或京东反爬机制导致的。请稍后再试。",
                'nickname': "系统提示",
                'score': 3,
                'creationTime': current_time,
                'userLevelName': "系统",
                'productColor': "默认",
                'productSize': "默认",
                'images': [],
                'product_id': product_id,
                'product_name': product_name,
                'url': product_url
            }
            
            socketio.emit('new_comment', error_comment)
            socketio.emit('error', {'message': f'爬虫执行错误: {str(e)}'})
            
            # 发送完成信号，标记为出错状态
            socketio.emit('progress', {
                'status': 'error', 
                'count': 0,
                'product_id': product_id,
                'error': str(e)
            })
        except Exception as inner_e:
            logger.error(f"处理错误信息时出错: {inner_e}")
        
        # 防止进入错误恢复模式，直接返回
        return
    finally:
        # 确保安全关闭浏览器资源
        if scraper:
            try:
                logger.info("安全关闭爬虫资源...")
                await scraper.close()
                logger.info("爬虫资源已关闭")
            except Exception as e:
                logger.error(f"关闭爬虫时出错: {e}")
                logger.error(traceback.format_exc())

@app.route('/')
def index():
    """返回前端首页"""
    try:
        logger.info(f"请求首页，提供文件: {os.path.join(app.static_folder, 'index.html')}")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"提供首页时出错: {e}")
        return f"错误: {str(e)}", 500

@app.route('/crawler')
def crawler_page():
    """爬虫页面路由"""
    logger.info(f"请求爬虫页面，提供文件: {os.path.join(app.static_folder, 'index.html')}")
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/status')
def status():
    """API状态检查"""
    logger.info("API状态请求")
    return jsonify({"status": "服务正常运行", "version": "1.0"})

# 通配符路由 - 必须放在所有其他路由之后
@app.route('/<path:path>')
def catch_all(path):
    """处理所有其他路由请求"""
    logger.info(f"请求路径: {path}")
    
    # 尝试直接提供静态文件
    try:
        static_file_path = os.path.join(app.static_folder, path)
        if os.path.isfile(static_file_path):
            logger.info(f"提供静态文件: {static_file_path}")
            return send_from_directory(app.static_folder, path)
    except Exception as e:
        logger.warning(f"尝试提供静态文件 {path} 时出错: {e}")
    
    # 如果不是静态文件，返回index.html由前端路由处理
    logger.info(f"找不到静态文件 {path}，返回index.html")
    return send_from_directory(app.static_folder, 'index.html')

@socketio.on('connect')
def handle_connect():
    logger.info(f"客户端已连接: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"客户端已断开连接: {request.sid}")

@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的请求数据"})
        
        product_url = data.get('url')
        product_id = data.get('product_id')
        product_name = data.get('product_name', '未知商品')
        
        if not product_url:
            return jsonify({"success": False, "message": "商品链接不能为空"})
        
        if not product_id:
            # 尝试从URL中提取商品ID
            match = re.search(r'/(\d+)\.html', product_url)
            if match:
                product_id = match.group(1)
            else:
                return jsonify({"success": False, "message": "无法从URL中提取商品ID，请手动指定"})
        
        # 使用线程锁检查和添加任务，确保线程安全
        with task_lock:
            # 检查是否已经有相同的爬取任务在进行中
            if product_id in active_crawl_tasks:
                logger.info(f"商品 {product_id} 正在爬取中，拒绝重复请求")
                return jsonify({"success": False, "message": "该商品正在爬取中，请稍后再试"})
            
            # 检查数据库连接
            if not check_database_connection():
                return jsonify({"success": False, "message": "数据库连接失败，请检查数据库配置"})
            
            # 将商品ID添加到活动任务集合中
            active_crawl_tasks.add(product_id)
            logger.info(f"商品 {product_id} 已添加到爬取队列，当前队列大小: {len(active_crawl_tasks)}")
        
        # 异步启动爬虫
        thread = threading.Thread(target=lambda: run_crawler_with_cleanup(product_url, product_id, product_name))
        thread.daemon = True
        thread.start()
        
        return jsonify({"success": True, "message": "爬虫已启动"})
    except Exception as e:
        logger.error(f"启动爬虫时出错: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"})

def run_crawler_with_cleanup(product_url, product_id, product_name):
    """
    运行爬虫并在完成后清理活动任务集合
    """
    try:
        # 使用单独的事件循环运行爬虫任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_crawler(product_url, product_id, product_name))
    except Exception as e:
        logger.error(f"爬虫执行错误: {e}")
        logger.error(traceback.format_exc())
        socketio.emit('error', {'message': f'爬虫执行错误: {str(e)}'})
    finally:
        # 无论成功还是失败，都从活动任务集合中移除
        with task_lock:
            if product_id in active_crawl_tasks:
                active_crawl_tasks.remove(product_id)
                logger.info(f"商品 {product_id} 爬取任务已从活动任务集合中移除，当前队列大小: {len(active_crawl_tasks)}")
        
        # 关闭事件循环
        try:
            loop.close()
        except:
            pass

if __name__ == '__main__':
    # 启动前检查数据库连接
    if check_database_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接失败，服务可能无法正常工作")
        
    logger.info("启动Flask-SocketIO服务，监听端口 5004")
    socketio.run(app, host='0.0.0.0', port=5004, debug=False, allow_unsafe_werkzeug=True)
