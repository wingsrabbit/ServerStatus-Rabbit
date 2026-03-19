# Web UI 需求变更 #1

**分支：** ServerStatus-Rabbit-feature-v0.12
**日期：** 2026-03-19

---

## 需求 1：后台可自定义页面标题文字

**现状：** 监控页顶部标题 `"Server Status"` 和副标题 `"Servers' Probes Set up with ServerStatus-Rabbit"` 硬编码在 `web/status-src/public/config.js` 中，修改需要重新构建前端。

**需求：** 在后台管理面板中增加两个文本输入框，允许管理员在线修改：
- **页面标题**（对应 `config.js` 的 `header` 字段，默认值 `"Server Status"`）
- **页面副标题**（对应 `config.js` 的 `subHeader` 字段，默认值 `"Servers' Probes Set up with ServerStatus-Rabbit"`）

**实现思路：**
- 后端 `settings.json` 新增 `ui` 配置段：
  ```json
  "ui": {
    "header": "Server Status",
    "subHeader": "Servers' Probes Set up with ServerStatus-Rabbit"
  }
  ```
- 新增 API `GET/POST /api/settings/ui`，用于读取和保存 UI 配置
- 前端 `config.js` 改为动态方案：`App.vue` 在初始化时请求 `/api/settings/ui`（公开接口），用返回值覆盖 `window.__PRE_CONFIG__` 中的 `header` 和 `subHeader`；如果接口不可用则使用 `config.js` 中的默认值
- 后台管理面板新增「页面设置」区域，包含标题和副标题输入框 + 保存按钮

**涉及文件：**
- `server/config_manager.py` — `DEFAULT_SETTINGS` 新增 `ui` 段
- `server/web_server.py` — 新增 `/api/settings/ui` 路由（GET 为公开，POST 需登录）
- `web/admin/index.html` — 新增页面设置 UI
- `web/status-src/src/App.vue` 或 `TheHeader.vue` — 从 API 获取标题文字

---

## 需求 2：在线时间（uptime）显示格式修正

**现状：** 表格中 `uptime` 字段直接显示原始秒数（如 `87199`），不易阅读。

**需求：** 将 uptime 秒数转换为人类可读的递进式时间格式，规则如下：

| 范围 | 显示格式 | 示例 |
|------|----------|------|
| < 60 秒 | `X秒` | `45秒` |
| ≥ 60 秒 且 < 60 分钟 | `X分Y秒` | `3分28秒` |
| ≥ 60 分钟 且 < 24 小时 | `X小时Y分` （不显示秒） | `2小时15分` |
| ≥ 24 小时 | `X天Y小时` （不显示分钟） | `3天12小时` |

**实现思路：**
- 在 `useStatus.ts` 中新增 `formatUptime` 计算属性（或工具函数），接收 `uptime` 字符串（秒数），返回格式化后的字符串
- `TableItem.vue` 中 `{{ server.uptime || '–' }}` 改为 `{{ formatUptime }}`
- `CardItem.vue` 如有显示 uptime 的地方也做同样处理

**涉及文件：**
- `web/status-src/src/components/useStatus.ts` — 新增 `formatUptime`
- `web/status-src/src/components/TableItem.vue` — 使用 `formatUptime`

---

## 需求 3：展开行新增 CPU 信息

**现状：** 点击表格行展开后，显示内存信息、交换分区、硬盘信息。无 CPU 详细信息。

**需求：** 在展开区域的**内存信息上方**新增一行 CPU 信息，显示格式：

```
CPU信息: 20%
```

> **说明：** 当前 `GET /api/stats` 返回的数据中只有 `cpu`（使用率百分比），没有 CPU 核心数字段。如果后续需要显示核心数（如 `20% / 8 Core`），需要客户端 `collector.py` 新增采集 `cpu_cores` 字段并通过 TCP 上报，后端 `state.py` 的 `get_all_stats()` 也需要新增该字段。**本次先实现百分比显示，核心数作为后续增强。**

**如果同时实现核心数（推荐一步到位）：**
- 客户端 `collector.py` 新增 `cpu_cores: psutil.cpu_count(logical=True)` 
- 后端 `state.py` 的 `_make_default_node()` 和 `get_all_stats()` 新增 `cpu_cores` 字段
- 前端 `types/index.ts` 的 `StatusItem` 新增 `cpu_cores: number`
- 展开行显示：`CPU信息: 20% / 8 Core`

**涉及文件：**
- `web/status-src/src/components/TableItem.vue` — 展开区域新增 CPU 行
- `web/status-src/src/types/index.ts` — `StatusItem` 新增 `cpu_cores`
- `client/collector.py` — 采集 CPU 核心数
- `server/state.py` — 新增 `cpu_cores` 字段

---

## 需求 4：「最后更新」移至页脚并实时刷新

**现状：**
- `UpdateTime.vue` 组件在表格下方显示 `"最后更新: 5 分钟前."`
- 该组件的计算属性只在 `updated` prop 变化时重新计算，不会自动随时间流逝刷新显示文字
- 位置突兀，且不会实时更新

**需求：**
1. **删除** 当前位置的 `UpdateTime` 组件（表格下方的独立显示）
2. 将「最后更新」信息**移入页脚**，Footer 显示为：
   ```
   Powered by ServerStatus-Rabbit · 进入后台 · 最后更新：X秒前
   ```
3. 「最后更新」文字**每秒自动刷新**，反映与 `updated` 时间戳的真实差距
4. 当 API 轮询成功时 `updated` 会更新，所以正常情况下应该显示几秒前（因为默认每 2 秒轮询一次）；如果节点都掉线或 API 不可用，时间差会逐渐增大

**显示格式：** 复用需求 2 的递进式时间风格，但添加 `"前"` 后缀：
- `X秒前`、`X分Y秒前`、`X小时Y分前`、`X天Y小时前`

**实现思路：**
- `App.vue` 中移除 `<update-time>` 组件
- `TheFooter.vue` 接收 `updated` prop，内部用 `setInterval` 每秒计算时间差并格式化
- Footer 不再从 `config.js` 读取静态 HTML，改为动态渲染
- 或者保留 `config.js` 的 footer 配置作为基础文字，动态 append 最后更新时间

**涉及文件：**
- `web/status-src/src/App.vue` — 移除 `<update-time>`，给 `<the-footer>` 传 `updated`
- `web/status-src/src/components/TheFooter.vue` — 接收 `updated`，实时显示最后更新
- `web/status-src/src/components/UpdateTime.vue` — 可删除或保留但不再使用

---

## 变更影响汇总

| 文件 | 需求 1 | 需求 2 | 需求 3 | 需求 4 |
|------|--------|--------|--------|--------|
| `server/config_manager.py` | ✏️ | | | |
| `server/web_server.py` | ✏️ | | | |
| `server/state.py` | | | ✏️ | |
| `client/collector.py` | | | ✏️ | |
| `web/admin/index.html` | ✏️ | | | |
| `web/status-src/src/App.vue` | ✏️ | | | ✏️ |
| `web/status-src/src/components/TheHeader.vue` | ✏️ | | | |
| `web/status-src/src/components/TheFooter.vue` | | | | ✏️ |
| `web/status-src/src/components/UpdateTime.vue` | | | | 🗑️ |
| `web/status-src/src/components/useStatus.ts` | | ✏️ | | |
| `web/status-src/src/components/TableItem.vue` | | ✏️ | ✏️ | |
| `web/status-src/src/components/CardItem.vue` | | ✏️ | | |
| `web/status-src/src/types/index.ts` | | | ✏️ | |
| `web/status-src/public/config.js` | ✏️ | | | |

✏️ = 修改 · 🗑️ = 删除或废弃
