# v0.128 更新说明

版本状态：已发布标签

来源：

- Git tag：v0.128
- 标签日期：2026-03-19
- 对应提交：acee974
- 提交标题：fix(admin): certbot 失败时显示真实错误信息 v0.128

本版本定位：

- 围绕 HTTPS 证书申请失败可诊断性的修复版

核心更新：

- 后台在 certbot 失败时尽量返回真实错误信息，而不是模糊失败提示
- 改进 HTTPS/certbot 异常链路中的错误透传
- 降低管理员排查 Let's Encrypt 申请失败时的信息损耗

改动规模：

- 4 个文件变更
- 52 行新增
- 8 行删除

主要涉及文件：

- server/https_manager.py
- server/web_server.py
- web/admin/index.html

备注：

- 这是 v0.126 问题分析之后的实际落地修复版本。