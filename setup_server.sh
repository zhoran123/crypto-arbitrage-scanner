#!/bin/bash
# ============================================
# Установка Arb-Scanner на сервер (Ubuntu)
# Запусти один раз: bash setup_server.sh
# ============================================

echo "=== Обновление системы ==="
sudo apt update && sudo apt upgrade -y

echo "=== Установка Docker ==="
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

echo "=== Установка Docker Compose ==="
sudo apt install -y docker-compose-plugin

echo ""
echo "============================================"
echo "  Установка завершена!"
echo "  ВАЖНО: перезайди на сервер (exit + ssh)"
echo "  чтобы Docker заработал без sudo"
echo ""
echo "  Затем:"
echo "  1. cd arb-scanner"
echo "  2. nano backend/.env    (впиши токен)"
echo "  3. docker compose up -d --build"
echo "============================================"
