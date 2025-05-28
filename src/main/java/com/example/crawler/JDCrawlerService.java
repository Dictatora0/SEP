package com.example.crawler;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.http.HttpEntity;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 京东评论爬虫服务
 * 用于与Python爬虫服务进行通信
 */
@Service
public class JDCrawlerService {
    
    @Value("${python.crawler.url}/api/crawl")
    private String crawlerServiceUrl;
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    /**
     * 异步启动爬虫爬取评论
     * @param productUrl 商品URL
     * @param productId 商品ID
     * @param productName 商品名称
     * @return 异步结果
     */
    public CompletableFuture<Map<String, Object>> startCrawler(String productUrl, String productId, String productName) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                return callCrawlerService(productUrl, productId, productName);
            } catch (IOException e) {
                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("success", false);
                errorResult.put("message", "调用爬虫服务失败: " + e.getMessage());
                return errorResult;
            }
        });
    }
    
    /**
     * 调用Python爬虫服务API
     * @param productUrl 商品URL
     * @param productId 商品ID
     * @param productName 商品名称
     * @return 响应结果
     * @throws IOException 网络异常
     */
    private Map<String, Object> callCrawlerService(String productUrl, String productId, String productName) throws IOException {
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpPost httpPost = new HttpPost(crawlerServiceUrl);
            httpPost.setHeader("Content-Type", "application/json");
            
            // 构建请求体
            Map<String, String> requestBody = new HashMap<>();
            requestBody.put("url", productUrl);
            requestBody.put("product_id", productId);
            requestBody.put("product_name", productName);
            
            String jsonBody = objectMapper.writeValueAsString(requestBody);
            httpPost.setEntity(new StringEntity(jsonBody, "UTF-8"));
            
            // 执行请求
            try (CloseableHttpResponse response = httpClient.execute(httpPost)) {
                HttpEntity entity = response.getEntity();
                String responseBody = EntityUtils.toString(entity);
                
                // 解析响应
                return objectMapper.readValue(responseBody, Map.class);
            }
        }
    }
} 