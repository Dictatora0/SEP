<template>
  <div class="crawler-container">
    <div class="header">
      <h2>京东评论爬取</h2>
    </div>
    
    <div class="input-section">
      <el-input 
        v-model="productUrl" 
        placeholder="请输入京东商品URL" 
        class="url-input">
      </el-input>
      <el-input 
        v-model="productId" 
        placeholder="商品ID（必填）" 
        class="id-input">
      </el-input>
      <el-button 
        type="primary" 
        @click="startCrawler" 
        :loading="isLoading">
        开始爬取
      </el-button>
    </div>
    
    <div v-if="crawlerStatus" class="status-section">
      <div class="status-info">
        <div class="status-badge" :class="statusClass">
          {{ statusText }}
        </div>
        <div v-if="commentCount > 0" class="comment-count">
          已爬取 <span class="count-number">{{ commentCount }}</span> 条评论
        </div>
      </div>
      <el-progress 
        v-if="crawlerStatus === 'crawling'" 
        :percentage="progressPercentage" 
        :stroke-width="15" 
        :format="progressFormat">
      </el-progress>
    </div>
    
    <div v-if="recentComments.length > 0" class="comments-section">
      <h3>最新爬取的评论</h3>
      <div class="comments-container">
        <div v-for="(comment, index) in recentComments" :key="index" class="comment-item">
          <div class="comment-header">
            <span class="nickname">{{ comment.nickname || '匿名用户' }}</span>
            <div class="rating">
              <el-rate :value="comment.score" disabled show-score text-color="#ff9900"></el-rate>
            </div>
            <span class="time">{{ comment.creation_time }}</span>
          </div>
          <div class="comment-content">{{ comment.content }}</div>
        </div>
      </div>
    </div>
    
    <div v-if="error" class="error-message">
      <el-alert :title="error" type="error" show-icon></el-alert>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client';

export default {
  name: 'CommentCrawler',
  data() {
    return {
      productUrl: '',
      productId: '',
      isLoading: false,
      crawlerStatus: null, // null, 'starting', 'crawling', 'completed'
      commentCount: 0,
      targetCount: 100, // 估计目标数量
      recentComments: [],
      error: null,
      socket: null
    };
  },
  computed: {
    statusText() {
      switch(this.crawlerStatus) {
        case 'starting': return '正在启动爬虫...';
        case 'crawling': return '爬取中...';
        case 'completed': return '爬取完成';
        default: return '';
      }
    },
    statusClass() {
      switch(this.crawlerStatus) {
        case 'starting': return 'status-starting';
        case 'crawling': return 'status-crawling';
        case 'completed': return 'status-completed';
        default: return '';
      }
    },
    progressPercentage() {
      // 根据评论数动态调整进度，最高100%
      const percentage = Math.min(100, (this.commentCount / this.targetCount) * 100);
      return parseFloat(percentage.toFixed(1));
    }
  },
  methods: {
    progressFormat() {
      return `${this.commentCount} 条评论`;
    },
    startCrawler() {
      if (!this.productUrl) {
        this.$message.error('请输入商品URL');
        return;
      }

      if (!this.productId) {
        this.$message.error('请输入商品ID');
        return;
      }
      
      this.isLoading = true;
      this.error = null;
      this.recentComments = [];
      this.commentCount = 0;
      this.crawlerStatus = 'starting';
      
      // 连接WebSocket
      this.connectWebSocket();
      
      // 发送爬取请求到Python服务
      this.$http.post('http://localhost:5004/api/crawl', {
        url: this.productUrl,
        product_id: this.productId,
        product_name: this.productId
      }).then(response => {
        console.log('爬虫请求已发送:', response.data);
      }).catch(error => {
        this.error = error.message || '系统错误';
        this.isLoading = false;
        this.disconnectWebSocket();
      });
    },
    connectWebSocket() {
      // 连接到Python服务的Socket.IO
      this.socket = io('http://localhost:5004');
      
      this.socket.on('connect', () => {
        console.log('WebSocket连接成功');
      });
      
      this.socket.on('progress', (data) => {
        console.log('收到进度更新:', data);
        this.crawlerStatus = 'crawling';
        if (data.current) {
          this.commentCount = data.current;
        }
      });
      
      this.socket.on('new_comment', (comment) => {
        console.log('收到新评论:', comment);
        // 将新评论添加到顶部
        this.recentComments.unshift(comment);
        
        // 最多显示20条最新评论
        if (this.recentComments.length > 20) {
          this.recentComments.pop();
        }
      });
      
      this.socket.on('complete', (data) => {
        console.log('爬取完成:', data);
        this.crawlerStatus = 'completed';
        this.isLoading = false;
        if (data.total) {
          this.commentCount = data.total;
        }
        this.$message.success(`爬取完成，共获取${this.commentCount}条评论`);
      });
      
      this.socket.on('error', (error) => {
        console.error('WebSocket错误:', error);
        this.error = error.message || '爬取过程中发生错误';
        this.isLoading = false;
      });
      
      this.socket.on('disconnect', () => {
        console.log('WebSocket断开连接');
      });
    },
    disconnectWebSocket() {
      if (this.socket) {
        this.socket.disconnect();
        this.socket = null;
      }
    }
  },
  beforeDestroy() {
    this.disconnectWebSocket();
  }
}
</script>

<style scoped>
.crawler-container {
  padding: 20px;
}
.header {
  margin-bottom: 20px;
}
.input-section {
  display: flex;
  margin-bottom: 20px;
  gap: 10px;
}
.url-input {
  flex: 3;
}
.id-input {
  flex: 1;
}
.status-section {
  background-color: #f8f8f8;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.status-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.status-badge {
  padding: 5px 10px;
  border-radius: 3px;
  color: white;
  font-weight: bold;
}
.status-starting {
  background-color: #409EFF;
}
.status-crawling {
  background-color: #E6A23C;
}
.status-completed {
  background-color: #67C23A;
}
.comment-count {
  font-size: 16px;
}
.count-number {
  font-weight: bold;
  color: #409EFF;
}
.comments-section {
  margin-top: 20px;
}
.comments-container {
  max-height: 400px;
  overflow-y: auto;
}
.comment-item {
  background-color: #fff;
  padding: 15px;
  margin-bottom: 15px;
  border: 1px solid #eee;
  border-radius: 5px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  align-items: center;
}
.nickname {
  font-weight: bold;
  color: #333;
}
.time {
  color: #999;
  font-size: 12px;
}
.comment-content {
  line-height: 1.6;
}
.error-message {
  margin-top: 20px;
}
</style> 