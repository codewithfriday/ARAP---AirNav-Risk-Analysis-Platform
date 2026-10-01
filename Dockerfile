# NAVRAP — single container (API + web app) for free/simple hosting such as Render.
# Build: docker build -t navrap .   Run: docker run -p 8000:8000 -e ARAP_DATABASE_URL=... -e ARAP_SECRET_KEY=... navrap
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ARAP_STATIC_DIR=/app/static MPLCONFIGDIR=/tmp/matplotlib
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /web/dist /app/static
EXPOSE 8000
# Render (and most hosts) set $PORT; one worker keeps memory inside a 512 MB free instance.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
