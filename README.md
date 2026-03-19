# ServerStatus-Rabbit 🐇

轻量级多服务器状态监控面板，基于 Python + Vue 3 构建，兼容 [ServerStatus-Hotaru](https://github.com/cokemine/ServerStatus-Hotaru) 客户端协议。

![version](https://img.shields.io/badge/version-v0.13-blue)
![Python](https://img.shields.io/badge/python-3.12-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 目录

- [功能特性](#功能特性)
- [快速开始 — 服务端](#快速开始--服务端)
- [快速开始 — 客户端](#快速开始--客户端)
- [更新与维护](#更新与维护)
- [后台管理](#后台管理)
- [端口说明](#端口说明)
- [数据持久化](#数据持久化)
- [紧急恢复](#紧急恢复)
- [非 Docker 部署](#非-docker-部署)
- [技术栈](#技术栈)

---

## 功能特性

| 类别 | 特性 |
|------|------|
| 监控 | CPU、内存、磁盘、网络流量、系统负载实时展示 |
| 管理 | Web 后台增删改节点，无需编辑配置文件 |
| 分组 | 按地区/用途对节点分组，支持全部折叠/展开 |
| 告警 | 节点掉线/恢复 Webhook 通知（企业微信、Slack、自定义 URL） |
| HTTPS | Let's Encrypt 一键申请 / 手动上传证书 |
| 部署 | Docker 多阶段构建，服务端/客户端双角色 |
| 主题 | 监控页与后台均支持深色模式 |
| 兼容 | 兼容 ServerStatus-Hotaru 原版 Python 客户端协议 |

---

## 快速开始 — 服务端

在你的**主控服务器**上执行：

### 1. 构建镜像

```bash
git clone https://github.com/wingsrabbit/ServerStatus-Rabbit.git
cd ServerStatus-Rabbit
docker build -t serverstatus-rabbit .
```

### 2. 启动服务端

```bash
docker run -d --restart=always \
  --name ss-server \
  -p 9191:9191 \
  -p 9192:9192 \
  -p 443:443 \
  -p 80:80 \
  -v $(pwd)/data:/app/data \
  serverstatus-rabbit
```

启动后：
- 监控页面：`http://你的IP:9191`
- 后台管理：`http://你的IP:9191/admin`（首次访问需设置管理员密码）

### 3. 在后台添加节点

登录后台管理，点击「+ 新增节点」，填写节点名称、用户名、密码等信息并保存。系统会自动生成该节点对应的客户端部署命令。

---

## 快速开始 — 客户端

在每台**被监控服务器**上执行：

### 1. 构建镜像（每台被监控机器都需要）

```bash
git clone https://github.com/wingsrabbit/ServerStatus-Rabbit.git
cd ServerStatus-Rabbit
docker build -t serverstatus-rabbit .
```

> 客户端和服务端使用同一个镜像，通过启动参数区分角色。

### 2. 启动客户端

使用后台管理为该节点生成的部署命令运行：

```bash
docker run -d --restart=always \
  --pid=host --net=host \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /:/host/rootfs:ro \
  serverstatus-rabbit client \
  --server=服务端IP \
  --port=9192 \
  --user=节点用户名 \
  --pass=节点密码
```

将 `服务端IP`、`节点用户名`、`节点密码` 替换为后台管理中的实际值。启动后节点会自动出现在监控页面上。

---

## 更新与维护

### 完整重建（涉及前端监控页或 Dockerfile 改动时）

```bash
cd ServerStatus-Rabbit
git pull
docker stop ss-server && docker rm ss-server
docker build -t serverstatus-rabbit .
docker run -d --restart=always \
  --name ss-server \
  -p 9191:9191 \
  -p 9192:9192 \
  -p 443:443 \
  -p 80:80 \
  -v $(pwd)/data:/app/data \
  serverstatus-rabbit
```

> `data/` 目录中的配置和账户信息会保留，无需重新设置。

### 热更新（仅后端或管理页面改动时）

```bash
cd ServerStatus-Rabbit
git pull
bash update.sh ss-server
```

脚本会将 `server/`、`client/`、`app.py`、`web/admin/` 复制到容器内并重启，无需重建镜像。

> **注意：** 前端监控页（`web/status-src/` 下的 Vue 组件）或 Dockerfile 改动仍需完整重建。

---

## 后台管理

| 功能 | 说明 |
|------|------|
| 节点管理 | 增删改查，支持分组、禁用/启用、一键生成部署命令 |
| HTTPS 设置 | Let's Encrypt 自动申请或手动上传证书，内置 DNS 检测工具 |
| 端口管理 | 动态开关 9191 HTTP 端口（HTTPS 启用后可关闭） |
| 页面设置 | 自定义监控页标题和副标题 |
| 告警设置 | Webhook 掉线/恢复通知，支持测试发送 |
| 深色模式 | 一键切换，偏好自动保存 |

---

## 端口说明

| 端口 | 用途 | 必需 |
|------|------|------|
| 9191 | Web 监控页 + 后台管理（HTTP） | ✅ |
| 9192 | TCP 数据通信（客户端上报） | ✅ |
| 443 | HTTPS（后台开启后生效） | 可选 |
| 80 | Let's Encrypt 证书验证（certbot 临时监听数秒，平时空闲） | 可选 |

---

## 数据持久化

所有数据存储在容器内 `/app/data/`，通过 `-v $(pwd)/data:/app/data` 挂载到宿主机：

```
data/
├── config.json      # 节点配置
├── admin.json       # 管理员账户
├── settings.json    # 系统设置（HTTPS、端口、Webhook、页面）
└── certs/           # SSL 证书
```

---

## 紧急恢复

**HTTPS 配置出错导致无法访问后台：**

```bash
docker exec -it ss-server python recover.py
docker restart ss-server
```

**管理员密码忘记或被锁定（连续 10 次错误）：**

```bash
docker exec -it ss-server python recover.py --reset-password
docker restart ss-server
```

---

## 非 Docker 部署

### 服务端

```bash
pip install -r requirements.txt

# 构建前端（需要 Node.js）
cd web/status-src
npm install && npm run build
cd ../..
mkdir -p web/status
cp -r web/status-src/dist/* web/status/

python app.py
```

### 客户端

```bash
pip install psutil requests
python app.py client --server=服务端IP --port=9192 --user=用户名 --pass=密码
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + Flask + werkzeug |
| 前端监控页 | Vue 3 + TypeScript + Semantic UI |
| 后台管理 | Vue 3 (CDN) + Semantic UI (CDN) |
| 数据采集 | psutil |
| 容器 | Docker 多阶段构建（node:18-slim + python:3.12-slim） |

---

## License

MIT
