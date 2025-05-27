<template>
  <div>
    <el-menu
      :default-active="defaultActive"
      class="el-menu-vertical-demo"
      @open="handleOpen"
      @close="handleClose"
      :default-openeds='["1"]'
    >
    <el-submenu index="1">
      <template slot="title">
        <i class="el-icon-location"></i>
        <span>系统管理</span>
      </template>
      <el-menu-item index="dashboard" @click="navigateTo('Dashboard')">首页</el-menu-item>
      <el-menu-item index="crawler" @click="navigateTo('CommentCrawler')">评论爬取</el-menu-item>
    </el-submenu>
    </el-menu>
  </div>
</template>

<script>
export default {
  name: 'Aside',
  data() {
    return {
    };
  },
  computed: {
    defaultActive() {
      // 根据当前路由名称设置 active 菜单项
      return this.$route.name === 'Dashboard' ? 'dashboard' : 'crawler';
    }
  },
  methods: {
    navigateTo(routeName) {
      this.$router.push({ name: routeName });
    },
    handleOpen(key, keyPath) {
      console.log(key, keyPath);
    },
    handleClose(key, keyPath) {
      console.log(key, keyPath);
    }
  }
};
</script>

<style scoped>
.el-menu-vertical-demo {
  height: 100%;
}
</style>