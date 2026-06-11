# syntax=docker/dockerfile:1
FROM oven/bun:alpine

# install deps at root so the /app bind mount doesn't shadow node_modules
WORKDIR /
COPY src/frontend/package.json src/frontend/bun.lock ./
RUN bun install --frozen-lockfile

WORKDIR /app
COPY src/frontend/ .

# expose the development port
EXPOSE 3000

# set environment to development
ENV NODE_ENV development

# run the development server
CMD ["bun", "run", "dev"]
