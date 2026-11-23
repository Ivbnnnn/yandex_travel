FROM node:24-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run lint
RUN npm run build

FROM nginx:1.30.7-alpine
COPY --from=build /app/dist/ /usr/share/nginx/html/
