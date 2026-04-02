# v0.122 更新说明

版本状态：已发布标签

来源：

- Git tag：v0.122
- 标签日期：2026-03-19
- 对应提交：e3126ff
- 提交标题：fix: v0.122 四项问题修复

本版本定位：

- 一个明确的问题修复版本
- 重点修正端口说明、在线时间语义和页脚更新时间逻辑

核心更新：

- 移除 Dockerfile 默认暴露 80 端口，并从 README 的常规 docker run 示例里去掉 80 映射
- 节点离线时，在线时间列改为显示破折号，而不是 0 秒
- 在线时间改为“本次连接时长”，不再直接展示服务器系统 uptime
- 页脚“最后更新”改成基于浏览器本地收到响应的时间计算，10 秒内统一显示为“10秒内”

改动规模：

- 7 个文件变更
- 122 行新增
- 11 行删除

主要涉及文件：

- Dockerfile
- README.md
- server/state.py
- web/status-src/src/App.vue
- web/status-src/src/components/TableItem.vue
- web/status-src/src/components/TheFooter.vue

备注：

- 这是当前项目里非常关键的一次语义修正，因为它改变了前端 uptime 的真实含义。