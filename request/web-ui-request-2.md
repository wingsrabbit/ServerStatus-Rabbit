# Web UI 问题修复 #2

**分支：** ServerStatus-Rabbit-feature-v0.12  
**日期：** 2026-03-19  
**版本：** v0.121 → v0.122

---

## 问题 1：80 端口不应该默认暴露

**现象：** 浏览器访问服务器 80 端口时出现内容（可能是旧版 ServerStatus-Hotaru 残留，或其他服务）。用户预期 80 端口只在 certbot 申请 SSL 证书时短暂开放。

**根因：** `Dockerfile` 中 `EXPOSE 9191 9192 443 80` 暴露了 80 端口，`README.md` 的 `docker run` 示例中也映射了 `-p 80:80`。如果用户用 `-p 80:80` 启动容器，宿主机的 80 端口会被映射到容器内。虽然我们的 Python 代码不在 80 端口监听任何服务，但如果宿主机上有其他服务或旧容器占用 80 端口也会造成混淆。

**修复方案：**
1. `Dockerfile` 的 `EXPOSE` 移除 `80`，改为 `EXPOSE 9191 9192 443`
2. `README.md` 的 `docker run` 示例移除 `-p 80:80`，在端口说明表格中将 80 端口标注为「certbot 验证专用，仅申请证书时临时使用，无需映射」
3. 代码层面无需改动，certbot 申请时会自行临时监听 80 端口

**涉及文件：**
- `Dockerfile` — 移除 EXPOSE 80
- `README.md` — 移除 -p 80:80，更新端口说明

---

## 问题 2：节点离线时 CPU/内存/硬盘列应显示红色「维护中」

**现象：** 节点离线时，表格中 CPU/内存/硬盘进度条的「维护中」文字颜色与原版不一致。原版显示为红色 `error` 样式的进度条，当前可能因 `getCpuStatus` 返回 `100`（offline 默认值），导致 `getProcessBarStatus(100)` 返回 `'error'`，但条的宽度仍为 100%。同时在线时间列在离线时不应显示 `0秒`，应显示 `–`。

**修复方案：**
1. 在线时间列：离线时显示 `–` 而非 `0秒`
   ```
   {{ getStatus ? formatUptime : '–' }}
   ```

2. CPU/内存/硬盘进度条：离线时强制使用 `error` class + 100% 宽度 + 「维护中」文字（现有逻辑实际已接近正确，确认无 CSS 覆盖问题即可）

**涉及文件：**
- `web/status-src/src/components/TableItem.vue` — 在线时间列加 `getStatus` 判断

---

## 问题 3：在线时间应显示「连接时长」而非「服务器系统 uptime」

**现象：** 节点被添加后，表格显示 `1天0小时`，这是服务器的系统运行时长（`psutil.boot_time()` 计算）。用户要求显示的是：**节点连接到 ServerStatus-Rabbit 后经过的时间**，即「本次在线时长」。

**修复方案：**

### 后端 `server/state.py`

1. `_make_default_node()` 新增 `connected_since: 0` 字段
2. `update_node()` 中：当节点从离线变为在线时（`node['online']` 从 `False` 变 `True`），记录 `connected_since = time.time()`
3. `get_all_stats()` 中：`uptime` 改为由服务端计算 `int(now - connected_since)` 而非使用客户端上报的 uptime 值；离线时返回 `'0'`
4. `set_offline()` 中：重置 `connected_since = 0`

### 客户端 `client/collector.py`

无需改动。客户端仍然上报系统 uptime，但服务端不再使用此字段作为前端展示值（保留用于内部参考）。

### 前端

无需改动。`formatUptime` 已正确格式化秒数。

**涉及文件：**
- `server/state.py` — 新增 `connected_since`，修改 `update_node` / `get_all_stats` / `set_offline`

---

## 问题 4：「最后更新」应基于客户端收到响应的时刻计算

**现象：** 页脚「最后更新：5分36秒前 / 5分37秒前」来回跳。原因是 `updated` 使用的是服务器端 `time.time()` 时间戳，与浏览器本地时间 `Date.now()/1000` 存在固定偏差（服务器时钟与浏览器时钟不完全同步）。

**修复方案：**

改为**客户端本地计时**：
1. `App.vue` 中不再透传服务器的 `updated` 时间戳给 Footer
2. 新增一个 `lastFetchTime` ref，每次 API 轮询成功时记录 `Date.now() / 1000`（浏览器本地时间）
3. `TheFooter.vue` 接收 `lastFetchTime` prop（浏览器本地时间戳），每秒用 `Date.now()/1000 - lastFetchTime` 计算差值
4. 正常轮询（每 2 秒）时显示效果约为 `0秒前` ~ `2秒前`；如果客户端断网，差值会自然递增

**显示规则：**
- ≤ 10 秒：`10秒内`
- > 10 秒：按递进式格式 `X秒前` → `X分Y秒前` → `X小时Y分前` → `X天Y小时前`

**涉及文件：**
- `web/status-src/src/App.vue` — 新增 `lastFetchTime`，替代透传 `updated`
- `web/status-src/src/components/TheFooter.vue` — 使用 `lastFetchTime` 本地计时

---

## 变更影响汇总

| 文件 | 问题 1 | 问题 2 | 问题 3 | 问题 4 |
|------|--------|--------|--------|--------|
| `Dockerfile` | ✏️ | | | |
| `README.md` | ✏️ | | | |
| `server/state.py` | | | ✏️ | |
| `web/status-src/src/components/TableItem.vue` | | ✏️ | | |
| `web/status-src/src/App.vue` | | | | ✏️ |
| `web/status-src/src/components/TheFooter.vue` | | | | ✏️ |

✏️ = 修改
