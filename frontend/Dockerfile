FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
RUN npm install -g serve && addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /app/dist ./dist
USER app
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
