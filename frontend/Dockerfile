# Stage 1: Build compilation
FROM node:24-alpine AS build

WORKDIR /app

# Copy dependency configs
COPY package.json ./
RUN npm install

# Copy source files
COPY . .

# Compile TypeScript and build production bundles
RUN npm run build

# Stage 2: Production web server
FROM nginx:alpine

# Copy custom Nginx routing configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from build stage to nginx folder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
