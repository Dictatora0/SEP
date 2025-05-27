# 京东评论爬虫集成指南

本项目实现了将Python爬虫程序集成到JavaWeb前后端系统中，支持实时反馈爬取进度和评论内容。

## 系统架构

系统由以下几部分组成：

1. **Python爬虫服务**：基于Flask和SocketIO，封装了原有的jd.py爬虫
2. **Java后端**：Spring Boot应用，提供API接口和WebSocket支持
3. **Vue前端**：展示爬取进度和实时评论数据

## 部署步骤

### 1. Python爬虫服务部署

```bash
# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install

# 启动服务
python jd_service.py
```

服务将在 http://localhost:5000 上运行。

### 2. Java后端配置

确保在 `application.properties` 中已配置：

```properties
# Python爬虫服务配置
python.crawler.url=http://localhost:5000
```

并添加了必要的依赖：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-websocket</artifactId>
</dependency>
```

### 3. 前端部署

```bash
# 进入前端目录
cd vue1

# 安装依赖
npm install

# 启动开发服务器
npm run serve
```

## 使用说明

1. 访问前端页面，导航到"评论爬取"页面
2. 输入京东商品URL（例如：https://item.jd.com/100016034372.html）
3. 点击"开始爬取"按钮
4. 实时查看爬取进度和最新评论

## 数据库结构

系统使用以下表存储数据：

1. **product表**：存储商品信息
   - id: 商品ID
   - name: 商品名称
   - url: 商品URL
   - create_time: 创建时间
   - update_time: 更新时间

2. **comment表**：存储评论信息
   - id: 评论ID
   - product_id: 商品ID
   - content: 评论内容
   - nickname: 用户昵称
   - score: 评分(1-5)
   - create_time: 评论时间
   - sentiment_score: 情感评分
   - sentiment_label: 情感标签

## 技术细节

1. **实时通信**：使用WebSocket协议实现前后端实时通信
2. **数据存储**：爬取的评论实时存入MySQL数据库
3. **异步处理**：爬虫任务在后台异步执行，不阻塞主线程

## 常见问题

1. **爬虫服务无法连接**：检查Python服务是否正常运行，以及application.properties中的URL配置是否正确
2. **WebSocket连接失败**：检查前端SockJS配置和后端WebSocket配置
3. **数据库连接问题**：检查数据库配置和表结构

## 扩展功能

1. 增加爬虫任务管理功能
2. 添加评论数据分析和可视化功能
3. 支持多种电商平台的评论爬取 