package com.example.demo.controller;

import com.example.demo.common.Result;
import com.example.demo.entity.Product;
import com.example.demo.mapper.ProductMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@RestController
@RequestMapping("/crawler")
public class CrawlerController {

    private static final Logger logger = LoggerFactory.getLogger(CrawlerController.class);

    @Resource
    private ProductMapper productMapper;
    
    @Resource
    private RestTemplate restTemplate;
    
    @Value("${python.crawler.url}")
    private String pythonCrawlerUrl;
    
    @Resource
    private SimpMessagingTemplate messagingTemplate;

    /**
     * 启动爬虫任务
     */
    @PostMapping("/start")
    public Result<?> startCrawler(@RequestBody Map<String, String> params) {
        try {
            String productUrl = params.get("url");
            if (productUrl == null || !productUrl.contains("jd.com")) {
                return Result.error("400", "请提供有效的京东商品URL");
            }
            
            // 从URL中提取商品ID
            String productId = extractProductId(productUrl);
            if (productId == null) {
                return Result.error("400", "无法从URL中提取商品ID");
            }
            
            // 检查商品是否已在数据库中
            Product product = productMapper.selectById(productId);
            String productName = "";
            
            if (product == null) {
                // 新商品，添加到数据库
                product = new Product();
                product.setId(productId);
                product.setUrl(productUrl);
                product.setName(params.getOrDefault("name", "未命名商品"));
                product.setCreateTime(LocalDateTime.now());
                product.setUpdateTime(LocalDateTime.now());
                productMapper.insert(product);
                logger.info("新增商品: {}", productId);
            } else {
                // 更新已有商品
                productName = product.getName();
                product.setUpdateTime(LocalDateTime.now());
                productMapper.updateById(product);
                logger.info("更新商品: {}", productId);
            }
            
            // 调用Python爬虫服务
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("url", productUrl);
            requestBody.put("product_id", productId);
            requestBody.put("product_name", productName);
            
            logger.info("调用Python爬虫服务: {}, 参数: {}", pythonCrawlerUrl, requestBody);
            
            ResponseEntity<Map> response = restTemplate.postForEntity(
                pythonCrawlerUrl + "/api/crawl", 
                requestBody, 
                Map.class
            );
            
            if (response.getStatusCode().is2xxSuccessful() && 
                Boolean.TRUE.equals(response.getBody().get("success"))) {
                return Result.success("爬虫任务已启动");
            } else {
                logger.error("启动爬虫失败: {}", response.getBody());
                return Result.error("500", "启动爬虫失败: " + response.getBody().get("message"));
            }
            
        } catch (Exception e) {
            logger.error("启动爬虫任务异常", e);
            return Result.error("500", "启动爬虫任务失败: " + e.getMessage());
        }
    }
    
    /**
     * 从URL中提取商品ID
     */
    private String extractProductId(String url) {
        Pattern pattern = Pattern.compile("/([0-9]+)\\.html");
        Matcher matcher = pattern.matcher(url);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return null;
    }
    
    /**
     * 接收并转发WebSocket消息
     * 这个方法将被用于接收来自Python服务的消息并转发给前端
     */
    @PostMapping("/ws-relay/progress")
    public Result<?> relayProgress(@RequestBody Map<String, Object> message) {
        try {
            messagingTemplate.convertAndSend("/topic/progress", message);
            return Result.success();
        } catch (Exception e) {
            logger.error("转发进度消息失败", e);
            return Result.error("500", "转发进度消息失败: " + e.getMessage());
        }
    }
    
    /**
     * 接收并转发新评论消息
     */
    @PostMapping("/ws-relay/comment")
    public Result<?> relayComment(@RequestBody Map<String, Object> comment) {
        try {
            messagingTemplate.convertAndSend("/topic/comments", comment);
            return Result.success();
        } catch (Exception e) {
            logger.error("转发评论消息失败", e);
            return Result.error("500", "转发评论消息失败: " + e.getMessage());
        }
    }
    
    /**
     * 接收并转发错误消息
     */
    @PostMapping("/ws-relay/error")
    public Result<?> relayError(@RequestBody Map<String, String> error) {
        try {
            messagingTemplate.convertAndSend("/topic/errors", error);
            return Result.success();
        } catch (Exception e) {
            logger.error("转发错误消息失败", e);
            return Result.error("500", "转发错误消息失败: " + e.getMessage());
        }
    }
} 