# Docker развертывание CubeSat 1U системы

## Обзор

CubeSat 1U система может быть развернута с использованием Docker контейнеров для изоляции, управления зависимостями и упрощения деплоя.

## Структура Docker

### Docker файлы
```
CubeSat-1U/
├── Dockerfile              # Dockerfile для Raspberry Pi компонента
├── Dockerfile.ground       # Dockerfile для наземной станции
├── docker-compose.yml      # Композиция сервисов
└── docker/                 # Дополнительные Docker файлы
    ├── docker-compose.prod.yml  # Продуктовая композиция
    └── docker-compose.dev.yml   # Разработка композиция
```

## Dockerfile для Raspberry Pi компонента

### Основной Dockerfile
```dockerfile
# Dockerfile для CubeSat Raspberry Pi компонента
FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        git \
        curl \
        gnupg \
        build-essential \
        libatlas-base-dev \
        libhdf5-serial-dev \
        libjasper-dev \
        libqtgui4 \
        libqt4-test \
        pkg-config \
        zip \
        && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей Python
COPY raspberry-pi-code/requirements.txt /app/requirements.txt

# Установка зависимостей Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копирование проекта
COPY . /app/

# Создание необходимых директорий
RUN mkdir -p /app/logs /app/data /app/images /app/telemetry /app/updates /app/backups

# Создание непривилегированного пользователя для безопасности
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Открытие портов (если необходимо для сетевых сервисов)
EXPOSE 5000

# Запуск контроллера полета
CMD ["python", "raspberry-pi-code/flight_controller.py"]
```

## Dockerfile для наземной станции

### Dockerfile.ground
```dockerfile
# Dockerfile для наземной станции CubeSat
FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей Python
COPY ground-station/requirements.txt /app/requirements.txt

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Установка Streamlit для веб-интерфейса
RUN pip install streamlit plotly pandas

# Копирование проекта
COPY ground-station/ /app/

# Создание необходимых директорий
RUN mkdir -p /app/logs /app/data /app/images

# Создание непривилегированного пользователя
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Открытие порта для веб-интерфейса
EXPOSE 8501

# Запуск веб-интерфейса
CMD ["streamlit", "run", "ground_station.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

## Docker Compose конфигурация

### docker-compose.yml
```yaml
version: '3.8'

services:
  cubesat-pi:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: cubesat-pi
    volumes:
      - ./config.json:/app/config.json
      - ./logs:/app/logs
      - ./data:/app/data
      - ./images:/app/images
      - ./telemetry:/app/telemetry
    environment:
      - PYTHONUNBUFFERED=1
      - CUBESAT_DEBUG=false
    networks:
      - cubesat-network
    privileged: true  # Требуется для GPIO доступа (в реальном развертывании)
    restart: unless-stopped

  ground-station:
    build:
      context: .
      dockerfile: Dockerfile.ground
    container_name: ground-station
    volumes:
      - ./config.json:/app/config.json
      - ./logs:/app/logs
    ports:
      - "8501:8501"  # Веб-интерфейс наземной станции
    environment:
      - STREAMLIT_SERVER_ENABLE_CORS=false
      - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
    networks:
      - cubesat-network
    depends_on:
      - cubesat-pi
    restart: unless-stopped

networks:
  cubesat-network:
    driver: bridge

volumes:
  config-data:
  log-data:
  telemetry-data:
  image-data:
```

## Сборка и запуск

### Сборка образов
```bash
# Сборка всех образов
docker-compose build

# Сборка конкретного сервиса
docker-compose build cubesat-pi
docker-compose build ground-station
```

### Запуск контейнеров
```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск конкретного сервиса
docker-compose up cubesat-pi -d
docker-compose up ground-station -d
```

### Проверка состояния
```bash
# Проверка статуса контейнеров
docker-compose ps

# Просмотр логов
docker-compose logs -f
docker-compose logs -f cubesat-pi
docker-compose logs -f ground-station
```

## Управление контейнерами

### Остановка и удаление
```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением томов
docker-compose down -v

# Перезапуск сервиса
docker-compose restart cubesat-pi
```

### Обновление образов
```bash
# Пересборка и обновление
docker-compose up -d --build

# Обновление конкретного сервиса
docker-compose up -d --build cubesat-pi
```

## Продуктовое развертывание

### docker-compose.prod.yml
```yaml
version: '3.8'

services:
  cubesat-pi:
    build:
      context: .
      dockerfile: Dockerfile
    image: cubesat/cubesat-pi:latest
    container_name: cubesat-pi-prod
    volumes:
      - /opt/cubesat/config.json:/app/config.json:ro
      - /opt/cubesat/logs:/app/logs
      - /opt/cubesat/data:/app/data
    environment:
      - PYTHONUNBUFFERED=1
      - CUBESAT_DEBUG=false
    networks:
      - cubesat-prod
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  ground-station:
    build:
      context: .
      dockerfile: Dockerfile.ground
    image: cubesat/ground-station:latest
    container_name: ground-station-prod
    volumes:
      - /opt/cubesat/logs:/app/logs
    ports:
      - "80:8501"  # Продуктовый порт
    environment:
      - STREAMLIT_SERVER_ENABLE_CORS=false
      - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
    networks:
      - cubesat-prod
    depends_on:
      - cubesat-pi
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  cubesat-prod:
    driver: bridge

volumes:
  prod-logs:
  prod-data:
  prod-telemetry:
```

## Разработка с Docker

### docker-compose.dev.yml
```yaml
version: '3.8'

services:
  cubesat-pi-dev:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: cubesat-pi-dev
    volumes:
      - ./:/app  # Монтирование исходного кода для разработки
      - ./config.json:/app/config.json
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - CUBESAT_DEBUG=true
    networks:
      - cubesat-dev
    stdin_open: true
    tty: true
    restart: "no"

  ground-station-dev:
    build:
      context: .
      dockerfile: Dockerfile.ground
    container_name: ground-station-dev
    volumes:
      - ./ground-station:/app
      - ./logs:/app/logs
    ports:
      - "8501:8501"
    environment:
      - STREAMLIT_SERVER_ENABLE_CORS=false
      - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
      - STREAMLIT_SERVER_HEADLESS=false
    networks:
      - cubesat-dev
    depends_on:
      - cubesat-pi-dev
    stdin_open: true
    tty: true
    restart: "no"

networks:
  cubesat-dev:
    driver: bridge
```

## Запуск в режиме разработки
```bash
# Запуск в режиме разработки
docker-compose -f docker-compose.dev.yml up

# Запуск конкретного сервиса в режиме разработки
docker-compose -f docker-compose.dev.yml up cubesat-pi-dev
```

## Безопасность в Docker

### Безопасные практики

1. **Непривилегированные пользователи**:
   - Все контейнеры запускаются от непривилегированного пользователя
   - Избегайте использования root пользователя

2. **Ограничение ресурсов**:
   ```yaml
   services:
     cubesat-pi:
       # ...
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '0.5'
           reservations:
             memory: 256M
             cpus: '0.25'
   ```

3. **Сканеры уязвимостей**:
   - Регулярное сканирование образов на уязвимости
   - Использование безопасных базовых образов

4. **Минимизация поверхности атаки**:
   - Минимальный набор открытых портов
   - Ограничение доступа к хост-системе

## Мониторинг контейнеров

### Docker Stats
```bash
# Мониторинг ресурсов контейнеров
docker stats

# Мониторинг конкретного контейнера
docker stats cubesat-pi
```

### Логирование
```bash
# Просмотр логов контейнера
docker logs cubesat-pi
docker logs ground-station

# Прослушивание логов в реальном времени
docker logs -f cubesat-pi
```

## CI/CD интеграция

### Пример GitHub Actions workflow
```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v1
    
    - name: Login to DockerHub
      uses: docker/login-action@v1
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push cubesat-pi
      uses: docker/build-push-action@v2
      with:
        context: .
        file: ./Dockerfile
        push: true
        tags: cubesat/cubesat-pi:latest
    
    - name: Build and push ground-station
      uses: docker/build-push-action@v2
      with:
        context: .
        file: ./Dockerfile.ground
        push: true
        tags: cubesat/ground-station:latest
```

## Устранение неполадок

### Общие проблемы

1. **Недостаточно прав для GPIO**:
   - Добавить `--privileged` флаг или конкретные устройства
   - В продуктивной среде использовать более точные разрешения

2. **Проблемы с сетью**:
   - Проверить настройки сети в compose файле
   - Убедиться, что порты не заняты

3. **Недостаточно памяти**:
   - Увеличить лимиты памяти в compose файле
   - Оптимизировать приложение для меньшего потребления

### Команды диагностики
```bash
# Проверка состояния системы
docker system df

# Проверка использования ресурсов
docker stats --no-stream

# Проверка образов
docker images

# Проверка контейнеров
docker ps -a
```

## Лицензия
MIT License