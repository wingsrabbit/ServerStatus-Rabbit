# Web UI 问题修复 #3

**分支：** ServerStatus-Rabbit-feature-v0.12  
**日期：** 2026-03-19  
**版本：** v0.122 → v0.123

---

## 问题 1 & 4（合并）：CPU/内存/硬盘「维护中」样式与运行状态不一致

### 现象

截图 1（已离线节点）、截图 3（在线→维护中过渡）均显示：左侧「运行状态」列的**维护中**为红色 `error` 进度条（100% 宽度），但 CPU/内存/硬盘列的「维护中」样式不同——进度条宽度可能很小（残留在线时的百分比）、颜色可能是绿色 `success`（如 CPU 值很小时），与运行状态列视觉不一致。

### 根因分析

运行状态列模板（离线时）：
```html
<div class="ui progress error">
  <div class="bar" style="width: 100%"><span> 维护中 </span></div>
</div>
```

CPU/内存/硬盘列模板（离线时）：
```html
<div class="ui progress" :class="getProcessBarStatus(getCpuStatus)">
  <!-- getProcessBarStatus 取决于上次残留数据，可能返回 'success'/'warning'/'error' -->
  <div class="bar" :style="{'width': `${getCpuStatus.toString()}%`}">
    <!-- 宽度为上次残留值如 0.2% -->
    维护中
  </div>
</div>
```

当 `!getStatus` 时：
1. **bar class**：仍然基于 `getCpuStatus` 的残留值计算，可能为 `success`（绿色）
2. **bar width**：仍然为 `getCpuStatus.toString()%`（残留值，如 0.2%），而非 100%
3. **文字「维护中」**：文字正确但被压缩在极窄的进度条里，视觉效果完全不对

### 修复方案

**文件：`web/status-src/src/components/TableItem.vue`**

将 CPU/内存/硬盘的三个 `<td>` 改为：当 `!getStatus` 时，强制使用 `error` 类 + `width: 100%` + 文字「维护中」，与运行状态列完全一致。

修改前：
```html
<td>
  <div class="ui progress" :class="getProcessBarStatus(getCpuStatus)">
    <div class="bar" :style="{'width': `${getCpuStatus.toString()}%`}">
      {{ getStatus ? `${getCpuStatus.toString()}%` : '维护中' }}
    </div>
  </div>
</td>
```

修改后：
```html
<td>
  <div class="ui progress" :class="getStatus ? getProcessBarStatus(getCpuStatus) : 'error'">
    <div class="bar" :style="{'width': getStatus ? `${getCpuStatus.toString()}%` : '100%'}">
      {{ getStatus ? `${getCpuStatus.toString()}%` : '维护中' }}
    </div>
  </div>
</td>
```

三列（CPU / 内存 / 硬盘）均做相同改动。效果：离线时 CPU/内存/硬盘列渲染结果完全等价于 `<div class="ui progress error"><div class="bar" style="width:100%">维护中</div></div>`，与运行状态列的「维护中」视觉一致。

---

## 问题 2：直接访问 IP（80 端口）仍然打开旧页面

### 现象

浏览器访问 `http://45.192.177.58/`（即 80 端口）仍然能打开一个监控页面。v0.122 已在 Dockerfile 中移除了 `EXPOSE 80`，README 也移除了 `-p 80:80`，但用户的当前容器仍以旧参数运行。

### 根因分析

这**不是代码问题**。当前运行的 Docker 容器是用旧的 `docker run` 命令启动的（包含 `-p 80:80` 或 `-p 80:9191` 端口映射），所以宿主机 80 端口仍被映射到容器内的 9191 服务。v0.122 的 Dockerfile 修改只影响新构建的镜像和新创建的容器。

### 修复方案

**无需代码改动**，需要重新部署：

```bash
# 1. 停止并删除旧容器
docker stop ss-server
docker rm ss-server

# 2. 重新构建镜像（使用新的 Dockerfile，不含 EXPOSE 80）
docker build -t serverstatus-rabbit .

# 3. 用新参数启动容器（不映射 80 端口）
docker run -d --restart=always \
  --name ss-server \
  -p 9191:9191 \
  -p 9192:9192 \
  -p 443:443 \
  -v $(pwd)/data:/app/data \
  serverstatus-rabbit
```

> **注意：** 如果宿主机上还有其他服务（如 nginx、旧版 ServerStatus-Hotaru）在监听 80 端口，需要另外停止/删除那些服务。

---

## 问题 3：离线检测延迟 + 在线时间冻结行为

### 现象

卸载从属服务器（客户端）后：
1. 节点仍然显示「运行中」
2. 在线时间**重置为 0 后又开始增加**
3. 过了约 30 秒才最终显示掉线

用户期望的行为：
- 客户端断开后，在线时间**立刻冻结**（不再增长），状态仍显示「运行中」
- 超过 **10 秒**没有收到数据，节点进入「维护中」

### 根因分析

当前流程（bugs）：

```
时刻 T=0    客户端 TCP 断开
            → tcp_server.py finally 调用 state.set_offline(username)
            → node['online'] = False, node['connected_since'] = 0
            ↑ 节点立刻离线（但用户期望有 10 秒缓冲）

时刻 T=10   check_offline(30) 检测线程运行
            → 发现 last_seen 距今 < 30 秒
            → 进入 else 分支：node['online'] = True, connected_since = now
            ↑ 节点被错误地「复活」，在线时间从 0 重新开始

时刻 T=30+  check_offline(30) 检测
            → 发现 last_seen 距今 > 30 秒
            → node['online'] = False
            ↑ 最终离线，延迟 ~30 秒
```

三个 bug：
1. **`set_offline` 不应在 TCP 断开时立即调用** — 应改为依赖 `check_offline` 超时机制
2. **`check_offline` 不应有「复活」逻辑** — else 分支会把被 `set_offline` 标记为离线的节点重新置为在线
3. **超时时间 30 秒太长** — 用户期望 10 秒
4. **在线时间在断连后仍递增** — 公式 `time.time() - connected_since` 持续增长，应在客户端停止上报后冻结

### 修复方案

#### 3a. `server/tcp_server.py` — 移除 `set_offline` 调用

TCP 连接断开时，只清理连接映射，**不**主动将节点设为离线。让 `check_offline` 统一处理离线检测。

```python
# finally 块修改前：
finally:
    if username:
        with _clients_lock:
            _connected_clients.pop(username, None)
        state.set_offline(username)
        logger.info("客户端断开: %s", username)

# finally 块修改后：
finally:
    if username:
        with _clients_lock:
            _connected_clients.pop(username, None)
        logger.info("客户端断开: %s", username)
```

#### 3b. `server/state.py` — `check_offline` 移除「复活」逻辑

`check_offline` 应当只负责**标记离线**，不应将离线节点恢复为在线。在线恢复只通过 `update_node`（实际收到数据时）触发。

```python
# 修改前：
def check_offline(timeout_seconds):
    now = time.time()
    newly_offline = []
    newly_online = []
    with _lock:
        for username, node in _nodes.items():
            if node['last_seen'] == 0:
                continue
            if now - node['last_seen'] > timeout_seconds:
                if node['online']:
                    node['online'] = False
                    node['connected_since'] = 0
                    newly_offline.append(username)
            else:
                if not node['online']:          # ← 这个分支导致「复活」bug
                    node['online'] = True
                    node['connected_since'] = now
                    newly_online.append(username)
    return newly_offline, newly_online

# 修改后：
def check_offline(timeout_seconds):
    now = time.time()
    newly_offline = []
    with _lock:
        for username, node in _nodes.items():
            if node['last_seen'] == 0:
                continue
            if now - node['last_seen'] > timeout_seconds:
                if node['online']:
                    node['online'] = False
                    node['connected_since'] = 0
                    newly_offline.append(username)
    return newly_offline
```

> **注意：** 返回值从 `(newly_offline, newly_online)` 改为只返回 `newly_offline`。所有调用方需同步修改。

#### 3c. `server/alert.py` — 适配 `check_offline` 新返回值

```python
# 修改前：
newly_offline, newly_online = state.check_offline(timeout_seconds)

# 修改后：
newly_offline = state.check_offline(timeout_seconds)
```

`newly_online` 的检测改为：由 `update_node` 返回是否为新上线节点，或在 `check_and_alert` 中用其他方式检测。

具体方案：让 `update_node` 在节点从离线变为在线时，将用户名记入一个「新上线队列」，由 `check_and_alert` 定期消费。

在 `state.py` 中新增：
```python
_newly_online_queue = []

def update_node(username, data):
    with _lock:
        ...
        if not node['online']:
            node['connected_since'] = time.time()
            _newly_online_queue.append(username)  # 新增
        node['online'] = True
        ...

def pop_newly_online():
    """取出并清空新上线节点列表"""
    with _lock:
        result = list(_newly_online_queue)
        _newly_online_queue.clear()
        return result
```

在 `alert.py` 的 `check_and_alert` 中：
```python
newly_offline = state.check_offline(timeout_seconds)
newly_online = state.pop_newly_online()
```

#### 3d. 超时时间默认 10 秒

`server/alert.py` 中：
```python
# 修改前：
timeout_seconds = webhook_cfg.get('timeout_seconds', 30)

# 修改后：
timeout_seconds = webhook_cfg.get('timeout_seconds', 10)
```

#### 3e. 在线时间冻结

`server/state.py` 中 `get_all_stats()` 的 `uptime` 计算改为使用 `last_seen` 作为上界，而非 `time.time()`：

```python
# 修改前：
'uptime': str(int(time.time() - node['connected_since']))
         if node['online'] and node.get('connected_since', 0) > 0 else '0',

# 修改后：
'uptime': str(int(node['last_seen'] - node['connected_since']))
         if node['online'] and node.get('connected_since', 0) > 0
            and node['last_seen'] > node['connected_since'] else '0',
```

效果：
- **正常运行时**：`last_seen` 每秒更新（客户端每 1 秒上报），所以 `last_seen - connected_since` 每秒增长 1，显示平滑
- **客户端断连后**：`last_seen` 不再更新，`uptime` 冻结在最后一次收到数据的时刻
- **10 秒后**：`check_offline` 将节点标记离线，前端显示 `–`

#### 3f. `server/web_server.py` — 禁用节点时直接设为离线

由于 TCP finally 不再调用 `set_offline`，禁用节点时需确保状态立即更新。当前代码中 `update_server` 路由在禁用时已调用 `state.set_offline(username)`，无需额外改动。确认现有代码：

```python
if updates['disabled'] and not was_disabled:
    tcp_server.disconnect_user(username)
    state.set_offline(username)       # ← 已有，保留
```

`delete_server` 路由中也需要加上 `set_offline`：

```python
# 修改前（delete_server）：
tcp_server.disconnect_user(username)
config_manager.delete_server(username)

# 修改后：
tcp_server.disconnect_user(username)
state.set_offline(username)  # 删除前确保状态清理
config_manager.delete_server(username)
```

#### 3g. TCP socket timeout 优化（可选）

当前数据阶段 `conn.settimeout(60.0)`，在客户端异常断开（网络中断而非进程退出）时，recv 会阻塞长达 60 秒。可降低到 15 秒以加速资源回收：

```python
# 可选优化：
conn.settimeout(15.0)  # 数据阶段超时
```

此项为可选优化，不影响掉线检测逻辑（`check_offline` 独立运行）。

### 修复后时序

```
时刻 T=0    客户端 TCP 断开
            → tcp_server.py finally 只清理 _connected_clients
            → node 仍为 online，last_seen 冻结在最后一次上报时刻
            → 前端看到：运行中，在线时间冻结

时刻 T=10   check_offline(10) 检测线程运行
            → 发现 last_seen 距今 > 10 秒
            → node['online'] = False
            → 前端看到：维护中，在线时间显示 –
```

---

## 变更影响汇总

| 文件 | 问题 1&4 | 问题 2 | 问题 3 |
|------|----------|--------|--------|
| `web/status-src/src/components/TableItem.vue` | ✏️ | | |
| `server/tcp_server.py` | | | ✏️ |
| `server/state.py` | | | ✏️ |
| `server/alert.py` | | | ✏️ |
| `server/web_server.py` | | | ✏️ |

✏️ = 修改  
问题 2 无代码改动，需重新部署容器。
