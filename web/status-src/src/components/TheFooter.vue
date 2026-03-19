<template>
  <div class="footer">
    <p>Powered by ServerStatus-Rabbit · <a href="/admin">进入后台</a> · 最后更新：{{ timeSince }}</p>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';

export default defineComponent({
  name: 'TheFooter',
  props: {
    lastFetchTime: { type: Number, default: 0 }
  },
  setup(props) {
    const timeSince = ref('--');
    let timer: number;

    const formatTimeSince = () => {
      if (!props.lastFetchTime) { timeSince.value = '从未'; return; }
      const totalSeconds = Math.floor(Date.now() / 1000 - props.lastFetchTime);
      if (totalSeconds < 0 || totalSeconds <= 10) { timeSince.value = '10秒内'; return; }
      const days = Math.floor(totalSeconds / 86400);
      const hours = Math.floor((totalSeconds % 86400) / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      if (days > 0) timeSince.value = `${days}天${hours}小时前`;
      else if (hours > 0) timeSince.value = `${hours}小时${minutes}分前`;
      else if (minutes > 0) timeSince.value = `${minutes}分${seconds}秒前`;
      else timeSince.value = `${seconds}秒前`;
    };

    onMounted(() => {
      formatTimeSince();
      timer = setInterval(formatTimeSince, 1000);
    });
    onBeforeUnmount(() => clearInterval(timer));

    return { timeSince };
  }
});
</script>

<style>
.footer p {
  text-align: center;
  padding-bottom: 15px;
}

.footer p a {
  vertical-align: middle;
  transition: color .3s ease;
}

.footer p a:hover {
  color: #ff779a;
}
</style>
