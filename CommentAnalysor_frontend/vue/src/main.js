import Vue from 'vue'
import App from './App.vue'
import router from './router'
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
import axios from 'axios'
import i18n from './i18n'

Vue.config.productionTip = false

// 使用ElementUI
Vue.use(ElementUI)

// 配置axios
axios.defaults.baseURL = 'http://localhost:8080' // 指定后端API地址
axios.defaults.withCredentials = true // 允许发送cookie
axios.defaults.headers.common['Content-Type'] = 'application/json'
axios.defaults.headers.common['Accept'] = 'application/json'

// 添加请求拦截器，用于调试
axios.interceptors.request.use(
  config => {
    console.log(`发送请求到: ${config.url}`, config);
    // 从sessionStorage获取token
    const user = JSON.parse(sessionStorage.getItem('user') || '{}')
    if (user.token) {
      config.headers['token'] = user.token
    }
    return config;
  },
  error => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

Vue.prototype.$axios = axios
Vue.prototype.$http = axios

// 响应拦截处理
axios.interceptors.response.use(
  response => {
    console.log(`收到响应: ${response.config.url}`, response.data);
    return response
  },
  error => {
    console.error('API请求错误:', error)
    if (error.response) {
      console.error('错误状态码:', error.response.status);
      console.error('错误数据:', error.response.data);
    }
    ElementUI.Message.error('请求失败: ' + (error.response && error.response.data && error.response.data.message || error.message))
    return Promise.reject(error)
  }
)

new Vue({
  router,
  i18n,
  render: h => h(App)
}).$mount('#app') 