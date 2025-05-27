# 京东评论爬虫系统

这是一个基于Spring Boot、Vue和Python的京东商品评论爬虫系统，包含以下组件：
- Python爬虫服务：负责爬取京东商品评论
- Spring Boot后端：处理业务逻辑和API请求
- Vue前端：提供用户界面

## 系统要求

- Java 8+
- Python 3.8+
- Node.js 14+
- MySQL 5.7+

## 快速开始

### 启动系统

使用以下命令启动整个系统（Python爬虫、Java后端和Vue前端）：

```bash
./start_system.sh
```

此脚本会：
- 检查必要的系统依赖
- 停止可能已经运行的相关进程
- 自动配置服务端口，避免冲突
- 启动Python爬虫服务
- 编译并启动Java后端服务
- 安装依赖并启动Vue前端服务
- 创建日志记录

### 停止系统

使用以下命令停止所有服务：

```bash
./stop_system.sh
```

此脚本会：
- 优雅地尝试停止所有相关进程
- 检查服务是否成功停止
- 提供强制停止选项（如果需要）

### 检查系统状态

使用以下命令检查系统状态：

```bash
./check_system.sh
```

您也可以指定特定的检查项：

```bash
./check_system.sh status logs   # 只检查状态和日志
```

可用的选项：
- `status`：显示系统运行状态
- `logs`：显示最近日志
- `resources`：显示资源使用情况
- `db`：检查数据库连接
- `ports`：检查端口使用情况
- `all`：执行所有检查
- `help`：显示帮助信息

## 日志文件

所有日志文件位于`logs/`目录下：
- Python爬虫：`logs/python_crawler.log`
- Java后端：`logs/java_backend.log`
- Vue前端：`logs/vue_frontend.log`
- 错误日志：`logs/error.log`

## 注意事项

1. 请确保MySQL服务已经启动且配置正确
2. 首次运行时可能需要较长时间安装依赖
3. 如果遇到端口冲突问题，脚本会自动尝试使用其他可用端口
4. 京东爬虫服务需要手动扫码登录京东账号 