# Nua Frontend — React (CRA + craco) served by nginx.
# REACT_APP_BACKEND_URL is baked at BUILD time (CRA replaces it in the bundle),
# so it must be passed via --build-arg or fly.toml's [build.args].
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 600000

COPY . .

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}
RUN yarn build

# ---------- runtime ----------
FROM nginx:alpine

# SPA-friendly nginx config — every unknown path falls through to /index.html
RUN printf '%s\n' \
    'server {' \
    '  listen 8080;' \
    '  root /usr/share/nginx/html;' \
    '  gzip on;' \
    '  gzip_types text/plain text/css application/javascript application/json image/svg+xml;' \
    '  location / {' \
    '    try_files $uri $uri/ /index.html;' \
    '  }' \
    '  location ~* \.(?:js|css|woff2?|ttf|png|jpg|jpeg|gif|svg|ico)$ {' \
    '    expires 30d;' \
    '    add_header Cache-Control "public, immutable";' \
    '  }' \
    '}' > /etc/nginx/conf.d/default.conf

COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
