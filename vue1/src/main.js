import Vue from 'vue'
import App from './App.vue'
import router from './router'
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
import axios from 'axios'
import io from 'socket.io-client'

Vue.config.productionTip = false

// 配置ElementUI
Vue.use(ElementUI)

// 配置axios
axios.defaults.baseURL = process.env.VUE_APP_BASE_API || 'http://localhost:8080'
Vue.prototype.$http = axios

// 添加Socket.IO到Vue原型
Vue.prototype.$io = io

new Vue({
  router,
  render: h => h(App)
}).$mount('#app') 