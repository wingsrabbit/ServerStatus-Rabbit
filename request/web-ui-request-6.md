# 后台管理修复 #6 — certbot 申请失败问题

**分支：** ServerStatus-Rabbit-feature-v0.12  
**日期：** 2026-03-19  
**版本：** v0.125 → v0.126

---

## 问题现象

DNS 检测显示域名 `status.wingsrabbit.com` 已正确指向服务器 IP `45.192.177.58`，但点击保存设置后仍然报错「certbot 申请失败：域名 DNS 未指向本服务器」。

## 根因分析

两个问题叠加：

### 问题 A：80 端口未映射，certbot 无法完成 HTTP-01 验证

certbot `--standalone` 模式会在容器内 80 端口**临时**启动 HTTP 服务器，Let's Encrypt 通过 `http://域名:80/.well-known/acme-challenge/xxx` 来验证域名所有权。certbot 验证完成后自动退出，80 端口自动释放。**这个临时监听/释放是 certbot 自身的行为，不需要我们写代码控制。**

但：如果 `docker run` 时没有 `-p 80:80`，外部流量根本到不了容器内的 80 端口，certbot 的验证服务器等于无效，验证必然失败。

v0.122 为解决「访问 IP:80 打开旧页面」移除了 `-p 80:80`，这直接导致 certbot 无法申请证书。

**结论：** `-p 80:80` 必须在 `docker run` 时映射。我们自己的代码不在 80 端口运行任何常驻服务，80 端口只有 certbot 执行的那几秒钟有东西在监听，平时是空闲的。之前用户看到的 80 端口页面是宿主机上其他服务（旧版 ServerStatus-Hotaru 等）导致的，与本项目无关。

### 问题 B：错误信息不准确，无法 debug

当前流程：
1. `https_manager.py` 的 `request_letsencrypt_cert` 拿到了 certbot 真实错误（`result.stderr`），但只写了日志，返回值是 `(False, None, None)`
2. `web_server.py` 收到 `False` 后，写死返回「certbot 申请失败：域名 DNS 未指向本服务器」
3. 不管真实原因是 80 端口不通、频率限制、还是网络问题，前端永远只看到这一句

---

## 修复方案

### 6a. 恢复 80 端口映射

**`Dockerfile`**：恢复 `EXPOSE 80`

```dockerfile
# 暴露端口：Web(9191) + TCP通信(9192) + HTTPS(443) + certbot验证(80)
EXPOSE 9191 9192 443 80
```

**`README.md`**：

1. `docker run` 示例恢复 `-p 80:80`
2. 端口说明表格改为：`80 | certbot 证书验证（仅申请/续期时临时监听数秒，平时空闲）`
3. 「升级已有部署」章节恢复 `-p 80:80`
4. 移除之前「不要映射 80 端口」的注意事项

### 6b. 传递 certbot 真实错误信息到前端

**`server/https_manager.py`**：`request_letsencrypt_cert` 增加第四个返回值——错误信息字符串

```python
# 成功：
return True, cert_path, key_path, None

# 各种失败分支：
return False, None, None, "具体错误描述"
```

各分支的错误信息：
- certbot 返回非零退出码 → `result.stderr or result.stdout or "未知错误"`
- 证书文件不存在 → `"证书文件生成失败"`
- 执行超时 → `"certbot 执行超时（120秒）"`
- certbot 未安装 → `"certbot 未安装"`

**`server/web_server.py`**：使用真实错误信息

```python
# 修改前：
success, cert_path, key_path = https_manager.request_letsencrypt_cert(domain, email)
if not success:
    return jsonify(ok=False, message="certbot 申请失败：域名 DNS 未指向本服务器"), 500

# 修改后：
success, cert_path, key_path, cert_error = https_manager.request_letsencrypt_cert(domain, email)
if not success:
    return jsonify(ok=False, message=f"certbot 申请失败：{cert_error}"), 500
```

---

## 涉及文件

| 文件 | 改动 |
|------|------|
| `Dockerfile` | ✏️ 恢复 `EXPOSE 80` |
| `README.md` | ✏️ 恢复 `-p 80:80`，更新端口说明 |
| `server/https_manager.py` | ✏️ 增加错误信息返回值 |
| `server/web_server.py` | ✏️ 使用真实错误信息 |

✏️ = 修改
