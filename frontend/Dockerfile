FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
ENV NODE_OPTIONS="--max-old-space-size=4096"
COPY package*.json ./

RUN npm ci --legacy-peer-deps

RUN npm cache clean --force
RUN rm -rf node_modules/.cache

# Explicitly install the correct esbuild version
RUN npm install esbuild@0.25.4 --save-dev

# Copy source code
COPY . .

# Build the application with legacy peer deps to avoid version conflicts
RUN npm run build -- --configuration=production

# Production stage
FROM nginx:alpine
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist/frontend/browser/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Debug: List files in nginx directory
RUN ls -la /usr/share/nginx/html/

# Start nginx
CMD ["nginx", "-g", "daemon off;"]