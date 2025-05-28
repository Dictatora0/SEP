<template>
  <div style="height: 50px; line-height: 50px; border-bottom: 1px solid #ccc; display:flex;" >
    <div style="width: 200px; padding-left: 30px; font-weight: bold;color: dodgerblue ">
      <el-select v-model="currentLang" size="small" @change="handleLanguageChange" style="width: 100px;">
        <el-option
          v-for="item in languages"
          :key="item.value"
          :label="item.label"
          :value="item.value">
        </el-option>
      </el-select>
    </div>
    <div style="flex: 1; display: flex; justify-content: center;">
      <!-- 添加导航菜单 -->
      <el-menu 
        :default-active="activeIndex" 
        mode="horizontal" 
        @select="handleSelect"
        background-color="transparent"
        text-color="#333"
        active-text-color="#409EFF">
        <el-menu-item index="home">首页</el-menu-item>
        <el-menu-item index="crawler">评论爬取</el-menu-item>
        <el-menu-item index="comment-category">评论分类</el-menu-item>
        <el-menu-item index="comment-summary">评论摘要</el-menu-item>
        <el-menu-item index="comment-compare">评论对比</el-menu-item>
      </el-menu>
    </div>
    <div style="width: 150px; display: flex; align-items: center; justify-content: flex-end;">
      <template v-if="user">
        <el-dropdown @command="handleCommand">
          <span class="el-dropdown-link">
            <el-avatar :size="30" :src="user.avatar" style="margin-right: 10px;">
              <img v-if="!user.avatar" :src="defaultAvatar" alt=""/>
            </el-avatar>
            {{ user.nickName }}
            <i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="person">{{ $t('header.personInfo') }}</el-dropdown-item>
            <el-dropdown-item command="logout">{{ $t('header.logout') }}</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </template>
      <template v-else>
        <el-button type="primary" @click="$router.push('/login')">{{ $t('header.login') }}</el-button>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Header',
  props: {
    user: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      defaultAvatar: require('@/assets/default-avatar.png'),
      currentLang: 'zh',
      languages: [
        { value: 'zh', label: '中文' },
        { value: 'en', label: 'English' }
      ],
      activeIndex: 'home' // 默认激活的菜单项
    }
  },
  created() {
    console.log('Header组件创建，用户信息:', this.user)
    // 从localStorage获取保存的语言设置
    const savedLang = localStorage.getItem('language')
    if (savedLang) {
      this.currentLang = savedLang
      this.$i18n.locale = savedLang
    }
    
    // 根据当前路由设置激活的菜单项
    this.setActiveMenu()
  },
  watch: {
    user: {
      handler(newVal) {
        console.log('Header组件用户信息变化:', newVal)
      },
      immediate: true
    },
    '$route': {
      handler() {
        // 路由变化时更新激活的菜单项
        this.setActiveMenu()
      },
      immediate: true
    }
  },
  methods: {
    handleCommand(command) {
      console.log('下拉菜单命令:', command)
      if (command === 'person') {
        this.handlePersonClick()
      } else if (command === 'logout') {
        this.handleLogoutClick()
      }
    },
    handleSelect(key) {
      // 导航菜单选择处理
      if (key === 'home') {
        this.$router.push('/')
      } else if (key === 'crawler') {
        this.$router.push('/crawler')
      } else {
        this.$router.push(`/${key}`)
      }
    },
    setActiveMenu() {
      // 根据当前路由设置激活的菜单项
      const path = this.$route.path
      if (path === '/' || path === '/home') {
        this.activeIndex = 'home'
      } else if (path === '/crawler') {
        this.activeIndex = 'crawler'
      } else if (path.includes('comment-category')) {
        this.activeIndex = 'comment-category'
      } else if (path.includes('comment-summary')) {
        this.activeIndex = 'comment-summary'
      } else if (path.includes('comment-compare')) {
        this.activeIndex = 'comment-compare'
      }
    },
    handlePersonClick() {
      console.log('点击个人信息按钮')
      if (!this.user) {
        console.log('用户未登录')
        this.$message.warning('请先登录')
        this.$router.push('/login')
        return
      }
      console.log('准备跳转到个人信息页面')
      this.$router.push({
        path: '/person',
        query: {from: this.$route.path}
      }).catch(err => {
        console.error('路由跳转失败:', err)
      })
    },
    handleLogoutClick() {
      // 清除用户信息
      sessionStorage.removeItem("user")
      this.$message.success('退出成功')
      this.$router.push('/login')
    },
    handleLanguageChange(lang) {
      // 保存语言设置到localStorage
      localStorage.setItem('language', lang)
      // 更新i18n的语言设置
      this.$i18n.locale = lang
      // 显示切换成功提示
      this.$message.success(lang === 'zh' ? '已切换到中文' : 'Switched to English')
    }
  }
}
</script>

<style scoped>
.el-dropdown-link {
  line-height: 50px;
  cursor: pointer;
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
}

.el-dropdown {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.el-dropdown-link {
  border: none;
  outline: none;
}

.el-menu {
  border-bottom: none !important;
}

.el-menu--horizontal>.el-menu-item {
  height: 49px;
  line-height: 49px;
}
</style>