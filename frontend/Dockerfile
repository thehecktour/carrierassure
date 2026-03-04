# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Multi-stage Dockerfile for Next.js app with standalone output,
#          optimized for Docker Compose integration."
# Modifications: Switched from Vite/Nginx to Next.js standalone output,
#                replaced VITE_API_URL with NEXT_PUBLIC_API_URL,
#                removed nginx stage in favor of Next.js built-in server.
# --- END AI-ASSISTED ---

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]