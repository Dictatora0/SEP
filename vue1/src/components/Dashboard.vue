<template>
  <div class="dashboard-container">
    <h1>商品评论爬取系统</h1>
    <div class="dashboard-info">
      <div class="info-card">
        <h3>系统概述</h3>
        <p>本系统提供商品评论爬取功能，支持实时监控爬取进度及结果展示。</p>
      </div>
      <div class="info-card">
        <h3>使用指南</h3>
        <p>1. 前往"评论爬取"页面</p>
        <p>2. 输入商品ID和URL</p>
        <p>3. 点击开始爬取按钮</p>
        <p>4. 实时查看爬取进度和结果</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Dashboard',
  data() {
    return {
      
    }
  }
}
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.dashboard-info {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 20px;
}

.info-card {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 20px;
  flex: 1;
  min-width: 300px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

h1 {
  color: #409EFF;
}

h3 {
  margin-top: 0;
  color: #409EFF;
}
</style> 