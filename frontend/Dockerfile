# The build context is the repository root (see backend/docker-compose.yml).
# `npm run build` runs `tsc -b`, which type-checks the generated-enum drift test
# against docs/openapi.json — a file outside frontend/, so a frontend-only
# context could not build the app at all.
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# The published contract the generated types are checked against.
COPY docs/openapi.json /docs/openapi.json

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
