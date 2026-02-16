#!/bin/bash
# CubeSat-1U root3315-ui - Quick Start Script
# Автоматическая установка и запуск системы

set -e

echo "============================================================"
echo "CubeSat-1U root3315-ui - Быстрый Старт"
echo "============================================================"
echo

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка Python
echo "[1/6] Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 не найден!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 установлен ($(python3 --version))${NC}"

# Проверка зависимостей
echo
echo "[2/6] Проверка зависимостей..."
REQUIRED_PACKAGES="pyserial numpy opencv-python Pillow cryptography psutil requests aiohttp"
MISSING_PACKAGES=""

for package in $REQUIRED_PACKAGES; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES="$MISSING_PACKAGES $package"
    fi
done

if [ -n "$MISSING_PACKAGES" ]; then
    echo -e "${YELLOW}! Отсутствуют пакеты:$MISSING_PACKAGES${NC}"
    echo "Установка зависимостей..."
    
    if [ -f "src/raspberry-pi-code/requirements.txt" ]; then
        pip3 install --break-system-packages -r src/raspberry-pi-code/requirements.txt
    else
        pip3 install --break-system-packages $MISSING_PACKAGES
    fi
    echo -e "${GREEN}✓ Зависимости установлены${NC}"
else
    echo -e "${GREEN}✓ Все зависимости установлены${NC}"
fi

# Генерация ключей безопасности
echo
echo "[3/6] Генерация ключей безопасности..."

if [ -z "$CUBESAT_SHARED_SECRET" ]; then
    echo "Генерация CUBESAT_SHARED_SECRET..."
    export CUBESAT_SHARED_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo -e "${GREEN}✓ Сгенерирован секретный ключ${NC}"
    echo "  (сохраните его для продакшена)"
else
    echo -e "${GREEN}✓ CUBESAT_SHARED_SECRET уже установлен${NC}"
fi

# Создание директорий
echo
echo "[4/6] Создание рабочих директорий..."

for dir in logs certs backups updates images telemetry; do
    mkdir -p "src/raspberry-pi-code/$dir"
done

for dir in logs certs; do
    mkdir -p "src/ground-station/$dir"
done

echo -e "${GREEN}✓ Директории созданы${NC}"

# Генерация SSL сертификатов (опционально)
echo
echo "[5/6] Генерация SSL сертификатов..."

if [ ! -f "src/raspberry-pi-code/certs/server.crt" ]; then
    if command -v openssl &> /dev/null; then
        echo "Генерация самоподписанных сертификатов..."
        openssl req -x509 -newkey rsa:2048 \
            -keyout "src/raspberry-pi-code/certs/server.key" \
            -out "src/raspberry-pi-code/certs/server.crt" \
            -days 365 -nodes \
            -subj "/C=US/ST=CA/L=SF/O=CubeSat/CN=cubesat.local" 2>/dev/null
        echo -e "${GREEN}✓ SSL сертификаты сгенерированы${NC}"
    else
        echo -e "${YELLOW}! OpenSSL не найден, SSL будет отключен${NC}"
    fi
else
    echo -e "${GREEN}✓ SSL сертификаты уже существуют${NC}"
fi

# Проверка конфигурации
echo
echo "[6/6] Проверка конфигурации..."

if [ -f "config/config.json" ]; then
    echo -e "${GREEN}✓ Конфигурация найдена${NC}"
else
    echo -e "${YELLOW}! Конфигурация не найдена, будет создана${NC}"
fi

# Финальные инструкции
echo
echo "============================================================"
echo -e "${GREEN}✓ Установка завершена успешно!${NC}"
echo "============================================================"
echo
echo "Запуск системы:"
echo
echo "1. Запуск бортового контроллера (Raspberry Pi):"
echo "   cd src/raspberry-pi-code"
echo "   export CUBESAT_SHARED_SECRET='your-secret-key'"
echo "   python3 flight_controller.py"
echo
echo "2. Запуск наземной станции (в новом терминале):"
echo "   cd src/ground-station"
echo "   streamlit run ground_station.py"
echo
echo "3. Открыть веб-интерфейс:"
echo "   http://localhost:8501"
echo
echo "============================================================"
echo "Документация:"
echo "  - README.md - основная документация"
echo "  - TEST_REPORT.md - отчет о тестировании"
echo "  - BUG_FIXES_SUMMARY.md - исправления безопасности"
echo "  - docs/ - полная документация"
echo "============================================================"
echo
