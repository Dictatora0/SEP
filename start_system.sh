#!/bin/bash

# 京东评论爬虫系统启动脚本
# 用于自动启动Python爬虫服务、Spring Boot后端和Vue前端

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
echo -e "${BLUE}项目根目录: $PROJECT_ROOT${NC}"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 日志文件
PYTHON_LOG="$LOG_DIR/python_crawler.log"
JAVA_LOG="$LOG_DIR/java_backend.log"
VUE_LOG="$LOG_DIR/vue_frontend.log"
ERROR_LOG="$LOG_DIR/error.log"

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}检查系统依赖...${NC}"
    
    # 检查Python
    if ! command -v python &> /dev/null; then
        echo -e "${RED}错误: 未找到Python命令${NC}" | tee -a "$ERROR_LOG"
        exit 1
    fi
    
    # 检查Java
    if ! command -v java &> /dev/null; then
        echo -e "${RED}错误: 未找到Java命令${NC}" | tee -a "$ERROR_LOG"
        exit 1
    fi
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}错误: 未找到Node.js命令${NC}" | tee -a "$ERROR_LOG"
        exit 1
    fi
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}错误: 未找到npm命令${NC}" | tee -a "$ERROR_LOG"
        exit 1
    fi

    # 检查MySQL是否正在运行
    if ! pgrep -x "mysqld" > /dev/null; then
        echo -e "${YELLOW}警告: MySQL似乎未运行，请确保数据库可用${NC}" | tee -a "$ERROR_LOG"
    fi
    
    echo -e "${GREEN}系统依赖检查完毕${NC}"
}

# 停止已有进程
stop_existing_processes() {
    echo -e "${BLUE}停止已有进程...${NC}"
    
    # 停止Python爬虫进程
    if pgrep -f "jd_service.py" > /dev/null; then
        echo "停止Python爬虫进程..."
        pkill -f "jd_service.py"
        sleep 2
    fi
    
    # 停止Java后端进程
    if pgrep -f "demo2-.*.jar" > /dev/null; then
        echo "停止Java后端进程..."
        pkill -f "demo2-.*.jar"
        sleep 2
    fi
    
    # 停止Vue前端进程
    if pgrep -f "vue-cli-service" > /dev/null; then
        echo "停止Vue前端进程..."
        pkill -f "vue-cli-service"
        sleep 2
    fi
    
    echo -e "${GREEN}已停止所有相关进程${NC}"
}

# 更新Python爬虫服务配置(解决端口冲突问题)
update_python_service_port() {
    echo -e "${BLUE}更新Python服务端口配置...${NC}"
    
    # 设置固定端口5004
    PYTHON_SERVICE_FILE="$PROJECT_ROOT/jd_service.py"
    
    if [ -f "$PYTHON_SERVICE_FILE" ]; then
        # 确保Python服务使用端口5004
        if grep -q "socketio.run(app, host='0.0.0.0', port=" "$PYTHON_SERVICE_FILE"; then
            sed -i.bak "s/socketio.run(app, host='0.0.0.0', port=[0-9]*/socketio.run(app, host='0.0.0.0', port=5004/g" "$PYTHON_SERVICE_FILE"
            echo -e "${GREEN}已设置Python服务端口为: 5004${NC}"
        else
            echo -e "${YELLOW}警告: 无法在Python服务文件中找到端口配置${NC}" | tee -a "$ERROR_LOG"
        fi
        
        # 更新vue1/src/components/CommentCrawler.vue文件
        COMMENT_CRAWLER_FILE="$PROJECT_ROOT/vue1/src/components/CommentCrawler.vue"
        if [ -f "$COMMENT_CRAWLER_FILE" ]; then
            if grep -q "this.socket = io('http://localhost:[0-9]*'" "$COMMENT_CRAWLER_FILE"; then
                sed -i.bak "s/this.socket = io('http:\/\/localhost:[0-9]*'/this.socket = io('http:\/\/localhost:5004'/g" "$COMMENT_CRAWLER_FILE"
                echo -e "${GREEN}已更新CommentCrawler.vue中的WebSocket连接端口为: 5004${NC}"
            fi
            
            if grep -q "this.\$http.post('http://localhost:[0-9]*/" "$COMMENT_CRAWLER_FILE"; then
                sed -i.bak "s/this.\$http.post('http:\/\/localhost:[0-9]*\//this.\$http.post('http:\/\/localhost:5004\//g" "$COMMENT_CRAWLER_FILE"
                echo -e "${GREEN}已更新CommentCrawler.vue中的API请求端口为: 5004${NC}"
            fi
        fi
        
        # 检查端口可用性
        if lsof -i :5004 &> /dev/null; then
            echo -e "${RED}警告: 端口5004已被占用，请关闭占用此端口的程序${NC}" | tee -a "$ERROR_LOG"
            return 1
        else
            echo -e "${GREEN}Python服务端口 5004 可用${NC}"
        fi
    else
        echo -e "${RED}错误: 无法找到Python服务文件${NC}" | tee -a "$ERROR_LOG"
        return 1
    fi
    
    return 0
}

# 启动Python爬虫服务
start_python_crawler() {
    echo -e "${BLUE}启动Python爬虫服务...${NC}"
    
    # 检查Python虚拟环境
    if [ -d "$PROJECT_ROOT/jd_env" ] && [ -f "$PROJECT_ROOT/jd_env/bin/activate" ]; then
        echo "激活Python虚拟环境..."
        # 使用source命令激活环境
        source "$PROJECT_ROOT/jd_env/bin/activate" || {
            echo -e "${YELLOW}警告: 无法激活虚拟环境，使用系统Python${NC}" | tee -a "$ERROR_LOG"
        }
    else
        echo -e "${YELLOW}警告: 未找到虚拟环境，使用系统Python${NC}" | tee -a "$ERROR_LOG"
    fi
    
    # 安装依赖
    echo "安装Python依赖..."
    pip install -r "$PROJECT_ROOT/requirements.txt" >> "$PYTHON_LOG" 2>&1
    
    # 启动Python爬虫服务
    echo "启动爬虫服务..."
    cd "$PROJECT_ROOT"
    
    # 确保停止任何现有的Python进程
    pkill -f "jd_service.py" 2>/dev/null
    sleep 2
    
    # 使用nohup启动后台进程并记录PID
    nohup python jd_service.py > "$PYTHON_LOG" 2>&1 &
    PYTHON_PID=$!
    
    # 将PID写入文件
    echo "$PYTHON_PID" > "$LOG_DIR/python.pid"
    
    # 检查服务是否成功启动
    sleep 5
    if ps -p $PYTHON_PID > /dev/null; then
        echo -e "${GREEN}Python爬虫服务成功启动，PID: $PYTHON_PID${NC}"
        # 检查端口
        sleep 2
        if lsof -i :5004 | grep LISTEN > /dev/null; then
            echo -e "${GREEN}Python服务端口 5004 正在监听${NC}"
        else
            echo -e "${YELLOW}警告: Python服务端口 5004 未在监听，可能启动失败${NC}" | tee -a "$ERROR_LOG"
            echo "检查日志: $PYTHON_LOG"
            return 1
        fi
    else
        echo -e "${RED}错误: Python爬虫服务启动失败${NC}" | tee -a "$ERROR_LOG"
        echo "查看日志: $PYTHON_LOG"
        return 1
    fi
    
    return 0
}

# 启动Vue前端服务
start_vue_frontend() {
    echo -e "${BLUE}启动Vue前端服务...${NC}"
    
    # 进入Vue项目目录
    cd "$PROJECT_ROOT/vue1" || {
        echo -e "${RED}错误: 无法进入Vue项目目录${NC}" | tee -a "$ERROR_LOG"
        return 1
    }
    
    # 确保node_modules/.bin中的文件有执行权限
    echo "设置执行权限..."
    chmod -R +x ./node_modules/.bin/
    
    # 安装Vue依赖
    echo "安装Vue依赖..."
    npm install --legacy-peer-deps >> "$VUE_LOG" 2>&1
    
    # 启动Vue开发服务器
    echo "启动Vue开发服务器..."
    
    # 确保停止任何现有的Vue进程
    pkill -f "vue-cli-service" 2>/dev/null
    sleep 2
    
    # 使用nohup启动并保存PID
    nohup npm run serve > "$VUE_LOG" 2>&1 &
    VUE_PID=$!
    
    # 将PID写入文件
    echo "$VUE_PID" > "$LOG_DIR/vue.pid"
    
    # 检查服务是否成功启动
    sleep 10
    if ps -p $VUE_PID > /dev/null; then
        echo -e "${GREEN}Vue前端服务成功启动，PID: $VUE_PID${NC}"
        # 检查端口
        sleep 2
        if lsof -i :9876 | grep LISTEN > /dev/null; then
            echo -e "${GREEN}Vue服务端口 9876 正在监听${NC}"
        else
            echo -e "${YELLOW}警告: Vue服务可能启动失败，端口9876未监听${NC}" | tee -a "$ERROR_LOG"
            echo "查看日志: $VUE_LOG"
            return 1
        fi
    else
        echo -e "${RED}错误: Vue前端服务启动失败${NC}" | tee -a "$ERROR_LOG"
        echo "查看日志: $VUE_LOG"
        return 1
    fi
    
    return 0
}

# 检查服务状态
check_system_status() {
    echo -e "${BLUE}检查系统状态...${NC}"
    
    # 检查Python服务
    if [ -f "$LOG_DIR/python.pid" ]; then
        PYTHON_PID=$(cat "$LOG_DIR/python.pid")
        if ps -p "$PYTHON_PID" > /dev/null; then
            echo -e "${GREEN}Python爬虫服务运行中 (PID: $PYTHON_PID)${NC}"
            
            # 检查端口
            if lsof -i :5004 | grep LISTEN > /dev/null; then
                echo -e "${GREEN}Python服务端口 5004 正在监听${NC}"
            else
                echo -e "${YELLOW}警告: Python服务端口 5004 未在监听${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${RED}错误: Python爬虫服务未运行${NC}" | tee -a "$ERROR_LOG"
        fi
    else
        echo -e "${RED}错误: 未找到Python PID文件${NC}" | tee -a "$ERROR_LOG"
    fi
    
    # 检查Vue服务
    if [ -f "$LOG_DIR/vue.pid" ]; then
        VUE_PID=$(cat "$LOG_DIR/vue.pid")
        if ps -p "$VUE_PID" > /dev/null; then
            echo -e "${GREEN}Vue前端服务运行中 (PID: $VUE_PID)${NC}"
            
            # 检查端口
            if lsof -i :9876 | grep LISTEN > /dev/null; then
                echo -e "${GREEN}Vue服务端口 9876 正在监听${NC}"
            else
                echo -e "${YELLOW}警告: Vue服务端口 9876 未在监听${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${RED}错误: Vue前端服务未运行${NC}" | tee -a "$ERROR_LOG"
        fi
    else
        echo -e "${RED}错误: 未找到Vue PID文件${NC}" | tee -a "$ERROR_LOG"
    fi
}

# 显示帮助信息
show_logs_help() {
    echo -e "${BLUE}系统日志位置:${NC}"
    echo "Python爬虫服务日志: $PYTHON_LOG"
    echo "Vue前端服务日志: $VUE_LOG"
    echo "错误日志: $ERROR_LOG"
    echo ""
    echo -e "${BLUE}使用以下命令查看实时日志:${NC}"
    echo "Python爬虫: tail -f $PYTHON_LOG"
    echo "Vue前端: tail -f $VUE_LOG"
    echo "错误日志: tail -f $ERROR_LOG"
}

# 主函数
main() {
    echo -e "\n${BLUE}===== 京东评论爬虫系统启动脚本 =====${NC}\n"
    
    # 检查依赖
    check_dependencies
    
    # 停止已有进程
    stop_existing_processes
    
    # 更新Python服务端口配置
    update_python_service_port || {
        echo -e "${RED}端口配置更新失败，请解决端口冲突问题后重试${NC}"
        exit 1
    }
    
    # 启动Python爬虫服务
    start_python_crawler || {
        echo -e "${RED}Python爬虫服务启动失败${NC}"
        exit 1
    }
    
    # 启动Vue前端服务
    start_vue_frontend || {
        echo -e "${RED}Vue前端服务启动失败${NC}"
        exit 1
    }
    
    echo -e "\n${GREEN}===== 所有服务已启动 =====${NC}\n"
    
    # 检查状态
    check_system_status
    
    # 显示日志帮助
    echo ""
    show_logs_help
    
    echo -e "\n${BLUE}系统已启动完成，请访问 http://localhost:9876 使用系统${NC}"
}

# 执行主函数
main 