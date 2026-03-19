# ServerStatus-Rabbit 🐇

轻量级多服务器状态监控面板，基于 Python 重写后端，兼容 [ServerStatus-Hotaru](https://github.com/cokemine/ServerStatus-Hotaru) 客户端协议。

![ServerStatus-Rabbit](https://img.shields.io/badge/version-v0.1-blue)
![Python](https://img.shields.io/badge/python-3.12-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 功能特性

- **实时监控** — CPU、内存、磁盘、网络流量、系统负载一目了然
- **分组管理** — 按地区/用途对节点分组显示
- **Web 后台** — 浏览器中增删改节点，无需编辑配置文件
- **一键部署命令** — 新增节点后自动生成客户端 Docker 部署命令
- **掉线告警** — Webhook 通知（支持企业微信、Slack、自定义 URL）
- **HTTPS 支持** — Let's Encrypt 自动申请 / 手动上传证书
- **深色模式** — 监控页和后台管理均支持
- **Docker 一键部署** — 多阶段构建，服务端/客户端双角色

## 快速开始

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
  -v $(pwd)/data:/app/data \
  serverstatus-rabbit
```

启动后访问 `http://你的IP:9191` 查看监控页面，访问 `http://你的IP:9191/admin` 进入后台管理。

> **首次访问后台**会提示设置管理员密码（至少 6 位）。

### 3. 添加被监控节点

在后台管理页面点击「新增节点」，填写节点信息后系统会自动生成部署命令，形如：

```bash
docker run -d --restart=always \
  --pid=host --net=host \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /:/host/rootfs:ro \
  serverstatus-rabbit client \
  --server=你的服务端IP \
  --port=9192 \
  --user=节点用户名 \
  --pass=节点密码
```

在被监控服务器上运行该命令即可。

## 端口说明

| 端口 | 用途 |
|------|------|
| 9191 | Web 监控页面 + 后台管理（HTTP） |
| 9192 | TCP 数据通信（客户端上报数据） |
| 443 | HTTPS（可选，后台开启后生效） |
| 80 | Let's Encrypt 证书验证（certbot 申请时临时使用，无需映射） |

## 数据持久化

所有数据存储在 `/app/data/` 目录中，请挂载宿主机卷以持久化：

```
data/
├── config.json      # 节点配置
├── admin.json       # 管理员账户
├── settings.json    # 系统设置（HTTPS、端口、Webhook）
└── certs/           # SSL 证书
```

## 后台管理功能

| 功能 | 说明 |
|------|------|
| 节点管理 | 增删改节点，支持分组、禁用/启用 |
| HTTPS 管理 | Let's Encrypt 自动申请或手动上传证书 |
| 端口管理 | 动态开关 9191 端口（HTTPS 启用后可关闭） |
| Webhook | 节点掉线/恢复时发送通知，支持测试 |
| 深色模式 | 一键切换，偏好自动保存 |

## 紧急恢复

如果 HTTPS 配置出错导致无法访问后台：

```bash
docker exec -it ss-server python recover.py
docker restart ss-server
```

如果管理员密码忘记或被锁定（连续 10 次错误）：

```bash
docker exec -it ss-server python recover.py --reset-password
docker restart ss-server
```

## 非 Docker 部署

### 服务端

```bash
# 安装依赖
pip install -r requirements.txt

# 构建前端（需要 Node.js）
cd web/status-src
npm install && npm run build
cd ../..
mkdir -p web/status
cp -r web/status-src/dist/* web/status/

# 启动服务端
python app.py
```

### 客户端

```bash
pip install psutil requests
python app.py client --server=服务端IP --port=9192 --user=用户名 --pass=密码
```

## 技术栈

- **后端**：Python 3.12 + Flask + werkzeug
- **前端监控页**：Vue 3 + TypeScript + Semantic UI
- **后台管理**：Vue 3 (CDN) + Semantic UI (CDN)
- **数据采集**：psutil
- **容器**：Docker 多阶段构建

## 兼容性

- 兼容 ServerStatus-Hotaru 原版 Python 客户端协议
- 旧客户端可直接连接，无需修改

## License

MIT
