package com.example.controller;

import com.example.crawler.JDCrawlerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 爬虫控制器
 * 提供爬取京东商品评论的API接口
 */
@RestController
@RequestMapping("/api/crawler")
public class CrawlerController {

    private final JDCrawlerService jdCrawlerService;

    @Autowired
    public CrawlerController(JDCrawlerService jdCrawlerService) {
        this.jdCrawlerService = jdCrawlerService;
    }

    /**
     * 启动爬虫爬取评论
     * @param params 请求参数
     * @return 异步响应结果
     */
    @PostMapping("/start")
    public CompletableFuture<ResponseEntity<Map<String, Object>>> startCrawler(@RequestBody Map<String, String> params) {
        String productUrl = params.get("url");
        String productId = params.get("productId");
        String productName = params.get("productName");

        // 参数验证
        if (productUrl == null || productUrl.isEmpty()) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", "商品链接不能为空");
            return CompletableFuture.completedFuture(ResponseEntity.badRequest().body(errorResponse));
        }

        // 如果未提供商品ID，尝试从URL中提取
        if (productId == null || productId.isEmpty()) {
            // 从URL中提取商品ID
            java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("/([0-9]+)\\.html");
            java.util.regex.Matcher matcher = pattern.matcher(productUrl);
            if (matcher.find()) {
                productId = matcher.group(1);
            } else {
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("success", false);
                errorResponse.put("message", "无法从URL中提取商品ID，请手动指定");
                return CompletableFuture.completedFuture(ResponseEntity.badRequest().body(errorResponse));
            }
        }

        // 调用爬虫服务
        return jdCrawlerService.startCrawler(productUrl, productId, productName)
                .thenApply(result -> {
                    if ((Boolean) result.getOrDefault("success", false)) {
                        return ResponseEntity.ok(result);
                    } else {
                        return ResponseEntity.status(500).body(result);
                    }
                });
    }

    /**
     * 爬虫状态查询接口
     * 前端可以通过轮询此接口获取爬虫状态
     * 注意：实际使用中推荐使用WebSocket实时推送，这里提供轮询方式作为备选
     */
    @GetMapping("/status/{productId}")
    public ResponseEntity<Map<String, Object>> getCrawlerStatus(@PathVariable("productId") String productId) {
        // 这里应该实现查询爬虫状态的逻辑
        // 由于我们使用WebSocket实时推送，此接口仅作为备选方案
        Map<String, Object> status = new HashMap<>();
        status.put("message", "请使用WebSocket连接获取实时爬取进度");
        return ResponseEntity.ok(status);
    }
} 