# =============================================================================
# PRANELY Frontend Dockerfile
# Multi-stage build for Next.js 15
# =============================================================================

# =============================================================================
# PRANELY Frontend Dockerfile
# Development build with hot reload
# =============================================================================

FROM node:22.13.1-alpine
WORKDIR /app
RUN npm install -g pnpm@9.12.2
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]