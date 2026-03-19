# 阶段 1：构建监控展示页前端
FROM node:18-slim AS frontend-builder
COPY web/status-src /frontend
WORKDIR /frontend
RUN npm install && npm run build

# 阶段 2：最终镜像
FROM python:3.12-slim

# 安装系统依赖（certbot 用于自动申请 Let's Encrypt 证书）
RUN apt-get update && apt-get install -y --no-install-recommends certbot && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制项目文件
COPY . /app
WORKDIR /app

# 复制前端构建产物
COPY --from=frontend-builder /frontend/dist /app/web/status/

# 暴露端口：Web(9191) + TCP通信(9192) + HTTPS(443) + HTTP验证(80)
EXPOSE 9191 9192 443 80

# 入口
ENTRYPOINT ["python", "app.py"]
