#!/bin/bash

# 京东评论爬虫系统启动脚本（修复版）
# 用于自动启动Python爬虫服务和Vue前端

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
echo -e "${BLUE}项目根目录: $PROJECT_ROOT${NC}"

# 前端项目路径
VUE_DIR="$PROJECT_ROOT/CommentAnalysor_frontend/vue"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 日志文件
PYTHON_LOG="$LOG_DIR/python_crawler.log"
VUE_LOG="$LOG_DIR/vue_frontend.log"
JAVA_LOG="$LOG_DIR/java_backend.log"
ERROR_LOG="$LOG_DIR/error.log"

# 停止已有进程
stop_existing_processes() {
    echo -e "${BLUE}停止已有进程...${NC}"
    
    # 清空错误日志
    > "$ERROR_LOG"
    
    # 清空PID文件
    > "$LOG_DIR/python.pid"
    > "$LOG_DIR/java.pid"
    
    # 更彻底地检查和停止Python爬虫进程
    echo "检查并停止Python爬虫进程..."
    python_pids=$(pgrep -f "jd_service.py" 2>/dev/null)
    if [ -n "$python_pids" ]; then
        echo "发现Python爬虫进程: $python_pids"
        for pid in $python_pids; do
            echo "终止进程 $pid..."
            kill -9 $pid 2>/dev/null
        done
        echo "等待Python进程完全终止..."
        sleep 2
    else
        echo "未发现运行中的Python爬虫进程"
    fi
    
    # 更彻底地检查和停止Spring Boot后端进程
    echo "检查并停止Spring Boot后端进程..."
    java_pids=$(pgrep -f "demo2-0.0.1-SNAPSHOT.jar" 2>/dev/null)
    if [ -n "$java_pids" ]; then
        echo "发现Spring Boot进程: $java_pids"
        for pid in $java_pids; do
            echo "终止进程 $pid..."
            kill -9 $pid 2>/dev/null
        done
        echo "等待Java进程完全终止..."
        sleep 2
    else
        echo "未发现运行中的Spring Boot后端进程"
    fi
    
    # 更彻底地检查和停止Vue前端进程
    echo "检查并停止Vue前端进程..."
    vue_pids=$(pgrep -f "vue-cli-service\|npm run serve" 2>/dev/null)
    if [ -n "$vue_pids" ]; then
        echo "发现Vue前端进程: $vue_pids"
        for pid in $vue_pids; do
            echo "终止进程 $pid..."
            kill -9 $pid 2>/dev/null
        done
        echo "等待Vue进程完全终止..."
        sleep 2
    else
        echo "未发现运行中的Vue前端进程"
    fi
    
    # 检查端口占用情况
    echo "检查端口占用情况..."
    if lsof -i :8080 -t > /dev/null 2>&1; then
        echo "端口8080仍被占用，尝试释放..."
        lsof -i :8080 -t | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    if lsof -i :5004 -t > /dev/null 2>&1; then
        echo "端口5004仍被占用，尝试释放..."
        lsof -i :5004 -t | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    if lsof -i :8083 -t > /dev/null 2>&1; then
        echo "端口8083仍被占用，尝试释放..."
        lsof -i :8083 -t | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    if lsof -i :8084 -t > /dev/null 2>&1; then
        echo "端口8084仍被占用，尝试释放..."
        lsof -i :8084 -t | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    echo -e "${GREEN}已停止所有相关进程${NC}"
}

# 启动Python爬虫服务
start_python_crawler() {
    echo -e "${BLUE}启动Python爬虫服务...${NC}"
    
    # 检查Python虚拟环境
    if [ -d "$PROJECT_ROOT/jd_env" ] && [ -f "$PROJECT_ROOT/jd_env/bin/activate" ]; then
        echo "激活Python虚拟环境..."
        source "$PROJECT_ROOT/jd_env/bin/activate" || {
            echo -e "${YELLOW}警告: 无法激活虚拟环境，使用系统Python${NC}" | tee -a "$ERROR_LOG"
        }
    else
        echo -e "${YELLOW}警告: 未找到虚拟环境，使用系统Python${NC}" | tee -a "$ERROR_LOG"
    fi
    
    # 安装基本依赖
    echo "安装Python依赖..."
    pip install flask flask-socketio flask-cors playwright mysql-connector-python >> "$PYTHON_LOG" 2>&1
    
    # 安装playwright浏览器
    echo "安装Playwright浏览器..."
    python -m playwright install chromium >> "$PYTHON_LOG" 2>&1
    
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

# 启动Spring Boot后端
start_java_backend() {
    echo -e "${BLUE}启动Spring Boot后端...${NC}"
    
    # 检查JAR文件是否存在
    JAR_FILE="$PROJECT_ROOT/target/demo2-0.0.1-SNAPSHOT.jar"
    if [ ! -f "$JAR_FILE" ]; then
        echo -e "${RED}错误: Spring Boot JAR文件不存在: $JAR_FILE${NC}" | tee -a "$ERROR_LOG"
        return 1
    fi
    
    echo "启动Spring Boot应用..."
    cd "$PROJECT_ROOT"
    
    # 清空上一次的日志文件
    > "$JAVA_LOG"
    
    # 确保停止任何现有的Java进程
    pkill -f "demo2-0.0.1-SNAPSHOT.jar" 2>/dev/null
    sleep 2
    
    # 使用nohup启动后台进程并记录PID
    echo "使用以下命令启动: java -jar \"$JAR_FILE\""
    nohup java -jar "$JAR_FILE" > "$JAVA_LOG" 2>&1 &
    JAVA_PID=$!
    
    # 将PID写入文件
    echo "$JAVA_PID" > "$LOG_DIR/java.pid"
    
    # 检查服务是否成功启动
    echo "等待Spring Boot应用启动..."
    for i in {1..30}; do
        if ps -p $JAVA_PID > /dev/null; then
            # 检查日志是否包含启动成功信息
            if grep -q "Started Demo2Application" "$JAVA_LOG" 2>/dev/null; then
                echo -e "${GREEN}Spring Boot后端成功启动，PID: $JAVA_PID${NC}"
                # 检查端口
                if lsof -i :8080 | grep LISTEN > /dev/null; then
                    echo -e "${GREEN}后端服务端口 8080 正在监听${NC}"
                    return 0
                fi
            fi
        else
            echo -e "${RED}错误: Spring Boot进程已终止${NC}" | tee -a "$ERROR_LOG"
            break
        fi
        echo "等待中... ($i/30)"
        sleep 1
    done
    
    # 检查是否有启动错误
    if grep -q "APPLICATION FAILED TO START" "$JAVA_LOG"; then
        echo -e "${RED}错误: Spring Boot应用启动失败${NC}" | tee -a "$ERROR_LOG"
        echo "错误摘要:"
        grep -A 10 "APPLICATION FAILED TO START" "$JAVA_LOG" | head -n 15
        echo "完整日志: $JAVA_LOG"
    else
        echo -e "${YELLOW}警告: 启动超时或状态未知${NC}" | tee -a "$ERROR_LOG"
        echo "查看日志: $JAVA_LOG"
    fi
    
    return 1
}

# 启动Vue前端服务（直接终端启动，不在后台）
start_vue_frontend() {
    echo -e "${BLUE}启动Vue前端服务...${NC}"
    
    # 检查Vue项目目录是否存在
    if [ ! -d "$VUE_DIR" ]; then
        echo -e "${RED}错误: 前端目录不存在: $VUE_DIR${NC}" | tee -a "$ERROR_LOG"
        return 1
    fi
    
    # 进入Vue项目目录
    cd "$VUE_DIR" || {
        echo -e "${RED}错误: 无法进入Vue项目目录: $VUE_DIR${NC}" | tee -a "$ERROR_LOG"
        return 1
    }
    
    echo "当前工作目录: $(pwd)"
    
    # 安装Vue依赖
    echo "安装Vue依赖..."
    npm install --legacy-peer-deps
    
    # 提示用户手动启动Vue服务
    echo -e "${GREEN}依赖安装完成${NC}"
    echo -e "${BLUE}请在新的终端窗口中运行以下命令启动Vue前端服务:${NC}"
    echo -e "${YELLOW}cd $VUE_DIR && npm run serve${NC}"
    echo -e "${BLUE}启动后，请注意控制台输出的访问地址，通常是 http://localhost:8083${NC}"
    
    read -p "是否在当前终端中启动Vue服务? (y/n): " choice
    if [[ $choice == "y" || $choice == "Y" ]]; then
        echo "正在启动Vue服务..."
        npm run serve
    fi
}

# 主函数
main() {
    echo -e "\n${BLUE}===== 京东评论爬虫系统启动脚本 =====${NC}\n"
    
    # 停止已有进程
    stop_existing_processes
    
    # 启动Spring Boot后端
    start_java_backend || {
        echo -e "${RED}Spring Boot后端启动失败${NC}"
        echo "查看日志: $JAVA_LOG"
        read -p "是否继续启动其他服务? (y/n): " choice
        if [[ $choice != "y" && $choice != "Y" ]]; then
            exit 1
        fi
    }
    
    # 启动Python爬虫服务
    start_python_crawler || {
        echo -e "${RED}Python爬虫服务启动失败${NC}"
        echo "查看日志: $PYTHON_LOG"
        read -p "是否继续启动前端服务? (y/n): " choice
        if [[ $choice != "y" && $choice != "Y" ]]; then
            exit 1
        fi
    }
    
    # 启动Vue前端服务
    start_vue_frontend
    
    echo -e "\n${BLUE}系统启动流程已完成${NC}"
    echo -e "${BLUE}==================================${NC}"
    echo -e "后端API服务: ${GREEN}http://localhost:8080${NC}"
    echo -e "Python爬虫服务: ${GREEN}http://localhost:5004${NC}"
    echo -e "Vue前端服务: ${GREEN}http://localhost:8083${NC} 或 ${GREEN}http://localhost:8084${NC}"
    echo -e "${BLUE}==================================${NC}"
}

# 执行主函数
main 