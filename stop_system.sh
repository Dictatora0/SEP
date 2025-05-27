#!/bin/bash

# 京东评论爬虫系统停止脚本
# 用于停止Python爬虫服务、Spring Boot后端和Vue前端

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 日志文件
ERROR_LOG="$LOG_DIR/error.log"

# 停止Python爬虫服务
stop_python_crawler() {
    echo -e "${BLUE}停止Python爬虫服务...${NC}"
    
    PYTHON_PID_FILE="$LOG_DIR/python.pid"
    if [ -f "$PYTHON_PID_FILE" ]; then
        PYTHON_PID=$(cat "$PYTHON_PID_FILE")
        if ps -p $PYTHON_PID > /dev/null; then
            echo "停止PID为 $PYTHON_PID 的Python爬虫进程..."
            kill $PYTHON_PID
            sleep 2
            
            # 确认进程已停止
            if ps -p $PYTHON_PID > /dev/null; then
                echo -e "${YELLOW}进程未响应，尝试强制终止...${NC}"
                kill -9 $PYTHON_PID
                sleep 1
            fi
            
            if ! ps -p $PYTHON_PID > /dev/null; then
                echo -e "${GREEN}Python爬虫服务已停止${NC}"
                rm -f "$PYTHON_PID_FILE"
            else
                echo -e "${RED}无法停止Python爬虫服务${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${YELLOW}Python爬虫服务(PID: $PYTHON_PID)已经不在运行${NC}"
            rm -f "$PYTHON_PID_FILE"
        fi
    else
        # 尝试查找并杀死所有jd_service.py进程
        PIDS=$(pgrep -f "jd_service.py")
        if [ ! -z "$PIDS" ]; then
            echo "发现Python爬虫进程，正在停止..."
            pkill -f "jd_service.py"
            sleep 2
            
            if pgrep -f "jd_service.py" > /dev/null; then
                echo -e "${YELLOW}进程未响应，尝试强制终止...${NC}"
                pkill -9 -f "jd_service.py"
                sleep 1
            fi
            
            if ! pgrep -f "jd_service.py" > /dev/null; then
                echo -e "${GREEN}所有Python爬虫进程已停止${NC}"
            else
                echo -e "${RED}无法停止部分Python爬虫进程${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${YELLOW}未找到正在运行的Python爬虫进程${NC}"
        fi
    fi
}

# 停止Java后端服务
stop_java_backend() {
    echo -e "${BLUE}停止Java后端服务...${NC}"
    
    JAVA_PID_FILE="$LOG_DIR/java.pid"
    if [ -f "$JAVA_PID_FILE" ]; then
        JAVA_PID=$(cat "$JAVA_PID_FILE")
        if ps -p $JAVA_PID > /dev/null; then
            echo "停止PID为 $JAVA_PID 的Java后端进程..."
            kill $JAVA_PID
            sleep 2
            
            # 确认进程已停止
            if ps -p $JAVA_PID > /dev/null; then
                echo -e "${YELLOW}进程未响应，尝试强制终止...${NC}"
                kill -9 $JAVA_PID
                sleep 1
            fi
            
            if ! ps -p $JAVA_PID > /dev/null; then
                echo -e "${GREEN}Java后端服务已停止${NC}"
                rm -f "$JAVA_PID_FILE"
            else
                echo -e "${RED}无法停止Java后端服务${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${YELLOW}Java后端服务(PID: $JAVA_PID)已经不在运行${NC}"
            rm -f "$JAVA_PID_FILE"
        fi
    else
        # 尝试查找并杀死所有Java进程
        PIDS=$(pgrep -f "demo2-.*.jar")
        if [ ! -z "$PIDS" ]; then
            echo "发现Java后端进程，正在停止..."
            pkill -f "demo2-.*.jar"
            sleep 2
            
            if pgrep -f "demo2-.*.jar" > /dev/null; then
                echo -e "${YELLOW}进程未响应，尝试强制终止...${NC}"
                pkill -9 -f "demo2-.*.jar"
                sleep 1
            fi
            
            if ! pgrep -f "demo2-.*.jar" > /dev/null; then
                echo -e "${GREEN}所有Java后端进程已停止${NC}"
            else
                echo -e "${RED}无法停止部分Java后端进程${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${YELLOW}未找到正在运行的Java后端进程${NC}"
        fi
    fi
}

# 停止Vue前端服务
stop_vue_frontend() {
    echo -e "${BLUE}停止Vue前端服务...${NC}"
    
    VUE_PID_FILE="$LOG_DIR/vue.pid"
    if [ -f "$VUE_PID_FILE" ]; then
        VUE_PID=$(cat "$VUE_PID_FILE")
        if ps -p $VUE_PID > /dev/null; then
            echo "停止PID为 $VUE_PID 的Vue前端进程..."
            kill $VUE_PID
            sleep 2
            
            # 确认进程已停止
            if ps -p $VUE_PID > /dev/null; then
                echo -e "${YELLOW}进程未响应，尝试强制终止...${NC}"
                kill -9 $VUE_PID
                sleep 1
            fi
            
            if ! ps -p $VUE_PID > /dev/null; then
                echo -e "${GREEN}Vue前端服务已停止${NC}"
                rm -f "$VUE_PID_FILE"
            else
                echo -e "${RED}无法停止Vue前端服务${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${YELLOW}Vue前端服务(PID: $VUE_PID)已经不在运行${NC}"
            rm -f "$VUE_PID_FILE"
        fi
    else
        # 尝试查找并杀死所有Vue-CLI进程
        PIDS=$(pgrep -f "vue-cli-service")
        if [ ! -z "$PIDS" ]; then
            echo "发现Vue前端进程，正在停止..."
            pkill -f "vue-cli-service"
            sleep 2
            
            if pgrep -f "vue-cli-service" > /dev/null; then
                echo -e "${YELLOW}进程未响应，尝试强制终止...${NC}"
                pkill -9 -f "vue-cli-service"
                sleep 1
            fi
            
            if ! pgrep -f "vue-cli-service" > /dev/null; then
                echo -e "${GREEN}所有Vue前端进程已停止${NC}"
            else
                echo -e "${RED}无法停止部分Vue前端进程${NC}" | tee -a "$ERROR_LOG"
            fi
        else
            echo -e "${YELLOW}未找到正在运行的Vue前端进程${NC}"
        fi
    fi
}

# 检查服务状态
check_stopped_status() {
    echo -e "\n${BLUE}检查服务停止状态...${NC}"
    
    # 检查Python服务
    if pgrep -f "jd_service.py" > /dev/null; then
        echo -e "${RED}警告: 仍有Python爬虫进程在运行${NC}" | tee -a "$ERROR_LOG"
    else
        echo -e "${GREEN}Python爬虫服务已完全停止${NC}"
    fi
    
    # 检查Java服务
    if pgrep -f "demo2-.*.jar" > /dev/null; then
        echo -e "${RED}警告: 仍有Java后端进程在运行${NC}" | tee -a "$ERROR_LOG"
    else
        echo -e "${GREEN}Java后端服务已完全停止${NC}"
    fi
    
    # 检查Vue服务
    if pgrep -f "vue-cli-service" > /dev/null; then
        echo -e "${RED}警告: 仍有Vue前端进程在运行${NC}" | tee -a "$ERROR_LOG"
    else
        echo -e "${GREEN}Vue前端服务已完全停止${NC}"
    fi
    
    # 检查端口
    if lsof -i ":5000" &> /dev/null || lsof -i ":5001" &> /dev/null || lsof -i ":5002" &> /dev/null || lsof -i ":5003" &> /dev/null; then
        echo -e "${YELLOW}警告: 有进程仍在监听Python服务端口${NC}" | tee -a "$ERROR_LOG"
    fi
    
    if lsof -i ":8080" &> /dev/null; then
        echo -e "${YELLOW}警告: 有进程仍在监听Java服务端口${NC}" | tee -a "$ERROR_LOG"
    fi
}

# 主函数
main() {
    echo -e "\n${BLUE}===== 京东评论爬虫系统停止脚本 =====${NC}\n"
    
    # 停止Python爬虫服务
    stop_python_crawler
    
    # 停止Java后端服务
    stop_java_backend
    
    # 停止Vue前端服务
    stop_vue_frontend
    
    # 检查服务状态
    check_stopped_status
    
    echo -e "\n${GREEN}===== 所有服务已尝试停止 =====${NC}"
    
    # 如果还有服务未能正常停止，提供强制关闭选项
    if pgrep -f "jd_service.py|demo2-.*.jar|vue-cli-service" > /dev/null; then
        echo -e "\n${YELLOW}有服务未能正常停止，如需强制关闭所有相关进程，可执行:${NC}"
        echo "pkill -9 -f \"jd_service.py|demo2-.*.jar|vue-cli-service\""
    fi
}

# 执行主函数
main 