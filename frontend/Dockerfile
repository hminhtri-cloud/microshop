# Giai đoạn 1: cài thư viện và build giao diện.
FROM node:24-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --include=dev --include=optional

COPY . .
RUN npm run build

# Giai đoạn 2: chỉ giữ Nginx và giao diện đã build.
FROM nginx:1.28-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]