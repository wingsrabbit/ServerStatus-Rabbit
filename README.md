# ServerStatus-Rabbit 🐇

轻量级多服务器状态监控面板，基于 Python + Vue 3 构建，兼容 [ServerStatus-Hotaru](https://github.com/cokemine/ServerStatus-Hotaru) 客户端协议。

![version](https://img.shields.io/badge/version-v0.131-blue)
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
| 部署 | Docker 多阶段构建，服务端/客户端双角色，支持一行脚本自动装 Docker 并完成部署 |
| 主题 | 监控页与后台均支持深色模式 |
| 兼容 | 兼容 ServerStatus-Hotaru 原版 Python 客户端协议 |

---

## 快速开始 — 服务端

在你的**主控服务器**上以 root 执行下面这一行：

```bash
bash -lc 'set -e; if ! command -v curl >/dev/null 2>&1; then if command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y curl; elif command -v dnf >/dev/null 2>&1; then dnf install -y curl; elif command -v yum >/dev/null 2>&1; then yum install -y curl; else echo "请先安装 curl"; exit 1; fi; fi; curl -fsSL https://raw.githubusercontent.com/wingsrabbit/ServerStatus-Rabbit/ServerStatus-Rabbit-NG/scripts/install-server.sh | bash'
```

这条命令会自动完成这些事情：

- 没有 Docker 就先安装 Docker
- 没有 Git 就先安装 Git
- 拉取 `ServerStatus-Rabbit-NG` 分支代码
- 构建 `serverstatus-rabbit:v0.131`
- 启动服务端容器 `ssr-server`
- 自动把服务端监听端口写入 `data/settings.json`

默认端口：

- Web：`9191`
- TCP 上报：`9192`

启动后：
- 监控页面：`http://你的IP:9191`
- 后台管理：`http://你的IP:9191/admin`（首次访问需设置管理员密码）

如果你的机器上 9191 或 9192 已经被占用，可以直接在同一条命令里覆盖端口：

```bash
bash -lc 'set -e; if ! command -v curl >/dev/null 2>&1; then if command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y curl; elif command -v dnf >/dev/null 2>&1; then dnf install -y curl; elif command -v yum >/dev/null 2>&1; then yum install -y curl; else echo "请先安装 curl"; exit 1; fi; fi; curl -fsSL https://raw.githubusercontent.com/wingsrabbit/ServerStatus-Rabbit/ServerStatus-Rabbit-NG/scripts/install-server.sh | env SSR_WEB_PORT=9291 SSR_TCP_PORT=9292 bash'
```

### 1. 在后台添加节点

登录后台管理，点击「+ 新增节点」，填写节点名称、用户名、密码等信息并保存。系统会自动生成该节点对应的客户端部署命令。

---

## 快速开始 — 客户端

在每台**被监控服务器**上以 root 执行下面这一行：

```bash
bash -lc 'set -e; if ! command -v curl >/dev/null 2>&1; then if command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y curl; elif command -v dnf >/dev/null 2>&1; then dnf install -y curl; elif command -v yum >/dev/null 2>&1; then yum install -y curl; else echo "请先安装 curl"; exit 1; fi; fi; curl -fsSL https://raw.githubusercontent.com/wingsrabbit/ServerStatus-Rabbit/ServerStatus-Rabbit-NG/scripts/install-client.sh | env SSR_SERVER=服务端IP SSR_USER=节点用户名 SSR_PASS=节点密码 bash'
```

这条命令会自动完成这些事情：

- 没有 Docker 就先安装 Docker
- 没有 Git 就先安装 Git
- 拉取 `ServerStatus-Rabbit-NG` 分支代码
- 构建 `serverstatus-rabbit:v0.131`
- 以 `--pid=host --net=host` 方式启动客户端容器
- 直接主动连接服务端 TCP 端口

如果服务端 TCP 端口不是默认的 `9192`，就在同一条命令里加 `SSR_PORT`：

```bash
bash -lc 'set -e; if ! command -v curl >/dev/null 2>&1; then if command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y curl; elif command -v dnf >/dev/null 2>&1; then dnf install -y curl; elif command -v yum >/dev/null 2>&1; then yum install -y curl; else echo "请先安装 curl"; exit 1; fi; fi; curl -fsSL https://raw.githubusercontent.com/wingsrabbit/ServerStatus-Rabbit/ServerStatus-Rabbit-NG/scripts/install-client.sh | env SSR_SERVER=服务端IP SSR_PORT=9292 SSR_USER=节点用户名 SSR_PASS=节点密码 bash'
```

### NAT 和公网是否要区分

不用区分。

当前项目的客户端始终是**主动向服务端发起 TCP 连接**，所以：

- 公网客户端可以用这条命令
- NAT 客户端也可以用这条命令
- 不需要额外的 NAT mode
- 不需要为“普通公网 Agent”单独准备另一套启动方式

只有一种情况需要额外写端口：服务端没有使用默认的 `9192`，而是改成了别的 TCP 端口，这时才需要显式传 `SSR_PORT`。

将 `服务端IP`、`节点用户名`、`节点密码` 替换为后台管理中的实际值。启动后节点会自动出现在监控页面上。

---

## 更新与维护

### 完整重建（涉及前端监控页或 Dockerfile 改动时）

```bash
cd ServerStatus-Rabbit
git pull origin ServerStatus-Rabbit-NG
docker stop ssr-server && docker rm ssr-server
docker build -t serverstatus-rabbit:v0.131 .
docker run -d --restart=always \
  --name ssr-server \
  -p 9191:9191 \
  -p 9192:9192 \
  -v $(pwd)/data:/app/data \
  serverstatus-rabbit:v0.131
```

> `data/` 目录中的配置和账户信息会保留，无需重新设置。

### 热更新（仅后端或管理页面改动时）

```bash
cd ServerStatus-Rabbit
git pull origin ServerStatus-Rabbit-NG
bash update.sh ssr-server
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

说明：

- 默认一行安装脚本直接使用 `9191` 和 `9192`
- 如果你的服务器要避开端口冲突，可以在安装命令中改成 `SSR_WEB_PORT` 和 `SSR_TCP_PORT`
- 客户端不区分 NAT 或公网，统一只需要能主动访问服务端的 TCP 端口即可

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

## 当前版本

当前主线版本：v0.131

说明：

- `main` 保留 v0.130 正式版
- `ServerStatus-Rabbit-NG` 作为 v0.131 升级分支
- v0.131 已纳入 192.168.88.102 NAT 客户端的实机接入与交接资料
- v0.131 README 已提供服务端与客户端的一行安装命令

## License

MIT
