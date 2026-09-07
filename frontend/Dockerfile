# =============================================================================
# CAMS Frontend — Multi-Stage Production Dockerfile
# =============================================================================
# Stage 1: Build static distribution bundle with Node.js 20 on Alpine
# Stage 2: Serve optimized assets via high-performance Nginx Alpine
# =============================================================================

# ── Stage 1: Build Single-Page Application ──────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Cache package dependencies
COPY package*.json ./
RUN npm ci

# Copy source code and compile production distribution
COPY . .
RUN npm run build

# ── Stage 2: Serve with Nginx Reverse Proxy ──────────────────────────────────
FROM nginx:alpine

# Remove default boilerplate configuration
RUN rm -rf /etc/nginx/conf.d/default.conf /usr/share/nginx/html/*

# Copy compiled SPA bundle and custom reverse-proxy routing rules
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
