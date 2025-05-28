const path = require('path')

module.exports = {
  devServer: {
    port: 8084, // 修改为实际运行的端口8084
    open: true, // 自动打开浏览器
    proxy: {
      '/api': {
        target: 'http://localhost:8080', // 后端API地址
        changeOrigin: true,
        pathRewrite: {
          '^/api': '' // 重写路径
        }
      },
      '/user': {
        target: 'http://localhost:8080', // 用户API
        changeOrigin: true,
        pathRewrite: {
          '^/user': '/user' // 保持路径不变
        }
      },
      '/admin': {
        target: 'http://localhost:8080', // 管理员API
        changeOrigin: true,
        pathRewrite: {
          '^/admin': '/admin' // 保持路径不变
        }
      },
      '/crawler': {
        target: 'http://localhost:5004', // 爬虫服务地址
        changeOrigin: true
      }
    }
  },
  // 生产环境不生成sourcemap
  productionSourceMap: false,
  // 输出目录设置
  outputDir: 'dist',
  // 静态资源目录
  assetsDir: 'static',
  // CSS配置
  css: {
    loaderOptions: {
      sass: {
        additionalData: `@import "@/styles/variables.scss";`
      }
    }
  },
  transpileDependencies: [],
  configureWebpack: {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    }
  }
} 