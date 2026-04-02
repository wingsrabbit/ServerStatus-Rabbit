# v0.121 更新说明

版本状态：已发布标签

来源：

- Git tag：v0.121
- 标签日期：2026-03-19
- 对应提交：18151ae
- 提交标题：fix: 修复 App.vue ESLint no-empty-function 错误

本版本定位：

- 将 v0.12 的前端 UI 升级和一次 ESLint 修复一起收敛成带标签版本

核心更新：

- 实际打包了 v0.12 的前端 UI 四项需求实现
- 修复 App.vue 中的 ESLint no-empty-function 问题
- 同步补齐页面标题、CPU 核心数、在线时间等前后端配套逻辑

改动规模：

- 12 个文件变更
- 287 行新增
- 29 行删除

主要涉及文件：

- client/collector.py
- server/config_manager.py
- server/state.py
- server/web_server.py
- web/admin/index.html
- web/status-src/src/App.vue
- web/status-src/src/components/TableItem.vue
- web/status-src/src/components/TheFooter.vue
- web/status-src/src/components/TheHeader.vue
- web/status-src/src/components/useStatus.ts
- web/status-src/src/types/index.ts

备注：

- 如果把 v0.12 看作功能节点，那么 v0.121 更像是它的首个可交付标签版。