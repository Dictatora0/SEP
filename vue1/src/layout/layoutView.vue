<template>
    <nav>
      <!--  头部  -->
      <Header />
      <!--主体-->
      <div style="display: flex;">
        <!--侧边栏-->
        <Aside />
        <!--      内容区域-->
        <router-view style="flex: 1;" />
      </div>
    </nav>
</template>

<script>
import Aside from "@/components/Aside.vue";
import Header from "@/components/Header.vue";

export default {
  name: 'Layout',
  components: {
    Aside,
    Header
  }
}
</script>

<style scoped>

</style>