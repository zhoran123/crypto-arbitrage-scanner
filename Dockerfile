# === Стадия 1: сборка React ===
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# === Стадия 2: Python бэкенд ===
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Зависимости
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код бэкенда
COPY backend/ .

# Копируем собранный фронтенд
COPY --from=frontend-build /app/build ./static

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
