# ServerStatus-Rabbit 测试环境说明

更新时间：2026-04-02

本目录的作用只有一个：

让任何后来接手这个项目的人，第一时间知道现在有哪些可用测试机器、每台机器扮演什么角色、ServerStatus-Rabbit 已经实际部署到了哪里、应该用什么方式登录和核验。

## 1. 当前测试环境拓扑

### 1.1 服务端

| 角色 | IP | 主机名 | 当前用途 |
| --- | --- | --- | --- |
| ServerStatus-Rabbit 服务端 | 123.253.226.10 | Test-HK1 | 部署 v0.130 服务端，提供 Web 页面、管理页和 TCP 上报通道 |

### 1.2 客户端

| 角色 | IP | 主机名 | 当前用途 |
| --- | --- | --- | --- |
| ServerStatus Client 11 | 123.253.226.11 | test2 | 连接 123.253.226.10:9292，上报主机状态 |
| ServerStatus Client 12 | 123.253.226.12 | test3 | 连接 123.253.226.10:9292，上报主机状态 |
| ServerStatus Client 13 | 123.253.226.13 | test4 | 连接 123.253.226.10:9292，上报主机状态 |

## 2. 2026-04-02 实际部署结果

以下内容不是计划，而是已经完成并实际验证通过的状态：

| IP | 部署结果 | 运行方式 | 已核验事实 |
| --- | --- | --- | --- |
| 123.253.226.10 | 已部署服务端 | Docker | 代码位于 /opt/ServerStatus-Rabbit；容器名 ssr-server；镜像名 serverstatus-rabbit:v0.130；对外使用 9291 和 9292 |
| 123.253.226.11 | 已部署客户端 | Python venv + systemd | 代码位于 /opt/ServerStatus-Rabbit；服务名 serverstatus-rabbit-client.service；状态 active |
| 123.253.226.12 | 已部署客户端 | Python venv + systemd | 代码位于 /opt/ServerStatus-Rabbit；服务名 serverstatus-rabbit-client.service；状态 active |
| 123.253.226.13 | 已部署客户端 | Python venv + systemd | 代码位于 /opt/ServerStatus-Rabbit；服务名 serverstatus-rabbit-client.service；状态 active |

补充结论：

1. 四台机器都已经通过 D:/wingsrabbit-key/id_rsa_private 实机登录验证。
2. 123.253.226.10 当前同时还承载 NetworkStatus-Rabbit，所以不能占用它原有的 9191 和 9192。
3. 本次 ServerStatus-Rabbit 测试部署已明确改走 9291 和 9292，不影响现有 NetworkStatus-Rabbit。
4. 服务端当前通过 http://127.0.0.1:9291/api/stats 已实际看到 3 个客户端全部 online=true。

## 3. 当前部署参数

### 3.1 服务端 123.253.226.10

| 项目 | 当前值 |
| --- | --- |
| 部署路径 | /opt/ServerStatus-Rabbit |
| Git 基线 | GitHub main |
| 实际版本口径 | v0.130 |
| Web 端口 | 9291 |
| TCP 上报端口 | 9292 |
| 容器名 | ssr-server |
| 镜像名 | serverstatus-rabbit:v0.130 |
| 页面标题 | ServerStatus-Rabbit v0.130 Test |
| 页面副标题 | Server 123.253.226.10 with clients 123.253.226.11-13 |

管理页和监控页访问入口：

1. 监控页：http://123.253.226.10:9291/
2. 管理页：http://123.253.226.10:9291/admin

### 3.2 客户端 123.253.226.11 到 123.253.226.13

| 客户端 IP | 用户名 | 密码 | systemd 服务 | 连接目标 |
| --- | --- | --- | --- | --- |
| 123.253.226.11 | ssr-11 | SSR130-client11 | serverstatus-rabbit-client.service | 123.253.226.10:9292 |
| 123.253.226.12 | ssr-12 | SSR130-client12 | serverstatus-rabbit-client.service | 123.253.226.10:9292 |
| 123.253.226.13 | ssr-13 | SSR130-client13 | serverstatus-rabbit-client.service | 123.253.226.10:9292 |

客户端统一参数：

1. 部署路径都是 /opt/ServerStatus-Rabbit
2. Python 虚拟环境路径都是 /opt/ServerStatus-Rabbit/venv
3. 服务以 root 用户运行
4. 服务设置为开机自启并自动重启

## 4. 登录方式

当前这组测试机器统一按 SSH 密钥登录。

已知信息：

1. 密钥目录在 D:/wingsrabbit-key/
2. 当前已经实机确认：四台机器都可以使用 D:/wingsrabbit-key/id_rsa_private 登录
3. 当前已经实机确认：四台机器登录用户都是 root

## 5. 核验方式

### 5.1 在服务端核验

常用检查：

1. 查看服务端容器是否存在：docker ps --format '{{.Names}} {{.Image}} {{.Ports}}'
2. 查看服务端统计接口：curl http://127.0.0.1:9291/api/stats
3. 查看服务端代码目录：ls -la /opt/ServerStatus-Rabbit

### 5.2 在客户端核验

常用检查：

1. 查看 systemd 状态：systemctl status serverstatus-rabbit-client --no-pager
2. 查看最近日志：journalctl -u serverstatus-rabbit-client -n 20 --no-pager
3. 查看代码目录：ls -la /opt/ServerStatus-Rabbit

## 6. 注意事项

这组机器当前不是纯净环境，已经同时承载另一套系统，所以后续操作必须注意边界：

1. 123.253.226.10 上已有 NetworkStatus-Rabbit 的 ns-center、ns-nginx、ns-influxdb 容器在运行。
2. 123.253.226.11 到 123.253.226.13 上已有 networkstatus-agent.service 在运行。
3. 不要为了处理 ServerStatus-Rabbit 去停掉现有的 NetworkStatus-Rabbit 服务。
4. 不要把 ServerStatus-Rabbit 的端口改回 9191 或 9192，除非先处理现有环境冲突。
5. 如果要重部署服务端，优先只操作 /opt/ServerStatus-Rabbit 和 ssr-server。
6. 如果要重部署客户端，优先只操作 /opt/ServerStatus-Rabbit 和 serverstatus-rabbit-client.service。

## 7. 新人接手时最短结论

如果只是想快速接手这套测试环境，先记住下面几件事：

1. ServerStatus-Rabbit 服务端在 123.253.226.10，不在 9191 和 9192，而是在 9291 和 9292。
2. 三台客户端是 123.253.226.11 到 123.253.226.13，已经接入并在线。
3. 服务端用 Docker，客户端用 Python venv + systemd。
4. 全部机器都用 root + D:/wingsrabbit-key/id_rsa_private 登录。
5. 这次实机部署对应的仓库版本口径是 v0.130，代码基线来自 GitHub main。