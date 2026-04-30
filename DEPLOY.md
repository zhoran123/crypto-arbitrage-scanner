# Деплой FlashArb на сервер

## Шаг 1 — Подготовить сервер

Самый простой сценарий — обычный Ubuntu-сервер с Docker.

1. Создай сервер.
2. Запиши его текущий публичный IP.
3. Добавь свой SSH-ключ при создании сервера.

### Как создать SSH-ключ на Windows

Открой PowerShell и выполни:

```bash
ssh-keygen -t ed25519
```

Потом выведи публичный ключ:

```bash
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

Скопируй его в панель провайдера при создании сервера.

## Шаг 2 — Подключиться к серверу

```bash
ssh root@ТВОЙ_IP
```

## Шаг 3 — Загрузить проект на сервер

С локального компьютера:

```bash
scp -r C:\Users\EgorY\Flasharb root@ТВОЙ_IP:~/Flasharb
```

## Шаг 4 — Установить Docker

На сервере:

```bash
bash ~/Flasharb/setup_server.sh
```

После установки переподключись по SSH, чтобы Docker работал корректно без старой сессии:

```bash
exit
ssh root@ТВОЙ_IP
```

## Шаг 5 — Проверить `.env`

```bash
nano ~/Flasharb/backend/.env
```

Убедись, что заполнены:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
MIN_TG_SPREAD=0.5
TELEGRAM_INVITE_URL=https://t.me/+...
```

## Шаг 6 — Открыть порт 8000

Если включен `ufw`, открой порт приложения:

```bash
ufw allow 8000/tcp
ufw status
```

## Шаг 7 — Запустить приложение

```bash
cd ~/Flasharb
docker compose up -d --build
```

## Шаг 8 — Проверить, что сервис жив

На сервере:

```bash
docker compose ps
docker compose logs --tail=100
curl http://127.0.0.1:8000/stats
```

Если `curl` на `127.0.0.1:8000` отвечает JSON, значит приложение поднялось нормально.

## Шаг 9 — Узнать актуальный внешний IP

Если сервер переезжал, пересоздавался или менялся провайдер, не используй старый IP из памяти.
Всегда проверяй текущий адрес командой:

```bash
hostname -I
curl -4 ifconfig.me
```

Открывай сайт только по актуальному адресу:

```text
http://АКТУАЛЬНЫЙ_IP:8000
```

## Полезные команды

```bash
# Статус контейнера
docker compose ps

# Логи
docker compose logs -f

# Пересборка и перезапуск
docker compose up -d --build

# Остановка
docker compose down

# Проверка порта на сервере
ss -ltnp | grep :8000

# Проверка firewall
ufw status numbered
```

## Важно

- Фронтенд не требует ручной правки `API_URL` или `WS_URL` перед деплоем: в production он работает от текущего `window.location.origin`.
- `HEAD /` может вернуть `405 Method Not Allowed` — это не ошибка сайта, если обычный `GET /` открывается.
- Если сайт локально внутри сервера работает, а снаружи нет, сначала проверяй актуальный IP и правила firewall.
