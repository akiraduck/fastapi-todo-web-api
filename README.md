Как запустить проект:

```bash
# Перейти в директорию проекта
cd fastapi-todo-web-api

# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

Запуск NATS:

```bash
docker compose up -d
```

Запуск сервера

```bash
# Новый терминал (с активированным venv и NATS!!!)
python -m uvicorn app.main:app --reload

# Вы должны увидеть:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

```
# Эндпоинт для websocket
ws://localhost:8000/ws/currencies
```

Для запуска nats-клиента с сообщениями в реальном времени запустить python app/nats_subscriber.py