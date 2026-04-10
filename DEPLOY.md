# Деплой Arb-Scanner на сервер

## Шаг 1 — Купить сервер

Самый простой и дешёвый вариант — **Hetzner** (ты в Европе, сервера рядом):

1. Зайди на https://www.hetzner.com/cloud
2. Зарегистрируйся
3. Создай сервер:
   - Location: **Falkenstein** (или Amsterdam)
   - OS: **Ubuntu 24.04**
   - Type: **CX22** (2 CPU, 4GB RAM) — ~€4/мес
   - SSH Key: добавь свой (инструкция ниже)
4. Запиши IP-адрес сервера

### Как создать SSH-ключ (Windows)

Открой PowerShell и выполни:
```
ssh-keygen -t ed25519
```
Нажимай Enter на все вопросы. Затем:
```
cat ~/.ssh/id_ed25519.pub
```
Скопируй результат и вставь при создании сервера в Hetzner.


## Шаг 2 — Подключиться к серверу

```
ssh root@ТВОЙ_IP
```


## Шаг 3 — Загрузить проект на сервер

С компьютера (в новом терминале):
```
scp -r C:\Users\EgorY\crypto_signals\Arb_scanner root@ТВОЙ_IP:~/arb-scanner
```


## Шаг 4 — Установить Docker

На сервере:
```
bash arb-scanner/setup_server.sh
```
Дождись окончания. Затем:
```
exit
```
И подключись заново:
```
ssh root@ТВОЙ_IP
```


## Шаг 5 — Проверить .env

```
nano arb-scanner/backend/.env
```
Убедись что TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID заполнены.
Сохрани: Ctrl+O, Enter, Ctrl+X.


## Шаг 6 — Запустить!

```
cd arb-scanner
docker compose up -d --build
```

Готово! Сканер работает в фоне 24/7.


## Полезные команды

```bash
# Посмотреть логи (живые)
docker compose logs -f

# Посмотреть статус
docker compose ps

# Остановить
docker compose down

# Перезапустить
docker compose restart

# Обновить код и перезапустить
docker compose up -d --build
```


## Подключить дашборд с ПК

Открой в браузере:
```
http://ТВОЙ_IP:8000/prices
http://ТВОЙ_IP:8000/stats
```

Чтобы подключить React-дашборд к серверу,
поменяй в frontend/src/App.js:
```
const WS_URL = "ws://ТВОЙ_IP:8000/ws";
const API_URL = "http://ТВОЙ_IP:8000";
```
