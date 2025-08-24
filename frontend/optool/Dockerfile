# Stage 1: Build the Quasar app
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files first (for caching)
COPY package*.json ./
COPY quasar.config.* ./

# Install dependencies (this will run postinstall)
RUN npm install
RUN npm install -g @quasar/cli

# Copy the rest of the project
COPY . .

# Build Quasar
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist/spa /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
