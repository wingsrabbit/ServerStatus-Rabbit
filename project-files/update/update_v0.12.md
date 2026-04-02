# v0.12 更新说明

版本状态：开发分支节点，未发现独立 Git tag

来源：

- 提交：298aead
- 提交标题：feat: v0.12 前端 UI 四项需求实现
- README 中提到的开发分支：ServerStatus-Rabbit-feature-v0.12

本版本定位：

- 一次以监控页体验为核心的前端升级节点
- 后续被纳入 v0.121 所在的标签区间

核心更新：

- 支持自定义页面标题和副标题
- 优化在线时间格式化展示
- 增加 CPU 核心数显示
- 页脚更新时间改进为更实时的展示方式
- 为上述 UI 改动补齐前后端数据字段和设置接口

主要涉及模块：

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

备注：

- 虽然没有独立 tag，但它是 v0.121 之前最重要的功能节点之一。