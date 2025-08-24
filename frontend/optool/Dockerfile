# Stage 1: Build the Quasar app
FROM node:20-alpine AS builder

# Set working directory to Quasar project
WORKDIR /app

# Copy package.json and package-lock.json for dependency install
COPY frontend/optool/package*.json ./

# Install dependencies
RUN npm install

# Install Quasar CLI globally
RUN npm install -g @quasar/cli

# Copy the rest of the frontend source code
COPY frontend/optool/ .

# Build the production version
RUN quasar build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx static files
RUN rm -rf /usr/share/nginx/html/*

# Copy built files from builder
COPY --from=builder /app/dist/spa /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
