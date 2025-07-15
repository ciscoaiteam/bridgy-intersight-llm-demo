# Distribution Only Build

# Simple nginx container for pre-built React app (OpenShift compatible)
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy pre-built React app from local dist folder
COPY dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Make nginx run as any user (OpenShift will assign a random UID)
RUN chmod -R 755 /usr/share/nginx/html && \
    chmod -R 777 /var/cache/nginx && \
    chmod -R 777 /var/run && \
    chmod -R 777 /etc/nginx

# Expose port 8080 (OpenShift doesn't allow privileged ports)
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]