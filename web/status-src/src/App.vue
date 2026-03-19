<template>
  <div class="theme-toggle" @click="toggleTheme">{{ isDark ? '☀️' : '🌙' }}</div>
  <the-header :header="headerText" :sub-header="subHeaderText"/>
  <the-error v-show="!servers"/>
  <div class="container">
    <servers-table :servers="servers"/>
    <servers-card :servers="servers"/>
  </div>
  <the-footer :last-fetch-time="lastFetchTime"/>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';

import TheHeader from '@/components/TheHeader.vue';
import TheError from '@/components/TheError.vue';
import ServersTable from '@/components/ServersTable.vue';
import ServersCard from '@/components/ServersCard.vue';
import TheFooter from '@/components/TheFooter.vue';
import { BoxItem, StatusItem } from '@/types';

export default defineComponent({
  name: 'App',
  components: {
    TheHeader,
    TheError,
    ServersTable,
    ServersCard,
    TheFooter
  },
  setup() {
    const servers = ref<Array<StatusItem | BoxItem>>();
    const updated = ref<number>();
    const lastFetchTime = ref<number>(0);
    const { interval, header, subHeader } = window.__PRE_CONFIG__;
    const headerText = ref(header);
    const subHeaderText = ref(subHeader);
    let timer: number;
    const runFetch = () => axios.get('/api/stats')
      .then(res => {
        servers.value = res.data.servers;
        updated.value = Number(res.data.updated);
        lastFetchTime.value = Date.now() / 1000;
      })
      .catch(err => console.log(err));
    onMounted(() => {
      runFetch();
      timer = setInterval(runFetch, interval * 1000);
      // 加载自定义 UI 设置
      axios.get('/api/settings/ui').then(res => {
        if (res.data.ok && res.data.data) {
          if (res.data.data.header) headerText.value = res.data.data.header;
          if (res.data.data.subHeader) subHeaderText.value = res.data.data.subHeader;
        }
      }).catch(() => { /* ignore */ });
    });
    onBeforeUnmount(() => clearInterval(timer));

    // 深色模式
    const isDark = ref(false);
    const initTheme = () => {
      const saved = localStorage.getItem('theme');
      if (saved) {
        isDark.value = saved === 'dark';
      } else {
        isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
      document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light');
    };
    const toggleTheme = () => {
      isDark.value = !isDark.value;
      localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light');
    };
    onMounted(initTheme);

    return {
      servers,
      updated,
      lastFetchTime,
      isDark,
      toggleTheme,
      headerText,
      subHeaderText
    };
  }
});
</script>

<style>
/* CSS Variables for theming */
:root,
[data-theme="light"] {
  --bg-color: #ffffff;
  --text-color: #333333;
  --card-bg: rgba(255, 255, 255, .8);
  --table-row-bg: rgba(249, 249, 249, .8);
  --table-text: #616366;
  --header-text: #9da2a6;
  --border-color: rgba(34, 36, 38, .1);
  --footer-text: #333;
  --group-header-bg: rgba(0, 0, 0, .03);
  --updated-text: #555;
}

[data-theme="dark"] {
  --bg-color: #1a1a2e;
  --text-color: #e0e0e0;
  --card-bg: rgba(30, 30, 50, .85);
  --table-row-bg: rgba(30, 30, 50, .8);
  --table-text: #c0c0c0;
  --header-text: #8a8f93;
  --border-color: rgba(255, 255, 255, .1);
  --footer-text: #aaa;
  --group-header-bg: rgba(255, 255, 255, .05);
  --updated-text: #aaa;
}

[data-theme="dark"] body {
  background: #1a1a2e !important;
}

[data-theme="dark"] #table {
  color: var(--table-text);
}

[data-theme="dark"] #table thead tr th {
  color: var(--header-text) !important;
}

[data-theme="dark"] tr.tableRow {
  background-color: var(--table-row-bg) !important;
}

[data-theme="dark"] tr td {
  color: var(--table-text) !important;
}

[data-theme="dark"] div.card {
  background-color: var(--card-bg) !important;
  color: var(--text-color);
}

[data-theme="dark"] .footer p {
  color: var(--footer-text);
}

[data-theme="dark"] .footer p a {
  color: #7da8d6;
}

[data-theme="dark"] .updated {
  color: var(--updated-text);
}

[data-theme="dark"] p.error {
  color: var(--table-text);
}

.theme-toggle {
  position: fixed;
  top: 15px;
  right: 20px;
  z-index: 1000;
  cursor: pointer;
  font-size: 1.5rem;
  padding: 5px 10px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  backdrop-filter: blur(5px);
  user-select: none;
}

.group-header {
  cursor: pointer;
  padding: 8px 12px;
  margin: 10px 0 5px;
  background: var(--group-header-bg, rgba(0,0,0,.03));
  border-radius: 4px;
  font-weight: bold;
  font-size: 1.05rem;
  color: var(--text-color, #333);
  user-select: none;
}

.group-header:hover {
  opacity: 0.8;
}

body {
  /*Replace your background image at this place!*/
  background: url("./assets/img/bg_parts.png") repeat-y left top, url('./assets/img/bg.png') repeat left top;
}

/*Global*/
div.bar {
  min-width: 0 !important;
}

/*Responsive*/
@media only screen and (min-width: 1200px) {
  .container {
    width: 1155px;
    margin: 0 auto;
  }
}

@media only screen and (max-width: 1200px) {
  #app .container {
    width: auto;
    margin: 0 .8rem;
  }

  #table thead tr th, #table tr.tableRow td {
    padding: .7em;
  }
}

@media only screen and (max-width: 1075px) {
  #type, tr td:nth-child(3) {
    display: none;
  }
}

@media only screen and (max-width: 992px) {
  html, body {
    font-size: 13px;
  }
}

@media only screen and (max-width: 910px) {
  #location, tr td:nth-child(4) {
    display: none;
  }
}

@media (max-width: 768px) {
  html, body {
    font-size: 12px;
  }

  #servers div.progress {
    width: 40px;
  }

  #cards .card div.card-header span {
    font-size: 1.55rem;
  }

  #cards .card div.card-content p {
    font-size: 1.25rem;
    margin-bottom: 0.6rem;
  }

  #app #header {
    height: 20rem;
    /*Replace your header image (for mobile use) at this place!*/
    background: url("assets/img/cover_mobile.png") no-repeat center center !important;
  }
}

@media only screen and (max-width: 720px) {
  #uptime, tr td:nth-child(5) {
    display: none;
  }
}

@media only screen and (max-width: 660px) {
  #load, tr td:nth-child(6) {
    display: none;
  }
}

@media only screen and (max-width: 600px) {
  #traffic, tr td:nth-child(8) {
    display: none;
  }
}

@media only screen and (max-width: 533px) {
  #name, tr td:nth-child(2) {
    min-width: 20px;
    max-width: 60px;
    text-overflow: ellipsis;
    overflow: hidden;
  }

  #hdd, tr td:nth-child(11) {
    display: none;
  }

  #cpu, #ram {
    min-width: 20px;
    max-width: 40px;
  }
}
</style>
