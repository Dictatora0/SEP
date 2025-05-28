package com.example.demo.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

@Configuration
public class GlobalCorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        // 创建CORS配置对象
        CorsConfiguration config = new CorsConfiguration();
        
        // 允许所有来源跨域调用
        config.addAllowedOrigin("http://localhost:8083");
        config.addAllowedOrigin("http://localhost:8084");
        config.addAllowedOrigin("http://localhost:5004");
        
        // 如果需要允许所有来源，可以使用下面的代码（但不能与setAllowCredentials(true)一起使用）
        // config.addAllowedOriginPattern("*");
        
        // 允许跨域发送cookie
        config.setAllowCredentials(true);
        
        // 放行全部原始头信息
        config.addAllowedHeader("*");
        
        // 允许所有请求方法跨域调用
        config.addAllowedMethod("*");
        
        // 暴露头信息
        config.addExposedHeader("*");
        
        // 预检请求的有效期，单位为秒
        config.setMaxAge(3600L);
        
        // 添加映射路径，拦截一切请求
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        
        return new CorsFilter(source);
    }
} 