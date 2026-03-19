<template>
  <div v-for="(group, gIndex) of groups" :key="gIndex" class="group-section">
    <div class="group-header" @click="toggleGroup(group.name)">
      <span>{{ collapsed[group.name] ? '▶' : '▼' }} {{ group.name || '未分组' }} ({{ group.servers.length }}台)</span>
    </div>
    <table class="ui basic unstackable table" id="table" v-show="!collapsed[group.name]">
      <thead>
      <tr>
        <th id="status4">运行状态</th>
        <th id="name">节点名</th>
        <th id="type">类型</th>
        <th id="location">服务器位置</th>
        <th id="uptime">在线时间</th>
        <th id="load">负载</th>
        <th id="network">网络(B/s) ↓|↑</th>
        <th id="traffic">流量(B) ↓|↑</th>
        <th id="cpu">CPU</th>
        <th id="ram">内存</th>
        <th id="hdd">硬盘</th>
      </tr>
      </thead>
      <tbody id="servers">
      <table-item v-for="(server, index) of group.servers" :key="index" :server="server"/>
      </tbody>
    </table>
  </div>
</template>
<script lang="ts">
import { defineComponent, PropType, computed, reactive } from 'vue';
import TableItem from '@/components/TableItem.vue';
import { StatusItem } from '@/types';

export default defineComponent({
  name: 'ServersTable',
  props: {
    servers: {
      type: Array as PropType<Array<StatusItem>>,
      default: () => ([])
    }
  },
  components: {
    TableItem
  },
  setup(props) {
    const collapsed = reactive<Record<string, boolean>>({});

    const groups = computed(() => {
      const groupMap: Record<string, StatusItem[]> = {};
      const order: string[] = [];
      const ungrouped: StatusItem[] = [];

      if (!props.servers) return [];

      for (const server of props.servers) {
        const g = (server as any).group || '';
        if (!g) {
          ungrouped.push(server);
        } else {
          if (!groupMap[g]) {
            groupMap[g] = [];
            order.push(g);
          }
          groupMap[g].push(server);
        }
      }

      const result = order.map(name => ({ name, servers: groupMap[name] }));
      if (ungrouped.length > 0 || result.length === 0) {
        result.push({ name: '', servers: ungrouped });
      }
      return result;
    });

    const toggleGroup = (name: string) => {
      collapsed[name] = !collapsed[name];
    };

    return { groups, collapsed, toggleGroup };
  }
});
</script>
<style>
#table {
  font-size: 1rem;
  border: none;
  text-align: center;
  vertical-align: middle;
}

#table thead tr th {
  color: #9da2a6;
  white-space: nowrap;
}
</style>
