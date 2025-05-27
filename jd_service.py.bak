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

# 创建爬虫类的扩展，增加实时消息推送功能
class WebSocketJDScraper(JDCommentScraper):
    def __init__(self, product_id, product_name, headless=True, test_mode=True):
        super().__init__(headless=headless, test_mode=test_mode)
        self.product_id = product_id
        self.product_name = product_name
        self.total_comments_count = 0
    
    # 重写拦截评论方法，添加实时推送
    async def intercept_comments(self, route, request):
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
                        self.total_comments_count += len(comments)
                        logger.info(f"已爬取 {self.total_comments_count} 条评论")
                        socketio.emit('progress', {'status': 'crawling', 'count': self.total_comments_count, 'product_id': self.product_id})
                        
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
                                logger.debug(f"推送新评论: {comment_data['nickname']} - {comment_data['content'][:30]}...")
                                
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

    # 重写load_comments方法，确保测试模式下也能发送SocketIO消息
    async def load_comments(self, product_url, max_pages=3):
        """在测试模式下，确保模拟数据也会通过WebSocket发送"""
        # 调用父类的load_comments方法
        comments = await super().load_comments(product_url, max_pages)
        
        # 如果是测试模式，确保评论通过WebSocket发送
        if self.test_mode:
            logger.info("测试模式：通过WebSocket发送模拟评论")
            
            # 发送初始进度
            socketio.emit('progress', {'status': 'starting', 'product_id': self.product_id})
            await asyncio.sleep(1)  # 稍微延迟，模拟爬取过程
            
            # 逐条发送评论，模拟实时爬取效果
            for i, comment in enumerate(self.captured_comments):
                # 确保评论有product_id和product_name
                comment_data = {
                    **comment,
                    'product_id': self.product_id,
                    'product_name': self.product_name
                }
                
                # 发送评论和进度
                socketio.emit('new_comment', comment_data)
                self.total_comments_count += 1
                socketio.emit('progress', {
                    'status': 'crawling', 
                    'count': self.total_comments_count, 
                    'product_id': self.product_id
                })
                
                # 保存到数据库
                save_comment_to_db(comment_data)
                
                # 添加随机延迟，模拟真实爬取速度
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # 发送完成消息
            socketio.emit('progress', {
                'status': 'completed', 
                'count': len(self.captured_comments),
                'product_id': self.product_id
            })
        
        return comments

# 保存评论到数据库
def save_comment_to_db(comment_data):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 准备SQL语句
        sql = """INSERT INTO comment 
               (product_id, content, nickname, score, create_time) 
               VALUES (%s, %s, %s, %s, %s)"""
               
        # 转换日期格式
        creation_time = datetime.strptime(comment_data['creationTime'], 
                                         '%Y-%m-%d %H:%M:%S')
        
        # 执行插入
        cursor.execute(sql, (
            comment_data['product_id'],
            comment_data['content'],
            comment_data['nickname'],
            comment_data['score'],
            creation_time
        ))
        
        conn.commit()
        logger.info(f"评论已保存到数据库: {comment_data['nickname']} - ID: {cursor.lastrowid}")
        conn.close()
        
    except Exception as e:
        logger.error(f"保存评论到数据库失败: {e}")
        logger.error(traceback.format_exc())
        socketio.emit('error', {'message': f'保存评论失败: {str(e)}'})

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
def run_crawler(product_url, product_id, product_name):
    # 关闭测试模式，爬取真实评论
    always_test_mode = False
    
    async def run():
        try:
            logger.info(f"开始爬取商品: {product_id} - {product_name}")
            socketio.emit('progress', {'status': 'starting', 'product_id': product_id})
            
            # 初始化爬虫，使用测试模式
            scraper = await WebSocketJDScraper(product_id, product_name, headless=True, test_mode=always_test_mode).setup()
            
            # 开始爬取评论
            await scraper.load_comments(product_url)
            
            # 结束爬取
            await scraper.close()
            
            logger.info(f"商品 {product_id} 爬取完成，共获取 {len(scraper.captured_comments)} 条评论")
            socketio.emit('progress', {
                'status': 'completed', 
                'count': len(scraper.captured_comments),
                'product_id': product_id
            })
            
        except Exception as e:
            logger.error(f"爬虫执行错误: {e}")
            logger.error(traceback.format_exc())
            socketio.emit('error', {'message': f'爬虫执行错误: {str(e)}'})
    
    # 在事件循环中运行异步任务
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())

@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    try:
        data = request.json
        logger.info(f"收到爬取请求: {data}")
        
        product_url = data.get('url')
        product_id = data.get('product_id')
        product_name = data.get('product_name', '')
        
        if not product_url or not product_id:
            logger.warning("请求缺少必要参数")
            return jsonify({'success': False, 'message': '缺少商品URL或ID'}), 400
        
        # 检查数据库连接
        if not check_database_connection():
            return jsonify({'success': False, 'message': '数据库连接失败，请检查配置'}), 500
        
        # 在后台线程中执行爬虫
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
        
    logger.info("启动Flask-SocketIO服务，监听端口 5004")
    socketio.run(app, host='0.0.0.0', port=5004, debug=False, allow_unsafe_werkzeug=True) 