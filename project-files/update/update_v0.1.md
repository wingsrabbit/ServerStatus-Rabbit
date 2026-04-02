# v0.1 更新说明

版本状态：已发布标签

来源：

- Git tag：v0.1
- 标签日期：2026-03-19
- 对应提交：0601d24
- 提交标题：feat: ServerStatus-Rabbit v0.1 初始版本

本版本定位：

- 项目初始版本
- 后续所有小版本的基础基线

核心更新：

- 建立服务端和客户端共仓库、共入口的整体结构
- 落地 TCP 上报协议、节点状态管理、Flask Web 服务和后台管理页
- 引入 JSON 配置持久化、Webhook、HTTPS 管理和恢复脚本
- 提供 Dockerfile、requirements.txt 和完整部署骨架
- 集成 Vue 监控页源码工程、静态资源和区域图标素材

改动规模：

- 303 个文件变更
- 29078 行新增

主要落地目录：

- client/
- server/
- web/admin/
- web/status-src/
- app.py、Dockerfile、recover.py、README.md

备注：

- 这是 ServerStatus-Rabbit 真正意义上的起点版本。