# 后台管理修复 #7 — certbot 错误信息透传

**分支：** ServerStatus-Rabbit-feature-v0.12  
**日期：** 2026-03-19  
**版本：** v0.127 → v0.128

---

## 问题现象

certbot 申请失败时，前端始终显示硬编码的「certbot 申请失败：域名 DNS 未指向本服务器」，无论真实原因是什么（80 端口不通、频率限制、网络问题等）。

## 根因

- `https_manager.py` 的 `request_letsencrypt_cert` 记录了真实错误日志，但返回值只有 `(False, None, None)`，错误信息丢失。
- `web_server.py` 收到 `False` 后返回硬编码字符串，无法区分失败原因。

## 修复方案

### `server/https_manager.py`

`request_letsencrypt_cert` 返回 4 元组 `(success, cert_path, key_path, error_msg)`：

| 失败场景 | error_msg |
|---------|-----------|
| certbot 非零退出码 | `result.stderr or result.stdout or "未知错误"` |
| 证书文件未生成 | `"证书文件生成失败"` |
| 执行超时 | `"certbot 执行超时（120秒）"` |
| certbot 未安装 | `"certbot 未安装"` |
| 成功 | `None` |

### `server/web_server.py`

解包 4 元组，失败时使用真实错误：`f"certbot 申请失败：{cert_error}"`

---

## 涉及文件

| 文件 | 改动 |
|------|------|
| `server/https_manager.py` | ✏️ 增加第四个返回值 |
| `server/web_server.py` | ✏️ 使用真实错误信息 |
| `web/admin/index.html` | ✏️ 版本号更新 |
