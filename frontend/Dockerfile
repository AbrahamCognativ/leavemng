FROM node:18-alpine as build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build --prod

# Copy build output to nginx
FROM nginx:alpine
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist/frontend/* /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Debug: List files in nginx directory
RUN ls -la /usr/share/nginx/html/

EXPOSE 80