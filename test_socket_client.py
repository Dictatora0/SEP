#!/usr/bin/env python3
import socketio
import time
import sys
import requests

# 创建SocketIO客户端
sio = socketio.Client()

# 记录时间戳
start_time = time.time()

# 事件计数器
events = {
    'progress': 0,
    'new_comment': 0,
    'error': 0
}

# 爬取是否完成标志
crawling_completed = False

# 连接处理函数
@sio.event
def connect():
    print(f"已连接到爬虫服务器，等待数据推送...")

# 断开连接处理函数
@sio.event
def disconnect():
    print(f"已断开连接")

# 进度事件处理函数
@sio.on('progress')
def on_progress(data):
    global crawling_completed
    events['progress'] += 1
    print(f"收到进度更新: 状态={data.get('status')}, 评论数量={data.get('count')}, 商品ID={data.get('product_id')}")
    if data.get('status') == 'completed':
        crawling_completed = True
        print(f"\n爬取完成！总共爬取了 {data.get('count')} 条评论")
        print(f"总运行时间: {time.time() - start_time:.2f} 秒")
        print(f"收到事件总数: progress={events['progress']}, new_comment={events['new_comment']}, error={events['error']}")

# 新评论事件处理函数
@sio.on('new_comment')
def on_new_comment(data):
    events['new_comment'] += 1
    print(f"收到新评论: {data.get('nickname')} - {data.get('content')[:30]}...")

# 错误事件处理函数
@sio.on('error')
def on_error(data):
    events['error'] += 1
    print(f"错误: {data.get('message')}")

if __name__ == '__main__':
    # 设置服务器URL
    server_url = "http://localhost:5004"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
        
    print(f"连接到爬虫服务器: {server_url}")
    
    try:
        # 连接到服务器
        sio.connect(server_url)
        
        # 发送测试爬取请求
        print(f"发送爬取请求...")
        response = requests.post(
            f"{server_url}/api/crawl",
            json={
                "url": "https://item.jd.com/100019125512.html", 
                "product_id": "100019125512", 
                "product_name": "华为手机测试"
            }
        )
        print(f"爬取请求响应: {response.json()}")
        
        # 等待爬取完成
        max_wait_time = 60  # 最多等待60秒
        wait_start = time.time()
        print(f"等待爬取完成，最多等待 {max_wait_time} 秒...")
        
        while not crawling_completed:
            time.sleep(1)
            elapsed = time.time() - wait_start
            if elapsed > max_wait_time:
                print("等待超时，未收到爬取完成信号")
                break
            # 每10秒打印一次等待状态
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                print(f"已等待 {int(elapsed)} 秒，已收到 {events['new_comment']} 条评论...")
        
        # 等待3秒，确保所有数据都已接收
        time.sleep(3)
        sio.disconnect()
        
    except Exception as e:
        print(f"发生错误: {e}")
        if hasattr(sio, 'connected') and sio.connected:
            sio.disconnect()