FROM node:22-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile --ignore-scripts || pnpm install --ignore-scripts
RUN node node_modules/esbuild/install.js
COPY . .
RUN pnpm build

FROM node:22-slim
WORKDIR /app
COPY --from=build /app/.output ./.output
ENV HOST=0.0.0.0 PORT=3000
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
