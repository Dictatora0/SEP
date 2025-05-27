#!/bin/bash

# 京东评论爬虫系统状态检查脚本
# 用于检查Python爬虫服务、Spring Boot后端和Vue前端的运行状态和日志

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

# 日志文件
PYTHON_LOG="$LOG_DIR/python_crawler.log"
JAVA_LOG="$LOG_DIR/java_backend.log"
VUE_LOG="$LOG_DIR/vue_frontend.log"
ERROR_LOG="$LOG_DIR/error.log"

# 检查服务状态
check_system_status() {
    echo -e "${BLUE}===== 系统运行状态 =====${NC}"
    
    # 检查Python爬虫服务
    echo -e "\n${BLUE}Python爬虫服务状态:${NC}"
    PYTHON_PIDS=$(pgrep -f "jd_service.py")
    if [ ! -z "$PYTHON_PIDS" ]; then
        echo -e "${GREEN}运行中 - PID: $PYTHON_PIDS${NC}"
        
        # 检查端口
        for PORT in 5000 5001 5002 5003; do
            if lsof -i ":$PORT" | grep LISTEN > /dev/null; then
                echo -e "${GREEN}监听端口: $PORT${NC}"
                # 提取Python服务URL配置
                APP_PROP_FILE="$PROJECT_ROOT/src/main/resources/application.properties"
                if [ -f "$APP_PROP_FILE" ]; then
                    PYTHON_URL=$(grep "python.crawler.url" "$APP_PROP_FILE" | cut -d'=' -f2)
                    echo -e "${BLUE}配置URL: $PYTHON_URL${NC}"
                fi
                break
            fi
        done
    else
        echo -e "${RED}未运行${NC}"
    fi
    
    # 检查Java后端服务
    echo -e "\n${BLUE}Java后端服务状态:${NC}"
    JAVA_PIDS=$(pgrep -f "demo2-.*.jar")
    if [ ! -z "$JAVA_PIDS" ]; then
        echo -e "${GREEN}运行中 - PID: $JAVA_PIDS${NC}"
        
        # 检查端口
        if lsof -i ":8080" | grep LISTEN > /dev/null; then
            echo -e "${GREEN}监听端口: 8080${NC}"
        else
            echo -e "${YELLOW}警告: 进程存在但端口未监听${NC}"
        fi
    else
        echo -e "${RED}未运行${NC}"
    fi
    
    # 检查Vue前端服务
    echo -e "\n${BLUE}Vue前端服务状态:${NC}"
    VUE_PIDS=$(pgrep -f "vue-cli-service")
    if [ ! -z "$VUE_PIDS" ]; then
        echo -e "${GREEN}运行中 - PID: $VUE_PIDS${NC}"
        
        # 检查Vue服务端口
        for PORT in 8081 8082 8083; do
            if lsof -i ":$PORT" | grep LISTEN > /dev/null; then
                echo -e "${GREEN}监听端口: $PORT${NC}"
                echo -e "${BLUE}访问URL: http://localhost:$PORT${NC}"
                break
            fi
        done
    else
        echo -e "${RED}未运行${NC}"
    fi
}

# 查看最近日志
show_recent_logs() {
    echo -e "\n${BLUE}===== 最近日志 =====${NC}"
    
    # 检查Python爬虫日志
    echo -e "\n${BLUE}Python爬虫最近日志:${NC}"
    if [ -f "$PYTHON_LOG" ]; then
        echo -e "${YELLOW}最新20行:${NC}"
        tail -20 "$PYTHON_LOG"
    else
        echo -e "${RED}日志文件不存在${NC}"
    fi
    
    # 检查Java后端日志
    echo -e "\n${BLUE}Java后端最近日志:${NC}"
    if [ -f "$JAVA_LOG" ]; then
        echo -e "${YELLOW}最新20行:${NC}"
        tail -20 "$JAVA_LOG"
    else
        echo -e "${RED}日志文件不存在${NC}"
    fi
    
    # 检查Vue前端日志
    echo -e "\n${BLUE}Vue前端最近日志:${NC}"
    if [ -f "$VUE_LOG" ]; then
        echo -e "${YELLOW}最新20行:${NC}"
        tail -20 "$VUE_LOG"
    else
        echo -e "${RED}日志文件不存在${NC}"
    fi
    
    # 检查错误日志
    if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
        echo -e "\n${RED}错误日志:${NC}"
        cat "$ERROR_LOG"
    fi
}

# 资源使用情况
check_resource_usage() {
    echo -e "\n${BLUE}===== 系统资源使用情况 =====${NC}"
    
    echo -e "\n${BLUE}CPU和内存使用:${NC}"
    echo -e "${YELLOW}总体状况:${NC}"
    top -l 1 | head -10
    
    echo -e "\n${YELLOW}Python爬虫进程资源使用:${NC}"
    ps -eo pid,%cpu,%mem,command | grep "[j]d_service.py" || echo "无Python爬虫进程"
    
    echo -e "\n${YELLOW}Java后端进程资源使用:${NC}"
    ps -eo pid,%cpu,%mem,command | grep "[d]emo2-.*.jar" || echo "无Java后端进程"
    
    echo -e "\n${YELLOW}Vue前端进程资源使用:${NC}"
    ps -eo pid,%cpu,%mem,command | grep "[v]ue-cli-service" || echo "无Vue前端进程"
    
    echo -e "\n${BLUE}磁盘使用:${NC}"
    df -h | grep -E "^Filesystem|/$"
}

# 检查数据库连接
check_database() {
    echo -e "\n${BLUE}===== 数据库连接检查 =====${NC}"
    
    # 检查MySQL进程
    if pgrep -x "mysqld" > /dev/null; then
        echo -e "${GREEN}MySQL服务运行中${NC}"
        
        # 检查数据库可连接性
        if command -v mysql > /dev/null; then
            echo "尝试连接数据库..."
            if mysql -u root -p12345678 -e "SELECT 1" SEP &> /dev/null; then
                echo -e "${GREEN}数据库连接正常${NC}"
                
                # 检查评论表
                if mysql -u root -p12345678 -e "SHOW TABLES LIKE 'comment'" SEP 2>/dev/null | grep -q "comment"; then
                    echo -e "${GREEN}评论表存在${NC}"
                    
                    # 显示评论记录数
                    COUNT=$(mysql -u root -p12345678 -e "SELECT COUNT(*) FROM comment" SEP 2>/dev/null | tail -1)
                    echo -e "${BLUE}评论表记录数: $COUNT${NC}"
                else
                    echo -e "${RED}评论表不存在${NC}"
                fi
            else
                echo -e "${RED}无法连接到数据库${NC}"
            fi
        else
            echo -e "${YELLOW}未安装MySQL客户端，无法检查连接${NC}"
        fi
    else
        echo -e "${RED}MySQL服务未运行${NC}"
    fi
}

# 检查端口冲突
check_port_conflicts() {
    echo -e "\n${BLUE}===== 端口使用情况 =====${NC}"
    
    echo -e "${YELLOW}检查关键端口使用情况:${NC}"
    for PORT in 5000 5001 5002 5003 8080 8081 8082; do
        RESULT=$(lsof -i ":$PORT" 2>/dev/null)
        if [ ! -z "$RESULT" ]; then
            echo -e "${BLUE}端口 $PORT:${NC}"
            echo "$RESULT"
        else
            echo -e "${GREEN}端口 $PORT: 未被使用${NC}"
        fi
    done
}

# 显示帮助信息
show_help() {
    echo "使用: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  status    - 显示系统运行状态"
    echo "  logs      - 显示最近日志"
    echo "  resources - 显示资源使用情况"
    echo "  db        - 检查数据库连接"
    echo "  ports     - 检查端口使用情况"
    echo "  all       - 执行所有检查"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "示例: $0 status logs"
}

# 主函数
main() {
    # 如果没有参数，执行所有检查
    if [ $# -eq 0 ]; then
        check_system_status
        show_recent_logs
        check_resource_usage
        check_database
        check_port_conflicts
    else
        # 处理命令行参数
        for arg in "$@"; do
            case $arg in
                status)
                    check_system_status
                    ;;
                logs)
                    show_recent_logs
                    ;;
                resources)
                    check_resource_usage
                    ;;
                db)
                    check_database
                    ;;
                ports)
                    check_port_conflicts
                    ;;
                all)
                    check_system_status
                    show_recent_logs
                    check_resource_usage
                    check_database
                    check_port_conflicts
                    ;;
                help)
                    show_help
                    exit 0
                    ;;
                *)
                    echo -e "${RED}未知选项: $arg${NC}"
                    show_help
                    exit 1
                    ;;
            esac
        done
    fi
}

# 执行主函数
main "$@" 