# Web UI 改进 #4 — 一键折叠/展开所有分组

**分支：** ServerStatus-Rabbit-feature-v0.12  
**日期：** 2026-03-19  
**版本：** v0.123 → v0.124

---

## 需求

当节点分组较多时（如 Asia、Europe、North America、South America、Africa、Oceania 共 6 组），逐个点击 ▶/▼ 折叠展开非常繁琐。

**期望：** 在上半部分（表格视图 ServersTable）和下半部分（卡片视图 ServersCard）的第一个分组上方，各添加一个「全部折叠 / 全部展开」按钮。

---

## 设计

### 按钮行为

- **初始状态**：所有分组默认展开（与现行一致），按钮显示「▼ 全部折叠」
- **点击「▼ 全部折叠」**：所有分组折叠，按钮切换为「▶ 全部展开」
- **点击「▶ 全部展开」**：所有分组展开，按钮切换为「▼ 全部折叠」
- **混合状态**（部分手动展开/折叠后）：按钮根据「是否全部折叠」判断 — 若全部已折叠则显示「▶ 全部展开」，否则显示「▼ 全部折叠」

### 视觉

- 按钮样式与分组标题（group-header）风格一致，使用同样的 `cursor: pointer`
- 文字靠左对齐，字号略小或颜色稍浅以区别于分组标题
- 放置于分组列表之前（`v-for` 上方）

---

## 实现方案

### `web/status-src/src/components/ServersTable.vue`

1. 新增 `allCollapsed` computed：检查所有分组是否均已折叠
2. 新增 `toggleAll` 方法：遍历所有分组名，统一设置 `collapsed[name]`
3. 模板中 `v-for` 上方插入按钮行

```html
<!-- v-for 之前 -->
<div class="toggle-all" @click="toggleAll" v-if="groups.length > 1">
  <span>{{ allCollapsed ? '▶ 全部展开' : '▼ 全部折叠' }}</span>
</div>
```

```typescript
const allCollapsed = computed(() =>
  groups.value.length > 0 && groups.value.every(g => collapsed[g.name])
);

const toggleAll = () => {
  const target = !allCollapsed.value;
  for (const g of groups.value) {
    collapsed[g.name] = target;
  }
};
```

### `web/status-src/src/components/ServersCard.vue`

同样的逻辑，在 `#cards` 内 `v-for` 之前插入按钮。

---

## 涉及文件

| 文件 | 改动 |
|------|------|
| `web/status-src/src/components/ServersTable.vue` | ✏️ 新增 toggleAll + allCollapsed + 按钮 |
| `web/status-src/src/components/ServersCard.vue` | ✏️ 同上 |

✏️ = 修改
