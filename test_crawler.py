import requests
import socketio
import time
import sys
from datetime import datetime

# 连接到Socket.IO服务器
sio = socketio.Client()
received_comments = []
progress_updates = 0

@sio.event
def connect():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 已连接到爬虫服务器")

@sio.event
def disconnect():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 与服务器连接断开")

@sio.on('progress')
def on_progress(data):
    global progress_updates
    progress_updates += 1
    status = data.get('status', 'unknown')
    count = data.get('count', 0)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 进度更新: 状态={status}, 评论数={count}")
    
    if status == 'completed':
        print(f"\n爬取完成，共获取 {count} 条评论")
        print(f"总共收到 {progress_updates} 次进度更新和 {len(received_comments)} 条评论")
        print(f"总耗时: {time.time() - start_time:.2f} 秒")
        sio.disconnect()

@sio.on('new_comment')
def on_new_comment(comment):
    received_comments.append(comment)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 新评论: {comment.get('nickname', '匿名')} - {comment.get('content', '')[:30]}...")

@sio.on('error')
def on_error(error):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {error.get('message', '未知错误')}")

def main():
    server_url = 'http://localhost:5004'
    product_url = 'https://item.jd.com/100019125512.html'
    product_id = '100019125512'
    
    if len(sys.argv) > 1:
        product_url = sys.argv[1]
        product_id = sys.argv[2] if len(sys.argv) > 2 else product_url.split('/')[-1].replace('.html', '')
    
    try:
        # 连接WebSocket
        print(f"连接到爬虫服务器: {server_url}")
        sio.connect(server_url)
        
        # 发送爬取请求
        print(f"发送爬取请求: 商品ID={product_id}, URL={product_url}")
        response = requests.post(f"{server_url}/api/crawl", 
                               json={
                                   "url": product_url,
                                   "product_id": product_id,
                                   "product_name": "测试商品"
                               })
        
        print(f"请求响应: {response.status_code} - {response.text}")
        
        # 等待爬取完成
        print("等待爬取完成...(按Ctrl+C中断)")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n用户中断，正在断开连接...")
        sio.disconnect()
    except Exception as e:
        print(f"发生错误: {e}")
        try:
            sio.disconnect()
        except:
            pass

if __name__ == "__main__":
    global start_time
    start_time = time.time()
    main() 