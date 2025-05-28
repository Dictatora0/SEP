# 京东商品评论分析系统

本系统用于爬取京东商品评论并进行分析，包括评论分类、摘要和对比功能。

## 系统架构

系统采用前后端分离架构：
- 前端：Vue.js (Element UI)
- 后端：Spring Boot + Python Flask
- 数据库：MySQL

### 主要模块

1. **Java后端**：提供API接口，调用Python爬虫服务
2. **Python爬虫服务**：基于Flask + Socket.IO，实时爬取京东商品评论
3. **Vue前端**：用户界面，显示爬取进度和评论内容

## 数据库结构

- **product表**：存储商品信息
  - id：商品ID
  - name：商品名称
  - created_time：创建时间
  - updated_time：更新时间

- **comment_[product_id]表**：每个商品有独立的评论表
  - id：评论ID
  - content：评论内容
  - nickname：用户昵称
  - score：评分
  - create_time：评论时间
  - category：评论分类

## 启动指南

### 1. 启动Python爬虫服务

```bash
# 安装依赖
pip install flask flask-socketio flask-cors playwright mysql-connector-python

# 初始化Playwright
playwright install chromium

# 启动服务
python jd_service.py
```

服务将在 http://localhost:5004 运行

### 2. 启动Java后端

```bash
# 使用Maven构建项目
mvn clean package

# 运行Spring Boot应用
java -jar target/comment-analysor.jar
```

### 3. 启动前端开发服务器

```bash
cd CommentAnalysor_frontend/vue

# 安装依赖
npm install

# 启动开发服务器
npm run serve
```

## 使用流程

1. 访问系统首页，登录账号
2. 点击导航栏的"评论爬取"
3. 输入京东商品链接，点击"开始爬取"
4. 系统会实时显示爬取进度和评论内容
5. 爬取完成后，可以在评论分析页面查看分析结果

## 数据流向

1. 用户在前端提交商品URL
2. 前端发送请求到Java后端 `/api/crawler/start`
3. Java后端调用Python爬虫服务 `/api/crawl`
4. Python爬虫启动爬取过程
5. 爬虫实时通过WebSocket推送评论和进度到前端
6. 爬虫同时将评论保存到MySQL数据库

## 技术实现要点

1. **实时数据推送**：使用Socket.IO实现爬虫进度和评论的实时推送
2. **动态表创建**：根据商品ID动态创建评论表
3. **异步爬虫**：后台异步运行爬虫，不阻塞API响应
4. **无状态设计**：前端可以随时连接WebSocket获取最新状态

## 常见问题排查

1. **WebSocket连接失败**：检查防火墙设置和网络连接
2. **数据库连接错误**：检查MySQL配置和权限
3. **爬虫运行失败**：查看Python服务日志，可能是浏览器驱动问题 