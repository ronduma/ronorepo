# syntax=docker/dockerfile:1
FROM oven/bun:alpine

WORKDIR /app

# copy package files
COPY src/frontend/package.json src/frontend/bun.lock ./

# install dependencies
RUN bun install --frozen-lockfile

# copy source code
COPY src/frontend/ .

# expose the development port
EXPOSE 3000

# set environment to development
ENV NODE_ENV development

# run the development server
CMD ["bun", "run", "dev"]
