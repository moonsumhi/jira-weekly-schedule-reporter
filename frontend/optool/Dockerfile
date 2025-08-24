# Stage 1: Build Quasar app
FROM node:20-alpine AS builder

# Set working directory inside container
WORKDIR /app

# Copy everything from the Quasar project
COPY . .

# Install global Quasar CLI
RUN npm install -g @quasar/cli

# Install dependencies
RUN npm install

# Build production version
RUN npx quasar build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default Nginx files
RUN rm -rf /usr/share/nginx/html/*

# Copy built SPA from builder
COPY --from=builder /app/dist/spa /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
