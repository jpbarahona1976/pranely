# =============================================================================
# PRANELY Frontend Dockerfile
# Multi-stage build for Next.js 15
# =============================================================================

# ---- Dependencies ----
FROM node:22.13.1-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN npm install -g pnpm@9.12.2 && pnpm install

# ---- Builder ----
FROM node:22.13.1-alpine AS builder
WORKDIR /app
RUN npm install -g pnpm@9.12.2
COPY --from=deps /app/node_modules ./node_modules
COPY . ./
RUN pnpm build

# ---- Runner ----
FROM node:22.13.1-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
RUN npm install -g pnpm@9.12.2
COPY --from=builder /app ./
EXPOSE 3000
CMD ["pnpm", "start"]