#!/bin/bash

# 系统功能测试脚本
# 用于测试系统各组件是否正常工作

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

echo -e "${BLUE}===== 京东评论分析系统测试脚本 =====${NC}"

# 1. 测试数据库连接
echo -e "\n${BLUE}1. 测试数据库连接${NC}"
if mysql -u root -p12345678 -e "USE SEP; SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}数据库连接成功${NC}"
else
    echo -e "${RED}数据库连接失败${NC}"
    exit 1
fi

# 2. 测试后端API
echo -e "\n${BLUE}2. 测试后端API${NC}"
USER_LOGIN=$(curl -s -X POST -H "Content-Type: application/json" -d '{"username":"testuser","password":"123456"}' http://localhost:8080/user/login)
if [[ $USER_LOGIN == *"\"code\":\"0\""* ]]; then
    echo -e "${GREEN}用户登录API正常${NC}"
else
    echo -e "${RED}用户登录API异常: $USER_LOGIN${NC}"
fi

# 3. 测试爬虫服务
echo -e "\n${BLUE}3. 测试爬虫服务${NC}"
CRAWLER_STATUS=$(curl -s -X GET http://localhost:5004/api/status)
if [[ $CRAWLER_STATUS == *"服务正常运行"* ]]; then
    echo -e "${GREEN}爬虫服务正常运行${NC}"
else
    echo -e "${RED}爬虫服务异常: $CRAWLER_STATUS${NC}"
fi

# 4. 测试爬虫功能
echo -e "\n${BLUE}4. 测试爬虫功能${NC}"
CRAWLER_RESULT=$(curl -s -X POST -H "Content-Type: application/json" -d '{"url":"https://item.jd.com/100006584130.html", "product_id":"100006584130", "product_name":"iPhone 13"}' http://localhost:5004/api/crawl)
if [[ $CRAWLER_RESULT == *"\"success\":true"* ]]; then
    echo -e "${GREEN}爬虫功能正常${NC}"
else
    echo -e "${RED}爬虫功能异常: $CRAWLER_RESULT${NC}"
fi

# 5. 检查评论数据
echo -e "\n${BLUE}5. 检查评论数据${NC}"
COMMENT_COUNT=$(mysql -u root -p12345678 -se "USE SEP; SELECT COUNT(*) FROM comment_100006584130;")
echo -e "${GREEN}已爬取评论数: $COMMENT_COUNT${NC}"

echo -e "\n${BLUE}===== 测试完成 =====${NC}" 