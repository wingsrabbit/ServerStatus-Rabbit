<template>
  <div id="cards">
    <div v-for="(group, gIndex) of groups" :key="gIndex" class="group-section">
      <div class="group-header" @click="toggleGroup(group.name)">
        <span>{{ collapsed[group.name] ? '▶' : '▼' }} {{ group.name || '未分组' }} ({{ group.servers.length }}台)</span>
      </div>
      <div class="ui doubling three column grid" v-show="!collapsed[group.name]">
        <CardItem v-for="(server, index) of group.servers" :key="index" :server="server"/>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType, computed, reactive } from 'vue';
import CardItem from '@/components/CardItem.vue';
import { StatusItem } from '@/types';

export default defineComponent({
  name: 'ServersCard',
  props: {
    servers: Array as PropType<Array<StatusItem>>
  },
  components: {
    CardItem
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
#cards {
  padding-top: 3.4rem;
  padding-bottom: 3.5rem;
}

@media only screen and (max-width: 767px) {
  #cards .column {
    width: 100% !important;
    margin: 0 auto !important;
  }
}
</style>
