import Vue from 'vue'
import Router from 'vue-router'
import Layout from './layout/layoutView.vue'
import CommentCrawler from './components/CommentCrawler.vue'

Vue.use(Router)

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('./components/Dashboard.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'crawler',
        name: 'CommentCrawler',
        component: CommentCrawler,
        meta: { title: '评论爬取' }
      }
    ]
  }
]

const router = new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

export default router 