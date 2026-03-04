# --- AI-ASSISTED ---
# Tool: ChatGPT GPT-5
# Prompt: "Create a production-ready multi-stage Dockerfile for a Vite + React
#          dashboard using import.meta.env.VITE_API_URL, optimized for Docker
#          Compose integration with a Mongo + backend service architecture."
# Modifications: Implemented multi-stage build (Node → Nginx), injected VITE_API_URL
#                as build ARG, optimized layer caching strategy, added SPA-ready
#                Nginx configuration support, production-optimized alpine images.
# --- END AI-ASSISTED ---

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

RUN npm install

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html

RUN printf 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]