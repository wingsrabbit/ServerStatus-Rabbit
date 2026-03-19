# 后台管理改进 #5 — DNS 检测 + HTTPS 保存即时反馈

**分支：** ServerStatus-Rabbit-feature-v0.12  
**日期：** 2026-03-19  
**版本：** v0.124 → v0.125

---

## 需求 1：DNS 检测工具

在「保存设置」按钮的右边添加一行 DNS 检测工具：左侧输入框填入域名（默认取 `httpsForm.domain`），右侧显示该域名解析到的 IP 地址。

### 交互

- 输入框默认值：`httpsForm.domain`（与上方域名字段联动）
- 点击「检测」按钮后，调用后端 API 解析域名
- 结果显示：
  - 解析成功 → 显示 IP（如 `45.192.177.58`）
  - 域名无记录 → 显示 「无指向」
  - 其他错误 → 显示错误信息

### 后端 API

新增 `GET /api/dns-check?domain=xxx`（需登录）：

```python
@app.route('/api/dns-check')
@_require_login
def dns_check():
    domain = request.args.get('domain', '').strip()
    if not domain:
        return jsonify(ok=False, message="域名不能为空")
    try:
        ip = socket.gethostbyname(domain)
        return jsonify(ok=True, ip=ip)
    except socket.gaierror:
        return jsonify(ok=True, ip="无指向")
```

### 前端

在「保存设置」按钮**右侧**同一行内添加：

```html
<span style="margin-left:20px;">
  DNS 检测：
  <input v-model="dnsCheckDomain" placeholder="status.example.com" style="width:220px;">
  <button class="ui small button" @click="checkDns">检测</button>
  <span v-if="dnsCheckResult">→ {{ dnsCheckResult }}</span>
</span>
```

新增响应式数据：
```javascript
const dnsCheckDomain = ref('');
const dnsCheckResult = ref('');
```

`dnsCheckDomain` 初始值在 `httpsForm.domain` 变化时同步（或用 `computed` / `watch`）。简单起见直接使用 `httpsForm.domain` 作为默认值，用户可以手动修改。

```javascript
async function checkDns() {
  dnsCheckResult.value = '检测中...';
  const d = dnsCheckDomain.value || httpsForm.domain;
  if (!d) { dnsCheckResult.value = '请输入域名'; return; }
  const res = await api(`/api/dns-check?domain=${encodeURIComponent(d)}`);
  dnsCheckResult.value = res.ok ? res.ip : res.message;
}
```

### 涉及文件

| 文件 | 改动 |
|------|------|
| `server/web_server.py` | ✏️ 新增 `/api/dns-check` 路由 |
| `web/admin/index.html` | ✏️ 添加 DNS 检测 UI + 逻辑 |

---

## 需求 2：HTTPS 保存即时反馈

### 现状

点击「保存设置」后，`saveSettings()` 调用 `POST /api/settings/https`，如果 certbot 执行失败（通常需要几秒），完成后才在页面顶部 `globalMsg` 区域显示红色错误。用户等待期间没有任何视觉反馈。

### 改进方案

直接复用顶部 `globalMsg` 条（截图中 `certbot 申请失败：域名 DNS 未指向本服务器` 的位置）：

1. **点击「保存设置」时**：`globalMsg` 立即显示绿色 `正在运行...`
2. **请求完成 — 成功**：绿色 `✅ 设置已保存`，3 秒后消失
3. **请求完成 — 失败**：变为红色，显示错误信息（如 `certbot 申请失败：域名 DNS 未指向本服务器`），不自动消失

### 实现

修改 `saveSettings()`：
```javascript
async function saveSettings() {
  globalMsg.value = '正在运行...';
  globalOk.value = true;           // 绿色

  const httpsRes = await api('/api/settings/https', { ... });
  if (!httpsRes.ok) {
    globalMsg.value = httpsRes.message;
    globalOk.value = false;        // 变红
    return;                        // 不自动消失
  }

  const portRes = await api('/api/settings/port9191', { ... });
  if (portRes.ok) {
    globalMsg.value = '✅ 设置已保存';
    globalOk.value = true;
    setTimeout(() => { globalMsg.value = ''; }, 3000);
  } else {
    globalMsg.value = portRes.message;
    globalOk.value = false;        // 不自动消失
  }
}
```

### 涉及文件

| 文件 | 改动 |
|------|------|
| `web/admin/index.html` | ✏️ 修改 `saveSettings()` 函数 |

---

## 变更影响汇总

| 文件 | 需求 1 | 需求 2 |
|------|--------|--------|
| `server/web_server.py` | ✏️ | |
| `web/admin/index.html` | ✏️ | ✏️ |

✏️ = 修改
