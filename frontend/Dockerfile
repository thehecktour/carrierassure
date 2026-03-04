# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Multi-stage Dockerfile for Next.js app with standalone output,
#          optimized for Docker Compose integration."
# Modifications: Removed COPY public step since no static assets exist,
#                added mkdir -p public to avoid missing directory error,
#                added HOSTNAME=0.0.0.0 and PORT=3000 for container binding,
#                switched from Vite/Nginx to Next.js standalone server.
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
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN mkdir -p ./public

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]