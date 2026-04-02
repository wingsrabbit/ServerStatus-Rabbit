# v0.123 更新说明

版本状态：已发布标签

来源：

- Git tag：v0.123
- 标签日期：2026-03-19
- 对应提交：f62d73f
- 提交标题：fix: v0.123 维护中样式统一 + 离线检测优化

本版本定位：

- 一个围绕离线状态视觉和掉线行为的稳定性修复版

核心更新：

- 统一监控页中“维护中”状态的展示样式
- 优化节点离线检测与状态切换逻辑
- 调整告警、TCP 连接处理和 Web 层对离线状态的配合方式

改动规模：

- 7 个文件变更
- 403 行新增
- 21 行删除

主要涉及文件：

- server/alert.py
- server/state.py
- server/tcp_server.py
- server/web_server.py
- web/status-src/src/components/TableItem.vue
- README.md

备注：

- 这是从“能显示”走向“离线状态更一致、更可信”的一次修补。