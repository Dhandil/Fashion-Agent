# ── 构建阶段：生成前端静态产物 ──
FROM node:22-alpine AS builder

WORKDIR /build

# 依赖层：只有 package.json / lockfile 变化才重新 npm ci
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 复制源码并构建
COPY frontend/ ./

# 演示/开发部署注入默认用户身份；真实生产由认证系统替代
ARG VITE_DEV_USER_ID=dev-user-001
RUN echo "VITE_DEV_USER_ID=${VITE_DEV_USER_ID}" > .env.production

RUN npm run build

# ── 运行阶段：nginx 托管静态文件并反向代理 /api ──
FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=5s \
  CMD wget -q -O - http://127.0.0.1/healthz || exit 1
