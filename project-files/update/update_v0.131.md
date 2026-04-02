# v0.131 更新说明

版本状态：当前 NG 升级版本

来源：

- 基于 GitHub `main` 的 v0.130 收口版本复制出独立目录 `ServerStatus-Rabbit-NG`
- 在该副本中创建并使用 Git 分支 `ServerStatus-Rabbit-NG`

本版本定位：

- 用于继续演进而不触碰正式主线 `main` 的 NG 升级版本
- 完成服务端、既有客户端和新增 NAT 客户端的统一升级部署版本

本次升级内容：

- 将版本文案从 v0.130 升级到 v0.131
- 新增 `project-files/update/update_v0.131.md` 作为当前正式版本说明
- 更新 `project-files/update/README.md`，明确 NG 分支正式版本切换到 v0.131
- 更新 `project-files/testread/README.md`，纳入 192.168.88.102 NAT 客户端和五机实际部署结果
- 更新 `project-files/20260402-project.md`，使总档与 NG 分支现状保持一致
- 计划将服务端与全部客户端统一切换到 `ServerStatus-Rabbit-NG` 分支对应代码
- 新增 `scripts/install-server.sh` 与 `scripts/install-client.sh`
- 更新 README 与后台生成的部署命令，使服务端和客户端都支持一行安装，并统一适配 NAT 与公网客户端
- 修复后台创建节点后生成的客户端部署命令：改为可直接粘贴执行的单行命令，并自动填入当前服务端地址
- 修复 README 中一行安装命令的粘贴体验：去掉外层嵌套引号，执行时会先输出下载与运行提示，避免看起来像卡死
- 修复一行安装脚本中的 Docker 安装路径：优先使用系统包管理器安装 Docker，失败时再回退到 `get.docker.com`
- 修复一行安装脚本对已有仓库的处理：如果现有 `origin` 不是 GitHub 官方仓库，会自动改回正确远端后继续更新
- 修复一行安装脚本对脏工作树的处理：客户端会自动 fresh clone，服务端会在保留 `data/` 的前提下刷新代码
- 调整客户端一行安装的默认代码目录：改为 `/opt/ServerStatus-Rabbit-节点用户名`，避免同机已有部署互相踩目录
- 更新后台节点创建后生成的客户端命令：显式带上 `SSR_APP_DIR=/opt/ServerStatus-Rabbit-用户名`，让复制出的命令本身就是完整且可复现的
- 增加客户端一行安装的运行时兜底：若 Docker 基础镜像拉取失败，会自动退到 `python3 + venv + systemd` 继续完成部署

本次部署侧变化：

- 服务端继续运行在 123.253.226.10，端口仍为 9291 和 9292
- 123.253.226.11 到 123.253.226.13 保持原有连接方式，但升级为 v0.131 对应代码基线
- 新增 192.168.88.102 作为纯 NAT 客户端，不需要任何公网入口，只通过主动出站连接 123.253.226.10:9292 接入

当前应以什么为准：

- `main`：继续保留 v0.130 正式版
- `ServerStatus-Rabbit-NG`：当前 v0.131 升级分支
- 当前 NG 版本号：`v0.131`

备注：

- 这个文件描述的是 NG 升级路径，不覆盖 `main` 上 v0.130 的正式版事实。
- 如果后续继续演进，应继续在 `ServerStatus-Rabbit-NG` 或其后续替代分支上进行，而不要直接改动正式主线。